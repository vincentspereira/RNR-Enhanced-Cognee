# Integrating Enhanced Cognee with Multi-Agent System (MAS)

This guide wires Enhanced Cognee as the memory layer for the Multi-Agent System
at `C:\Users\vince\Projects\AI Agents\Multi-Agent System`.

**Per Q1 answer in PRODUCTION_READINESS_PLAN.md:** Enhanced Cognee SHARES the
memory system with MAS's existing memory layer. They coexist; Enhanced Cognee
becomes the primary store for new memories, while the existing layer remains
for legacy data.

## Two integration surfaces (read this first)

Enhanced Cognee exposes the SAME 122 tools over two transports. Pick the one
that matches how the calling code runs:

| Surface | Entry point | Tools | Transport | Use when |
| ------- | ----------- | ----- | --------- | -------- |
| **A. stdio MCP** (primary) | `bin/enhanced_cognee_mcp_server.py` via `.claude.json` | all 122 | stdio (MCP protocol) | The caller is a Claude Code agent. This is how MAS agents consume memory. Works today; nothing to build. |
| **B. HTTP REST** | `src/enhanced_cognee_mcp.py` (FastAPI), port `8080` | all 122 via `POST /tools/{tool_name}` | HTTP/HTTPS | The caller is plain Python / another language / a service that is not an MCP client. Backed by the `enhanced_cognee_client` Python SDK. |

- **Surface A is the recommended path for MAS** because MAS agents run on
  Claude Code, which speaks MCP natively. Register the server (Step 1) and the
  full tool set is available immediately -- no HTTP, no ports, no auth tokens.
- **Surface B** is for non-MCP callers. The HTTP server listens on the port set
  by `ENHANCED_HTTPS_PORT` (default `8080`), authenticates every request
  (Bearer JWT/OIDC or `X-API-Key`) and enforces per-tool RBAC. See
  "Surface B: calling over HTTP" below.

> Whichever surface you use, `agent_id` segregation, dynamic categories and the
> audit log behave identically -- they are properties of the storage layer, not
> the transport.

## Architecture

```
+---------------------------------------------------------+
|                Multi-Agent System (MAS)                 |
|                                                         |
|  +-------------+  +-------------+  +-----------------+  |
|  | trading-bot |  | sdlc-agent  |  | analysis-agent  |  |
|  +------+------+  +------+------+  +--------+--------+  |
|         |                |                  |           |
|         +----------------+------------------+           |
|                          |                              |
|                          v                              |
|  +---------------------------------------------------+  |
|  |    MAS Memory Router (existing)                   |  |
|  |    +- legacy_memory (existing in-memory store)    |  |
|  |    \- enhanced_cognee_mcp (NEW: this project)     |  |
|  +---------------------+-----------------------------+  |
|                        |                                |
+------------------------+--------------------------------+
                         |
                         v
                +--------+----------+
                |  Enhanced Cognee  |
                |   MCP Server      |
                |  (122 tools)      |
                +-------------------+
                         |
           +-------------+-------------+-------------+
           |             |             |             |
           v             v             v             v
     +----------+  +--------+  +----------+  +---------+
     | Postgres |  | Qdrant |  | ArcadeDB |  | Valkey  |
     +----------+  +--------+  +----------+  +---------+
```

> **DB providers (Phase 2 default):** the graph store is **ArcadeDB**
> (openCypher + Bolt, Apache-2.0) and the cache is **Valkey** (Apache-2.0),
> replacing Neo4j and Redis respectively. The connection env-var NAMES are kept
> for drop-in compatibility -- `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` point
> at ArcadeDB's Bolt endpoint, and `REDIS_HOST`/`REDIS_PORT` point at Valkey.
> Set `ENHANCED_GRAPH_PROVIDER=neo4j` to opt back into Neo4j.

## Step 1: Register Enhanced Cognee in MAS's `~/.claude.json`

If MAS uses its own `.claude.json` (or a per-project equivalent), add the
Enhanced Cognee MCP server entry:

```json
{
  "mcpServers": {
    "cognee": {
      "command": "C:\\Users\\vince\\Projects\\AI Agents\\enhanced-cognee\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\vince\\Projects\\AI Agents\\enhanced-cognee\\bin\\enhanced_cognee_mcp_server.py"
      ],
      "env": {
        "ENHANCED_COGNEE_MODE": "true",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "25432",
        "POSTGRES_DB": "cognee_db",
        "POSTGRES_USER": "cognee_user",
        "POSTGRES_PASSWORD": "your-db-password",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "26333",
        "NEO4J_URI": "bolt://localhost:27687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-db-password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "26379"
      }
    }
  }
}
```

> **Secrets:** `your-db-password` above is a placeholder. Use the strong
> passwords generated by the installer (written to the stack `.env`) and never
> commit real credentials. The MCP server reads `POSTGRES_PASSWORD` /
> `NEO4J_PASSWORD` (and `ARCADEDB_PASSWORD`) from the environment / `.env`.

## Step 2: Agent ID Conventions

MAS already has agent IDs in its codebase. Map them to Enhanced Cognee's
`agent_id` field so memories are properly segregated:

| MAS Agent | Enhanced Cognee `agent_id` | Default `memory_category` |
| --------- | -------------------------- | ------------------------- |
| AlgorithmicTradingSystem | `trading-bot` | `trading` |
| OrderManagementAgent     | `oma-agent`   | `trading` |
| SmartMoneyConcepts       | `smc-agent`   | `trading` |
| SDLCIntegrationManager   | `sdlc-agent`  | `development` |
| DataScienceAgent         | `ds-agent`    | `analysis` |
| BusinessIntelligenceAgent| `bi-agent`    | `analysis` |
| RiskManagementAgent      | `risk-agent`  | `trading` |

## Step 3: Configure Category Prefixes

Create `C:\Users\vince\Projects\AI Agents\Multi-Agent System\.enhanced-cognee-config.json`:

```json
{
  "categories": {
    "trading": {
      "prefix": "trading_",
      "description": "Trading-system memories (strategies, positions, signals)"
    },
    "development": {
      "prefix": "dev_",
      "description": "SDLC-related memories (bugs, decisions, code reviews)"
    },
    "analysis": {
      "prefix": "analysis_",
      "description": "Data science and BI analysis results"
    },
    "shared": {
      "prefix": "shared_",
      "description": "Cross-agent shared knowledge"
    }
  }
}
```

Set the env var so MAS picks it up:

```bash
# Windows (Powershell)
[Environment]::SetEnvironmentVariable("ENHANCED_COGNEE_CONFIG_PATH",
    "C:\Users\vince\Projects\AI Agents\Multi-Agent System\.enhanced-cognee-config.json",
    "User")
```

## Step 4: Memory-router shim in MAS

Inside MAS, create a thin wrapper that delegates to whichever store is
appropriate. Pseudocode:

```python
# Multi-Agent System/memory/router.py
class MemoryRouter:
    def __init__(self, legacy_store, cognee_client):
        self.legacy = legacy_store
        self.cognee = cognee_client

    async def add(self, agent_id, content, category=None):
        # All NEW memories go to Enhanced Cognee
        return await self.cognee.add_memory(
            content=content,
            agent_id=agent_id,
            metadata=json.dumps({"category": category}) if category else None,
        )

    async def search(self, query, agent_id=None, limit=10):
        # Search both stores, prefer Cognee results
        cognee_hits = await self.cognee.search_memories(
            query=query, agent_id=agent_id, limit=limit
        )
        if len(cognee_hits) < limit:
            legacy_hits = self.legacy.search(query, limit=limit - len(cognee_hits))
            return cognee_hits + legacy_hits
        return cognee_hits

    async def migrate_legacy(self, batch_size=100):
        # One-time: walk legacy store, copy into Cognee, mark as migrated
        for batch in self.legacy.iter_batches(batch_size):
            for entry in batch:
                await self.cognee.add_memory(
                    content=entry.content,
                    agent_id=entry.agent_id,
                    metadata=json.dumps({
                        "category": entry.category,
                        "migrated_from": "legacy",
                        "original_id": entry.id,
                    }),
                )
                self.legacy.mark_migrated(entry.id)
```

