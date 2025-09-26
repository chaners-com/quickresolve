#!/usr/bin/env python3

"""
Redaction service.

Redaction perates on chunks to maximize safety and parallelism.

Mask PII types with deterministic rules (always enabled in v1):
  - Emails in text and in URLs (including `mailto:`)
  - IPv4 and IPv6 (validated)
  - Credit card candidates (Luhn-validated)
  - IBAN (mod-97 check)
  - E.164 phones (conservative pattern)
Deterministic per-document suffix:
  - Use HMAC-SHA256 with a per-document key derived as
    `HMAC(service_secret, file_id)`; token suffix
    for each matched value is `HMAC(per_doc_key, value)[:suffix_bytes]`
    in hex. This guarantees consistent suffixes for the same value within
    a document even when chunks are processed in parallel
    and across instances, without in-memory maps.
  - If later we need cross-file stability within a workspace,
    derive `per_workspace_key = HMAC(service_secret, workspace_id)`
    and switch derivation accordingly. For now, per-document only.
Produce output Markdown preserving structure.

"""

import json
import os
from typing import Optional

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# OpenTelemetry (metrics + traces)
from observability_utils import (
    start_process_resource_metrics,
    stop_resource_sampler,
)
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
from src.redaction_strategies import (
    PatternBasedRedactionStrategy,
    RedactionConfig,
)
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

app = FastAPI(
    title="Redaction Service",
    description=(
        "Chunk-level redaction: accepts chunk_id/workspace_id, "
        "updates payload in S3 in place."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICE_BASE = os.getenv(
    "REDACTION_SERVICE_URL", "http://redaction-service:8007"
)

# S3 configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3 = None

# Broker/Manager for consuming redact tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/redact",
    health_url=f"{SERVICE_BASE}/health",
    topic="redact",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("REDACT_MAX_CONCURRENT", "20"))
)

# OpenTelemetry init
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "redaction-service")
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
OTEL_SDK_DISABLED = os.getenv("OTEL_SDK_DISABLED", "true").lower() == "true"
OTEL_METRICS_ENABLED = (
    os.getenv("OTEL_METRICS_ENABLED", "false").lower() == "true"
)

_resource = Resource.create({"service.name": OTEL_SERVICE_NAME})
if not OTEL_SDK_DISABLED:
    _tracer_provider = TracerProvider(resource=_resource)
    _tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(_tracer_provider)
_tracer = trace.get_tracer(__name__)
if OTEL_METRICS_ENABLED and not OTEL_SDK_DISABLED:
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
RED_REQS = _meter.create_counter("redaction_requests_total")
RED_DONE = _meter.create_counter("redaction_completions_total")
RED_ERRS = _meter.create_counter("redaction_errors_total")
RED_LAT = _meter.create_histogram("redaction_latency_seconds", unit="s")
QWAIT = _meter.create_histogram("queue_wait_seconds", unit="s")
ACK_LAG = _meter.create_histogram("ack_lag_seconds", unit="s")

S3_GET_LAT = _meter.create_histogram("s3_download_latency_seconds", unit="s")
S3_PUT_LAT = _meter.create_histogram("s3_upload_latency_seconds", unit="s")
S3_GET_ERRS = _meter.create_counter("s3_get_errors_total")
S3_PUT_ERRS = _meter.create_counter("s3_put_errors_total")
PAYLOAD_IN = _meter.create_counter("payload_bytes_in_total", unit="By")
PAYLOAD_OUT = _meter.create_counter("payload_bytes_out_total", unit="By")

# Strategy info gauge
_strategy_name = "pattern-based"
_strategy_version = getattr(PatternBasedRedactionStrategy, "VERSION", "1")


def _strategy_info_cb(options):
    try:
        return [
            Observation(
                1,
                {
                    "service": OTEL_SERVICE_NAME,
                    "strategy": _strategy_name,
                    "version": _strategy_version,
                },
            )
        ]
    except Exception:
        return []


RED_STRATEGY_INFO = _meter.create_observable_gauge(
    "redaction_strategy_info", callbacks=[_strategy_info_cb]
)


class RedactRequest(BaseModel):
    workspace_id: int
    chunk_id: str
    task_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "redaction"}


@app.on_event("startup")
async def on_startup():
    global s3
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
    await manager.start()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


