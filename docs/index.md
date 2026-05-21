# Enhanced Cognee

Enterprise-grade AI memory infrastructure with multi-tenant support, **30 pluggable storage providers** across 4 tiers, **122 MCP tools**, and 4 cross-language client SDKs.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-green)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-4661%20passing-brightgreen)](https://github.com/vincentspereira/Enhanced-Cognee)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/vincentspereira/Enhanced-Cognee)
[![Providers](https://img.shields.io/badge/pluggable%20providers-30%20across%204%20tiers-blueviolet)](PROFILES.md)
[![SDKs](https://img.shields.io/badge/SDKs-Python%20%7C%20Node%20%7C%20Go%20%7C%20Rust-blueviolet)](SDK_PUBLISHING.md)

## What is Enhanced Cognee

Enhanced Cognee is a fork of [Cognee](https://github.com/topoteretes/cognee) that adds production-grade infrastructure: multi-tenant data partitioning, 30 pluggable storage providers, four official client SDKs, MCP server hardening (API-key + rate limit + payload cap), HTTPS/TLS support, encryption at rest, GDPR tooling, backup + recovery, and SigNoz + Apache Superset observability.

It exposes 122 MCP tools (Model Context Protocol) for AI IDEs like Claude Code, Cursor, and Continue, plus a FastAPI HTTP variant for cross-language SDK use.

## Default stack -- 100% MIT + Apache-2.0

| Tier | Default provider | License |
| --- | --- | --- |
| Graph | **ArcadeDB** | Apache-2.0 |
| Vector | **Qdrant** | Apache-2.0 |
| Cache | **Valkey** | Apache-2.0 |
| Relational | **PostgreSQL + pgvector** | PostgreSQL License |

Every tier accepts a drop-in alternate via `ENHANCED_*_PROVIDER` env vars -- see [Pluggable DB Backends](PLUGGABLE_DB_BACKENDS.md) for the full matrix.

## Quick links

- [Quick Start](QUICK_START.md) -- install in 30 seconds + first MCP call
- [Pluggable DB Backends](PLUGGABLE_DB_BACKENDS.md) -- 4-tier factory architecture + how to add adapters
- [Profiles](PROFILES.md) -- 5 pre-baked deployment profiles + per-adapter caveat tables
- [Deployment Quickstart](DEPLOYMENT_QUICKSTART.md) -- local + VPS deployment runbooks
- [Monitoring](MONITORING.md) -- SigNoz + Apache Superset observability stack
- [Secrets Management](SECRETS_MANAGEMENT.md) -- four levels of secrecy from laptop dev to compliance-driven
- [SDK Publishing](SDK_PUBLISHING.md) -- how to push Node / Rust / Go SDKs to npm / crates.io / pkg.go.dev
- [Feature -> License Matrix](FEATURE_LICENSE_MATRIX.md) -- per-feature licensing verdict for downstream commercial use (MAS etc.)
- [License Audit](LICENSE_AUDIT.md) -- per-component license analysis
- [Commercialisation Guide](COMMERCIALISATION_LICENSE_GUIDE.md) -- compliance considerations for paid use

## Key features

### Memory + Knowledge Graph

- 122 MCP tools across 25+ categories (CRUD, search, dedup, summarisation, GDPR, backup, undo/redo, ...)
- Semantic search with vector embeddings (Qdrant + pgvector + LanceDB + Chroma + Weaviate + Milvus)
- Knowledge graph ingestion (`cognify`) with 9 graph backends including ArcadeDB / Apache AGE / Memgraph / Kuzu
- Memory deduplication, summarisation, consolidation, tiering, provenance, confidence scoring, importance scoring
- Versioning with undo / redo
- Real Redis-backed personalization (agent affinity + interaction recency + query affinity)

### Production Infrastructure

- Multi-tenant data partitioning (`TenantContext` + per-tenant Postgres schema + HTTP X-Tenant-ID middleware)
- Cross-language client SDKs: Python on PyPI; Node / Go / Rust registry-ready
- MCP server hardening: API-key auth + per-tool token-bucket rate limit + payload cap
- HTTPS/TLS support on the FastAPI server
- Encryption at rest (Fernet AES-128-CBC) with key rotation
- Audit logging + GDPR (consent, export, delete, tenant-isolation verifier)
- Backup + verification + recovery + transaction manager
- 4,661 tests passing, 95% coverage

### Observability

- SigNoz APM (replaces Grafana / Loki / Tempo / Jaeger -- all Apache-2.0)
- Apache Superset BI with 5 importable dashboards
- Prometheus metrics, OpenTelemetry tracing
- LLM cost tracker with per-model budgets

## Performance

Real Locust benchmark against the live default stack (ArcadeDB + Qdrant + Valkey + PostgreSQL):

| Metric | Value |
| --- | --- |
| RPS | 48.86 |
| p50 latency | 11 ms |
| p95 latency | 14 ms |
| p99 latency | 17 ms |
| Error rate | 0.00% |

60s run with 20 concurrent users + 5/sec spawn rate. See [`tests/benchmarks/baselines/`](https://github.com/vincentspereira/Enhanced-Cognee/tree/main/tests/benchmarks/baselines).

## Get started

```bash
git clone https://github.com/vincentspereira/Enhanced-Cognee.git
cd Enhanced-Cognee
docker compose -p enhanced-cognee -f config/docker/docker-compose-enhanced-cognee.yml up -d
python -m uvicorn src.enhanced_cognee_mcp:app --port 8080
```

Then point Claude Code's MCP config at `bin/enhanced_cognee_mcp_server.py`. Full setup in [Quick Start](QUICK_START.md).

## License

[Apache-2.0](https://github.com/vincentspereira/Enhanced-Cognee/blob/main/LICENSE).
