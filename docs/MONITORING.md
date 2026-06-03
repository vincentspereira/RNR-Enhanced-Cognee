# Monitoring & Observability

**Status:** SigNoz + Apache Superset stack since Phase 4 (2026-05-19).

Enhanced Cognee ships an **optional** observability stack as a separate
compose file: `monitoring/docker-compose-monitoring.yml`. The main
`docker/docker-compose-enhanced-cognee.yml` runs without it; bring
monitoring up only when you want it.

## What's in the stack

| Component | Role | License | Port |
| --- | --- | --- | --- |
| Prometheus | Scrape `/metrics` from the MCP server, Qdrant, etc. | Apache-2.0 | 9090 |
| SigNoz OTel Collector | Ingest OTLP traces / logs / metrics from the MCP server | MIT app + Apache-2.0 binary | 4317 (gRPC) / 4318 (HTTP) |
| SigNoz ClickHouse | Persistent store for SigNoz | Apache-2.0 | (internal) |
| SigNoz ZooKeeper | ClickHouse coordination | Apache-2.0 | (internal) |
| SigNoz Query Service | Backend API for the SigNoz UI | MIT | (internal) |
| SigNoz Frontend | APM / traces / alerts / logs UI | MIT | 3301 |
| SigNoz Alertmanager | Alert routing | MIT | (internal) |
| Apache Superset | BI / analytical dashboards over ClickHouse + Postgres | Apache-2.0 | 8088 |

100% MIT + Apache-2.0. No AGPL, no copyleft. This is the *only*
observability stack we ship; the old Grafana + Loki + Tempo + Jaeger
combination was removed in Phase 4.

If you prefer a Kibana-style query-driven UI over SigNoz's APM-first
layout, see `monitoring/docker-compose-monitoring-hyperdx.yml` for the
**HyperDX** (MIT) alternative. ⚠ HyperDX bundles MongoDB (SSPL) for
its metadata; this is safe for self-hosted use but not for products
that need *strict* end-to-end permissive licensing including metadata
storage. SigNoz wins on that axis.

---

## Quick start

```bash
# 1. Bring up the main Enhanced Cognee stack first.
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

# 2. Bring up the observability stack.
docker compose -f monitoring/docker-compose-monitoring.yml up -d

# 3. Point your MCP server at the SigNoz OTel collector. Either:
#    a) Restart the MCP server with OTEL_EXPORTER_OTLP_ENDPOINT set:
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
#    b) Or add the env var to your installer-registered MCP entry in
#       ~/.claude.json under mcpServers.cognee.env.
```

UIs once everything is healthy:

- **SigNoz**     http://localhost:3301
- **Superset**   http://localhost:8088 (admin / `cognee_admin` -- change in production)
- **Prometheus** http://localhost:9090

Verify traces are flowing:

```bash
python -c "
from src.tracing import init_tracing, trace_tool
init_tracing()  # picks up OTEL_EXPORTER_OTLP_ENDPOINT from env
with trace_tool('smoke_test', agent_id='manual') as span:
    span.set_attribute('demo', 1)
print('span sent')
"
```

Then refresh the SigNoz **Traces** tab -- the span should appear within
a few seconds.

---

## Component deep-dive

### Prometheus

Unchanged from the previous Grafana stack. Scrapes `/metrics` from:

- the MCP server (`host.docker.internal:8080` -- exposed by the
  `prometheus-client` instrumentation in
  `src/llm_cost_tracker.py` and `src/performance_analytics.py`),
- Qdrant (`host.docker.internal:26333/metrics`),
- itself (`localhost:9090`).

Scrape config lives in `monitoring/prometheus.yml`. Retention is 30
days. SigNoz reads Prometheus directly as a federated metrics source,
so existing Prometheus dashboards keep working.

### SigNoz

OTel-native APM. Ingests traces / logs / metrics via the OpenTelemetry
collector on ports 4317 (gRPC) and 4318 (HTTP), persists them to
ClickHouse, and serves a built-in UI for:

- Service-level RED metrics (request rate / error rate / duration)
- Distributed trace explorer with flame graphs
- Log explorer with structured filters
- Alerts (rule editor + Alertmanager integration)
- Per-service exception tracking

