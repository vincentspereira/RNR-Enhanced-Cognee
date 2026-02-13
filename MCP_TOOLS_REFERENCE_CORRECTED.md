# Enhanced Cognee MCP Tools Reference - Corrected

**Total Tools:** 59
**Classification:** Based on README.md (lines 870-1200)

---

## Tool Classification Summary

| Type | Count | Description |
|------|-------|-------------|
| **Manual (M)** | 10 | Tools requiring explicit user invocation (destructive operations, policy settings) |
| **Auto (A)** | 16 | Tools automatically triggered by AI IDEs (Claude Code, Cursor, etc.) |
| **System (S)** | 32 | Tools automatically triggered by Enhanced Cognee (chained automation, scheduled tasks) |
| **Total** | 59 | All tools with comprehensive automation chains |

---

## Manual (M) Tools - 10 Total

These tools require explicit user invocation. They are typically destructive operations or policy settings.

| # | Tool | Purpose | Category |
|---|-------|---------|----------|
| 1 | `delete_memory` | Delete a specific memory | Standard Memory |
| 2 | `expire_memories` | Expire old memories | Memory Management |
| 3 | `set_memory_ttl` | Set time-to-live for memory | Memory Management |
| 4 | `archive_category` | Archive memories by category | Memory Management |
| 5 | `set_memory_sharing` | Set sharing policy for memory | Cross-Agent Sharing |
| 6 | `create_backup` | Create system backup | Backup & Recovery |
| 7 | `restore_backup` | Restore from backup | Backup & Recovery |
| 8 | `create_shared_space` | Create shared memory space | Cross-Agent Sharing |
| 9 | `schedule_task` | Schedule maintenance task | Scheduling |
| 10 | `cancel_task` | Cancel scheduled task | Scheduling |

**Usage Pattern:** User must explicitly trigger these tools through commands or UI actions.

---

## Auto (A) Tools - 16 Total

These tools are automatically triggered by AI IDEs (Claude Code, Cursor, Windsurf, etc.) based on user queries and context needs.

| # | Tool | Purpose | Category |
|---|-------|---------|----------|
| 1 | `add_memory` | Add memory with metadata | Standard Memory |
| 2 | `search_memories` | Semantic + text search | Standard Memory |
| 3 | `get_memories` | List all memories | Standard Memory |
| 4 | `get_memory` | Get specific memory by ID | Standard Memory |
| 5 | `update_memory` | Update existing memory | Standard Memory |
| 6 | `list_agents` | List all agents | Standard Memory |
| 7 | `cognify` | Transform data to knowledge graph | Enhanced Cognee |
| 8 | `search` | Search knowledge graph | Enhanced Cognee |
| 9 | `list_data` | List all documents | Enhanced Cognee |
| 10 | `get_stats` | Get system statistics | Enhanced Cognee |
| 11 | `health` | Health check all databases | Enhanced Cognee |
| 12 | `check_memory_access` | Check if agent can access memory | Cross-Agent Sharing |
| 13 | `get_shared_memories` | Get shared memories for agent | Cross-Agent Sharing |
| 14 | `list_backups` | List all backups | Backup & Recovery |
| 15 | `list_tasks` | List scheduled tasks | Scheduling |
| 16 | `sync_agent_state` | Sync memories between agents | Real-Time Sync |

**Usage Pattern:** AI IDE calls these automatically based on user queries. No user intervention required.

---

## System (S) Tools - 32 Total

These tools are automatically triggered by Enhanced Cognee based on events, scheduled tasks, and chained automation.

### Performance & Monitoring (5 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 1 | `get_performance_metrics` | Comprehensive performance data |
| 2 | `get_slow_queries` | Queries above threshold |
| 3 | `get_prometheus_metrics` | Prometheus export |
| 4 | `check_duplicate` | Check if content is duplicate |
| 5 | `publish_memory_event` | Publish memory update events |

