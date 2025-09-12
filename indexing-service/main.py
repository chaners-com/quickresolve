#!/usr/bin/env python3
"""
Indexing Service
Upserts embedded chunks into Qdrant.
"""

import asyncio
import json
import os
from typing import Optional

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager


class IndexChunkRequest(BaseModel):
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
    "INDEXING_SERVICE_URL", "http://indexing-service:8012"
)
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/index-chunk",
    health_url=f"{SERVICE_BASE}/health",
    topic="index",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("INDEX_MAX_CONCURRENT", "3"))
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "indexing-service"}


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
            import time

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


@app.post("/index-chunk")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        req = IndexChunkRequest(
            workspace_id=payload["workspace_id"],
            chunk_id=payload["chunk_id"],
            task_id=payload.get("task_id"),
        )
        # Retrieve payload metadata and vector from S3, then upsert
        payload_key = f"{req.workspace_id}/payloads/{req.chunk_id}.json"
        obj = s3.get_object(Bucket=S3_BUCKET, Key=payload_key)
        payload_bytes = obj["Body"].read()
        chunk_payload = json.loads(payload_bytes.decode("utf-8"))

        vec_key = f"{req.workspace_id}/vectors/{req.chunk_id}.vec"
        vec_obj = s3.get_object(Bucket=S3_BUCKET, Key=vec_key)
        vec_bytes = vec_obj["Body"].read()
        try:
            embedding = json.loads(vec_bytes.decode("utf-8"))
        except Exception:
            # If stored in another format in the future, handle accordingly
            raise ValueError("Invalid vector file content")

        if not isinstance(embedding, list) or not embedding:
            raise ValueError("Missing or invalid embedding vector")

        # Upsert to Qdrant
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

        return {
            "success": True,
            "chunk_id": chunk_payload.get("chunk_id"),
            "workspace_id": req.workspace_id,
        }

    return await manager.execute_task(input, work)
