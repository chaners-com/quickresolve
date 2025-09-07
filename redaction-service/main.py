#!/usr/bin/env python3
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

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

SERVICE_BASE = os.getenv("REDACTION_SERVICE_URL", "http://redaction-service:8007")


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


# Task broker client/manager for consuming redact tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/redact",
    health_url=f"{SERVICE_BASE}/health",
    topic="redact",
)
manager = TaskManager(broker, max_concurrent=int(os.getenv("REDACT_MAX_CONCURRENT", "2")))


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


async def _process_redaction(req: RedactRequest) -> dict:
    # No-op: return same key; a real service would write a redacted artifact
    return {
        "redacted_s3_key": req.s3_key,
        "file_id": req.file_id,
        "workspace_id": req.workspace_id,
    }


@app.post("/redact")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        req = RedactRequest(
            s3_key=payload["s3_key"],
            file_id=payload["file_id"],
            workspace_id=payload["workspace_id"],
            original_filename=payload.get("original_filename"),
            document_parser_version=payload.get("document_parser_version"),
            task_id=payload.get("task_id"),
        )
        # Let exceptions bubble to TaskManager so it FAILs and frees slot
        return await _process_redaction(req)

    return await manager.execute_task(input, work)
