#!/usr/bin/env python3
"""
Embedding Service
Embeds chunks and writes vector files to S3 under vectors/.
Does not store vectors in payload JSON.
"""

import asyncio
import json
import os
import time
from typing import Optional, Union

import boto3
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from observability_utils import (
    start_process_resource_metrics,
    stop_resource_sampler,
)

# OpenTelemetry (metrics + traces)
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.metrics import Observation, get_meter, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager


class FileInfo(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int


class SearchResult(BaseModel):
    id: Union[str, int]
    payload: Optional[dict] = None
    score: float


class EmbedChunkRequest(BaseModel):
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

GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
embedding_model = "models/embedding-001"

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

# Broker/Manager
SERVICE_BASE = os.getenv(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8001"
)
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/embed-chunk",
    health_url=f"{SERVICE_BASE}/health",
    topic="embed",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("EMBED_MAX_CONCURRENT", "20"))
)

# OpenTelemetry init
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "embedding-service")
OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"
)
OTEL_METRICS_EXPORT_INTERVAL_MS = int(
    os.getenv("OTEL_METRICS_EXPORT_INTERVAL_MS", "10000")
)
RESOURCE_SAMPLER_ENABLED = (
    os.getenv("RESOURCE_SAMPLER_ENABLED", "true").lower() == "true"
)
RESOURCE_SAMPLER_HZ = float(os.getenv("RESOURCE_SAMPLER_HZ", "1"))
GPU_METRICS_ENABLED = (
    os.getenv("GPU_METRICS_ENABLED", "false").lower() == "true"
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

# Instruments
EMB_REQS = _meter.create_counter("embedding_requests_total")
EMB_DONE = _meter.create_counter("embedding_completions_total")
EMB_ERRS = _meter.create_counter("embedding_errors_total")
EMB_LAT = _meter.create_histogram("embedding_latency_seconds", unit="s")
QWAIT = _meter.create_histogram("queue_wait_seconds", unit="s")
ACK_LAG = _meter.create_histogram("ack_lag_seconds", unit="s")

S3_GET_LAT = _meter.create_histogram("s3_download_latency_seconds", unit="s")
S3_PUT_LAT = _meter.create_histogram("s3_upload_latency_seconds", unit="s")
S3_PUT_VEC_LAT = _meter.create_histogram(
    "s3_upload_vector_latency_seconds", unit="s"
)
PAYLOAD_IN = _meter.create_counter("payload_bytes_in_total", unit="By")
PAYLOAD_OUT = _meter.create_counter("payload_bytes_out_total", unit="By")
VECTOR_OUT = _meter.create_counter("vector_bytes_out_total", unit="By")
S3_GET_ERRS = _meter.create_counter("s3_get_errors_total")
S3_PUT_ERRS = _meter.create_counter("s3_put_errors_total")

EMB_VECTORS = _meter.create_counter("embedding_vectors_total")
VEC_DIM = _meter.create_histogram("embedding_vector_dim")
VEC_DIM_MISMATCH = _meter.create_counter("embedding_vector_dim_mismatch_total")

# Resource usage metrics handled by shared utility

# Info-style model gauge


def _model_info_callback(options):
    try:
        return [
            Observation(
                1,
                {
                    "name": embedding_model,
                    "version": embedding_model,
                    "service": OTEL_SERVICE_NAME,
                },
            )
        ]
    except Exception:
        return []


EMB_MODEL_INFO = _meter.create_observable_gauge(
    "embedding_model_info", callbacks=[_model_info_callback]
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "embedding-service"}


@app.on_event("startup")
def startup_event():
    # Advertise readiness for one task slot
    asyncio.get_event_loop().create_task(manager.start())


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


def _retry_backoff_delays(max_attempts: int = 3) -> list[float]:
    return [0.5 * (2**i) for i in range(max_attempts)]


@app.post("/embed-chunk")
async def consume(input: dict):
    service_attrs = {
        "service": OTEL_SERVICE_NAME,
    }
    EMB_REQS.add(1, attributes=service_attrs)

    async def work(payload: dict) -> dict:
        t0 = time.time()
        with _tracer.start_as_current_span("embed") as span:
            sampler_handle = None
            if RESOURCE_SAMPLER_ENABLED:
                sampler_handle = start_process_resource_metrics(
                    meter=_meter,
                    base_attributes=service_attrs,
                    stage="embed",
                    hz=RESOURCE_SAMPLER_HZ,
                    enable_gpu=GPU_METRICS_ENABLED,
                )
            try:
                req = EmbedChunkRequest(
                    workspace_id=payload["workspace_id"],
                    chunk_id=payload["chunk_id"],
                    task_id=payload.get("task_id"),
                )

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

                # Retrieve canonical chunk payload from S3
                payload_key = (
                    f"{req.workspace_id}/payloads/{req.chunk_id}.json"
                )
                _ta = time.time()
                try:
                    obj = s3.get_object(Bucket=S3_BUCKET, Key=payload_key)
                except Exception as e:
                    S3_GET_ERRS.add(
                        1,
                        attributes={
                            **service_attrs,
                            "error": type(e).__name__,
                        },
                    )
                    raise
                payload_bytes = obj["Body"].read()
                S3_GET_LAT.record(
                    time.time() - _ta,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                PAYLOAD_IN.add(
                    len(payload_bytes),
                    attributes={"stage": "embed", **service_attrs},
                )
                chunk_payload = json.loads(payload_bytes.decode("utf-8"))

                text = chunk_payload.get("content", "")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Empty content in payload")

                vec = genai.embed_content(
                    model=embedding_model,
                    content=text,
                    task_type="retrieval_document",
                )["embedding"]

                # Count and dimension
                try:
                    EMB_VECTORS.add(
                        1,
                        attributes={
                            **service_attrs,
                            "embedding_model": embedding_model,
                        },
                    )
                    VEC_DIM.record(
                        len(vec or []),
                        attributes=service_attrs,
                        context=otel_context.get_current(),
                    )
                    if len(vec or []) != 768:
                        VEC_DIM_MISMATCH.add(1, attributes=service_attrs)
                except Exception:
                    pass

                # Ensure version.embedding_model is populated
                version = chunk_payload.get("version") or {}
                if isinstance(version, dict):
                    version["embedding_model"] = embedding_model
                    chunk_payload["version"] = version

                # Persist payload (without vector) to keep metadata updated
                body = json.dumps(chunk_payload).encode("utf-8")
                last_err: Exception | None = None
                _tb = time.time()
                for delay in _retry_backoff_delays(3):
                    try:
                        s3.put_object(
                            Bucket=S3_BUCKET, Key=payload_key, Body=body
                        )
                        break
                    except Exception as e:
                        last_err = e
                        S3_PUT_ERRS.add(
                            1,
                            attributes={
                                **service_attrs,
                                "error": type(e).__name__,
                            },
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Failed to persist payload metadata to S3: {last_err}"
                    )
                S3_PUT_LAT.record(
                    time.time() - _tb,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                PAYLOAD_OUT.add(
                    len(body),
                    attributes={"stage": "embed", **service_attrs},
                )

                # Write vector file separately
                # under vectors/<chunk_id>.vec as JSON array
                vec_key = f"{req.workspace_id}/vectors/{req.chunk_id}.vec"
                vec_body = json.dumps(vec).encode("utf-8")
                last_err = None
                _tc = time.time()
                for delay in _retry_backoff_delays(3):
                    try:
                        s3.put_object(
                            Bucket=S3_BUCKET,
                            Key=vec_key,
                            Body=vec_body,
                            ContentType="application/octet-stream",
                        )
                        break
                    except Exception as e:
                        last_err = e
                        S3_PUT_ERRS.add(
                            1,
                            attributes={
                                **service_attrs,
                                "error": type(e).__name__,
                            },
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Failed to persist vector to S3: {last_err}"
                    )
                S3_PUT_VEC_LAT.record(
                    time.time() - _tc,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                VECTOR_OUT.add(
                    len(vec_body),
                    attributes={"stage": "embed", **service_attrs},
                )

                result = {
                    "success": True,
                    "chunk_id": chunk_payload.get("chunk_id"),
                    "workspace_id": req.workspace_id,
                    "_end_ts": time.time(),
                }
                EMB_DONE.add(1, attributes={**service_attrs, "status_code": 2})
                return result
            except Exception as e:
                EMB_ERRS.add(
                    1, attributes={**service_attrs, "error": type(e).__name__}
                )
                span.record_exception(e)
                raise
            finally:
                if RESOURCE_SAMPLER_ENABLED and sampler_handle is not None:
                    try:
                        stop_resource_sampler(sampler_handle)
                    except Exception:
                        pass
                EMB_LAT.record(
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
            attributes={"stage": "embed", **service_attrs},
            context=otel_context.get_current(),
        )
    return result
