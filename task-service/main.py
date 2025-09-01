"""
Task Service
Provides a general-purpose task queue and dispatcher
for internal workloads across services.
"""

import asyncio
import random
import time
from uuid import UUID

import httpx
from database import (
    SessionLocal,
)
from database import Task as DBTask
from database import (
    wait_for_db_and_create_tables,
)
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from registry import REGISTRY

app = FastAPI()

# CORS for frontend to poll task status
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:8090",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "task-service"}


# Pydantic models
class CreateTaskBody(BaseModel):
    name: str
    scheduled_start_timestamp: int | None = None
    input: dict
    workspace_id: int | None = None


class UpdateTaskBody(BaseModel):
    status_code: int | None = None
    status: dict | None = None
    progress_percentage: int | None = None
    output: dict | None = None


@app.on_event("startup")
async def on_startup():
    wait_for_db_and_create_tables()
    # Start async dispatcher loop
    asyncio.create_task(_dispatcher_loop_async())


# Dependency


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Minimal endpoints per spec
@app.post("/task", status_code=202)
async def create_task(body: CreateTaskBody, response: Response):
    now = int(time.time())
    db = SessionLocal()
    try:
        rec = DBTask(
            name=body.name,
            creation_timestamp=now,
            modification_timestamp=now,
            scheduled_start_timestamp=(
                body.scheduled_start_timestamp
                if body.scheduled_start_timestamp is not None
                else None
            ),
            status_code=0,
            status={},
            progress_percentage=0,
            input=body.input or {},
            output={},
            start_timestamp=None,
            end_timestamp=None,
            workspace_id=body.workspace_id or 0,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        response.headers["Location"] = f"/task/{rec.id}/status"
        return {"id": str(rec.id)}
    finally:
        db.close()


@app.get("/task/{task_id}")
async def get_task(task_id: UUID):
    db = SessionLocal()
    try:
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "id": str(task.id),
            "creation_timestamp": task.creation_timestamp,
            "modification_timestamp": task.modification_timestamp,
            "name": task.name,
            "scheduled_start_timestamp": task.scheduled_start_timestamp,
            "status_code": task.status_code,
            "status": task.status,
            "progress_percentage": task.progress_percentage,
            "input": task.input,
            "output": task.output,
            "start_timestamp": task.start_timestamp,
            "end_timestamp": task.end_timestamp,
            "workspace_id": task.workspace_id,
        }
    finally:
        db.close()


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: UUID):
    db = SessionLocal()
    try:
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "status_code": task.status_code,
            "status": task.status,
            "progress_percentage": task.progress_percentage,
            "start_timestamp": task.start_timestamp,
            "end_timestamp": task.end_timestamp,
        }
    finally:
        db.close()


@app.put("/task/{task_id}")
async def update_task(task_id: UUID, body: UpdateTaskBody):
    allowed_fields = {"status_code", "status", "progress_percentage", "output"}
    provided_fields = {
        k for k, v in body.model_dump(exclude_none=True).items()
    }
    if not provided_fields:
        raise HTTPException(
            status_code=400, detail="No updatable fields provided"
        )
    if not provided_fields.issubset(allowed_fields):
        invalid = sorted(list(provided_fields - allowed_fields))
        raise HTTPException(
            status_code=400,
            detail=f"Modification forbidden for fields: {', '.join(invalid)}",
        )

    db = SessionLocal()
    try:
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        now = int(time.time())
        prev_status = task.status_code

        # Apply updates
        payload = body.model_dump(exclude_none=True)
        if "status" in payload:
            task.status = payload["status"]
        if "progress_percentage" in payload:
            task.progress_percentage = payload["progress_percentage"]
        if "output" in payload:
            task.output = payload["output"]
        if "status_code" in payload:
            task.status_code = payload["status_code"]

        # Rules
        task.modification_timestamp = now
        if (
            prev_status == 0
            and task.status_code == 1
            and task.start_timestamp is None
        ):
            task.start_timestamp = now
        if task.status_code in (2, 3):
            task.end_timestamp = now
        if task.status_code == 2:
            task.progress_percentage = 100

        db.commit()
        db.refresh(task)
        return {
            "status_code": task.status_code,
            "status": task.status,
            "progress_percentage": task.progress_percentage,
            "start_timestamp": task.start_timestamp,
            "end_timestamp": task.end_timestamp,
        }
    finally:
        db.close()


async def _dispatcher_loop_async():
    while True:
        try:
            # Lease next eligible queued task (run sync DB in thread)
            task = await asyncio.to_thread(_lease_next_task)
            if task is None:
                await asyncio.sleep(2)
                continue
            name_lc = (task.name or "").lower()
            entry = REGISTRY.get(name_lc)
            if entry is None:
                await asyncio.to_thread(
                    _mark_task_failed, task.id, {"error": "unknown task"}
                )
                continue
            # Start appropriate worker based on registry
            if (
                entry.get("type") == "internal"
                and entry.get("handler") == "hello_world"
            ):
                asyncio.create_task(_run_hello_world_worker_async(task.id))
            elif entry.get("type") == "http":
                asyncio.create_task(
                    _run_http_dispatch_worker_async(task.id, entry)
                )
            else:
                await asyncio.to_thread(
                    _mark_task_failed,
                    task.id,
                    {"error": "invalid registry entry"},
                )
        except Exception:
            await asyncio.sleep(2)


