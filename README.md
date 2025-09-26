# QuickResolve

A comprehensive AI-powered document intelligence platform built with modern microservices architecture, featuring advanced semantic search, intelligent document parsing, and conversational AI capabilities powered by Google Gemini AI and vector storage with Qdrant.

## Project Status

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2.30-black.svg)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18.3+-blue.svg)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.9+-green.svg)](https://qdrant.tech/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-green.svg)](https://github.com/features/actions)

**Services**: 8 microservices | **Ports**: 12+ endpoints | **AI Models**: Google Gemini | **Database**: PostgreSQL + Qdrant | **Storage**: MinIO S3

## Security Update (Latest)

**Next.js Security Patch Applied**: Successfully upgraded Next.js from 14.2.5 to 14.2.30 to resolve [CVE-2024-XXXXX: Authorization Bypass in Next.js Middleware](https://github.com/vercel/next.js/security/advisories/GHSA-xxxx-xxxx-xxxx). This vulnerability could have allowed attackers to bypass middleware authorization checks.

**What was fixed:**
- ✅ Next.js upgraded to secure version 14.2.30
- ✅ eslint-config-next updated to 14.2.30 for consistency
- ✅ Container rebuilt and deployed with patched version
- ✅ Dependabot alert #10 resolved

## Overview

QuickResolve is an enterprise-grade document intelligence platform that transforms how organizations manage, search, and interact with their document repositories. Built with a scalable microservices architecture, it combines cutting-edge AI technologies including Google Gemini AI for semantic understanding, advanced document parsing with Docling, intelligent chunking strategies, and a conversational AI agent for natural language document queries. The system automatically processes documents in multiple formats (PDF, DOC, DOCX, Markdown), generates contextual embeddings, and provides lightning-fast semantic search with source attribution. Perfect for knowledge management, customer service automation, research platforms, and enterprise document workflows.

## Languages & Frameworks

### **Backend Technologies**
- **Python 3.11+**: Core microservices and AI integration
- **FastAPI**: High-performance web framework for APIs
- **SQLAlchemy**: Database ORM and connection management
- **Pydantic**: Data validation and serialization

### **Frontend Technologies**
- **HTML5/CSS3**: Modern web standards and responsive design
- **Vanilla JavaScript (ES6+)**: Interactive frontend functionality
- **Next.js 14.2.30**: React-based landing page framework (security patched)
- **React 18**: Component-based UI library
- **TypeScript**: Type-safe JavaScript development
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animation and motion library

### **AI & Machine Learning**
- **Google Gemini AI**: Advanced language models for embeddings and chat
- **Docling**: Intelligent document parsing and conversion
- **LangChain**: Document chunking and processing strategies
- **Vector Search**: High-dimensional similarity search algorithms

### **Infrastructure & DevOps**
- **Docker**: Containerization and deployment
- **Docker Compose**: Multi-service orchestration
- **PostgreSQL**: Relational database management
- **OpenTelemetry, OTel Collector → Tempo + Mimir → Grafana**: Observability Stack
- **Qdrant**: Vector database for embeddings
- **MinIO**: S3-compatible object storage
- **Nginx**: Web server and reverse proxy

### **Development Tools**
- **Black**: Python code formatting
- **isort**: Import statement organization
- **flake8**: Code linting and style checking
- **bandit**: Security vulnerability scanning
- **GitHub Actions**: CI/CD automation
- **Dependabot**: Automated dependency updates

## Architecture

The application consists of the following microservices:

### Core Services
- **Frontend** (`frontend/`): Web interface for file upload, search, and AI chat
- **Landing Page** (`landing-next/`): Modern Next.js landing page with Tailwind CSS and Framer Motion
- **Ingestion Service** (`ingestion-service/`): Handles file uploads and metadata management
- **Task Service** (`task-service/`): General-purpose task queue/dispatcher with HTTP workers registry
- **Index Document Service** (`index-document-service/`): Orchestrates multi-step indexing pipelines
- **Document Parsing Service** (`document-parsing-service/`): Parses PDF/DOC/DOCX into Markdown using Docling
- **Chunking Service** (`chunking-service/`): Chunks Markdown into embedding-ready payloads
- **Redaction Service** (`redaction-service/`): Redacts/masks PII in parsed Markdown before
 chunking
- **Embedding Service** (`embedding-service/`): Generates embeddings using Gemini AI
- **Indexing Service** (`indexing-service/`): Index embeddings.
- **AI Agent Service** (`ai-agent-service/`): AI-powered customer service chatbot
- **Data Generator** (`data-generator/`): Generates sample customer service tickets for testing

### Infrastructure Services
- **PostgreSQL**: Stores user, workspace, and file metadata
- **Qdrant**: Vector database for storing and searching embeddings
- **MinIO**: S3-compatible object storage for file storage
* **OTel-collector**: Collects, processes, and exports observability data.
* **Tempo**: Distributed tracing backend for observability.
* **Mimir**: Horizontally scalable metrics storage system.
* **Grafana**: Visualization platform for metrics and logs.

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Landing Page**: Next.js 14.2.30, React 18, TypeScript, Tailwind CSS, Framer Motion
- **Database**: PostgreSQL
- **Vector Database**: Qdrant
- **Object Storage**: MinIO
- **Observability***: OpenTelemetry, OTel Collector → Tempo + Mimir → Grafana
- **AI/ML**: Google Gemini AI; IBM models for document parsing
- **Containerization**: Docker & Docker Compose
- **Code Quality**: Black, isort, flake8, bandit
- **CI/CD**: GitHub Actions with automated testing and security checks

## Prerequisites

Before running QuickResolve, ensure you have:

- Docker and Docker Compose installed
- A Google Gemini API key
- At least 4GB of available RAM
- Ports 8080, 8090, 8000, 8001, 8002, 8005, 8006, 8007, 5432, 6333, 9000, 9001 available

## Environment Variables

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

# Enable metrics. Default: OTEL_SDK_DISABLED=true and OTEL_METRICS_ENABLED= false
# OTEL_SDK_DISABLED=false
# OTEL_METRICS_ENABLED=true
```

### Required API Keys

- **Google Gemini API Key**: Required for AI functionality. Get yours at [Google AI Studio](https://makersuite.google.com/app/apikey)

### Environment Setup Steps

1. **Copy the example file**: `cp .env.example .env`
2. **Edit the .env file**: Update all placeholder values with your actual configuration
3. **Never commit .env**: The .env file is already in .gitignore for security

## Quick Start

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
- **Landing Page**: http://localhost:8090
- **Chat Interface**: http://localhost:8080/chat
- **MinIO Console**: http://localhost:9001
- **Ingestion Service API**: http://localhost:8000
- **Task Service API**: http://localhost:8010
- **Index Document Service API**: http://localhost:8011
- **Document Parsing Service API**: http://localhost:8005
- **Chunking Service API**: http://localhost:8006
- **Redaction Service API**: http://localhost:8007
- **Embedding Service API**: http://localhost:8001
- **Indexing Service API**: http://localhost:8010
- **AI Agent Service API**: http://localhost:8002
- **Qdrant**: http://localhost:6333
- **OTel-Collector**: http://localhost:4317 (OTLP gRP) http://localhost:4318 (OTLP HTTP)
- **Tempo**: http://localhost:3200
- **Mimir**: http://localhost:9009
- **Grafana**: http://localhost:3000

## Usage Guide

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

## Container Architecture & Services

QuickResolve uses a microservices architecture with 8 main containers, each serving a specific purpose:

### Core Application Services

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

#### **Landing Page Container** (`landing-next`)
- **Purpose**: Modern, responsive landing page showcasing QuickResolve features
- **Technology**: Next.js 14, React 18, TypeScript, Tailwind CSS, Framer Motion
- **Port**: 8090
- **Features**:
  - Professional landing page design
  - Smooth animations and transitions
  - Responsive mobile-first design
  - Modern UI/UX patterns

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

#### **Task Service Container** (`task-service`)
- **Purpose**: General-purpose task queue and HTTP dispatcher; central status store
- **Technology**: FastAPI (Python) + SQLAlchemy
- **Port**: 8010
- **Features**:
  - Enqueue tasks via `POST /task`
  - Poll status via `GET /task/{id}` and `GET /task/{id}/status`
  - Update status/output via `PUT /task/{id}`
  - HTTP worker routing via registry (see `task-service/registry.py`)
  - CORS enabled for browser polling

#### **Index Document Service Container** (`index-document-service`)
- **Purpose**: Orchestrates indexing pipeline steps (parse → redact → chunk → embed)
- **Technology**: FastAPI (Python)
- **Port**: 8011
- **Features**:
  - Sequential step execution with retries
  - Fan-out `embed` per chunk with semaphore-limited concurrency
  - Root task status updates on success/failure

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
  - MinIO file access

  #### **Indexing Service Container** (`indexing-service`)
- **Purpose**: Index embeddings into Qdrant database.
- **Technology**: FastAPI (Python) + Qdrant client
- **Port**: 8010
- **Features**:
  - Qdrant vector database integration

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


### Infrastructure Services

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

#### **OTel-Collector** (`otel-collector`)
- **Purpose**: Collects, processes, and exports observability data.
- **Technology**: OpenTelemetry Collector
- **Ports**: 4317 (OTLP gRP) 4318 (OTLP HTTP)

#### **Tempo** (`tempo`)
- **Purpose**: Distributed tracing backend for observability.
- **Technology**: Tempo
- **Ports**: 3200

#### **Mimir** (`mimir`)
- **Purpose**: Horizontally scalable metrics storage system.
- **Technology**: Mimir
- **Ports**: 9009

#### **Grafana** (`grafana`)
- **Purpose**: Visualization platform for metrics and logs.
- **Technology**: Grafana
- **Ports**: 3000

### Data Generation Service

#### **Data Generator Container** (`data-generator`)
- **Purpose**: Generates sample customer service data for testing
- **Technology**: Python + Google Gemini AI
- **Profile**: `generate-data` (optional)
- **Features**:
  - AI-generated sample tickets
  - Realistic customer service scenarios
  - Configurable data volume
  - Testing and development support





## API Endpoints

### Ingestion Service (Port 8000)

- `GET /health` - Service health check
- `POST /uploadfile` (202) - Accepts `workspace_id` query param and file form field; schedules S3 upload and creates an index-document task; returns Location header for task status
- `GET /file-content/?s3_key={key}` - Retrieve file content from S3
- Users/Workspaces:
  - `POST /users/` (201)
  - `GET /users/?username={username}`
  - `POST /workspaces/` (201)
  - `GET /workspaces/?name={name}&owner_id={id}`
  - `GET /workspaces/all`

### Task Service (Port 8010)

- `GET /health` - Service health check
- `POST /task` (202) - Create a task; Location header points to `/task/{id}/status`
- `GET /task/{task_id}` - Get full task details
- `GET /task/{task_id}/status` - Get task status snapshot
- `PUT /task/{task_id}` - Update task fields (status_code, status, progress, output, state, scheduled_start_timestamp)
- Consumers registry:
  - `PUT /consumer` - Upsert consumer (endpoint_url, health_url, topic, ready)
  - `DELETE /consumer` - Remove consumer

### Document Parsing Service (Port 8005)

- `GET /health` - Service health check
- `GET /supported-types` - Supported file types
- `POST /parse` - Run parse job: `{ s3_key, file_id, workspace_id, original_filename }`

### Chunking Service (Port 8006)

- `GET /health` - Service health check
- `POST /chunk` - Chunk parsed/redacted Markdown into canonical payloads; input: `{ s3_key, file_id, workspace_id, original_filename, document_parser_version }`

### Redaction Service (Port 8007)

- `GET /health` - Service health check
- `POST /redact` - Redact payload; input: `{ s3_key, file_id, workspace_id, original_filename, document_parser_version }`

### Embedding Service (Port 8001)

- `GET /health` - Service health check
- `POST /embed-chunk` - Embed a single chunk by `{ workspace_id, chunk_id }`

### Indexing Service (Port 8010)

- `GET /health` - Service health check
- `POST /index-chunk` - Index a single chunk: pulls payload from S3 and upserts vector + payload into Qdrant

### AI Agent Service (Port 8002)

- `GET /health` - Service health check
- `GET /workspaces` - List available workspaces (from ingestion)
- `POST /conversation` - Agent conversation
- `GET /search/{workspace_id}` - Search documents in a workspace


## Project Structure

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
├── landing-next/            # Modern Next.js landing page
│   ├── app/                 # Next.js app directory
│   ├── public/              # Static assets
│   ├── package.json         # Node.js dependencies
│   ├── Dockerfile           # Landing page container
│   └── tailwind.config.ts   # Tailwind CSS configuration
├── ingestion-service/        # File upload and metadata service
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database models and connection
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── task-service/             # Task queue/dispatcher and status API
│   ├── main.py              # FastAPI application
│   ├── registry.py          # HTTP worker routes
│   ├── database.py          # SQLAlchemy models & session
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── index-document-service/   # Indexing pipeline orchestrator
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── document-parsing-service/ # PDF/DOC/DOCX → Markdown parsing
│   ├── main.py              # FastAPI application
│   ├── Dockerfile           # Conditional installs via parser version
│   └── src/parsers/         # Parser classes (complete/fast)
├── redaction-service/        # Redaction service
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── chunking-service/         # Markdown chunking to canonical payloads
│   ├── main.py              # FastAPI application
│   └── src/                 # Chunking strategies
├── embedding-service/        # AI embedding generation service
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── indexing-service/         # Upserts vectors to Qdrant
│   ├── main.py              # FastAPI application
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
├── customer_service_data/   # Generated sample data
├── minio_data/              # MinIO storage data
├── qdrant_storage/          # Qdrant vector database data
├── qdrant_snapshots/        # Snapshot backups
├── .github/                 # GitHub configuration and workflows
│   ├── workflows/           # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/      # Issue templates
│   └── dependabot.yml       # Dependency updates
├── docker-compose.yml       # Service orchestration
├── pyproject.toml          # Python tool configuration (Black, isort)
├── .bandit                 # Security linting configuration
├── libs/                    # Shared internal libraries
│   ├── task_broker_client/  # Broker client used by services
│   ├── task_manager/        # Manager for consumer readiness & task execution
│   └── observability_utils/ # Resource sampler and OTel helpers
├── docs/                    # Documentation
│   ├── observability/       # Service metrics specs and Grafana guide
│   │   └── grafana-user-guide.md
│   ├── task-service.png
│   └── index-document-pipeline.png
├── start-chat.sh           # Linux/Mac startup script
├── start-chat.bat          # Windows startup script
├── CHANGELOG.md            # Project changelog
└── README.md               # This file
```


## Indexer and Task Orchestration

### Overview
The indexing pipeline is orchestrated via `task-service` and driven by the `index-document-service`. A file upload to `ingestion-service` creates an `index-document` task with a definition that lists the steps to run. Each step is executed sequentially and the output of each becomes the input of the next. If a step named `embed` is present, the indexer fans out one `embed` task per chunk in parallel with a controlled concurrency limit.

### End-to-end flow
- **Ingestion** (`ingestion-service`):
  - `POST /uploadfile?workspace_id={id}` buffers the upload to a temp file, schedules an S3 upload in the background, and immediately creates an `index-document` task in `task-service`.
  - Responds `202 Accepted` with a `Location` header pointing to the task status URL (no response body).
- **Task creation** (`task-service`):
  - Receives `index-document` creation request and enqueues it.
  - The dispatcher delivers the task to `index-document-service` (HTTP worker per registry entry).
- **Index orchestration** (`index-document-service`):
  - Loads the pipeline steps from the task input and runs each step.
  - For `embed`, spawns one task per chunk and waits until all finish (or any fails).
  - Updates the `index-document` root task status (0=waiting, 1=processing, 2=completed, 3=failed) with a status message.

### Index definition (example)
```json
{
  "description": "Indexing document <file-uuid>",
  "s3_key": "<workspace-id>/<file-uuid>.<ext>",
  "file_id": "<file-uuid>",
  "workspace_id": 1,
  "original_filename": "document.pdf",
  "steps": [
    { "name": "parse-document" },
    { "name": "chunk" },
    { "name": "redact" },
    { "name": "embed" },
    { "name": "index" }
  ]
}
```
Note: For Markdown uploads, `ingestion-service` omits the `parse-document` step.

### Step inputs and outputs
- **parse-document** (`document-parsing-service`):
  - Input: `{ s3_key, file_id, workspace_id, original_filename }`
  - Output: `{ parsed_s3_key, document_parser_version, images: [...] }`
- **chunk** (`chunking-service`):
  - Input: `{ s3_key: redacted_s3_key | parsed_s3_key, file_id, workspace_id, original_filename, document_parser_version }`
  - Output: `{ chunks: [ { chunk_id, ...payloadFields } ] }`
- **redact** (`redaction-service`):
  - Input: `{ s3_key: parsed_s3_key, file_id, workspace_id, original_filename, document_parser_version }`
  - Output: `{ redacted_s3_key, file_id, workspace_id }`
- **embed** (`embedding-service`):
  - Fan-out: one task per chunk
  - Input per task: `{ chunk_id, workspace_id }`
- **index** (`indexing-service`):
  - Fan-out: one task per chunk
  - Input per task: `{ chunk_id, workspace_id }`
  - Side effect: Stores/upserts embedding + payload in Qdrant

### Task registry (routing)
`task-service/registry.py` maps task names to HTTP endpoints:
- `index-document` → `index-document-service /`
- `parse-document` → `document-parsing-service /parse`
- `chunk` → `chunking-service /chunk`
- `redact` → `redaction-service /redact`
- `embed` → `embedding-service /embed-chunk`
- `index` → `indexing-service /index-chunk`

### Polling and status
- Each worker step is created via `task-service` (`status code` 0 (waiting)) and polled by the orchestrator (`status code` ` (processing)) until it reaches `status_code` 2 (success) or 3 (failure).
- The index document service retries a failed step up to 3 times (with backoff). If still failing, it marks the root `index-document` task as failed.

### Client integration
- Upload a file via `ingestion-service` and read the `Location` header from the 202 response:
  - Example: `Location: http://localhost:8010/task/<task-id>/status`
- Poll the task status URL from the browser (CORS enabled on `task-service`).
- When the root `index-document` task reaches `status_code=2`, the document is fully indexed and searchable.

## Observability & Metrics (OTel)

By default, observability is disabled to reduce overhead:
- `OTEL_SDK_DISABLED=true`
- `OTEL_METRICS_ENABLED=false`

To enable metrics and traces per service, set these in your environment (e.g., `.env`) or directly in `docker-compose.yml` for the services you want:

```env
OTEL_SDK_DISABLED=false
OTEL_METRICS_ENABLED=true
```

Notes:
- Ensure the observability stack is running: `otel-collector`, `mimir`, `tempo`, and `grafana` are defined in `docker-compose.yml`.
- Resource sampler (CPU/RAM/IO/GPU) follows the same kill switch and is controlled by:
  - `RESOURCE_SAMPLER_ENABLED=true|false` (default true)
  - `RESOURCE_SAMPLER_HZ=1` (sampling frequency)
  - `GPU_METRICS_ENABLED=true|false` (default false)
- See detailed guidance, PromQL examples, and Grafana tips in `observability/README.md`.

## Development

### Code Quality Tools

QuickResolve uses several tools to maintain code quality:

- **Black**: Code formatting (line length: 79, Python 3.11+)
- **isort**: Import sorting (Black-compatible profile)
- **flake8**: Linting and style checking
- **bandit**: Security vulnerability scanning
- **GitHub Actions**: Automated CI/CD pipeline

### Running Services Individually

```bash
# Start only specific services
docker-compose up -d qdrant db minio
docker-compose up -d ingestion-service
docker-compose up -d redaction-service
docker-compose up -d embedding-service
docker-compose up -d frontend
docker-compose up -d landing-next
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

## Testing

### Automated Testing

QuickResolve includes a comprehensive CI/CD pipeline:

- **Automated Testing**: Runs on every push and pull request
- **Code Quality Checks**: Black, isort, flake8, bandit
- **Security Scanning**: Automated vulnerability detection
- **Coverage Reports**: Test coverage tracking
- **Docker Builds**: Automated container builds

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

## Security Considerations

- The application is designed for development/testing use
- In production, consider:
  - Adding authentication and authorization
  - Using HTTPS
  - Implementing rate limiting
  - Securing API keys and credentials
  - Adding input validation and sanitization
- Automated security scanning with bandit
- Regular dependency updates via Dependabot

## Troubleshooting

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure code quality tools pass
5. Test thoroughly
6. Submit a pull request

### Development Standards

- Follow Black formatting (79 character line length)
- Use isort for import organization
- Pass all flake8 linting checks
- Ensure bandit security checks pass
- Write tests for new functionality
- Update documentation as needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Open an issue on the repository
4. Check the comprehensive documentation

---

**Note**: This is a development/testing environment. For production use, additional security measures and optimizations should be implemented.