async def _process_redaction(req: RedactRequest) -> dict:
    # 1) Fetch canonical payload from S3
    key = f"{req.workspace_id}/payloads/{req.chunk_id}.json"
    _ta = None
    obj = None
    try:
        _ta = float(os.times().elapsed) if hasattr(os, "times") else None
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    except Exception as e:
        S3_GET_ERRS.add(
            1,
            attributes={
                "service": OTEL_SERVICE_NAME,
                "error": type(e).__name__,
            },
        )
        raise
    payload_bytes = obj["Body"].read()
    if _ta is not None:
        try:
            S3_GET_LAT.record(
                (float(os.times().elapsed) - _ta),
                attributes={"service": OTEL_SERVICE_NAME},
                context=otel_context.get_current(),
            )
        except Exception:
            pass
    PAYLOAD_IN.add(
        len(payload_bytes),
        attributes={"service": OTEL_SERVICE_NAME, "stage": "redact"},
    )
    payload = json.loads(payload_bytes.decode("utf-8"))

    # 2) Apply pattern-based strategy
    text = payload.get("content")
    if text is None:
        text = ""
    elif not isinstance(text, str):
        text = str(text)
    file_id_value = payload.get("file_id")
    file_id = str(file_id_value) if file_id_value is not None else ""

    # Load service secret and suffix bytes
    secret_raw = os.getenv("HMAC_KEY_DEFAULT", "")
    try:
        suffix_bytes = max(
            0, int(os.getenv("REDACTION_SUFFIX_BYTES", "1") or "1")
        )
    except Exception:
        suffix_bytes = 1
    cfg = RedactionConfig(
        suffix_bytes=suffix_bytes,
        file_id=file_id,
        workspace_id=req.workspace_id,
        service_secret=(secret_raw.encode("utf-8") if secret_raw else None),
    )
    strategy = PatternBasedRedactionStrategy()
    result = strategy.redact(text, cfg)

    # 3) Update payload in place and write back to S3
    payload["content"] = result.text
    version = payload.get("version") or {}
    if not isinstance(version, dict):
        version = {}
    version["redaction_strategy"] = getattr(
        PatternBasedRedactionStrategy, "VERSION", "pattern-based-1"
    )
    payload["version"] = version

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    _tb = None
    try:
        _tb = float(os.times().elapsed) if hasattr(os, "times") else None
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
    except Exception as e:
        S3_PUT_ERRS.add(
            1,
            attributes={
                "service": OTEL_SERVICE_NAME,
                "error": type(e).__name__,
            },
        )
        raise
    if _tb is not None:
        try:
            S3_PUT_LAT.record(
                (float(os.times().elapsed) - _tb),
                attributes={"service": OTEL_SERVICE_NAME},
                context=otel_context.get_current(),
            )
        except Exception:
            pass
    PAYLOAD_OUT.add(
        len(body), attributes={"service": OTEL_SERVICE_NAME, "stage": "redact"}
    )

    # Return output; TaskManager will ACK with this payload
    return {
        "chunk_id": req.chunk_id,
        "workspace_id": req.workspace_id,
        "metrics": result.metrics,
    }


@app.post("/redact")
async def consume(input: dict):
    service_attrs = {"service": OTEL_SERVICE_NAME}
    RED_REQS.add(1, attributes=service_attrs)

    async def work(payload: dict) -> dict:
        # queue wait if provided
        sched_ms = payload.get("scheduled_start_timestamp")
        t_start_ms = payload.get("_task_received_ts_ms")
        if isinstance(sched_ms, (int, float)) and isinstance(
            t_start_ms, (int, float)
        ):
            try:
                qwait = max(
                    0.0, (float(t_start_ms) - float(sched_ms)) / 1000.0
                )
                QWAIT.record(
                    qwait,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
            except Exception:
                pass

        sampler_handle = None
        with _tracer.start_as_current_span("redact") as span:
            if RESOURCE_SAMPLER_ENABLED:
                sampler_handle = start_process_resource_metrics(
                    meter=_meter,
                    base_attributes=service_attrs,
                    stage="redact",
                    hz=RESOURCE_SAMPLER_HZ,
                    enable_gpu=GPU_METRICS_ENABLED,
                )
            try:
                req = RedactRequest(
                    workspace_id=payload["workspace_id"],
                    chunk_id=payload["chunk_id"],
                    task_id=payload.get("task_id"),
                )
                result = await _process_redaction(req)
                RED_DONE.add(1, attributes={**service_attrs, "status_code": 2})
                return result
            except Exception as e:
                RED_ERRS.add(
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

    t0 = float(os.times().elapsed) if hasattr(os, "times") else None
    result = await manager.execute_task(input, work)
    # ack lag
    if isinstance(t0, (int, float)):
        try:
            ACK_LAG.record(
                max(0.0, (float(os.times().elapsed) - float(t0))),
                attributes={"stage": "redact", **service_attrs},
                context=otel_context.get_current(),
            )
        except Exception:
            pass
    return result
