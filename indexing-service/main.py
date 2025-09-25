#!/usr/bin/env python3
"""
Indexing Service
Upserts embedded chunks into Qdrant.
"""

import asyncio
import json
import os
import time
import threading
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

QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "file_embeddings")

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
RESOURCE_SAMPLER_ENABLED = os.getenv("RESOURCE_SAMPLER_ENABLED", "true").lower() == "true"
RESOURCE_SAMPLER_HZ = float(os.getenv("RESOURCE_SAMPLER_HZ", "1"))

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

# Resource usage instruments
CPU_PCT = _meter.create_histogram("process_cpu_percent", unit="%")
MEM_RSS = _meter.create_histogram("process_memory_rss_bytes", unit="By")
IO_RD_BPS = _meter.create_histogram("process_io_read_bytes_per_second", unit="By/s")
IO_WR_BPS = _meter.create_histogram("process_io_write_bytes_per_second", unit="By/s")
CPU_PCT_PEAK = _meter.create_histogram("process_cpu_percent_peak", unit="%")
MEM_RSS_PEAK = _meter.create_histogram("process_memory_rss_peak_bytes", unit="By")
IO_RD_BPS_PEAK = _meter.create_histogram("process_io_read_bps_peak", unit="By/s")
IO_WR_BPS_PEAK = _meter.create_histogram("process_io_write_bps_peak", unit="By/s")


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


def _sample_resources_thread(stop_event: threading.Event, attributes: dict, hz: float, ctx):
    import psutil  # local import to avoid import if not used
    p = psutil.Process(os.getpid())
    try:
        p.cpu_percent(None)
    except Exception:
        pass
    prev_time = time.time()
    try:
        io_prev = p.io_counters()
        rd_prev = io_prev.read_bytes
        wr_prev = io_prev.write_bytes
    except Exception:
        rd_prev = 0
        wr_prev = 0

    cpu_peak = 0.0
    mem_peak = 0
    rd_bps_peak = 0.0
    wr_bps_peak = 0.0

    interval = max(0.05, 1.0 / max(0.1, hz))
    while not stop_event.is_set():
        t1 = time.time()
        dt = max(1e-6, t1 - prev_time)
        try:
            cpu = float(p.cpu_percent(None))
        except Exception:
            cpu = 0.0
        try:
            mem = int(p.memory_info().rss)
        except Exception:
            mem = 0
        try:
            io_now = p.io_counters()
            rd = int(io_now.read_bytes)
            wr = int(io_now.write_bytes)
            rd_bps = max(0.0, (rd - rd_prev) / dt)
            wr_bps = max(0.0, (wr - wr_prev) / dt)
            rd_prev, wr_prev = rd, wr
        except Exception:
            rd_bps = 0.0
            wr_bps = 0.0

        cpu_peak = max(cpu_peak, cpu)
        mem_peak = max(mem_peak, mem)
        rd_bps_peak = max(rd_bps_peak, rd_bps)
        wr_bps_peak = max(wr_bps_peak, wr_bps)

        try:
            CPU_PCT.record(cpu, attributes=attributes, context=ctx)
            MEM_RSS.record(mem, attributes=attributes, context=ctx)
            IO_RD_BPS.record(rd_bps, attributes=attributes, context=ctx)
            IO_WR_BPS.record(wr_bps, attributes=attributes, context=ctx)
        except Exception:
            pass

        # responsive sleep
        stop_event.wait(max(0.0, interval - (time.time() - t1)))
        prev_time = t1

    try:
        CPU_PCT_PEAK.record(cpu_peak, attributes=attributes, context=ctx)
        MEM_RSS_PEAK.record(mem_peak, attributes=attributes, context=ctx)
        IO_RD_BPS_PEAK.record(rd_bps_peak, attributes=attributes, context=ctx)
        IO_WR_BPS_PEAK.record(wr_bps_peak, attributes=attributes, context=ctx)
    except Exception:
        pass


@app.post("/index-chunk")
async def consume(input: dict):
    service_attrs = {
        "service": OTEL_SERVICE_NAME,
    }
    IDX_REQS.add(1, attributes=service_attrs)

    async def work(payload: dict) -> dict:
        t0 = time.time()
        with _tracer.start_as_current_span("index") as span:
            sampler_thread = None
            stop_event = threading.Event()
            ctx = otel_context.get_current()
            res_attrs = {"stage": "index", **service_attrs}
            if RESOURCE_SAMPLER_ENABLED:
                sampler_thread = threading.Thread(
                    target=_sample_resources_thread,
                    args=(stop_event, res_attrs, RESOURCE_SAMPLER_HZ, ctx),
                    daemon=True,
                )
                sampler_thread.start()
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
                qdr_attrs = {**service_attrs, "qdrant_collection": QDRANT_COLLECTION_NAME}
                _tu = time.time()
                try:
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
                        attributes=qdr_attrs,
                        context=otel_context.get_current(),
                    )
                    UPserts.add(1, attributes=qdr_attrs)
                except Exception as qe:
                    UP_ERRS.add(1, attributes={**qdr_attrs, "error": type(qe).__name__})
                    raise

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
                if RESOURCE_SAMPLER_ENABLED:
                    try:
                        stop_event.set()
                        if sampler_thread is not None:
                            sampler_thread.join(timeout=2.0)
                    except Exception:
                        pass
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
 