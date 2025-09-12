FROM python:3.9-slim

WORKDIR /app

COPY search-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY search-service/main.py .
COPY search-service/__init__.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"] 