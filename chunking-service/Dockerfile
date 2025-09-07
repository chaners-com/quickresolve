FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared task libraries
COPY libs/task_broker_client /app/libs/task_broker_client
COPY libs/task_manager /app/libs/task_manager
RUN pip install -e /app/libs/task_broker_client && \
    pip install -e /app/libs/task_manager

COPY main.py .
COPY src ./src

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"] 