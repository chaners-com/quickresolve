FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tar \
    gzip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy snapshot service code
COPY snapshot_service.py .
COPY config.py .

# Create snapshot directory
RUN mkdir -p /app/snapshots

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SNAPSHOT_INTERVAL=300
ENV MAX_SNAPSHOTS=10
ENV QDRANT_URL=http://qdrant:6333
ENV COLLECTION_NAME=file_embeddings

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Run the snapshot service
CMD ["python", "snapshot_service.py"] 