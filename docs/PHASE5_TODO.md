# Phase 5 / Outstanding Items - TODO

Honest accounting of work that's been mentioned but NOT yet shipped as
of 2026-05-20. Each item is grouped with effort estimate, the user
problem it solves, and the trigger that should pull it forward.

The goal here is to make sure nothing falls through the cracks between
sessions; this file is the single landing page for "what's left."

---

## Pluggable adapters - Phase 5 long tail

### Vector tier alternates (high effort)

| Provider | Status | Effort | Trigger |
|---|---|---|---|
| `pgvector` | ✅ **SHIPPED 2026-05-20** | -- | Closes the lean profile vector hole. Narrow API surface. |
| `lancedb` | ✅ **SHIPPED 2026-05-20** | -- | Embedded MIT vector store; laptop / offline. |
| `chroma` | ✅ **SHIPPED 2026-05-20** | -- | Apache-2.0; persistent + network modes. |
| `weaviate` | ✅ **SHIPPED 2026-05-20** | -- | BSD-3; v4 client. |
| `milvus` | ✅ **SHIPPED 2026-05-20** | -- | Apache-2.0; pymilvus v2 client. |

**Status as of 2026-05-20:** all five non-Qdrant vector adapters
shipped. Each follows the same duck-typed `_CollectionDescription` /
`_SearchHit` / `_CountResult` shape so call sites don't have to
special-case the provider. All five expose the narrow QdrantClient
surface Enhanced Cognee actually uses; the long tail of Qdrant
features (rich filters, named vectors, sparse vectors, payload
indexes, quantization, hybrid search) raises `NotImplementedError`
with a clear pointer to the per-adapter sub-section in PROFILES.md.

### Graph tier alternates with different query languages

| Provider | Query language | Status | Notes |
|---|---|---|---|
| `arangodb` | AQL | ✅ **SHIPPED 2026-05-20** | Cypher-to-AQL translator for the narrow subset our codebase uses. Multi-hop / WHERE clauses raise `NotImplementedError`. |
| `nebulagraph` | nGQL | ✅ **SHIPPED 2026-05-20** | Routes through NebulaGraph 3+ openCypher mode; only the literal-RETURN form gets a `YIELD` rewrite. |
| `ladybug` | Cognee-native | ✅ **SHIPPED 2026-05-20** | In-process adapter mirroring the `networkx_inmemory` shape; uses ladybug's native graph API for COUNT / DETACH DELETE / RETURN-all. |

### Relational tier alternates (added 2026-05-20)

| Provider | Status | Notes |
|---|---|---|
| `duckdb` | ✅ **SHIPPED 2026-05-20** (PR 10) | MIT-licensed embedded columnar OLAP database. asyncpg-shaped facade via `asyncio.to_thread` over the sync duckdb driver. Great for analytics workloads + Superset BI dashboards. See `docs/PROFILES.md` for caveats. |
| `mysql` / `mariadb` | ✅ **SHIPPED 2026-05-20** (PR 10) | MySQL 8+ / MariaDB 10+ via the asyncmy (Apache-2.0) driver. Targets managed offerings: Aurora MySQL, Cloud SQL for MySQL, Azure DB for MySQL, PlanetScale, Vitess. |
| CockroachDB | 🟢 **WORKS VIA postgres** | Speaks Postgres wire protocol; existing `postgres` adapter targets it with no code changes. Set `POSTGRES_HOST=cockroach.internal POSTGRES_PORT=26257`. See PROFILES.md for caveats (no pgvector, no AGE). |

### Misc

- `redis_compat` -- wire-compatible alternative Redis fork (e.g. KeyDB
  / Garnet / Dragonfly). ✅ **SHIPPED 2026-05-20** as a labelled alias
  of the valkey adapter. Operational intent in env vars: "this isn't
  real Redis OR Valkey, it's a third-party fork." See
  `src/db_adapters/cache_redis_compat.py`.

---

## Operational verification (need a running stack)

