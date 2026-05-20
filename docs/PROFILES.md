# Deployment Profiles

**Status:** Phase 3 (Apache AGE + lean profile) shipped 2026-05-19.
Phase 5 quick-win adapters (Memgraph / Kuzu / NetworkX-in-memory /
Memcached / SQLite) shipped 2026-05-20. See "Provider matrix" below
for the full set and the "Deferred" section for what's still pending.

Enhanced Cognee ships four deployment **profiles** -- presets that pin
the four `ENHANCED_*_PROVIDER` env vars to a coherent combination. They
exist so that the same code base can run on a laptop, a 4 GB VPS, an
enterprise cluster, or someone's BYO managed cloud, without forking the
codebase.

A profile is just a set of env vars. There's no global "profile switch"
toggle -- `docker compose up -d` always brings up whatever the
`docker-compose-enhanced-cognee.yml` file declares; the **profile** is
the choice of env vars you export before launching the MCP server.

## TL;DR

| Profile        | Relational | Vector   | Graph        | Cache       | Containers needed                 | Best for                                      |
| -------------- | ---------- | -------- | ------------ | ----------- | --------------------------------- | --------------------------------------------- |
| `production`   | postgres   | qdrant   | arcadedb     | valkey      | postgres + qdrant + arcadedb + valkey | Production; what the default compose ships |
| `apache_only`  | postgres   | qdrant   | apache_age   | valkey      | postgres (with AGE) + qdrant + valkey  | All-Apache-2.0 stack, no JVM container    |
| `lean`         | postgres   | pgvector | apache_age   | in_memory   | postgres (with AGE + vector)      | Laptops / small VPS / offline (1 container)   |
| `byo`          | (env)      | (env)    | (env)        | (env)       | none (all external)               | Managed cloud / multi-tenant SaaS             |

All four resolve through `src/db_factory.py`. The `ENHANCED_*_PROVIDER`
env vars are the public interface; `*_BACKEND` legacy aliases are still
honoured at lower precedence.

---

## production (default)

The default 4-database stack since Phase 2:

```bash
ENHANCED_RELATIONAL_PROVIDER=postgres
ENHANCED_VECTOR_PROVIDER=qdrant
ENHANCED_GRAPH_PROVIDER=arcadedb        # Apache-2.0; flipped from neo4j in Phase 2
ENHANCED_CACHE_PROVIDER=valkey          # Apache-2.0; replaced redis in Phase 1
```

`docker compose -f docker/docker-compose-enhanced-cognee.yml up -d` brings
this up out of the box. This is the recommended path for any deployment
that has multi-GB headroom and wants the best operational experience
(graph-native indexes, multi-protocol API, dedicated cache pub/sub).

100% Apache-2.0 across the database tier. The only AGPL-tinged
components are in the *optional* monitoring stack
(`docker/docker-compose-monitoring.yml`) and are being swapped to SigNoz
+ Superset in Phase 4.

---

## apache_only

Same as `production` but with the graph layer collapsed into Postgres:

```bash
ENHANCED_RELATIONAL_PROVIDER=postgres
ENHANCED_VECTOR_PROVIDER=qdrant
ENHANCED_GRAPH_PROVIDER=apache_age     # Apache AGE Postgres extension
ENHANCED_CACHE_PROVIDER=valkey
```

Use when you want:

- One fewer container (no Java runtime)
- A single Postgres-shaped operational surface (backups, monitoring, tooling)
- The strictest interpretation of "Apache-2.0 throughout" (AGE is ASF)

You'll need to enable AGE inside the Postgres container -- see the
`apache_only` setup section below.

---

## lean

Smallest viable stack -- one Postgres container plus the MCP server.
Updated 2026-05-20 to use `pgvector` now that the adapter has shipped:

```bash
ENHANCED_RELATIONAL_PROVIDER=postgres
ENHANCED_VECTOR_PROVIDER=pgvector       # was: qdrant; pgvector shipped 2026-05-20
ENHANCED_GRAPH_PROVIDER=apache_age
ENHANCED_CACHE_PROVIDER=in_memory       # process-local dict
```

