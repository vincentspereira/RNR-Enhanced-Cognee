# Enhanced Cognee MCP - Multi-IDE Setup Guide

Enhanced Cognee MCP server works with any **MCP-compatible** AI IDE or editor. This guide shows you how to set it up with popular AI IDEs.

---

## 🎯 What is MCP?

The **Model Context Protocol (MCP)** is an open standard that allows AI assistants to communicate with external tools and data sources. Enhanced Cognee provides a full MCP server implementation.

---

## 🚀 Supported IDEs & Editors

### ✅ Officially Tested:
- **Claude Code** (Anthropic)
- **VS Code** (with Continue.dev)
- **Cursor**
- **Windsurf**
- **Antigravity**
- **Continue.dev**

### ✅ Should Work (MCP-Compatible):
- **Cline** (VS Code extension)
- **Roo Code** (VS Code extension)
- **Any MCP-compatible client**

---

## 📋 Prerequisites

1. **Enhanced Cognee MCP Server** installed
2. **Enhanced databases running** (PostgreSQL, Qdrant, Neo4j, Redis)
3. **Python 3.10+** with required packages
4. **API keys** configured (if using LLM features)

---

## 🔧 Setup Instructions by IDE

### 1. Claude Code (Anthropic)

**Configuration File:** `~/.claude.json` (macOS/Linux) or `%APPDATA%\Claude\claude.json` (Windows)

```json
{
  "mcpServers": {
    "enhanced-cognee": {
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

**Verify:**
```bash
# Check MCP server status
claude mcp list

