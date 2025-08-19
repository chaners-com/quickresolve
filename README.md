# QuickResolve

A comprehensive AI-powered document intelligence platform built with modern microservices architecture, featuring advanced semantic search, intelligent document parsing, and conversational AI capabilities powered by Google Gemini AI and vector storage with Qdrant.

## 📊 Project Status

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

## 🔒 Security Update (Latest)

**Next.js Security Patch Applied**: Successfully upgraded Next.js from 14.2.5 to 14.2.30 to resolve [CVE-2024-XXXXX: Authorization Bypass in Next.js Middleware](https://github.com/vercel/next.js/security/advisories/GHSA-xxxx-xxxx-xxxx). This vulnerability could have allowed attackers to bypass middleware authorization checks.

**What was fixed:**
- ✅ Next.js upgraded to secure version 14.2.30
- ✅ eslint-config-next updated to 14.2.30 for consistency
- ✅ Container rebuilt and deployed with patched version
- ✅ Dependabot alert #10 resolved

## 🚀 Overview

QuickResolve is an enterprise-grade document intelligence platform that transforms how organizations manage, search, and interact with their document repositories. Built with a scalable microservices architecture, it combines cutting-edge AI technologies including Google Gemini AI for semantic understanding, advanced document parsing with Docling, intelligent chunking strategies, and a conversational AI agent for natural language document queries. The system automatically processes documents in multiple formats (PDF, DOC, DOCX, Markdown), generates contextual embeddings, and provides lightning-fast semantic search with source attribution. Perfect for knowledge management, customer service automation, research platforms, and enterprise document workflows.

## 🛠️ Languages & Frameworks

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

## 🏗️ Architecture

The application consists of the following microservices:

### Core Services
- **Frontend** (`frontend/`): Web interface for file upload, search, and AI chat
- **Landing Page** (`landing-next/`): Modern Next.js landing page with Tailwind CSS and Framer Motion
- **Ingestion Service** (`ingestion-service/`): Handles file uploads and metadata management
- **Redaction Service** (`redaction-service/`): Redacts/masks PII in parsed Markdown before chunking
- **Embedding Service** (`embedding-service/`): Generates embeddings using Gemini AI
- **AI Agent Service** (`ai-agent-service/`): AI-powered customer service chatbot
- **Document Parsing Service** (`document-parsing-service/`): Parses PDF/DOC/DOCX into Markdown using Docling
- **Chunking Service** (`chunking-service/`): Chunks Markdown into embedding-ready payloads
- **Data Generator** (`data-generator/`): Generates sample customer service tickets for testing

### Infrastructure Services
- **PostgreSQL**: Stores user, workspace, and file metadata
- **Qdrant**: Vector database for storing and searching embeddings
- **MinIO**: S3-compatible object storage for file storage

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Landing Page**: Next.js 14.2.30, React 18, TypeScript, Tailwind CSS, Framer Motion
- **Database**: PostgreSQL
- **Vector Database**: Qdrant
- **Object Storage**: MinIO
- **AI/ML**: Google Gemini AI; IBM models for document parsing
- **Containerization**: Docker & Docker Compose
- **Code Quality**: Black, isort, flake8, bandit
- **CI/CD**: GitHub Actions with automated testing and security checks

## 📋 Prerequisites

Before running QuickResolve, ensure you have:

- Docker and Docker Compose installed
- A Google Gemini API key
- At least 4GB of available RAM
- Ports 8080, 8090, 8000, 8001, 8002, 8005, 8006, 8007, 5432, 6333, 9000, 9001 available

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
- **Landing Page**: http://localhost:8090
- **Chat Interface**: http://localhost:8080/chat
- **MinIO Console**: http://localhost:9001
- **Ingestion Service API**: http://localhost:8000
- **Embedding Service API**: http://localhost:8001
- **AI Agent Service API**: http://localhost:8002
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

QuickResolve uses a microservices architecture with 8 main containers, each serving a specific purpose:

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


- `POST /cleanup` - Clean up old snapshots

### Management Service (Port 8004)

- `GET /health` - Overall system health check


### Document Parsing Service (Port 8005)

- `GET /health` - Service health check
- `GET /supported-types` - List supported file types
- `POST /parse/` - Enqueue parse job
  - Body: `{ s3_key, file_id, workspace_id, original_filename }`

### Chunking Service (Port 8006)

- `GET /health` - Service health check
- `POST /chunk` - Chunk a parsed Markdown into S3-backed canonical payloads and trigger embedding
  - Body: `{ s3_key, file_id, workspace_id, original_filename, document_parser_version }`



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
├── start-chat.sh           # Linux/Mac startup script
├── start-chat.bat          # Windows startup script
├── CHANGELOG.md            # Project changelog
└── README.md               # This file
```

## 🔧 Development

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

## 🧪 Testing

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

## 🔒 Security Considerations

- The application is designed for development/testing use
- In production, consider:
  - Adding authentication and authorization
  - Using HTTPS
  - Implementing rate limiting
  - Securing API keys and credentials
  - Adding input validation and sanitization
- Automated security scanning with bandit
- Regular dependency updates via Dependabot

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

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Open an issue on the repository
4. Check the comprehensive documentation

---

**Note**: This is a development/testing environment. For production use, additional security measures and optimizations should be implemented.
