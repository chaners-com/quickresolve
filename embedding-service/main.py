from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time
import boto3
import os
import google.generativeai as genai
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

# --- Pydantic Models ---
class FileInfo(BaseModel):
    s3_key: str
    file_id: int
    workspace_id: int

class SearchResult(BaseModel):
    id: int
    payload: Optional[dict] = None
    score: float

# --- App and Clients Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
embedding_model = "models/embedding-001"

s3 = boto3.client(
    's3',
    endpoint_url=os.getenv("S3_ENDPOINT"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY")
)
S3_BUCKET = os.getenv("S3_BUCKET")
QDRANT_COLLECTION_NAME = "file_embeddings"

# --- Startup Event to Ensure Qdrant Collection Exists ---
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
            time.sleep(5)
            retries -= 1
    
    if retries == 0:
        print("Could not connect to Qdrant. Exiting.")
        exit(1)

    try:
        qdrant_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
    except (UnexpectedResponse, Exception):
        qdrant_client.recreate_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
        )

# --- API Endpoints ---
@app.post("/embed/")
async def embed_file(file_info: FileInfo):
    """Downloads a file, generates embeddings, and stores them in Qdrant."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=file_info.s3_key)
        file_content = response['Body'].read().decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download from S3: {e}")

    try:
        embedding = genai.embed_content(
            model=embedding_model,
            content=file_content,
            task_type="retrieval_document"
        )["embedding"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {e}")

    try:
        qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=file_info.file_id,
                    vector=embedding,
                    payload={"workspace_id": file_info.workspace_id, "s3_key": file_info.s3_key}
                )
            ],
            wait=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upsert to Qdrant: {e}")

    return {"message": f"Successfully embedded file {file_info.s3_key}"}

@app.get("/search/", response_model=list[SearchResult])
async def search(query: str, workspace_id: int, top_k: int = 5):
    """Embeds a query and searches for similar vectors in a specific workspace."""
    try:
        query_embedding = genai.embed_content(
            model=embedding_model,
            content=query,
            task_type="retrieval_query"
        )["embedding"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate query embedding: {e}")

    try:
        search_results = qdrant_client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id))
                ]
            ),
            limit=top_k,
            with_payload=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search in Qdrant: {e}")

    results = [SearchResult(id=hit.id, payload=hit.payload, score=hit.score) for hit in search_results]
    return results 