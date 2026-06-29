# RNR Enhanced Cognee Implementation for Codex

## Overview

This document is the Codex-facing counterpart to `CLAUDE.md`. Both files describe
the same RNR Enhanced Cognee memory architecture; this one is tuned for the Codex CLI
and uses ASCII-only formatting throughout (no emojis, no checkmarks) so it round-trips
cleanly through Windows cp1252 consoles.

If you're Claude, read `CLAUDE.md`. If you're Codex, this file is yours.

---

## CRITICAL REQUIREMENTS

### 1. ASCII-Only Output (NO Unicode Encoding)

All output must use ASCII characters ONLY. Do NOT use Unicode symbols.

Prohibited:

- Checkmarks / crosses (no Unicode tick, cross, or x-mark glyphs)
- Warning symbols (no Unicode warning sign)
- Emojis of any kind (no chart/wrench/agent/memory/rocket pictographs)
- Arrows (no Unicode left/right/up/down arrows -- use `->`, `<-`, `^`, `v`)
- Special symbols (no Unicode info, sparkle, bullet glyphs)

Use ASCII equivalents:

- Success    -> `OK`   or `[OK]`
- Warning    -> `WARN` or `[WARNING]`
- Error      -> `ERR`  or `[ERROR]`
- Info       -> `INFO` or `[INFO]`
- Document   -> `[DOC]`
- Library    -> `[LIB]`
- Agent      -> `[AGENT]`
- Memory     -> `[MEM]`

Why: Windows console (cp1252 encoding) cannot display Unicode characters. Using
Unicode causes `UnicodeEncodeError: 'charmap' codec can't encode character ...`
which kills any process that tries to print to stdout/stderr.

### 2. Dynamic Categories (NO Hardcoded Categories)

Do NOT use hardcoded categories like ATS/OMA/SMC in code.

WRONG -- hardcoded enum:

```python
class MemoryCategory(Enum):
    ATS = "ats"
    OMA = "oma"
    SMC = "smc"

if category not in ["ats", "oma", "smc"]:
    raise ValueError(f"Invalid category: {category}")
```

CORRECT -- dynamic category loading from config:

```python
config = EnhancedConfig()
categories = config.category_prefixes  # Loaded from .enhanced-cognee-config.json

def add_memory(agent_id: str, content: str, memory_category: str):
    # Categories are dynamic - accept any string
    # No validation against hardcoded list
    pass
```

Configuration file (`.enhanced-cognee-config.json`):

```json
{
  "categories": {
    "trading": {"prefix": "trading_"},
    "development": {"prefix": "dev_"},
    "analysis": {"prefix": "analysis_"},
    "custom_project": {"prefix": "proj1_"}
  }
}
```

### 3. Standard Memory MCP Interface

RNR Enhanced Cognee MCP server provides standard memory tools for Codex integration.

Available Memory Tools:

- `add_memory`       -- Add memory entry
- `search_memories`  -- Search memories (semantic + text)
- `get_memories`     -- List all memories with filters
- `get_memory`       -- Get specific memory by ID
- `update_memory`    -- Update existing memory
- `delete_memory`    -- Delete memory
- `list_agents`      -- List all agents with memories

RNR Enhanced Cognee Tools:

- `cognify`    -- Add data to knowledge graph
- `search`     -- Search knowledge graph
- `list_data`  -- List all documents
- `get_stats`  -- Get system statistics
- `health`     -- Health check

All memory tools accept an optional `tenant_id` parameter. HTTP callers should
prefer the `X-Tenant-ID` request header instead -- the FastAPI middleware opens
a `TenantContext` automatically.

---

## Implementation Status (as of 2026-05-21)

Completed components:

- [OK] RNR Enhanced Cognee MCP server (stdio + FastAPI HTTP variants, ASCII-only)
- [OK] Standard Memory MCP tools (Codex-compatible)
- [OK] Dynamic Category System (no hardcoded categories)
- [OK] Multi-tenant data partitioning (ContextVar + naming helpers + per-tenant
       Postgres schema bootstrap + HTTP X-Tenant-ID middleware)