### Statistics (7 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 6 | `get_memory_age_stats` | Memory age distribution |
| 7 | `get_deduplication_stats` | Deduplication statistics |
| 8 | `get_summary_stats` | Summarization stats |
| 9 | `get_summarization_stats` | Get summarization stats |
| 10 | `summary_stats` | Get summary statistics |
| 11 | `get_sync_status` | Synchronization status |
| 12 | `get_search_analytics` | Search analytics and statistics |

### Deduplication (5 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 13 | `auto_deduplicate` | Auto-find duplicates |
| 14 | `deduplicate` | Manual deduplication |
| 15 | `deduplication_report` | Get deduplication report |
| 16 | `schedule_deduplication` | Schedule auto-deduplication |

### Summarization (6 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 17 | `summarize_old_memories` | Summarize old memories |
| 18 | `summarize_category` | Summarize specific category |
| 19 | `intelligent_summarize` | LLM-powered summarization |
| 20 | `auto_summarize_old_memories` | Auto batch summarize |
| 21 | `schedule_summarization` | Schedule auto-summarization |

### Backup & Recovery (2 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 22 | `verify_backup` | Verify backup integrity |
| 23 | `rollback_restore` | Rollback failed restore |

### Multi-Language (6 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 24 | `detect_language` | Detect text language |
| 25 | `get_supported_languages` | List supported languages |
| 26 | `search_by_language` | Search by language filter |
| 27 | `get_language_distribution` | Get language statistics |
| 28 | `cross_language_search` | Cross-language search |
| 29 | `get_search_facets` | Get search facets |

### Advanced AI & Search (3 tools)

| # | Tool | Purpose |
|---|-------|---------|
| 30 | `cluster_memories` | Cluster memories semantically |
| 31 | `advanced_search` | Advanced search with re-ranking |
| 32 | `expand_search_query` | Expand search query with LLM |

**Usage Pattern:** Enhanced Cognee automatically triggers these tools based on:
- Events (e.g., add_memory triggers check_duplicate)
- Scheduled maintenance tasks
- Performance monitoring
- Chained automation workflows

---

## How MCP Tools Work - Three Types of Invocation

### 1. Manual Invocation (M) - User Controlled

**Characteristics:**
- User explicitly requests tool usage
- Direct control over tool execution
- Used for destructive or policy operations

**Example:**
```
User: "Delete all memories older than 1 year"
→ expire_memories(days=365, dry_run=False) [MANUAL]
```

**Tools (10):**
- delete_memory, expire_memories, set_memory_ttl, archive_category
- set_memory_sharing, create_backup, restore_backup
- create_shared_space, schedule_task, cancel_task

### 2. Automatic Invocation (A) - AI IDE Controlled

**Characteristics:**
- AI IDE decides when to call tools
- Based on user queries and context needs
- No user intervention required

**Example:**
```
User: "What did we discuss about authentication?"
→ search_memories(query="authentication", limit=10) [AUTO]
```

**Tools (16):**
- add_memory, search_memories, get_memories, get_memory, update_memory, list_agents
- cognify, search, list_data, get_stats, health
- check_memory_access, get_shared_memories
- list_backups, list_tasks, sync_agent_state

### 3. System Invocation (S) - Enhanced Cognee Controlled

**Characteristics:**
- Enhanced Cognee triggers tools based on events
- Chained automation after user/AI actions
- Scheduled maintenance tasks
- No direct user or AI IDE intervention

**Example:**
```
User: "Add memory: We use JWT for authentication"
→ add_memory(...) [AUTO - triggered by AI]
  → check_duplicate() [SYSTEM - chained]
  → publish_memory_event() [SYSTEM - chained]
  → get_performance_metrics() [SYSTEM - chained]
```

**Tools (32):**
- Performance & Monitoring (5): get_performance_metrics, get_slow_queries, get_prometheus_metrics, check_duplicate, publish_memory_event
- Statistics (7): get_memory_age_stats, get_deduplication_stats, get_summary_stats, get_summarization_stats, summary_stats, get_sync_status, get_search_analytics
- Deduplication (5): auto_deduplicate, deduplicate, deduplication_report, schedule_deduplication
- Summarization (6): summarize_old_memories, summarize_category, intelligent_summarize, auto_summarize_old_memories, schedule_summarization
- Backup (2): verify_backup, rollback_restore
- Multi-Language (6): detect_language, get_supported_languages, search_by_language, get_language_distribution, cross_language_search, get_search_facets
- Advanced AI (3): cluster_memories, advanced_search, expand_search_query