| Item | Why deferred | What's needed |
|---|---|---|
| Live integration tests against ArcadeDB | 🟡 **PARTIAL 2026-05-20** | `tests/integration/test_arcadedb_integration.py` -- 4 tests (connectivity ping, record iteration, write round-trip, async). Skip locally + in CI because the public `arcadedata/arcadedb:26.x` image doesn't ship the Bolt plugin our adapter speaks (the adapter uses `neo4j-driver`). Run locally via `docker compose -f docker/docker-compose-enhanced-cognee.yml up arcadedb` -- which mounts an enterprise license file -- to exercise them. CI revisit when a community Bolt build lands. |
| Live integration tests against Apache AGE | ✅ **SHIPPED 2026-05-20** | `tests/integration/test_apache_age_integration.py` -- 4 tests including native `_AGENode` / `_AGERelationship` round-trips. CI swaps the Postgres image to `apache/age:PG16_latest` and bootstraps `CREATE EXTENSION age` + `create_graph('cognee_test_graph')` via an idempotent psql step. |
| Live verification of SigNoz + Superset stack | ✅ **SCAFFOLDED 2026-05-20** (PR 14) | `tests/integration/test_signoz_smoke.py` emits an OTel span with a unique marker, queries SigNoz's API for it, and asserts it lands within 5s. Gated by `ENHANCED_RUN_SIGNOZ_SMOKE=1`. Run after booting `monitoring/docker-compose-monitoring.yml`. |
| Exported Superset dashboards | ✅ **SHIPPED 2026-05-20** | All 5 dashboards (memory_growth / agent_activity / llm_cost_trends / dedup_effectiveness / perf_regression) ship as importable Superset 4.x JSON in `monitoring/superset-dashboards/` with a shared `_dataset_definitions.yaml`. The queries hit the real schemas (`shared_memory.documents`, `shared_memory.llm_usage`, `shared_memory.embeddings`, `signoz_traces.signoz_index_v2`); the dashboards light up as soon as data flows. |

---

## Performance + benchmarks (H4)

| Item | Status | Effort | Trigger |
|---|---|---|---|
| Locust scenarios against the live stack | ✅ **SHIPPED 2026-05-20** | -- | `tests/load/locustfile.py` now ships 8 `HttpUser` classes -- the original 3 memory-CRUD profiles plus 4 Phase 5 additions (SemanticSearchUser, KnowledgeGraphUser, GDPRWorkflowUser, BackupVerifyUser) + the opt-in HealthCheckUser. See `tests/load/README.md` for run instructions + recommended SLAs. |
| Perf-regression dashboard in SigNoz | ✅ **SHIPPED 2026-05-20** | -- | Ships as `monitoring/superset-dashboards/perf_regression.json` -- p50/p95/p99 latency, error %, RPS, slowest-endpoints, all sourced from SigNoz's ClickHouse trace store. Use to compare Locust runs against a baseline. |
| Benchmarks comparing graph providers (arcadedb / neo4j / apache_age / kuzu) | ✅ **SHIPPED 2026-05-20** | -- | `tests/benchmarks/run_provider_comparison.py` drives Locust against 5 provider permutations (default / lean / neo4j_stack / embedded / memgraph_kuzu) and emits a comparison report. Caller boots the underlying services; runner shells out to `locust --headless --csv` and parses the CSV output into JSON + markdown comparison tables. |

---

## AGE adapter feature gaps

The `apache_age` adapter ships in a deliberately narrow state. Tracked
gaps:

| Gap | Effort | Trigger |
|---|---|---|
| Parameterised Cypher (`$param` syntax) | ✅ **SHIPPED 2026-05-20** | Now passes through AGE's three-arg `cypher(graph, $$ ... $$, agtype_map)` form via psycopg2 parameter binding. Rejects payloads containing `$$` to prevent dollar-quote breakout. |
| Async session API | ✅ **SHIPPED 2026-05-20** | `get_async_graph_driver()` returns an asyncpg-backed `_AsyncAGEDriver`. Use `async with driver.session() as s: await s.run(cypher)`. |
| Returning native graph elements as neo4j `Node` / `Relationship` objects | ✅ **SHIPPED 2026-05-20** | `_unwrap_agtype` now converts `::vertex` payloads to `_AGENode` and `::edge` payloads to `_AGERelationship`, both shaped like `neo4j.graph.Node` / `Relationship` (`.id` / `.labels` / `.type` / `.start_node` / `.end_node` / dict protocol). `::path` decodes to `List[_AGENode \| _AGERelationship]`. |

---

## Triage policy

When considering whether to pull something from this file forward:

1. **Customer ask** -> ship it. Phase 5 is explicitly demand-driven.
2. **Adjacent work** -> ship it. If you're already touching the
   graph layer, fold in the missing graph adapter someone's asked
   for; if you're already wiring CI, fold in the integration tests.
3. **Speculative** -> leave on this list. "Maybe we'll need pgvector
   someday" is not a reason to spend 3-5 days shipping it now.

---

## Cross-reference

- Roadmap source of truth: [`STRATEGY.md` §4.3](./STRATEGY.md#43-implementation-phases-effort-estimates-revised-2026-05-19)
- Decision records: [`STRATEGY.md` §9](./STRATEGY.md#9-appendix-decision-records)
- Active provider matrix: [`PROFILES.md`](./PROFILES.md)
- Session handover: [`HANDOVER.md`](./HANDOVER.md)