- [OK] Enhanced Memory Stack: PostgreSQL, Qdrant, ArcadeDB (default), Valkey
- [OK] 20+ pluggable storage providers across 4 tiers
- [OK] Cross-language client SDKs: Python, Node.js, Go, Rust
- [OK] ASCII-only output (no Unicode encoding issues)

MCP Server Configuration:

- Stdio entry: `/path/to/enhanced-cognee/enhanced_cognee_mcp_server.py`
- HTTP entry: `src/enhanced_cognee_mcp.py` (FastAPI)
- Default Memory: YES -- can be used as Codex's default memory system

---

## Architecture Overview

### Memory Stack Architecture

```
RNR Enhanced Cognee Memory Stack (default profile, 100% MIT + Apache-2.0)
+-- PostgreSQL + pgvector (Port 25432)
|   +-- Relational database with vector extension
|   +-- Agent memory persistence
|   +-- SQL + vector similarity search
+-- Qdrant (Port 26333)
|   +-- High-performance vector database
|   +-- Semantic search capabilities
|   +-- Memory embeddings storage
+-- ArcadeDB (Port 27687 Bolt, 22480 Studio HTTP) -- Apache-2.0
|   +-- Multi-model graph database (was Neo4j; default since Phase 2)
|   +-- openCypher + Bolt (drop-in for neo4j Python driver)
|   +-- Dual transport: ARCADEDB_TRANSPORT=bolt (default) | http
|   +-- Set ENHANCED_GRAPH_PROVIDER=neo4j to opt back into Neo4j
+-- Valkey (Port 26379) -- Apache-2.0 (was Redis)
|   +-- High-speed caching layer
|   +-- Real-time memory access
|   +-- Session management
+-- RNR Enhanced Cognee MCP Server
    +-- Standard Memory MCP tools (Codex)
    +-- RNR Enhanced Cognee tools (advanced features)
    +-- ASCII-only output (Windows compatible)
```

### Pluggable Storage Providers (4 tiers, ~20 providers)

Switch any tier via env vars; see `docs/PROFILES.md` for full matrix.

Graph tier (9 providers):

- arcadedb (default, Apache-2.0, Bolt + HTTP transports)
- neo4j (GPLv3 community, opt-in)
- apache_age (Postgres extension, openCypher subset)
- memgraph (BSL)
- kuzu (MIT embedded)
- networkx_inmemory (BSD, in-process)
- arangodb (Apache-2.0, AQL via Cypher translator)
- nebulagraph (Apache-2.0, nGQL via openCypher mode)
- ladybug (Cognee-native in-process)

Vector tier (6 providers):

- qdrant (default, Apache-2.0)
- pgvector (Postgres extension)
- lancedb (Apache-2.0, embedded)
- chroma (Apache-2.0)
- weaviate (BSD-3, v4 client)
- milvus (Apache-2.0)

Cache tier (5 providers):

- valkey (default, Apache-2.0)
- memcached (Apache-2.0)
- sqlite (built-in, persistent fallback)
- redis (BSD, opt-in via legacy stacks)
- redis_compat (labelled alias of valkey for KeyDB / Garnet / Dragonfly)

Relational tier (12 providers):

- postgres (default), sqlite, duckdb (MIT analytics), cockroachdb (via postgres
  wire protocol), mysql / mariadb (asyncmy), mssql / sqlserver (aioodbc),
  oracle (oracledb thin/thick), db2 (ibm_db), snowflake (cloud DW),
  databricks (Unity Catalog SQL Warehouse)

### Multi-Tenant Data Partitioning

Tenant isolation is enforced at the storage layer via `src/multi_tenant.py`:

- `TenantContext("acme")` -- ContextVar-based sync + async context manager
- `tenant_scoped_table("shared_memory.documents")` -> `shared_memory.documents_t_acme`
- `tenant_scoped_collection("embeddings")` -> `embeddings_t_acme`
- `tenant_scoped_key("session:abc")` -> `t_acme:session:abc`
- `tenant_scoped_graph("default")` -> `default_t_acme`
- `ensure_tenant_schema(pool, tenant_id)` -- lazy per-tenant CREATE TABLE LIKE
- `ENHANCED_REQUIRE_TENANT=1` -- production safety knob (refuse un-tenanted
  storage calls instead of falling back to global tables)

