"""
Task Service
Provides a general-purpose task queue and dispatcher
for internal workloads across services.
"""

import os
import time
from uuid import UUID
from fastapi import FastAPI, HTTPException, Response, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    Base,
    SessionLocal,
    Task as DBTask,
    engine,
    wait_for_db_and_create_tables,
)

app = FastAPI()


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
def on_startup():
    wait_for_db_and_create_tables()


# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Minimal endpoints skeleton per spec
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
    provided_fields = {k for k, v in body.model_dump(exclude_none=True).items()}
    if not provided_fields:
        raise HTTPException(status_code=400, detail="No updatable fields provided")
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
        if prev_status == 0 and task.status_code == 1 and task.start_timestamp is None:
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