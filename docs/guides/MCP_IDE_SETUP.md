# RNR Enhanced Cognee MCP - Client Setup Guide

RNR Enhanced Cognee MCP server works with any **MCP-compatible** IDE, editor,
or custom client. This guide shows you how to connect any Model Context
Protocol client to the server.

---

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard that allows AI
assistants to communicate with external tools and data sources. RNR Enhanced
Cognee provides a full MCP server implementation exposing 122 tools.

---

## Prerequisites

1. **RNR Enhanced Cognee MCP Server** installed
2. **Enhanced databases running** (PostgreSQL, Qdrant, ArcadeDB, Valkey)
3. **Python 3.10+** with required packages
4. **API keys** configured (if using LLM features)

---

## Setup Instructions (any MCP client)

MCP clients launch the server over **stdio**. Register the server in your
client's MCP configuration using the standard `mcpServers` schema:

```json
{
  "mcpServers": {
    "RNR-Enhanced-Cognee": {
      "command": "python",
      "args": [
        "/path/to/enhanced-cognee/bin/enhanced_cognee_mcp_server.py"
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
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "26379"
      }
    }
  }
}
```

Notes:

- Use the **absolute path** to the server script and to the Python
  interpreter that has the dependencies installed.
- The `env` block can be omitted if your `.env` file already configures
  the database connections.
- `NEO4J_URI` is kept for compatibility; with the default profile it
  points at ArcadeDB's Bolt port (27687).

### Connecting over HTTP instead of stdio

If your client speaks MCP over HTTP (or you want to use the plain REST
surface), start the FastAPI server and point the client at port 8080:

```bash
python -m uvicorn src.enhanced_cognee_mcp:app --host 127.0.0.1 --port 8080
```

- Named routes: `POST /mcp/add_memory`, `/mcp/search_memories`, ...
- Generic dispatch: `POST /tools/{tool_name}` -- reaches all 122 tools.
- Auth headers: `X-API-Key` (when `ENHANCED_API_KEY` is set) and
  `X-Tenant-ID` (multi-tenant deployments).

---

## Testing the Connection

### Method 1: Client-side MCP listing

Most MCP clients provide a command or palette action that lists configured
MCP servers and their connection status. Look for the server named
`RNR-Enhanced-Cognee` and confirm it reports connected with 122 tools.

### Method 2: Manual Test

```bash
# Start the MCP server manually
python bin/enhanced_cognee_mcp_server.py

# Should see:
# =================================================================
#          RNR Enhanced Cognee MCP Server - Enhanced Stack
# =================================================================
# OK Initializing RNR Enhanced Cognee stack...
# OK PostgreSQL connected
# OK Qdrant connected (X collections)
# OK ArcadeDB connected
# OK Valkey connected
#
# OK RNR Enhanced Cognee MCP Server starting...
#   Available tools:
#     Standard Memory MCP Tools:
#       - add_memory
#       - search_memories
#       ...
```

---

## Troubleshooting

### Issue: MCP Server Not Connecting

**Symptoms:**
- Client shows "Failed to connect"
- Tools not appearing

**Solutions:**

1. **Verify Python path:**
   ```bash
   which python  # macOS/Linux
   where python  # Windows

   # Use the absolute path in your client's MCP config
   ```

2. **Check Enhanced databases are running:**
   ```bash
   docker ps | grep enhanced

   # Should show:
   # postgres-enhanced
   # qdrant-enhanced
   # arcadedb-enhanced
   # cognee-mcp-valkey
   ```

3. **Verify .env configuration:**
   ```bash
   cat .env | grep -E "POSTGRES|QDRANT|ARCADEDB|REDIS"
   ```

4. **Check Python dependencies:**
   ```bash
   pip list | grep -E "asyncpg|qdrant|mcp|redis"
   ```

### Issue: Tools Not Showing in the Client

**Solution:**
1. Restart the client completely
2. Clear the client's MCP cache (see your client's documentation)
3. Re-configure the MCP server entry

### Issue: Unicode Encoding Errors on Windows

**Symptoms:**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Solution:**
The RNR Enhanced Cognee MCP server uses ASCII-only output by design. If you
still see errors:

```json
"PYTHONIOENCODING": "utf-8"
```

---

## Available MCP Tools

Once connected, RNR Enhanced Cognee provides **122 tools** across multiple
categories:

### Standard Memory Tools
- `add_memory` - Add memory entries
- `search_memories` - Search with semantic and text search
- `get_memories` - List all memories with filters
- `get_memory` - Get specific memory by ID
- `update_memory` - Update existing memory
- `delete_memory` - Delete memory
- `list_agents` - List all agents

### RNR Enhanced Cognee Tools
- `cognify` - Transform data to knowledge graph
- `search` - Search knowledge graph
- `list_data` - List all documents
- `get_stats` - Get system statistics
- `health` - Health check for all databases

### Memory Management Tools
- `expire_memories` - Expire or archive old memories
- `get_memory_age_stats` - Get memory age distribution
- `set_memory_ttl` - Set time-to-live for specific memory
- `archive_category` - Archive memories by category

### Memory Deduplication Tools
- `check_duplicate` - Check if content is duplicate
- `auto_deduplicate` - Automatically find and merge duplicates
- `get_deduplication_stats` - Get deduplication statistics

### Memory Summarization Tools
- `summarize_old_memories` - Summarize old memories to save space
- `summarize_category` - Summarize memories in a category
- `get_summary_stats` - Get summarization statistics

### Performance Analytics Tools
- `get_performance_metrics` - Get comprehensive performance metrics
- `get_slow_queries` - Identify slow queries
- `get_prometheus_metrics` - Export Prometheus-format metrics

### Cross-Agent Sharing Tools
- `set_memory_sharing` - Set memory sharing policy
- `check_memory_access` - Check if agent can access memory
- `get_shared_memories` - Get shared memories for agent
- `create_shared_space` - Create shared memory space

### Real-Time Sync Tools
- `publish_memory_event` - Publish memory update events
- `get_sync_status` - Get synchronization status
- `sync_agent_state` - Sync memories between agents

See the root `README.md` for the complete 122-tool reference with trigger
types.

---

## Usage Examples

From any MCP-connected client:

```
You: Add a memory about my project structure
AI: [Uses add_memory tool]
You: Search for memories about microservices
AI: [Uses search_memories tool]
```

From Python (HTTP surface):

```python
from enhanced_cognee_client import EnhancedCogneeClient

async with EnhancedCogneeClient(host="localhost", port=8080) as client:
    await client.add_memory(content="Project uses hexagonal architecture")
    hits = await client.search_memories(query="architecture", limit=5)
```
