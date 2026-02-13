# Enhanced Cognee MCP Tools - Complete Documentation

**Total Tools:** 59
**Last Updated:** 2026-02-09
**Status:** All tools fully operational with Enhanced Stack

---

## Tool Categories

### [A] Core Memory Operations (Standard Claude Code Memory Interface)
These are the standard memory tools that Claude Code uses as its default memory system.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 1 | `add_memory` | Add a memory entry to Enhanced Cognee | Manual (M) |
| 2 | `search_memories` | Search memories using semantic + text search | Manual (M) |
| 3 | `get_memories` | List all memories with optional filters | Manual (M) |
| 4 | `get_memory` | Get specific memory by ID | Manual (M) |
| 5 | `update_memory` | Update existing memory content | Manual (M) |
| 6 | `delete_memory` | Delete a memory by ID | Manual (M) |
| 7 | `list_agents` | List all agents with memory counts | Manual (M) |

### [B] Enhanced Cognee Core Tools
Core tools for interacting with the Enhanced Cognee knowledge graph.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 8 | `cognify` | Transform data into knowledge graph | Manual (M) |
| 9 | `search` | Search the knowledge graph | Manual (M) |
| 10 | `get_stats` | Get Enhanced Cognee statistics | Manual (M) |
| 11 | `health` | Health check for all databases | Manual (M) |
| 12 | `list_data` | List all documents in knowledge graph | Manual (M) |

### [C] Memory Management (TTL & Expiration)
Advanced memory lifecycle management.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 13 | `expire_memories` | Manually expire memories matching criteria | Manual (M) |
| 14 | `get_memory_age_stats` | Get statistics about memory age distribution | Manual (M) |
| 15 | `set_memory_ttl` | Set time-to-live for specific memory or category | Manual (M) |

### [D] Memory Deduplication
Automatic and manual duplicate detection and resolution.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 16 | `check_duplicate` | Check if a memory is a duplicate | Manual (M) |
| 17 | `auto_deduplicate` | Automatically deduplicate memories | Auto (A) |
| 18 | `get_deduplication_stats` | Get deduplication statistics | Manual (M) |
| 19 | `deduplicate` | Manual deduplication of memories | Manual (M) |
| 20 | `schedule_deduplication` | Schedule automatic deduplication task | System (S) |
| 21 | `deduplication_report` | Generate deduplication report | Manual (M) |

### [E] Memory Summarization
AI-powered memory summarization for efficient storage.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 22 | `summarize_old_memories` | Summarize memories older than threshold | Manual (M) |
| 23 | `summarize_category` | Summarize all memories in a category | Manual (M) |
| 24 | `get_summary_stats` | Get summarization statistics | Manual (M) |
| 25 | `schedule_summarization` | Schedule automatic summarization task | System (S) |
| 26 | `summary_stats` | Get summary statistics (alias) | Manual (M) |

### [F] Performance Analytics
Monitor and optimize memory system performance.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 27 | `get_performance_metrics` | Get system performance metrics | Manual (M) |
| 28 | `get_slow_queries` | Get slow performing queries | Manual (M) |
| 29 | `get_prometheus_metrics` | Get Prometheus-compatible metrics | Manual (M) |

### [G] Cross-Agent Memory Sharing
Share memories between different agents.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 30 | `set_memory_sharing` | Configure memory sharing policy | Manual (M) |
| 31 | `check_memory_access` | Check if agent can access memory | Manual (M) |
| 32 | `get_shared_memories` | Get memories shared to/from agent | Manual (M) |
| 33 | `create_shared_space` | Create shared memory space | Manual (M) |

### [H] Real-Time Synchronization
Real-time memory synchronization across agents.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 34 | `publish_memory_event` | Publish memory event to Redis pub/sub | Auto (A) |
| 35 | `get_sync_status` | Get synchronization status | Manual (M) |
| 36 | `sync_agent_state` | Sync agent state across instances | Auto (A) |

### [I] Backup & Restore
Complete backup and restore functionality.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 37 | `create_backup` | Create full system backup | Manual (M) |
| 38 | `restore_backup` | Restore from backup | Manual (M) |
| 39 | `list_backups` | List all available backups | Manual (M) |
| 40 | `verify_backup` | Verify backup integrity | Manual (M) |
| 41 | `rollback_restore` | Rollback to previous state | Manual (M) |

### [J] Archive Management
Archive old memories for long-term storage.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 42 | `archive_category` | Archive all memories in a category | Manual (M) |

### [K] Task Scheduling
Schedule and manage background tasks.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 43 | `schedule_task` | Schedule a background task | System (S) |
| 44 | `list_tasks` | List all scheduled tasks | Manual (M) |
| 45 | `cancel_task` | Cancel a scheduled task | Manual (M) |

### [L] Multi-Language Support (Sprint 9)
Detect and search memories in multiple languages.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 46 | `detect_language` | Detect language of text | Manual (M) |
| 47 | `get_supported_languages` | Get list of supported languages | Manual (M) |
| 48 | `search_by_language` | Search memories by language | Manual (M) |
| 49 | `get_language_distribution` | Get memory distribution by language | Manual (M) |
| 50 | `cross_language_search` | Search across multiple languages | Manual (M) |

