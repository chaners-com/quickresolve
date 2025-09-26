FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY redaction-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared task libraries
COPY libs/task_broker_client /app/libs/task_broker_client
COPY libs/task_manager /app/libs/task_manager
COPY libs/observability_utils /app/libs/observability_utils
RUN pip install -e /app/libs/task_broker_client && \
    pip install -e /app/libs/task_manager && \
    pip install -e /app/libs/observability_utils

COPY redaction-service/main.py .
COPY redaction-service/src ./src

EXPOSE 8007

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"] 