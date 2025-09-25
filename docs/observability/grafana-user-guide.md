### Grafana User Guide (QuickResolve Observability)

This guide shows how to view metrics and traces for QuickResolve using Grafana with Mimir (metrics) and Tempo (traces). It’s written for beginners.

#### 1) Access Grafana
- Open your browser at `http://localhost:3000`.
- Default credentials: `admin` / `admin` (if login is enabled). In this repo, anonymous access may be enabled with admin rights.
- If you can’t log in or see data sources, see Troubleshooting below.

#### 2) Verify data sources
- Left menu → Plugins and data → Data sources.
- Ensure two datasources exist and are healthy when you click “Save & test”:
  - Mimir (type: Prometheus) → URL `http://mimir:9009/prometheus`
  - Tempo (type: Tempo) → URL `http://tempo:3200`
- If either is not healthy, see Troubleshooting.

#### 3) Explore metrics (PromQL)
- Left menu → Explore → pick `Mimir` datasource.
- Common queries:
  - Indexing throughput (upserts/sec):
    ```promql
    sum(rate(index_upserts_total[1m]))
    ```
  - Indexing latency p95:
    ```promql
    histogram_quantile(0.95, sum(rate(indexing_latency_seconds_bucket[5m])) by (le))
    ```
  - CPU usage (avg over 5m):
    ```promql
    avg_over_time(process_cpu_percent{service="indexing-service"}[5m])
    ```
  - Peak RSS (last 15m p95):
    ```promql
    histogram_quantile(0.95, sum(rate(process_memory_rss_peak_bytes_bucket{service="indexing-service"}[15m])) by (le))
    ```
  - Disk read throughput (bytes/sec):
    ```promql
    avg(rate(process_io_read_bytes_per_second_sum{service="indexing-service"}[5m]))
    ```
- Tip: In the panel’s right-side “Display” options, set Unit to “bytes (SI)” or “bytes (IEC)” so values show as MB/GB.

#### 4) Build a dashboard panel
- Left menu → Dashboards → New → New dashboard → Add a visualization → Choose “Time series”.
- Select datasource `Mimir`.
- Paste a query (e.g., indexing latency p95 above).
- Panel options:
  - Unit: set to seconds or bytes as appropriate.
  - Exemplars: toggle ON (Field → Standard options → Exemplars).
  - Legend: show labels like `service`, `stage`.
- Click “Apply”. Repeat to add CPU, RAM, throughput panels.

#### 5) Traces in Tempo
- Left menu → Explore → pick `Tempo` datasource.
- Search by `Service name` (e.g., `indexing-service`).
- Select a trace → view spans and attributes. You’ll see span names like `index` and attributes such as `service` (and `qdrant_collection` on Qdrant ops).

#### 6) Link metrics ↔ traces (Exemplars)
- In a metrics panel with exemplars enabled, hover a data point to see a diamond marker.
- Click the exemplar to jump directly to the related trace in Tempo.
- From a Tempo trace page, use the time range selector to open Explore with the same window and review related metrics.

#### 7) Units and conventions
- Metrics are exported in base units (seconds, bytes, bytes/sec, percent). Format them in Grafana using Units.
- CPU can be shown as percent in our setup. If you prefer ratio (0..1), divide by 100 or switch unit.

#### 8) Useful starter panels
- Indexing
  - Requests/sec: `sum(rate(indexing_requests_total[1m]))`
  - Errors/sec: `sum(rate(indexing_errors_total[5m]))`
  - Latency p95: `histogram_quantile(0.95, sum(rate(indexing_latency_seconds_bucket[5m])) by (le))`
  - Upsert latency p95: `histogram_quantile(0.95, sum(rate(index_upsert_latency_seconds_bucket[5m])) by (le))`
- Resources (indexing-service)
  - CPU avg 5m: `avg_over_time(process_cpu_percent{service="indexing-service"}[5m])`
  - RSS p95 15m: `histogram_quantile(0.95, sum(rate(process_memory_rss_bytes_bucket{service="indexing-service"}[15m])) by (le))`
  - Disk read B/s avg: `avg(rate(process_io_read_bytes_per_second_sum{service="indexing-service"}[5m]))`

#### 9) Troubleshooting
- I see no metrics in Explore:
  - Check services are running and exporting to `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`.
  - Check `otel-collector`, `mimir`, and `grafana` are healthy: `docker compose ps`.
  - In `grafana` → Data sources → Mimir → “Save & test”. It must say “Data source is working”.
- Grafana shows no Settings / cannot log in:
  - This repo config may enable anonymous admin or show the login form. If not visible, set in Compose:
    - `GF_AUTH_ANONYMOUS_ORG_ROLE=Admin`
    - `GF_AUTH_DISABLE_LOGIN_FORM=false`
  - Restart Grafana: `docker compose up -d grafana`.
- Mimir keeps restarting:
  - Inspect logs: `docker compose logs -f mimir | cat`.
  - Ensure `observability/mimir.yaml` matches the repo’s single-binary, filesystem configuration and that filesystem directories do not overlap.
- Exemplars don’t show:
  - Use histogram queries (e.g., `_bucket` metrics) or metrics recorded with span context.
  - Turn on Exemplars in the panel’s Field options.

#### 10) Next steps
- Add similar panels for `document-parsing-service`, `chunking-service`, `redaction-service`, `embedding-service`, `task-service`, and `search-service` once instrumented.
- Save dashboards and export JSON to keep them under version control. 