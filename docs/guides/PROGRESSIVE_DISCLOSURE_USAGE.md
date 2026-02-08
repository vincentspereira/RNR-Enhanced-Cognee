# Progressive Disclosure Search - Usage Guide

**Enhanced Cognee Token-Efficient Search**

This guide explains how to use progressive disclosure search for 10x token efficiency.

---

## Overview

Progressive disclosure is a 3-layer search architecture that dramatically reduces token usage while maintaining full access to information.

### The 3 Layers

**Layer 1: `search_index`** - Compact Results
- Returns IDs + summaries only (~50 tokens per result)
- 10x more efficient than returning full content
- Use for: Initial search and discovery

**Layer 2: `get_timeline`** - Chronological Context
- Shows what happened before and after a memory
- Provides context without loading everything
- Use for: Understanding memory relationships

**Layer 3: `get_memory_batch`** - Full Details
- Returns complete content for selected memories
- Always batch multiple IDs for efficiency
- Use for: Getting full details when needed

---

## Usage Pattern

### Standard Workflow

```python
# Step 1: Search index (get compact results)
results = await search_index(
    query="authentication flow",
    agent_id="default",
    limit=20
)

# Returns:
# {
#   "result_count": 15,
#   "results": [
#     {"memory_id": "uuid-1", "summary": "Implemented OAuth...", "estimated_tokens": 500},
#     {"memory_id": "uuid-2", "summary": "Fixed login bug...", "estimated_tokens": 300},
#     ...
#   ],
#   "token_savings": {
#     "tokens_saved": 6750,  # 10x savings!
#     "efficiency_percent": 90.0
#   }
# }

# Step 2: Get timeline for interesting memory
timeline = await get_timeline(
    memory_id="uuid-1",
    before=5,  # 5 memories before
    after=5   # 5 memories after
)

# Returns chronological context:
# {
#   "before": [...],    # 5 memories that happened before
#   "current": {...},  # The target memory
#   "after": [...]     # 5 memories that happened after
# }

# Step 3: Batch fetch full details for selected memories
full_details = await get_memory_batch(
    memory_ids=["uuid-1", "uuid-5", "uuid-10"],
    include_metadata=True
)

# Returns complete content for selected memories only
```

---

## MCP Tools

### search_index

Layer 1 compact search.

**Parameters:**
- `query` (str): Search query text
- `agent_id` (str, optional): Agent ID (default: "default")
- `limit` (int, optional): Max results (default: 50)
- `data_type` (str, optional): Filter by data type

**Returns:**
```json
{
  "query": "authentication",
  "layer": 1,
  "result_count": 15,
  "results": [
    {
      "memory_id": "uuid",
      "summary": "Brief summary...",
      "data_type": "observation",
      "created_at": "2026-02-06T10:00:00Z",
      "estimated_tokens": 500
    }
  ],
  "token_savings": {
    "estimated_full_tokens": 7500,
    "compact_tokens": 750,
    "tokens_saved": 6750,
    "efficiency_percent": 90.0
  }
}
```

**Example:**
```python
# Search for authentication-related memories
results = await mcp.call_tool("search_index", {
    "query": "OAuth authentication flow",
    "agent_id": "claude-code",
    "limit": 20
})
```

### get_timeline

Layer 2 chronological context.

**Parameters:**
- `memory_id` (str): Memory ID to get context for
- `before` (int, optional): Memories before (default: 5)
- `after` (int, optional): Memories after (default: 5)
- `include_summaries` (bool, optional): Include summaries (default: true)

**Returns:**
```json
{
  "memory_id": "uuid",
  "layer": 2,
  "before": [
    {
      "memory_id": "uuid-1",
      "summary": "Before memory 1...",
      "created_at": "2026-02-06T09:55:00Z"
    }
  ],
  "current": {
    "memory_id": "uuid",
    "summary": "Target memory...",
    "created_at": "2026-02-06T10:00:00Z"
  },
  "after": [
    {
      "memory_id": "uuid+1",
      "summary": "After memory 1...",
      "created_at": "2026-02-06T10:05:00Z"
    }
  ]
}
```

**Example:**
```python
# Get context around a memory
timeline = await mcp.call_tool("get_timeline", {
    "memory_id": "uuid-here",
    "before": 3,
    "after": 3
})
```

### get_memory_batch

Layer 3 full details.

**Parameters:**
- `memory_ids` (list[str]): List of memory IDs
- `include_metadata` (bool, optional): Include metadata (default: false)

**Returns:**
```json
{
  "layer": 3,
  "count": 3,
  "memories": [
    {
      "memory_id": "uuid",
      "content": "Full memory content here...",
      "data_type": "observation",
      "summary": "Brief summary...",
      "created_at": "2026-02-06T10:00:00Z",
      "updated_at": "2026-02-06T10:00:00Z",
      "agent_id": "claude-code"
    }
  ]
}
```

**Example:**
```python
# Get full details for selected memories
details = await mcp.call_tool("get_memory_batch", {
    "memory_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "include_metadata": true
})
```

---

## Real-World Examples

### Example 1: Finding a Bug Fix

```python
# Layer 1: Search for bug fix
results = await search_index(query="fix login bug", limit=20)

# Find interesting result
bug_fix_id = results["results"][0]["memory_id"]

# Layer 2: Get context - what led to the bug fix?
timeline = await get_timeline(memory_id=bug_fix_id, before=5, after=2)

# See the bug report and investigation that led to the fix
for memory in timeline["before"]:
    print(f"{memory['created_at']}: {memory['summary']}")

# Layer 3: Get full details of the fix itself
fix_details = await get_memory_batch(memory_ids=[bug_fix_id], include_metadata=True)
print(f"Full fix: {fix_details['memories'][0]['content']}")
```