HTTP callers send `X-Tenant-ID: acme` and the FastAPI middleware opens the
TenantContext for the entire request. Bare stdio MCP callers can pass
`tenant_id="acme"` to any of the memory tools.

### Dynamic Category System

```
Dynamic Memory Categories (configured in .enhanced-cognee-config.json)

Categories are NOT hardcoded. Projects define their own:

Example configurations:
- Trading System: "trading"     category with "trading_"  prefix
- Development:    "development"  category with "dev_"      prefix
- Analysis:       "analysis"     category with "analysis_" prefix
- Custom:         Any category name, any prefix

No hardcoded ATS/OMA/SMC restrictions.
```

---

## Codex Integration Guidelines

### Memory Operations with MCP Tools

Adding memories:

```
Use MCP tool: add_memory
Parameters:
  - content:   str - The memory content to store
  - user_id:   str - User identifier (default: "default")
  - agent_id:  str - Agent identifier (default: "codex")
  - tenant_id: str - Optional tenant ID for multi-tenant isolation
  - metadata:  str - Optional JSON string with metadata

Returns: Memory ID
```

Searching memories:

```
Use MCP tool: search_memories
Parameters:
  - query:     str - Search query text
  - limit:     int - Maximum results (default: 10)
  - user_id:   str - User identifier (default: "default")
  - agent_id:  str - Optional agent filter
  - tenant_id: str - Optional tenant ID

Returns: Formatted memory results with content
```

Retrieving memories:

```
Use MCP tool: get_memories
Parameters:
  - user_id:   str - User identifier (default: "default")
  - agent_id:  str - Optional agent filter
  - limit:     int - Maximum results (default: 50)
  - tenant_id: str - Optional tenant ID

Returns: List of all memories matching filters
```

Getting / updating / deleting a specific memory:

```
Use MCP tool: get_memory     (memory_id: str)              -> full memory
Use MCP tool: update_memory  (memory_id: str, content: str) -> status
Use MCP tool: delete_memory  (memory_id: str)              -> status
```

Listing agents:

```
Use MCP tool: list_agents
Parameters: None
Returns:    List of all agent IDs with memory counts
```

### RNR Enhanced Cognee Tools (Advanced)

Cognify -- transform data to knowledge:

```
Use MCP tool: cognify
Parameters:
  - data: str - Text data to process and add to knowledge graph
Returns: Status message with document ID
```

Search knowledge graph:

```
Use MCP tool: search
Parameters:
  - query: str - Search query text
  - limit: int - Maximum results (default: 10)
Returns: Search results from knowledge graph
```

List documents:

```
Use MCP tool: list_data
Parameters: None
Returns:    Formatted list of all documents
```

Stats / health:

```
Use MCP tool: get_stats   -> System status and statistics (JSON)
Use MCP tool: health      -> Health status of all database connections
```

### Memory Storage Patterns

Pattern 1 -- simple memory storage:

```python
add_memory(
    content="Important information to remember",
    agent_id="my-agent",
)
```

Pattern 2 -- categorised memory storage with metadata:

```python
add_memory(
    content="Trading strategy parameters",
    agent_id="trading-bot",
    metadata='{"category": "trading", "strategy": "momentum"}',
)
```

Pattern 3 -- tenant-scoped search:

```python
search_memories(
    query="risk management",
    limit=10,
    agent_id="trading-bot",
    tenant_id="acme",
)
```

---

## Project Structure for Codex

### Key Files and Their Purposes

