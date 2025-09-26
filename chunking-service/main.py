#!/usr/bin/env python3
"""
Chunking Service
Chunk markdown files using different chunking strategies.
"""

import asyncio
import json
import os
from typing import List, Optional

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Observability utils (resource sampler)
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
from src.chunking_strategies import markdown_paragraph_sentence as mps
from src.chunking_strategies.markdown_paragraph_sentence import (
    MarkdownParagraphSentenceChunkingStrategy,
)
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

# App setup
app = FastAPI(
    title="Chunking Service", description="Chunking with single strategy"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
SERVICE_BASE = os.getenv(
    "CHUNKING_SERVICE_URL", "http://chunking-service:8006"
)

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "chunking-service")
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
INCLUDE_FILE_ID = (
    os.getenv("CHUNK_METRICS_INCLUDE_FILE_ID", "false").lower() == "true"
)
OTEL_SDK_DISABLED = os.getenv("OTEL_SDK_DISABLED", "true").lower() == "true"
OTEL_METRICS_ENABLED = (
    os.getenv("OTEL_METRICS_ENABLED", "false").lower() == "true"
)

# Clients
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)

# Task broker client/manager for consuming chunk tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/chunk",
    health_url=f"{SERVICE_BASE}/health",
    topic="chunk",
)
manager = TaskManager(
    broker, max_concurrent=int(os.getenv("CHUNK_MAX_CONCURRENT", "20"))
)

# OTel init (traces + metrics)
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
CH_REQS = _meter.create_counter("chunking_requests_total")
CH_DONE = _meter.create_counter("chunking_completions_total")
CH_ERRS = _meter.create_counter("chunking_errors_total")
CH_LAT = _meter.create_histogram("chunking_latency_seconds", unit="s")
QWAIT = _meter.create_histogram("queue_wait_seconds", unit="s")
ACK_LAG = _meter.create_histogram("ack_lag_seconds", unit="s")

S3_GET_LAT = _meter.create_histogram("s3_download_latency_seconds", unit="s")
S3_PUT_LAT = _meter.create_histogram("s3_upload_latency_seconds", unit="s")

PAYLOAD_IN = _meter.create_counter("payload_bytes_in_total", unit="By")
PAYLOAD_OUT = _meter.create_counter("payload_bytes_out_total", unit="By")

CH_COUNT = _meter.create_counter("chunking_chunks_total")
CH_SIZE_CHARS = _meter.create_histogram("chunking_chunk_size_chars")
CH_CHARS_OUT_PER_DOC = _meter.create_histogram("chunking_chars_out_per_doc")
CH_TOKENS = _meter.create_histogram("chunking_chunk_tokens")
CH_OVERLAP_CHARS_TOTAL = _meter.create_counter("chunking_overlap_chars_total")
CH_OVERLAP_FRAC = _meter.create_histogram("chunking_overlap_fraction")
CH_OVERLAP_TOKENS_TOTAL = _meter.create_counter(
    "chunking_overlap_tokens_total"
)
CH_OVERLAP_TOKENS_FRAC = _meter.create_histogram(
    "chunking_overlap_tokens_fraction"
)

# Strategy info gauge
_strategy_name = "markdown_paragraph_sentence"
_strategy_version = getattr(mps, "STRATEGY_VERSION", "unknown")


def _strategy_info_cb(options):
    try:
        return [
            Observation(
                1,
                {
                    "service": OTEL_SERVICE_NAME,
                    "name": _strategy_name,
                    "version": _strategy_version,
                },
            )
        ]
    except Exception:
        return []


STRATEGY_INFO = _meter.create_observable_gauge(
    "chunking_strategy_info", callbacks=[_strategy_info_cb]
)