### Example 2: Researching a Feature

```python
# Layer 1: Search for feature implementation
results = await search_index(query="OAuth integration", limit=30)

# Review top results
for result in results["results"][:10]:
    print(f"{result['memory_id']}: {result['summary']}")

# Select interesting memories
interesting_ids = [r["memory_id"] for r in results["results"][:3]]

# Layer 2: Get timeline for each
for memory_id in interesting_ids:
    timeline = await get_timeline(memory_id=memory_id, before=2, after=2)
    print(f"\nContext for {memory_id}:")
    print(f"  Before: {len(timeline['before'])} memories")
    print(f"  After: {len(timeline['after'])} memories")

# Layer 3: Batch fetch full details
full_details = await get_memory_batch(
    memory_ids=interesting_ids,
    include_metadata=True
)
```

### Example 3: Code Review Context

```python
# Layer 1: Find recent changes to a file
results = await search_index(
    query="auth.py changes",
    data_type="observation",
    limit=10
)

# Layer 2: Understand the sequence of changes
for result in results["results"]:
    memory_id = result["memory_id"]
    timeline = await get_timeline(
        memory_id=memory_id,
        before=3,
        after=1
    )

    print(f"\nSequence for {memory_id}:")
    print("  Before:")
    for mem in timeline["before"]:
        print(f"    - {mem['summary']}")

    print("  Current:")
    print(f"    - {timeline['current']['summary']}")

# Layer 3: Get full content for review
review_ids = [r["memory_id"] for r in results["results"][:3]]
review_content = await get_memory_batch(memory_ids=review_ids)
```

---

## Token Efficiency

### Comparison: Traditional vs Progressive Disclosure

**Traditional Search (returns full content):**
```
Query: "authentication"
Results: 10 memories
Average: 500 tokens per memory
Total: 5,000 tokens
```

**Progressive Disclosure (Layer 1):**
```
Query: "authentication"
Results: 10 memories (compact)
Average: 50 tokens per result
Total: 500 tokens

Savings: 4,500 tokens (90% reduction)
```

### When to Use Each Layer

**Layer 1 (search_index):**
- Initial search and discovery
- Browsing many results
- Getting overview of topics
- Token-constrained situations

**Layer 2 (get_timeline):**
- Understanding context
- Seeing chronological flow
- Investigating relationships
- Finding related memories

**Layer 3 (get_memory_batch):**
- Getting full content when needed
- Detailed analysis
- Export/import operations
- Final review before action

---

## Best Practices

### DO:
- Always start with Layer 1 for search
- Use Layer 2 to understand context before fetching full details
- Batch multiple IDs in Layer 3 for efficiency
- Filter by data_type when possible
- Use appropriate limits (10-50 for Layer 1)

### DON'T:
- Don't fetch full details for all search results
- Don't skip Layer 2 if you need context
- Don't fetch memories one-by-one (use batching)
- Don't use Layer 3 for large numbers of memories (>50)

---

## Performance Tips

### Optimizing Token Usage

```python
# GOOD: Progressive disclosure
results = await search_index(query="API design", limit=20)
timeline = await get_timeline(memory_id=results["results"][0]["memory_id"])
details = await get_memory_batch(memory_ids=[selected_id])

# BAD: Fetching everything at once
all_memories = await get_memories(agent_id="default", limit=1000)  # Expensive!
```

### Caching Strategies

```python
# Cache Layer 1 results for frequent queries
search_cache = {}

if query not in search_cache:
    search_cache[query] = await search_index(query=query)

# Cache Layer 2 timelines
timeline_cache = {}
if memory_id not in timeline_cache:
    timeline_cache[memory_id] = await get_timeline(memory_id=memory_id)

# Layer 3 rarely needs caching (use as needed)
```

---

## Statistics

Monitor your token efficiency:

```python
stats = await get_token_efficiency_stats()

print(f"Total searches: {stats['layer1_searches']}")
print(f"Total timelines: {stats['layer2_timelines']}")
print(f"Total batches: {stats['layer3_batches']}")
print(f"Tokens saved: {stats['tokens_saved']}")
print(f"Efficiency: {stats['database']['token_efficiency_percent']}%")
```

---

## Troubleshooting

### Issue: Empty results

**Cause:** Query too specific or no matches

**Solution:**
- Try broader query terms
- Remove filters (data_type)
- Increase limit

### Issue: Timeline has no results

**Cause:** Memory ID not found or no context

**Solution:**
- Verify memory_id from Layer 1 results
- Increase before/after values
- Check if memories exist around that time

### Issue: High token usage

**Cause:** Using Layer 3 too frequently

**Solution:**
- Use Layer 1 for initial search
- Only fetch Layer 3 for selected memories
- Always batch multiple IDs

---

## Summary

Progressive disclosure provides 10x token efficiency through:

1. **Layer 1 (search_index)**: Compact search results
2. **Layer 2 (get_timeline)**: Chronological context
3. **Layer 3 (get_memory_batch)**: Full details on demand

**Usage Pattern:**
```
Search (Layer 1) → Context (Layer 2) → Details (Layer 3)
    ↓                ↓                ↓
  500 tokens       300 tokens       500 tokens
  (10 results)    (11 memories)    (3 full memories)

Total: 1,300 tokens vs 5,000+ with traditional search
Savings: 74% reduction
```

---

**Generated:** 2026-02-06
**Enhanced Cognee Team**
