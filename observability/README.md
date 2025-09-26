## Observability Stack (OTel Collector → Tempo + Mimir → Grafana)

### Enabling metrics and traces (defaults are OFF)
- Defaults in services:
  - `OTEL_SDK_DISABLED=true`
  - `OTEL_METRICS_ENABLED=false`
- To enable per service, set (in `.env` or compose):
  - `OTEL_SDK_DISABLED=false` to initialize OTel providers
  - `OTEL_METRICS_ENABLED=true` to activate metrics emission
- Optional resource sampler controls:
  - `RESOURCE_SAMPLER_ENABLED=true|false` (default true)
  - `RESOURCE_SAMPLER_HZ=1` (Hz)
  - `GPU_METRICS_ENABLED=true|false` (default false)

See root `README.md` for a quick overview and `docs/observability/grafana-user-guide.md` for Grafana usage.

This guide explains how to run the OpenTelemetry Collector and Grafana backends (Tempo for traces, Mimir for metrics), and how to explore metrics and traces in Grafana.

### Components
- OpenTelemetry Collector: Receives OTLP metrics and traces from services and fan-outs:
  - traces → Tempo (OTLP)
  - metrics → Mimir (Prometheus Remote Write)
- Tempo: Trace backend
- Mimir: Prometheus-compatible metrics backend (remote write)
- Grafana: Visualization and dashboards; queries Mimir with PromQL and Tempo for traces

### Files
- `observability/otel-collector-config.yaml`: Collector configuration
- `observability/tempo.yaml`: Tempo configuration (local storage)
- `observability/mimir.yaml`: Mimir configuration (filesystem storage)
- `observability/grafana/datasources/datasources.yaml`: Datasource provisioning (Mimir + Tempo)
- `observability/grafana/provisioning/dashboards/dashboards.yaml`: Dashboards auto-loading (drop JSON in `/var/lib/grafana/dashboards`)
- Beginner guide: `docs/observability/grafana-user-guide.md` (how to access Grafana, query metrics, view traces, and use exemplars)
- Shared lib: `libs/observability_utils` (resource sampler + standardized resource instruments)

### Docker Compose additions
Add the following services to your compose (already configured by the repo edits):
- `otel-collector` (ports: 4317 gRPC, 4318 HTTP)
- `tempo` (HTTP UI on 3200)
- `mimir` (HTTP API 9009)
- `grafana` (UI on 3000)

Services should export:
- `OTEL_SERVICE_NAME`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`
- Optional: `OTEL_METRICS_EXPORT_INTERVAL_MS`, histogram view config via code
- Optional resource sampler envs: `RESOURCE_SAMPLER_ENABLED=true`, `RESOURCE_SAMPLER_HZ=1`, `GPU_METRICS_ENABLED=false`

### How to use Grafana
1) Open Grafana at `http://localhost:3000` (default admin/admin)
2) Datasources:
   - `Mimir` (Prometheus): default; PromQL queries
   - `Tempo` (traces): query by service or trace ID
3) Build a metrics panel (PromQL):
   - Stage latency p95 by stage
   ```promql
   histogram_quantile(0.95, sum(rate(stage_latency_seconds_bucket[5m])) by (le, stage))
   ```
   - Error rate by stage
   ```promql
   sum(rate(stage_errors_total[5m])) by (stage)
   /
   sum(rate(stage_requests_total[5m])) by (stage)
   ```
   - Indexing upserts per second
   ```promql
   sum(rate(index_upserts_total[1m]))
   ```
4) Enable exemplars:
   - In a histogram panel, open Panel Editor → Field → Standard options → Exemplars = On.
   - When points show, click an exemplar to jump to the trace in Tempo.
5) Explore traces:
   - Open the `Tempo` datasource, filter by `service.name` (e.g., `indexing-service`).
   - Click a trace to see spans; attributes (e.g., `task.id`) appear on spans.
