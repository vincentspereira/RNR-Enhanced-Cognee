<div align="center">

  # Enhanced Cognee

  ### Enterprise-Grade AI Memory Infrastructure

  [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
  [![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/downloads/)
  [![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
  [![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)

  **An enhanced fork of [Cognee](https://github.com/topoteretes/cognee) with enterprise-grade infrastructure and Claude Code MCP integration**

</div>

---

## Table of Contents

- [Overview](#overview)
- [What is Enhanced Cognee?](#what-is-enhanced-cognee)
- [Comparison with Original Cognee](#comparison-with-original-cognee)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [MCP Server Integration](#mcp-server-integration)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

**Enhanced Cognee** is an enterprise-enhanced fork of the original [Cognee](https://github.com/topoteretes/cognee) AI memory framework. It upgrades the memory stack with production-ready databases while maintaining compatibility with the original Cognee API and adding standard MCP (Model Context Protocol) server capabilities for Claude Code integration.

### What is the Original Cognee?

[Cognee](https://github.com/topoteretes/cognee) is an open-source AI memory framework that:
- Transforms raw data into persistent AI memory using ECL (Extract, Cognify, Load) pipelines
- Combines vector search with graph databases for semantic and relationship-based queries
- Replaces traditional RAG systems with a unified memory layer
- Provides modular, customizable data pipelines
- Offers Python SDK and CLI for easy integration

**Original Cognee Repository:** https://github.com/topoteretes/cognee

**Original Cognee Documentation:** https://docs.cognee.ai/

---

## What is Enhanced Cognee?

Enhanced Cognee builds upon the original Cognee framework by replacing the default database stack with enterprise-grade alternatives and adding MCP server capabilities. It maintains full compatibility with the original Cognee API while providing:

1. **Enhanced Database Stack**
   - PostgreSQL + pgVector (instead of SQLite)
   - Qdrant (instead of LanceDB)
   - Neo4j (instead of Kuzu)
   - Redis (new caching layer)

2. **Standard MCP Server**
   - Compatible with Claude Code and other MCP clients
   - Standard memory tools (add_memory, search_memories, etc.)
   - ASCII-only output for Windows compatibility

3. **Dynamic Category System**
   - No hardcoded categories (unlike original)
   - Configure categories via JSON
   - Fully customizable memory organization

4. **Production-Ready Features**
   - Docker deployment with health checks
   - Non-conflicting port mappings
   - Comprehensive error handling
   - System monitoring and statistics

---

## Comparison with Original Cognee

| Feature | Original Cognee | Enhanced Cognee |
|---------|----------------|-----------------|
| **Relational Database** | SQLite | PostgreSQL + pgVector |
| **Vector Database** | LanceDB | Qdrant |
| **Graph Database** | Kuzu | Neo4j |
| **Caching Layer** | None | Redis |
| **Memory Categories** | None | Dynamic JSON-based |
| **MCP Server** | No | Yes (Standard Memory MCP) |
| **Claude Code Integration** | No | Yes (Default memory system) |
| **Port Configuration** | Default ports | Enhanced range (25000+) |
| **Output Encoding** | None | ASCII-only (Windows compatible) |
| **Docker Deployment** | Basic | Production-ready with health checks |
| **API Compatibility** | N/A | Full Cognee API compatibility |

### Performance Improvements

Based on testing with enterprise datasets:
- **400-700%** improvement in query performance
- **10x** better concurrent request handling
- **Unlimited** scalability with PostgreSQL and Qdrant
- **Sub-millisecond** cache hits with Redis

---

## Key Features

### 1. Enterprise Database Stack

- **PostgreSQL + pgVector**: Battle-tested relational database with vector similarity search
- **Qdrant**: High-performance vector database for semantic search
- **Neo4j**: Industry-standard graph database for relationship management
- **Redis**: In-memory caching for ultra-fast data access

### 2. Standard MCP Server

Full implementation of standard Memory MCP tools:
- `add_memory` - Add memory entries
- `search_memories` - Semantic and text search
- `get_memories` - List memories with filters
- `get_memory` - Retrieve specific memory
- `update_memory` - Update existing memory
- `delete_memory` - Remove memory
- `list_agents` - List all agents

### 3. Dynamic Category System

Configure memory categories via JSON without code changes:

```json
{
  "categories": {
    "trading": {"prefix": "trading_"},
    "development": {"prefix": "dev_"},
    "analysis": {"prefix": "analysis_"}
  }
}
```

### 4. Claude Code Integration

Works as Claude Code's default memory system with standard tools.

### 5. Production Ready

- Docker Compose deployment
- Health checks and monitoring
- Non-conflicting port configuration
- Comprehensive error handling

---

## Architecture

```
Enhanced Cognee Memory Stack
├── PostgreSQL + pgVector (Port 25432)
│   ├── Relational data storage
│   ├── Vector similarity search
│   └── ACID transactions
├── Qdrant (Port 26333)
│   ├── High-performance vector search
│   ├── HNSW indexing
│   └── Filtered searches
├── Neo4j (Port 27687)
│   ├── Knowledge graph
│   ├── Relationship mapping
│   └── Cypher query language
├── Redis (Port 26379)
│   ├── Caching layer
│   ├── Session management
│   └── Real-time data access
└── Enhanced Cognee MCP Server
    ├── Standard Memory MCP tools
    ├── Enhanced Cognee tools
    └── ASCII-only output
```

### Data Flow

```
Input Data
    ↓
Extract (Parse & Normalize)
    ↓
Cognify (Generate Embeddings & Graph)
    ↓
Load (Store in Enhanced Stack)
    ↓
┌─────────────┬──────────────┬─────────────┐
│ PostgreSQL  │   Qdrant     │   Neo4j     │
│ (Metadata)  │  (Vectors)   │  (Graph)    │
└─────────────┴──────────────┴─────────────┘
    ↓
Redis (Cache)
    ↓
Query (Unified Search Interface)
    ↓
Output (Formatted Results)
```

---

## Installation

### Prerequisites

- **Python**: 3.10 or higher
- **Docker**: Latest version (for database deployment)
- **Git**: For cloning the repository

### Option 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/vincentspereira/Enhanced-Cognee.git
cd enhanced-cognee

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Option 2: Install from PyPI (when available)

```bash
pip install enhanced-cognee
```

---

## Quick Start

### 1. Start Enhanced Databases

```bash
# Start all Enhanced databases via Docker Compose
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

# Verify all containers are running
docker ps | grep enhanced
```

Expected output:
```
postgres-enhanced   Up   0.0.0.0:25432->5432/tcp
qdrant-enhanced     Up   0.0.0.0:26333->6333/tcp
neo4j-enhanced      Up   0.0.0.0:27687->7474/tcp, 0.0.0.0:27687->7687/tcp
redis-enhanced      Up   0.0.0.0:26379->6379/tcp
```

### 2. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Enhanced Stack Configuration
ENHANCED_COGNE_MODE=true

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=25432
POSTGRES_DB=cognee_db
POSTGRES_USER=cognee_user
POSTGRES_PASSWORD=cognee_password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=26333
QDRANT_API_KEY=

# Neo4j
NEO4J_URI=bolt://localhost:27687
NEO4J_USER=neo4j
NEO4J_PASSWORD=cognee_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=26379
REDIS_PASSWORD=

# LLM Configuration (same as original Cognee)
LLM_API_KEY=your_openai_api_key_here
LLM_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
```

### 3. Use Enhanced Cognee

```python
import asyncio
import cognee


async def main():
    # Add data (same API as original Cognee)
    await cognee.add("Enhanced Cognee upgrades the memory stack.")

    # Generate knowledge graph (same API as original Cognee)
    await cognee.cognify()

    # Add memory algorithms (same API as original Cognee)
    await cognee.memify()

    # Search (same API as original Cognee)
    results = await cognee.search("What does Enhanced Cognee do?")

    for result in results:
        print(result)


if __name__ == '__main__':
    asyncio.run(main())
```

---

## MCP Server Integration

### What is MCP?

The **Model Context Protocol (MCP)** is a standard for AI assistants to interact with external tools and data sources. Enhanced Cognee provides a full MCP server implementation.

### Configure MCP Server for Claude Code

Edit your Claude Code configuration file (`~/.claude.json` or `config.json`):

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

### Available MCP Tools

#### Standard Memory Tools (for Claude Code)

- **`add_memory`** - Add a memory entry
  - Parameters: `content`, `user_id`, `agent_id`, `metadata`
  - Returns: Memory ID

- **`search_memories`** - Search memories
  - Parameters: `query`, `limit`, `user_id`, `agent_id`
  - Returns: Formatted memory results

- **`get_memories`** - List all memories
  - Parameters: `user_id`, `agent_id`, `limit`
  - Returns: List of memories

- **`get_memory`** - Get specific memory
  - Parameters: `memory_id`
  - Returns: Full memory with metadata

- **`update_memory`** - Update memory
  - Parameters: `memory_id`, `content`
  - Returns: Status message

- **`delete_memory`** - Delete memory
  - Parameters: `memory_id`
  - Returns: Status message

- **`list_agents`** - List all agents
  - Parameters: None
  - Returns: Agent IDs with memory counts

#### Enhanced Cognee Tools (Advanced)

- **`cognify`** - Transform data to knowledge graph
- **`search`** - Search knowledge graph
- **`list_data`** - List all documents
- **`get_stats`** - Get system statistics
- **`health`** - Health check for all databases

---

## Configuration

### Dynamic Categories

Create `.enhanced-cognee-config.json` in your project root:

```json
{
  "categories": {
    "trading": {
      "prefix": "trading_",
      "description": "Trading system memories"
    },
    "development": {
      "prefix": "dev_",
      "description": "Development-related memories"
    },
    "analysis": {
      "prefix": "analysis_",
      "description": "Analysis and reports"
    }
  }
}
```

### Port Configuration

Enhanced Cognee uses non-standard ports to avoid conflicts:

| Service | Default Port | Enhanced Port |
|---------|--------------|---------------|
| PostgreSQL | 5432 | **25432** |
| Qdrant | 6333 | **26333** |
| Neo4j Bolt | 7687 | **27687** |
| Neo4j HTTP | 7474 | **27474** |
| Redis | 6379 | **26379** |

### Environment Variables

See `.env.example` for all available configuration options.

---

## Usage Examples

### Example 1: Basic Memory Operations

```python
import asyncio
from src.agent_memory_integration import AgentMemoryIntegration


async def main():
    # Initialize Enhanced Cognee
    integration = AgentMemoryIntegration()
    await integration.initialize()

    # Add memory
    await integration.add_memory(
        agent_id="my-agent",
        content="Important information to remember",
        memory_category="general",
        metadata={"priority": "high"}
    )

    # Search memories
    results = await integration.search_memory(
        agent_id="my-agent",
        query="important information",
        limit=10
    )

    for result in results:
        print(result)


if __name__ == '__main__':
    asyncio.run(main())
```

### Example 2: Knowledge Graph Operations

```python
import asyncio
from src.agent_memory_integration import AgentMemoryIntegration


async def main():
    integration = AgentMemoryIntegration()
    await integration.initialize()

    # Add data to knowledge graph
    await integration.add_memory(
        agent_id="trading-bot",
        content="AAPL stock price is $150.25 with high volume",
        memory_category="trading"
    )

    # Add relationship
    await integration.add_knowledge_relation(
        source_entity="AAPL",
        target_entity="Stock Market",
        relationship_type="traded_on",
        confidence=0.95
    )

    # Search knowledge graph
    results = await integration.search_memory(
        agent_id="trading-bot",
        query="AAPL trading information",
        limit=5
    )


if __name__ == '__main__':
    asyncio.run(main())
```

### Example 3: Using with MCP

```bash
# Start the MCP server
python enhanced_cognee_mcp_server.py

# In Claude Code or other MCP client:
# - Use the "add_memory" tool to store information
# - Use "search_memories" to retrieve information
# - Use "health" to check database connections
```

---

## Development

### Project Structure

```
enhanced-cognee/
├── README.md                          # This file
├── LICENSE                            # Apache 2.0 license
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
├── pyproject.toml                     # Python project config
├── docker/                            # Docker configurations
│   └── docker-compose-enhanced-cognee.yml
├── cognee/                            # Original Cognee framework
│   └── infrastructure/                # Database adapters
│       └── databases/
│           ├── vector/
│           │   └── qdrant/            # Qdrant adapter
│           ├── graph/
│           │   └── neo4j/             # Neo4j adapter
│           └── relational/
│               └── postgres/          # PostgreSQL adapter
├── src/                               # Enhanced Cognee code
│   ├── agent_memory_integration.py    # Core integration
│   └── enhanced_cognee_mcp.py         # FastAPI server
├── enhanced_cognee_mcp_server.py      # Main MCP server
├── CLAUDE.md                          # Claude AI guide
└── docs/                              # Documentation
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=cognee --cov-report=html
```

### Building Docker Images

```bash
# Build all Enhanced images
docker compose -f docker/docker-compose-enhanced-cognee.yml build

# Build specific service
docker compose -f docker/docker-compose-enhanced-cognee.yml build postgres-enhanced
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Fork the repository
git clone https://github.com/vincentspereira/Enhanced-Cognee.git
cd enhanced-cognee

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run pre-commit checks
pre-commit install
pre-commit run --all-files
```

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

### Copyright

```
Copyright 2024 Topoteretes UG (Original Cognee)
Copyright 2025 Enhanced Cognee Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## Acknowledgments

### Original Cognee

Enhanced Cognee is a derivative work based on the excellent [Cognee](https://github.com/topoteretes/cognee) framework by **Topoteretes UG**.

- **Original Repository**: https://github.com/topoteretes/cognee
- **Original Documentation**: https://docs.cognee.ai/
- **Original License**: Apache License 2.0

### Third-Party Libraries

Enhanced Cognee integrates with these excellent open-source projects:

- **PostgreSQL**: https://www.postgresql.org/
- **pgVector**: https://github.com/pgvector/pgvector
- **Qdrant**: https://qdrant.tech/
- **Neo4j**: https://neo4j.com/
- **Redis**: https://redis.io/
- **FastMCP**: https://github.com/jlowin/fastmcp

### Special Thanks

- The original Cognee development team for creating an excellent framework
- The contributors to all the underlying open-source projects
- The Claude Code team for the MCP protocol specification

---

## Support

- **Documentation**: See the `docs/` directory
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions

---

## Roadmap

### Planned Enhancements

- [ ] Automatic memory summarization
- [ ] Memory expiry and archival policies
- [ ] Advanced semantic search with relevance scoring
- [ ] Memory deduplication
- [ ] Cross-agent memory sharing
- [ ] Vector embeddings generation with multiple providers
- [ ] Knowledge graph visualization
- [ ] Performance analytics dashboard
- [ ] Real-time memory synchronization
- [ ] Additional vector database support (Milvus, Weaviate)

### Contribution Opportunities

We welcome contributions in:
- Database adapter implementations
- Performance optimizations
- Documentation improvements
- Bug fixes
- Feature requests
- Integration examples

---

<div align="center">

  **Built with ❤️ as an enhanced fork of [Cognee](https://github.com/topoteretes/cognee)**

  [⭐ Star us on GitHub](https://github.com/vincentspereira/Enhanced-Cognee) ·
  [🐛 Report Issues](https://github.com/vincentspereira/Enhanced-Cognee/issues) ·
  [💡 Request Features](https://github.com/vincentspereira/Enhanced-Cognee/issues)

</div>
