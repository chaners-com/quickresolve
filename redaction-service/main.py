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

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")


class RedactRequest(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: Optional[str] = None
    document_parser_version: Optional[str] = None
    task_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "redaction"}


async def _update_task_status(task_id: Optional[str], **kwargs):
    if not task_id:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(f"{TASK_SERVICE_URL}/task/{task_id}", json=kwargs)
    except Exception:
        pass


@app.post("/redact")
async def redact(req: RedactRequest):
    # Simulate redaction as a no-op and update own task when done
    await _update_task_status(
        req.task_id, status_code=1, status={"message": "Running redaction"}
    )

    # No-op: return same key; a real service would write
    # a redacted artifact and return its key
    await _update_task_status(
        req.task_id,
        status_code=2,
        status={"message": "Redaction completed"},
        output={
            "redacted_s3_key": req.s3_key,
            "file_id": req.file_id,
            "workspace_id": req.workspace_id,
        },
    )
    return {"accepted": True}
