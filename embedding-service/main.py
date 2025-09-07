#!/usr/bin/env python3
"""
Embedding Service
Embeds chunks and stores in Qdrant.
"""

import asyncio
import json
import os
import time
from typing import Optional, Union

import boto3
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager


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


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), timeout=60)
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

# Broker/Manager
SERVICE_BASE = os.getenv(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8001"
)
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/embed-chunk",
    health_url=f"{SERVICE_BASE}/health",
    topic="embed",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("EMBED_MAX_CONCURRENT", "4"))
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "embedding-service"}


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

    # Advertise readiness for one task slot
    asyncio.get_event_loop().create_task(manager.start())


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


def _retry_backoff_delays(max_attempts: int = 3) -> list[float]:
    return [0.5 * (2**i) for i in range(max_attempts)]


@app.post("/embed-chunk")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        req = EmbedChunkRequest(
            workspace_id=payload["workspace_id"],
            chunk_id=payload["chunk_id"],
            task_id=payload.get("task_id"),
        )
        # Retrieve canonical chunk payload
        # from S3 and upsert embedding by chunk_id.
        key = f"{req.workspace_id}/payload/{req.chunk_id}.json"
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        payload_bytes = obj["Body"].read()
        chunk_payload = json.loads(payload_bytes.decode("utf-8"))

        text = chunk_payload.get("content", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty content in payload")

        embedding = genai.embed_content(
            model=embedding_model,
            content=text,
            task_type="retrieval_document",
        )["embedding"]

        # Ensure version.embedding_model is populated by embedding-service
        version = chunk_payload.get("version") or {}
        if isinstance(version, dict):
            version["embedding_model"] = embedding_model
            chunk_payload["version"] = version

        # Upsert with retries
        last_err: Exception | None = None
        for delay in _retry_backoff_delays(3):
            try:
                qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=[
                        models.PointStruct(
                            id=chunk_payload.get("chunk_id"),
                            vector=embedding,
                            payload=chunk_payload,
                        )
                    ],
                    wait=False,
                )
                break
            except Exception as e:
                last_err = e
                if delay > 0:
                    await asyncio.sleep(delay)
        else:
            raise RuntimeError(f"Failed to upsert chunk to Qdrant: {last_err}")

        return {
            "success": True,
            "chunk_id": chunk_payload.get("chunk_id"),
            "workspace_id": req.workspace_id,
        }

    return await manager.execute_task(input, work)


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
            last_err = e
            if delay > 0:
                await asyncio.sleep(delay)
    raise RuntimeError(f"Failed to search in Qdrant: {last_err}")
