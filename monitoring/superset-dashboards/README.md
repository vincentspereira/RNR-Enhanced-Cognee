# Apache Superset Dashboards

This directory holds the Enhanced Cognee BI / analytical Superset
dashboards. The dashboards in here are the non-APM-style charts that
the old Grafana dashboard used to host -- the APM-style charts
(request latency, error rates, RED metrics, flamegraphs) now live
natively in the SigNoz UI and don't need exports.

## What ships here (as of 2026-05-20)

| File | Drives | Data source |
| --- | --- | --- |
| `_dataset_definitions.yaml` | All dashboards below | Postgres + ClickHouse |
| `memory_growth.json` | Memory-store size + category mix over time | Postgres `shared_memory.documents` |
| `agent_activity.json` | Heatmap of MCP tool calls per agent over time | ClickHouse `signoz_index_v2` |
| `llm_cost_trends.json` | Daily / weekly LLM token spend by agent + model | Postgres `shared_memory.llm_usage` |
| `dedup_effectiveness.json` | Dedup hit-rate derived from chunk-hash distinctness | Postgres `shared_memory.embeddings` |
| `perf_regression.json` | Per-endpoint p50 / p95 / p99 latency + error-rate (Locust regression tracking) | ClickHouse `signoz_index_v2` |

All 5 dashboards are **importable scaffolds** -- they target the
real schemas Enhanced Cognee writes, so they light up as soon as
there is data in the underlying tables.

## First-time setup

Before importing the dashboards, register two database connections in
Superset:

1. **`enhanced_cognee_postgres`** -- the main Postgres instance:
   ```
   postgresql+psycopg2://cognee_user:cognee_password@postgres-enhanced:5432/cognee_db
   ```
2. **`signoz_clickhouse`** -- SigNoz's ClickHouse trace store:
   ```
   clickhouse+native://signoz:9000/signoz_traces
   ```

The database connection *names* are what `_dataset_definitions.yaml`
references; the *DSNs* live only in the Superset connection record so
secrets stay out of Git.

## Importing the dashboards

The compose file at `monitoring/docker-compose-monitoring.yml` mounts
this directory **read-only** at `/opt/cognee-dashboards`.

```bash
# 1. Import datasets first (the dashboards reference them by name)
docker exec cognee-monitoring-superset \
  superset import-datasources -p /opt/cognee-dashboards/_dataset_definitions.yaml

# 2. Then import each dashboard
for dash in memory_growth agent_activity llm_cost_trends dedup_effectiveness perf_regression; do
  docker exec cognee-monitoring-superset \
    superset import-dashboards -p /opt/cognee-dashboards/${dash}.json
done
```

After import, open Superset at http://localhost:8088 (default admin
credentials are documented in `docs/MONITORING.md`).

## Exporting a dashboard from a running Superset

After you tweak a chart in the UI and want to commit the change back:

```bash
docker exec -t cognee-monitoring-superset \
  superset export-dashboards --path /opt/cognee-dashboards/<name>.json
# then copy the file out of the container if you didn't mount this dir
docker cp cognee-monitoring-superset:/opt/cognee-dashboards/<name>.json .
```

The export format Superset produces is a YAML+JSON bundle; what's
checked into this directory is the *minimum scaffold* that imports
cleanly -- Superset adds the full slice metadata on first save.

## Why not Grafana JSON?

The old Grafana dashboard at `monitoring/grafana-dashboard.json` was
deleted in the Phase 4 swap. Operational dashboards (latency / error
rate / p95) now come for free from SigNoz's auto-instrumented OTel
tracing. Analytical / cross-tier dashboards live here as Superset JSON
because Superset is strictly better at SQL-driven BI than Grafana ever
was for our use case.

See `docs/MONITORING.md` for the full stack overview.