## Step 5: Verify the integration

### Surface A (stdio MCP) -- the path MAS uses

After editing `.claude.json` (Step 1) and restarting Claude Code, the 122 tools
are available to the agent directly. Confirm by asking the agent to call
`health` and then `add_memory` / `search_memories`. There is no port or token
to manage -- the MCP transport is the stdio pipe Claude Code already owns.

### Surface B (HTTP) -- for non-MCP callers

> **Status:** the generic `POST /tools/{tool_name}` dispatch and the matching
> `enhanced_cognee_client` default port land in the companion commit in this
> series. Until then the HTTP server exposes the named `/mcp/*` routes
> (`/mcp/add_memory`, `/mcp/search_memories`, `/mcp/get_memories`,
> `/mcp/update_memory`, `/mcp/delete_memory`, `/mcp/list_agents`) plus
> `/health*`, `/metrics`, `/stats` -- all on port `8080` with the same auth.

Start the HTTP server and hit it over plain HTTP. It listens on
`ENHANCED_HTTPS_PORT` (default `8080`) and authenticates every request, so pass
a bearer token (or `X-API-Key`):

```python
import asyncio
from enhanced_cognee_client import EnhancedCogneeClient

async def main():
    # port defaults to 8080 (the HTTP server's ENHANCED_HTTPS_PORT)
    async with EnhancedCogneeClient(host="localhost", port=8080,
                                    api_key="<bearer-token>") as client:
        result = await client.add_memory(
            content="MAS integration test memory",
            user_id="default",
            agent_id="trading-bot",
        )
        print("Added:", result)
        hits = await client.search_memories(query="integration test")
        print("Found:", hits)

asyncio.run(main())
```

The SDK wraps `POST /tools/{tool_name}` (the generic dispatch that exposes all
122 tools over HTTP). If you prefer raw HTTP, the same call is:

```bash
curl -X POST http://localhost:8080/tools/add_memory \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"content": "MAS integration test memory", "agent_id": "trading-bot"}}'
```

> In a no-auth dev deployment (`ENHANCED_ALLOW_INSECURE_DEFAULTS=1` with no
> production flags), the server fails open to a local admin principal, so the
> token can be omitted. Production refuses to start without auth configured.

## Step 6: Decide on a migration cutover date

| Phase | Action |
| ----- | ------ |
| Week 0 | Both stores active. New writes -> Cognee. Reads from both. |
| Week 1 | Run `MemoryRouter.migrate_legacy()` to backfill old memories into Cognee. |
| Week 2 | Switch reads to Cognee-first, legacy as fallback. |
| Week 4 | Disable legacy writes entirely. Keep legacy DB for emergency rollback. |
| Week 8 | Archive legacy DB. Single-source-of-truth = Cognee. |

## Day-2: Useful MCP tool combos for MAS

| Use case | Tools |
| -------- | ----- |
| Agent recalls past conversation | `recall(agent_id, query)` |
| Save lesson from a bug fix | `remember(agent_id, "Fixed race condition by...")` |
| Cross-agent knowledge sharing | `create_shared_space()` + `set_memory_sharing(memory_id, "public")` |
| Trading strategy review | `search(query="momentum strategy", filters={"category":"trading"})` |
| Audit compliance query | `query_audit_log(agent_id, since=...)` |
| Find duplicate strategies | `find_consolidation_candidates(threshold=0.85)` |

## Troubleshooting

- **`mcp not found` in MAS**: Confirm `~/.claude.json` was edited and Claude Code restarted.
- **Wrong agent_id in stored memories**: Check the MAS agent's `_agent_id` attribute matches the table above.
- **Memory not searchable**: Check `cognify_status()` - background indexing may still be running.
- **Slow responses**: Run `get_performance_metrics()` to find bottlenecks.

See `docs/operations/RUNBOOK.md` for more.
