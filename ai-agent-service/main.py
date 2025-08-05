import os
import time
from typing import List, Optional
import json

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

# --- Pydantic Models ---

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ConversationRequest(BaseModel):
    messages: List[Message]
    workspace_id: int
    user_id: Optional[str] = None

class ConversationResponse(BaseModel):
    response: str
    relevant_docs: List[dict]
    workspace_id: int

class WorkspaceInfo(BaseModel):
    workspace_id: int
    name: str
    description: Optional[str] = None

# --- App and Clients Setup ---
app = FastAPI(title="AI Customer Service Agent")

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
chat_model = genai.GenerativeModel('gemini-1.5-flash')

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
        print(f"Collection {QDRANT_COLLECTION_NAME} not found.")

# --- Helper Functions ---

def search_relevant_documents(query: str, workspace_id: int, top_k: int = 3) -> List[dict]:
    """Search for relevant documents in the specified workspace."""
    try:
        query_embedding = genai.embed_content(
            model=embedding_model, content=query, task_type="retrieval_query"
        )["embedding"]
    except Exception as e:
        print(f"Failed to generate query embedding: {e}")
        return []

    try:
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
        )
        
        # Fetch the actual content from S3 or return metadata
        results = []
        for hit in search_results:
            result = {
                "id": hit.id,
                "score": hit.score,
                "s3_key": hit.payload.get("s3_key", ""),
                "workspace_id": hit.payload.get("workspace_id", workspace_id)
            }
            results.append(result)
        
        return results
    except Exception as e:
        print(f"Failed to search in Qdrant: {e}")
        return []

def generate_response(messages: List[Message], relevant_docs: List[dict], workspace_id: int) -> str:
    """Generate a response using the conversation history and relevant documents."""
    
    # Create context from relevant documents
    context = ""
    if relevant_docs:
        context = "Based on the following relevant information:\n\n"
        for i, doc in enumerate(relevant_docs, 1):
            context += f"Document {i} (Relevance: {doc['score']:.2f}):\n"
            context += f"File: {doc['s3_key']}\n\n"
    
    # Create the system prompt
    system_prompt = f"""You are a helpful customer service AI assistant for workspace {workspace_id}. 
Your role is to help users with their questions and issues based on the available documentation and knowledge base.

{context}

Please provide helpful, accurate, and professional responses. If you don't have enough information to answer a question, 
be honest about it and suggest what additional information might be needed.

Always be polite, patient, and try to provide actionable solutions when possible."""

    # Prepare conversation for Gemini
    conversation = []
    conversation.append({"role": "user", "parts": [system_prompt]})
    
    # Add the conversation history
    for message in messages:
        conversation.append({
            "role": message.role,
            "parts": [message.content]
        })
    
    try:
        response = chat_model.generate_content(conversation)
        return response.text
    except Exception as e:
        print(f"Failed to generate response: {e}")
        return "I apologize, but I'm having trouble generating a response right now. Please try again."

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ai-agent"}

@app.get("/workspaces", response_model=List[WorkspaceInfo])
async def get_workspaces():
    """Get list of available workspaces."""
    try:
        # This is a simplified version - in a real app you'd have a proper workspace management system
        # For now, we'll return some example workspaces
        workspaces = [
            WorkspaceInfo(workspace_id=1, name="General Support", description="General customer support knowledge base"),
            WorkspaceInfo(workspace_id=2, name="Technical Support", description="Technical issues and troubleshooting"),
            WorkspaceInfo(workspace_id=3, name="Product Documentation", description="Product features and documentation")
        ]
        return workspaces
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspaces: {e}")

@app.post("/conversation", response_model=ConversationResponse)
async def handle_conversation(request: ConversationRequest):
    """Handle a conversation turn with the AI agent."""
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Get the latest user message
        latest_message = request.messages[-1]
        if latest_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        # Search for relevant documents
        relevant_docs = search_relevant_documents(
            latest_message.content, 
            request.workspace_id, 
            top_k=3
        )
        
        # Generate response
        response = generate_response(
            request.messages, 
            relevant_docs, 
            request.workspace_id
        )
        
        return ConversationResponse(
            response=response,
            relevant_docs=relevant_docs,
            workspace_id=request.workspace_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process conversation: {e}")

@app.get("/search/{workspace_id}")
async def search_workspace(query: str, workspace_id: int, top_k: int = 5):
    """Search for documents in a specific workspace."""
    try:
        results = search_relevant_documents(query, workspace_id, top_k)
        return {"results": results, "workspace_id": workspace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 