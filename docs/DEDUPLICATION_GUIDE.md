# Enhanced Cognee - Deduplication Guide

Complete guide to deduplicating memories in Enhanced Cognee.

## Overview

Enhanced Cognee includes comprehensive deduplication capabilities:
- Automatic duplicate detection
- Scheduled periodic deduplication
- Dry-run mode for preview
- Approval workflow
- Undo capability
- Detailed reporting

## How Deduplication Works

### Detection Methods

1. **Exact Text Match**: Identical content
2. **Vector Similarity**: Semantically similar content (95%+ threshold)
3. **Content Hash**: Hash-based grouping

### Merge Strategies

1. **Keep Newest**: Retain the most recent memory
2. **Keep Both**: Retain all versions
3. **Append**: Merge content together

## Manual Deduplication

### Dry Run (Preview)

See what would be deduplicated without making changes:

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import deduplicate

async def dedup():
    result = await deduplicate(
        agent_id=None,  # All agents
        dry_run=True
    )
    print(result)

asyncio.run(dedup())
"
```

### Execute Deduplication

After reviewing dry run, execute actual deduplication:

```bash
# Execute deduplication
python -c "
import asyncio
from enhanced_cognee_mcp_server import deduplicate

async def dedup():
    result = await deduplicate(
        agent_id=None,
        dry_run=False
    )
    print(result)

asyncio.run(dedup())
"
```

### Agent-Specific Deduplication

Deduplicate memories for a specific agent:

```bash
# Deduplicate single agent
python -c "
result = await deduplicate(
    agent_id='claude-code',
    dry_run=False
)
"
```

## Scheduled Deduplication

### Configure Schedule

Configure weekly deduplication (default: Sunday 4 AM):

```json
// deduplication_config.json
{
  "schedule": "weekly",
  "dry_run_first": true,
  "require_approval": true,
  "similarity_threshold": 0.95,
  "merge_strategy": "keep_newest"
}
```

### Enable Auto-Approve

Skip approval for automatic deduplication:

```json
{
  "schedule": "weekly",
  "dry_run_first": false,
  "require_approval": false
}
```

## Approval Workflow

### 1. Dry Run

System runs dry-run and shows duplicates:

```
Deduplication Report
====================

Found 15 duplicate groups
Estimated token savings: 4,523 tokens

This will merge duplicate memories, keeping the newest version of each group.

Examples:

Group 1 (3 duplicates):
  - abc123: This is important information about trading strategies...
  - def456: This is important information about trading strategies...
  - ghi789: This is important information about trading strategies...

... and 12 more groups

Approve this deduplication?
```

### 2. Approve

```python
from src.scheduled_deduplication import ScheduledDeduplication

dedup = ScheduledDeduplication(postgres_pool, qdrant_client)

# First, run dry run
dry_run_result = await dedup.dry_run_deduplication()
print(dry_run_result['approval_message'])

# Then approve
result = await dedup.approve_deduplication(dry_run_result['deduplication_id'])
print(result)
```

### 3. Reject

```python
# Reject deduplication
dedup.reject_deduplication(dry_run_result['deduplication_id'])
```

## Deduplication Reports

### View Report

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import deduplication_report

async def report():
    result = await deduplication_report()
    print(result)

asyncio.run(report())
"
```

### Report Contents

```json
{
  "total_deduplications": 5,
  "total_duplicates_found": 75,
  "total_memories_merged": 60,
  "total_token_savings": 18234,
  "recent_deduplications": [
    {
      "deduplication_id": "abc-123",
      "started_at": "2025-02-06T04:00:00",
      "duplicates_found": 15,
      "merged_count": 12,
      "token_savings": 4500
    }
  ]
}
```

## Undo Deduplication

Undo last deduplication:

```python
from src.scheduled_deduplication import ScheduledDeduplication

dedup = ScheduledDeduplication(postgres_pool, qdrant_client)

# Undo last deduplication
result = await dedup.undo_deduplication('deduplication_id')
print(result)
```

**WARNING**: Undo functionality is limited. Always keep backups!

## Configuration

### Similarity Threshold

Adjust how similar memories must be to be considered duplicates:

```json
{
  "similarity_threshold": 0.95
}
```

- **0.90**: Aggressive deduplication (may merge different but similar)
- **0.95**: Balanced (recommended)
- **0.99**: Conservative (only near-exact matches)

### Merge Strategy

Choose how to handle duplicates:

```json
{
  "merge_strategy": "keep_newest"
}
```

- **keep_newest**: Retain most recent version (recommended)
- **keep_both**: Keep all versions (for auditing)
- **append**: Merge content together

## Best Practices

1. **Always Dry Run First**: Preview before deduplicating
2. **Review Reports**: Check what will be merged
3. **Schedule Regularly**: Weekly or monthly deduplication
4. **Adjust Threshold**: Tune similarity threshold for your data
5. **Keep Backups**: Always have recent backup before deduplication
6. **Monitor Token Savings**: Track impact over time
7. **Audit Trail**: Review deduplication history

## Troubleshooting

### No Duplicates Found

**Problem**: Dry run finds 0 duplicates

**Possible causes**:
- Deduplication already run recently
- Similarity threshold too high
- Data quality is good

**Solution**:
```python
# Lower threshold temporarily
config = {"similarity_threshold": 0.90}
dedup = ScheduledDeduplication(postgres_pool, qdrant_client, config)
result = await dedup.dry_run_deduplication()
```

### Too Many Duplicates

**Problem**: Too many memories flagged as duplicates

**Solution**:
```python
# Raise threshold
config = {"similarity_threshold": 0.99}
```

### Deduplication Fails

**Problem**: Deduplication fails with error

**Solution**:
```python
# Check database connections
import asyncio
async def check():
    async with postgres_pool.acquire() as conn:
        await conn.fetchval('SELECT 1')
    print("OK PostgreSQL connected")

asyncio.run(check())
```

## Performance Considerations

- **Dry Run**: 1-5 minutes for 10,000 memories
- **Execution**: 2-10 minutes depending on duplicates found
- **Impact**: Minimal on running system
- **Frequency**: Weekly recommended for active systems

## Next Steps

- Read [Summarization Guide](SUMMARIZATION_GUIDE.md)
- Review [Maintenance Scheduling](MAINTENANCE_SCHEDULING.md)
- Check [Backup & Restore](BACKUP_RESTORE_GUIDE.md)

---

**Deduplication** - Keep your Enhanced Cognee memory lean and efficient.
