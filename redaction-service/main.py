#!/usr/bin/env python3

"""
Redaction service.

Redaction perates on chunks to maximize safety and parallelism.

Mask PII types with deterministic rules (always enabled in v1):
  - Emails in text and in URLs (including `mailto:`)
  - IPv4 and IPv6 (validated)
  - Credit card candidates (Luhn-validated)
  - IBAN (mod-97 check)
  - E.164 phones (conservative pattern)
Deterministic per-document suffix:
  - Use HMAC-SHA256 with a per-document key derived as
    `HMAC(service_secret, file_id)`; token suffix
    for each matched value is `HMAC(per_doc_key, value)[:suffix_bytes]`
    in hex. This guarantees consistent suffixes for the same value within
    a document even when chunks are processed in parallel
    and across instances, without in-memory maps.
  - If later we need cross-file stability within a workspace,
    derive `per_workspace_key = HMAC(service_secret, workspace_id)`
    and switch derivation accordingly. For now, per-document only.
Produce output Markdown preserving structure.

"""

import json
import os
from typing import Optional

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.redaction_strategies import (
    PatternBasedRedactionStrategy,
    RedactionConfig,
)
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

app = FastAPI(
    title="Redaction Service",
    description=(
        "Chunk-level redaction: accepts chunk_id/workspace_id, "
        "updates payload in S3 in place."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICE_BASE = os.getenv(
    "REDACTION_SERVICE_URL", "http://redaction-service:8007"
)

# S3 configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3 = None


@app.on_event("startup")
async def on_startup():
    global s3
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
    await manager.start()


class RedactRequest(BaseModel):
    workspace_id: int
    chunk_id: str
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
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("REDACT_MAX_CONCURRENT", "20"))
)


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


async def _process_redaction(req: RedactRequest) -> dict:
    # 1) Fetch canonical payload from S3
    key = f"{req.workspace_id}/payload/{req.chunk_id}.json"
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    payload_bytes = obj["Body"].read()
    payload = json.loads(payload_bytes.decode("utf-8"))

    # 2) Apply pattern-based strategy
    text = payload.get("content")
    if text is None:
        text = ""
    elif not isinstance(text, str):
        text = str(text)
    file_id_value = payload.get("file_id")
    file_id = str(file_id_value) if file_id_value is not None else ""

    # Load service secret and suffix bytes
    secret_raw = os.getenv("HMAC_KEY_DEFAULT", "")
    try:
        suffix_bytes = max(
            0, int(os.getenv("REDACTION_SUFFIX_BYTES", "1") or "1")
        )
    except Exception:
        suffix_bytes = 1
    cfg = RedactionConfig(
        suffix_bytes=suffix_bytes,
        file_id=file_id,
        workspace_id=req.workspace_id,
        service_secret=(secret_raw.encode("utf-8") if secret_raw else None),
    )
    strategy = PatternBasedRedactionStrategy()
    result = strategy.redact(text, cfg)

    # 3) Update payload in place and write back to S3
    payload["content"] = result.text
    version = payload.get("version") or {}
    if not isinstance(version, dict):
        version = {}
    version["redaction_strategy"] = getattr(
        PatternBasedRedactionStrategy, "VERSION", "pattern-based-1"
    )
    payload["version"] = version

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    # Return output; TaskManager will ACK with this payload
    return {
        "chunk_id": req.chunk_id,
        "workspace_id": req.workspace_id,
        "metrics": result.metrics,
    }


@app.post("/redact")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        req = RedactRequest(
            workspace_id=payload["workspace_id"],
            chunk_id=payload["chunk_id"],
            task_id=payload.get("task_id"),
        )
        return await _process_redaction(req)

    return await manager.execute_task(input, work)
