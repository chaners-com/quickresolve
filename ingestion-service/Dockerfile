FROM python:3.9-slim

WORKDIR /app

COPY ingestion-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion-service/main.py .
COPY ingestion-service/database.py .
COPY ingestion-service/__init__.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 