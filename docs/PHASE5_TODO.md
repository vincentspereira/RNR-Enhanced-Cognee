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
| Live integration tests against ArcadeDB | HANDOVER §9 acceptance criterion. Integration tests are `continue-on-error: true` so non-blocking. | Wire CI to bring up the ArcadeDB stack + run `tests/integration/`. |
| Live integration tests against Apache AGE | Same as above. | Wire CI to install Postgres with AGE extension. |
| Live verification of SigNoz + Superset stack | Compose YAML validates, but runtime smoke test requires booting the stack and checking traces appear in the UI. | Bring up `monitoring/docker-compose-monitoring.yml`, send a trace via `src/tracing.py`, screenshot/verify. |
| Exported Superset dashboards | The four dashboard slots in `monitoring/superset-dashboards/README.md` (memory_growth / agent_activity / llm_cost_trends / dedup_effectiveness) are placeholders. | Build them in a live Superset instance with representative data, then `superset export-dashboards -p /opt/cognee-dashboards/<name>.json` to harvest the JSON. |

---

## Performance + benchmarks (H4)

| Item | Status | Effort | Trigger |
|---|---|---|---|
| Locust scenarios against the live stack | ✅ **SHIPPED 2026-05-20** | -- | `tests/load/locustfile.py` now ships 8 `HttpUser` classes -- the original 3 memory-CRUD profiles plus 4 Phase 5 additions (SemanticSearchUser, KnowledgeGraphUser, GDPRWorkflowUser, BackupVerifyUser) + the opt-in HealthCheckUser. See `tests/load/README.md` for run instructions + recommended SLAs. |
| Perf-regression dashboard in SigNoz | 📋 | 0.5 days | Once Locust is wired (now done), point its OTel output at SigNoz. Needs a running stack. |
| Benchmarks comparing graph providers (arcadedb / neo4j / apache_age / kuzu) | 📋 | 1-2 days | Used to defend the Phase 2 default choice with numbers, not just licence rationale. Needs a running stack. |

---

## AGE adapter feature gaps

The `apache_age` adapter ships in a deliberately narrow state. Tracked
gaps:

| Gap | Effort | Trigger |
|---|---|---|
| Parameterised Cypher (`$param` syntax) | ✅ **SHIPPED 2026-05-20** | Now passes through AGE's three-arg `cypher(graph, $$ ... $$, agtype_map)` form via psycopg2 parameter binding. Rejects payloads containing `$$` to prevent dollar-quote breakout. |
| Async session API | ✅ **SHIPPED 2026-05-20** | `get_async_graph_driver()` returns an asyncpg-backed `_AsyncAGEDriver`. Use `async with driver.session() as s: await s.run(cypher)`. |
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
