# Feature -> License Matrix

> **Purpose:** When porting Enhanced Cognee features into a downstream project
> (e.g. Multi-Agent System / MAS or any other commercial product), you need
> to know which open-source licenses each feature pulls in. This file tags
> every major feature with its license footprint and a verdict for
> commercial / closed-source incorporation.
>
> **Last refreshed:** 2026-05-21. Re-run `pip-licenses --format=markdown
> --output-file=docs/pip-licenses.md` after any dependency bump.

## Verdict legend

| Verdict | Meaning |
| --- | --- |
| **SAFE** | Permissive licenses only (MIT, Apache-2.0, BSD, PSF, ISC, PostgreSQL). Drop into any commercial product without obligations beyond attribution. |
| **SAFE+ATTR** | Same as SAFE but the upstream license requires a `NOTICE` or `LICENSE` attribution file shipped with derivative works (Apache-2.0 §4(d)). |
| **REVIEW** | Weak copyleft (LGPL, MPL-2.0, EPL). Static-linking concerns; dynamic linking + unmodified upstream is usually OK but consult counsel. |
| **OPT-IN** | Strong copyleft / restrictive (GPL, AGPL, BSL, SSPL, Commons Clause). The feature works with this provider but the project defaults to an alternative; do NOT pull in the copyleft provider unless you can comply with its terms. |
| **CONFLICT** | License is incompatible with closed-source distribution. Skip the feature or replace its dependency. |

The Enhanced Cognee codebase itself is **Apache-2.0** (`LICENSE` at repo root). All feature tags below assume the consuming project tolerates Apache-2.0.

---

## A. Memory System Core

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Memory CRUD (add/search/get/update/delete) | `src/mcp_memory_tools.py`, `src/agent_memory_integration.py`, `src/enhanced_cognee_mcp.py` | asyncpg, qdrant-client, redis | Apache-2.0 / Apache-2.0 / MIT | **SAFE+ATTR** |
| Semantic search with embeddings | `src/advanced_search.py`, `src/advanced_search_reranking.py` | qdrant-client / pgvector | Apache-2.0 / PostgreSQL | **SAFE+ATTR** |
| Memory deduplication | `src/memory_deduplication.py`, `src/scheduled_deduplication.py` | datasketch (MinHash) | MIT | **SAFE** |
| Memory summarization | `src/memory_summarization.py`, `src/intelligent_summarization.py`, `src/scheduled_summarization.py` | (LLM API only) | Apache-2.0 (anthropic SDK) | **SAFE+ATTR** |
| Memory consolidation | `src/memory_consolidator.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory expiry / TTL / archival | `src/memory_management.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory tier management | `src/memory_tier_manager.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory provenance | `src/memory_provenance.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory confidence scoring | `src/memory_confidence.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory importance scoring | `src/memory_importance_scorer.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory versioning + undo/redo | `src/memory_versioner.py`, `src/undo_manager.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory observation (EAV structured) | `src/memory_observation.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Memory clustering | `src/memory_consolidator.py` cluster_memories | scikit-learn (BSD-3) | BSD-3 | **SAFE** |
| Memory reranking (Redis-backed personalization) | `src/advanced_search_reranking.py`, `src/memory_reranker.py` | redis-py (cache adapter) | MIT | **SAFE** |

---

