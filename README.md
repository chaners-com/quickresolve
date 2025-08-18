# QuickResolve

A modern document search and retrieval system built with microservices architecture, featuring semantic search capabilities powered by Google Gemini AI and vector storage with Qdrant.

## 🚀 Overview

QuickResolve is a full-stack application that allows users to upload documents, automatically generate embeddings using Google's Gemini AI, perform semantic search across their documents, and interact with an AI-powered customer service chatbot. The system is designed with a microservices architecture for scalability and maintainability.

## 🏗️ Architecture

The application consists of the following microservices:

### Core Services
- **Frontend** (`frontend/`): Web interface for file upload, search, and AI chat
- **Ingestion Service** (`ingestion-service/`): Handles file uploads and metadata management
- **Redaction Service** (`redaction-service/`): Redacts/masks PII in parsed Markdown before chunking (currently a pass-through proxy to chunking)
- **Embedding Service** (`embedding-service/`): Generates embeddings using Gemini AI
- **AI Agent Service** (`ai-agent-service/`): AI-powered customer service chatbot
- **Data Generator** (`data-generator/`): Generates sample customer service tickets for testing

### Infrastructure Services
- **PostgreSQL**: Stores user, workspace, and file metadata
- **Qdrant**: Vector database for storing and searching embeddings
- **MinIO**: S3-compatible object storage for file storage

### Management & Operations Services
- **Management Service** (`management-service/`): Containerized service for graceful shutdown orchestration and service management
- **Snapshot Service** (`snapshot-service/`): Containerized service for continuous Qdrant data backups and restoration

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Database**: PostgreSQL
- **Vector Database**: Qdrant
- **Object Storage**: MinIO
- **AI/ML**: Google Gemini AI; IBM models for document parsing.
- **Containerization**: Docker & Docker Compose

## 📋 Prerequisites

Before running QuickResolve, ensure you have:

- Docker and Docker Compose installed
- A Google Gemini API key
- At least 4GB of available RAM
- Ports 8080, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 5432, 6333, 9000, 9001 available

## 🔧 Environment Variables

**IMPORTANT**: Copy the provided `.env.example` file to `.env` and update the values with your actual configuration:

```bash
cp .env.example .env
```

Then edit the `.env` file with your actual values. The file contains the following variables:

```env
# Database Configuration
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=quickresolve

# MinIO Configuration
MINIO_ROOT_USER=your_minio_user
MINIO_ROOT_PASSWORD=your_minio_password
S3_BUCKET=documents

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Document Parsing Configuration
# Select parser implementations used at build and runtime
# Options: complete-pdf-parser-1.0.0 | fast-pdf-parser-1.0.0
PDF_PARSER_VERSION=complete-pdf-parser-1.0.0
# Options: complete-docx-parser-1.0.0 | fast-docx-parser-1.0.0
DOCX_PARSER_VERSION=complete-docx-parser-1.0.0
```

### 🔑 Required API Keys