Storage backend: ClickHouse, coordinated by ZooKeeper. Default storage
is on a Docker volume (`signoz_clickhouse_data`); for production you
want to mount that on persistent disk and set ClickHouse retention
policies. See https://github.com/SigNoz/signoz/blob/main/deploy/README.md
for production-grade ClickHouse tuning.

Default credentials: SigNoz prompts for an admin account on first
login -- there's no pre-seeded password.

### Apache Superset

BI / analytical dashboards. Superset re-uses our main-stack Postgres
(`cognee_db`) for its own metadata schema (`superset_metadata`), so
**you only need to keep one Postgres backup process running**.
Dashboards query ClickHouse (via SigNoz's schema) and Postgres
directly.

Default admin login: `admin` / `cognee_admin` (set via
`SUPERSET_SECRET_KEY` and the bootstrap step; **change before
production**).

Exported dashboards live in `monitoring/superset-dashboards/`. The
compose file mounts that directory read-only at
`/opt/cognee-dashboards` inside the container so you can re-import on
a fresh boot:

```bash
docker exec cognee-monitoring-superset \
  superset import-dashboards -p /opt/cognee-dashboards/<name>.json
```

See `monitoring/superset-dashboards/README.md` for the dashboard
roadmap.

---

## Sizing

Single-host budget on a Hetzner CX22 (4 GB RAM, 2 vCPUs):

| Component | Steady state RSS |
| --- | --- |
| ClickHouse + ZooKeeper | ~700 MB |
| 4 x SigNoz services | ~400 MB |
| Apache Superset | ~250 MB |
| Prometheus | ~150 MB |
| **Subtotal** | **~1.5 GB** |

Plus the main 4-database stack (~1.5 GB) plus the MCP server itself
(~200 MB) puts you at ~3.2 GB used. **Tight but viable on a CX22.**

If you want to free up more RAM, swap the 4 SigNoz container images
for the SigNoz **all-in-one** image which bundles them into one
process -- saves ~150 MB at the cost of slightly less operational
isolation. Or, for production, run the observability stack on a
separate small VPS and point the OTel collector at it over the
private network.

---

## License posture

After Phase 4 the entire default Enhanced Cognee deployment -- both
the main 4-DB stack AND the optional observability stack -- is 100%
permissive (MIT + Apache-2.0). The previous Grafana / Loki / Tempo
components were AGPLv3 and have been removed.

`docs/COMMERCIALISATION_LICENSE_GUIDE.md` FAQ "What if I want to
remove all GPL/AGPL components entirely?" now answers "the default
already is".

---

## Migration from the old Grafana stack

If you upgraded an existing deployment that was running the old
Grafana + Loki + Tempo + Jaeger stack:

1. `docker compose -f monitoring/docker-compose-monitoring.yml down`
   (this is the old file path; pulled from git history if you need it).
2. Your old `grafana_data`, `loki_data` Docker volumes still exist on
   disk -- nothing has been destroyed.
3. Pull the Phase 4 compose file (this file).
4. `docker compose -f monitoring/docker-compose-monitoring.yml up -d`.
5. Re-point `OTEL_EXPORTER_OTLP_ENDPOINT` from the old Jaeger collector
   (was `http://localhost:4317` against `jaeger-collector`) to the new
   SigNoz collector at the same port -- **the env var doesn't change**,
   only the container behind it.
6. Rebuild operational dashboards inside SigNoz (RED metrics, latency
   percentiles -- these are mostly auto-generated from your OTel data
   so the rebuild is shallow).
7. Rebuild analytical dashboards inside Apache Superset over the same
   ClickHouse store. Export them to
   `monitoring/superset-dashboards/<name>.json` so they survive a
   fresh-boot.

You can keep your old Grafana volumes around as a historical archive,
or `docker volume rm grafana_data loki_data` once you're satisfied
the new stack is producing equivalent data.

---

## Related docs

- `monitoring/README.md` -- per-file quick reference for this dir
- `docs/STRATEGY.md` section 5.2 + DR-13 -- decision rationale
- `docs/COMMERCIALISATION_LICENSE_GUIDE.md` -- licensing implications
- `docs/LICENSE_AUDIT.md` -- per-component licence detail
- HyperDX docs: https://www.hyperdx.io/docs
- SigNoz docs: https://signoz.io/docs/
- Apache Superset docs: https://superset.apache.org/docs/intro
