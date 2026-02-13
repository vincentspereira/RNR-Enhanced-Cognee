# Enhanced Cognee MCP Configuration Summary (CORRECTED)

**Date:** 2026-02-09
**Status:** Configuration Complete
**Scope:** Global User Scope (All Projects)

---

## Configuration Changes Made

### 1. Fixed MCP Server Path
**Before:**
```
C:/Users/vince/Projects/AI Agents/enhanced-cognee/enhanced_cognee_mcp_server.py
```

**After:**
```
C:/Users/vince/Projects/AI Agents/enhanced-cognee/bin/enhanced_cognee_mcp_server.py
```

### 2. Added LLM Configuration
Added missing environment variables for Sprint 10 AI features:
```json
"LLM_API_KEY": "56b25fee3dc44a4bb7ca3d60c1b751ff.ebOlp9WhbLgJXv10",
"LLM_MODEL": "glm-4.7",
"LLM_PROVIDER": "zai",
"LLM_ENDPOINT": "https://api.z.ai/v1"
```

---

## MCP Tools Available - CORRECTED CLASSIFICATION

**Total: 59 MCP Tools**

### Correct Classification (per README.md lines 870-1200)

| Type | Count | Description |
|------|-------|-------------|
| **Manual (M)** | 10 | Explicit user invocation (destructive operations, policy settings) |
| **Auto (A)** | 16 | AI IDE controlled (Claude Code, Cursor, etc.) |
| **System (S)** | 32 | Enhanced Cognee controlled (chained automation, scheduled tasks) |

### Manual (M) Tools - 10 Total
Tools requiring explicit user invocation:

1. `delete_memory` - Delete a specific memory
2. `expire_memories` - Expire old memories
3. `set_memory_ttl` - Set time-to-live for memory
4. `archive_category` - Archive memories by category
5. `set_memory_sharing` - Set sharing policy for memory
6. `create_backup` - Create system backup
7. `restore_backup` - Restore from backup
8. `create_shared_space` - Create shared memory space
9. `schedule_task` - Schedule maintenance task
10. `cancel_task` - Cancel scheduled task

### Auto (A) Tools - 16 Total
Tools automatically triggered by AI IDEs:

1. `add_memory` - Add memory with metadata
2. `search_memories` - Semantic + text search
3. `get_memories` - List all memories
4. `get_memory` - Get specific memory by ID
5. `update_memory` - Update existing memory
6. `list_agents` - List all agents
7. `cognify` - Transform data to knowledge graph
8. `search` - Search knowledge graph
9. `list_data` - List all documents
10. `get_stats` - Get system statistics
11. `health` - Health check all databases
12. `check_memory_access` - Check if agent can access memory
13. `get_shared_memories` - Get shared memories for agent
14. `list_backups` - List all backups
15. `list_tasks` - List scheduled tasks
16. `sync_agent_state` - Sync memories between agents

### System (S) Tools - 32 Total
Tools automatically triggered by Enhanced Cognee:

**Performance & Monitoring (5):**
- get_performance_metrics, get_slow_queries, get_prometheus_metrics
- check_duplicate, publish_memory_event

**Statistics (7):**
- get_memory_age_stats, get_deduplication_stats, get_summary_stats
- get_summarization_stats, summary_stats, get_sync_status, get_search_analytics

**Deduplication (5):**
- auto_deduplicate, deduplicate, deduplication_report, schedule_deduplication

**Summarization (6):**
- summarize_old_memories, summarize_category, intelligent_summarize
- auto_summarize_old_memories, schedule_summarization

**Backup (2):**
- verify_backup, rollback_restore

**Multi-Language (6):**
- detect_language, get_supported_languages, search_by_language
- get_language_distribution, cross_language_search, get_search_facets

**Advanced AI (3):**
- cluster_memories, advanced_search, expand_search_query

---

## Configuration File

### File: `C:\Users\vince\.claude.json`

