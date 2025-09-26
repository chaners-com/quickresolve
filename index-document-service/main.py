"""
Index Document Service
AKA "Indexer"
This service orchestrates the indexing pipeline for a document.
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI

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
from opentelemetry.metrics import get_meter, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel
from task_broker_client import TaskBrokerClient
from task_manager import TaskManager

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")
SERVICE_BASE = os.getenv(
    "INDEX_DOCUMENT_SERVICE_URL", "http://index-document-service:8011"
)

app = FastAPI()


# OTel env
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "index-document-service")
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

# Instruments (pipeline-level)
INDEX_REQS = _meter.create_counter("index_pipeline_requests_total")
INDEX_DONE = _meter.create_counter("index_pipeline_completions_total")
INDEX_ERRS = _meter.create_counter("index_pipeline_errors_total")
INDEX_LAT = _meter.create_histogram("index_pipeline_latency_seconds", unit="s")

# Step orchestration instruments
ORCH_STEPS = _meter.create_counter("orchestration_steps_total")
ORCH_RETRIES = _meter.create_counter("orchestration_step_retries_total")
ORCH_FANOUT_TASKS = _meter.create_counter("orchestration_fanout_tasks_total")
ORCH_QWAIT = _meter.create_histogram(
    "orchestration_step_queue_wait_seconds", unit="s"
)
ORCH_PROC = _meter.create_histogram(
    "orchestration_step_processing_seconds", unit="s"
)
ORCH_TOTAL = _meter.create_histogram(
    "orchestration_step_total_seconds", unit="s"
)

# Task-service interaction instruments
TASK_CREATE_LAT = _meter.create_histogram(
    "task_create_latency_seconds", unit="s"
)
TASK_GET_LAT = _meter.create_histogram("task_get_latency_seconds", unit="s")
TASK_SVC_ERRS = _meter.create_counter("task_service_errors_total")


def _derive_doc_type(original_filename: Optional[str]) -> str:
    try:
        if not original_filename:
            return "unknown"
        name = original_filename.lower().strip()
        if "." not in name:
            return "unknown"
        return name.split(".")[-1]
    except Exception:
        return "unknown"


class PipelineStep(BaseModel):
    name: str


class PipelineDefinition(BaseModel):
    description: Optional[str] = None
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: str
    steps: List[PipelineStep]
    task_id: Optional[str] = None


# Task broker client/manager for consuming index-document tasks
broker = TaskBrokerClient(
    endpoint_url=f"{SERVICE_BASE}/",
    health_url=f"{SERVICE_BASE}/health",
    topic="index-document",
)
manager = TaskManager(
    broker,
    max_concurrent=max(
        1, int(os.getenv("INDEX_DOC_MAX_CONCURRENT", "20") or "20")
    ),
)


@app.on_event("startup")
async def on_startup():
    await manager.start()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "index-document-service"}


def _canonicalize_steps(steps: List[PipelineStep]) -> List[PipelineStep]:
    """Return steps ordered as:
    parse-document -> chunk -> redact -> embed -> index (others last)."""
    priority = {
        "parse-document": 0,
        "chunk": 1,
        "redact": 2,
        "embed": 3,
        "index": 4,
    }
    return sorted(
        steps, key=lambda s: priority.get((s.name or "").strip().lower(), 5)
    )


@app.post("/")
async def consume(input: dict):
    async def work(payload: dict) -> dict:
        doc_type = _derive_doc_type(payload.get("original_filename"))
        base_attrs = {
            "service": OTEL_SERVICE_NAME,
            "stage": "orchestrate",
            "file_id": payload.get("file_id", "unknown"),
            "doc_type": doc_type,
        }
        try:
            INDEX_REQS.add(1, attributes=base_attrs)
        except Exception:
            pass
        t0 = time.time()
        sampler_handle = None
        with _tracer.start_as_current_span("orchestrate") as span:
            if RESOURCE_SAMPLER_ENABLED:
                try:
                    sampler_handle = start_process_resource_metrics(
                        meter=_meter,
                        base_attributes=base_attrs,
                        stage="orchestrate",
                        hz=RESOURCE_SAMPLER_HZ,
                        enable_gpu=GPU_METRICS_ENABLED,
                    )
                except Exception:
                    sampler_handle = None
            try:
                definition = PipelineDefinition(
                    description="Index document pipeline",
                    s3_key=payload["s3_key"],
                    file_id=payload["file_id"],
                    workspace_id=payload["workspace_id"],
                    original_filename=payload["original_filename"],
                    steps=[
                        PipelineStep(name=s["name"])
                        for s in payload.get("steps", [])
                    ],
                    task_id=payload.get("task_id"),
                )
                # Let exceptions bubble to TaskManager
                # so it FAILs and frees slot
                await _run_pipeline(definition, base_attrs)
                try:
                    INDEX_DONE.add(
                        1, attributes={**base_attrs, "status_code": 2}
                    )
                except Exception:
                    pass
                return {}
            except Exception as e:
                try:
                    INDEX_ERRS.add(
                        1, attributes={**base_attrs, "error": type(e).__name__}
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
                    INDEX_LAT.record(
                        time.time() - t0,
                        attributes=base_attrs,
                        context=otel_context.get_current(),
                    )
                except Exception:
                    pass
        definition = PipelineDefinition(
            description="Index document pipeline",
            s3_key=payload["s3_key"],
            file_id=payload["file_id"],
            workspace_id=payload["workspace_id"],
            original_filename=payload["original_filename"],
            steps=[
                PipelineStep(name=s["name"]) for s in payload.get("steps", [])
            ],
            task_id=payload.get("task_id"),
        )
        # Let exceptions bubble to TaskManager so it FAILs and frees slot
        await _run_pipeline(definition, base_attrs)
        return {}

    return await manager.execute_task(input, work)


async def _run_pipeline(
    definition: PipelineDefinition, base_attrs: Dict[str, Any]
):
    workspace_id = definition.workspace_id
    root_ctx: Dict[str, Any] = {
        "s3_key": definition.s3_key,
        "file_id": definition.file_id,
        "workspace_id": workspace_id,
        "original_filename": definition.original_filename,
    }
    # Artifact context persists outputs needed by later steps
    # regardless of order
    artifact_ctx: Dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        prev_output: Dict[str, Any] | None = None
        ordered_steps = _canonicalize_steps(definition.steps)
        for step in ordered_steps:
            name = (step.name or "").strip().lower()

            # Redaction is a fanout over chunks
            if name == "redact":
                chunks = (prev_output or {}).get("chunks") or artifact_ctx.get(
                    "chunks", []
                )
                if not isinstance(chunks, list):
                    chunks = []
                await _run_redact_fanout(
                    client, chunks, workspace_id, base_attrs
                )
                # keep prev_output pointing to chunks for next steps
                prev_output = {"chunks": chunks}
                continue

            # Embed is a fanout over redaction
            if name == "embed":
                chunks = (prev_output or {}).get("chunks") or artifact_ctx.get(
                    "chunks", []
                )
                if not isinstance(chunks, list):
                    chunks = []
                await _run_embed_fanout(
                    client, chunks, workspace_id, base_attrs
                )
                # keep prev_output pointing to chunks for next steps
                prev_output = {"chunks": chunks}
                continue

            # Index is a fanout over chunks
            if name == "index":
                chunks = (prev_output or {}).get("chunks") or artifact_ctx.get(
                    "chunks", []
                )
                if not isinstance(chunks, list):
                    chunks = []
                await _run_index_fanout(
                    client, chunks, workspace_id, base_attrs
                )
                continue

            # Regular single task step with simple retries
            tries = 0
            while tries < 3:
                tries += 1
                try:
                    prev_output = await _create_and_wait_task(
                        client=client,
                        name=name,
                        workspace_id=workspace_id,
                        root_ctx=root_ctx,
                        artifact_ctx=artifact_ctx,
                        prev_output=prev_output,
                        base_attrs=base_attrs,
                    )
                    # Persist key artifacts for later steps
                    if name == "parse-document":
                        if isinstance(prev_output, dict):
                            if prev_output.get("parsed_s3_key"):
                                artifact_ctx["parsed_s3_key"] = prev_output[
                                    "parsed_s3_key"
                                ]
                            if prev_output.get("document_parser_version"):
                                artifact_ctx["document_parser_version"] = (
                                    prev_output["document_parser_version"]
                                )
                    elif name == "chunk":
                        if isinstance(prev_output, dict) and prev_output.get(
                            "chunks"
                        ):
                            artifact_ctx["chunks"] = prev_output["chunks"]
                    break
                except Exception:
                    if tries >= 3:
                        # Propagate failure to TaskManager
                        raise
                    # Record retry occurrence for this step
                    try:
                        ORCH_RETRIES.add(
                            1, attributes={**base_attrs, "step": name}
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(2 * tries)
    # Completed all steps without embed/index
    return


async def _create_and_wait_task(
    *,
    client: httpx.AsyncClient,
    name: str,
    workspace_id: int,
    root_ctx: Dict[str, Any],
    artifact_ctx: Dict[str, Any],
    prev_output: Dict[str, Any] | None,
    base_attrs: Dict[str, Any],
) -> Dict[str, Any]:
    # Build task input depending on step
    step_input: Dict[str, Any]
    if name == "parse-document":
        step_input = {
            "s3_key": root_ctx["s3_key"],
            "file_id": root_ctx["file_id"],
            "workspace_id": workspace_id,
            "original_filename": root_ctx["original_filename"],
        }
    elif name == "chunk":
        step_input = {
            # Use redacted if available, else parsed, else original
            "s3_key": artifact_ctx.get("redacted_s3_key")
            or (prev_output or {}).get("redacted_s3_key")
            or artifact_ctx.get("parsed_s3_key")
            or (prev_output or {}).get("parsed_s3_key")
            or root_ctx.get("s3_key"),
            "file_id": root_ctx["file_id"],
            "workspace_id": workspace_id,
            "original_filename": root_ctx["original_filename"],
            "document_parser_version": artifact_ctx.get(
                "document_parser_version"
            )
            or (prev_output or {}).get("document_parser_version"),
        }
    else:
        # Default passthrough if an unknown step shows up
        step_input = {
            "context": (prev_output or {}),
            "workspace_id": workspace_id,
        }

    step_attrs = {**base_attrs, "step": name}
    _t_post = time.time()
    try:
        r = await client.post(
            f"{TASK_SERVICE_URL}/task",
            json={
                "name": name,
                "input": step_input,
                "workspace_id": workspace_id,
            },
        )
    except Exception as e:
        try:
            TASK_SVC_ERRS.add(
                1, attributes={**step_attrs, "error": type(e).__name__}
            )
        except Exception:
            pass
        raise
    finally:
        try:
            TASK_CREATE_LAT.record(
                time.time() - _t_post,
                attributes=step_attrs,
                context=otel_context.get_current(),
            )
        except Exception:
            pass
    r.raise_for_status()
    task_id = r.json().get("id")
    if not task_id:
        raise RuntimeError("Task creation did not return id")
    try:
        ORCH_STEPS.add(1, attributes=step_attrs)
    except Exception:
        pass

    # Poll until done or failed
    prev_code: Optional[int] = None
    while True:
        await asyncio.sleep(1)
        _t_get = time.time()
        try:
            s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
        except Exception as e:
            try:
                TASK_SVC_ERRS.add(
                    1, attributes={**step_attrs, "error": type(e).__name__}
                )
            except Exception:
                pass
            continue
        if s.status_code != 200:
            continue
        data = s.json()
        code = int(data.get("status_code") or 0)
        try:
            if code != prev_code:
                TASK_GET_LAT.record(
                    time.time() - _t_get,
                    attributes=step_attrs,
                    context=otel_context.get_current(),
                )
                prev_code = code
        except Exception:
            pass
        if code == 2:
            # Record step timings if available
            try:
                ct = data.get("creation_timestamp")
                st = data.get("start_timestamp")
                et = data.get("end_timestamp")
                if isinstance(ct, (int, float)) and isinstance(
                    st, (int, float)
                ):
                    ORCH_QWAIT.record(
                        max(0.0, float(st) - float(ct)),
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                if isinstance(st, (int, float)) and isinstance(
                    et, (int, float)
                ):
                    ORCH_PROC.record(
                        max(0.0, float(et) - float(st)),
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                if isinstance(ct, (int, float)) and isinstance(
                    et, (int, float)
                ):
                    ORCH_TOTAL.record(
                        max(0.0, float(et) - float(ct)),
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
            except Exception:
                pass
            return data.get("output") or {}
        if code == 3:
            # Also try to record timings on failure
            try:
                ct = data.get("creation_timestamp")
                st = data.get("start_timestamp")
                et = data.get("end_timestamp")
                if isinstance(ct, (int, float)) and isinstance(
                    st, (int, float)
                ):
                    ORCH_QWAIT.record(
                        max(0.0, float(st) - float(ct)),
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                if isinstance(st, (int, float)) and isinstance(
                    et, (int, float)
                ):
                    ORCH_PROC.record(
                        max(0.0, float(et) - float(st)),
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                if isinstance(ct, (int, float)) and isinstance(
                    et, (int, float)
                ):
                    ORCH_TOTAL.record(
                        max(0.0, float(et) - float(ct)),
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
            except Exception:
                pass
            raise RuntimeError(f"Task {name} {task_id} failed")


async def _run_redact_fanout(
    client: httpx.AsyncClient,
    chunks: List[Dict[str, Any]],
    workspace_id: int,
    base_attrs: Dict[str, Any],
):
    # Run multiple redact tasks and wait for all to complete
    step_attrs = {**base_attrs, "step": "redact"}
    try:
        ORCH_FANOUT_TASKS.add(len(chunks or []), attributes=step_attrs)
    except Exception:
        pass

    async def _one(chunk: Dict[str, Any]):
        body = {
            "name": "redact",
            "input": {
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "workspace_id": workspace_id,
            },
            "workspace_id": workspace_id,
        }
        _t_post = time.time()
        try:
            r = await client.post(f"{TASK_SERVICE_URL}/task", json=body)
        except Exception as e:
            try:
                TASK_SVC_ERRS.add(
                    1, attributes={**step_attrs, "error": type(e).__name__}
                )
            except Exception:
                pass
            raise
        finally:
            try:
                TASK_CREATE_LAT.record(
                    time.time() - _t_post,
                    attributes=step_attrs,
                    context=otel_context.get_current(),
                )
            except Exception:
                pass
        r.raise_for_status()
        try:
            ORCH_STEPS.add(1, attributes=step_attrs)
        except Exception:
            pass
        task_id = r.json().get("id")
        if not task_id:
            raise RuntimeError("Task creation did not return id")
        prev_code: Optional[int] = None
        while True:
            await asyncio.sleep(1)
            _t_get = time.time()
            try:
                s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
            except Exception as e:
                try:
                    TASK_SVC_ERRS.add(
                        1, attributes={**step_attrs, "error": type(e).__name__}
                    )
                except Exception:
                    pass
                continue
            if s.status_code != 200:
                continue
            data = s.json()
            code = int(data.get("status_code") or 0)
            try:
                if code != prev_code:
                    TASK_GET_LAT.record(
                        time.time() - _t_get,
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                    prev_code = code
            except Exception:
                pass
            if code == 2:
                # Record step timings
                try:
                    ct = data.get("creation_timestamp")
                    st = data.get("start_timestamp")
                    et = data.get("end_timestamp")
                    if isinstance(ct, (int, float)) and isinstance(
                        st, (int, float)
                    ):
                        ORCH_QWAIT.record(
                            max(0.0, float(st) - float(ct)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                    if isinstance(st, (int, float)) and isinstance(
                        et, (int, float)
                    ):
                        ORCH_PROC.record(
                            max(0.0, float(et) - float(st)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                    if isinstance(ct, (int, float)) and isinstance(
                        et, (int, float)
                    ):
                        ORCH_TOTAL.record(
                            max(0.0, float(et) - float(ct)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                except Exception:
                    pass
                return
            if code == 3:
                raise RuntimeError("redact failed")

    tasks = [asyncio.create_task(_one(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)


async def _run_embed_fanout(
    client: httpx.AsyncClient,
    chunks: List[Dict[str, Any]],
    workspace_id: int,
    base_attrs: Dict[str, Any],
):
    # Run multiple embed tasks and wait for all to complete
    step_attrs = {**base_attrs, "step": "embed"}
    try:
        ORCH_FANOUT_TASKS.add(len(chunks or []), attributes=step_attrs)
    except Exception:
        pass

    async def _one(chunk: Dict[str, Any]):
        body = {
            "name": "embed",
            "input": {
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "workspace_id": workspace_id,
            },
            "workspace_id": workspace_id,
        }
        _t_post = time.time()
        try:
            r = await client.post(f"{TASK_SERVICE_URL}/task", json=body)
        except Exception as e:
            try:
                TASK_SVC_ERRS.add(
                    1, attributes={**step_attrs, "error": type(e).__name__}
                )
            except Exception:
                pass
            raise
        finally:
            try:
                TASK_CREATE_LAT.record(
                    time.time() - _t_post,
                    attributes=step_attrs,
                    context=otel_context.get_current(),
                )
            except Exception:
                pass
        r.raise_for_status()
        try:
            ORCH_STEPS.add(1, attributes=step_attrs)
        except Exception:
            pass
        task_id = r.json().get("id")
        if not task_id:
            raise RuntimeError("Task creation did not return id")
        prev_code: Optional[int] = None
        while True:
            await asyncio.sleep(1)
            _t_get = time.time()
            try:
                s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
            except Exception as e:
                try:
                    TASK_SVC_ERRS.add(
                        1, attributes={**step_attrs, "error": type(e).__name__}
                    )
                except Exception:
                    pass
                continue
            if s.status_code != 200:
                continue
            data = s.json()
            code = int(data.get("status_code") or 0)
            try:
                if code != prev_code:
                    TASK_GET_LAT.record(
                        time.time() - _t_get,
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                    prev_code = code
            except Exception:
                pass
            if code == 2:
                try:
                    ct = data.get("creation_timestamp")
                    st = data.get("start_timestamp")
                    et = data.get("end_timestamp")
                    if isinstance(ct, (int, float)) and isinstance(
                        st, (int, float)
                    ):
                        ORCH_QWAIT.record(
                            max(0.0, float(st) - float(ct)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                    if isinstance(st, (int, float)) and isinstance(
                        et, (int, float)
                    ):
                        ORCH_PROC.record(
                            max(0.0, float(et) - float(st)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                    if isinstance(ct, (int, float)) and isinstance(
                        et, (int, float)
                    ):
                        ORCH_TOTAL.record(
                            max(0.0, float(et) - float(ct)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                except Exception:
                    pass
                return
            if code == 3:
                raise RuntimeError("embed failed")

    tasks = [asyncio.create_task(_one(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)


async def _run_index_fanout(
    client: httpx.AsyncClient,
    chunks: List[Dict[str, Any]],
    workspace_id: int,
    base_attrs: Dict[str, Any],
):
    # Create multiple index tasks and wait for all to complete
    step_attrs = {**base_attrs, "step": "index"}
    try:
        ORCH_FANOUT_TASKS.add(len(chunks or []), attributes=step_attrs)
    except Exception:
        pass

    async def _one(chunk: Dict[str, Any]):
        body = {
            "name": "index",
            "input": {
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "workspace_id": workspace_id,
            },
            "workspace_id": workspace_id,
        }
        _t_post = time.time()
        try:
            r = await client.post(f"{TASK_SERVICE_URL}/task", json=body)
        except Exception as e:
            try:
                TASK_SVC_ERRS.add(
                    1, attributes={**step_attrs, "error": type(e).__name__}
                )
            except Exception:
                pass
            raise
        finally:
            try:
                TASK_CREATE_LAT.record(
                    time.time() - _t_post,
                    attributes=step_attrs,
                    context=otel_context.get_current(),
                )
            except Exception:
                pass
        r.raise_for_status()
        try:
            ORCH_STEPS.add(1, attributes=step_attrs)
        except Exception:
            pass
        task_id = r.json().get("id")
        if not task_id:
            raise RuntimeError("Task creation did not return id")
        prev_code: Optional[int] = None
        while True:
            await asyncio.sleep(1)
            _t_get = time.time()
            try:
                s = await client.get(f"{TASK_SERVICE_URL}/task/{task_id}")
            except Exception as e:
                try:
                    TASK_SVC_ERRS.add(
                        1, attributes={**step_attrs, "error": type(e).__name__}
                    )
                except Exception:
                    pass
                continue
            if s.status_code != 200:
                continue
            data = s.json()
            code = int(data.get("status_code") or 0)
            try:
                if code != prev_code:
                    TASK_GET_LAT.record(
                        time.time() - _t_get,
                        attributes=step_attrs,
                        context=otel_context.get_current(),
                    )
                    prev_code = code
            except Exception:
                pass
            if code == 2:
                try:
                    ct = data.get("creation_timestamp")
                    st = data.get("start_timestamp")
                    et = data.get("end_timestamp")
                    if isinstance(ct, (int, float)) and isinstance(
                        st, (int, float)
                    ):
                        ORCH_QWAIT.record(
                            max(0.0, float(st) - float(ct)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                    if isinstance(st, (int, float)) and isinstance(
                        et, (int, float)
                    ):
                        ORCH_PROC.record(
                            max(0.0, float(et) - float(st)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                    if isinstance(ct, (int, float)) and isinstance(
                        et, (int, float)
                    ):
                        ORCH_TOTAL.record(
                            max(0.0, float(et) - float(ct)),
                            attributes=step_attrs,
                            context=otel_context.get_current(),
                        )
                except Exception:
                    pass
                return
            if code == 3:
                raise RuntimeError("index failed")

    tasks = [asyncio.create_task(_one(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)
