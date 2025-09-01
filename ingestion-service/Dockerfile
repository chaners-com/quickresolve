FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY ingestion-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion-service/main.py .
COPY ingestion-service/__init__.py .
# Shared DB models (also mounted as a volume in docker-compose for dev)
COPY backend/db ./backend/db

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
