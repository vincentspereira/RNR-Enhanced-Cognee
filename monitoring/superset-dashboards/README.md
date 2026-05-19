# Apache Superset Dashboards

This directory holds **exported** Superset dashboard JSON files for the
Enhanced Cognee BI / analytical layer. The dashboards in here are the
non-APM-style charts that the old Grafana dashboard used to host -- the
APM-style charts (request latency, error rates, RED metrics, flamegraphs)
now live natively in the SigNoz UI and don't need exports.

## Exporting a dashboard from a running Superset

```bash
docker exec -t cognee-monitoring-superset \
  superset export-dashboards --path /opt/cognee-dashboards/<name>.json
# then copy the file out of the container if you didn't mount this dir
docker cp cognee-monitoring-superset:/opt/cognee-dashboards/<name>.json .
```

The compose file mounts this directory at `/opt/cognee-dashboards` so
you can export straight into the host filesystem.

## Importing dashboards on a fresh Superset

The compose file at `monitoring/docker-compose-monitoring.yml` mounts
this directory **read-only** at `/opt/cognee-dashboards`. To re-import:

```bash
docker exec cognee-monitoring-superset \
  superset import-dashboards -p /opt/cognee-dashboards/<name>.json
```

## Dashboards we plan to ship

Per HANDOVER section 4 Phase 4 and STRATEGY.md section 5.3, the
analytical / BI dashboards (versus APM dashboards which live in SigNoz):

| Dashboard | Source data | Description |
| --- | --- | --- |
| memory_growth.json | ClickHouse traces + Postgres metrics | Memory store size and category mix over time |
| agent_activity.json | ClickHouse traces | Heatmap of tool calls per agent over time |
| llm_cost_trends.json | Postgres llm_cost_tracker table | Daily / weekly LLM token spend by provider |
| dedup_effectiveness.json | Postgres dedup logs | Memory deduplication hit rate over time |

These are not yet exported. The Phase 4 PR ships the routing /
infrastructure; the dashboards themselves are a follow-up once the live
SigNoz + Superset stack has been running long enough to generate
representative data.

## Why not Grafana JSON?

The old Grafana dashboard at `monitoring/grafana-dashboard.json` was
deleted in the Phase 4 swap. Operational dashboards (latency / error
rate / p95) now come for free from SigNoz's auto-instrumented OTel
tracing. Analytical / cross-tier dashboards live here as Superset JSON
because Superset is strictly better at SQL-driven BI than Grafana ever
was for our use case.

See `docs/MONITORING.md` for the full stack overview.
