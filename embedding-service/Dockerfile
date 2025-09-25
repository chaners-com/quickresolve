FROM python:3.9-slim

WORKDIR /app

COPY embedding-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared libraries
COPY libs/task_broker_client /app/libs/task_broker_client
COPY libs/task_manager /app/libs/task_manager
COPY libs/observability_utils /app/libs/observability_utils
RUN pip install -e /app/libs/task_broker_client && \
    pip install -e /app/libs/task_manager && \
    pip install -e /app/libs/observability_utils

COPY embedding-service/main.py .
COPY embedding-service/__init__.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"] 