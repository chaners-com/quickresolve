import os
import time
from typing import List, Optional, TypedDict, Any
import json
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

# LangChain / LangGraph stack
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

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

# External services inside the docker-compose network
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:8001")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8000")

# LLM configured via LangChain
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Allow startup; requests will fail gracefully if used without key
    print("Warning: GEMINI_API_KEY is not set. LLM calls will fail until configured.")
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.2,
)

QDRANT_COLLECTION_NAME = "file_embeddings"

# --- Startup Event ---

@app.on_event("startup")
def startup_event():
    # Qdrant is optional for this service because retrieval is delegated.
    # If available, we log readiness; otherwise, we proceed without blocking.
    try:
        if os.getenv("QDRANT_URL"):
            qdrant_client.get_collections()
            try:
                qdrant_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
                print("Qdrant collection accessible.")
            except Exception:
                print(f"Qdrant reachable but collection '{QDRANT_COLLECTION_NAME}' not found (delegated to embedding-service).")
        else:
            print("QDRANT_URL not set; retrieval delegated to embedding-service.")
    except Exception as e:
        print(f"Qdrant check skipped due to error: {e}. Continuing startup.")

# --- Helper Functions ---

def search_relevant_documents(query: str, workspace_id: int, top_k: int = 3) -> List[dict]:
    """Search for relevant documents for a workspace via the embedding service."""
    try:
        resp = requests.get(
            f"{EMBEDDING_SERVICE_URL}/search/",
            params={"query": query, "workspace_id": workspace_id, "top_k": top_k},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
        # Normalize to internal dict shape
        normalized: List[dict] = []
        for hit in results:
            payload = hit.get("payload") or {}
            normalized.append(
                {
                    "id": hit.get("id"),
                    "score": hit.get("score"),
                    "s3_key": payload.get("s3_key", ""),
                    "workspace_id": payload.get("workspace_id", workspace_id),
                }
            )
        return normalized
    except Exception as e:
        print(f"Failed to search for relevant documents: {e}")
        return []


def fetch_file_content(s3_key: str) -> str:
    """Fetch raw file content from the ingestion service for a given key."""
    try:
        resp = requests.get(
            f"{INGESTION_SERVICE_URL}/file-content/", params={"s3_key": s3_key}, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("content", "")
    except Exception as e:
        print(f"Failed to fetch file content for {s3_key}: {e}")
        return ""

class AgentState(TypedDict):
    messages: List[AnyMessage]
    workspace_id: int


def build_tools_for_workspace(workspace_id: int):
    @tool("retrieve_knowledge", return_direct=False)
    def retrieve_knowledge(query: str, top_k: int = 3) -> str:
        """Retrieve concise, relevant information for the given user query.
        Focus on accuracy and brevity. Do not include any source identifiers."""
        hits = search_relevant_documents(query, workspace_id, top_k=top_k)
        if not hits:
            return ""
        snippets: List[str] = []
        for hit in hits:
            s3_key = hit.get("s3_key", "")
            if not s3_key:
                continue
            content = fetch_file_content(s3_key)
            if not content:
                continue
            # Trim each document to avoid oversized context
            trimmed = content.strip()
            if len(trimmed) > 1600:
                trimmed = trimmed[:1600]
            snippets.append(trimmed)
            if len(snippets) >= top_k:
                break
        return "\n\n---\n\n".join(snippets)

    @tool("escalate_to_human", return_direct=True)
    def escalate_to_human(reason: str = "") -> str:
        """Escalate the conversation to a human agent when appropriate."""
        return (
            "It looks like this needs human attention. I've escalated your request to our support team. "
            "You will hear back shortly."
        )

    return [retrieve_knowledge, escalate_to_human]


def build_agent_graph(workspace_id: int):
    tools = build_tools_for_workspace(workspace_id)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: AgentState):
        system = SystemMessage(
            content=(
                "You are a senior customer service assistant."
                " Provide accurate, concise, and actionable answers."
                " Never disclose internal tooling, systems, or where information comes from."
                " Ask at most one clarifying question if absolutely necessary."
                " Prefer answering directly when enough context is available."
            )
        )
        response = model_with_tools.invoke([system, *state["messages"]])
        return {"messages": [response]}

    tool_node = ToolNode(build_tools_for_workspace(workspace_id))

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def generate_response(messages: List[Message], workspace_id: int) -> str:
    """Run the LangGraph agent on the given conversation and return the final text."""
    try:
        graph = build_agent_graph(workspace_id)
        # Convert incoming history to LangChain messages
        lc_history: List[AnyMessage] = []
        for m in messages:
            if m.role == "user":
                lc_history.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                lc_history.append(AIMessage(content=m.content))
            else:
                lc_history.append(SystemMessage(content=m.content))
        state: AgentState = {"messages": lc_history, "workspace_id": workspace_id}
        result = graph.invoke(state)
        # Find the last assistant message text
        for msg in reversed(result["messages"]):
            if getattr(msg, "type", "") == "ai":
                return msg.content if isinstance(msg.content, str) else str(msg.content)
        # Fallback: return last message content
        last = result["messages"][-1]
        return last.content if isinstance(last.content, str) else str(last.content)
    except Exception as e:
        print(f"Agent failed: {e}")
        return (
            "Sorry, I'm having trouble responding right now. Please try again in a moment."
        )

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
        
        # Generate response via agent graph (retrieval occurs internally when needed)
        response = generate_response(
            request.messages,
            request.workspace_id,
        )
        
        return ConversationResponse(
            response=response,
            # Intentionally not exposing retrieval provenance
            relevant_docs=[],
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