#!/usr/bin/env python3
"""
Indexing Service
Upserts embedded chunks into Qdrant.
"""

import asyncio
import json
import os
import time
from typing import Optional

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# OpenTelemetry (metrics + traces)
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.metrics import get_meter, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager


class IndexChunkRequest(BaseModel):
    workspace_id: int
    chunk_id: str
    task_id: Optional[str] = None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), timeout=60)

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

# Clients
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)

QDRANT_COLLECTION_NAME = "file_embeddings"

# Broker/Manager
SERVICE_BASE = os.getenv(
    "INDEXING_SERVICE_URL", "http://indexing-service:8012"
)
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/index-chunk",
    health_url=f"{SERVICE_BASE}/health",
    topic="index",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("INDEX_MAX_CONCURRENT", "3"))
)

# OpenTelemetry init
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "indexing-service")
OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"
)
OTEL_METRICS_EXPORT_INTERVAL_MS = int(
    os.getenv("OTEL_METRICS_EXPORT_INTERVAL_MS", "10000")
)
_resource = Resource.create({"service.name": OTEL_SERVICE_NAME})
_tracer_provider = TracerProvider(resource=_resource)
_tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT))
)
trace.set_tracer_provider(_tracer_provider)
_tracer = trace.get_tracer(__name__)
_metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTLP_ENDPOINT),
    export_interval_millis=OTEL_METRICS_EXPORT_INTERVAL_MS,
)
_meter_provider = MeterProvider(
    resource=_resource, metric_readers=[_metric_reader]
)
set_meter_provider(_meter_provider)
_meter = get_meter(__name__)

# Instruments (see observability
IDX_REQS = _meter.create_counter("indexing_requests_total")
IDX_DONE = _meter.create_counter("indexing_completions_total")
IDX_ERRS = _meter.create_counter("indexing_errors_total")
IDX_LAT = _meter.create_histogram("indexing_latency_seconds", unit="s")
S3_GET_LAT = _meter.create_histogram("s3_download_latency_seconds", unit="s")
PAYLOAD_IN = _meter.create_counter("payload_bytes_in_total", unit="By")
VECTOR_IN = _meter.create_counter("vector_bytes_in_total", unit="By")
UPserts = _meter.create_counter("index_upserts_total")
UP_LAT = _meter.create_histogram("index_upsert_latency_seconds", unit="s")
UP_ERRS = _meter.create_counter("index_upsert_errors_total")
BATCH = _meter.create_histogram("index_batch_size")
VEC_DIM = _meter.create_histogram("index_vector_dim")
VEC_DIM_MISMATCH = _meter.create_counter("index_vector_dim_mismatch_total")
QWAIT = _meter.create_histogram("queue_wait_seconds", unit="s")
ACK_LAG = _meter.create_histogram("ack_lag_seconds", unit="s")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "indexing-service"}


@app.on_event("startup")
def startup_event():
    # Wait for Qdrant to be ready
    retries = 10
    while retries > 0:
        try:
            qdrant_client.get_collections()
            print("Qdrant is ready.")
            break
        except (UnexpectedResponse, Exception):
            print("Qdrant not ready, waiting...")
            import time

            time.sleep(5)
            retries -= 1

    if retries == 0:
        print("Could not connect to Qdrant. Exiting.")
        exit(1)

    try:
        qdrant_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
    except (UnexpectedResponse, Exception):
        qdrant_client.recreate_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=768, distance=models.Distance.COSINE
            ),
        )

    # Advertise readiness for one task slot
    asyncio.get_event_loop().create_task(manager.start())


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


@app.post("/index-chunk")
async def consume(input: dict):
    service_attrs = {
        "service": OTEL_SERVICE_NAME,
        "collection": QDRANT_COLLECTION_NAME,
    }
    IDX_REQS.add(1, attributes=service_attrs)

    async def work(payload: dict) -> dict:
        t0 = time.time()
        with _tracer.start_as_current_span("index") as span:
            try:
                req = IndexChunkRequest(
                    workspace_id=payload["workspace_id"],
                    chunk_id=payload["chunk_id"],
                    task_id=payload.get("task_id"),
                )
                # Retrieve payload metadata and vector from S3, then upsert
                payload_key = (
                    f"{req.workspace_id}/payloads/{req.chunk_id}.json"
                )
                _ta = time.time()
                obj = s3.get_object(Bucket=S3_BUCKET, Key=payload_key)
                payload_bytes = obj["Body"].read()
                S3_GET_LAT.record(
                    time.time() - _ta,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                PAYLOAD_IN.add(
                    len(payload_bytes),
                    attributes={"stage": "index", **service_attrs},
                )
                chunk_payload = json.loads(payload_bytes.decode("utf-8"))

                vec_key = f"{req.workspace_id}/vectors/{req.chunk_id}.vec"
                _tb = time.time()
                vec_obj = s3.get_object(Bucket=S3_BUCKET, Key=vec_key)
                vec_bytes = vec_obj["Body"].read()
                S3_GET_LAT.record(
                    time.time() - _tb,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                VECTOR_IN.add(
                    len(vec_bytes),
                    attributes={"stage": "index", **service_attrs},
                )
                try:
                    embedding = json.loads(vec_bytes.decode("utf-8"))
                except Exception:
                    # If stored in another format in the future,
                    # handle accordingly
                    raise ValueError("Invalid vector file content")

                if not isinstance(embedding, list) or not embedding:
                    raise ValueError("Missing or invalid embedding vector")

                # Optional: record vector dimension
                try:
                    VEC_DIM.record(
                        len(embedding),
                        attributes=service_attrs,
                        context=otel_context.get_current(),
                    )
                    if len(embedding) != 768:
                        VEC_DIM_MISMATCH.add(1, attributes=service_attrs)
                except Exception:
                    pass

                # Upsert to Qdrant
                _tu = time.time()
                qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=[
                        models.PointStruct(
                            id=chunk_payload.get("chunk_id"),
                            vector=embedding,
                            payload=chunk_payload,
                        )
                    ],
                    wait=False,
                )
                UP_LAT.record(
                    time.time() - _tu,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                UPserts.add(1, attributes=service_attrs)

                # Queue wait if provided
                sched_ms = payload.get("scheduled_start_timestamp")
                start_ms = int(t0 * 1000)
                if sched_ms is not None:
                    qwait = max(0.0, (sched_ms - start_ms) / 1000.0)
                    QWAIT.record(
                        qwait,
                        attributes=service_attrs,
                        context=otel_context.get_current(),
                    )

                result = {
                    "success": True,
                    "chunk_id": chunk_payload.get("chunk_id"),
                    "workspace_id": req.workspace_id,
                    "_end_ts": time.time(),
                }
                IDX_DONE.add(1, attributes={**service_attrs, "status_code": 2})
                return result
            except Exception as e:
                IDX_ERRS.add(
                    1, attributes={**service_attrs, "error": type(e).__name__}
                )
                span.record_exception(e)
                raise
            finally:
                IDX_LAT.record(
                    time.time() - t0,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )

    result = await manager.execute_task(input, work)
    # Observe ack lag if the worker returned end timestamp
    end_ts = result.get("_end_ts") if isinstance(result, dict) else None
    if isinstance(end_ts, (int, float)):
        ACK_LAG.record(
            max(0.0, time.time() - float(end_ts)),
            attributes={"stage": "index", **service_attrs},
            context=otel_context.get_current(),
        )
    return result
