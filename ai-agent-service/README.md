# AI Customer Service Agent

This service provides an AI-powered customer service chatbot that can handle conversations and query the Qdrant vector database for relevant information.

## Features

- **Conversation Management**: Handles multi-turn conversations with context awareness
- **Document Retrieval**: Searches Qdrant database for relevant documents based on user queries
- **AI Response Generation**: Uses Google's Gemini model to generate contextual responses
- **Workspace Support**: Supports multiple workspaces for different knowledge domains
- **RESTful API**: Provides clean API endpoints for integration

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Workspaces
- `GET /workspaces` - Get list of available workspaces

### Conversation
- `POST /conversation` - Handle a conversation turn

### Search
- `GET /search/{workspace_id}` - Search documents in a specific workspace

## Environment Variables

- `QDRANT_URL`: URL of the Qdrant vector database
- `GEMINI_API_KEY`: Google Gemini API key

## Usage

### Starting the Service

```bash
# Using Docker
docker build -t ai-agent-service .
docker run -p 8002:8002 \
  -e QDRANT_URL=http://localhost:6333 \
  -e GEMINI_API_KEY=your_api_key \
  ai-agent-service

# Using Python directly
pip install -r requirements.txt
python main.py
```

### Example API Usage

```python
import requests

# Get available workspaces
response = requests.get("http://localhost:8002/workspaces")
workspaces = response.json()

# Start a conversation
conversation_data = {
    "messages": [
        {"role": "user", "content": "How can I reset my password?"}
    ],
    "workspace_id": 1
}

response = requests.post("http://localhost:8002/conversation", json=conversation_data)
result = response.json()
print(result["response"])
```

## Architecture

The service integrates with:
- **Qdrant**: Vector database for document storage and retrieval
- **Google Gemini**: AI model for response generation
- **FastAPI**: Web framework for API endpoints

## Testing

Run the tests with:
```bash
pytest test_main.py
```

## Dependencies

- FastAPI
- Uvicorn
- Google Generative AI
- Qdrant Client
- Pydantic 