# QuickResolve

A modern document search and retrieval system built with microservices architecture, featuring semantic search capabilities powered by Google Gemini AI and vector storage with Qdrant.

## 🚀 Overview

QuickResolve is a full-stack application that allows users to upload documents, automatically generate embeddings using Google's Gemini AI, and perform semantic search across their documents. The system is designed with a microservices architecture for scalability and maintainability.

## 🏗️ Architecture

The application consists of the following microservices:

### Core Services
- **Frontend** (`frontend/`): Web interface for file upload and search
- **Ingestion Service** (`ingestion-service/`): Handles file uploads and metadata management
- **Embedding Service** (`embedding-service/`): Generates embeddings using Gemini AI
- **Data Generator** (`data-generator/`): Generates sample customer service tickets for testing

### Infrastructure Services
- **PostgreSQL**: Stores user, workspace, and file metadata
- **Qdrant**: Vector database for storing and searching embeddings
- **MinIO**: S3-compatible object storage for file storage

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Database**: PostgreSQL
- **Vector Database**: Qdrant
- **Object Storage**: MinIO
- **AI/ML**: Google Gemini AI
- **Containerization**: Docker & Docker Compose

## 📋 Prerequisites

Before running QuickResolve, ensure you have:

- Docker and Docker Compose installed
- A Google Gemini API key
- At least 4GB of available RAM
- Ports 8080, 8000, 8001, 5432, 6333, 9000, 9001 available

## 🔧 Environment Variables

Create a `.env` file in the root directory with the following variables:

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
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd quickresolve
```

### 2. Create Environment File

Create a `.env` file with your configuration (see Environment Variables section above).

### 3. Start the Application

```bash
# Start all services
docker-compose up -d

# Or start with data generation
docker-compose --profile generate-data up -d
```

### 4. Access the Application

- **Frontend**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **Ingestion Service API**: http://localhost:8000
- **Embedding Service API**: http://localhost:8001
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

### 3. Generate Sample Data

To generate sample customer service tickets for testing:

```bash
docker-compose --profile generate-data up data-generator
```

This will create 100 sample tickets in the `customer_service_data/` directory.

## 🔍 API Endpoints

### Ingestion Service (Port 8000)

- `POST /users/` - Create a new user
- `GET /users/?username={username}` - Get user by username
- `POST /workspaces/` - Create a new workspace
- `GET /workspaces/?name={name}&owner_id={id}` - Get workspace by name and owner
- `POST /uploadfile/?workspace_id={id}` - Upload a file
- `GET /file-content/?s3_key={key}` - Get file content from S3

### Embedding Service (Port 8001)

- `POST /embed/` - Generate embeddings for a file
- `GET /search/?query={query}&workspace_id={id}&top_k={k}` - Search documents

## 🏗️ Project Structure

```
quickresolve/
├── frontend/                 # Web interface
│   ├── index.html           # Main HTML file
│   ├── script.js            # Frontend JavaScript
│   ├── style.css            # Styling
│   ├── Dockerfile           # Frontend container
│   └── nginx.conf           # Nginx configuration
├── ingestion-service/        # File upload and metadata service
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database models and connection
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── embedding-service/        # AI embedding generation service
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Service container
├── data-generator/          # Sample data generation
│   ├── generate_dataset.py  # Data generation script
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Generator container
├── customer_service_data/   # Generated sample data
├── minio_data/              # MinIO storage data
├── qdrant_storage/          # Qdrant vector database data
├── docker-compose.yml       # Service orchestration
└── README.md               # This file
```

## 🔧 Development

### Running Services Individually

```bash
# Start only specific services
docker-compose up -d qdrant db minio
docker-compose up -d ingestion-service
docker-compose up -d embedding-service
docker-compose up -d frontend
```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f ingestion-service
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
