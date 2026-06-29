# Quick Start

Get RNR Enhanced Cognee running locally in under 5 minutes.

## Prerequisites

- Docker Desktop or compatible (Docker Engine 20+, Compose v2+)
- Python 3.10+
- (Optional) A Claude Code or Cursor install for MCP integration

## 1. Clone + boot the stack

```bash
git clone https://github.com/vincentspereira/RNR-Enhanced-Cognee.git
cd RNR-Enhanced-Cognee

# Boot the 4-container default stack (PostgreSQL + Qdrant + Valkey + ArcadeDB)
docker compose -p RNR-Enhanced-Cognee \
  -f config/docker/docker-compose-enhanced-cognee.yml up -d

# Wait ~10s for containers to become healthy, then verify
docker ps --filter "network=RNR-Enhanced-Cognee" \
  --format "table {{.Names}}\t{{.Status}}"
```

You should see:

```
NAMES                 STATUS
cognee-mcp-postgres   Up (healthy)
cognee-mcp-qdrant     Up (healthy)
cognee-mcp-valkey     Up (healthy)
cognee-mcp-arcadedb   Up
```

## 2. Install the Python deps + bootstrap the schema

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Bootstrap the shared_memory schema in PostgreSQL
docker exec -i cognee-mcp-postgres psql -U cognee_user -d cognee_db \
  < docker/init-scripts/01-init-pgvector.sql
```

## 3. Use it -- two paths

### Path A: Claude Code / Cursor MCP integration (recommended)

Add this block to `~/.claude.json` (Claude Code) or your IDE's MCP config:

```json
{
  "mcpServers": {
    "cognee": {
      "command": "python",
      "args": [
        "/path/to/Enhanced-Cognee/bin/enhanced_cognee_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/path/to/Enhanced-Cognee",
        "ENHANCED_COGNEE_MODE": "true",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "25432",
        "POSTGRES_DB": "cognee_db",
        "POSTGRES_USER": "cognee_user",
        "POSTGRES_PASSWORD": "your-db-password",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "26333",
        "ENHANCED_GRAPH_PROVIDER": "arcadedb",
        "ARCADEDB_TRANSPORT": "http",
        "ARCADEDB_HOST": "localhost",
        "ARCADEDB_HTTP_PORT": "22480",
        "ARCADEDB_DATABASE": "cognee_graph",
        "ARCADEDB_USER": "root",
        "ARCADEDB_PASSWORD": "your-db-password",
        "ENHANCED_CACHE_PROVIDER": "valkey",
        "VALKEY_HOST": "localhost",
        "VALKEY_PORT": "26379"
      }
    }
  }
}
```

Restart Claude Code. You should see 122 new tools available with names like `add_memory`, `search_memories`, `cognify`, `get_memories`, etc.

### Path B: HTTP variant for cross-language SDKs

```bash
python -m uvicorn src.enhanced_cognee_mcp:app --host 127.0.0.1 --port 8080
```

Then in another terminal:

```bash
# Add a memory
curl -X POST http://127.0.0.1:8080/mcp/add_memory \
  -H "Content-Type: application/json" \
  -d '{"content":"RNR Enhanced Cognee uses ArcadeDB as default graph DB","agent_id":"my-agent"}'

# Search
curl -X POST http://127.0.0.1:8080/mcp/search_memories \
  -H "Content-Type: application/json" \
  -d '{"query":"ArcadeDB","limit":5}'

# Health
curl http://127.0.0.1:8080/health
```

## 4. (Optional) Enable MCP server hardening

For production deploys, set these env vars before launching the MCP server:

```bash
export ENHANCED_API_KEY="use-a-32-char-random-token-here"
export ENHANCED_RATE_LIMIT_ADD_MEMORY_PER_MIN=120
export ENHANCED_MAX_PAYLOAD_BYTES=1048576    # 1 MiB
```

Then every `/mcp/*` HTTP call must include `X-API-Key: ...` header. See [Secrets Management](SECRETS_MANAGEMENT.md) for production-grade secret handling.

## 5. (Optional) Enable HTTPS/TLS

For HTTPS termination at the application layer:

```bash
export ENHANCED_HTTPS_CERT_FILE=/path/to/server.crt
export ENHANCED_HTTPS_KEY_FILE=/path/to/server.key

python -m src.enhanced_cognee_mcp   # listens on https://0.0.0.0:8080
```

Or terminate TLS at a reverse proxy (Caddy / nginx) and keep the FastAPI server on plain HTTP behind it.

## Troubleshooting

**ArcadeDB connection refused (HTTP 403 "Security error")?**
The Bolt plugin isn't installed in the public `arcadedata/arcadedb:latest` image. Set `ARCADEDB_TRANSPORT=http` (not `bolt`). The MCP server then routes graph ops through `/api/v1/command/{db}` REST endpoint instead.

**Tests fail because shared_memory.documents doesn't exist?**
Run step 2's `psql -f docker/init-scripts/01-init-pgvector.sql` to bootstrap.

**Memory operations return 500?**
Check `~/.claude.json` env vars match the running containers (ports, credentials, provider names).

**`UnicodeEncodeError: 'charmap' codec can't encode character`?**
You ran RNR Enhanced Cognee against a Windows cp1252 console with Unicode in some output. Our code is ASCII-only by policy; check if a custom plugin / wrapper is injecting emoji. The fix is to remove the emoji or change PYTHONIOENCODING=utf-8 on the calling side.

## Next steps

- [Pluggable DB Backends](PLUGGABLE_DB_BACKENDS.md) -- swap providers per tier
- [Profiles](PROFILES.md) -- 5 pre-baked deployment profiles
- [Monitoring](MONITORING.md) -- SigNoz + Superset observability
- [SDK Publishing](SDK_PUBLISHING.md) -- if you maintain a client SDK
- [Secrets Management](SECRETS_MANAGEMENT.md) -- production secret handling
