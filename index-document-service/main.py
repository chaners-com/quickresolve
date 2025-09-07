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
SERVICE_BASE = os.getenv("INDEX_DOCUMENT_SERVICE_URL", "http://index-document-service:8011")

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


async def _update_task_status(task_id: Optional[str], **kwargs):
    if not task_id:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(f"{TASK_SERVICE_URL}/task/{task_id}", json=kwargs)
    except Exception:
        pass


# Global cap for concurrent embed tasks across
# all pipelines (per service instance)
try:
    MAX_EMBEDDING_CONCURRENT_TASKS = max(
        1, int(os.getenv("MAX_EMBEDDING_CONCURRENT_TASKS", "4") or "4")
    )
except ValueError:
    MAX_EMBEDDING_CONCURRENT_TASKS = 4
EMBED_SEM = asyncio.Semaphore(MAX_EMBEDDING_CONCURRENT_TASKS)

# Task broker client/manager for consuming index-document tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/",
    health_url=f"{SERVICE_BASE}/health",
    topic="index-document",
)
manager = TaskManager(broker, max_concurrent=int(os.getenv("INDEX_DOC_MAX_CONCURRENT", "2")))


@app.on_event("startup")
async def on_startup():
    # Initial readiness is advertised by TaskManager in __init__
    pass


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "index-document-service"}


@app.post("/")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        # payload contains task_id + original input fields
        definition = PipelineDefinition(
            description="Index document pipeline",
            s3_key=payload["s3_key"],
            file_id=payload["file_id"],
            workspace_id=payload["workspace_id"],
            original_filename=payload["original_filename"],
            steps=[PipelineStep(name=s["name"]) for s in payload.get("steps", [])],
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

    async with httpx.AsyncClient(timeout=30) as client:
        prev_output: Dict[str, Any] | None = None
        for step in definition.steps:
            name = (step.name or "").strip().lower()
            if name == "embed":
                # Fan-out per chunk and return when done
                chunks = (prev_output or {}).get("chunks") or []
                if not isinstance(chunks, list):
                    chunks = []
                await _run_embed_fanout(client, chunks, workspace_id)
                return

            # Regular single task step
            tries = 0
            while tries < 3:
                tries += 1
                try:
                    prev_output = await _create_and_wait_task(
                        client=client,
                        name=name,
                        workspace_id=workspace_id,
                        root_ctx=root_ctx,
                        prev_output=prev_output,
                    )
                    break
                except Exception:
                    if tries >= 3:
                        # Propagate failure to TaskManager
                        raise
                    await asyncio.sleep(2 * tries)
        # Completed all steps without embed
        return


async def _create_and_wait_task(
    *,
    client: httpx.AsyncClient,
    name: str,
    workspace_id: int,
    root_ctx: Dict[str, Any],
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
    elif name == "redact":
        step_input = {
            "s3_key": (prev_output or {}).get("parsed_s3_key")
            or root_ctx.get("s3_key"),
            "file_id": root_ctx["file_id"],
            "workspace_id": workspace_id,
            "original_filename": root_ctx["original_filename"],
            "document_parser_version": (prev_output or {}).get(
                "document_parser_version"
            ),
        }
    elif name == "chunk":
        step_input = {
            "s3_key": (prev_output or {}).get("redacted_s3_key")
            or (prev_output or {}).get("parsed_s3_key")
            or root_ctx.get("s3_key"),
            "file_id": root_ctx["file_id"],
            "workspace_id": workspace_id,
            "original_filename": root_ctx["original_filename"],
            "document_parser_version": (prev_output or {}).get(
                "document_parser_version"
            ),
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


async def _run_embed_fanout(
    client: httpx.AsyncClient, chunks: List[Dict[str, Any]], workspace_id: int
):
    # Run multiple embed tasks and wait
    # for all to complete (globally capped by EMBED_SEM)
    sem = EMBED_SEM

    async def _one(chunk: Dict[str, Any]):
        async with sem:
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
