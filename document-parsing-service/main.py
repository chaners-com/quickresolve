#!/usr/bin/env python3
"""
Document Parsing Service
Parses PDF/DOC/DOCX to Markdown,
Once parsed, it forwards to the chunking service.
"""

import asyncio
import os
import time

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
from src.parsers.registry import get_parser_class, warmup_parsers
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

app = FastAPI(
    title="Document Parsing Service",
    description="""Parses PDF/DOC/DOCX to Markdown,
    uploads to S3, and forwards to the redaction service (then chunking).""",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment and clients
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
PUBLIC_S3_ENDPOINT = os.getenv("PUBLIC_S3_ENDPOINT")

SERVICE_BASE = os.getenv(
    "DOCUMENT_PARSING_SERVICE_URL", "http://document-parsing-service:8005"
)

# OTel env
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "document-parsing-service")
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

s3_client = None

# Task broker client/manager for consuming parse-document tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/parse",
    health_url=f"{SERVICE_BASE}/health",
    topic="parse-document",
)

manager = TaskManager(
    broker, max_concurrent=int(os.getenv("PARSE_MAX_CONCURRENT", "1"))
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
PARSE_REQS = _meter.create_counter("parsing_requests_total")
PARSE_DONE = _meter.create_counter("parsing_completions_total")
PARSE_ERRS = _meter.create_counter("parsing_errors_total")
PARSE_LAT = _meter.create_histogram("parsing_latency_seconds", unit="s")
QWAIT = _meter.create_histogram("queue_wait_seconds", unit="s")
ACK_LAG = _meter.create_histogram("ack_lag_seconds", unit="s")

S3_GET_LAT = _meter.create_histogram("s3_download_latency_seconds", unit="s")
S3_PUT_LAT = _meter.create_histogram("s3_upload_latency_seconds", unit="s")
S3_PUT_IMG_LAT = _meter.create_histogram(
    "s3_upload_image_latency_seconds", unit="s"
)
PAYLOAD_IN = _meter.create_counter("payload_bytes_in_total", unit="By")
PAYLOAD_OUT = _meter.create_counter("payload_bytes_out_total", unit="By")
S3_GET_ERRS = _meter.create_counter("s3_get_errors_total")
S3_PUT_ERRS = _meter.create_counter("s3_put_errors_total")

DOC_BYTES_IN = _meter.create_counter("document_bytes_in_total", unit="By")
PARSED_CHARS = _meter.create_counter("parsed_chars_out_total")
PARSED_MD_BYTES = _meter.create_counter(
    "parsed_markdown_bytes_total", unit="By"
)
PARSED_PAGES = _meter.create_counter("parsed_pages_total")
PARSED_IMAGES = _meter.create_counter("parsed_images_total")
PARSED_IMAGE_BYTES = _meter.create_counter(
    "parsed_image_bytes_total", unit="By"
)

# Info-style gauge for parser version
_current_parser_version: str | None = None


def _parser_info_cb(options):
    try:
        if not _current_parser_version:
            return []
        return [
            Observation(
                1,
                {
                    "service": OTEL_SERVICE_NAME,
                    "parser_version": _current_parser_version,
                },
            )
        ]
    except Exception:
        return []


PARSER_INFO = _meter.create_observable_gauge(
    "parsing_strategy_info", callbacks=[_parser_info_cb]
)


@app.on_event("startup")
async def on_startup():
    global s3_client
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )

    await warmup_parsers()

    await manager.start()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


