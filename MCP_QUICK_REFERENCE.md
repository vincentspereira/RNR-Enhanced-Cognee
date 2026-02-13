# Enhanced Cognee MCP - Quick Reference Guide

**Top 20 Most Commonly Used Tools**

---

## Core Memory Operations (Claude Code Standard Memory)

### 1. add_memory
**Purpose:** Add a new memory entry
**Usage:**
```python
add_memory(
    content="Important information to remember",
    agent_id="my-agent",
    metadata='{"category": "trading", "priority": "high"}'
)
```

### 2. search_memories
**Purpose:** Search memories (semantic + text)
**Usage:**
```python
search_memories(
    query="risk management strategies",
    limit=10,
    agent_id="trading-bot"
)
```

### 3. get_memories
**Purpose:** List all memories with filters
**Usage:**
```python
get_memories(
    agent_id="my-agent",
    limit=50
)
```

### 4. get_memory
**Purpose:** Get specific memory by ID
**Usage:**
```python
get_memory(memory_id="uuid-here")
```

### 5. update_memory
**Purpose:** Update existing memory
**Usage:**
```python
update_memory(
    memory_id="uuid-here",
    content="Updated content"
)
```

### 6. delete_memory
**Purpose:** Delete a memory
**Usage:**
```python
delete_memory(memory_id="uuid-here")
```

### 7. list_agents
**Purpose:** List all agents with memory counts
**Usage:**
```python
list_agents()
```

---

## Enhanced Cognee Core Tools

### 8. cognify
**Purpose:** Transform data into knowledge graph
**Usage:**
```python
cognify(data="Text data to process and add to knowledge graph")
```

### 9. search
**Purpose:** Search knowledge graph
**Usage:**
```python
search(query="semantic search query", limit=10)
```

### 10. health
**Purpose:** Check system health
**Usage:**
```python
health()
# Returns:
# Enhanced Cognee Health:
# OK PostgreSQL
# OK Qdrant
# OK Neo4j
# OK Redis
```

### 11. get_stats
**Purpose:** Get system statistics
**Usage:**
```python
get_stats()
# Returns JSON with database status and document counts
```

### 12. list_data
**Purpose:** List all documents
**Usage:**
```python
list_data()
```

---

## Memory Management

### 13. set_memory_ttl
**Purpose:** Set time-to-live for memories
**Usage:**
```python
set_memory_ttl(
    category="trading",
    ttl_days=30
)
```

### 14. archive_category
**Purpose:** Archive old memories
**Usage:**
```python
archive_category(
    category="trading",
    older_than_days=90
)
```

### 15. expire_memories
**Purpose:** Manually expire memories
**Usage:**
```python
expire_memories(
    category="trading",
    older_than_days=30
)
```

---

## Deduplication

### 16. check_duplicate
**Purpose:** Check if memory is duplicate
**Usage:**
```python
check_duplicate(content="Potential duplicate content")
```

### 17. auto_deduplicate
**Purpose:** Auto-deduplicate memories
**Usage:**
```python
auto_deduplicate(
    agent_id="my-agent",
    similarity_threshold=0.85
)
```

### 18. get_deduplication_stats
**Purpose:** Get deduplication statistics
**Usage:**
```python
get_deduplication_stats()
```

---

## Summarization

### 19. summarize_old_memories
**Purpose:** Summarize old memories
**Usage:**
```python
summarize_old_memories(
    agent_id="my-agent",
    older_than_days=60
)
```

### 20. intelligent_summarize
**Purpose:** AI-powered intelligent summarization
**Usage:**
```python
intelligent_summarize(
    memory_ids=["uuid1", "uuid2"],
    strategy="semantic"
)
```

---

## Backup & Restore

### create_backup
**Purpose:** Create full system backup
**Usage:**
```python
create_backup(description="Daily backup")
```

### restore_backup
**Purpose:** Restore from backup
**Usage:**
```python
restore_backup(backup_id="backup-uuid")
```

### list_backups
**Purpose:** List all backups
**Usage:**
```python
list_backups()
```

---

## Cross-Agent Sharing

### set_memory_sharing
**Purpose:** Configure memory sharing
**Usage:**
```python
set_memory_sharing(
    agent_id="my-agent",
    share_with=["other-agent"],
    policy="read"
)
```

### get_shared_memories
**Purpose:** Get shared memories
**Usage:**
```python
get_shared_memories(agent_id="my-agent")
```

---

## Multi-Language Support

### detect_language
**Purpose:** Detect language of text
**Usage:**
```python
detect_language(text="Text to analyze")
```

### cross_language_search
**Purpose:** Search across languages
**Usage:**
```python
cross_language_search(
    query="search in English",
    target_languages=["es", "fr", "de"]
)
```

---

## Advanced Search

### advanced_search
**Purpose:** Advanced search with re-ranking
**Usage:**
```python
advanced_search(
    query="complex search query",
    rerank_strategy="semantic",
    limit=20
)
```

### get_search_analytics
**Purpose:** Get search analytics
**Usage:**
```python
get_search_analytics(days_back=7)
```

---

## Performance Monitoring

### get_performance_metrics
**Purpose:** Get performance metrics
**Usage:**
```python
get_performance_metrics()
```

### get_slow_queries
**Purpose:** Get slow queries
**Usage:**
```python
get_slow_queries(threshold_ms=1000)
```

---

## Quick Command Summary

```
Memory Operations:
- add_memory()          → Add new memory
- search_memories()     → Search memories
- get_memories()        → List all memories
- get_memory()          → Get specific memory
- update_memory()       → Update memory
- delete_memory()       → Delete memory
- list_agents()         → List agents

System Operations:
- health()              → Check system health
- get_stats()           → Get statistics
- cognify()             → Add to knowledge graph
- search()              → Search knowledge graph

Management:
- set_memory_ttl()      → Set expiration
- archive_category()    → Archive old memories
- auto_deduplicate()    → Remove duplicates
- summarize_old_memories() → Summarize old memories

Backup:
- create_backup()       → Create backup
- restore_backup()      → Restore from backup
- list_backups()        → List backups
```

---

## Configuration Status

**MCP Server:** Configured and Running (Global User Scope)
**Path:** `C:/Users/vince/Projects/AI Agents/enhanced-cognee/bin/enhanced_cognee_mcp_server.py`
**Status:** All 59 tools accessible
**Enhanced Stack:** All databases connected (PostgreSQL, Qdrant, Neo4j, Redis)

---

For complete documentation of all 59 tools, see: `MCP_TOOLS_DOCUMENTATION.md`
