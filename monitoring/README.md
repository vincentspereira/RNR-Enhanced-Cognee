# `monitoring/` -- Observability stack files

Optional. Bring up only if you want metrics / traces / logs / dashboards.

Authoritative reference: [`../docs/MONITORING.md`](../docs/MONITORING.md).
This file is just a quick directory map.

## Files

| File | Purpose |
| --- | --- |
| `docker-compose-monitoring.yml` | **Primary stack.** Prometheus + SigNoz + ClickHouse + Apache Superset. 100% MIT + Apache-2.0. |
| `docker-compose-monitoring-hyperdx.yml` | Alternative. HyperDX (MIT) + Prometheus. ⚠ Bundles MongoDB (SSPL) -- see file header. |
| `prometheus.yml` | Scrape config used by both stacks. |
| `superset-dashboards/` | Exported Superset dashboard JSON. Mounted read-only at `/opt/cognee-dashboards` inside the Superset container. |

## Quick start

```bash
# Bring up the optional observability stack (after the main stack):
docker compose -f monitoring/docker-compose-monitoring.yml up -d

# Then point the MCP server at SigNoz's OTel collector:
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

UIs:

- SigNoz       http://localhost:3301
- Superset     http://localhost:8088
- Prometheus   http://localhost:9090

## History

The previous Grafana + Loki + Tempo + Jaeger stack was removed in
Phase 4 (2026-05-19). It was AGPLv3-tinged. Files removed from this
directory in that swap: `grafana-dashboard.json`,
`grafana-dashboard-provider.yml`, `grafana-datasources.yml`,
`promtail-config.yml`. The old dashboard is in git history if you need
to reference it for rebuilding equivalents in SigNoz / Superset.

See [`../docs/STRATEGY.md`](../docs/STRATEGY.md) DR-13 for the
decision record.