class ParseRequest(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: str
    task_id: str | None = None


async def _download_from_s3(key: str) -> tuple[bytes, str]:
    def _get():
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        content_type = obj.get("ContentType") or ""
        return obj["Body"].read(), content_type

    return await asyncio.to_thread(_get)


async def _upload_to_s3(
    key: str, body: bytes, content_type: str = "text/markdown"
) -> None:
    def _put():
        s3_client.put_object(
            Bucket=S3_BUCKET, Key=key, Body=body, ContentType=content_type
        )

    await asyncio.to_thread(_put)


async def _run_parse_job(request: ParseRequest) -> dict:
    started = time.time()
    print(
        f"""Parsing document {request.s3_key}
             for file {request.file_id} in workspace {request.workspace_id}"""
    )
    service_attrs = {"service": OTEL_SERVICE_NAME}
    PARSE_REQS.add(1, attributes=service_attrs)

    sampler_handle = None
    with _tracer.start_as_current_span("parse") as span:
        try:
            # Download original content (also capture content-type if set)
            _t_get = time.time()
            content_bytes, s3_content_type = await _download_from_s3(
                request.s3_key
            )
            try:
                S3_GET_LAT.record(
                    time.time() - _t_get,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                DOC_BYTES_IN.add(
                    len(content_bytes),
                    attributes={
                        **service_attrs,
                        "doc_type": (
                            request.original_filename.lower()
                            .strip()
                            .split(".")[-1]
                            if request.original_filename
                            else "unknown"
                        ),
                    },
                )
                PAYLOAD_IN.add(
                    len(content_bytes),
                    attributes={"stage": "parse", **service_attrs},
                )
            except Exception:
                pass

            # Determine extension
            # TODO: do not only rely on the extension,
            # also check the content type.
            ext = request.original_filename.lower().strip().split(".")[-1]

            # Select parser from registry by extension and content type,
            # honoring env overrides
            parser_cls = get_parser_class(ext, s3_content_type)

            if not parser_cls:
                raise ValueError(f"unsupported file type: .{ext}")

            # Build context for parser
            parse_context = {
                "workspace_id": request.workspace_id,
                "file_id": request.file_id,
                "public_s3_endpoint": PUBLIC_S3_ENDPOINT,
            }

            # Capture parser version BEFORE parse
            document_parser_version = getattr(parser_cls, "VERSION", "unknown")
            # Expose parser version via info-gauge
            global _current_parser_version
            _current_parser_version = document_parser_version
            # Start resource sampler (include file_id; GPU optionally)
            if RESOURCE_SAMPLER_ENABLED:
                sampler_handle = start_process_resource_metrics(
                    meter=_meter,
                    base_attributes={
                        "service": OTEL_SERVICE_NAME,
                        "file_id": request.file_id,
                    },
                    stage="parse",
                    hz=RESOURCE_SAMPLER_HZ,
                    enable_gpu=GPU_METRICS_ENABLED,
                )

            # Parse using the parser class
            parser_result = parser_cls.parse(content_bytes, parse_context)
            if asyncio.iscoroutine(parser_result):
                parsed_md, images = await parser_result
            else:
                parsed_md, images = parser_result

            # Minimal validation
            if not parsed_md or len(parsed_md.strip()) < int(
                os.getenv("MIN_OUTPUT_CHARS", "20")
            ):
                raise ValueError("validation failed")

            # Upload images (if any)
            # to S3 under {workspace}/parsed/{file}/images
            image_base = (
                f"{request.workspace_id}/parsed/{request.file_id}/images"
            )
            images = images or []
            for img in images:
                ext = (img.get("ext") or "png").lstrip(".")
                idx = img.get("index") or 0
                key = f"{image_base}/image-{idx}.{ext}"
                _t_put_img = time.time()
                await _upload_to_s3(
                    key, img.get("content", b""), content_type=f"image/{ext}"
                )
                try:
                    S3_PUT_IMG_LAT.record(
                        time.time() - _t_put_img,
                        attributes=service_attrs,
                        context=otel_context.get_current(),
                    )
                    PARSED_IMAGES.add(
                        1, attributes={**service_attrs, "doc_type": ext}
                    )
                    content_len = len(img.get("content", b""))
                    if content_len > 0:
                        PARSED_IMAGE_BYTES.add(
                            content_len,
                            attributes={**service_attrs, "doc_type": ext},
                        )
                except Exception:
                    pass

            parsed_bytes = parsed_md.encode("utf-8")
            parsed_s3_key = (
                f"{request.workspace_id}/parsed/{request.file_id}.md"
            )

            # Upload parsed markdown
            _t_put_md = time.time()
            await _upload_to_s3(
                parsed_s3_key, parsed_bytes, content_type="text/markdown"
            )
            try:
                S3_PUT_LAT.record(
                    time.time() - _t_put_md,
                    attributes=service_attrs,
                    context=otel_context.get_current(),
                )
                PAYLOAD_OUT.add(
                    len(parsed_bytes),
                    attributes={"stage": "parse", **service_attrs},
                )
            except Exception:
                pass

            try:
                PARSED_CHARS.add(
                    len(parsed_md),
                    attributes={
                        **service_attrs,
                        "parser_version": document_parser_version,
                        "doc_type": ext,
                    },
                )
                PARSED_MD_BYTES.add(
                    len(parsed_bytes),
                    attributes={
                        **service_attrs,
                        "parser_version": document_parser_version,
                        "doc_type": ext,
                    },
                )
                PARSE_DONE.add(
                    1, attributes={**service_attrs, "status_code": 2}
                )
            except Exception:
                pass

            return {
                "parsed_s3_key": parsed_s3_key,
                "document_parser_version": document_parser_version,
                "images": [
                    {
                        "key": (
                            f"{request.workspace_id}/parsed/"
                            f"{request.file_id}/images/"
                            f"image-{(img.get('index') or 0)}."
                            f"{(img.get('ext') or 'png').lstrip('.')}"
                        )
                    }
                    for img in (images or [])
                ],
                "_end_ts": time.time(),
            }
        except Exception as e:
            try:
                PARSE_ERRS.add(
                    1, attributes={**service_attrs, "error": type(e).__name__}
                )
            except Exception:
                pass
            span.record_exception(e)
            raise
        finally:
            if RESOURCE_SAMPLER_ENABLED and sampler_handle is not None:
                try:
                    stop_resource_sampler(sampler_handle)
                except Exception:
                    pass
            try:
                PARSE_LAT.record(
                    time.time() - started,
                    attributes={
                        **service_attrs,
                        "parser_version": _current_parser_version or "unknown",
                        "doc_type": (
                            request.original_filename.lower()
                            .strip()
                            .split(".")[-1]
                            if request.original_filename
                            else "unknown"
                        ),
                    },
                    context=otel_context.get_current(),
                )
            except Exception:
                pass


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "document-parsing-service",
        "timestamp": int(time.time()),
    }


@app.get("/supported-types")
async def get_supported_types():
    return {
        "supported_formats": [
            {"extension": ".pdf", "description": "PDF documents"},
            {"extension": ".docx", "description": "Microsoft Word documents"},
            {
                "extension": ".doc",
                "description": "Microsoft Word legacy documents",
            },
        ]
    }


@app.post("/parse")
async def consume(input: dict):
    service_attrs = {"service": OTEL_SERVICE_NAME}
    # queue wait if provided
    t0 = time.time()
    sched_ms = input.get("scheduled_start_timestamp")
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

    async def work(payload: dict) -> dict:
        req = ParseRequest(
            s3_key=payload["s3_key"],
            file_id=payload["file_id"],
            workspace_id=payload["workspace_id"],
            original_filename=payload["original_filename"],
            task_id=payload.get("task_id"),
        )
        return await _run_parse_job(req)

    result = await manager.execute_task(input, work)
    # Observe ack lag if the worker returned end timestamp
    end_ts = result.get("_end_ts") if isinstance(result, dict) else None
    if isinstance(end_ts, (int, float)):
        try:
            ACK_LAG.record(
                max(0.0, time.time() - float(end_ts)),
                attributes={"stage": "parse", **service_attrs},
                context=otel_context.get_current(),
            )
        except Exception:
            pass
    return result
