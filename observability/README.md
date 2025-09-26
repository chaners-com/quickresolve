### Observability Stack (OTel Collector → Tempo + Mimir → Grafana)

#### Enabling metrics and traces (defaults are OFF)
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

#### Components
- OpenTelemetry Collector: Receives OTLP metrics and traces from services and fan-outs:
  - traces → Tempo (OTLP)
  - metrics → Mimir (Prometheus Remote Write)
- Tempo: Trace backend
- Mimir: Prometheus-compatible metrics backend (remote write)
- Grafana: Visualization and dashboards; queries Mimir with PromQL and Tempo for traces

#### Files
- `observability/otel-collector-config.yaml`: Collector configuration
- `observability/tempo.yaml`: Tempo configuration (local storage)
- `observability/mimir.yaml`: Mimir configuration (filesystem storage)
- `observability/grafana/datasources/datasources.yaml`: Datasource provisioning (Mimir + Tempo)
- `observability/grafana/provisioning/dashboards/dashboards.yaml`: Dashboards auto-loading (drop JSON in `/var/lib/grafana/dashboards`)
- Beginner guide: `docs/observability/grafana-user-guide.md` (how to access Grafana, query metrics, view traces, and use exemplars)
- Shared lib: `libs/observability_utils` (resource sampler + standardized resource instruments)

#### Docker Compose additions
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

#### How to use Grafana
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

#### Common queries
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

#### Shared resource utils (usage)
- Import in service:
  - `from observability_utils import build_resource_instruments, start_resource_sampler, stop_resource_sampler`
- Build instruments once per service: `RI = build_resource_instruments(meter)` and assign to local names to keep queries stable.
- Start sampler around span:
  - Define `_tick(sample)` to record CPU/RAM/IO/GPU to your instruments with attributes `{service, stage}` and optional `device` for GPU.
  - Define `_peaks(peaks)` to record peak histograms at end of task.
  - `handle = start_resource_sampler(_tick, _peaks, hz=float(os.getenv("RESOURCE_SAMPLER_HZ","1")), enable_gpu=os.getenv("GPU_METRICS_ENABLED","false").lower()=="true")`
  - On finally: `stop_resource_sampler(handle)`.
- Metric names/units are standardized across services via the builder. Low-cardinality labels only.

#### Recommendations
- Keep labels low-cardinality: `stage`, `service`; use `qdrant_collection` only on Qdrant metrics.
- Configure histogram buckets via OTel Views in code to match useful ranges.
- If you add exporters (Grafana Cloud), switch Collector `prometheusremotewrite` endpoint and auth headers.