import os
from typing import List, Optional, TypedDict
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient

# LangChain / LangGraph stack
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
)
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
EMBEDDING_SERVICE_URL = os.getenv(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8001"
)
INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "http://ingestion-service:8000"
)

# LLM configured via LangChain
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Allow startup; requests will fail gracefully if used without key
    print(
        "Warning: GEMINI_API_KEY is not set. LLM calls will fail until configured."
    )
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.2,
)

QDRANT_COLLECTION_NAME = "file_embeddings"

# --- Startup Event ---


@app.on_event("startup")
def startup_event():
    # Log service URLs for debugging
    print("AI Agent Service starting up...")
    print(f"Embedding Service URL: {EMBEDDING_SERVICE_URL}")
    print(f"Ingestion Service URL: {INGESTION_SERVICE_URL}")

    # Test connectivity to external services
    try:
        # Test embedding service
        resp = requests.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=5)
        print(f"Embedding service health check: {resp.status_code}")
    except Exception as e:
        print(f"Warning: Cannot connect to embedding service: {e}")

    try:
        # Test ingestion service
        resp = requests.get(f"{INGESTION_SERVICE_URL}/health", timeout=5)
        print(f"Ingestion service health check: {resp.status_code}")
    except Exception as e:
        print(f"Warning: Cannot connect to ingestion service: {e}")

    # Qdrant is optional for this service because retrieval is delegated.
    # If available, we log readiness; otherwise, we proceed without blocking.
    try:
        if os.getenv("QDRANT_URL"):
            qdrant_client.get_collections()
            try:
                qdrant_client.get_collection(
                    collection_name=QDRANT_COLLECTION_NAME
                )
                print("Qdrant collection accessible.")
            except Exception:
                print(
                    f"Qdrant reachable but collection '{QDRANT_COLLECTION_NAME}' "
                    f"not found (delegated to embedding-service)."
                )
        else:
            print(
                "QDRANT_URL not set; retrieval delegated to embedding-service."
            )
    except Exception as e:
        print(f"Qdrant check skipped due to error: {e}. Continuing startup.")


# --- Helper Functions ---