### [M] Advanced AI Features (Sprint 10)
Intelligent summarization and advanced search.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 51 | `intelligent_summarize` | AI-powered intelligent summarization | Auto (A) |
| 52 | `auto_summarize_old_memories` | Auto-summarize old memories | Auto (A) |
| 53 | `cluster_memories` | Cluster similar memories | Auto (A) |
| 54 | `advanced_search` | Advanced search with re-ranking | Manual (M) |
| 55 | `expand_search_query` | Expand search query with synonyms | Auto (A) |
| 56 | `get_search_analytics` | Get search analytics | Manual (M) |
| 57 | `get_search_facets` | Get search facets for filtering | Manual (M) |
| 58 | `get_summarization_stats` | Get detailed summarization statistics | Manual (M) |

### [N] System Operations (Internal)
System-level operations automatically triggered.

| # | Tool Name | Description | Operation Type |
|---|-----------|-------------|----------------|
| 59 | `get_memory_age_stats` | Internal: Get memory age for auto-tasks | System (S) |

---

## Operation Type Legend

- **Manual (M)**: Tools that users/agents call directly
- **Auto (A)**: Tools automatically triggered by the system
- **System (S)**: Tools for system-level operations and scheduling

---

## Tool Categories by Operation Type

### Manual Tools (42 tools)
These are tools that users, Claude Code, or agents call directly to perform operations:

**Core Memory (7):** add_memory, search_memories, get_memories, get_memory, update_memory, delete_memory, list_agents

**Enhanced Cognee (5):** cognify, search, get_stats, health, list_data

**Memory Management (3):** expire_memories, get_memory_age_stats, set_memory_ttl

**Deduplication (4):** check_duplicate, auto_deduplicate, get_deduplication_stats, deduplication_report

**Summarization (4):** summarize_old_memories, summarize_category, get_summary_stats, summary_stats

**Performance (3):** get_performance_metrics, get_slow_queries, get_prometheus_metrics

**Cross-Agent (4):** set_memory_sharing, check_memory_access, get_shared_memories, create_shared_space

**Real-Time Sync (1):** get_sync_status

**Backup (5):** create_backup, restore_backup, list_backups, verify_backup, rollback_restore

**Archive (1):** archive_category

**Tasks (2):** list_tasks, cancel_task

**Multi-Language (5):** detect_language, get_supported_languages, search_by_language, get_language_distribution, cross_language_search

**Advanced AI (6):** advanced_search, get_search_analytics, get_search_facets, get_summarization_stats, intelligent_summarize, get_search_facets

### Auto Tools (9 tools)
These tools are automatically triggered by the system:

**Deduplication:** deduplicate (auto-run on schedule)

**Real-Time Sync:** publish_memory_event, sync_agent_state

**Advanced AI:** intelligent_summarize, auto_summarize_old_memories, cluster_memories, expand_search_query

### System Tools (8 tools)
These tools manage system-level operations and scheduling:

**Tasks:** schedule_task, schedule_deduplication, schedule_summarization

**Internal:** get_memory_age_stats (for auto-expiry), deduplicate (scheduled runs)

---

## Usage Examples

### Adding a Memory (Standard Claude Code Memory)
```
Tool: add_memory
Parameters:
  - content: "Important information to remember"
  - agent_id: "my-agent"
  - metadata: '{"category": "trading", "priority": "high"}'
```

### Searching Memories
```
Tool: search_memories
Parameters:
  - query: "risk management strategies"
  - limit: 10
  - agent_id: "trading-bot"
```

### Checking System Health
```
Tool: health
Returns:
  Enhanced Cognee Health:
  OK PostgreSQL
  OK Qdrant
  OK Neo4j
  OK Redis
```

### Getting Statistics
```
Tool: get_stats
Returns:
  {
    "status": "Enhanced Cognee MCP Server",
    "databases": {
      "postgresql": "OK Connected (42 documents)",
      "qdrant": "OK Connected (5 collections)",
      "neo4j": "OK Connected",
      "redis": "OK Connected"
    }
  }
```

---

## Configuration

All 59 tools are now available through the Enhanced Cognee MCP Server at:

**Server Path:** `C:/Users/vince/Projects/AI Agents/enhanced-cognee/bin/enhanced_cognee_mcp_server.py`

**Configuration:** `~/.claude.json` (User Scope - Global)

**Environment Variables:** `C:/Users/vince/Projects/AI Agents/enhanced-cognee/.env`

**Enhanced Stack Status:**
- PostgreSQL: Port 25432 (OK)
- Qdrant: Port 26333 (OK)
- Neo4j: Port 27687 (OK)
- Redis: Port 26379 (OK)

---

## Integration with Claude Code

The Enhanced Cognee MCP Server provides:

1. **Standard Memory Interface**: Compatible with Claude Code's memory system
2. **59 MCP Tools**: Complete memory management and operations
3. **ASCII-Only Output**: No Unicode encoding issues on Windows
4. **Dynamic Categories**: No hardcoded ATS/OMA/SMC restrictions
5. **Global User Scope**: Available to all projects

---

**Document Status:** Complete - All 59 tools documented with categories and operation types.
