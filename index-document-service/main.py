"""
Index Document Service
AKA "Indexer"
This service orchestrates the indexing pipeline for a document.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")
SERVICE_BASE = os.getenv(
    "INDEX_DOCUMENT_SERVICE_URL", "http://index-document-service:8011"
)

app = FastAPI()


class PipelineStep(BaseModel):
    name: str


class PipelineDefinition(BaseModel):
    description: Optional[str] = None
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: str
    steps: List[PipelineStep]
    task_id: Optional[str] = None


# Task broker client/manager for consuming index-document tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/",
    health_url=f"{SERVICE_BASE}/health",
    topic="index-document",
)
manager = TaskManager(
    broker,
    max_concurrent=max(
        1, int(os.getenv("INDEX_DOC_MAX_CONCURRENT", "20") or "20")
    ),
)


@app.on_event("startup")
async def on_startup():
    await manager.start()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "index-document-service"}


def _canonicalize_steps(steps: List[PipelineStep]) -> List[PipelineStep]:
    """Return steps ordered as:
    parse-document -> chunk -> redact -> embed -> index (others last)."""
    priority = {
        "parse-document": 0,
        "chunk": 1,
        "redact": 2,
        "embed": 3,
        "index": 4,
    }
    return sorted(
        steps, key=lambda s: priority.get((s.name or "").strip().lower(), 5)
    )


@app.post("/")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        definition = PipelineDefinition(
            description="Index document pipeline",
            s3_key=payload["s3_key"],
            file_id=payload["file_id"],
            workspace_id=payload["workspace_id"],
            original_filename=payload["original_filename"],
            steps=[
                PipelineStep(name=s["name"]) for s in payload.get("steps", [])
            ],
            task_id=payload.get("task_id"),
        )
        # Let exceptions bubble to TaskManager so it FAILs and frees slot
        await _run_pipeline(definition)
        return {}

    return await manager.execute_task(input, work)


async def _run_pipeline(definition: PipelineDefinition):
    workspace_id = definition.workspace_id
    root_ctx: Dict[str, Any] = {
        "s3_key": definition.s3_key,
        "file_id": definition.file_id,
        "workspace_id": workspace_id,
        "original_filename": definition.original_filename,
    }
    # Artifact context persists outputs needed by later steps
    # regardless of order
    artifact_ctx: Dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        prev_output: Dict[str, Any] | None = None
        ordered_steps = _canonicalize_steps(definition.steps)
        for step in ordered_steps:
            name = (step.name or "").strip().lower()

            # Redaction is a fanout over chunks
            if name == "redact":
                chunks = (prev_output or {}).get("chunks") or artifact_ctx.get(
                    "chunks", []
                )
                if not isinstance(chunks, list):
                    chunks = []
                await _run_redact_fanout(client, chunks, workspace_id)
                # keep prev_output pointing to chunks for next steps
                prev_output = {"chunks": chunks}
                continue

            # Embed is a fanout over redaction
            if name == "embed":
                chunks = (prev_output or {}).get("chunks") or artifact_ctx.get(
                    "chunks", []
                )
                if not isinstance(chunks, list):
                    chunks = []
                await _run_embed_fanout(client, chunks, workspace_id)
                # keep prev_output pointing to chunks for next steps
                prev_output = {"chunks": chunks}
                continue

            # Index is a fanout over chunks
            if name == "index":
                chunks = (prev_output or {}).get("chunks") or artifact_ctx.get(
                    "chunks", []
                )
                if not isinstance(chunks, list):
                    chunks = []
                await _run_index_fanout(client, chunks, workspace_id)
                continue

            # Regular single task step with simple retries
            tries = 0
            while tries < 3:
                tries += 1
                try:
                    prev_output = await _create_and_wait_task(
                        client=client,
                        name=name,
                        workspace_id=workspace_id,
                        root_ctx=root_ctx,
                        artifact_ctx=artifact_ctx,
                        prev_output=prev_output,
                    )
                    # Persist key artifacts for later steps
                    if name == "parse-document":
                        if isinstance(prev_output, dict):
                            if prev_output.get("parsed_s3_key"):
                                artifact_ctx["parsed_s3_key"] = prev_output[
                                    "parsed_s3_key"
                                ]
                            if prev_output.get("document_parser_version"):
                                artifact_ctx["document_parser_version"] = (
                                    prev_output["document_parser_version"]
                                )
                    elif name == "chunk":
                        if isinstance(prev_output, dict) and prev_output.get(
                            "chunks"
                        ):
                            artifact_ctx["chunks"] = prev_output["chunks"]
                    break
                except Exception:
                    if tries >= 3:
                        # Propagate failure to TaskManager
                        raise
                    await asyncio.sleep(2 * tries)
    # Completed all steps without embed/index
    return


async def _create_and_wait_task(
    *,
    client: httpx.AsyncClient,
    name: str,
    workspace_id: int,
    root_ctx: Dict[str, Any],
    artifact_ctx: Dict[str, Any],
    prev_output: Dict[str, Any] | None,
) -> Dict[str, Any]:
    # Build task input depending on step
    step_input: Dict[str, Any]
    if name == "parse-document":
        step_input = {
            "s3_key": root_ctx["s3_key"],
            "file_id": root_ctx["file_id"],
            "workspace_id": workspace_id,
            "original_filename": root_ctx["original_filename"],
        }
    elif name == "chunk":
        step_input = {
            # Use redacted if available, else parsed, else original
            "s3_key": artifact_ctx.get("redacted_s3_key")
            or (prev_output or {}).get("redacted_s3_key")
            or artifact_ctx.get("parsed_s3_key")
            or (prev_output or {}).get("parsed_s3_key")
            or root_ctx.get("s3_key"),
            "file_id": root_ctx["file_id"],
            "workspace_id": workspace_id,
            "original_filename": root_ctx["original_filename"],
            "document_parser_version": artifact_ctx.get(
                "document_parser_version"
            )
            or (prev_output or {}).get("document_parser_version"),
        }
    else:
        # Default passthrough if an unknown step shows up
        step_input = {
            "context": (prev_output or {}),
            "workspace_id": workspace_id,
        }

    r = await client.post(
        f"{TASK_SERVICE_URL}/task",
        json={
            "name": name,
            "input": step_input,
            "workspace_id": workspace_id,
        },
    )
    r.raise_for_status()
    task_id = r.json().get("id")
    if not task_id:
        raise RuntimeError("Task creation did not return id")

    # Poll until done or failed
    while True:
        await asyncio.sleep(1)
        s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
        if s.status_code != 200:
            continue
        data = s.json()
        code = int(data.get("status_code") or 0)
        if code == 2:
            return data.get("output") or {}
        if code == 3:
            raise RuntimeError(f"Task {name} {task_id} failed")


async def _run_redact_fanout(
    client: httpx.AsyncClient, chunks: List[Dict[str, Any]], workspace_id: int
):
    # Run multiple redact tasks and wait for all to complete
    async def _one(chunk: Dict[str, Any]):
        body = {
            "name": "redact",
            "input": {
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "workspace_id": workspace_id,
            },
            "workspace_id": workspace_id,
        }
        r = await client.post(f"{TASK_SERVICE_URL}/task", json=body)
        r.raise_for_status()
        task_id = r.json().get("id")
        if not task_id:
            raise RuntimeError("Task creation did not return id")
        while True:
            await asyncio.sleep(1)
            s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
            if s.status_code != 200:
                continue
            data = s.json()
            code = int(data.get("status_code") or 0)
            if code == 2:
                return
            if code == 3:
                raise RuntimeError("redact failed")

    tasks = [asyncio.create_task(_one(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)


async def _run_embed_fanout(
    client: httpx.AsyncClient, chunks: List[Dict[str, Any]], workspace_id: int
):
    # Run multiple embed tasks and wait for all to complete
    async def _one(chunk: Dict[str, Any]):
        body = {
            "name": "embed",
            "input": {
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "workspace_id": workspace_id,
            },
            "workspace_id": workspace_id,
        }
        r = await client.post(f"{TASK_SERVICE_URL}/task", json=body)
        r.raise_for_status()
        task_id = r.json().get("id")
        if not task_id:
            raise RuntimeError("Task creation did not return id")
        while True:
            await asyncio.sleep(1)
            s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
            if s.status_code != 200:
                continue
            data = s.json()
            code = int(data.get("status_code") or 0)
            if code == 2:
                return
            if code == 3:
                raise RuntimeError("embed failed")

    tasks = [asyncio.create_task(_one(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)


async def _run_index_fanout(
    client: httpx.AsyncClient, chunks: List[Dict[str, Any]], workspace_id: int
):
    # Create multiple index tasks and wait for all to complete
    async def _one(chunk: Dict[str, Any]):
        body = {
            "name": "index",
            "input": {
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "workspace_id": workspace_id,
            },
            "workspace_id": workspace_id,
        }
        r = await client.post(f"{TASK_SERVICE_URL}/task", json=body)
        r.raise_for_status()
        task_id = r.json().get("id")
        if not task_id:
            raise RuntimeError("Task creation did not return id")
        while True:
            await asyncio.sleep(1)
            s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
            if s.status_code != 200:
                continue
            data = s.json()
            code = int(data.get("status_code") or 0)
            if code == 2:
                return
            if code == 3:
                raise RuntimeError("index failed")

    tasks = [asyncio.create_task(_one(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)