---

## Complete Tool List by Category

### Standard Memory Tools (7)
| Tool | Type |
|------|------|
| add_memory | (A) Auto |
| search_memories | (A) Auto |
| get_memories | (A) Auto |
| get_memory | (A) Auto |
| update_memory | (A) Auto |
| delete_memory | (M) Manual |
| list_agents | (A) Auto |

### Enhanced Cognee Tools (5)
| Tool | Type |
|------|------|
| cognify | (A) Auto |
| search | (A) Auto |
| list_data | (A) Auto |
| get_stats | (A) Auto |
| health | (A) Auto |

### Memory Management Tools (4)
| Tool | Type |
|------|------|
| expire_memories | (M) Manual |
| get_memory_age_stats | (S) System |
| set_memory_ttl | (M) Manual |
| archive_category | (M) Manual |

### Memory Deduplication Tools (5)
| Tool | Type |
|------|------|
| check_duplicate | (S) System |
| auto_deduplicate | (S) System |
| get_deduplication_stats | (S) System |
| deduplicate | (S) System |
| deduplication_report | (S) System |

### Memory Summarization Tools (5)
| Tool | Type |
|------|------|
| summarize_old_memories | (S) System |
| summarize_category | (S) System |
| get_summary_stats | (S) System |
| get_summarization_stats | (S) System |
| summary_stats | (S) System |

### Performance Analytics Tools (3)
| Tool | Type |
|------|------|
| get_performance_metrics | (S) System |
| get_slow_queries | (S) System |
| get_prometheus_metrics | (S) System |

### Cross-Agent Sharing Tools (4)
| Tool | Type |
|------|------|
| set_memory_sharing | (M) Manual |
| check_memory_access | (A) Auto |
| get_shared_memories | (A) Auto |
| create_shared_space | (M) Manual |

### Real-Time Sync Tools (3)
| Tool | Type |
|------|------|
| publish_memory_event | (S) System |
| get_sync_status | (S) System |
| sync_agent_state | (A) Auto |

### Backup & Recovery Tools (5)
| Tool | Type |
|------|------|
| create_backup | (M) Manual |
| restore_backup | (M) Manual |
| list_backups | (A) Auto |
| verify_backup | (S) System |
| rollback_restore | (S) System |

### Scheduling Tools (3)
| Tool | Type |
|------|------|
| schedule_task | (M) Manual |
| list_tasks | (A) Auto |
| cancel_task | (M) Manual |

### Scheduling Automation Tools (3)
| Tool | Type |
|------|------|
| schedule_deduplication | (S) System |
| schedule_summarization | (S) System |
| deduplication_report | (S) System |

### Multi-Language Tools (6)
| Tool | Type |
|------|------|
| detect_language | (S) System |
| get_supported_languages | (S) System |
| search_by_language | (S) System |
| get_language_distribution | (S) System |
| cross_language_search | (S) System |
| get_search_facets | (S) System |

### Advanced AI & Search Tools (6)
| Tool | Type |
|------|------|
| intelligent_summarize | (S) System |
| auto_summarize_old_memories | (S) System |
| cluster_memories | (S) System |
| advanced_search | (S) System |
| expand_search_query | (S) System |
| get_search_analytics | (S) System |

---

## Summary

- **Manual (M):** 10 tools - Destructive operations and policy settings requiring explicit user invocation
- **Auto (A):** 16 tools - AI IDE controlled based on user queries and context
- **System (S):** 32 tools - Enhanced Cognee controlled via chained automation and scheduled tasks
- **Total:** 59 tools with comprehensive automation

**Source:** Enhanced Cognee README.md (lines 870-1200)
