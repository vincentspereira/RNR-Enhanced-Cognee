# Enhanced Cognee - Summarization Guide

Complete guide to summarizing memories in Enhanced Cognee.

## Overview

Enhanced Cognee includes comprehensive summarization capabilities:
- Automatic old memory summarization
- Content preservation (originals always kept)
- LLM-powered summaries
- Token savings tracking
- Compression ratio reporting
- Scheduled periodic summarization

## How Summarization Works

### Content Preservation

**IMPORTANT**: Summarization ALWAYS preserves original content:

- Original content stored in metadata
- Summary replaces visible content
- Can restore original if needed
- Tracks original length and summary date

### Summarization Process

1. **Identify Candidates**: Old memories above minimum length
2. **Generate Summary**: Use LLM or extractive summarization
3. **Store Summary**: Replace visible content with summary
4. **Preserve Original**: Store original in metadata
5. **Track Savings**: Calculate token and space savings

## Manual Summarization

### Dry Run (Preview)

See what would be summarized without making changes:

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import summarize_old_memories

async def summarize():
    result = await summarize_old_memories(
        days=30,
        min_length=1000,
        dry_run=True
    )
    print(result)

asyncio.run(summarize())
"
```

### Execute Summarization

After reviewing dry run, execute actual summarization:

```bash
# Execute summarization
python -c "
import asyncio
from enhanced_cognee_mcp_server import summarize_old_memories

async def summarize():
    result = await summarize_old_memories(
        days=30,
        min_length=1000,
        dry_run=False
    )
    print(result)

asyncio.run(summarize())
"
```

## Scheduled Summarization

### Configure Schedule

Configure monthly summarization (default: 1st of month, 3 AM):

```json
// summarization_config.json
{
  "schedule": "monthly",
  "age_threshold_days": 30,
  "min_length": 1000,
  "summary_target_length": 200,
  "preserve_original": true
}
```

### Schedule Configuration Options

- **schedule**: "monthly" or "weekly"
- **age_threshold_days**: Minimum age in days
- **min_length**: Minimum content length (characters)
- **summary_target_length**: Target summary length (characters)
- **preserve_original**: Always true (safety measure)

## LLM Integration

### Configure LLM

```json
{
  "llm_settings": {
    "provider": "anthropic",
    "model": "claude-3-haiku",
    "max_tokens": 300
  }
}
```

### Supported Providers

- **Anthropic**: Claude models (recommended)
- **OpenAI**: GPT models
- **Local**: Ollama, llama.cpp

### Fallback Mode

If LLM unavailable, uses extractive summarization:
- Takes first N sentences that fit target length
- Simple but effective
- No external dependencies

## Viewing Statistics

### Get Summarization Stats

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import summary_stats

async def stats():
    result = await summary_stats()
    print(result)

asyncio.run(stats())
"
```

### Sample Output

```
OK Summarization Statistics
Total memories: 15234
Summarized: 8923
Full memories: 6311
Summarization ratio: 58.6%
Space saved: 145.23 MB
```

## Advanced Features

### Summarize by Type

Summarize specific memory types:

```bash
# Summarize by type
python -c "
from src.scheduled_summarization import ScheduledSummarization

summarizer = ScheduledSummarization(postgres_pool)
result = await summarizer.summarize_by_type(
    memory_type='trading_strategy',
    days=30
)
print(result)
"
```

### Summarize by Concept

Summarize memories containing specific concepts:

```bash
# Summarize by concept
python -c "
result = await summarizer.summarize_by_concept(
    memory_concept='risk_management',
    days=30
)
print(result)
"
```

## Configuration Tuning

### Age Threshold

Adjust how old memories must be before summarization:

```json
{
  "age_threshold_days": 30
}
```

- **7 days**: Aggressive (more summarization)
- **30 days**: Balanced (recommended)
- **90 days**: Conservative (less summarization)

### Minimum Length

Adjust minimum content length:

```json
{
  "min_length": 1000
}
```

- **500**: Summarize more memories
- **1000**: Balanced (recommended)
- **2000**: Summarize only long memories

### Summary Target Length

Adjust summary length:

```json
{
  "summary_target_length": 200
}
```

- **100**: Very brief summaries
- **200**: Balanced (recommended)
- **500**: Detailed summaries

## Best Practices

1. **Start Conservative**: Begin with high age threshold and length
2. **Review Dry Runs**: Always preview before summarizing
3. **Monitor Quality**: Check summary quality regularly
4. **Keep Backups**: Have backup before large summarization jobs
5. **Track Savings**: Monitor compression ratio and token savings
6. **Adjust Gradually**: Tune parameters based on results
7. **Preserve Context**: Don't summarize critical recent memories

## Troubleshooting

### Poor Summary Quality

**Problem**: Summaries don't capture key information

**Solutions**:
```json
// Increase summary length
{
  "summary_target_length": 500
}

// Or use better LLM
{
  "llm_settings": {
    "provider": "anthropic",
    "model": "claude-3-sonnet"  // Better quality
  }
}
```

### Too Much Summarization

**Problem**: Too many memories being summarized

**Solution**:
```json
// Raise thresholds
{
  "age_threshold_days": 90,
  "min_length": 2000
}
```

### LLM Fails

**Problem**: LLM summarization fails

**Solution**:
```json
// Fallback to extractive (automatic)
// Or check LLM configuration
{
  "llm_settings": {
    "api_key": "your_key",
    "endpoint": "https://api.anthropic.com"
  }
}
```

## Performance Considerations

- **Dry Run**: 1-3 minutes for 100 candidates
- **LLM Summarization**: 5-15 minutes for 100 memories
- **Extractive**: 1-2 minutes for 100 memories
- **Impact**: Minimal on running system
- **Frequency**: Monthly recommended

## Content Restoration

Restore original content from metadata:

```sql
-- Get summarized memories
SELECT id, metadata->>'original_length' as original_length
FROM shared_memory.documents
WHERE metadata->>'summarized' = 'true';

-- Restore from backup if needed
-- (Originals preserved in metadata but visible content is summary)
```

## Next Steps

- Read [Deduplication Guide](DEDUPLICATION_GUIDE.md)
- Review [Maintenance Scheduling](MAINTENANCE_SCHEDULING.md)
- Check [Backup & Restore](BACKUP_RESTORE_GUIDE.md)

---

**Summarization** - Reduce memory size while preserving information with Enhanced Cognee.
