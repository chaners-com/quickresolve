#!/usr/bin/env python3
"""
Embedding Service
Embeds chunks and writes vector files to S3 under vectors/.
Does not store vectors in payload JSON.
"""

import asyncio
import json
import os
from typing import Optional, Union

import boto3
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    broker, max_concurrent=int(os.getenv("EMBED_MAX_CONCURRENT", "20"))
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "embedding-service"}


@app.on_event("startup")
def startup_event():
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
        # Retrieve canonical chunk payload from S3
        payload_key = f"{req.workspace_id}/payloads/{req.chunk_id}.json"
        obj = s3.get_object(Bucket=S3_BUCKET, Key=payload_key)
        payload_bytes = obj["Body"].read()
        chunk_payload = json.loads(payload_bytes.decode("utf-8"))

        text = chunk_payload.get("content", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty content in payload")

        vec = genai.embed_content(
            model=embedding_model,
            content=text,
            task_type="retrieval_document",
        )["embedding"]

        # Ensure version.embedding_model
        # is populated (in payload metadata only)
        version = chunk_payload.get("version") or {}
        if isinstance(version, dict):
            version["embedding_model"] = embedding_model
            chunk_payload["version"] = version

        # Persist payload (without vector) to keep metadata updated
        body = json.dumps(chunk_payload).encode("utf-8")
        last_err: Exception | None = None
        for delay in _retry_backoff_delays(3):
            try:
                s3.put_object(Bucket=S3_BUCKET, Key=payload_key, Body=body)
                break
            except Exception as e:
                last_err = e
                if delay > 0:
                    await asyncio.sleep(delay)
        else:
            raise RuntimeError(
                f"Failed to persist payload metadata to S3: {last_err}"
            )

        # Write vector file separately under
        # vectors/<chunk_id>.vec as JSON array
        vec_key = f"{req.workspace_id}/vectors/{req.chunk_id}.vec"
        vec_body = json.dumps(vec).encode("utf-8")
        last_err = None
        for delay in _retry_backoff_delays(3):
            try:
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=vec_key,
                    Body=vec_body,
                    ContentType="application/octet-stream",
                )
                break
            except Exception as e:
                last_err = e
                if delay > 0:
                    await asyncio.sleep(delay)
        else:
            raise RuntimeError(f"Failed to persist vector to S3: {last_err}")

        return {
            "success": True,
            "chunk_id": chunk_payload.get("chunk_id"),
            "workspace_id": req.workspace_id,
        }

    return await manager.execute_task(input, work)
