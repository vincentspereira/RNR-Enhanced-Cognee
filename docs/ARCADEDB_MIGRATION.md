# ArcadeDB Migration Guide

**Status:** Default graph DB since Phase 2 (2026-05-19; STRATEGY.md DR-11).

**TL;DR:** ArcadeDB (Apache-2.0, multi-model) replaces Neo4j Community
(GPLv3) as the default graph database. The swap is **drop-in for callers
of the `neo4j` Python driver** because ArcadeDB exposes a Bolt-compatible
endpoint. No code in `src/` changed; we route through `src/db_factory.py`
which now defaults `ENHANCED_GRAPH_PROVIDER` to `arcadedb`.

---

## 1. Why ArcadeDB

| Criterion                  | ArcadeDB                                                       | Neo4j Community                            |
| -------------------------- | -------------------------------------------------------------- | ------------------------------------------ |
| Licence                    | Apache-2.0 (commercial-distribution safe)                      | GPLv3 (carve-out required for bundling)    |
| Query language             | openCypher (drop-in)                                           | Cypher                                     |
| Wire protocol              | Bolt (drop-in for `neo4j` Python driver)                       | Bolt                                       |
| Multi-model                | Graph + Document + KV + Vector + Time-series + Geospatial      | Graph only                                 |
| Operational footprint      | Single Java 21+ container; HTTP Studio at port 2480            | Single Java 17+ container; Browser at 7474 |
| Default admin user         | `root`                                                          | `neo4j`                                    |