`deploy/profiles/lean.yaml` documents the exact set. **One container**:
Postgres (with the `vector` extension auto-installed by the pgvector
adapter on first `create_collection`, and the `age` extension created
manually -- see the `apache_only` setup section below).

Limitations (intentional):

- Cache loses state on process restart (`in_memory`)
- No pub/sub -- realtime sync degrades gracefully but pub/sub channels noop
- Single-process only -- a second MCP process won't share cache state
- pgvector adapter has a narrow Qdrant API surface; see its
  sub-section below for what's supported

`lean` is not recommended for production; it exists so that "give me
the smallest possible Enhanced Cognee" works as a single Postgres
container.

---

## byo (Bring Your Own infra)

```bash
ENHANCED_RELATIONAL_PROVIDER=postgres
ENHANCED_VECTOR_PROVIDER=qdrant
ENHANCED_GRAPH_PROVIDER=arcadedb        # or neo4j / apache_age
ENHANCED_CACHE_PROVIDER=valkey          # or redis

# Connection details for each tier point to your existing infra
POSTGRES_HOST=postgres.internal
POSTGRES_PORT=5432
QDRANT_HOST=qdrant.internal
NEO4J_URI=bolt://graph.internal:7687    # or ARCADEDB_URI
REDIS_HOST=cache.internal
```

No compose file is involved -- the MCP server just connects to whatever
endpoints you point it at. Common when you're on AWS RDS for Postgres,
Qdrant Cloud for vectors, etc.

---

## Phase 5 adapter sub-sections

### Memgraph adapter

