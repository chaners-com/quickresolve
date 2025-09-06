#!/usr/bin/env python3

"""
Redaction service.

Redaction operates on chunks to maximize safety and parallelism:
"""

import json
import os
from typing import Optional

import boto3
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.redaction_strategies import (
    PatternBasedRedactionStrategy,
    RedactionConfig,
)

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

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")

# S3 configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3 = None


@app.on_event("startup")
def on_startup():
    global s3
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


class RedactRequest(BaseModel):
    workspace_id: int
    chunk_id: str
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
    print(f"Redacting chunk {req.chunk_id} for workspace {req.workspace_id}")
    await _update_task_status(
        req.task_id, status_code=1, status={"message": "Running redaction"}
    )

    # 1) Fetch canonical payload from S3
    key = f"{req.workspace_id}/payload/{req.chunk_id}.json"
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        payload_bytes = obj["Body"].read()
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Fetch payload failed: {e}")
        await _update_task_status(
            req.task_id,
            status_code=3,
            status={"message": f"Fetch payload failed: {e}"},
        )
        return {"accepted": False}

    # 2) Apply pattern-based strategy
    text = payload.get("content")
    if text is None:
        text = ""
    else:
        text = str(text)
    file_id_value = payload.get("file_id")
    file_id = str(file_id_value) if file_id_value is not None else ""

    # Load service secret and suffix bytes
    secret_raw = os.getenv("HMAC_KEY_DEFAULT", "")
    suffix_bytes = 1
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
    if isinstance(version, dict):
        try:
            version["redaction_strategy"] = getattr(
                PatternBasedRedactionStrategy, "VERSION", "pattern-based-1"
            )
            payload["version"] = version
        except Exception:
            pass

    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        await _update_task_status(
            req.task_id,
            status_code=3,
            status={"message": f"Write payload failed: {e}"},
        )
        return {"accepted": False}

    # 4) Mark done with metrics in output
    await _update_task_status(
        req.task_id,
        status_code=2,
        status={"message": "Redaction completed"},
        output={
            "chunk_id": req.chunk_id,
            "workspace_id": req.workspace_id,
            "metrics": result.metrics,
        },
    )
    return {"accepted": True}
