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


# --- App and Clients Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
embedding_model = "models/embedding-001"

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
)
S3_BUCKET = os.getenv("S3_BUCKET")
QDRANT_COLLECTION_NAME = "file_embeddings"

INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "http://ingestion-service:8000"
)

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


async def _update_file_status_async(file_id: str, status: int):
    """Asynchronously update file status in ingestion service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(
                f"{INGESTION_SERVICE_URL}/files/{file_id}/status",
                params={"status": status},
            )
    except Exception as e:
        # Log but don't fail the embedding request
        print(
            f"""Warning: failed to update file status for
        {file_id}: {e}"""
        )


@app.post("/embed-chunk")
async def embed_chunk(req: EmbedChunkRequest):
    """Retrieve canonical chunk payload
    from S3 and upsert embedding by chunk_id."""
    try:
        key = f"{req.workspace_id}/payload/{req.chunk_id}.json"
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        payload_bytes = obj["Body"].read()
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch chunk payload: {e}")
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
        asyncio.create_task(
            _update_file_status_async(payload.get("file_id"), 3)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate chunk embedding: {e}"
        )

    # Ensure version.embedding_model is populated by embedding-service
    version = payload.get("version") or {}
    if isinstance(version, dict):
        version["embedding_model"] = embedding_model
        payload["version"] = version

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
            wait=True,
        )

    except Exception as e:
        print(f"Failed to upsert chunk to Qdrant: {e}")
        asyncio.create_task(
            _update_file_status_async(payload.get("file_id"), 3)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to upsert chunk to Qdrant: {e}"
        )

    return {
        "success": True,
        "chunk_id": payload.get("chunk_id"),
        "workspace_id": req.workspace_id,
    }


@app.get("/search/", response_model=list[SearchResult])
async def search(query: str, workspace_id: int, top_k: int = 5):
    """Embeds a query and searches for similar vectors in a specific \
workspace."""
    try:
        query_embedding = genai.embed_content(
            model=embedding_model, content=query, task_type="retrieval_query"
        )["embedding"]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate query embedding: {e}"
        )

    try:
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
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search in Qdrant: {e}"
        )

    results = [
        SearchResult(id=hit.id, payload=hit.payload, score=hit.score)
        for hit in search_results
    ]
    return results