```
enhanced-cognee/
+-- README.md                       # Comprehensive project documentation
+-- AGENTS.md                       # This file (Codex)
+-- CLAUDE.md                       # Claude equivalent
+-- .env                            # Environment configuration
+-- .enhanced-cognee-config.json    # Dynamic category configuration
+-- docker/                         # Docker deployment files
|   +-- docker-compose-enhanced-cognee.yml
+-- enhanced_cognee_mcp_server.py   # Stdio MCP server entry
+-- src/                            # Source code
|   +-- enhanced_cognee_mcp.py      # FastAPI HTTP MCP server
|   +-- mcp_memory_tools.py         # Standard memory tools
|   +-- agent_memory_integration.py # Core memory integration
|   +-- multi_tenant.py             # Tenant isolation helpers
|   +-- db_factory.py               # Pluggable provider factory
|   +-- db_adapters/                # ~20 pluggable adapters
+-- clients/                        # Cross-language client SDKs
|   +-- python/                     # PyPI: enhanced-cognee-client
|   +-- node/                       # npm-ready
|   +-- go/                         # pkg.go.dev-ready
|   +-- rust/                       # crates.io-ready
+-- tests/                          # 4000+ unit + integration tests
|   +-- benchmarks/                 # Cross-provider benchmark runner
|   +-- integration/                # Live stack integration tests
|   +-- load/                       # Locust load test scenarios
+-- monitoring/                     # SigNoz + Superset dashboards
+-- docs/                           # Architecture, profiles, runbooks
```

### MCP Server Configuration

Stdio entry: `/path/to/enhanced-cognee/enhanced_cognee_mcp_server.py`

Codex MCP config (`~/.codex/mcp_servers.json` or equivalent):

```json
{
  "mcpServers": {
    "cognee": {
      "command": "python",
      "args": [
        "/path/to/enhanced-cognee/enhanced_cognee_mcp_server.py"
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
        "ENHANCED_GRAPH_PROVIDER": "arcadedb",
        "ARCADEDB_HOST": "localhost",
        "ARCADEDB_BOLT_PORT": "27687",
        "ARCADEDB_HTTP_PORT": "22480",
        "ARCADEDB_DATABASE": "cognee",
        "ARCADEDB_USER": "root",
        "ARCADEDB_PASSWORD": "your-db-password",
        "ARCADEDB_TRANSPORT": "bolt",
        "ENHANCED_CACHE_PROVIDER": "valkey",
        "VALKEY_HOST": "localhost",
        "VALKEY_PORT": "26379"
      }
    }
  }
}
```

---

## Quick Start for Codex

### 1. Start Enhanced Stack

```bash
cd /path/to/enhanced-cognee
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

docker ps
# Should see: postgres-enhanced, qdrant-enhanced, arcadedb-enhanced, valkey-enhanced
```

### 2. Configure Dynamic Categories (Optional)

Create `.enhanced-cognee-config.json`:

```json
{
  "categories": {
    "trading":     {"prefix": "trading_", "description": "Trading system memories"},
    "development": {"prefix": "dev_",     "description": "Development memories"}
  }
}
```

### 3. Use MCP Memory Tools

Add a memory:

```
Call MCP tool: add_memory
Parameters:
  content:   "Important information to remember"
  agent_id:  "my-agent"
  metadata:  '{"category": "trading", "priority": "high"}'
  tenant_id: "acme"     # optional
```

Search memories:

```
Call MCP tool: search_memories
Parameters:
  query:    "risk management"
  limit:    10
  agent_id: "my-agent"
```

### 4. Use RNR Enhanced Cognee Tools

```
Call MCP tool: cognify  (data: "Text to process and add to knowledge graph")
Call MCP tool: search   (query: "semantic search query", limit: 10)
Call MCP tool: health   -> Connection status of all databases
```

### 5. Verify Installation

```bash
codex mcp list
# Should show:
#   cognee: python .../enhanced_cognee_mcp_server.py
#   Status: [OK] Connected
```

---

## Monitoring and Debugging

### Health Checks

```python
# Via MCP tool
health() ->
Returns:
  RNR Enhanced Cognee Health:
  OK PostgreSQL
  OK Qdrant
  OK ArcadeDB
  OK Valkey
```

### System Statistics

```python
get_stats() ->
{
  "status": "RNR Enhanced Cognee MCP Server",
  "databases": {
    "postgresql": "OK Connected (42 documents)",
    "qdrant":     "OK Connected (5 collections)",
    "arcadedb":   "OK Connected",
    "valkey":     "OK Connected"
  }
}
```

### Debug Commands

