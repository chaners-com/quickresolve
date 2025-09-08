#!/usr/bin/env python3
"""
Chunking Service
Chunk markdown files using different chunking strategies.
"""

import asyncio
import json
import os
from typing import List, Optional

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.chunking_strategies.markdown_paragraph_sentence import (
    MarkdownParagraphSentenceChunkingStrategy,
)
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

# App setup
app = FastAPI(
    title="Chunking Service", description="Chunking with single strategy"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
SERVICE_BASE = os.getenv(
    "CHUNKING_SERVICE_URL", "http://chunking-service:8006"
)

# Clients
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)

# Task broker client/manager for consuming chunk tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/chunk",
    health_url=f"{SERVICE_BASE}/health",
    topic="chunk",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("CHUNK_MAX_CONCURRENT", "20"))
)


class ChunkRequest(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: Optional[str] = None
    document_parser_version: Optional[str] = None
    task_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chunking"}


@app.on_event("startup")
async def on_startup():
    await manager.start()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


async def _s3_get_text(bucket: str, key: str) -> str:
    obj = await asyncio.to_thread(s3.get_object, Bucket=bucket, Key=key)
    body = await asyncio.to_thread(obj["Body"].read)
    return body.decode("utf-8")


async def _s3_put_json(bucket: str, key: str, data_bytes: bytes) -> None:
    await asyncio.to_thread(
        s3.put_object,
        Bucket=bucket,
        Key=key,
        Body=data_bytes,
        ContentType="application/json",
    )


async def _process_chunk(req: ChunkRequest) -> dict:
    # 1) Download markdown from S3
    markdown_text = await _s3_get_text(S3_BUCKET, req.s3_key)

    # 2) Chunk using the strategy
    chunker = MarkdownParagraphSentenceChunkingStrategy()
    all_chunks = chunker.chunk(
        text=markdown_text,
        file_id=req.file_id,
        workspace_id=req.workspace_id,
        s3_key=req.s3_key,
        document_parser_version=req.document_parser_version,
    )

    # 3) Save chunk JSONs to S3
    put_tasks: List[asyncio.Task] = []
    for d in all_chunks:
        key = f"{req.workspace_id}/payload/{d['chunk_id']}.json"
        payload_bytes = json.dumps(d, ensure_ascii=False).encode("utf-8")
        put_tasks.append(_s3_put_json(S3_BUCKET, key, payload_bytes))
    if put_tasks:
        await asyncio.gather(*put_tasks)

    # Return output for ACK
    return {"chunks": all_chunks}


@app.post("/chunk")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        req = ChunkRequest(
            s3_key=payload["s3_key"],
            file_id=payload["file_id"],
            workspace_id=payload["workspace_id"],
            original_filename=payload.get("original_filename"),
            document_parser_version=payload.get("document_parser_version"),
            task_id=payload.get("task_id"),
        )

        return await _process_chunk(req)

    return await manager.execute_task(input, work)
