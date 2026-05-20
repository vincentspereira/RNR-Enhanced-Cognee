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
| `pgvector` | ✅ **SHIPPED 2026-05-20** | -- | Closes the lean profile vector hole. Narrow API surface (see docs/PROFILES.md) -- no rich search filters, no named/sparse vectors, no quantization. |
| `lancedb` | 📋 | 3-5 days | Embedded-DB use case (laptop / offline) |
| `weaviate` | 📋 | 3-5 days | Customer already running Weaviate |
| `milvus` | 📋 | 3-5 days | Large-scale vector workload requirement |
| `chroma` | 📋 | 2-3 days | Light Chroma-shaped workload requirement |

**Why the rest are still deferred:** the vector tier surface in this
codebase is the `QdrantClient` API -- `get_collections` /
`get_collection` / `create_collection` / `upsert` / `search` / etc.
Each alternate provider has to mirror that across every call site OR
sit behind a thicker translation layer. pgvector (the first one
shipped) sets the abstraction pattern via the `_PgVectorClient` shim
in `src/db_adapters/vector_pgvector.py`; subsequent adapters can
follow the same `_CollectionDescription` / `_SearchHit` / etc.
duck-typing pattern. Per HANDOVER §4 Phase 5: "Build these only when
a paying customer asks or you're already in that area."

### Graph tier alternates with different query languages (medium effort)

| Provider | Query language | Status | Effort | Notes |
|---|---|---|---|---|
| `arangodb` | AQL | 📋 | 3-5 days | Need Cypher-or-AQL translation layer |
| `nebulagraph` | nGQL | 📋 | 3-5 days | Distributed scale-out; nGQL ≠ Cypher |
| `ladybug` | Cognee-native | 📋 | 1-3 days | Upstream Cognee's experimental engine; needs upstream investigation first |

**Why deferred:** these all need a Cypher-to-X translation layer
because Enhanced Cognee call sites speak Cypher. The translation work
is the bottleneck, not the connection layer.

### Misc

- `redis_compat` -- wire-compatible alternative Redis fork (e.g. KeyDB
  / Garnet). Status 📋. Effort: ~2 hours. Currently the `redis`
  provider routes through the Valkey adapter anyway since they're
  wire-compatible; this is just labelling.

---

## Operational verification (need a running stack)

| Item | Why deferred | What's needed |
|---|---|---|
| Live integration tests against ArcadeDB | HANDOVER §9 acceptance criterion. Integration tests are `continue-on-error: true` so non-blocking. | Wire CI to bring up the ArcadeDB stack + run `tests/integration/`. |
| Live integration tests against Apache AGE | Same as above. | Wire CI to install Postgres with AGE extension. |
| Live verification of SigNoz + Superset stack | Compose YAML validates, but runtime smoke test requires booting the stack and checking traces appear in the UI. | Bring up `monitoring/docker-compose-monitoring.yml`, send a trace via `src/tracing.py`, screenshot/verify. |
| Exported Superset dashboards | The four dashboard slots in `monitoring/superset-dashboards/README.md` (memory_growth / agent_activity / llm_cost_trends / dedup_effectiveness) are placeholders. | Build them in a live Superset instance with representative data, then `superset export-dashboards -p /opt/cognee-dashboards/<name>.json` to harvest the JSON. |

---

## Performance + benchmarks (H4)

| Item | Effort | Trigger |
|---|---|---|
| Locust scenarios against the live stack | 1-2 days | Documented p50/p95/p99 latency under load is a pre-commercial-release ask. |
| Perf-regression dashboard in SigNoz | 0.5 days | Once Locust is wired, point its OTel output at SigNoz. |
| Benchmarks comparing graph providers (arcadedb / neo4j / apache_age / kuzu) | 1-2 days | Used to defend the Phase 2 default choice with numbers, not just licence rationale. |

---

## AGE adapter feature gaps

The `apache_age` adapter ships in a deliberately narrow state. Tracked
gaps:

| Gap | Effort | Trigger |
|---|---|---|
| Parameterised Cypher (`$param` syntax) | 2-3 days | Currently raises `NotImplementedError`. Needs translation of `$param` into AGE's `cypher('graph', $$ ... $$, %s::agtype)` form via psycopg2 parameter binding. |
| Async session API | 3-5 days | Currently raises `NotImplementedError`. Would need an asyncpg-based variant; not asyncpg's natural use case. |
| Returning native graph elements as neo4j `Node` / `Relationship` objects | 2-3 days | Today, callers receive parsed agtype JSON (a dict). A real Node wrapper would close the API gap with the other graph providers. |

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
