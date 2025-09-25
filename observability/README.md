### Observability Stack (OTel Collector → Tempo + Mimir → Grafana)

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

#### Recommendations
- Keep labels low-cardinality: `stage`, `service`, maybe `collection` for indexing.
- Configure histogram buckets via OTel Views in code to match useful ranges.
- If you add exporters (Grafana Cloud), switch Collector `prometheusremotewrite` endpoint and auth headers.