## B. Knowledge Graph

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Cognify (text -> KG) | `cognee/` package (upstream) | nltk, spacy (optional) | Apache-2.0 / MIT | **SAFE+ATTR** |
| Entity / relationship extraction | `src/regex_extract_entities` (via MCP tool) | (regex, pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Graph compaction | `src/graph_compactor.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| KG search (Cypher / openCypher) | depends on graph provider chosen | -- | -- | **see C below** |

---

## C. Graph Adapters (pluggable; default = ArcadeDB)

| Adapter | Image / library | License | Note for downstream | MAS verdict |
| --- | --- | --- | --- | --- |
| **arcadedb** (default) | ArcadeDB server + `neo4j` Python driver | **Apache-2.0** / **Apache-2.0** | Default since Phase 2 (PR #20). Dual transport: Bolt (drop-in for neo4j client) or HTTP/JSON. | **SAFE+ATTR** |
| neo4j | Neo4j Community Edition | **GPLv3** | Server is GPLv3; the `neo4j` Python driver is Apache-2.0. Using the GPLv3 server in a hosted commercial offering is risky -- consult counsel. | **OPT-IN** |
| apache_age | Apache AGE (Postgres extension) | **Apache-2.0** | Runs inside PostgreSQL. | **SAFE+ATTR** |
| memgraph | Memgraph Community | **BSL (Business Source License)** | Free for non-production use; converts to MIT after 4 years per BSL. **Don't use in a paid SaaS without a Memgraph commercial license.** | **OPT-IN** |
| kuzu | Kuzu embedded graph DB | **MIT** | Single-process embedded. | **SAFE** |
| networkx_inmemory | NetworkX | **BSD-3** | In-process Python graph; no persistence. | **SAFE** |
| arangodb | ArangoDB | **Apache-2.0** (Community) / **commercial** (Enterprise) | Community edition is Apache-2.0; Enterprise requires a paid license. | **SAFE+ATTR** (Community only) |
| nebulagraph | NebulaGraph | **Apache-2.0** | Distributed graph DB. | **SAFE+ATTR** |
| ladybug | Cognee-native in-process | **Apache-2.0** | Ships as part of this repo. | **SAFE+ATTR** |

---

## D. Vector Adapters (pluggable; default = Qdrant)

| Adapter | Library / server | License | MAS verdict |
| --- | --- | --- | --- |
| **qdrant** (default) | Qdrant server + qdrant-client Python | **Apache-2.0** / Apache-2.0 | **SAFE+ATTR** |
| pgvector | PostgreSQL extension | **PostgreSQL License** (BSD-style) | **SAFE** |
| lancedb | LanceDB (Rust+Python) | **Apache-2.0** | **SAFE+ATTR** |
| chroma | Chroma | **Apache-2.0** | **SAFE+ATTR** |
| weaviate | Weaviate | **BSD-3-Clause** | **SAFE** |
| milvus | Milvus | **Apache-2.0** | **SAFE+ATTR** |

All vector adapters are SAFE for commercial use.

---

## E. Cache Adapters (pluggable; default = Valkey)

| Adapter | Library / server | License | MAS verdict |
| --- | --- | --- | --- |
| **valkey** (default) | Valkey + redis-py | **Apache-2.0** / MIT | Wire-compatible with Redis. Replaced Redis in Phase 5 to avoid BSL/SSPL/AGPLv3. | **SAFE+ATTR** |
| redis | Redis 7.4+ server | **BSL** (7.4 onwards) or AGPLv3 (8+) | **SaaS distribution prohibited under BSL.** Use only if you have a commercial license or self-host for internal use. | **OPT-IN** |
| redis_compat | Labelled alias of valkey for KeyDB / Garnet / Dragonfly | depends on operator's choice | Operator-specific | **REVIEW** |
| in_memory | Python dict | -- | **SAFE** |
| memcached | memcached + pymemcache | **BSD-3** / Apache-2.0 | **SAFE** |
| sqlite (cache mode) | SQLite | **Public Domain** | **SAFE** |

---

## F. Relational Adapters (pluggable; default = PostgreSQL)

| Adapter | Library / server | License | MAS verdict |
| --- | --- | --- | --- |
| **postgres** (default) | PostgreSQL server + asyncpg | **PostgreSQL License** (BSD-style) / Apache-2.0 | **SAFE+ATTR** |
| sqlite | SQLite + aiosqlite | **Public Domain** / BSD-3 | **SAFE** |
| duckdb | DuckDB + duckdb Python | **MIT** | **SAFE** |
| mysql / mariadb | asyncmy driver | **Apache-2.0** (driver) / **GPLv2** (MySQL server) or LGPL (MariaDB) | Driver is safe; **MySQL server is GPLv2** so client+server in one binary is risky. MariaDB LGPL is fine for dynamic linking. | **REVIEW** |
| mssql / sqlserver | aioodbc + Microsoft ODBC Driver 18 | **Apache-2.0** / **Microsoft EULA** | Driver redistribution requires Microsoft's terms. | **REVIEW** |
| oracle | oracledb driver | **UPL** (Universal Permissive License) | Apache-2.0-equivalent; OK. | **SAFE+ATTR** |
| db2 | ibm_db (binding) + IBM Db2 server | **Apache-2.0** (binding) / **IBM EULA** (server) | Server requires IBM license. | **REVIEW** |
| snowflake | snowflake-connector-python | **Apache-2.0** | Service is commercial / paid. | **SAFE+ATTR** |
| databricks | databricks-sql-connector | **Apache-2.0** | Service is commercial / paid. | **SAFE+ATTR** |
| cockroachdb (via postgres wire) | uses postgres adapter | **BSL** (CockroachDB Community 22.1+) | **SaaS distribution prohibited under BSL.** | **OPT-IN** |

---

## G. Multi-Tenancy

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| TenantContext + naming helpers | `src/multi_tenant.py` | (stdlib `contextvars`) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Per-tenant Postgres schema bootstrap | `src/multi_tenant.py` ensure_tenant_schema | asyncpg | Apache-2.0 | **SAFE+ATTR** |
| X-Tenant-ID HTTP middleware | `src/enhanced_cognee_mcp.py` _install_tenant_middleware | fastapi | MIT | **SAFE** |

---

## H. Security

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| PII detection | `src/pii_detector.py` | regex + presidio-analyzer (optional) | (this repo Apache-2.0) / MIT | **SAFE** |
| Encryption at rest (Fernet AES-128-CBC) | `src/encryption_manager.py` | cryptography | Apache-2.0 OR BSD-3 (dual) | **SAFE+ATTR** |
| Audit logging | `src/audit_logger.py` | asyncpg | Apache-2.0 | **SAFE+ATTR** |
| MCP server hardening (API-key + rate limit + payload cap) | `src/mcp_security.py` | (stdlib threading) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Rate limiter (general) | `src/rate_limiter.py` | (stdlib) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Circuit breaker | `src/circuit_breaker.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Session manager | `src/session_manager.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Approval workflow | `src/approval_workflow.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Password hashing | `src/security/auth.py` (if used) | passlib + bcrypt | BSD-3 / Apache-2.0 | **SAFE+ATTR** |

---

## I. GDPR / Compliance

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| GDPR consent + export + delete + tenant isolation verifier | `src/gdpr_manager.py` | asyncpg | Apache-2.0 | **SAFE+ATTR** |

---

## J. Backup / Recovery

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Backup manager | `src/backup_manager.py` | (stdlib + asyncpg) | Apache-2.0 | **SAFE+ATTR** |
| Backup verifier | `src/backup_verifier.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Recovery manager | `src/recovery_manager.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Transaction manager | `src/transaction_manager.py` | asyncpg | Apache-2.0 | **SAFE+ATTR** |

---

## K. Observability

| Feature | Source file(s) / image | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| OpenTelemetry tracing | `src/tracing.py` | opentelemetry-* SDKs | **Apache-2.0** | **SAFE+ATTR** |
| SigNoz APM | `monitoring/docker-compose-monitoring.yml` (signoz/signoz image) | SigNoz server | **MIT** (server), **Apache-2.0** (collector) | **SAFE** |
| Apache Superset BI dashboards | `monitoring/superset-dashboards/*.json` + Superset image | Apache Superset | **Apache-2.0** | **SAFE+ATTR** |
| Prometheus metrics | `src/performance_analytics.py` (get_prometheus_metrics) | prometheus-client | **Apache-2.0** | **SAFE+ATTR** |
| Performance analytics | `src/performance_analytics.py` | asyncpg | Apache-2.0 | **SAFE+ATTR** |
| LLM cost tracker | `src/llm_cost_tracker.py` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |

---

## L. Scheduling / Automation

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Task scheduler | `src/scheduler.py`, `src/maintenance_scheduler.py` | apscheduler | **MIT** | **SAFE** |
| Webhook delivery | `src/webhook_manager.py` | httpx | **BSD-3** | **SAFE** |
| Notifications (Slack / Discord) | `src/notification_manager.py` | httpx | **BSD-3** | **SAFE** |

---

## M. Integration / Plugins

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Plugin loader (data sources) | `src/plugin_loader.py` | (stdlib importlib) | (this repo Apache-2.0) | **SAFE+ATTR** |
| Document processor | `src/document_processor.py` | python-docx, pypdf, beautifulsoup4 | MIT / BSD / MIT | **SAFE** |
| URL ingestion | (via MCP tool ingest_url) | httpx, beautifulsoup4 | BSD-3 / MIT | **SAFE** |
| DB ingestion | (via MCP tool ingest_db) | sqlalchemy + driver-specific | MIT (sqlalchemy) | **SAFE** |
| Claude API integration | `src/claude_api_integration.py` | anthropic SDK | **MIT** | **SAFE** |
| Realtime sync | `src/realtime_sync.py` | redis-py (Valkey pub/sub) | MIT | **SAFE** |
| Realtime WebSocket server | `src/realtime_websocket_server.py` | fastapi + websockets | MIT / BSD-3 | **SAFE** |
| Cross-agent coordination | `src/coordination/` | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |

---

## N. MCP Server

| Variant | Source file | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Stdio MCP server (122 tools) | `bin/enhanced_cognee_mcp_server.py` | mcp / fastmcp | **MIT** / **MIT** | **SAFE** |
| FastAPI HTTP MCP server | `src/enhanced_cognee_mcp.py` | fastapi, uvicorn, pydantic | MIT / BSD-3 / MIT | **SAFE** |

---

## O. Client SDKs

| SDK | Location | License | MAS verdict |
| --- | --- | --- | --- |
| Python | `clients/python/` (PyPI: `enhanced-cognee-client`) | **Apache-2.0** | **SAFE+ATTR** |
| Node.js / TypeScript | `clients/node/` | **Apache-2.0** | **SAFE+ATTR** |
| Go | `clients/go/` | **Apache-2.0** | **SAFE+ATTR** |
| Rust | `clients/rust/` | **Apache-2.0** | **SAFE+ATTR** |

All four SDKs use only permissive transitive dependencies (httpx / undici / net/http / reqwest+rustls). All SAFE for commercial use.

---

## P. Multi-Language Support

| Feature | Source file(s) | OSS dependencies | Licenses | MAS verdict |
| --- | --- | --- | --- | --- |
| Language detection | `src/language_detector.py` | langdetect | **Apache-2.0** | **SAFE+ATTR** |
| Translation | (via MCP translate_text) | googletrans / DeepL (operator-chosen) | varies | **REVIEW** (depends on provider) |
| Multi-language search | `src/multi_language_search.py` | langdetect | Apache-2.0 | **SAFE+ATTR** |
| Cross-language search | `src/multi_language_search.py` cross_language_search | (pure Python) | (this repo Apache-2.0) | **SAFE+ATTR** |

---

## Quick Reference for MAS Integration

If you're porting a feature from Enhanced Cognee into MAS and MAS is closed-source / commercial:

1. **Anything tagged SAFE or SAFE+ATTR is fair game.** Just include the upstream NOTICE / LICENSE attribution in your MAS distribution.
2. **REVIEW tags require legal sign-off.** Usually fine for dynamic linking but the lawyer should look at it.
3. **OPT-IN tags should be replaced with their permissive alternatives:**
   - Neo4j (GPLv3) -> ArcadeDB or Apache AGE
   - Redis (BSL 7.4+) -> Valkey
   - Memgraph (BSL) -> kuzu (embedded) or NetworkX (in-memory)
   - CockroachDB (BSL) -> stay on PostgreSQL
4. **CONFLICT tags must not be redistributed.** None currently flagged.

## Quick Reference for the Default Stack

Enhanced Cognee's default stack is **100% MIT + Apache-2.0 + PostgreSQL-license** (no GPL, no AGPL, no BSL, no SSPL):

| Tier | Default provider | License |
| --- | --- | --- |
| Graph | ArcadeDB | Apache-2.0 |
| Vector | Qdrant | Apache-2.0 |
| Cache | Valkey | Apache-2.0 |
| Relational | PostgreSQL + pgvector | PostgreSQL License (BSD-style) |
| MCP transport | FastMCP + FastAPI | MIT |
| Observability | SigNoz (MIT) + Superset (Apache-2.0) + OTel SDKs (Apache-2.0) | mix |
| Encryption | cryptography (Apache-2.0 OR BSD-3) | mix |

When MAS imports any feature using only the default stack providers, the verdict is **SAFE+ATTR**: keep the NOTICE / LICENSE attributions from this repo in MAS's distribution.

## See also

- [`docs/LICENSE_AUDIT.md`](LICENSE_AUDIT.md) -- per-dependency analysis with Phase 5 license refresh rationale
- [`docs/COMMERCIALISATION_LICENSE_GUIDE.md`](COMMERCIALISATION_LICENSE_GUIDE.md) -- if you ever ship Enhanced Cognee as a paid product
- [`docs/PROFILES.md`](PROFILES.md) -- per-profile adapter matrix and caveats
- `NOTICE` (repo root) -- third-party attributions required by Apache-2.0 §4(d)