class ChunkRequest(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: Optional[str] = None
    document_parser_version: Optional[str] = None
    task_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chunking"}


@app.on_event("startup")
async def on_startup():
    await manager.start()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


async def _s3_get_text(bucket: str, key: str) -> str:
    obj = await asyncio.to_thread(s3.get_object, Bucket=bucket, Key=key)
    body = await asyncio.to_thread(obj["Body"].read)
    return body.decode("utf-8")


async def _s3_put_json(bucket: str, key: str, data_bytes: bytes) -> None:
    await asyncio.to_thread(
        s3.put_object,
        Bucket=bucket,
        Key=key,
        Body=data_bytes,
        ContentType="application/json",
    )


async def _put_json_with_metrics(
    bucket: str, key: str, data_bytes: bytes, service_attrs: dict
) -> None:
    _t = asyncio.get_event_loop().time()
    await _s3_put_json(bucket, key, data_bytes)
    try:
        S3_PUT_LAT.record(
            asyncio.get_event_loop().time() - _t,
            attributes=service_attrs,
            context=otel_context.get_current(),
        )
        PAYLOAD_OUT.add(
            len(data_bytes), attributes={"stage": "chunk", **service_attrs}
        )
    except Exception:
        pass


async def _process_chunk(req: ChunkRequest) -> dict:
    service_attrs = {
        "service": OTEL_SERVICE_NAME,
    }

    # 1) Download markdown from S3
    _ta = asyncio.get_event_loop().time()
    markdown_text = await _s3_get_text(S3_BUCKET, req.s3_key)
    try:
        S3_GET_LAT.record(
            asyncio.get_event_loop().time() - _ta,
            attributes=service_attrs,
            context=otel_context.get_current(),
        )
        PAYLOAD_IN.add(
            len(markdown_text.encode("utf-8")),
            attributes={"stage": "chunk", **service_attrs},
        )
    except Exception:
        pass

    # 2) Chunk using the strategy
    chunker = MarkdownParagraphSentenceChunkingStrategy()
    all_chunks = chunker.chunk(
        text=markdown_text,
        file_id=req.file_id,
        workspace_id=req.workspace_id,
        s3_key=req.s3_key,
        document_parser_version=req.document_parser_version,
    )

    # Aggregate per-document metrics
    total_chars = 0
    total_tokens = 0
    overlap_tokens_total = 0

    domain = (all_chunks[0].get("domain") if all_chunks else "") or "unknown"
    document_type = (
        all_chunks[0].get("document_type") if all_chunks else ""
    ) or "unknown"
    language = (
        all_chunks[0].get("language") if all_chunks else ""
    ) or "unknown"

    doc_attrs = {
        **service_attrs,
        "name": _strategy_name,
        "version": _strategy_version,
        "domain": domain,
        "document_type": document_type,
        "language": language,
    }
    if INCLUDE_FILE_ID:
        doc_attrs["file_id"] = req.file_id

    # Per-chunk observations
    for d in all_chunks:
        content = d.get("content") or ""
        size_chars = len(content)
        tokens = int(d.get("tokens") or 0)
        overlap_tokens = int(d.get("overlap_tokens") or 0)
        total_chars += size_chars
        total_tokens += max(0, tokens)
        overlap_tokens_total += max(0, overlap_tokens)
        try:
            CH_SIZE_CHARS.record(
                size_chars,
                attributes=doc_attrs,
                context=otel_context.get_current(),
            )
            if tokens > 0:
                CH_TOKENS.record(
                    tokens,
                    attributes=doc_attrs,
                    context=otel_context.get_current(),
                )
        except Exception:
            pass

    try:
        CH_COUNT.add(len(all_chunks), attributes=doc_attrs)
        CH_CHARS_OUT_PER_DOC.record(
            total_chars,
            attributes=doc_attrs,
            context=otel_context.get_current(),
        )
        if total_tokens > 0:
            # Overlap (tokens)
            CH_OVERLAP_TOKENS_TOTAL.add(
                overlap_tokens_total, attributes=doc_attrs
            )
            CH_OVERLAP_TOKENS_FRAC.record(
                float(overlap_tokens_total) / float(max(1, total_tokens)),
                attributes=doc_attrs,
                context=otel_context.get_current(),
            )
            # Estimate overlap chars from tokens ratio
            avg_chars_per_token = float(total_chars) / float(
                max(1, total_tokens)
            )
            overlap_chars_est = int(
                avg_chars_per_token * float(overlap_tokens_total)
            )
            CH_OVERLAP_CHARS_TOTAL.add(overlap_chars_est, attributes=doc_attrs)
            CH_OVERLAP_FRAC.record(
                float(overlap_chars_est) / float(max(1, total_chars)),
                attributes=doc_attrs,
                context=otel_context.get_current(),
            )
    except Exception:
        pass

    # 3) Save chunk JSONs to S3 (measure per put)
    put_tasks: List[asyncio.Task] = []
    for d in all_chunks:
        key = f"{req.workspace_id}/payloads/{d['chunk_id']}.json"
        payload_bytes = json.dumps(d, ensure_ascii=False).encode("utf-8")
        put_tasks.append(
            _put_json_with_metrics(
                S3_BUCKET, key, payload_bytes, service_attrs
            )
        )
    if put_tasks:
        await asyncio.gather(*put_tasks)

    # Return output for ACK
    return {"chunks": all_chunks, "_end_ts": asyncio.get_event_loop().time()}


@app.post("/chunk")
async def consume(input: dict):
    service_attrs = {
        "service": OTEL_SERVICE_NAME,
    }
    CH_REQS.add(1, attributes=service_attrs)

    async def work(payload: dict) -> dict:
        t0 = asyncio.get_event_loop().time()
        # queue wait if provided
        sched_ms = payload.get("scheduled_start_timestamp")
        start_ms = int(t0 * 1000)
        if isinstance(sched_ms, (int, float)):
            try:
                qwait = max(0.0, (float(sched_ms) - float(start_ms)) / 1000.0)
                QWAIT.record(
                    qwait,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
            except Exception:
                pass

        sampler_handle = None
        with _tracer.start_as_current_span("chunk") as span:
            if RESOURCE_SAMPLER_ENABLED:
                sampler_handle = start_process_resource_metrics(
                    meter=_meter,
                    base_attributes=service_attrs,
                    stage="chunk",
                    hz=RESOURCE_SAMPLER_HZ,
                    enable_gpu=GPU_METRICS_ENABLED,
                )
            try:
                req = ChunkRequest(
                    s3_key=payload["s3_key"],
                    file_id=payload["file_id"],
                    workspace_id=payload["workspace_id"],
                    original_filename=payload.get("original_filename"),
                    document_parser_version=payload.get(
                        "document_parser_version"
                    ),
                    task_id=payload.get("task_id"),
                )

                result = await _process_chunk(req)
                CH_DONE.add(1, attributes={**service_attrs, "status_code": 2})
                return result
            except Exception as e:
                CH_ERRS.add(
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
                CH_LAT.record(
                    asyncio.get_event_loop().time() - t0,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )

    result = await manager.execute_task(input, work)
    # Observe ack lag if the worker returned end timestamp
    end_ts = result.get("_end_ts") if isinstance(result, dict) else None
    if isinstance(end_ts, (int, float)):
        try:
            ACK_LAG.record(
                max(0.0, asyncio.get_event_loop().time() - float(end_ts)),
                attributes={"stage": "chunk", **service_attrs},
                context=otel_context.get_current(),
            )
        except Exception:
            pass
    return result
