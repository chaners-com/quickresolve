#!/usr/bin/env python3
"""
Document Parsing Service
FastAPI service that parses PDF/DOC/DOCX to Markdown, uploads to S3,
and notifies the embedding service.
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

import boto3
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.parsers.registry import PARSER_REGISTRY

app = FastAPI(
    title="Document Parsing Service",
    description="Convert PDF/DOC/DOCX to Markdown and forward to embedding",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment and clients
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

ingestion_service_url = os.getenv(
    "INGESTION_SERVICE_URL", "http://ingestion-service:8000"
)
chunking_service_url = os.getenv(
    "CHUNKING_SERVICE_URL", "http://chunking-service:8006"
)

s3_client = None


@app.on_event("startup")
def on_startup():
    global s3_client
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
    # Ensure local parsed directory exists for testing purposes
    Path("parsed").mkdir(parents=True, exist_ok=True)


class ParseRequest(BaseModel):
    s3_key: str
    file_id: int
    workspace_id: int
    original_filename: str


class ParseResponse(BaseModel):
    success: bool
    message: str
    parsed_s3_key: Optional[str] = None
    original_size_bytes: int
    parsed_size_bytes: Optional[int] = None
    processing_time_seconds: float
    extracted_metadata: Optional[dict] = None


async def _update_file_status_async(file_id: int, status: int):
    """Asynchronously update file status in ingestion service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(
                f"{ingestion_service_url}/files/{file_id}/status",
                params={"status": status},
            )
    except Exception as e:
        print(f"Warning: failed to update file status for {file_id}: {e}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "document-parsing-service",
        "timestamp": int(time.time()),
    }


@app.get("/supported-types")
async def get_supported_types():
    return {
        "supported_formats": [
            {"extension": ".pdf", "description": "PDF documents"},
            {"extension": ".docx", "description": "Microsoft Word documents"},
            {
                "extension": ".doc",
                "description": "Microsoft Word legacy documents",
            },
            {
                "extension": ".md",
                "description": "Markdown files (pass-through)",
            },
        ]
    }


@app.post("/parse/", response_model=ParseResponse)
async def parse_document(request: ParseRequest):
    started = time.time()

    print(
        f"""Parsing document {request.s3_key}
         for file {request.file_id}
         in workspace {request.workspace_id}"""
    )

    # 1) Download original content from S3
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=request.s3_key)
        content_bytes: bytes = obj["Body"].read()
        original_size = len(content_bytes)
    except Exception as e:
        asyncio.create_task(_update_file_status_async(request.file_id, 3))
        raise HTTPException(
            status_code=500, detail=f"Failed to download from S3: {e}"
        )

    # 2) Parse to Markdown using registry based on original filename extension
    ext = request.original_filename.lower().strip().split(".")[-1]
    try:
        parser_fn = PARSER_REGISTRY.get(ext)
        if not parser_fn:
            asyncio.create_task(_update_file_status_async(request.file_id, 3))
            raise ValueError(f"Unsupported file type: .{ext}")
        parsed_md, extracted_metadata = parser_fn(content_bytes)
    except Exception as e:
        asyncio.create_task(_update_file_status_async(request.file_id, 3))
        raise HTTPException(
            status_code=500, detail=f"Failed to parse document: {e}"
        )

    parsed_bytes = parsed_md.encode("utf-8")

    # 3) Upload parsed markdown to S3 under {workspace_id}/parsed/{file_id}.md
    parsed_s3_key = f"{request.workspace_id}/parsed/{request.file_id}.md"

    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=parsed_s3_key,
            Body=parsed_bytes,
            ContentType="text/markdown",
        )
    except Exception as e:
        asyncio.create_task(_update_file_status_async(request.file_id, 3))
        raise HTTPException(
            status_code=500, detail=f"Failed to upload parsed file to S3: {e}"
        )

    # 5) Forward to chunking-service
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{chunking_service_url}/chunk",
                json={
                    "s3_key": parsed_s3_key,
                    "file_id": request.file_id,
                    "workspace_id": request.workspace_id,
                    "original_filename": request.original_filename,
                },
            )
    except Exception as e:
        asyncio.create_task(_update_file_status_async(request.file_id, 3))
        raise HTTPException(
            status_code=500, detail=f"Failed to notify chunking-service: {e}"
        )

    duration = time.time() - started

    return ParseResponse(
        success=True,
        message="Parsed and forwarded for embedding",
        parsed_s3_key=parsed_s3_key,
        original_size_bytes=original_size,
        parsed_size_bytes=len(parsed_bytes),
        processing_time_seconds=round(duration, 3),
        extracted_metadata=extracted_metadata or None,
    )


"""
Local testing:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
"""
