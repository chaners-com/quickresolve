FROM python:3.11-slim

WORKDIR /app

COPY index-document-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared task libraries
COPY libs/task_broker_client /app/libs/task_broker_client
COPY libs/task_manager /app/libs/task_manager
RUN pip install -e /app/libs/task_broker_client && \
    pip install -e /app/libs/task_manager

COPY index-document-service/main.py .

EXPOSE 8011

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"] 