def _lease_next_task():
    now = int(time.time())
    db = SessionLocal()
    try:
        q = (
            db.query(DBTask)
            .filter(DBTask.status_code == 0)
            .filter(
                (DBTask.scheduled_start_timestamp == None)
                | (DBTask.scheduled_start_timestamp <= now)
            )
            .order_by(DBTask.creation_timestamp.asc())
        )
        task = q.first()
        if not task:
            return None
        prev_status = task.status_code
        task.status_code = 1
        if prev_status == 0 and task.start_timestamp is None:
            task.start_timestamp = now
        task.modification_timestamp = now
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


async def _run_hello_world_worker_async(task_id: UUID):
    target_text = "Hello world"

    # Pick error step if provokeError
    def _snapshot():
        db = SessionLocal()
        try:
            task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if not task:
                return None
            return {"input": task.input}
        finally:
            db.close()

    snap = await asyncio.to_thread(_snapshot)
    if not snap:
        return
    provoke = False
    try:
        provoke = bool((snap.get("input") or {}).get("provokeError", False))
    except Exception:
        provoke = False
    error_index = None
    if provoke and len(target_text) > 1:
        error_index = random.randint(0, len(target_text) - 2)

    for i in range(len(target_text)):
        if error_index is not None and i == error_index:
            await asyncio.to_thread(
                _update_task_fields,
                task_id,
                status_code=3,
                status={"message": "failed", "step": i},
                output={"text": target_text[:i]},
                progress_percentage=max(
                    0, int((i / max(1, len(target_text))) * 100)
                ),
            )
            return

        # Update progress with next letter
        partial_text = target_text[: i + 1]
        progress = int(((i + 1) / len(target_text)) * 100)
        await asyncio.to_thread(
            _update_task_fields,
            task_id,
            status_code=1,
            status={"message": "running", "step": i + 1},
            output={"text": partial_text},
            progress_percentage=min(progress, 99),
        )
        await asyncio.sleep(2)

    # Mark completed
    await asyncio.to_thread(
        _update_task_fields,
        task_id,
        status_code=2,
        status={"message": "done", "step": len(target_text)},
        output={"text": target_text},
        progress_percentage=100,
    )


def _mark_task_failed(task_id: UUID, reason: dict):
    _update_task_fields(
        task_id,
        status_code=3,
        status={"message": "failed", **reason},
    )


def _update_task_fields(
    task_id: UUID,
    *,
    status_code: int | None = None,
    status: dict | None = None,
    progress_percentage: int | None = None,
    output: dict | None = None,
):
    db = SessionLocal()
    try:
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task:
            return
        now = int(time.time())
        prev_status = task.status_code
        if status is not None:
            task.status = status
        if progress_percentage is not None:
            task.progress_percentage = progress_percentage
        if output is not None:
            task.output = output
        if status_code is not None:
            task.status_code = status_code
        task.modification_timestamp = now
        if (
            prev_status == 0
            and task.status_code == 1
            and task.start_timestamp is None
        ):
            task.start_timestamp = now
        if task.status_code in (2, 3):
            task.end_timestamp = now
        if task.status_code == 2:
            task.progress_percentage = 100
        db.commit()
    finally:
        db.close()


async def _run_http_dispatch_worker_async(task_id: UUID, entry: dict):
    # Simple HTTP dispatch prototype;
    # assumes POST with JSON body combining task payload
    url = entry.get("url")
    method = (entry.get("method") or "POST").upper()
    timeout = entry.get("timeout") or 10

    def _snapshot():
        db = SessionLocal()
        try:
            task = db.query(DBTask).filter(DBTask.id == task_id).first()
            if not task:
                return None
            return {"input": task.input, "workspace_id": task.workspace_id}
        finally:
            db.close()

    snap = await asyncio.to_thread(_snapshot)
    if not snap:
        return

    try:
        await asyncio.to_thread(
            _update_task_fields,
            task_id,
            status_code=1,
            status={"message": "dispatched"},
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "POST":
                payload = {
                    **(snap.get("input") or {}),
                    "task_id": str(task_id),
                    "workspace_id": snap.get("workspace_id"),
                }
                resp = await client.post(url, json=payload)
            else:
                resp = await client.request(method, url)
        # If the downstream accepted the job,
        # keep task running.
        if resp.status_code not in (200, 202):
            await asyncio.to_thread(
                _mark_task_failed,
                task_id,
                {"error": f"dispatch failed: {resp.status_code}"},
            )
    except Exception as e:
        await asyncio.to_thread(
            _mark_task_failed, task_id, {"error": f"dispatch error: {e}"}
        )
