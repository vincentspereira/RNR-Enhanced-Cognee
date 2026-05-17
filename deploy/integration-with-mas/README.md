# Integrating Enhanced Cognee with Multi-Agent System (MAS)

This guide wires Enhanced Cognee as the memory layer for the Multi-Agent System
at `C:\Users\vince\Projects\AI Agents\Multi-Agent System`.

**Per Q1 answer in PRODUCTION_READINESS_PLAN.md:** Enhanced Cognee SHARES the
memory system with MAS's existing memory layer. They coexist; Enhanced Cognee
becomes the primary store for new memories, while the existing layer remains
for legacy data.

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
              +----------+----------+
              |          |          |
              v          v          v          v
        +--------+  +-------+  +-----+  +---------+
        |Postgres|  |Qdrant |  |Neo4j|  |  Redis  |
        +--------+  +-------+  +-----+  +---------+
```

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
        "POSTGRES_PASSWORD": "cognee_password",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "26333",
        "NEO4J_URI": "bolt://localhost:27687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "cognee_password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "26379"
      }
    }
  }
}
```

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

Inside MAS, start a Python session and try calling a Cognee tool through the
MCP client:

```python
import asyncio
from enhanced_cognee_client import EnhancedCogneeClient  # pip install enhanced-cognee-client

async def main():
    async with EnhancedCogneeClient(host="localhost", port=37777) as client:
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
