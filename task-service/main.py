"""
Task Service
Microservice‑based task processing enabling multiple services
(e.g., parsing, redaction, chunking, embedding) to pull tasks
from a shared store and execute them concurrently with dynamic,
resource‑aware limits.

- Multiple services pull tasks from a shared queue/store.
- Allows variable service resources (hardware and software).
- Dynamic concurrency per instance based
  on real‑time capacity (managed by the consumer).
- No double processing (exactly one active consumer per task).
- No busy polling or static caps; consumers explicitly declare readiness.
- Horizontal scalability: adding instances increases throughput.
- Pluggable broker abstraction (RabbitMQ/Redis Streams compatible).
- FIFO dispatch: tasks are assigned strictly in order of
  `scheduled_start_timestamp`.

- Each consumer instance manages its own concurrency and resources locally.
- The broker tracks a single “ready token” per consumer
  (`is_ready = true/false`).
- Flow:
  1) Consumer sets `is_ready = true` when it can accept a task.
  2) Broker atomically assigns exactly one queued task
     (the earliest `scheduled_start_timestamp`)
     to that consumer and flips `is_ready = false`.
  3) If the consumer still has capacity (e.g., it runs tasks concurrently),
     it immediately sets `is_ready = true` again to pull the next task,
     even before finishing current ones.
  4) Consumer ACK/NACKs tasks independently;
    readiness is driven solely by the consumer’s capacity.

Consumer (has free slot) ──> Broker: ready(is_ready=true)
Broker: assign oldest task ─> Consumer: task
Broker flips ready=false
Consumer starts task; if more free slots → ready(true) again
Consumer ACK/NACK when done (readiness is independent)

"""

import asyncio
import random
import time
from uuid import UUID

import httpx
from database import Consumer as DBConsumer
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

# Global handle to the main event loop for scheduling from threads
_MAIN_LOOP = None

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
    state: dict | None = None
    scheduled_start_timestamp: int | None = None


class ConsumerBody(BaseModel):
    endpoint_url: str
    health_url: str
    topic: str
    ready: bool = True


@app.on_event("startup")
async def on_startup():
    global _MAIN_LOOP
    _MAIN_LOOP = asyncio.get_running_loop()
    wait_for_db_and_create_tables()
    # Start async loops
    asyncio.create_task(_broker_assignment_loop())
    asyncio.create_task(_consumer_health_loop())


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
            "state": task.state,
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
    allowed_fields = {
        "status_code",
        "status",
        "progress_percentage",
        "output",
        "state",
        "scheduled_start_timestamp",
    }
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
        if "state" in payload:
            task.state = payload["state"]
        if "scheduled_start_timestamp" in payload:
            task.scheduled_start_timestamp = payload[
                "scheduled_start_timestamp"
            ]
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


@app.put("/consumer")
async def put_consumer(body: ConsumerBody):
    db = SessionLocal()
    try:
        rec = (
            db.query(DBConsumer)
            .filter(DBConsumer.endpoint_url == body.endpoint_url)
            .first()
        )
        if not rec:
            rec = DBConsumer(
                endpoint_url=body.endpoint_url,
                health_url=body.health_url,
                topic=body.topic,
                is_ready=1 if body.ready else 0,
            )
            db.add(rec)
        else:
            rec.health_url = body.health_url
            rec.topic = body.topic
            rec.is_ready = 1 if body.ready else 0
        db.commit()
        return {"ok": True}
    finally:
        db.close()


class DeleteConsumerBody(BaseModel):
    endpoint_url: str


@app.delete("/consumer")
async def delete_consumer(body: DeleteConsumerBody):
    db = SessionLocal()
    try:
        db.query(DBConsumer).filter(
            DBConsumer.endpoint_url == body.endpoint_url
        ).delete()
        db.commit()
        return {"ok": True}
    finally:
        db.close()


async def _broker_assignment_loop():
    while True:
        try:
            await asyncio.to_thread(_assign_once_fifo)
            await asyncio.sleep(0.2)
        except Exception:
            await asyncio.sleep(0.5)


def _schedule_coro(coro):
    try:
        loop = _MAIN_LOOP
        if loop is not None:
            loop.call_soon_threadsafe(asyncio.create_task, coro)
    except Exception:
        pass