def search_relevant_documents(
    query: str, workspace_id: int, top_k: int = 3
) -> List[dict]:
    """Search for relevant documents for a workspace via the embedding service."""
    try:
        print(
            f"Searching for query: '{query}' in workspace {workspace_id} "
            f"with top_k={top_k}"
        )
        print(f"Using embedding service URL: {EMBEDDING_SERVICE_URL}")

        resp = requests.get(
            f"{EMBEDDING_SERVICE_URL}/search/",
            params={
                "query": query,
                "workspace_id": workspace_id,
                "top_k": top_k,
            },
            timeout=15,
        )

        print(f"Embedding service response status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"Embedding service error: {resp.text}")
            return []

        resp.raise_for_status()
        results = resp.json()
        print(f"Raw search results: {results}")

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

        print(f"Normalized {len(normalized)} results")
        return normalized
    except Exception as e:
        print(f"Failed to search for relevant documents: {e}")
        return []


def fetch_file_content(s3_key: str) -> str:
    """Fetch raw file content from the ingestion service for a given key."""
    try:
        resp = requests.get(
            f"{INGESTION_SERVICE_URL}/file-content/",
            params={"s3_key": s3_key},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("content", "")
    except Exception as e:
        print(f"Failed to fetch file content for {s3_key}: {e}")
        return ""


def get_workspace_name(workspace_id: int) -> str:
    """Get workspace name by ID."""
    try:
        response = requests.get(
            f"{INGESTION_SERVICE_URL}/workspaces/all", timeout=5
        )
        if response.status_code == 200:
            workspaces = response.json()
            for ws in workspaces:
                if ws["id"] == workspace_id:
                    return ws["name"]
    except Exception as e:
        print(f"Failed to get workspace name for {workspace_id}: {e}")
    return f"Workspace {workspace_id}"


class AgentState(TypedDict):
    messages: List[AnyMessage]
    workspace_id: int


def build_tools_for_workspace(workspace_id: int):
    @tool("retrieve_knowledge", return_direct=False)
    def retrieve_knowledge(query: str, top_k: int = 3) -> str:
        """Search and retrieve relevant information from the knowledge base to answer user questions.
        This tool should be used whenever the user asks a question that requires specific information.
        Always use this tool first to gather relevant context before providing an answer."""
        hits = search_relevant_documents(query, workspace_id, top_k=top_k)
        if not hits:
            return "No relevant information found in the knowledge base."
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
            "It looks like this needs human attention. I've escalated your request "
            "to our support team. You will hear back shortly."
        )

    return [retrieve_knowledge, escalate_to_human]


def build_agent_graph(workspace_id: int):
    tools = build_tools_for_workspace(workspace_id)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: AgentState):
        system = SystemMessage(
            content=(
                "You are a senior customer service assistant with access to a knowledge base."
                " IMPORTANT: For EVERY user question, you MUST use the 'retrieve_knowledge' "
                "tool first to search for relevant information."
                " Only after retrieving relevant context should you provide your answer."
                " Provide accurate, concise, and actionable answers based on the retrieved information."
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
    graph.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    graph.add_edge("tools", "agent")
    return graph.compile()


def generate_response(
    messages: List[Message], workspace_id: int
) -> tuple[str, List[dict]]:
    """Run the LangGraph agent on the given conversation and return the final text and retrieved documents."""
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

        state: AgentState = {
            "messages": lc_history,
            "workspace_id": workspace_id,
        }
        result = graph.invoke(state)

        # Track retrieved documents from tool usage
        retrieved_docs = []

        # Check if tools were used and extract document information
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get("name") == "retrieve_knowledge":
                        print(
                            f"Tool 'retrieve_knowledge' was called with: "
                            f"{tool_call.get('args', {})}"
                        )
                        # Extract the query used for retrieval
                        query = tool_call.get("args", {}).get("query", "")
                        if query:
                            # Search for documents using the same query
                            docs = search_relevant_documents(
                                query, workspace_id, top_k=3
                            )
                            for doc in docs:
                                content = fetch_file_content(
                                    doc.get("s3_key", "")
                                )
                                retrieved_docs.append(
                                    {
                                        "id": doc.get("id"),
                                        "score": doc.get("score"),
                                        "s3_key": doc.get("s3_key", ""),
                                        "workspace_id": doc.get(
                                            "workspace_id", workspace_id
                                        ),
                                        "content": (
                                            content[:500] + "..."
                                            if len(content) > 500
                                            else content
                                        ),
                                        "workspace_name": get_workspace_name(
                                            doc.get(
                                                "workspace_id", workspace_id
                                            )
                                        ),
                                    }
                                )

        # If no tools were used, fall back to searching with the latest user message
        if not retrieved_docs:
            print("No tools were used, falling back to direct search")
            latest_user_message = messages[-1].content if messages else ""
            docs = search_relevant_documents(
                latest_user_message, workspace_id, top_k=3
            )
            for doc in docs:
                content = fetch_file_content(doc.get("s3_key", ""))
                retrieved_docs.append(
                    {
                        "id": doc.get("id"),
                        "score": doc.get("score"),
                        "s3_key": doc.get("s3_key", ""),
                        "workspace_id": doc.get("workspace_id", workspace_id),
                        "content": (
                            content[:500] + "..."
                            if len(content) > 500
                            else content
                        ),
                        "workspace_name": get_workspace_name(
                            doc.get("workspace_id", workspace_id)
                        ),
                    }
                )

        print(f"Retrieved {len(retrieved_docs)} documents")

        # Find the last assistant message text
        for msg in reversed(result["messages"]):
            if getattr(msg, "type", "") == "ai":
                return (
                    msg.content
                    if isinstance(msg.content, str)
                    else str(msg.content)
                ), retrieved_docs
        # Fallback: return last message content
        last = result["messages"][-1]
        return (
            last.content
            if isinstance(last.content, str)
            else str(last.content)
        ), retrieved_docs
    except Exception as e:
        print(f"Agent failed: {e}")
        return (
            "Sorry, I'm having trouble responding right now. Please try again in a moment.",
            [],
        )


# --- API Endpoints ---


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ai-agent"}


@app.get("/workspaces", response_model=List[WorkspaceInfo])
async def get_workspaces():
    """Get list of available workspaces from the ingestion service."""
    try:
        # Fetch all workspaces from the ingestion service
        response = requests.get(
            f"{INGESTION_SERVICE_URL}/workspaces/all", timeout=10
        )

        if response.status_code == 404:
            # No workspaces found, return empty list
            return []

        response.raise_for_status()
        workspaces_data = response.json()

        # Convert to our WorkspaceInfo format
        workspaces = []
        for ws in workspaces_data:
            workspaces.append(
                WorkspaceInfo(
                    workspace_id=ws["id"],
                    name=ws["name"],
                    description=f"Workspace owned by user {ws['owner_id']}",
                )
            )

        return workspaces

    except Exception as e:
        print(f"Failed to get workspaces from ingestion service: {e}")
        # Return empty list instead of hardcoded workspaces
        return []


@app.post("/conversation", response_model=ConversationResponse)
async def handle_conversation(request: ConversationRequest):
    """Handle a conversation turn with the AI agent."""
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # Get the latest user message
        latest_message = request.messages[-1]
        if latest_message.role != "user":
            raise HTTPException(
                status_code=400, detail="Last message must be from user"
            )

        # Generate response via agent graph (retrieval occurs internally when needed)
        response, relevant_docs = generate_response(
            request.messages,
            request.workspace_id,
        )

        return ConversationResponse(
            response=response,
            relevant_docs=relevant_docs,
            workspace_id=request.workspace_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process conversation: {e}"
        )


@app.get("/search/{workspace_id}")
async def search_workspace(query: str, workspace_id: int, top_k: int = 5):
    """Search for documents in a specific workspace."""
    try:
        results = search_relevant_documents(query, workspace_id, top_k)
        return {"results": results, "workspace_id": workspace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@app.get("/test-search/{workspace_id}")
async def test_search_workspace(query: str, workspace_id: int, top_k: int = 3):
    """Test endpoint to verify search functionality."""
    try:
        print(
            f"Testing search for query: '{query}' in workspace {workspace_id}"
        )

        # Test the search function
        results = search_relevant_documents(query, workspace_id, top_k)
        print(f"Search returned {len(results)} results")

        # Test fetching content for each result
        enhanced_results = []
        for doc in results:
            content = fetch_file_content(doc.get("s3_key", ""))
            enhanced_results.append(
                {
                    "id": doc.get("id"),
                    "score": doc.get("score"),
                    "s3_key": doc.get("s3_key", ""),
                    "workspace_id": doc.get("workspace_id", workspace_id),
                    "content_preview": (
                        content[:200] + "..."
                        if len(content) > 200
                        else content
                    ),
                    "content_length": len(content),
                }
            )

        return {
            "query": query,
            "workspace_id": workspace_id,
            "results": enhanced_results,
            "total_results": len(enhanced_results),
        }
    except Exception as e:
        print(f"Test search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test search failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
