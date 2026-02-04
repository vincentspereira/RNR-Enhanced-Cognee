# Enhanced Cognee MCP - Multi-IDE Setup Guide

Enhanced Cognee MCP server works with any **MCP-compatible** AI IDE or editor. This guide shows you how to set it up with popular AI IDEs.

---

## 🎯 What is MCP?

The **Model Context Protocol (MCP)** is an open standard that allows AI assistants to communicate with external tools and data sources. Enhanced Cognee provides a full MCP server implementation.

---

## 🚀 Supported IDEs & Editors

### ✅ Officially Tested:
- **Claude Code** (Anthropic)
- **VS Code** (with Continue.dev, Kilo Code)
- **Cursor**
- **Windsurf**
- **Antigravity**
- **Continue.dev**
- **GitHub Copilot** (VS Code extension)

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

### 7. Kilo Code (VS Code Extension)

**Kilo Code** is a VS Code extension that provides AI-powered coding assistance with MCP support.

**Step 1: Install Kilo Code Extension**
```bash
# Install from VS Code Marketplace
# Search: "Kilo Code"
```

**Step 2: Configure Kilo Code**

Create/edit VS Code settings (`settings.json`):

**Via UI:**
1. Open VS Code
2. Go to Settings (Ctrl+, / Cmd+,)
3. Search for "kilo code"
4. Find "Kilo Code: MCP Servers" setting
5. Click "Edit in settings.json"

**Via settings.json:**

```json
{
  "kiloCode.mcpServers": {
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
```

**Alternative: Workspace Configuration**

Create `.vscode/settings.json` in your project:

```json
{
  "kiloCode.mcpServers": {
    "enhanced-cognee": {
      "command": "python",
      "args": [
        "${workspaceFolder}/../enhanced-cognee/enhanced_cognee_mcp_server.py"
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

**Step 3: Reload VS Code**
- Press Ctrl+Shift+P (Windows/Linux) or Cmd+Shift+P (Mac)
- Type "Reload Window" and press Enter

**Step 4: Verify**
- Open Kilo Code panel in VS Code
- Look for MCP connection indicator
- Should show "Enhanced Cognee" as connected

**Usage with Kilo Code:**
```
# In Kilo Code chat interface
User: Add memory about my project setup
Kilo Code: [Uses add_memory tool]

User: Search memories about database
Kilo Code: [Uses search_memories tool]
```

---

### 8. GitHub Copilot (VS Code Extension)

**GitHub Copilot** now supports MCP servers for extended capabilities.

**Step 1: Install GitHub Copilot Extension**
```bash
# Install from VS Code Marketplace
# Search: "GitHub Copilot"
```

**Step 2: Configure GitHub Copilot MCP**

Create/edit VS Code settings (`settings.json`):

**Via UI:**
1. Open VS Code
2. Go to Settings (Ctrl+, / Cmd+,)
3. Search for "github.copilot.mcp"
4. Click "Edit in settings.json"

**Via settings.json:**

```json
{
  "github.copilot.mcp.servers": {
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
```

**Alternative: Workspace Configuration**

Create `.vscode/settings.json` in your project:

```json
{
  "github.copilot.mcp.servers": {
    "enhanced-cognee": {
      "command": "python",
      "args": [
        "${workspaceFolder}/../enhanced-cognee/enhanced_cognee_mcp_server.py"
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

**Step 3: Reload VS Code**
- Press Ctrl+Shift+P (Windows/Linux) or Cmd+Shift+P (Mac)
- Type "Reload Window" and press Enter

**Step 4: Verify**
- Open GitHub Copilot Chat (Ctrl+I / Cmd+I)
- Type `@enhanced-cognee` to see available tools
- Should list all Enhanced Cognee MCP tools

**Usage with GitHub Copilot:**
```
# In Copilot Chat interface
User: @enhanced-cognee Add memory about my coding preferences
Copilot: [Uses add_memory tool] Memory added!

User: @enhanced-cognee Search for memories about testing
Copilot: [Uses search_memories tool] Found 2 memories about testing

User: @enhanced-cognee Get performance metrics
Copilot: [Uses get_performance_metrics tool]
```

**Advanced GitHub Copilot Features:**

**Combine Copilot with Enhanced Cognee:**
```
# Copilot can use Enhanced Cognee for context
User: @enhanced-cognee Remember my API endpoint structure
Copilot: [Stores in Enhanced Cognee]

# Later in coding session
User: @enhanced-cognee What do you know about my API structure?
Copilot: [Retrieves from Enhanced Cognee]
Based on your memories:
- API base URL: https://api.example.com/v2
- Authentication: Bearer token
- Rate limit: 1000 requests/minute

# Now Copilot uses this context for code generation
User: Generate API client code
Copilot: [Generates code matching your remembered structure]
```

**Note:** GitHub Copilot MCP support may require:
- GitHub Copilot Chat extension installed
- Copilot subscription (free or paid)
- Latest version of Copilot extensions

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

Once connected, Enhanced Cognee provides **30+ tools** across multiple categories:

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

### Kilo Code
```
# In Kilo Code panel
User: Add memory about my project architecture
Kilo Code: [Uses add_memory tool] Memory saved successfully!

User: What are my coding standards?
Kilo Code: [Uses search_memories tool] Based on your memories:
    - PEP 8 for Python
    - 4-space indentation
    - Type hints required
    - Docstrings for all functions
```

### GitHub Copilot
```
# In Copilot Chat (Ctrl+I / Cmd+I)
User: @enhanced-cognee Add memory about my API design
Copilot: [Uses add_memory tool] Added to memory!

User: @enhanced-cognee Search for API-related memories
Copilot: [Uses search_memories tool] Found 5 memories:
    - RESTful API design principles
    - JWT authentication
    - OpenAPI 3.0 specification
    - Error handling patterns
    - Rate limiting strategy
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
