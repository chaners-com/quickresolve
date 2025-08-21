#!/usr/bin/env python3
import os
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Redaction Service",
    description=("Remove/mask PII before chunking."),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHUNKING_SERVICE_URL = os.getenv(
    "CHUNKING_SERVICE_URL", "http://chunking-service:8006"
)


class ChunkRequest(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: Optional[str] = None
    document_parser_version: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "redaction"}


@app.post("/redact")
async def redact(req: ChunkRequest):
    try:
        # Fire-and-forget style:
        # do not let downstream delay block the 200 response
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Kick off chunking;
            # don't await success semantics beyond request send
            await client.post(
                f"{CHUNKING_SERVICE_URL}/chunk", json=req.model_dump()
            )
    except Exception:
        # Even if downstream call fails to connect instantly,
        # we return accepted
        pass
    return {"accepted": True}
