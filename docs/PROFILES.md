# Deployment Profiles

**Status:** Phase 3 (Apache AGE + lean profile) shipped 2026-05-19.

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
| `lean`         | postgres   | qdrant   | apache_age   | in_memory   | postgres (with AGE) + qdrant      | Laptops / small VPS / offline                 |
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

Smallest viable stack -- laptop or smallest-tier VPS:

```bash
ENHANCED_RELATIONAL_PROVIDER=postgres
ENHANCED_VECTOR_PROVIDER=qdrant         # pgvector pluggable in Phase 5
ENHANCED_GRAPH_PROVIDER=apache_age
ENHANCED_CACHE_PROVIDER=in_memory       # process-local dict
```

`deploy/profiles/lean.yaml` documents the exact set. Drop the Valkey
container, drop the ArcadeDB container, run everything against one
Postgres + Qdrant + the MCP server process.

Limitations (intentional):

- Cache loses state on process restart
- No pub/sub -- the realtime sync features degrade gracefully but pub/sub
  channels noop
- Single-process only -- a second MCP process won't share cache state

`lean` is not recommended for production; it exists so that "give me
the smallest possible Enhanced Cognee" works as a single command.

Future cleanup: once the Phase 5 `pgvector` vector adapter ships, lean
will collapse further to just Postgres + MCP process.

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
| Parameterised Cypher (`$param` syntax)             | not implemented | Raises `NotImplementedError`. Inline literals or use neo4j/arcadedb. |
| Async session API                                  | not implemented | `get_async_graph_driver()` raises. Use sync path or arcadedb/neo4j. |
| Returning whole graph elements (`MATCH (n) RETURN n`) | partial      | You get the agtype JSON. Parse with `record["n"]` -> dict.         |
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

## Provider × env-var quick reference

| Provider                              | Env vars consulted                                                                              |
| ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `ENHANCED_RELATIONAL_PROVIDER=postgres` | `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`        |
| `ENHANCED_VECTOR_PROVIDER=qdrant`       | `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_API_KEY`                                                |
| `ENHANCED_GRAPH_PROVIDER=arcadedb`      | `ARCADEDB_URI` / `ARCADEDB_USER` / `ARCADEDB_PASSWORD` (defaults to root admin)                 |
| `ENHANCED_GRAPH_PROVIDER=neo4j`         | `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD`                                                   |
| `ENHANCED_GRAPH_PROVIDER=apache_age`    | `AGE_HOST` / `AGE_PORT` / `AGE_DB` / `AGE_USER` / `AGE_PASSWORD` / `AGE_GRAPH_NAME`             |
|                                       | Falls through to `POSTGRES_*` for connection details.                                            |
| `ENHANCED_CACHE_PROVIDER=valkey`        | `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD`                                                  |
| `ENHANCED_CACHE_PROVIDER=redis`         | Same as `valkey` (wire-compatible).                                                              |
| `ENHANCED_CACHE_PROVIDER=in_memory`     | None -- pure in-process dict.                                                                    |

Legacy `*_BACKEND` aliases (`RELATIONAL_BACKEND` etc.) are still honoured
at lower precedence than the canonical `ENHANCED_*_PROVIDER` names.

---

## Related docs

- `docs/HANDOVER.md` section 4 -- phase-by-phase roadmap
- `docs/STRATEGY.md` section 4.1 -- profile design
- `docs/STRATEGY.md` DR-08 -- env-var routing decision
- `docs/ARCADEDB_MIGRATION.md` -- Phase 2 ArcadeDB swap
- `docs/LICENSE_AUDIT.md` -- per-component licence detail