- **Google Gemini API Key**: Required for AI functionality. Get yours at [Google AI Studio](https://makersuite.google.com/app/apikey)

### 📝 Environment Setup Steps

1. **Copy the example file**: `cp .env.example .env`
2. **Edit the .env file**: Update all placeholder values with your actual configuration
3. **Never commit .env**: The .env file is already in .gitignore for security

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd quickresolve
```

### 2. Create Environment File

Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env with your actual configuration values
```

### 3. Start the Application

```bash
# Start all services (recommended)
docker-compose up -d

# Start with data generation
docker-compose --profile generate-data up -d
```

### 4. Access the Application

- **Frontend**: http://localhost:8080
- **Chat Interface**: http://localhost:8080/chat
- **MinIO Console**: http://localhost:9001
- **Ingestion Service API**: http://localhost:8000
- **Embedding Service API**: http://localhost:8001
- **AI Agent Service API**: http://localhost:8002
- **Snapshot Service API**: http://localhost:8003
- **Management Service API**: http://localhost:8004
- **Document Parsing Service API**: http://localhost:8005
- **Chunking Service API**: http://localhost:8006
- **Redaction Service API**: http://localhost:8007
- **Qdrant**: http://localhost:6333

## 📖 Usage Guide

### 1. Upload Documents

1. Open http://localhost:8080 in your browser
2. Enter a username and workspace name
3. Select one or more files to upload
4. Click "Upload" to process your documents

### 2. Search Documents

1. After uploading files, use the search interface
2. Enter your search query
3. Click "Search" to find relevant documents
4. Click "Show Content" to view document contents

### 3. AI Chat Assistant

1. Navigate to the Chat Interface at http://localhost:8080/chat
2. Select a workspace from the dropdown
3. Start a conversation with the AI assistant
4. The AI will search through your documents to provide relevant answers
5. View the sources used by the AI in the sidebar

### 4. Generate Sample Data

To generate sample customer service tickets for testing:

```bash
docker-compose --profile generate-data up data-generator
```

This will create 100 sample tickets in the `customer_service_data/` directory.

## 🏗️ Container Architecture & Services

QuickResolve uses a microservices architecture with 10 main containers, each serving a specific purpose:

### 🔧 Core Application Services

#### **Frontend Container** (`frontend`)
- **Purpose**: Web-based user interface for document upload, search, and AI chat
- **Technology**: Nginx + HTML/CSS/JavaScript
- **Port**: 8080
- **Features**: 
  - File upload interface
  - Document search interface
  - AI chat interface
  - Responsive design
  - Service resilience (handles backend unavailability gracefully)

#### **Ingestion Service Container** (`ingestion-service`)
- **Purpose**: Handles file uploads, metadata management, and database operations
- **Technology**: FastAPI (Python)
- **Port**: 8000
- **Features**:
  - File upload processing
  - User and workspace management
  - PostgreSQL database integration
  - MinIO file storage integration
  - RESTful API endpoints

#### **Redaction Service Container** (`redaction-service`)
- **Purpose**: Remove or mask PII in documents prior to chunking.
- **Technology**: FastAPI (Python)
- **Port**: 8007
- **Integration**:
  - Called by `ingestion-service` for Markdown uploads
  - Called by `document-parsing-service` for parsed outputs (PDF/DOC/DOCX)
  - Proxies to `chunking-service` `/chunk`

#### **Embedding Service Container** (`embedding-service`)
- **Purpose**: Generates AI embeddings for documents using Google Gemini
- **Technology**: FastAPI (Python) + Google Gemini AI
- **Port**: 8001
- **Features**:
  - Document text extraction
  - AI embedding generation
  - Qdrant vector database integration
  - Semantic search capabilities
  - MinIO file access

#### **AI Agent Service Container** (`ai-agent-service`)
- **Purpose**: AI-powered customer service chatbot with document context
- **Technology**: FastAPI (Python) + Google Gemini AI
- **Port**: 8002
- **Features**:
  - Conversational AI interface
  - Document-aware responses
  - Context retrieval from Qdrant
  - Multi-workspace support
  - Source attribution

#### **Document Parsing Service Container** (`document-parsing-service`)
- **Purpose**: Parses PDF/DOC/DOCX into clean Markdown using Docling; triggers redaction/chunking
- **Technology**: FastAPI (Python) + Docling (+ optional IBM models)
- **Port**: 8005
- **Features**:
  - Asynchronous parse jobs (non-blocking)
  - S3 download/upload (original and parsed artifacts)
  - Parser selection via env (`PDF_PARSER_VERSION`, `DOCX_PARSER_VERSION`)
  - Error propagation via ingestion status updates (status=3)

#### **Chunking Service Container** (`chunking-service`)
- **Purpose**: Chunks Markdown into embedding-ready payloads; stores canonical payloads in S3 and forwards to embedding
- **Technology**: FastAPI (Python) + LangChain splitters
- **Port**: 8006
- **Features**:
  - Section/paragraph/sentence + token-window strategy
  - UUID v4 `chunk_id`, provenance, hashing
  - Canonical payload storage in S3 (`payload/{workspace_id}/{chunk_id}.json`)
  - Forwards to embedding service `/embed-chunk`

### 🗄️ Infrastructure Services

#### **PostgreSQL Container** (`db`)
- **Purpose**: Primary relational database for metadata storage
- **Technology**: PostgreSQL 13
- **Port**: 5432
- **Features**:
  - User management
  - Workspace management
  - File metadata storage
  - ACID compliance
  - Persistent data storage

#### **Qdrant Container** (`qdrant`)
- **Purpose**: Vector database for AI embeddings and semantic search
- **Technology**: Qdrant v1.9.0
- **Port**: 6333
- **Features**:
  - High-dimensional vector storage
  - Semantic similarity search
  - Data integrity protection (WAL sync)
  - Graceful shutdown support
  - Persistent storage

#### **MinIO Container** (`minio`)
- **Purpose**: S3-compatible object storage for document files
- **Technology**: MinIO
- **Ports**: 9000 (API), 9001 (Console)
- **Features**:
  - S3-compatible API
  - Web-based management console
  - File versioning
  - Access control
  - Persistent storage

### 🛠️ Management & Operations Services

#### **Management Service Container** (`management-service`)
- **Purpose**: Orchestrates graceful shutdowns and service management
- **Technology**: FastAPI (Python) + Docker SDK
- **Port**: 8004
- **Features**:
  - **Graceful Shutdown Orchestration**: Stops services in proper dependency order
  - **Service Health Monitoring**: Real-time status of all containers
  - **Container Management**: Start, stop, restart individual services
  - **Docker Integration**: Direct access to Docker daemon via socket
  - **REST API**: Programmatic control and monitoring
  - **CLI Interface**: User-friendly command-line tool (`quickresolve-cli.py`)

#### **Snapshot Service Container** (`snapshot-service`)
- **Purpose**: Continuous backup and restoration of Qdrant data
- **Technology**: FastAPI (Python)
- **Port**: 8003
- **Features**:
  - **Automatic Snapshots**: Every 5 minutes (configurable)
  - **Dual Backup Methods**: API snapshots + filesystem backups
  - **Retention Management**: Keeps latest 10 snapshots (configurable)
  - **Easy Restoration**: One-command snapshot restoration
  - **REST API**: Programmatic snapshot management
  - **CLI Interface**: User-friendly backup operations
  - **Health Monitoring**: Built-in health checks

### 🔄 Data Generation Service

#### **Data Generator Container** (`data-generator`)
- **Purpose**: Generates sample customer service data for testing
- **Technology**: Python + Google Gemini AI
- **Profile**: `generate-data` (optional)
- **Features**:
  - AI-generated sample tickets
  - Realistic customer service scenarios
  - Configurable data volume
  - Testing and development support

## 🛑 Graceful Shutdown

QuickResolve includes a containerized management service that handles graceful shutdowns automatically:

### Using the CLI Tool
```bash
# Show all services status
python quickresolve-cli.py status

# Graceful shutdown with confirmation
python quickresolve-cli.py shutdown

# Force shutdown (no confirmation)
python quickresolve-cli.py shutdown --force

# Restart a specific service
python quickresolve-cli.py restart qdrant
```

### Using the Management API
```bash
# Check service health
curl http://localhost:8004/health

# Graceful shutdown
curl -X POST http://localhost:8004/shutdown

# Get service status
curl http://localhost:8004/services
```

### Why Use Graceful Shutdown?

- **Data Integrity**: Ensures Qdrant flushes all pending writes to disk
- **No Corruption**: Prevents corrupted WAL (Write-Ahead Log) files
- **Proper Order**: Stops services in reverse dependency order
- **Extended Timeouts**: Gives Qdrant extra time to complete operations
- **Containerized**: Fully integrated with Docker ecosystem

### Manual Shutdown (Not Recommended)
If you must stop services manually:
```bash
# Stop with grace period
docker-compose stop -t 30

# Check service status
docker-compose ps
```

**⚠️ Warning**: Avoid using `docker-compose down` or force-killing containers as this may corrupt Qdrant data files.

## 📸 Continuous Snapshots

QuickResolve includes a containerized snapshot service that automatically backs up Qdrant data:

### Using the CLI Tool
```bash
# Create a new snapshot
python quickresolve-cli.py snapshot create

# List available snapshots
python quickresolve-cli.py snapshot list

# Download a snapshot
python quickresolve-cli.py snapshot download qdrant_snapshot_20231201_120000.tar.gz

# Restore from snapshot
python quickresolve-cli.py snapshot restore qdrant_snapshot_20231201_120000.tar.gz

# Clean up old snapshots
python quickresolve-cli.py snapshot cleanup
```

### Using the Snapshot API
```bash
# Check snapshot service health
curl http://localhost:8003/health

# Create snapshot
curl -X POST http://localhost:8003/snapshots

# List snapshots
curl http://localhost:8003/snapshots

# Download snapshot
curl http://localhost:8003/snapshots/qdrant_snapshot_20231201_120000.tar.gz -o backup.tar.gz
```

### Automatic Snapshots
The snapshot service runs automatically in the background:
- **Interval**: Every 5 minutes (configurable)
- **Retention**: Latest 10 snapshots (configurable)
- **Methods**: API snapshots with filesystem fallback
- **Storage**: Persistent volume mounted to host

**Features:**
- **Containerized**: Fully integrated with Docker ecosystem
- **REST API**: Programmatic access to all snapshot operations
- **Health Monitoring**: Built-in health checks and monitoring
- **Automatic Cleanup**: Configurable retention policies
- **Easy Restoration**: One-command snapshot restoration

## 🔍 API Endpoints

### Ingestion Service (Port 8000)

- `POST /users/` - Create a new user
- `GET /users/?username={username}` - Get user by username
- `POST /workspaces/` - Create a new workspace
- `GET /workspaces/?name={name}&owner_id={id}` - Get workspace by name and owner
- `POST /uploadfile/?workspace_id={id}` - Upload a file
- `GET /file-content/?s3_key={key}` - Get file content from S3

### Redaction Service (Port 8007)

- `GET /health` - Service health check
- `POST /redact` - Currently proxies to the chunking service `/chunk`. Intended to redact/mask PII before chunking in future versions.
  - Body: `{ s3_key, file_id, workspace_id, original_filename, document_parser_version }`

### Embedding Service (Port 8001)

- `POST /embed/` - Generate embeddings for a file
- `GET /search/?query={query}&workspace_id={id}&top_k={k}` - Search documents
- `POST /embed-chunk` - Embed a single chunk by `workspace_id` and `chunk_id`

### AI Agent Service (Port 8002)

- `GET /health` - Service health check
- `GET /workspaces` - Get available workspaces
- `POST /conversation` - Handle conversation with AI assistant
- `GET /search/{workspace_id}` - Search documents in specific workspace

### Snapshot Service (Port 8003)

- `GET /health` - Service health check
- `POST /snapshots` - Create new snapshot
- `GET /snapshots` - List all snapshots
- `GET /snapshots/{filename}` - Download specific snapshot
- `POST /snapshots/{filename}/restore` - Restore from snapshot
- `DELETE /snapshots/{filename}` - Delete snapshot
- `POST /cleanup` - Clean up old snapshots

### Management Service (Port 8004)

- `GET /health` - Overall system health check
- `GET /services` - Get status of all services
- `GET /services/{name}` - Get specific service status
- `POST /shutdown` - Graceful shutdown of all services
- `POST /services/start` - Start services
- `POST /services/{name}/restart` - Restart specific service
- `GET /services/{name}/health` - Check service health

### Document Parsing Service (Port 8005)

- `GET /health` - Service health check
- `GET /supported-types` - List supported file types
- `POST /parse/` - Enqueue parse job
  - Body: `{ s3_key, file_id, workspace_id, original_filename }`

### Chunking Service (Port 8006)

- `GET /health` - Service health check
- `POST /chunk` - Chunk a parsed Markdown into S3-backed canonical payloads and trigger embedding
  - Body: `{ s3_key, file_id, workspace_id, original_filename, document_parser_version }`

## 🖥️ Command Line Interface (CLI)

QuickResolve includes a powerful CLI tool (`quickresolve-cli.py`) for easy management:

### Installation
```bash
# No installation required - runs directly with Python
python quickresolve-cli.py --help
```

### CLI Commands

#### **Service Management**
```bash
# Check status of all services
python quickresolve-cli.py status

# Get detailed status of specific service
python quickresolve-cli.py status qdrant

# Restart a service
python quickresolve-cli.py restart ai-agent-service

# Start all services
python quickresolve-cli.py start
```

#### **Graceful Shutdown**
```bash
# Graceful shutdown with confirmation
python quickresolve-cli.py shutdown

# Force shutdown (no confirmation)
python quickresolve-cli.py shutdown --force
```

#### **Snapshot Management**
```bash
# Create a new snapshot
python quickresolve-cli.py snapshot create

# List all snapshots
python quickresolve-cli.py snapshot list

# Download a snapshot
python quickresolve-cli.py snapshot download qdrant_snapshot_20231201_120000.tar.gz

# Restore from snapshot
python quickresolve-cli.py snapshot restore qdrant_snapshot_20231201_120000.tar.gz

# Clean up old snapshots
python quickresolve-cli.py snapshot cleanup
```

### CLI Features
- **User-Friendly**: Simple commands with helpful output
- **Error Handling**: Graceful error handling with clear messages
- **JSON Output**: Structured output for programmatic use
- **Help System**: Built-in help for all commands
- **Service Discovery**: Automatically finds and manages all containers

## 🏗️ Project Structure

```
quickresolve/
├── frontend/                 # Web interface
│   ├── index.html           # Main HTML file
│   ├── script.js            # Frontend JavaScript
│   ├── style.css            # Styling
│   ├── chat.html            # Chat interface
│   ├── chat.js              # Chat functionality
│   ├── chat-style.css       # Chat styling
│   ├── Dockerfile           # Frontend container
│   └── nginx.conf           # Nginx configuration
├── ingestion-service/        # File upload and metadata service
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database models and connection
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── redaction-service/        # PII redaction proxy (pass-through today)
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── embedding-service/        # AI embedding generation service
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── ai-agent-service/        # AI customer service chatbot
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Service container
│   ├── test_main.py         # Unit tests
│   └── README.md            # Service documentation
├── document-parsing-service/ # PDF/DOC/DOCX → Markdown parsing
│   ├── main.py              # FastAPI application
│   ├── Dockerfile           # Conditional installs via parser version
│   └── src/parsers/         # Parser classes (complete/fast)
├── chunking-service/         # Markdown chunking to canonical payloads
│   ├── main.py              # FastAPI application
│   └── src/chunkers/        # Chunker classes and strategy
├── data-generator/          # Sample data generation
│   ├── generate_dataset.py  # Data generation script
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Generator container
├── snapshot-service/        # Containerized snapshot service
│   ├── Dockerfile          # Snapshot service container
│   ├── requirements.txt    # Python dependencies
│   ├── snapshot_service.py # Main snapshot service
│   └── config.py           # Snapshot service configuration
├── management-service/      # Containerized management service
│   ├── Dockerfile          # Management service container
│   ├── requirements.txt    # Python dependencies
│   ├── management_service.py # Main management service
│   └── config.py           # Management service configuration
├── customer_service_data/   # Generated sample data
├── minio_data/              # MinIO storage data
├── qdrant_storage/          # Qdrant vector database data
├── qdrant_snapshots/        # Snapshot backups
├── docker-compose.yml       # Service orchestration
├── quickresolve-cli.py     # CLI tool for management
├── start-chat.sh           # Linux/Mac startup script
├── start-chat.bat          # Windows startup script
└── README.md               # This file
```

## 🔧 Development

### Running Services Individually

```bash
# Start only specific services
docker-compose up -d qdrant db minio
docker-compose up -d ingestion-service
docker-compose up -d redaction-service
docker-compose up -d embedding-service
docker-compose up -d frontend
```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f ingestion-service
docker-compose logs -f redaction-service
docker-compose logs -f embedding-service
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: This will delete all data)
docker-compose down -v
```

## 🧪 Testing

### Manual Testing

1. Start the application with sample data:
   ```bash
   docker-compose --profile generate-data up -d
   ```

2. Upload the generated sample files through the web interface

3. Test search functionality with queries like:
   - "password reset"
   - "billing issue"
   - "login problem"

### API Testing

Use tools like curl or Postman to test the API endpoints:

```bash
# Create a user
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser"}'

# Search documents
curl "http://localhost:8001/search/?query=password%20reset&workspace_id=1&top_k=5"
```

## 🔒 Security Considerations

- The application is designed for development/testing use
- In production, consider:
  - Adding authentication and authorization
  - Using HTTPS
  - Implementing rate limiting
  - Securing API keys and credentials
  - Adding input validation and sanitization

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**: Check if required ports are available
2. **Database connection errors**: Ensure PostgreSQL container is running
3. **Embedding generation fails**: Verify your Gemini API key is valid
4. **File upload fails**: Check MinIO configuration and bucket creation

### Debug Commands

```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs [service-name]

# Access service containers
docker-compose exec [service-name] bash

# Check database connection
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Open an issue on the repository

---

**Note**: This is a development/testing environment. For production use, additional security measures and optimizations should be implemented.