```bash
docker ps | grep enhanced

# Postgres
docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
  -c "SELECT COUNT(*) FROM shared_memory.documents;"

# Qdrant
curl http://localhost:26333/collections

# ArcadeDB Studio
xdg-open http://localhost:22480

# Valkey
docker exec -it valkey-enhanced valkey-cli PING
```

---

## Best Practices for Codex

### CRITICAL: ASCII-Only Output

Always use ASCII characters in output:

- Success: `OK`   or `[OK]`
- Warning: `WARN` or `[WARNING]`
- Error:   `ERR`  or `[ERROR]`
- Info:    `INFO` or `[INFO]`

Never use Unicode symbols (checkmarks, crosses, emojis, arrows, special symbols).

Example:

```python
# CORRECT
print("OK PostgreSQL connected")
print("WARN Qdrant connection slow")
print("ERR Failed to connect to ArcadeDB")

# WRONG -- will UnicodeEncodeError on Windows cp1252
# print("<check> PostgreSQL connected")
```

### CRITICAL: Dynamic Categories (No Hardcoding)

Accept any category name; load from config; never validate against a hardcoded list.

### Memory Management

1. Use standard MCP tools (`add_memory`, `search_memories`, etc.) for Codex
   compatibility
2. Provide rich metadata JSON for better searchability
3. Always specify `agent_id` for memory segregation
4. Use `tenant_id` (or `X-Tenant-ID` HTTP header) for multi-tenant isolation
5. Configure categories via `.enhanced-cognee-config.json`, not hardcoded

### Performance Optimisation

1. Leverage Valkey cache -- frequently accessed data is automatically cached
2. Use vector search -- Qdrant / pgvector provides semantic similarity
3. Batch operations when possible
4. Monitor statistics via `get_stats()`

### Security Considerations