6) Correlate metrics ↔ traces:
   - From a metrics panel exemplar, click to open the trace.
   - From a trace, use “View related metrics” to open Panels scoped to the trace time window.

### Common queries
- Queue wait p95
```promql
histogram_quantile(0.95, sum(rate(queue_wait_seconds_bucket[5m])) by (le, stage))
```
- Throughput
```promql
sum(rate(stage_requests_total[1m])) by (stage)
```
- Per-task peak RAM p95
```promql
histogram_quantile(0.95, sum(rate(task_peak_rss_bytes_bucket[15m])) by (le, stage))
```

### Shared resource utils (usage)
- Import in service:
  - `from observability_utils import build_resource_instruments, start_resource_sampler, stop_resource_sampler`
- Build instruments once per service: `RI = build_resource_instruments(meter)` and assign to local names to keep queries stable.
- Start sampler around span:
  - Define `_tick(sample)` to record CPU/RAM/IO/GPU to your instruments with attributes `{service, stage}` and optional `device` for GPU.
  - Define `_peaks(peaks)` to record peak histograms at end of task.
  - `handle = start_resource_sampler(_tick, _peaks, hz=float(os.getenv("RESOURCE_SAMPLER_HZ","1")), enable_gpu=os.getenv("GPU_METRICS_ENABLED","false").lower()=="true")`
  - On finally: `stop_resource_sampler(handle)`.
- Metric names/units are standardized across services via the builder. Low-cardinality labels only.

## Metrics Index by Service (OpenTelemetry)

### Common resource metrics (sampler)

These are emitted by services that enable the shared resource sampler (`stage` varies by service):

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `process_cpu_percent` | Histogram | % | CPU utilization of the process. |
| `process_cpu_percent_peak` | Histogram | % | Peak CPU during the task. |
| `process_memory_rss_bytes` | Histogram | By | Resident memory (RSS). |
| `process_memory_rss_peak_bytes` | Histogram | By | Peak resident memory. |
| `process_io_read_bytes_per_second` | Histogram | By/s | Disk read throughput. |
| `process_io_write_bytes_per_second` | Histogram | By/s | Disk write throughput. |
| `process_io_read_bps_peak` | Histogram | By/s | Peak disk read throughput. |
| `process_io_write_bps_peak` | Histogram | By/s | Peak disk write throughput. |
| `gpu_util_percent` | Histogram | % | GPU utilization (when enabled). |
| `gpu_util_percent_peak` | Histogram | % | Peak GPU utilization (when enabled). |
| `gpu_memory_bytes` | Histogram | By | GPU memory in use (when enabled). |
| `gpu_memory_peak_bytes` | Histogram | By | Peak GPU memory (when enabled). | 

### index-document-service

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `index_pipeline_requests_total` | Counter | - | Pipelines started. |
| `index_pipeline_completions_total` | Counter | - | Pipelines finished; includes `status_code`. |
| `index_pipeline_errors_total` | Counter | - | Orchestration exceptions. |
| `index_pipeline_latency_seconds` | Histogram | s | End-to-end pipeline duration. |
| `orchestration_steps_total` | Counter | - | Tasks created per step. |
| `orchestration_step_retries_total` | Counter | - | Retries of single-task steps. |
| `orchestration_fanout_tasks_total` | Counter | - | Fan-out tasks created (redact/embed/index). |
| `orchestration_step_queue_wait_seconds` | Histogram | s | Time from task creation to start. |
| `orchestration_step_processing_seconds` | Histogram | s | Time from start to end of task. |
| `orchestration_step_total_seconds` | Histogram | s | Time from creation to end of task. |
| `task_create_latency_seconds` | Histogram | s | `POST /task` round-trip latency. |
| `task_get_latency_seconds` | Histogram | s | `GET /task/{id}` latency (on status changes). |
| `task_service_errors_total` | Counter | - | Task-service HTTP errors/timeouts. |

