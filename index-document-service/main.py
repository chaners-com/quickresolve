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

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")

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


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "index-document-service"}


@app.post("/")
async def run(definition: PipelineDefinition):
    # Fire-and-forget orchestration
    asyncio.create_task(_run_pipeline(definition))
    return {}


async def _run_pipeline(definition: PipelineDefinition):
    # Mark this index-document task as running
    await _update_task_status(
        definition.task_id, status_code=1, status={"message": "running"}
    )

    workspace_id = definition.workspace_id
    root_ctx: Dict[str, Any] = {
        "s3_key": definition.s3_key,
        "file_id": definition.file_id,
        "workspace_id": workspace_id,
        "original_filename": definition.original_filename,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            prev_output: Dict[str, Any] | None = None
            for step in definition.steps:
                name = (step.name or "").strip().lower()
                if name == "embed":
                    # Fan-out per chunk; then finalize this index-document task
                    chunks = (prev_output or {}).get("chunks") or []
                    if not isinstance(chunks, list):
                        chunks = []
                    try:
                        await _run_embed_fanout(client, chunks, workspace_id)
                        await _update_task_status(
                            definition.task_id,
                            status_code=2,
                            status={"message": "Document indexing completed"},
                        )
                        return
                    except Exception:
                        await _update_task_status(
                            definition.task_id,
                            status_code=3,
                            status={"message": "Document embedding failed"},
                        )
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
                            raise
                        await asyncio.sleep(2 * tries)

        # All steps done and no embed step was present; mark completed
        await _update_task_status(
            definition.task_id,
            status_code=2,
            status={"message": "Document indexed successfully"},
        )
        return
    except Exception:
        # Failed at some step
        await _update_task_status(
            definition.task_id,
            status_code=3,
            status={"message": "Document indexing failed"},
        )
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


ASYNC_LIMIT = 10


async def _run_embed_fanout(
    client: httpx.AsyncClient, chunks: List[Dict[str, Any]], workspace_id: int
):
    # Run multiple embed tasks and wait for all to complete
    sem = asyncio.Semaphore(ASYNC_LIMIT)

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