def _assign_once_fifo():
    now = int(time.time())
    db = SessionLocal()
    try:
        # For each topic present in consumers,
        # match ready consumers to oldest tasks
        topics = [t[0] for t in db.query(DBConsumer.topic).distinct().all()]
        for topic in topics:
            # Batch of ready consumers (single slot)
            consumers = (
                db.query(DBConsumer)
                .filter(DBConsumer.topic == topic, DBConsumer.is_ready == 1)
                .order_by(DBConsumer.endpoint_url.asc())
                .limit(64)
                .all()
            )
            if not consumers:
                continue
            # Batch of oldest queued tasks (FIFO by scheduled_start_timestamp)
            tasks = (
                db.query(DBTask)
                .filter(DBTask.name == topic, DBTask.status_code == 0)
                .filter(DBTask.scheduled_start_timestamp <= now)
                .order_by(DBTask.scheduled_start_timestamp.asc())
                .limit(len(consumers))
                .all()
            )
            for consumer, task in zip(consumers, tasks):
                try:
                    # Transaction: lock consumer, lease task, flip token
                    c = (
                        db.query(DBConsumer)
                        .filter(
                            DBConsumer.endpoint_url == consumer.endpoint_url
                        )
                        .with_for_update()
                        .first()
                    )
                    if not c or c.is_ready != 1:
                        db.rollback()
                        continue
                    t = (
                        db.query(DBTask)
                        .filter(DBTask.id == task.id, DBTask.status_code == 0)
                        .first()
                    )
                    if not t:
                        db.rollback()
                        continue
                    # Lease task
                    t.status_code = 1
                    t.modification_timestamp = now
                    if t.start_timestamp is None:
                        t.start_timestamp = now
                    # Consume token
                    c.is_ready = 0
                    db.commit()
                    # Dispatch via registry (HTTP) asynchronously
                    # on the main loop
                    name_lc = (t.name or "").lower()
                    entry = REGISTRY.get(name_lc)
                    if entry and entry.get("type") == "http":
                        _schedule_coro(
                            _run_http_dispatch_worker_async(t.id, entry)
                        )
                    elif (
                        entry
                        and entry.get("type") == "internal"
                        and entry.get("handler") == "hello_world"
                    ):
                        _schedule_coro(_run_hello_world_worker_async(t.id))
                    else:
                        _mark_task_failed(t.id, {"error": "unknown task"})
                except Exception:
                    db.rollback()
                    continue
    finally:
        db.close()


async def _consumer_health_loop():
    while True:
        try:
            await asyncio.to_thread(_prune_unhealthy_consumers)
            await asyncio.sleep(5)
        except Exception:
            await asyncio.sleep(5)


def _prune_unhealthy_consumers():
    db = SessionLocal()
    try:
        items = db.query(DBConsumer).limit(200).all()
        for c in items:
            try:
                r = httpx.get(c.health_url, timeout=2.0)
                if r.status_code not in (200, 204):
                    db.query(DBConsumer).filter(
                        DBConsumer.endpoint_url == c.endpoint_url
                    ).delete()
            except Exception:
                db.query(DBConsumer).filter(
                    DBConsumer.endpoint_url == c.endpoint_url
                ).delete()
        db.commit()
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
            )
            return
        await asyncio.sleep(0.1)
        await asyncio.to_thread(
            _update_task_fields,
            task_id,
            progress_percentage=int(((i + 1) / len(target_text)) * 100),
        )

    await asyncio.to_thread(
        _update_task_fields,
        task_id,
        status_code=2,
        status={"message": "done"},
        output={"text": target_text},
    )


async def _run_http_dispatch_worker_async(task_id: UUID, entry: dict):
    db = SessionLocal()
    try:
        t = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not t:
            return
        url = entry.get("url")
        timeout = float(entry.get("timeout", 30.0))
        payload = {"task_id": str(t.id), **(t.input or {})}
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                await client.post(url, json=payload)
            except Exception:
                pass
    finally:
        db.close()


def _update_task_fields(task_id: UUID, **fields):
    db = SessionLocal()
    try:
        t = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not t:
            return
        now = int(time.time())
        prev_status = t.status_code
        if "status_code" in fields:
            t.status_code = fields["status_code"]
        if "status" in fields:
            t.status = fields["status"]
        if "progress_percentage" in fields:
            t.progress_percentage = fields["progress_percentage"]
        if "output" in fields:
            t.output = fields["output"]
        if "state" in fields:
            t.state = fields["state"]
        if "scheduled_start_timestamp" in fields:
            t.scheduled_start_timestamp = fields["scheduled_start_timestamp"]
        t.modification_timestamp = now
        if (
            prev_status == 0
            and t.status_code == 1
            and t.start_timestamp is None
        ):
            t.start_timestamp = now
        if t.status_code in (2, 3):
            t.end_timestamp = now
        if t.status_code == 2:
            t.progress_percentage = 100
        db.commit()
    finally:
        db.close()


def _mark_task_failed(task_id: UUID, status: dict | None = None):
    _update_task_fields(
        task_id, status_code=3, status=status or {"error": "failed"}
    )
