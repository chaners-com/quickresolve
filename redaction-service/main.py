#!/usr/bin/env python3
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Redaction Service",
    description=(
        "Remove/mask PII before chunking."
    ),
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

CHUNKING_SERVICE_URL = os.getenv(
    "CHUNKING_SERVICE_URL", "http://chunking-service:8006"
)


class ChunkRequest(BaseModel):
    s3_key: str
    file_id: int
    workspace_id: int
    original_filename: Optional[str] = None
    document_parser_version: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "redaction"}


@app.post("/redact")
async def redact(req: ChunkRequest):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CHUNKING_SERVICE_URL}/chunk", json=req.model_dump()
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Redaction proxy failed: {e}"
        )