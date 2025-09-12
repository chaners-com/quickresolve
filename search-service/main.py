#!/usr/bin/env python3
"""
Search Service
Provides semantic search over Qdrant using Gemini embeddings for queries.
"""

import asyncio
import os
from typing import Optional, Union

import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse


class SearchResult(BaseModel):
    id: Union[str, int]
    payload: Optional[dict] = None
    score: float


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), timeout=60)
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
embedding_model = "models/embedding-001"
QDRANT_COLLECTION_NAME = "file_embeddings"


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "search-service"}


def _retry_backoff_delays(max_attempts: int = 3) -> list[float]:
    return [0.5 * (2**i) for i in range(max_attempts)]


@app.on_event("startup")
def startup_event():
    # Wait for Qdrant to be ready
    retries = 10
    while retries > 0:
        try:
            qdrant_client.get_collections()
            print("Qdrant is ready.")
            break
        except (UnexpectedResponse, Exception):
            print("Qdrant not ready, waiting...")
            import time

            time.sleep(5)
            retries -= 1

    if retries == 0:
        print("Could not connect to Qdrant. Exiting.")
        exit(1)


@app.get("/search/", response_model=list[SearchResult])
async def search(query: str, workspace_id: int, top_k: int = 5):
    last_err: Exception | None = None
    for delay in _retry_backoff_delays(3):
        try:
            query_embedding = genai.embed_content(
                model=embedding_model,
                content=query,
                task_type="retrieval_query",
            )["embedding"]
            search_results = qdrant_client.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="workspace_id",
                            match=models.MatchValue(value=workspace_id),
                        )
                    ]
                ),
                limit=top_k,
                with_payload=True,
                timeout=60,
            )
            results = [
                SearchResult(id=hit.id, payload=hit.payload, score=hit.score)
                for hit in search_results
            ]
            return results
        except Exception as e:
            last_err = e
            if delay > 0:
                await asyncio.sleep(delay)
    raise RuntimeError(f"Failed to search in Qdrant: {last_err}")