```json
{
  "mcpServers": {
    "cognee": {
      "command": "python",
      "args": [
        "C:/Users/vince/Projects/AI Agents/enhanced-cognee/bin/enhanced_cognee_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:/Users/vince/Projects/AI Agents/enhanced-cognee",
        "ENHANCED_COGNEE_MODE": "true",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "qwen3-embedding:4b-q4_K_M",
        "EMBEDDING_ENDPOINT": "http://localhost:11434/api/embed",
        "EMBEDDING_DIMENSIONS": "1024",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "25432",
        "POSTGRES_DB": "cognee_db",
        "POSTGRES_USER": "cognee_user",
        "POSTGRES_PASSWORD": "cognee_password",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "26333",
        "QDRANT_API_KEY": "***REMOVED***",
        "NEO4J_URI": "bolt://localhost:27687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "cognee_password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "26379",
        "LLM_API_KEY": "56b25fee3dc44a4bb7ca3d60c1b751ff.ebOlp9WhbLgJXv10",
        "LLM_MODEL": "glm-4.7",
        "LLM_PROVIDER": "zai",
        "LLM_ENDPOINT": "https://api.z.ai/v1"
      }
    }
  }
}
```

---

## Enhanced Stack Status

All containers are running and healthy:

```
NAMES                 STATUS              PORTS
cognee-mcp-redis      Up 5 hours (healthy)    0.0.0.0:26379->6379/tcp
cognee-mcp-postgres   Up 5 hours (healthy)    0.0.0.0:25432->5432/tcp
cognee-mcp-qdrant     Up 5 hours (healthy)    0.0.0.0:26333->6333/tcp
cognee-mcp-neo4j      Up 5 hours (healthy)    0.0.0.0:27687->7687/tcp
```

---

## How Tools Work

### Manual (M) - User Controlled
User explicitly triggers these tools for destructive operations or policy settings.

**Example:**
```
User: "Delete all memories older than 1 year"
→ expire_memories(days=365, dry_run=False) [MANUAL]
```

### Auto (A) - AI IDE Controlled
AI IDE automatically calls these based on user queries.

**Example:**
```
User: "What did we discuss about authentication?"
→ search_memories(query="authentication") [AUTO]
```

### System (S) - Enhanced Cognee Controlled
Enhanced Cognee automatically chains these tools after user/AI actions.

**Example:**
```
User: "Add memory: We use JWT"
→ add_memory(...) [AUTO - triggered by AI]
  → check_duplicate() [SYSTEM - chained]
  → publish_memory_event() [SYSTEM - chained]
  → get_performance_metrics() [SYSTEM - chained]
```

---

## Verification Steps

### Step 1: Restart Claude Code
After configuration changes, restart Claude Code to ensure MCP server reconnects.

### Step 2: Check MCP Server Status
```bash
claude mcp list
```

Expected output:
```
cognee: python .../bin/enhanced_cognee_mcp_server.py - [OK] Connected
```

### Step 3: Test Connection
Use the `health` tool to verify all databases are connected.

---

## Project Integration

The Enhanced Cognee MCP Server is configured with **User Scope**, available to all projects globally.

---

## Documentation Files

1. **MCP_TOOLS_REFERENCE_CORRECTED.md** - Corrected tool classification (this file)
2. **MCP_TOOLS_DOCUMENTATION.md** - Original documentation (incorrect classification)
3. **MCP_QUICK_REFERENCE.md** - Quick reference for top 20 tools
4. **README.md** - Official documentation (lines 870-1200)

---

## Configuration Status

**Status:** Complete
**Scope:** Global User Scope
**Tools:** 59 MCP Tools (10 Manual, 16 Auto, 32 System)
**Stack:** Enhanced (PostgreSQL, Qdrant, Neo4j, Redis) - All Healthy
**Path:** Corrected to `bin/enhanced_cognee_mcp_server.py`
**Ready for Use:** Yes (after Claude Code restart)

---

**Corrected by:** Claude (Sonnet 4.5) based on README.md verification
**Original source:** Enhanced Cognee README.md lines 870-1200