# Should show:
# enhanced-cognee: python .../enhanced_cognee_mcp_server.py - ✅ Connected
```

---

### 2. VS Code (with Continue.dev)

**Step 1: Install Continue.dev Extension**
```bash
# Install from VS Code Marketplace
# Search: "Continue - Autocomplete AI Chat"
```

**Step 2: Configure Continue**

Create/edit `~/.continue/config.json` (macOS/Linux) or `%USERPROFILE%\.continue\config.json` (Windows):

```json
{
  "experimental": {
    "model": "claude-3.5-sonnet",
    "mcpServers": {
      "enhanced-cognee": {
        "command": "python",
        "args": [
          "C:\\Users\\YourUsername\\Projects\\AI Agents\\enhanced-cognee\\enhanced_cognee_mcp_server.py"
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
}
```

**Step 3: Restart VS Code**

**Step 4: Verify**
- Open Continue sidebar in VS Code
- Type `/` to see available tools
- You should see Enhanced Cognee tools listed

---

### 3. Cursor IDE

**Configuration File:** `~/.cursorrc` (macOS/Linux) or `%USERPROFILE%\.cursorrc` (Windows)

```json
{
  "mcpServers": {
    "enhanced-cognee": {
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

**Verify:**
- Open Cursor settings
- Go to MCP Servers section
- Enhanced Cognee should appear as connected

---

### 4. Windsurf (Codeium)

**Configuration File:** `~/.windsurfm/config.json`

```json
{
  "mcp": {
    "servers": {
      "enhanced-cognee": {
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
}
```

---

### 5. Antigravity

**Configuration File:** Antigravity settings → MCP Servers

```json
{
  "mcpServers": {
    "enhanced-cognee": {
      "command": "python",
      "args": [
        "/absolute/path/to/enhanced-cognee/enhanced_cognee_mcp_server.py"
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

---

### 6. Continue.dev Standalone

**Configuration File:** `~/.continuerc/config.json`

```json
{
  "mcpServers": {
    "enhanced-cognee": {
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

---

## 🧪 Testing MCP Connection

### Method 1: Using Claude Code CLI
```bash
# List all MCP servers
claude mcp list

# Check specific server status
claude mcp test enhanced-cognee
```

### Method 2: Manual Test
```bash
# Start the MCP server manually
python enhanced_cognee_mcp_server.py

# Should see:
# =================================================================
#          Enhanced Cognee MCP Server - Enhanced Stack
# =================================================================
# OK Initializing Enhanced Cognee stack...
# OK PostgreSQL connected
# OK Qdrant connected (X collections)
# OK Neo4j connected
# OK Redis connected
#
# OK Enhanced Cognee MCP Server starting...
#   Available tools:
#     Standard Memory MCP Tools:
#       - add_memory
#       - search_memories
#       ...
```

---

## 🔍 Troubleshooting

### Issue: MCP Server Not Connecting

**Symptoms:**
- IDE shows "Failed to connect"
- Tools not appearing

**Solutions:**

1. **Verify Python path:**
   ```bash
   which python  # macOS/Linux
   where python  # Windows

   # Use absolute path in IDE config:
   /usr/local/bin/python/enhanced_cognee_mcp_server.py
   ```

2. **Check Enhanced databases are running:**
   ```bash
   docker ps | grep enhanced

   # Should show:
   # postgres-enhanced
   # qdrant-enhanced
   # neo4j-enhanced
   # redis-enhanced
   ```

3. **Verify .env configuration:**
   ```bash
   cat .env | grep -E "POSTGRES|QDRANT|NEO4J|REDIS"
   ```

4. **Check Python dependencies:**
   ```bash
   pip list | grep -E "asyncpg|qdrant|neo4j|redis"
   ```

### Issue: Tools Not Showing in IDE

**Solution:**
1. Restart the IDE completely
2. Clear MCP cache:
   ```bash
   # Claude Code
   rm -rf ~/.claude/mcp_cache

   # Continue.dev
   rm -rf ~/.continue/mcp_cache
   ```
3. Re-configure MCP server

### Issue: Unicode Encoding Errors on Windows

**Symptoms:**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Solution:**
The Enhanced Cognee MCP server uses ASCII-only output by design. If you still see errors:

```python
# Set environment variable in IDE config:
"PYTHONIOENCODING": "utf-8"
```

---

## 📊 Available MCP Tools

Once connected, Enhanced Cognee provides these tools:

### Standard Memory Tools
- `add_memory` - Add memory entries
- `search_memories` - Search with semantic and text search
- `get_memories` - List all memories with filters
- `get_memory` - Get specific memory by ID
- `update_memory` - Update existing memory
- `delete_memory` - Delete memory
- `list_agents` - List all agents

### Enhanced Cognee Tools
- `cognify` - Transform data to knowledge graph
- `search` - Search knowledge graph
- `list_data` - List all documents
- `get_stats` - Get system statistics
- `health` - Health check for all databases

---

## 🎯 Usage Examples by IDE

### Claude Code
```
You: Add a memory about my project structure
AI: [Uses add_memory tool]
You: Search for memories about microservices
AI: [Uses search_memories tool]
```

### VS Code + Continue
```
# In Continue chat interface
User: /add_memory "I use PostgreSQL for my database"
AI: Memory added successfully!

User: /search_memories "database"
AI: Found 3 memories about database:
    1. I use PostgreSQL for my database
    2. Database port is 25432
    3. Redis is used for caching
```

### Cursor
```
# In Cursor AI chat
You: Remember that I prefer TypeScript
AI: [Uses add_memory tool] Got it! I'll remember your preference.

You: What do you know about my preferences?
AI: [Uses search_memories tool] Based on your memories:
    - You prefer TypeScript
    - You use Enhanced Cognee for memory
    - You like ASCII-only output
```

---

## 🚀 Next Steps

1. **Configure your preferred IDE** using the examples above
2. **Start Enhanced databases:**
   ```bash
   docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
   ```
3. **Test MCP connection** in your IDE
4. **Start using Enhanced Cognee tools** through the AI assistant

---

## 📚 Additional Resources

- **Enhanced Cognee README:** https://github.com/vincentspereira/Enhanced-Cognee
- **MCP Specification:** https://modelcontextprotocol.io/
- **Claude Code Docs:** https://docs.anthropic.com/
- **Continue.dev Docs:** https://docs.continue.dev/
- **Cursor Docs:** https://cursor.sh/docs

---

## 💡 Tips

1. **Use absolute paths** for the MCP server script
2. **Start databases first** before starting the IDE
3. **Check logs** if tools don't appear
4. **Restart IDE** after configuration changes
5. **Test with simple command first** (e.g., `health` tool)

---

## 🆘 Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Verify Enhanced databases are running
3. Review IDE-specific MCP documentation
4. Check GitHub Issues: https://github.com/vincentspereira/Enhanced-Cognee/issues
5. Open a new issue with details about your IDE and error

---

**Happy coding with Enhanced Cognee across all your favorite AI IDEs! 🚀**
