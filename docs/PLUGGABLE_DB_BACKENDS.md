# Pluggable Database Backends Design

> **Status (2026-05-20):** ✅ **All 5 phases SHIPPED** across PRs
> #19-#31. The full pluggable stack is live -- 13 providers across
> 4 tiers, factory-dispatched via `ENHANCED_*_PROVIDER` env vars.
> See [`PROFILES.md`](PROFILES.md) for the user-facing matrix and
> per-adapter caveats. The sections below are preserved as a record
> of the original design + effort estimate; the implementation
> matched the plan closely.

## Shipped state (2026-05-20)

| Tier        | Providers                                                                                                |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| Graph (9)   | `arcadedb` (default) / `neo4j` / `apache_age` / `memgraph` / `kuzu` / `arangodb` / `nebulagraph` / `ladybug` / `networkx_inmemory` |
| Vector (6)  | `qdrant` (default) / `pgvector` / `lancedb` / `chroma` / `weaviate` / `milvus`                           |
| Cache (5)   | `valkey` (default) / `redis` / `redis_compat` / `in_memory` / `memcached`                                |
| Relational (2) | `postgres` (default) / `sqlite`                                                                       |

**Shared infrastructure:**
- `src/db_factory.py` -- env-var dispatch for every tier
- `src/db_adapters/` -- 24 adapter modules (one per provider + shared helpers)
- `src/db_adapters/_vector_filter.py` -- shared qdrant-Filter -> backend translator wired into all 5 vector adapters
- `tests/unit/test_db_factory.py` + per-adapter test modules -- 100% factory coverage
- `tests/integration/test_apache_age_integration.py` -- live AGE round-trips in CI
- `tests/benchmarks/run_provider_comparison.py` -- cross-provider Locust comparison runner

---

## Original Design Question (preserved for context)

**Question:** Original Cognee lets you pick the database (LanceDB / Qdrant /
PGVector / Weaviate / Milvus for vectors; Neo4j / Kuzu / Memgraph for graph).
Should RNR Enhanced Cognee do the same? Especially if it'll be incorporated into
MAS for commercialisation?

**Short answer:** **Yes -- but introduce it gradually.** RNR Enhanced Cognee was
designed around a fixed 4-database stack for operational simplicity. As we
grow toward commercial use cases, pluggability becomes a real win. This
document scopes out HOW to add it without breaking existing deployments.

---

## Why It Matters

| Reason | Concrete example |
|---|---|
| **Customer infrastructure constraints** | Acme Corp already runs Memgraph; they don't want to install Neo4j too. |
| **License compliance** | Customer's compliance team rejects GPLv3; they need Apache AGE on PostgreSQL instead. |
| **Cost optimisation** | Solo developer with 4 GB RAM wants to use SQLite + pgvector inside the same Postgres rather than Postgres + Qdrant separately. |
| **Performance preference** | High-scale customer uses Milvus for billion-vector indices; Qdrant doesn't scale that far for them. |
| **Vendor lock-in avoidance** | Auditor requires "we can swap any DB component within 4 weeks." |

These are all legitimate. The cost: more code paths to test (and a more
complex test matrix). With our current 4158-test suite already in place,
this cost is manageable.

---

## What Original Cognee Does

Upstream Cognee has:

- **Vector DBs:** LanceDB (default), Qdrant, PGVector, Weaviate, Milvus,
  Chroma — selected via env var `VECTOR_DB_PROVIDER`.
- **Graph DBs:** NetworkX (default, in-memory), Neo4j, Memgraph, Kuzu,
  Ladybug — selected via env var `GRAPH_DATABASE_PROVIDER`.
- **Relational DBs:** SQLite (default), PostgreSQL — selected via
  `DB_PROVIDER`.
- **Cache:** none by default; optional Redis.

The pattern is: **factory modules** with a switch on env var → return the
right driver instance. E.g.,
`cognee/infrastructure/databases/vector/create_vector_engine.py`.

RNR Enhanced Cognee uses this factory pattern under the hood (we inherit it
from upstream) but we **hard-code** which providers we use because we ship
the Docker stack pre-configured.

---

## Proposed Architecture for RNR Enhanced Cognee

### Tier 1: Production Defaults (no change to current behaviour)

`docker-compose-enhanced-cognee.yml` continues to ship the 4-database
stack. Out-of-the-box users get the validated production setup.

### Tier 2: Override via Environment Variables

Add support for these env vars in our deployment scripts and `bin/enhanced_cognee_mcp_server.py`:

| Env var | Default | Alternative values |
|---|---|---|
| `ENHANCED_VECTOR_PROVIDER` | `qdrant` | `pgvector`, `weaviate`, `milvus`, `chroma`, `lancedb` |
| `ENHANCED_GRAPH_PROVIDER` | `neo4j` | `apache_age`, `memgraph`, `kuzu`, `networkx_inmemory` |
| `ENHANCED_CACHE_PROVIDER` | `valkey` | `redis_compat`, `memcached`, `in_memory` |
| `ENHANCED_RELATIONAL_PROVIDER` | `postgres` | `sqlite` (limited; testing only) |

Set them in `.env` or via systemd `EnvironmentFile=`. The MCP server reads
them at startup and instantiates the right drivers.

### Tier 3: Profile Presets

Bundle ready-to-use profiles for common cases:

```bash
# Production (the current default)
ENHANCED_PROFILE=production    # postgres + qdrant + neo4j + valkey

# Apache-only (no GPL, for strict compliance)
ENHANCED_PROFILE=apache_only   # postgres + qdrant + apache_age + valkey

# Lean (for laptops / small servers)
ENHANCED_PROFILE=lean          # postgres + pgvector + networkx_inmemory + in_memory_cache
# (one container instead of four; pgvector embedded in postgres)

# Cloud-managed (use customer's existing infra)
ENHANCED_PROFILE=byo           # all providers read from env vars; no Docker
```

Each profile is a YAML file in `deploy/profiles/`. The installer asks
which profile, sets env vars, optionally brings up matching containers.

---

## Implementation Plan (effort estimates)

### Phase 1: Plumbing (1 week)

Goal: env var routing works for all 4 DB tiers without changing functionality.

1. Audit current hard-coded providers in `src/agent_memory_integration.py`
   and replace direct imports with a factory call:
   ```python
   from src.db_factory import get_vector_engine, get_graph_engine, ...
   self.qdrant_client = get_vector_engine()  # was: QdrantClient(...)
   self.neo4j_driver = get_graph_engine()    # was: GraphDatabase.driver(...)
   ```
2. Create `src/db_factory.py` with `get_*_engine()` functions that read env
   vars and return the right driver.
3. For each NEW provider, implement an adapter class with the methods
   RNR Enhanced Cognee's code expects.
4. Update test fixtures to mock the factory, not the specific drivers.

### Phase 2: Apache AGE adapter (1 week)

Highest-value alternative: removes the only GPL component.

1. Write `src/db_adapters/graph_apache_age.py` implementing the Bolt-like
   interface our code uses.
2. Translate the small set of Cypher queries we issue from Neo4j-flavoured
   to AGE-flavoured (mostly the same).
3. Run the full integration test suite against AGE; document any feature
   gaps (e.g., APOC procedures).
4. Add `apache_age` profile.

### Phase 3: pgvector-only "lean" profile (3 days)

Goal: solo dev / laptop / low-RAM customers get a one-container setup.

1. `src/db_adapters/vector_pgvector.py` implementing vector ops via pgvector
   inside the existing Postgres.
2. `lean` profile that omits Qdrant + Neo4j + Valkey containers; uses
   pgvector + networkx_inmemory + in-process cache.

### Phase 4: Remaining adapters (2-3 weeks)

- Memgraph adapter (similar to Neo4j; trivial)
- Milvus adapter (large-scale vector use)
- Weaviate adapter (hybrid search use)
- LanceDB adapter (for upstream-cognee compatibility)

Build these on demand based on customer requests.

### Phase 5: Documentation + tests (1 week)

- `docs/PROFILES.md` documenting each preset
- Per-adapter feature matrix (which MCP tools work fully, partially, not
  at all on each backend)
- Integration tests parametrised by adapter

**Total estimate: 5-7 weeks of focused work.** Realistically spread over
2-3 months alongside other product work.

---

## Why NOT to do this immediately

Counterpoints worth considering before starting:

1. **The current 4-DB stack works.** 4158 tests pass, all 6 production
   phases complete. Adding pluggability adds a test-matrix multiplier
   (4 vector backends × 3 graph backends × 2 cache backends = 24 cells
   to validate).

2. **Most customers will pick the default.** From experience, ~80% of
   self-hosted-software customers run the recommended stack. The other
   20% are vocal but represent enterprise sales conversations where you
   can quote a custom-integration consulting fee.

3. **License risk is manageable today.** As `COMMERCIALISATION_LICENSE_GUIDE.md`
   explains, the Neo4j GPL concern is solved by "customer pulls their own
   Neo4j image" without needing Apache AGE.

4. **Premature abstraction.** If we add 5 vector backends now, only 1 is
   battle-tested. The other 4 will have undocumented edge cases that bite
   you at 2am.

**Recommended timing:** Add Apache AGE adapter first (Phase 2 only, 1 week)
when you hit the first compliance request. Add more backends only when a
paying customer asks. Otherwise, defer.

---

## Decision Matrix

| You should add pluggability NOW if... | You can defer if... |
|---|---|
| A specific paying customer requires it | No customer has asked |
| Compliance audit (SOC 2, ISO 27001) requires "swap any component in 4 weeks" | Self-hosted by single developer / small team |
| MAS commercial product will ship NEXT QUARTER | MAS is still in research / dogfooding |
| Investor / acquirer is doing diligence on architecture flexibility | Internal use only |
| You're already touching the DB layer for a different reason | You're focused on other features |

---

## Backwards Compatibility Guarantee

Whatever we add, the **default behaviour must not change** for existing users:

```yaml
# This must continue to work unmodified:
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
# → still gives you Postgres + Qdrant + Neo4j + Valkey
```

We add new capability via env vars; we don't change existing defaults.

---

## Relation to MAS

If RNR Enhanced Cognee is incorporated into MAS:

- **If MAS has its own DB choices already**, pluggability is critical.
  Customers shouldn't run TWO Postgres instances (MAS's + Enhanced
  Cognee's). They should run ONE and have both services share it.

- **If MAS is greenfield**, the production-default 4-DB stack is fine.

This is the strongest argument for adding pluggability BEFORE the MAS
integration goes commercial. Recommendation: **plan Phase 1 + Phase 2
(Apache AGE) before MAS goes to paying customers**. Phases 3-4-5 can wait.