Full rationale: [`STRATEGY.md` §4.2](./STRATEGY.md#42-recommended-new-default-arcadedb-revised-2026-05-19)
and [`STRATEGY.md` DR-11](./STRATEGY.md#9-appendix-decision-records).

---

## 2. What changed in this fork

### Code
- New adapter: `src/db_adapters/graph_arcadedb.py`. Thin factory function
  that calls `from neo4j import GraphDatabase; GraphDatabase.driver(...)`
  against the ArcadeDB Bolt endpoint -- no new Python dependency.
- `src/db_factory.py`: `_VALID_GRAPH` now contains `{"arcadedb", "neo4j"}`,
  default flipped to `arcadedb`. `get_graph_driver` /
  `get_async_graph_driver` dispatch through the new adapter when the
  provider resolves to `arcadedb`.
- All previous call sites already routed through the factory in Phase 1,
  so no other source files needed changes for this migration.

### Infrastructure
- `docker/docker-compose-enhanced-cognee.yml`: the `neo4j` service is
  replaced by an `arcadedb` service. Container name
  `arcadedb-enhanced-cognee`. Bolt is exposed on host port `27687`
  (same as the previous Neo4j Bolt port -- drop-in). Studio HTTP at
  host port `22480`. ArcadeDB's Bolt plugin is enabled via
  `JAVA_OPTS=-Darcadedb.server.plugins=Bolt:com.arcadedb.bolt.BoltPlugin`.
- `deploy/local/install.ps1` and `deploy/local/install.sh`: the MCP
  server registration adds `ENHANCED_GRAPH_PROVIDER=arcadedb`,
  `ARCADEDB_URI=bolt://localhost:27687`, `ARCADEDB_USER=root`,
  `ARCADEDB_PASSWORD=cognee_password`. The legacy `NEO4J_*` env vars
  are retained pointed at the same host:port for back-compat with any
  callers still passing them explicitly.
- `.env.example`: `ENHANCED_GRAPH_PROVIDER=arcadedb` section added.

### Env vars
| Variable                  | Default                          | Notes                                                      |
| ------------------------- | -------------------------------- | ---------------------------------------------------------- |
| `ENHANCED_GRAPH_PROVIDER` | `arcadedb`                       | `neo4j` opts into legacy provider                          |
| `ARCADEDB_URI`            | `bolt://localhost:27687`         | host port matches the old Neo4j Bolt port                   |
| `ARCADEDB_USER`           | `root`                           | ArcadeDB's built-in admin                                  |
| `ARCADEDB_PASSWORD`       | `cognee_password`                | matches the old `NEO4J_PASSWORD` default                   |
| `NEO4J_URI` / `_USER` /   | (unchanged)                      | still read when `ENHANCED_GRAPH_PROVIDER=neo4j`            |
| `_PASSWORD`               |                                  |                                                            |
| `GRAPH_BACKEND`           | unset                            | legacy alias for `ENHANCED_GRAPH_PROVIDER`; lower precedence |

---

## 3. How to migrate an existing deployment

If you already have a stack running Neo4j and want to move to ArcadeDB:

### 3.1 Export your existing Neo4j data (one-time)

The exact command depends on whether you used the `_backup_neo4j` MCP
tool or `neo4j-admin dump`. Either output is a Cypher script. The
`backup_manager.py` Cypher-export fallback writes JSON we can re-import
via `restore_backup`.

### 3.2 Switch providers

1. `docker compose -f docker/docker-compose-enhanced-cognee.yml down`
2. Pull this branch (or main once Phase 2 is merged).
3. `docker compose -f docker/docker-compose-enhanced-cognee.yml up -d`
4. The new `arcadedb` service comes up; old `neo4j_*` volumes remain
   on disk untouched.
5. Re-import your data into ArcadeDB through `restore_backup` against
   the new endpoint (`bolt://localhost:27687` -- same URL as before).

### 3.3 Keep using Neo4j instead

Set `ENHANCED_GRAPH_PROVIDER=neo4j` in your environment and add the
Neo4j compose snippet back to `docker-compose-enhanced-cognee.yml`
(below). The factory route + integration code stay unchanged; only the
container behind `bolt://localhost:27687` differs.

```yaml
  # Neo4j Community fallback (set ENHANCED_GRAPH_PROVIDER=neo4j)
  neo4j:
    image: neo4j:5.25-community
    container_name: neo4j-enhanced-cognee
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-cognee_password}
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_dbms_security_procedures_unrestricted: apoc.*
      NEO4J_dbms_memory_heap_initial_size: 1G
      NEO4J_dbms_memory_heap_max_size: 2G
      NEO4J_dbms_memory_pagecache_size: 1G
      NEO4J_dbms_connector_bolt_listen_address: 0.0.0.0:7687
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
    ports:
      - "27474:7474"  # Browser
      - "27687:7687"  # Bolt (same host port; comment out the arcadedb mapping above)
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474/browser/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

You cannot bind both services to host port 27687 simultaneously; comment
out the `arcadedb` port mapping if you want both up at once on
different host ports.

---

## 4. Cypher dialect notes

ArcadeDB implements openCypher with a few divergences from Neo4j's
flavour. The ones that matter for Enhanced Cognee:

| Feature                              | Neo4j 5            | ArcadeDB           | Workaround                                                       |
| ------------------------------------ | ------------------ | ------------------ | ---------------------------------------------------------------- |
| `CREATE CONSTRAINT`                  | first-class        | partial            | Use schema commands via HTTP API or ALTER TYPE for indexes       |
| `MATCH (n) DETACH DELETE n`          | full               | full               | -- (this is what `recovery_manager._validate_neo4j` uses)        |
| APOC procedures (`apoc.*`)           | first-class plugin | not available      | Replace with native Cypher; APOC is Neo4j-only                   |
| Graph Data Science (`gds.*`)         | plugin             | not available      | Out of scope for memory store                                    |
| `RETURN COUNT(n)`                    | full               | full               | -- (used by validate paths)                                      |
| `elementId(n)`                       | full               | not available      | Use `id(n)` -- ArcadeDB returns numeric/Rid id; `backup_manager.py` already abstracts via `element_id(node)` helper |
| Multi-database support               | yes (`USE db`)     | partial (datab. per server) | Use `cognee_graph` as the single default database         |

Enhanced Cognee's existing Cypher usage (in `src/agent_memory_integration.py`,
`backup_manager.py`, `recovery_manager.py`) uses only the rows marked
"full" above. No code changes were required for the migration.

If you hit a query that fails on ArcadeDB, please open an issue and
add it to the table.

---

## 5. Operational considerations

- **Memory:** ArcadeDB runs on Java 21+. Default JVM heap is ~1 GB
  inside the container; tune via `JAVA_OPTS=-Xmx2g` if needed.
- **Studio UI:** http://localhost:22480 (login: `root` /
  `cognee_password`). Equivalent to Neo4j Browser.
- **Health check:** ArcadeDB exposes `GET /api/v1/ready` on the HTTP
  port; the compose health-check uses that endpoint.
- **Hetzner CX22 (4 GB RAM):** stack fits, but if you also run the
  SigNoz observability stack (Phase 4) on the same host you'll be
  tight. Consider running observability on a separate VPS.

---

## 6. Verification

### Quick smoke test

```bash
# Defaults (no env vars set)
python -c "from src.db_factory import get_provider_summary; print(get_provider_summary())"
# {'relational': 'postgres', 'vector': 'qdrant', 'graph': 'arcadedb', 'cache': 'valkey'}

# Get a driver (no live DB needed for this -- import only)
python -c "from src.db_factory import get_graph_driver; print(get_graph_driver.__doc__[:80])"

# Confirm the legacy alias still works
GRAPH_BACKEND=neo4j python -c "from src.db_factory import get_provider_summary; print(get_provider_summary())"
# {'graph': 'neo4j', ...}
```

### Against a running ArcadeDB instance

```bash
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d arcadedb

# Wait ~10-15s for ArcadeDB to start, then:
curl -s http://localhost:22480/api/v1/ready
# {"status":"OK"}

# Through the MCP server:
python -c "
import asyncio
from bin.enhanced_cognee_mcp_server import init_enhanced_stack
asyncio.run(init_enhanced_stack())
"
# Should log: 'OK ArcadeDB connected' (or 'OK Neo4j connected' label,
# since the existing init code still uses the neo4j label; cosmetic only).
```

---

## 7. Rollback plan

If something breaks in production:

1. Set `ENHANCED_GRAPH_PROVIDER=neo4j` in your `.env`.
2. Swap the compose `arcadedb` service back for the `neo4j` block in §3.3.
3. `docker compose down && up -d`.

The `neo4j_data`, `neo4j_logs`, `neo4j_import` volumes are still
declared in the compose file (just unused by default), so your previous
data is still on disk.

---

## 8. References

- ArcadeDB documentation: https://docs.arcadedb.com/
- ArcadeDB Bolt plugin: https://docs.arcadedb.com/#API-Bolt
- STRATEGY.md DR-11: [Decision Records](./STRATEGY.md#9-appendix-decision-records)
- HANDOVER §4 Phase 2: [Session handover brief](./HANDOVER.md)