### document-parsing-service

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `parsing_requests_total` | Counter | - | Parse tasks started. |
| `parsing_completions_total` | Counter | - | Parse tasks finished; includes `status_code`. |
| `parsing_errors_total` | Counter | - | Errors during parsing. |
| `parsing_latency_seconds` | Histogram | s | End-to-end parse latency. |
| `queue_wait_seconds` | Histogram | s | Time a parse task waited to start. |
| `ack_lag_seconds` | Histogram | s | Worker end-to-ack delay. |
| `s3_download_latency_seconds` | Histogram | s | S3 GET latency (original file). |
| `s3_upload_latency_seconds` | Histogram | s | S3 PUT latency (parsed markdown). |
| `s3_upload_image_latency_seconds` | Histogram | s | S3 PUT latency per image. |
| `payload_bytes_in_total` | Counter | By | Inbound bytes (stage="parse"). |
| `payload_bytes_out_total` | Counter | By | Outbound bytes (stage="parse"). |
| `s3_get_errors_total` | Counter | - | S3 GET errors. |
| `s3_put_errors_total` | Counter | - | S3 PUT errors. |
| `document_bytes_in_total` | Counter | By | Size of original file downloaded. |
| `parsed_chars_out_total` | Counter | - | Characters in parsed markdown. |
| `parsed_markdown_bytes_total` | Counter | By | Bytes of parsed markdown uploaded. |
| `parsed_pages_total` | Counter | - | Pages parsed (when available). |
| `parsed_images_total` | Counter | - | Images extracted/uploaded. |
| `parsed_image_bytes_total` | Counter | By | Bytes of images uploaded. |
| `parsing_strategy_info` | Gauge | - | Info gauge (1) with `parser_version`. |

### chunking-service

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `chunking_requests_total` | Counter | - | Chunking tasks started. |
| `chunking_completions_total` | Counter | - | Chunking tasks finished; includes `status_code`. |
| `chunking_errors_total` | Counter | - | Errors during chunking. |
| `chunking_latency_seconds` | Histogram | s | End-to-end chunking latency. |
| `queue_wait_seconds` | Histogram | s | Time a chunk task waited to start. |
| `ack_lag_seconds` | Histogram | s | Worker end-to-ack delay. |
| `s3_download_latency_seconds` | Histogram | s | S3 GET latency (input markdown). |
| `s3_upload_latency_seconds` | Histogram | s | S3 PUT latency (chunk JSON). |
| `payload_bytes_in_total` | Counter | By | Inbound bytes (stage="chunk"). |
| `payload_bytes_out_total` | Counter | By | Outbound bytes (stage="chunk"). |
| `chunking_chunks_total` | Counter | - | Chunks produced per document. |
| `chunking_chunk_size_chars` | Histogram | - | Per-chunk size in characters. |
| `chunking_chars_out_per_doc` | Histogram | - | Total characters across all chunks. |
| `chunking_chunk_tokens` | Histogram | - | Per-chunk size in tokens. |
| `chunking_overlap_chars_total` | Counter | - | Estimated overlapping characters total. |
| `chunking_overlap_fraction` | Histogram | - | Overlap chars fraction of total output. |
| `chunking_overlap_tokens_total` | Counter | - | Overlapping tokens total. |
| `chunking_overlap_tokens_fraction` | Histogram | - | Overlap tokens fraction of total tokens. |
| `chunking_strategy_info` | Gauge | - | Info gauge (1) with strategy `name`/`version`. |

