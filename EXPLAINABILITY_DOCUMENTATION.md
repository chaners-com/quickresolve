# QuickResolve Project - Complete Explainability Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Algorithms and AI Models](#algorithms-and-ai-models)
4. [API Endpoints and Data Flow](#api-endpoints-and-data-flow)
5. [Libraries and Dependencies](#libraries-and-dependencies)
6. [Database Schema](#database-schema)
7. [Vector Search Implementation](#vector-search-implementation)
8. [File Processing Pipeline](#file-processing-pipeline)
9. [AI Agent Conversation Flow](#ai-agent-conversation-flow)
10. [Security and Performance Considerations](#security-and-performance-considerations)
11. [Monitoring and Debugging](#monitoring-and-debugging)

---

## Project Overview

**QuickResolve** is a modern document search and retrieval system built with microservices architecture, featuring semantic search capabilities powered by Google Gemini AI and vector storage with Qdrant. The system enables users to upload documents, automatically generate embeddings, perform semantic search, and interact with an AI-powered customer service chatbot.

### Key Features
- **Document Upload & Storage**: Secure file upload with MinIO S3-compatible storage
- **Semantic Search**: AI-powered document search using vector embeddings
- **AI Chat Assistant**: Context-aware customer service chatbot
- **Multi-workspace Support**: Isolated workspaces for different user groups
- **Real-time Processing**: Asynchronous document processing pipeline

---

## System Architecture

### Microservices Architecture

The system follows a microservices pattern with the following components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Ingestion       │    │  Embedding      │
│   (Nginx)       │◄──►│  Service         │◄──►│  Service        │
│   Port: 8080    │    │  Port: 8000      │    │  Port: 8001     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         │              ┌──────────────────┐    ┌─────────────────┐
         │              │   PostgreSQL     │    │     Qdrant      │
         │              │   Port: 5432     │    │   Port: 6333    │
         │              └──────────────────┘    └─────────────────┘
         │                       │
         ▼                       │
┌─────────────────┐              │
│  AI Agent       │              │
│  Service        │              │
│  Port: 8002     │              │
└─────────────────┘              │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   MinIO         │    │   Data Generator │
│   Port: 9000    │    │   (Optional)     │
└─────────────────┘    └──────────────────┘
```

### Service Communication Flow

1. **Frontend** → **Ingestion Service**: File uploads and metadata management
2. **Ingestion Service** → **Embedding Service**: Trigger embedding generation
3. **Embedding Service** → **Qdrant**: Store vector embeddings
4. **AI Agent Service** → **Qdrant**: Retrieve relevant documents
5. **AI Agent Service** → **Gemini AI**: Generate responses

---

## Algorithms and AI Models

### 1. Google Gemini AI Integration

#### Embedding Model: `models/embedding-001`
- **Purpose**: Generate vector representations of documents and queries
- **Vector Dimensions**: 768-dimensional embeddings
- **Task Types**:
  - `retrieval_document`: For document content embedding
  - `retrieval_query`: For search query embedding
- **Distance Metric**: Cosine similarity
- **Why This Model**: 
  - State-of-the-art performance for semantic search
  - Optimized for retrieval tasks
  - Supports both document and query embedding

#### Chat Model: `gemini-1.5-flash`
- **Purpose**: Generate conversational responses
- **Context Window**: Large context window for conversation history
- **Capabilities**: 
  - Context-aware responses
  - Document-based reasoning
  - Professional customer service tone
- **Why This Model**:
  - Fast response generation
  - Good reasoning capabilities
  - Cost-effective for production use

### 2. Vector Search Algorithm

#### Similarity Search Process
```python
# 1. Query Embedding Generation
query_embedding = genai.embed_content(
    model="models/embedding-001",
    content=query,
    task_type="retrieval_query"
)["embedding"]

# 2. Vector Search in Qdrant
search_results = qdrant_client.search(
    collection_name="file_embeddings",
    query_vector=query_embedding,
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="workspace_id",
                match=models.MatchValue(value=workspace_id)
            )
        ]
    ),
    limit=top_k,
    with_payload=True
)
```

#### Search Algorithm Details
- **Distance Metric**: Cosine similarity (normalized dot product)
- **Filtering**: Workspace-based isolation
- **Ranking**: Score-based relevance ranking
- **Top-K Retrieval**: Configurable result count

### 3. Document Processing Algorithm

#### Text Processing Pipeline
1. **File Upload**: Raw file content extraction
2. **Encoding**: UTF-8 text encoding
3. **Embedding Generation**: Full document embedding
4. **Vector Storage**: Metadata + embedding storage

#### Chunking Strategy
- **Current Implementation**: Full document embedding
- **Future Enhancement**: Document chunking for better granularity
- **Metadata Storage**: File ID, workspace ID, S3 key

---

## API Endpoints and Data Flow

### 1. Ingestion Service (Port 8000)

#### User Management
```http
POST /users/
Content-Type: application/json
{
    "username": "string"
}
```
- **Purpose**: Create new users
- **Validation**: Unique username constraint
- **Response**: User ID and username

```http
GET /users/?username={username}
```
- **Purpose**: Retrieve user by username
- **Response**: User object or empty list

#### Workspace Management
```http
POST /workspaces/
Content-Type: application/json
{
    "name": "string",
    "owner_id": "integer"
}
```
- **Purpose**: Create isolated workspaces
- **Validation**: Owner must exist
- **Response**: Workspace ID and metadata

```http
GET /workspaces/?name={name}&owner_id={id}
```
- **Purpose**: Retrieve workspace by name and owner
- **Response**: Workspace object or empty list

#### File Upload
```http
POST /uploadfile/?workspace_id={id}
Content-Type: multipart/form-data
```
- **Purpose**: Upload and process documents
- **Process**:
  1. File validation
  2. S3 storage upload
  3. Database metadata storage
  4. Trigger embedding generation
- **Response**: File ID and S3 key

#### File Content Retrieval
```http
GET /file-content/?s3_key={key}
```
- **Purpose**: Retrieve file content from S3
- **Response**: File content as text

### 2. Embedding Service (Port 8001)

#### Embedding Generation
```http
POST /embed/
Content-Type: application/json
{
    "s3_key": "string",
    "file_id": "integer",
    "workspace_id": "integer"
}
```
- **Process**:
  1. Download file from S3
  2. Generate embedding using Gemini AI
  3. Store in Qdrant vector database
- **Response**: Success confirmation

#### Semantic Search
```http
GET /search/?query={query}&workspace_id={id}&top_k={k}
```
- **Process**:
  1. Generate query embedding
  2. Search Qdrant with workspace filter
  3. Return ranked results
- **Response**: List of search results with scores

### 3. AI Agent Service (Port 8002)

#### Health Check
```http
GET /health
```
- **Purpose**: Service health monitoring
- **Response**: Service status

#### Workspace Listing
```http
GET /workspaces
```
- **Purpose**: Get available workspaces
- **Response**: List of workspace information

#### Conversation Handling
```http
POST /conversation
Content-Type: application/json
{
    "messages": [
        {"role": "user", "content": "string"},
        {"role": "assistant", "content": "string"}
    ],
    "workspace_id": "integer",
    "user_id": "string (optional)"
}
```
- **Process**:
  1. Extract latest user message
  2. Search for relevant documents
  3. Generate context-aware response
  4. Return response with source documents
- **Response**: AI response and relevant document sources

#### Document Search
```http
GET /search/{workspace_id}?query={query}&top_k={k}
```
- **Purpose**: Search documents in specific workspace
- **Response**: Search results with relevance scores

---

## Libraries and Dependencies

### Backend Dependencies

#### Core Framework
- **FastAPI** (v0.104.1): Modern Python web framework
  - **Why**: High performance, automatic API documentation, type hints
  - **Features**: Async support, automatic validation, OpenAPI generation

#### Database and ORM
- **SQLAlchemy** (v2.0+): Python SQL toolkit and ORM
  - **Why**: Database abstraction, relationship management, migrations
- **psycopg2-binary**: PostgreSQL adapter
  - **Why**: Native PostgreSQL support, performance

#### Vector Database
- **qdrant-client** (v1.15.1): Qdrant vector database client
  - **Why**: High-performance vector search, filtering capabilities
  - **Features**: Cosine similarity, metadata filtering, batch operations

#### AI/ML Libraries
- **google-generativeai** (v0.3.2): Google Gemini AI client
  - **Why**: State-of-the-art AI models, embedding generation
  - **Features**: Text generation, embeddings, conversation management

#### Cloud Storage
- **boto3**: AWS SDK for Python
  - **Why**: S3-compatible storage (MinIO), file management
  - **Features**: File upload/download, bucket management

#### HTTP Client
- **requests**: HTTP library for Python
  - **Why**: Inter-service communication, API calls
  - **Features**: Session management, timeout handling

#### Web Server
- **uvicorn** (v0.24.0): ASGI server
  - **Why**: Fast, lightweight ASGI server for FastAPI
  - **Features**: Hot reload, multiple workers

#### Data Validation
- **pydantic** (v2.5.0): Data validation library
  - **Why**: Automatic data validation, serialization
  - **Features**: Type hints, model generation

### Frontend Dependencies

#### Web Server
- **Nginx**: High-performance web server
  - **Why**: Static file serving, reverse proxy, load balancing
  - **Features**: Caching, compression, SSL termination

#### JavaScript
- **Vanilla JavaScript**: No framework dependencies
  - **Why**: Lightweight, no build process, easy maintenance
  - **Features**: Modern ES6+ features, async/await

### Infrastructure Dependencies

#### Database
- **PostgreSQL** (v13): Relational database
  - **Why**: ACID compliance, complex queries, reliability
  - **Features**: JSON support, full-text search

#### Vector Database
- **Qdrant** (v1.9.0): Vector similarity search engine
  - **Why**: High-performance vector operations, filtering
  - **Features**: Cosine similarity, metadata filtering, persistence

#### Object Storage
- **MinIO**: S3-compatible object storage
  - **Why**: Scalable file storage, S3 API compatibility
  - **Features**: Versioning, lifecycle management

#### Containerization
- **Docker**: Container platform
  - **Why**: Consistent environments, easy deployment
  - **Features**: Multi-stage builds, volume management

---

## Database Schema

### PostgreSQL Tables

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL
);
```
- **Purpose**: User authentication and management
- **Indexes**: Primary key on id, unique index on username

#### Workspaces Table
```sql
CREATE TABLE workspaces (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    owner_id INTEGER REFERENCES users(id)
);
```
- **Purpose**: Workspace isolation and organization
- **Relationships**: Many-to-one with users
- **Indexes**: Primary key on id, index on owner_id

#### Files Table
```sql
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    s3_key VARCHAR UNIQUE NOT NULL,
    workspace_id INTEGER REFERENCES workspaces(id)
);
```
- **Purpose**: File metadata storage
- **Relationships**: Many-to-one with workspaces
- **Indexes**: Primary key on id, unique index on s3_key, index on workspace_id

### Qdrant Collections

#### File Embeddings Collection
```python
collection_config = {
    "name": "file_embeddings",
    "vectors": {
        "size": 768,
        "distance": "Cosine"
    }
}
```

#### Vector Structure
- **Vector**: 768-dimensional embedding
- **Payload**:
  - `workspace_id`: Integer (for filtering)
  - `s3_key`: String (file reference)
- **ID**: File ID from PostgreSQL

---

## Vector Search Implementation

### Embedding Generation Process

#### Document Embedding
```python
def generate_document_embedding(content: str) -> List[float]:
    """Generate embedding for document content."""
    embedding = genai.embed_content(
        model="models/embedding-001",
        content=content,
        task_type="retrieval_document"
    )["embedding"]
    return embedding
```

#### Query Embedding
```python
def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for search query."""
    embedding = genai.embed_content(
        model="models/embedding-001",
        content=query,
        task_type="retrieval_query"
    )["embedding"]
    return embedding
```

### Search Algorithm

#### Similarity Calculation
```python
def calculate_similarity(query_vector: List[float], 
                        document_vector: List[float]) -> float:
    """Calculate cosine similarity between query and document."""
    # Cosine similarity = dot_product / (norm_a * norm_b)
    dot_product = sum(a * b for a, b in zip(query_vector, document_vector))
    norm_a = sum(a * a for a in query_vector) ** 0.5
    norm_b = sum(b * b for b in document_vector) ** 0.5
    return dot_product / (norm_a * norm_b)
```

#### Search Process
1. **Query Processing**: Convert natural language to vector
2. **Vector Search**: Find similar vectors in Qdrant
3. **Filtering**: Apply workspace-based filters
4. **Ranking**: Sort by similarity score
5. **Result Retrieval**: Return top-k results with metadata

### Performance Optimizations

#### Indexing Strategy
- **Vector Index**: HNSW (Hierarchical Navigable Small World)
- **Metadata Index**: B-tree for workspace filtering
- **Batch Operations**: Bulk embedding storage

#### Caching Strategy
- **Query Cache**: Frequently searched queries
- **Embedding Cache**: Document embeddings
- **Result Cache**: Search results

---

## File Processing Pipeline

### Upload Flow

#### 1. File Validation
```python
def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file."""
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False
    
    # Check file type
    allowed_types = ['.txt', '.md', '.pdf', '.docx']
    if not any(file.filename.endswith(ext) for ext in allowed_types):
        return False
    
    return True
```

#### 2. Storage Process
```python
def store_file(file: UploadFile, workspace_id: int) -> str:
    """Store file in S3 and database."""
    # Generate S3 key
    s3_key = f"{workspace_id}/{file.filename}"
    
    # Upload to S3
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)
    
    # Store metadata in database
    db_file = File(
        name=file.filename,
        s3_key=s3_key,
        workspace_id=workspace_id
    )
    db.add(db_file)
    db.commit()
    
    return s3_key
```

#### 3. Embedding Generation
```python
def process_embedding(s3_key: str, file_id: int, workspace_id: int):
    """Generate and store embeddings."""
    # Download file content
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    content = response["Body"].read().decode("utf-8")
    
    # Generate embedding
    embedding = genai.embed_content(
        model="models/embedding-001",
        content=content,
        task_type="retrieval_document"
    )["embedding"]
    
    # Store in Qdrant
    qdrant_client.upsert(
        collection_name="file_embeddings",
        points=[{
            "id": file_id,
            "vector": embedding,
            "payload": {
                "workspace_id": workspace_id,
                "s3_key": s3_key
            }
        }]
    )
```

### Error Handling

#### Retry Mechanism
```python
def retry_operation(operation, max_retries=3, delay=1):
    """Retry operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay * (2 ** attempt))
```

#### Graceful Degradation
- **S3 Unavailable**: Store in local cache
- **Qdrant Unavailable**: Queue embeddings for later processing
- **AI Service Unavailable**: Return cached results

---

## AI Agent Conversation Flow

### Conversation Management

#### Message Processing
```python
def process_conversation(messages: List[Message], workspace_id: int):
    """Process conversation and generate response."""
    # Extract latest user message
    latest_message = messages[-1]
    
    # Search for relevant documents
    relevant_docs = search_relevant_documents(
        latest_message.content, 
        workspace_id, 
        top_k=3
    )
    
    # Generate context-aware response
    response = generate_response(messages, relevant_docs, workspace_id)
    
    return response, relevant_docs
```

#### Context Building
```python
def build_context(relevant_docs: List[dict]) -> str:
    """Build context from relevant documents."""
    context = "Based on the following relevant information:\n\n"
    
    for i, doc in enumerate(relevant_docs, 1):
        context += f"Document {i} (Relevance: {doc['score']:.2f}):\n"
        context += f"File: {doc['s3_key']}\n\n"
    
    return context
```

#### Response Generation
```python
def generate_response(messages: List[Message], 
                     relevant_docs: List[dict], 
                     workspace_id: int) -> str:
    """Generate AI response using conversation history and documents."""
    
    # Create system prompt
    system_prompt = f"""You are a helpful customer service AI assistant for workspace {workspace_id}. 
Your role is to help users with their questions and issues based on the available documentation and knowledge base.

{context}

Please provide helpful, accurate, and professional responses. If you don't have enough information to answer a question, 
be honest about it and suggest what additional information might be needed.

Always be polite, patient, and try to provide actionable solutions when possible."""

    # Prepare conversation for Gemini
    conversation = []
    conversation.append({"role": "user", "parts": [system_prompt]})
    
    # Add conversation history
    for message in messages:
        conversation.append({
            "role": message.role,
            "parts": [message.content]
        })
    
    # Generate response
    response = chat_model.generate_content(conversation)
    return response.text
```

### Conversation Features

#### Memory Management
- **Session-based**: Conversation history per session
- **Context Window**: Limited conversation history
- **Source Tracking**: Document sources for each response

#### Response Quality
- **Relevance Scoring**: Document relevance scores
- **Source Attribution**: Clear source document references
- **Confidence Indication**: Response confidence levels

---

## Security and Performance Considerations

### Security Measures

#### Input Validation
```python
def validate_input(data: dict) -> bool:
    """Validate user input."""
    # Check for SQL injection
    if any(char in data.get('username', '') for char in [';', '--', '/*']):
        return False
    
    # Check for XSS
    if '<script>' in data.get('content', '').lower():
        return False
    
    return True
```

#### Authentication (Future Enhancement)
- **JWT Tokens**: Stateless authentication
- **API Keys**: Service-to-service authentication
- **Rate Limiting**: Prevent abuse

#### Data Isolation
- **Workspace-based**: Complete data isolation
- **User-based**: User-specific data access
- **Encryption**: Data encryption at rest and in transit

### Performance Optimizations

#### Database Optimization
```sql
-- Indexes for performance
CREATE INDEX idx_files_workspace ON files(workspace_id);
CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_users_username ON users(username);
```

#### Caching Strategy
```python
# Redis cache for frequently accessed data
cache.set(f"user:{user_id}", user_data, ttl=3600)
cache.set(f"workspace:{workspace_id}", workspace_data, ttl=3600)
```

#### Connection Pooling
```python
# Database connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### Scalability Considerations

#### Horizontal Scaling
- **Load Balancing**: Nginx load balancer
- **Service Replication**: Multiple service instances
- **Database Sharding**: Workspace-based sharding

#### Resource Management
- **Memory Usage**: Embedding model memory optimization
- **CPU Usage**: Async processing for I/O operations
- **Storage**: Efficient vector storage and retrieval

---

## Monitoring and Debugging

### Logging Strategy

#### Structured Logging
```python
import logging
import json

def log_event(level: str, message: str, **kwargs):
    """Structured logging with context."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message,
        "service": "quickresolve",
        **kwargs
    }
    logging.getLogger().log(
        getattr(logging, level.upper()),
        json.dumps(log_entry)
    )
```

#### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failed operations
- **CRITICAL**: Critical system failures

### Health Checks

#### Service Health Endpoints
```python
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": check_database_connection(),
            "qdrant": check_qdrant_connection(),
            "s3": check_s3_connection(),
            "ai_service": check_ai_service_connection()
        }
    }
    return health_status
```

#### Monitoring Metrics
- **Response Times**: API endpoint response times
- **Error Rates**: Error percentage per endpoint
- **Throughput**: Requests per second
- **Resource Usage**: CPU, memory, disk usage

### Debugging Tools

#### API Documentation
- **OpenAPI/Swagger**: Automatic API documentation
- **Interactive Testing**: Built-in API testing interface
- **Request/Response Logging**: Detailed request tracking

#### Development Tools
```python
# Debug mode configuration
if DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### Troubleshooting Guide

#### Common Issues

1. **Database Connection Errors**
   - Check PostgreSQL container status
   - Verify connection string
   - Check network connectivity

2. **Embedding Generation Failures**
   - Verify Gemini API key
   - Check API quota limits
   - Validate file content encoding

3. **Vector Search Issues**
   - Check Qdrant collection existence
   - Verify vector dimensions match
   - Check workspace filtering

4. **File Upload Problems**
   - Verify MinIO bucket creation
   - Check file size limits
   - Validate file permissions

#### Debug Commands
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs -f [service-name]

# Access service containers
docker-compose exec [service-name] bash

# Check database connection
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB

# Monitor resource usage
docker stats
```

---

## Conclusion

This documentation provides a comprehensive overview of the QuickResolve project's architecture, algorithms, and implementation details. The system is designed with scalability, maintainability, and performance in mind, using modern technologies and best practices for AI-powered document search and retrieval.

### Key Strengths
- **Modular Architecture**: Microservices enable independent scaling and development
- **AI-Powered Search**: State-of-the-art semantic search using Gemini AI
- **Real-time Processing**: Asynchronous document processing pipeline
- **Multi-tenant Support**: Workspace-based data isolation
- **Comprehensive Monitoring**: Built-in health checks and logging

### Future Enhancements
- **Document Chunking**: Granular document processing for better search
- **Advanced Filtering**: Metadata-based search filters
- **User Authentication**: JWT-based authentication system
- **Performance Optimization**: Caching and connection pooling
- **Analytics Dashboard**: Usage analytics and insights

This documentation serves as a complete reference for understanding, monitoring, and maintaining the QuickResolve system. 