1. Store credentials in `.env`, never in code
2. Validate `agent_id` in memory operations
3. Sanitise metadata to prevent injection
4. Use `agent_id` + `tenant_id` for access control
5. MCP server hardening (PR #37): set `ENHANCED_API_KEY` to require `X-API-Key`;
   `ENHANCED_RATE_LIMIT_PER_MINUTE` for per-tool rate limits;
   `ENHANCED_MAX_PAYLOAD_BYTES` to cap request size

### Error Handling

Always use ASCII-only error messages:

```python
# CORRECT
try:
    result = await add_memory(...)
except Exception as e:
    logger.error(f"ERR Failed to add memory: {e}")
    return f"ERR Memory operation failed: {e}"
```

### Configuration Best Practices

1. Use `.env` file for all configuration
2. Define categories in `.enhanced-cognee-config.json`
3. Use Enhanced port range (25000+) to avoid host conflicts
4. Update Codex MCP config with correct paths

Example `.env`:

```bash
# Enhanced Stack Configuration
ENHANCED_COGNEE_MODE=true

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=25432
POSTGRES_DB=cognee_db
POSTGRES_USER=cognee_user
POSTGRES_PASSWORD=your-db-password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=26333

# ArcadeDB (default graph since Phase 2)
ENHANCED_GRAPH_PROVIDER=arcadedb
ARCADEDB_HOST=localhost
ARCADEDB_BOLT_PORT=27687
ARCADEDB_HTTP_PORT=22480
ARCADEDB_DATABASE=cognee
ARCADEDB_USER=root
ARCADEDB_PASSWORD=your-db-password
ARCADEDB_TRANSPORT=bolt

# Valkey (cache, replaces Redis)
ENHANCED_CACHE_PROVIDER=valkey
VALKEY_HOST=localhost
VALKEY_PORT=26379

# Dynamic Categories
MEMORY_CATEGORIZATION=true
ENHANCED_COGNEE_CONFIG_PATH=.enhanced-cognee-config.json

# Multi-tenant safety (refuse un-tenanted storage in production)
# ENHANCED_REQUIRE_TENANT=1

# MCP hardening
# ENHANCED_API_KEY=your-key-here
# ENHANCED_RATE_LIMIT_PER_MINUTE=120
# ENHANCED_MAX_PAYLOAD_BYTES=1048576
```

---

## Current Implementation State

### Completed Components (100%)

Enhanced Memory Stack:

- [OK] PostgreSQL + pgvector (Port 25432)
- [OK] Qdrant Vector Database (Port 26333)
- [OK] ArcadeDB Graph Database (Port 27687 Bolt + 22480 HTTP) -- default since Phase 2
- [OK] Valkey Cache (Port 26379)

MCP Server:

- [OK] Stdio MCP server (`enhanced_cognee_mcp_server.py`)
- [OK] FastAPI HTTP MCP server (`src/enhanced_cognee_mcp.py`)
- [OK] Standard Memory MCP tools (Codex compatible)
- [OK] RNR Enhanced Cognee tools (advanced features)
- [OK] ASCII-only output (Windows compatible)
- [OK] API key auth + token-bucket rate limiter + payload cap (PR #37)

Multi-Tenancy:

- [OK] TenantContext + naming helpers + per-tenant Postgres schema bootstrap (PR #39)
- [OK] Wired across 24 storage modules / 100+ call sites (PR #39)
- [OK] X-Tenant-ID HTTP header middleware (PR #43)
- [OK] 15 cross-tenant isolation tests (PR #42)

Cross-Language Clients (PR #41):

- [OK] Python (PyPI: enhanced-cognee-client)
- [OK] Node.js / TypeScript (npm-ready)
- [OK] Go (pkg.go.dev-ready)
- [OK] Rust (crates.io-ready)

Configuration:

- [OK] Dynamic category system (no hardcoded categories)
- [OK] Environment-based configuration
- [OK] JSON-based category configuration

Integration:

- [OK] Docker deployment with Enhanced stack
- [OK] MCP configuration for Codex
- [OK] Health checks and monitoring
- [OK] Live SigNoz + Superset smoke test (PR #38)
- [OK] Cross-provider benchmark runner (PR #37)
- [OK] Locust load test scenarios (PR #27)

### Integration Points

Port Mappings (Enhanced range):

- PostgreSQL: 25432 (not 5432)
- Qdrant:     26333 (not 6333)
- ArcadeDB:   27687 Bolt / 22480 HTTP (replaces Neo4j 7687)
- Valkey:     26379 (replaces Redis 6379)

Configuration Files:

- `.env`                          -- Database connection settings
- `.enhanced-cognee-config.json`  -- Dynamic category configuration
- Codex MCP config                -- Cognee server registration

### Architecture Benefits

Scalability:

- Enterprise-grade PostgreSQL handles large datasets
- Qdrant provides high-performance vector search
- ArcadeDB manages complex relationships with multi-model flexibility
- Valkey ensures low-latency cache access

Performance:

- 400-700% improvement over original memory stack
- Distributed architecture prevents bottlenecks
- Efficient caching reduces database load

Flexibility:

- Dynamic categories (no hardcoded ATS/OMA/SMC)
- 20+ pluggable providers across 4 tiers
- Modular architecture allows easy extension
- Standard MCP interface for Codex integration

Reliability:

- Health monitoring for all services
- Comprehensive error handling
- ENHANCED_REQUIRE_TENANT production safety knob

Licensing:

- Default stack: 100% MIT + Apache-2.0 (no GPL, no commercial gates)

---

## Support and Troubleshooting

### Common Issues and Solutions

1. MCP Server Not Connecting

   Problem: `codex mcp list` shows `Failed to connect`

   Solutions:

   ```bash
   # Check Python path in Codex MCP config
   # Should be: /path/to/enhanced-cognee/enhanced_cognee_mcp_server.py

   docker ps | grep enhanced
   ls /path/to/enhanced-cognee/.env
   ```

2. Unicode Encoding Error

   Problem: `UnicodeEncodeError: 'charmap' codec can't encode character`

   Solution: Ensure all output uses ASCII-only equivalents. See the ASCII-Only
   Output section above.

3. Category Not Found

   Problem: `Invalid category: trading`

   Solution: Ensure categories are configured dynamically in
   `.enhanced-cognee-config.json` rather than hardcoded in code.

4. Port Conflicts

   Problem: Services won't start due to port conflicts

   Solution: Enhanced stack uses non-standard ports:

   - PostgreSQL: 25432 (not 5432)
   - Qdrant:     26333 (not 6333)
   - ArcadeDB:   27687 / 22480
   - Valkey:     26379 (not 6379)

5. Multi-tenant Schema Not Found

   Problem: `relation "shared_memory.documents_t_<tenant>" does not exist`

   Solution: Call `ensure_tenant_schema(pool, tenant_id)` once on tenant
   onboarding, or rely on the lazy bootstrap that runs on the first storage
   write for a given tenant.

### Debug Commands

```bash
docker ps | grep enhanced

# Test PostgreSQL
docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db -c "SELECT 1;"

# Test Qdrant
curl http://localhost:26333/collections

# Test ArcadeDB
curl -u root:your-db-password http://localhost:22480/api/v1/server

# Test Valkey
docker exec -it valkey-enhanced valkey-cli PING
```

### Health Check via MCP

```
Call MCP tool: health

Returns:
  RNR Enhanced Cognee Health:
  OK PostgreSQL
  OK Qdrant
  OK ArcadeDB
  OK Valkey
```

---

## Future Enhancements

Planned but not currently active:

- MAS (Multi-Agent System) integration -- deferred to a future session
- SDK publishing to public registries (npm / pkg.go.dev / crates.io)
- Knowledge graph visualisation dashboard
- Additional vector database support (e.g. Marqo, Vespa)
- Cross-language gRPC transport (currently HTTP-only)

### Extension Points

Custom categories (`.enhanced-cognee-config.json`):

```json
{
  "categories": {
    "my_custom_category": {
      "prefix": "custom_",
      "description": "My custom memories"
    }
  }
}
```

Custom memory wrappers:

```python
class CustomMemoryWrapper:
    def __init__(self, mcp_client):
        self.mcp = mcp_client

    async def store_custom_data(self, data):
        return await self.mcp.add_memory(
            content=json.dumps(data),
            metadata='{"category": "custom"}',
        )
```

---

## Additional Resources

Documentation:

- `README.md`             -- Project documentation
- `docker/README.md`      -- Deployment instructions
- `docs/PROFILES.md`      -- Active provider matrix per profile
- `docs/PHASE5_TODO.md`   -- Outstanding work tracker
- `docs/HANDOVER.md`      -- Session handover notes

Configuration files:

- `.env`                          -- Database connection settings
- `.enhanced-cognee-config.json`  -- Dynamic categories

Source code:

- `enhanced_cognee_mcp_server.py`     -- Stdio MCP entry
- `src/enhanced_cognee_mcp.py`        -- FastAPI HTTP MCP server
- `src/mcp_memory_tools.py`           -- Standard memory tools
- `src/agent_memory_integration.py`   -- Core memory integration
- `src/multi_tenant.py`               -- Tenant isolation helpers
- `src/db_factory.py`                 -- Pluggable provider factory
- `src/db_adapters/`                  -- ~20 pluggable adapters

Client SDKs:

- `clients/python/` -- PyPI: enhanced-cognee-client
- `clients/node/`   -- npm-ready
- `clients/go/`     -- pkg.go.dev-ready
- `clients/rust/`   -- crates.io-ready

---

RNR Enhanced Cognee Implementation -- enterprise-grade memory architecture for
Codex with standard MCP memory interface, dynamic categories, multi-tenant
isolation, cross-language SDKs, and ASCII-only output.

For Codex: This system provides a complete, production-ready memory framework
that works as Codex's default memory system. All components are fully functional
and integrated with standard memory MCP tools.

Key Points:

1. ASCII-only output (no Unicode symbols)
2. Dynamic categories (no hardcoded ATS/OMA/SMC)
3. Standard Memory MCP tools (Codex compatible)
4. Enhanced Stack: PostgreSQL, Qdrant, ArcadeDB (default), Valkey
5. 20+ pluggable providers across 4 tiers
6. Multi-tenant data partitioning with HTTP header support
7. Cross-language client SDKs: Python, Node, Go, Rust
8. MCP server hardening: API key + rate limit + payload cap