### redaction-service

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `redaction_requests_total` | Counter | - | Redaction tasks started. |
| `redaction_completions_total` | Counter | - | Redaction tasks finished; includes `status_code`. |
| `redaction_errors_total` | Counter | - | Errors during redaction. |
| `redaction_latency_seconds` | Histogram | s | End-to-end redaction latency. |
| `queue_wait_seconds` | Histogram | s | Time a redaction task waited to start. |
| `ack_lag_seconds` | Histogram | s | Worker end-to-ack delay. |
| `s3_download_latency_seconds` | Histogram | s | S3 GET latency (payload). |
| `s3_upload_latency_seconds` | Histogram | s | S3 PUT latency (updated payload). |
| `s3_get_errors_total` | Counter | - | S3 GET errors. |
| `s3_put_errors_total` | Counter | - | S3 PUT errors. |
| `payload_bytes_in_total` | Counter | By | Inbound bytes (stage="redact"). |
| `payload_bytes_out_total` | Counter | By | Outbound bytes (stage="redact"). |
| `redaction_strategy_info` | Gauge | - | Info gauge (1) with strategy `version`. |

### embedding-service

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `embedding_requests_total` | Counter | - | Embedding tasks started. |
| `embedding_completions_total` | Counter | - | Embedding tasks finished; includes `status_code`. |
| `embedding_errors_total` | Counter | - | Errors during embedding. |
| `embedding_latency_seconds` | Histogram | s | End-to-end embedding latency. |
| `queue_wait_seconds` | Histogram | s | Time an embed task waited to start. |
| `ack_lag_seconds` | Histogram | s | Worker end-to-ack delay. |
| `s3_download_latency_seconds` | Histogram | s | S3 GET latency (payload). |
| `s3_upload_latency_seconds` | Histogram | s | S3 PUT latency (payload metadata). |
| `s3_upload_vector_latency_seconds` | Histogram | s | S3 PUT latency (vector file). |
| `payload_bytes_in_total` | Counter | By | Inbound bytes (stage="embed"). |
| `payload_bytes_out_total` | Counter | By | Outbound bytes (stage="embed"). |
| `vector_bytes_out_total` | Counter | By | Vector file bytes written. |
| `s3_get_errors_total` | Counter | - | S3 GET errors. |
| `s3_put_errors_total` | Counter | - | S3 PUT errors. |
| `embedding_vectors_total` | Counter | - | Embedding vectors generated. |
| `embedding_vector_dim` | Histogram | - | Dimension of produced vectors. |
| `embedding_vector_dim_mismatch_total` | Counter | - | Vectors with unexpected dimension. |
| `embedding_model_info` | Gauge | - | Info gauge (1) with model `name`/`version`. |

### indexing-service

| Metric | Type | Unit | Meaning |
|---|---|---|---|
| `indexing_requests_total` | Counter | - | Index tasks started. |
| `indexing_completions_total` | Counter | - | Index tasks finished; includes `status_code`. |
| `indexing_errors_total` | Counter | - | Errors during indexing. |
| `indexing_latency_seconds` | Histogram | s | End-to-end indexing latency. |
| `queue_wait_seconds` | Histogram | s | Time an index task waited to start. |
| `ack_lag_seconds` | Histogram | s | Worker end-to-ack delay. |
| `s3_download_latency_seconds` | Histogram | s | S3 GET latency (payload/vector). |
| `payload_bytes_in_total` | Counter | By | Payload bytes read (stage="index"). |
| `vector_bytes_in_total` | Counter | By | Vector bytes read (stage="index"). |
| `index_upserts_total` | Counter | - | Upserts sent to Qdrant. |
| `index_upsert_latency_seconds` | Histogram | s | Qdrant upsert latency. |
| `index_upsert_errors_total` | Counter | - | Qdrant upsert errors. |
| `index_batch_size` | Histogram | - | Batch size of upserts. |
| `index_vector_dim` | Histogram | - | Dimension of vectors being indexed. |
| `index_vector_dim_mismatch_total` | Counter | - | Vectors with unexpected dimension. |

## Recommendations
- Keep labels low-cardinality: `stage`, `service`; use `qdrant_collection` only on Qdrant metrics.
- Configure histogram buckets via OTel Views in code to match useful ranges.
- If you add exporters (Grafana Cloud), switch Collector `prometheusremotewrite` endpoint and auth headers.