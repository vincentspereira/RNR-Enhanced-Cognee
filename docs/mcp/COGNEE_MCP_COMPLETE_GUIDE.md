# Cognee MCP Server - Complete Setup Guide

## Overview

Cognee is now successfully configured as your **primary memory MCP server** with advanced knowledge graph capabilities and automatic fallback from Z.ai to Ollama.

## 📁 File Locations

### Core Configuration Files
- **Wrapper Script**: `C:\Users\Vincent_Pereira\cognee\cognee_mcp_wrapper.py`
- **Environment File**: `C:\Users\Vincent_Pereira\cognee\.env`
- **Cognee Library**: `C:\Users\Vincent_Pereira\cognee\cognee-mcp\src\server.py`

### MCP Configuration
- **Global MCP Config**: `C:\Users\Vincent_Pereira\.claude.json` (lines 273-280)

## 🔧 Current Configuration

### Primary LLM (Z.ai)
```bash
LLM_API_KEY="REDACTED"
LLM_MODEL="zhipu/glm-5"
LLM_PROVIDER="zai"
LLM_ENDPOINT="https://api.z.ai/api/coding/paas/v4/"
```

### Fallback LLM (Ollama)
```bash
LLM_API_KEY="ollama"
LLM_MODEL="glm-4.7-flash:q4_K_M"
LLM_PROVIDER="ollama"
LLM_ENDPOINT="http://localhost:11434/v1"
```

### Embeddings (Ollama)
```bash
EMBEDDING_PROVIDER="ollama"
EMBEDDING_MODEL="qwen3-embedding:4b-q4_K_M"
EMBEDDING_ENDPOINT="http://localhost:11434/api/embed"
EMBEDDING_DIMENSIONS=2560
```

## 🛠️ Available Tools

| Tool | Function | Description |
|------|----------|-------------|
| `cognify` | Knowledge Graph Creation | Convert data to knowledge graphs |
| `search` | Semantic Search | Query memory with multiple completion types |
| `list_data` | Data Management | List datasets and data items |
| `delete` | Memory Management | Remove data (soft/hard mode) |
| `prune` | Reset System | Reset all data |
| `codify` | Code Analysis | Analyze code repositories |

## 🔄 Automatic Fallback Logic

1. **Z.ai (Primary)**: Uses GLM-4.6 model
2. **Ollama (Fallback)**: Automatically switches when Z.ai fails
3. **Embeddings**: Always uses Ollama (qwen3-embedding:4b-q4_K_M)

## 🚀 Server Status

**✅ Connected**: `cognee-primary` is active and ready for use

## 📊 Priority Order in Your Memory Stack

1. **cognee-primary** (Advanced knowledge graphs - NEW)
2. enhanced-memory (Custom entity relationships)
3. mem0 (Vector-based memory)
4. memory (Basic file-based memory)

## 🔑 API Key Management

### Update Z.ai API Key
1. Edit `C:\Users\Vincent_Pereira\cognee\.env` line 5
2. Edit `C:\Users\Vincent_Pereira\cognee\cognee_mcp_wrapper.py` line 18
3. Restart MCP server:
   ```bash
   claude mcp remove cognee-primary
   claude mcp add cognee-primary python "C:/Users/Vincent_Pereira/cognee/cognee_mcp_wrapper.py"
   ```

## 🎯 How Cognee Works

### Auto-Invocation
Claude will automatically use Cognee for:
- Memory-related tasks
- Knowledge graph operations
- Semantic search requests
- Code repository analysis

### Smart Memory Features
- **Knowledge Graphs**: Creates semantic relationships between concepts
- **Multi-Modal Support**: Handles text, code, documents, structured data
- **Persistent Memory**: Maintains context across sessions
- **Advanced Search**: Multiple completion types (GRAPH_COMPLETION, RAG_COMPLETION)

## 🛠️ Troubleshooting

### Server Not Connecting
```bash
# Check server status
claude mcp list

# Restart server
claude mcp remove cognee-primary
claude mcp add cognee-primary python "C:/Users/Vincent_Pereira/cognee/cognee_mcp_wrapper.py"
```

### API Key Issues
- Verify Z.ai API key validity
- Check Ollama is running: `ollama list`
- Verify model availability: `ollama show gpt-oss:20b`

### Memory Issues
- Check database permissions
- Verify Ollama embedding model: `ollama show snowflake-arctic-embed2:568m`

## 📈 Performance Notes

- **Z.ai Response**: Fast, cloud-based inference
- **Ollama Response**: Local, slightly slower but reliable
- **Memory Storage**: Local SQLite/LanceDB/Kuzu (no cloud dependencies)
- **Knowledge Graphs**: Advanced semantic relationships maintained locally

---

**Last Updated**: 2025-11-06
**Status**: ✅ Fully Operational with Z.ai + Ollama Fallback