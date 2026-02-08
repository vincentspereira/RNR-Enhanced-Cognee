# Enhanced Cognee - Lite Mode Guide

Complete guide to using Enhanced Cognee in Lite Mode with SQLite-only backend.

## Overview

Lite Mode provides a simplified, lightweight version of Enhanced Cognee that requires only SQLite database. This is ideal for:
- Development and testing
- Small-scale deployments
- Resource-constrained environments
- Quick prototyping

## Lite Mode vs Full Mode

| Feature | Lite Mode | Full Mode |
|---------|-----------|-----------|
| Databases | SQLite only | PostgreSQL + Qdrant + Neo4j + Redis |
| Vector Search | Built-in | Qdrant (high-performance) |
| Graph Storage | Built-in | Neo4j (enterprise) |
| Caching | Built-in | Redis (distributed) |
| Resources | Low | Medium-High |
| Setup Time | 2 minutes | 10-15 minutes |
| Performance | Good | Excellent |

## Installation

### Quick Install

```bash
# Clone repository
git clone https://github.com/your-org/enhanced-cognee.git
cd enhanced-cognee

# Run installation script (Linux/Mac)
./install.sh --lite

# Or (Windows)
./install.ps1 -LiteMode
```

### Manual Install

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize Lite Mode
python -c "
from src.lite_mode.sqlite_manager import SQLiteManager
db = SQLiteManager('lite_cognee.db')
print('OK Lite Mode initialized')
"
```

## Usage

### Starting Lite Mode MCP Server

```bash
# Set environment variable
export ENHANCED_COGNEE_MODE=lite

# Start server
python src/lite_mode/lite_mcp_server.py
```

### Using Lite Mode Memory Tools

```python
from src.lite_mode.sqlite_manager import SQLiteManager

# Initialize database
db = SQLiteManager('lite_cognee.db')

# Add memory
memory_id = db.add_document(
    data_text="Important information to remember",
    data_type="memory",
    metadata={"category": "general"}
)

# Search memories
results = db.search_documents("important", limit=10)

# Get memory
memory = db.get_document(memory_id)
```

## Lite Mode Features

### 1. SQLite Database Manager

- Document storage with metadata
- Full-text search
- Vector similarity search (built-in)
- Automatic indexing

### 2. Essential MCP Tools (10 Tools)

Lite Mode MCP server includes these essential tools:

1. **add_memory** - Add memory entry
2. **search_memories** - Search memories
3. **get_memories** - List all memories
4. **get_memory** - Get specific memory by ID
5. **update_memory** - Update existing memory
6. **delete_memory** - Delete memory
7. **list_agents** - List all agents
8. **cognify** - Add data to knowledge graph
9. **search** - Search knowledge graph
10. **health** - Health check

### 3. Built-in Vector Search

Lite Mode includes built-in vector similarity search using SQLite FTS5:

```python
# Semantic search
results = db.vector_search(
    query_vector=[0.1, 0.2, ...],
    limit=10,
    threshold=0.7
)
```

### 4. Built-in Graph Storage

Lite Mode includes built-in graph storage using SQLite:

```python
# Create graph relationship
db.add_edge(
    source_id="memory1",
    target_id="memory2",
    edge_type="related_to"
)
```

## Configuration

### Environment Variables

```bash
# Lite Mode
ENHANCED_COGNEE_MODE=lite

# Database path
LITE_DB_PATH=./lite_cognee.db

# Optional: Custom configuration
LITE_CONFIG_PATH=./lite_config.json
```

### Configuration File

Create `lite_config.json`:

```json
{
  "database_path": "lite_cognee.db",
  "vector_dimensions": 1536,
  "max_memories": 100000,
  "enable_graph": true,
  "enable_caching": true
}
```

## Migration to Full Mode

When ready to upgrade to Full Mode:

```bash
# Export Lite Mode data
python -c "
from src.lite_mode.sqlite_manager import SQLiteManager
db = SQLiteManager('lite_cognee.db')
db.export_to_json('lite_export.json')
"

# Install Full Mode
./install.sh --full

# Import data to Full Mode
python scripts/migrate_to_full.py --source lite_export.json
```

## Performance Optimization

### Indexing

Lite Mode automatically creates indexes:

```sql
-- Full-text search index
CREATE VIRTUAL TABLE documents_fts USING fts5(content);

-- Vector similarity index (custom implementation)
-- Automatically created on first vector search
```

### Caching

Enable built-in caching:

```python
db = SQLiteManager('lite_cognee.db', cache_size=1000)
```

### Connection Pooling

```python
db = SQLiteManager('lite_cognee.db', pool_size=5)
```

## Troubleshooting

### Database Locked

```bash
# Check for open connections
lsof lite_cognee.db

# Close all connections and retry
```

### Slow Search Performance

```bash
# Rebuild indexes
python -c "
from src.lite_mode.sqlite_manager import SQLiteManager
db = SQLiteManager('lite_cognee.db')
db.rebuild_indexes()
"
```

### Migration Issues

```bash
# Validate export before migration
python scripts/validate_lite_export.py lite_export.json
```

## Best Practices

1. **Regular Backups**: Backup `lite_cognee.db` regularly
2. **Monitor Database Size**: Keep database under 10GB for optimal performance
3. **Use Transactions**: Batch operations in transactions
4. **Optimize Queries**: Use specific queries instead of broad searches
5. **Plan Migration**: Consider migration path when designing system

## Limitations

Lite Mode has these limitations compared to Full Mode:

- **Scalability**: Single-node only (no distributed architecture)
- **Performance**: Slower vector search on large datasets
- **Concurrent Writes**: Limited concurrent write support
- **Advanced Features**: No distributed caching, no graph queries

## Next Steps

- Read [Full Mode Guide](../README.md) for upgrade path
- Check [Backup & Restore Guide](BACKUP_RESTORE_GUIDE.md)
- Review [Maintenance Scheduling](MAINTENANCE_SCHEDULING.md)

---

**Lite Mode** - Lightweight Enhanced Cognee for development and small-scale deployments.
