import asyncio
import json
import os
import time
from typing import Optional, Union

import boto3
import google.generativeai as genai
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

# --- Pydantic Models ---


class FileInfo(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int


class SearchResult(BaseModel):
    id: Union[str, int]
    payload: Optional[dict] = None
    score: float


class EmbedChunkRequest(BaseModel):
    workspace_id: int
    chunk_id: str
    task_id: Optional[str] = None


# --- App and Clients Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), timeout=60)
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
embedding_model = "models/embedding-001"

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

# Clients
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)

QDRANT_COLLECTION_NAME = "file_embeddings"


# --- Health ---


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "embedding-service"}


# --- Startup Event to Ensure Qdrant Collection Exists ---


@app.on_event("startup")
def startup_event():
    # Wait for Qdrant to be ready
    retries = 10
    while retries > 0:
        try:
            qdrant_client.get_collections()
            print("Qdrant is ready.")
            break
        except (UnexpectedResponse, Exception):
            print("Qdrant not ready, waiting...")
            time.sleep(5)
            retries -= 1

    if retries == 0:
        print("Could not connect to Qdrant. Exiting.")
        exit(1)

    try:
        qdrant_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
    except (UnexpectedResponse, Exception):
        qdrant_client.recreate_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=768, distance=models.Distance.COSINE
            ),
        )


async def _update_task_status(task_id: Optional[str], **kwargs):
    if not task_id:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(f"{TASK_SERVICE_URL}/task/{task_id}", json=kwargs)
    except Exception:
        pass


def _retry_backoff_delays(max_attempts: int = 3) -> list[float]:
    return [0.5 * (2**i) for i in range(max_attempts)]


@app.post("/embed-chunk")
async def embed_chunk(req: EmbedChunkRequest):
    await _update_task_status(
        req.task_id, status_code=1, status={"message": "running"}
    )
    # Retrieve canonical chunk payload
    # from S3 and upsert embedding by chunk_id.
    try:
        key = f"{req.workspace_id}/payload/{req.chunk_id}.json"
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        payload_bytes = obj["Body"].read()
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch chunk payload: {e}")
        await _update_task_status(
            req.task_id,
            status_code=3,
            status={"message": f"fetch chunk failed: {e}"},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch chunk payload: {e}"
        )

    try:
        text = payload.get("content", "")
        if not text.strip():
            raise ValueError("Empty content in payload")
        embedding = genai.embed_content(
            model=embedding_model,
            content=text,
            task_type="retrieval_document",
        )["embedding"]
    except Exception as e:
        print(f"Failed to generate chunk embedding: {e}")
        await _update_task_status(
            req.task_id,
            status_code=3,
            status={"message": f"embedding failed: {e}"},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate chunk embedding: {e}"
        )

    # Ensure version.embedding_model is populated by embedding-service
    version = payload.get("version") or {}
    if isinstance(version, dict):
        version["embedding_model"] = embedding_model
        payload["version"] = version

    # Upsert with retries, non-blocking
    for delay in _retry_backoff_delays(3):
        try:
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=payload.get("chunk_id"),
                        vector=embedding,
                        payload=payload,
                    )
                ],
                wait=False,
            )
            break
        except Exception as e:
            print(f"Failed to upsert chunk to Qdrant: {e}")
            last_err = e
            if delay > 0:
                await asyncio.sleep(delay)
    else:
        print(f"Failed to upsert chunk to Qdrant (2): {last_err}")
        await _update_task_status(
            req.task_id,
            status_code=3,
            status={"message": f"qdrant upsert failed: {last_err}"},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upsert chunk to Qdrant: {last_err}",
        )

    await _update_task_status(
        req.task_id,
        status_code=2,
        output={"chunk_id": payload.get("chunk_id")},
    )
    return {
        "success": True,
        "chunk_id": payload.get("chunk_id"),
        "workspace_id": req.workspace_id,
    }


@app.post("/embed/")
async def embed_stub():
    return {"accepted": True}


@app.get("/search/", response_model=list[SearchResult])
async def search(query: str, workspace_id: int, top_k: int = 5):
    # Add lightweight retry for transient errors
    last_err: Exception | None = None
    for delay in _retry_backoff_delays(3):
        try:
            query_embedding = genai.embed_content(
                model=embedding_model,
                content=query,
                task_type="retrieval_query",
            )["embedding"]
            search_results = qdrant_client.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="workspace_id",
                            match=models.MatchValue(value=workspace_id),
                        )
                    ]
                ),
                limit=top_k,
                with_payload=True,
                timeout=60,
            )
            results = [
                SearchResult(id=hit.id, payload=hit.payload, score=hit.score)
                for hit in search_results
            ]
            return results
        except Exception as e:
            print(f"Failed to search in Qdrant: {e}")
            last_err = e
            if delay > 0:
                await asyncio.sleep(delay)
    print(f"Failed to search in Qdrant (2): {last_err}")
    raise HTTPException(
        status_code=500, detail=f"Failed to search in Qdrant: {last_err}"
    )
