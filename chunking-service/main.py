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
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.chunkers.markdown_paragraph_sentence import (
    MarkdownParagraphSentenceChunker,
)

# App setup
app = FastAPI(
    title="Chunking Service", description="Chunking with single strategy"
)

# Get CORS origins from environment variable, with fallback to localhost
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost,http://localhost:8080")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment
EMBEDDING_SERVICE_URL = os.getenv(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8001"
)
INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "http://ingestion-service:8000"
)
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


class ChunkRequest(BaseModel):
    s3_key: str
    file_id: int
    workspace_id: int
    original_filename: Optional[str] = None
    document_parser_version: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chunking"}


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


@app.post("/chunk")
async def chunk(req: ChunkRequest):
    try:
        # 1) Download markdown from S3
        markdown_text = await _s3_get_text(S3_BUCKET, req.s3_key)

        print(f"Markdown text: {markdown_text}")

        # 2) Chunk using the Phase 1 strategy via chunker lib
        chunker = MarkdownParagraphSentenceChunker()
        all_chunks = chunker.chunk(
            text=markdown_text,
            file_id=req.file_id,
            workspace_id=req.workspace_id,
            s3_key=req.s3_key,
            document_parser_version=req.document_parser_version,
        )

        print(f"All chunks: {all_chunks}")

        # 3) Save chunk JSONs to S3
        put_tasks: List[asyncio.Task] = []
        for d in all_chunks:
            key = f"{req.workspace_id}/payload/{d['chunk_id']}.json"
            payload_bytes = json.dumps(d, ensure_ascii=False).encode("utf-8")
            put_tasks.append(_s3_put_json(S3_BUCKET, key, payload_bytes))
        if put_tasks:
            await asyncio.gather(*put_tasks)

        # 4) Forward each chunk to embedding-service using /embed-chunk
        async with httpx.AsyncClient(timeout=30.0) as httpx_client:
            tasks = [
                httpx_client.post(
                    f"{EMBEDDING_SERVICE_URL}/embed-chunk",
                    json={
                        "workspace_id": req.workspace_id,
                        "chunk_id": chunk["chunk_id"],
                    },
                )
                for chunk in all_chunks
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            # Raise if any failed
            for resp in responses:
                if isinstance(resp, Exception):
                    raise resp
                resp.raise_for_status()

        return {"success": True, "chunks": len(all_chunks)}
    except Exception as e:
        # Best-effort: mark status=3 (error) asynchronously
        try:
            async with httpx.AsyncClient(timeout=10.0) as httpx_client:
                await httpx_client.put(
                    f"{INGESTION_SERVICE_URL}/files/{req.file_id}/status",
                    params={"status": 3},
                )
        except Exception:
            pass
        print(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chunking failed: {e}")