The Memgraph adapter is structurally identical to the ArcadeDB / Neo4j
adapter (it's another Bolt-protocol target). Its default URI is
`bolt://localhost:7687` (Memgraph's standard port; differs from our
ArcadeDB host-port 27687). **Note on licence:** Memgraph is BSL 1.1
with a 4-year delay to Apache-2.0, so it's not OSI-permissive *today*.
Use only if your distribution model is OK with BSL.

### Kuzu adapter

Embedded -- runs in-process, no Docker container. Filesystem-backed
via the `KUZU_DB_PATH` env var (default `./kuzu_data`). Cypher
parameters are first-class. **No async session API** -- wrap
`session.run()` in `asyncio.to_thread` at the call site if you need
to interleave with async I/O. The adapter raises a clear
`NotImplementedError` for `get_async_graph_driver()` on the `kuzu`
provider.

### NetworkX in-memory adapter -- supported query matrix

Pure-Python BSD library. **Not a Cypher engine.** Only three query
shapes are parsed; everything else raises `NotImplementedError`:

| Cypher | Supported | Notes |
| --- | --- | --- |
| `RETURN <literal>` | ✅ | `RETURN 1` / `RETURN 'ok'` / `RETURN true` / `RETURN null` |
| `MATCH (n) RETURN COUNT(n) [AS alias]` | ✅ | Returns the NX graph's `number_of_nodes()` |
| `MATCH (n) DETACH DELETE n` | ✅ | Clears the graph in-place |
| Parameterised queries (`$param`) | ❌ | Raises `NotImplementedError` |
| Anything else | ❌ | Raises `NotImplementedError` with a pointer here |

Suitable for: unit tests, the ping path in `bin/preflight.py`, and the
"`lean` profile on a laptop where graph workload is tiny".

### Memcached adapter -- supported method matrix

The redis-shaped surface is necessarily narrow because memcached has
no equivalent of pub/sub, sorted sets, or hash tables:

| Method | Supported | Notes |
| --- | --- | --- |
| `ping()` | ✅ | Maps to memcached's `version()` |
| `get(key)` | ✅ |  |
| `set(key, value, ex=ttl)` | ✅ |  |
| `delete(*keys)` | ✅ |  |
| `exists(*keys)` | ✅ | Implemented via `get()` since memcached has no native EXISTS |
| `expire(key, seconds)` | ✅ | Maps to memcached's `touch()` |
| `close()` | ✅ |  |
| `keys(pattern)` | ❌ | Memcached intentionally has no key enumeration |
| `flushdb()` | ❌ | Memcached's `flush_all()` wipes the *entire server*; not exposed under the redis name |
| Pub/sub | ❌ | Memcached has none |

### SQLite relational adapter -- compatibility caveats vs asyncpg

| Concern | Impact |
| --- | --- |
| Array / JSONB / pgvector types | Not supported -- schemas relying on these won't run unmodified |
| Parameter style | `?` placeholders (aiosqlite native), **not** asyncpg's `$1` / `$2`. Adapter does **not** translate query syntax |
| Connection pool | Single connection per `acquire()` -- no pooling. SQLite's write lock bounds concurrency |
| `database` kwarg | Used as the SQLite file path (defaults to `SQLITE_DB_PATH` env, then `POSTGRES_DB`, then `enhanced_cognee.db`). Pass `:memory:` for an ephemeral DB |

**Use only for tests / lean profile.** Production workloads must
pick `postgres`.

### pgvector adapter -- supported method matrix

`src/db_adapters/vector_pgvector.py` (shipped 2026-05-20) is a
`QdrantClient`-shaped shim over `psycopg2` + the `pgvector` Postgres
extension. Storage model: one Postgres table per Qdrant "collection",
prefixed with `PGVECTOR_TABLE_PREFIX` (default `ec_vec_`).

| Method | Supported | Notes |
| --- | --- | --- |
| `get_collections()` | ✅ | Lists tables matching the prefix |
| `get_collection(name)` | ✅ | Raises if the table doesn't exist (matches Qdrant) |
| `create_collection(name, vectors_config)` | ✅ | Auto-creates `vector` extension + IVFFLAT index. Distance: Cosine / Euclid / Dot |
| `upsert(name, points)` | ✅ | `ON CONFLICT (id) DO UPDATE` for idempotency |
| `count(name)` | ✅ |  |
| `search(name, query_vector, limit, score_threshold)` | ✅ | Supports single-`must` FieldCondition `query_filter` via the shared translator (see below). |
| `delete(name, points_selector)` -- ID list | ✅ |  |
| `delete(name, FilterSelector(filter=Filter(must=[FieldCondition(...)])))` | ✅ | Single `must` FieldCondition only -- enough for `gdpr_manager.delete_user_data` |
| `delete(...)` with `should` / `must_not` / multi-condition filters | ❌ | Raises `NotImplementedError`; query first and pass IDs |
| `search()` with `query_filter` | ✅ (single must FieldCondition) | Routes through `src/db_adapters/_vector_filter.py` to a `WHERE payload ->> %s = %s` JSONB extract. Compound filters raise `NotImplementedError`. |
| Named vectors / sparse vectors | ❌ | Not modelled in the schema |
| Payload field indexes | ❌ | All filters are evaluated against the JSONB column |
| Quantization / on-disk vectors / snapshots | ❌ | Out of scope for the minimum viable adapter |

The adapter sanitises collection names to alphanumeric + underscore
before formatting them into the table identifier, so the table-prefix
is **not** a SQL-injection surface.

**When to pick pgvector:** the lean profile, or any deployment where
"one Postgres" is operationally preferred over "Postgres + Qdrant".
Stick with `qdrant` for production-scale workloads that need rich
filters, named vectors, or large-collection performance.

### LanceDB adapter

`src/db_adapters/vector_lancedb.py` (shipped 2026-05-20). Embedded
MIT-licensed columnar vector store via Apache Arrow + Lance file
format. **Runs in-process** -- no Docker container, no network
protocol. Each Qdrant "collection" maps to a Lance table at the
configured `LANCEDB_URI` filesystem path. Suitable for laptop /
offline / single-process deployments where pgvector's Postgres-stack
requirement is overkill.

| Method | Supported | Notes |
| --- | --- | --- |
| `get_collections()` / `get_collection(name)` / `count(name)` | ✅ |  |
| `create_collection(name, vectors_config)` | ✅ | Cosine / Euclid / Dot supported via LanceDB's `metric` parameter |
| `upsert(name, points)` | ✅ | LanceDB has no native ON-CONFLICT; we delete-then-add atomically per batch |
| `search(name, query_vector, limit, score_threshold)` | ✅ | Returns ScoredPoint-shape hits; score normalised (1 - distance) |
| `delete()` by ID list | ✅ |  |
| `delete()` by single must FieldCondition | ✅ | LIKE substring match on JSON-encoded payload (GDPR shape) |
| `search()` with `query_filter` | ✅ (single must FieldCondition) | Routes through the shared `src/db_adapters/_vector_filter.py` translator: emits a LanceDB `WHERE payload LIKE '%"key":"value"%'` clause. Compound filters (`should` / `must_not` / multiple must) raise `NotImplementedError` -- query the points first and pass IDs. |
| Multi-condition / nested delete filters | ❌ |  |

### Chroma adapter

`src/db_adapters/vector_chroma.py` (shipped 2026-05-20). Apache-2.0
vector store with native Collection semantics. Network mode if
`CHROMA_HOST` is set, otherwise persistent in-process at
`CHROMA_PATH`. Chroma's API maps almost 1:1 onto Qdrant's, so the
adapter is shorter than pgvector / lancedb -- mostly straight
pass-throughs.

| Method | Supported | Notes |
| --- | --- | --- |
| `get_collections()` / `get_collection(name)` / `count(name)` | ✅ |  |
| `create_collection(name, vectors_config)` | ✅ | Distance metric via `metadata={"hnsw:space": metric}` |
| `upsert(name, points)` | ✅ | Native `collection.upsert(ids, embeddings, metadatas)` |
| `search(name, query_vector, limit, score_threshold)` | ✅ | Score = `1 - distance` |
| `delete()` by ID list | ✅ |  |
| `delete()` by single must FieldCondition | ✅ | Native `where={key: value}` map |
| `search()` with `query_filter` | ✅ (single must FieldCondition) | Routes through `_vector_filter.py` to Chroma's native `where={"key": value}` map. Compound filters raise `NotImplementedError`. |
| Multi-condition / nested delete filters | ❌ |  |

### Weaviate adapter

`src/db_adapters/vector_weaviate.py` (shipped 2026-05-20). BSD-3
vector database with rich GraphQL/REST API. Uses the v4
`weaviate-client` Python SDK. Each Qdrant collection maps to a
Weaviate Collection with a single `payload` TEXT property (JSON-
serialised). IDs are converted to UUIDs (passthrough if already
UUID, UUID5 hash otherwise).

| Method | Supported | Notes |
| --- | --- | --- |
| `get_collections()` / `get_collection(name)` / `count(name)` | ✅ | Count via Weaviate's `aggregate.over_all(total_count=True)` |
| `create_collection(name, vectors_config)` | ✅ | Distance: cosine / l2-squared / dot |
| `upsert(name, points)` | ✅ | Via v4 batch dynamic context manager |
| `search(name, query_vector, limit, score_threshold)` | ✅ | `near_vector(...)` with distance metadata |
| `delete()` by ID list | ✅ | Iterative `data.delete_by_id(uuid)` |
| `delete()` by single must FieldCondition | ✅ | LIKE on payload property (GDPR shape) |
| `search()` with `query_filter` | ✅ (single must FieldCondition) | Routes through `_vector_filter.py` to a `Filter.by_property("payload").like('*"key":"value"*')` chain. Compound filters raise `NotImplementedError`. |
| Multi-condition / nested delete filters | ❌ |  |
| Hybrid search (BM25 + vector) | ❌ | Not exposed by the qdrant-shaped API |

### Milvus adapter

`src/db_adapters/vector_milvus.py` (shipped 2026-05-20). Apache-2.0
vector database aimed at billion-scale workloads. Uses the v2
`pymilvus` `MilvusClient` API. Each Qdrant collection maps to a
Milvus collection with `id` (VARCHAR PK) + `vector` + `payload`
(JSON-encoded).

| Method | Supported | Notes |
| --- | --- | --- |
| `get_collections()` / `get_collection(name)` / `count(name)` | ✅ |  |
| `create_collection(name, vectors_config)` | ✅ | Distance: COSINE / L2 / IP via `metric_type` |
| `upsert(name, points)` | ✅ | Native idempotent `MilvusClient.upsert()` |
| `search(name, query_vector, limit, score_threshold)` | ✅ | Score normalised based on metric (COSINE / IP raw; L2 = 1-distance) |
| `delete()` by ID list | ✅ |  |
| `delete()` by single must FieldCondition | ✅ | Milvus `filter='payload like "..."'` expression |
| `search()` with `query_filter` | ✅ (single must FieldCondition) | Routes through `_vector_filter.py` to a Milvus `filter='payload like "%\"key\":\"value\"%"'` expression. Compound filters raise `NotImplementedError`. |
| Multi-condition / nested delete filters | ❌ |  |

### ArangoDB adapter

`src/db_adapters/graph_arangodb.py` (shipped 2026-05-20). Apache-2.0
multi-model DB; native AQL query language. The adapter translates
the narrow Cypher subset Enhanced Cognee uses into AQL via the
`python-arango` client. All graph nodes live in a single
ArangoDB document collection (default `cognee_graph_nodes`,
configurable via `ARANGO_COLLECTION_NAME`).

| Cypher | AQL translation |
| --- | --- |
| `RETURN <literal>` | `RETURN <literal>` |
| `MATCH (n) RETURN COUNT(n) [AS alias]` | `FOR d IN @@col COLLECT WITH COUNT INTO c RETURN c` |
| `MATCH (n) DETACH DELETE n` | `FOR d IN @@col REMOVE d IN @@col` |
| `MATCH (n) RETURN n` | `FOR d IN @@col RETURN d` |
| `CREATE (n:Label {props})` | Parameterised form only (raises if literal props) |
| Multi-hop / WHERE clauses | ❌ raises `NotImplementedError` -- python-arango doesn't ship a Cypher engine; you'd need a real translator (3-5 days of work) for arbitrary Cypher. Switch to arcadedb / neo4j for full Cypher coverage. |

**Async session API:** ✅ -- `get_async_graph_driver()` returns an
`_AsyncArangoDriver` that wraps sync `python-arango` calls in
`asyncio.to_thread`. The threading-boundary overhead is modest for
typical workloads.

### NebulaGraph adapter

`src/db_adapters/graph_nebulagraph.py` (shipped 2026-05-20).
Apache-2.0 distributed graph database via `nebula3-python`.
NebulaGraph 3+ supports openCypher mode natively, so most Cypher
queries pass through verbatim; the only rewrite is `RETURN <literal>`
-> `YIELD <literal>` (nGQL's literal-projection form). All graph
state lives in a single space (default `cognee_space`, configurable
via `NEBULA_SPACE_NAME`).

| Feature | Status |
| --- | --- |
| Connectivity ping (`RETURN 1` -> `YIELD 1`) | ✅ |
| `MATCH (n) RETURN COUNT(n) AS c` | ✅ (openCypher passthrough) |
| `MATCH (n) DETACH DELETE n` | ✅ (openCypher passthrough) |
| Multi-hop / WHERE clauses with property comparisons | ✅ for the queries NebulaGraph's openCypher mode supports natively. NebulaGraph 3+ is strict about tag schemas though -- properties must be declared on the tag first; that's a NebulaGraph constraint, not the adapter's. |
| Parameterised Cypher | ❌ -- nGQL parameter binding differs from Bolt-style. Inline literals or switch to arcadedb. |
| Async session API | ✅ -- `get_async_graph_driver()` returns an `_AsyncNebulaDriver` wrapping the sync `nebula3-python` client in `asyncio.to_thread`. |

### Ladybug adapter

`src/db_adapters/graph_ladybug.py` (shipped 2026-05-20). Upstream
Cognee's experimental in-process graph engine; already a hard core
dependency. The adapter mirrors the `networkx_inmemory` shape -- a
narrow Cypher parser (`RETURN <literal>` / `MATCH (n) RETURN
COUNT(n)` / `MATCH (n) DETACH DELETE n` / `MATCH (n) RETURN n`) on
top of ladybug's native graph API.

| Feature | Status |
| --- | --- |
| Connectivity ping (`RETURN 1`) | ✅ -- doesn't import ladybug; works as a no-op pre-flight |
| `MATCH (n) RETURN COUNT(n) [AS alias]` | ✅ |
| `MATCH (n) DETACH DELETE n` | ✅ |
| `MATCH (n) RETURN n` | ✅ |
| Parameterised Cypher | ❌ -- Ladybug's API isn't a Cypher engine; inline literals. |
| Async session API | ✅ -- `get_async_graph_driver()` returns an `_AsyncLadybugDriver` wrapping the in-process sync ladybug graph in `asyncio.to_thread`. |
| Multi-hop / WHERE | ❌ -- Ladybug's API doesn't expose pattern-matching. Switch to arcadedb / neo4j for those queries. |

---

## Apache AGE adapter -- supported query matrix

`src/db_adapters/graph_apache_age.py` is a hand-rolled shim that wraps
Cypher in AGE's `SELECT * FROM cypher('graph', $$ ... $$)` SQL form. It
covers the slice of Cypher Enhanced Cognee call sites use today; complex
Cypher features will raise `NotImplementedError` with a pointer back to
this file.

| Feature                                            | Status          | Notes                                                              |
| -------------------------------------------------- | --------------- | ------------------------------------------------------------------ |
| Connectivity ping (`RETURN 1`)                     | OK              | Used by `bin/preflight.py` and `recovery_manager._validate_neo4j`. |
| Scalar projections (`MATCH (n) RETURN COUNT(n)`)   | OK              | Returns `_AGERecord` with `[0]` / `["alias"]` access.              |
| Write queries (`MATCH ... DETACH DELETE`, `CREATE`)| OK              | Must still close with `AS (result agtype)` per AGE 1.5 rules.      |
| Iterating multiple records                         | OK              | `for record in result: ...` yields `_AGERecord` instances.         |
| Parameterised Cypher (`$param` syntax)             | OK (Phase 5)    | Passed via AGE's three-arg `cypher(graph, $$ ... $$, agtype_map)` form. Reject Cypher containing `$$` (would break the dollar-quoted block; raises `ValueError`). |
| Async session API                                  | OK (Phase 5)    | `get_async_graph_driver()` returns an asyncpg-backed `_AsyncAGEDriver`. Use `async with driver.session() as s:` then `await s.run(cypher)`. |
| Returning native graph elements (`MATCH (n) RETURN n`) | OK (Phase 5) | `::vertex` decodes to `_AGENode`, `::edge` to `_AGERelationship`, `::path` to `List[_AGENode \| _AGERelationship]`. Same surface as `neo4j.graph.Node` / `Relationship`: `.id` / `.labels` / `.type` / `.start_node` / `.end_node` / `node["prop"]` / `dict(node.items())`. Path endpoints are stub `_AGENode`s with only the id populated -- if you need their labels/properties, issue a follow-up `MATCH (n) WHERE id(n) = ...` (AGE's edge payload doesn't inline endpoint data). |
| APOC procedures (`apoc.*`)                         | not supported   | AGE has no APOC equivalent; switch to neo4j if you need APOC.      |

If you hit something that doesn't work and isn't on the matrix yet,
open an issue with the failing Cypher and we'll either add support or
expand the row.

---

## Setup steps

### production

Nothing to do beyond the default `install.sh` / `install.ps1`. The
default compose already wires the `production` profile env vars into
the MCP server's environment.

### apache_only

1. Use a Postgres image that bundles AGE -- e.g.
   `apache/age:PG16_latest` or
   `apache/age:PG14_latest` (replace the official postgres line in
   `docker-compose-enhanced-cognee.yml`).
2. Comment out the `arcadedb` service block. The MCP server's
   `depends_on` block needs the `arcadedb:` line removed too.
3. Set the env vars:
   ```bash
   ENHANCED_GRAPH_PROVIDER=apache_age
   AGE_GRAPH_NAME=cognee_graph
   ```
4. On first boot, create the graph (one-time):
   ```sql
   psql -h localhost -p 25432 -U cognee_user -d cognee_db -c "
     LOAD 'age';
     SELECT * FROM ag_catalog.create_graph('cognee_graph');
   "
   ```
5. Run the smoke test:
   ```bash
   python -c "
   from src.db_factory import get_graph_driver
   import os; os.environ['ENHANCED_GRAPH_PROVIDER'] = 'apache_age'
   d = get_graph_driver()
   with d.session() as s:
       print(s.run('RETURN 1').single()[0])
   "
   ```

### lean

Same as `apache_only` but also:

- Set `ENHANCED_CACHE_PROVIDER=in_memory`
- Optionally skip the Qdrant container if you don't need vector search
  (Phase 5's `pgvector` adapter will close this loop)
- Drop the Valkey container from the compose file

### byo

Point each `*_HOST` / `*_URI` / `*_USER` / `*_PASSWORD` env var at your
own infrastructure. No Compose file is required; the MCP server will
just connect.

---

## Provider matrix

Full set of providers wired into `src/db_factory.py` as of 2026-05-20.
"Status" reflects whether the adapter is feature-complete; see the
per-tier deep-dives below for query-matrix limitations.

### Relational tier (`ENHANCED_RELATIONAL_PROVIDER`)

| Provider | Status | Optional dep | Env vars consulted |
| --- | --- | --- | --- |
| `postgres` (default) | ✅ full | core (`asyncpg`) | `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` |
| `sqlite` | 🟡 partial -- testing / lean only | `[relational-sqlite]` (`aiosqlite`) | `SQLITE_DB_PATH` (falls back to `POSTGRES_DB`) |
| ~~`mysql` / `oracle`~~ | 📋 not on roadmap |  |  |

### Vector tier (`ENHANCED_VECTOR_PROVIDER`)

| Provider | Status | Optional dep | Env vars consulted |
| --- | --- | --- | --- |
| `qdrant` (default) | ✅ full | core (`qdrant-client`) | `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_API_KEY` |
| `pgvector` | 🟡 narrow API (no filter in search) | `[vector-pgvector]` (psycopg2 + pgvector) | `PGVECTOR_HOST` / `PGVECTOR_PORT` / `PGVECTOR_DB` / `PGVECTOR_USER` / `PGVECTOR_PASSWORD` / `PGVECTOR_TABLE_PREFIX` (falls through to `POSTGRES_*`) |
| `lancedb` | 🟡 narrow API (no filter in search) | `[vector-lancedb]` (`lancedb` + `pyarrow`) | `LANCEDB_URI` (filesystem path; default `./lancedb_data`) |
| `chroma` | 🟡 narrow API (no filter translation) | `[vector-chroma]` (`chromadb`) | `CHROMA_HOST` / `CHROMA_PORT` (network mode) or `CHROMA_PATH` (persistent in-process) |
| `weaviate` | 🟡 narrow API (no filter translation) | `[vector-weaviate]` (`weaviate-client>=4`) | `WEAVIATE_HOST` / `WEAVIATE_PORT` / `WEAVIATE_API_KEY` |
| `milvus` | 🟡 narrow API (no filter translation) | `[vector-milvus]` (`pymilvus>=2.4`) | `MILVUS_HOST` / `MILVUS_PORT` / `MILVUS_TOKEN` (or `MILVUS_USER` + `MILVUS_PASSWORD`) |

> The vector tier's API surface (Qdrant's `QdrantClient`) is rich
> (`get_collections` / `create_collection` / `upsert` / `search` / etc.).
> All five non-Qdrant adapters cover the narrow slice Enhanced Cognee
> actually uses; everything else (named vectors, sparse vectors,
> payload indexes, quantization, rich search filters, hybrid search)
> raises a clear `NotImplementedError`. The first adapter shipped
> (pgvector) set the `_PgVectorClient` duck-typing pattern; the
> remaining four (lancedb, chroma, weaviate, milvus, shipped
> 2026-05-20) follow the same `_CollectionDescription` / `_SearchHit`
> shape so callers don't have to special-case the provider.

### Graph tier (`ENHANCED_GRAPH_PROVIDER`)

| Provider | Status | Optional dep | Env vars consulted |
| --- | --- | --- | --- |
| `arcadedb` (default) | ✅ full | core (`neo4j`) | `ARCADEDB_URI` / `ARCADEDB_USER` / `ARCADEDB_PASSWORD` |
| `neo4j` | ✅ full (legacy) | core (`neo4j`) | `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` |
| `apache_age` | 🟡 narrow Cypher subset (params + async since 2026-05-20) | core (`psycopg2`) | `AGE_HOST` / `AGE_PORT` / `AGE_DB` / `AGE_USER` / `AGE_PASSWORD` / `AGE_GRAPH_NAME` (falls through to `POSTGRES_*`) |
| `memgraph` | ✅ full | `[graph-memgraph]` (reuses `neo4j`) | `MEMGRAPH_URI` / `MEMGRAPH_USER` / `MEMGRAPH_PASSWORD` |
| `kuzu` | 🟡 sync-only | `[graph-kuzu]` | `KUZU_DB_PATH` |
| `networkx_inmemory` | 🟡 narrow Cypher subset (testing only) | core (`networkx`) | -- |
| `arangodb` | 🟡 narrow Cypher subset translated to AQL | `[graph-arangodb]` (`python-arango`) | `ARANGO_HOST` / `ARANGO_PORT` / `ARANGO_DB` / `ARANGO_USER` / `ARANGO_PASSWORD` / `ARANGO_COLLECTION_NAME` |
| `nebulagraph` | 🟡 narrow Cypher subset via NebulaGraph openCypher mode | `[graph-nebulagraph]` (`nebula3-python`) | `NEBULA_HOST` / `NEBULA_PORT` / `NEBULA_USER` / `NEBULA_PASSWORD` / `NEBULA_SPACE_NAME` |
| `ladybug` | 🟡 narrow Cypher subset (upstream Cognee default) | `[graph-ladybug]` (ladybug already core) | `LADYBUG_DB_PATH` |

### Cache tier (`ENHANCED_CACHE_PROVIDER`)

| Provider | Status | Optional dep | Env vars consulted |
| --- | --- | --- | --- |
| `valkey` (default) | ✅ full | core (`redis`) | `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` |
| `redis` | ✅ full (alias) | core (`redis`) | Same as `valkey` (wire-compatible). |
| `redis_compat` | ✅ full (alias) | core (`redis`) | For wire-compatible Redis forks (KeyDB / Garnet / Dragonfly). Signals operational intent vs `valkey`/`redis`. Same env vars. |
| `in_memory` | 🟡 single-process only | none -- pure dict | -- |
| `memcached` | 🟡 no `keys()` / `flushdb()` | `[cache-memcached]` (`pymemcache`) | `MEMCACHED_HOST` / `MEMCACHED_PORT` |

### Status legend

- ✅ **full** -- complete neo4j-driver / asyncpg / QdrantClient / redis surface, suitable for production
- 🟡 **partial** -- works for a specific use case; see per-adapter sub-section below for the supported-query / API matrix
- 📋 **deferred** -- not yet wired; raise an issue if you need it shipped now

Legacy `*_BACKEND` aliases (`RELATIONAL_BACKEND` / `VECTOR_BACKEND` /
`GRAPH_BACKEND` / `CACHE_BACKEND`) are still honoured at lower
precedence than the canonical `ENHANCED_*_PROVIDER` names.

### Optional-dep install

To install only the adapters you actually use:

```bash
pip install "enhanced-cognee[graph-memgraph]"     # adds neo4j driver
pip install "enhanced-cognee[graph-kuzu]"
pip install "enhanced-cognee[graph-networkx]"
pip install "enhanced-cognee[cache-memcached]"
pip install "enhanced-cognee[relational-sqlite]"
```

Or all of them at once: `pip install "enhanced-cognee[graph-memgraph,graph-kuzu,graph-networkx,cache-memcached,relational-sqlite]"`.

---

## Related docs

- `docs/HANDOVER.md` section 4 -- phase-by-phase roadmap
- `docs/STRATEGY.md` section 4.1 -- profile design
- `docs/STRATEGY.md` DR-08 -- env-var routing decision
- `docs/ARCADEDB_MIGRATION.md` -- Phase 2 ArcadeDB swap
- `docs/LICENSE_AUDIT.md` -- per-component licence detail
