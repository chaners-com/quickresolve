#!/usr/bin/env python3
"""
Chunking Service
"""

import os
from datetime import datetime
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# App setup
app = FastAPI(title="Chunking Service", description="Pass-through chunking service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment
embedding_service_url = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:8001")
ingestion_service_url = os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8000")


class ChunkRequest(BaseModel):
    s3_key: str
    file_id: int
    workspace_id: int
    original_filename: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chunking"}


@app.post("/chunk")
async def chunk(req: ChunkRequest):
    try:
        # Pass-through to embedding service
        resp = requests.post(
            f"{embedding_service_url}/embed/",
            json={
                "s3_key": req.s3_key,
                "file_id": req.file_id,
                "workspace_id": req.workspace_id,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return {"success": True, "forwarded": True}
    except Exception as e:
        # Mark file as failed (status=3) in ingestion-service
        try:
            requests.put(
                f"{ingestion_service_url}/files/{req.file_id}/status",
                params={"status": 3},
                timeout=10,
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to forward to embedding: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006) 