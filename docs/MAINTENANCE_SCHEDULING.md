# Enhanced Cognee - Maintenance Scheduling Guide

Complete guide to configuring and managing automated maintenance tasks.

## Overview

Enhanced Cognee includes a comprehensive maintenance scheduler based on APScheduler:
- Scheduled cleanup of expired memories
- Scheduled archival of old data
- Index optimization
- Cache clearing
- Backup verification

## Scheduling Architecture

Enhanced Cognee uses APScheduler with cron expressions:

```python
from src.maintenance_scheduler import MaintenanceScheduler

scheduler = MaintenanceScheduler(mcp_client=None)
scheduler.start()
```

## Cron Expression Syntax

Cron expressions use 5 fields:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

### Common Examples

```bash
# Daily at 2 AM
0 2 * * *

# Weekly on Sunday at 3 AM
0 3 * * 0

# Monthly on 1st at 4 AM
0 4 1 * *

# Every 6 hours
0 */6 * * *

# Weekdays at 9 AM
0 9 * * 1-5

# Every hour
0 * * * *
```

## Available Maintenance Tasks

### 1. Cleanup Expired Memories

Delete memories older than specified days:

```python
# Schedule cleanup
scheduler.schedule_cleanup(
    days=90,
    schedule="0 2 * * *"  # Daily at 2 AM
)
```

**Configuration**:
```json
{
  "tasks": {
    "cleanup_expired_memories": {
      "enabled": true,
      "schedule": "0 2 * * *",
      "age_days": 90
    }
  }
}
```

### 2. Archive Old Sessions

Archive sessions older than specified days:

```python
# Schedule archival
scheduler.schedule_archival(
    days=365,
    schedule="0 3 * * 0"  # Sunday at 3 AM
)
```

**Configuration**:
```json
{
  "tasks": {
    "archive_old_sessions": {
      "enabled": true,
      "schedule": "0 3 * * 0",
      "age_days": 365
    }
  }
}
```

### 3. Optimize Indexes

Optimize database indexes:

```python
# Schedule optimization
scheduler.schedule_optimization(
    schedule="0 4 * * *"  # Daily at 4 AM
)
```

**Configuration**:
```json
{
  "tasks": {
    "optimize_indexes": {
      "enabled": true,
      "schedule": "0 4 * * *"
    }
  }
}
```

### 4. Clear Cache

Clear Redis cache:

```python
# Schedule cache clearing
scheduler.schedule_cache_clearing(
    schedule="0 5 * * *"  # Daily at 5 AM
)
```

**Configuration**:
```json
{
  "tasks": {
    "clear_cache": {
      "enabled": true,
      "schedule": "0 5 * * *"
    }
  }
}
```

### 5. Backup Verification

Verify backup integrity:

```python
# Schedule backup verification
scheduler.schedule_backup_verification(
    schedule="0 6 * * *"  # Daily at 6 AM
)
```

**Configuration**:
```json
{
  "tasks": {
    "backup_verification": {
      "enabled": true,
      "schedule": "0 6 * * *"
    }
  }
}
```

## Configuration File

Create `maintenance_config.json`:

```json
{
  "tasks": {
    "cleanup_expired_memories": {
      "enabled": true,
      "schedule": "0 2 * * *",
      "description": "Delete memories older than 90 days",
      "age_days": 90
    },
    "archive_old_sessions": {
      "enabled": true,
      "schedule": "0 3 * * 0",
      "description": "Archive sessions older than 365 days",
      "age_days": 365
    },
    "optimize_indexes": {
      "enabled": true,
      "schedule": "0 4 * * *",
      "description": "Optimize database indexes"
    },
    "clear_cache": {
      "enabled": true,
      "schedule": "0 5 * * *",
      "description": "Clear Redis cache"
    },
    "backup_verification": {
      "enabled": true,
      "schedule": "0 6 * * *",
      "description": "Verify backup integrity"
    }
  },
  "notifications": {
    "enabled": false,
    "on_failure": true,
    "on_success": false
  },
  "retention": {
    "task_history_days": 30,
    "execution_logs_days": 7
  }
}
```

## Managing Scheduled Tasks

### List Scheduled Tasks

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import list_tasks

async def main():
    result = await list_tasks()
    print(result)

asyncio.run(main())
"
```

### Cancel Scheduled Task

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import cancel_task

async def main():
    result = await cancel_task('cleanup_expired_memories')
    print(result)

asyncio.run(main())
"
```

### View Task History

```python
from src.maintenance_scheduler import MaintenanceScheduler

scheduler = MaintenanceScheduler()
history = scheduler.get_task_history(limit=50)

for execution in history:
    print(f"{execution['task_name']}: {execution['status']} ({execution['duration_seconds']}s)")
```

## Monitoring

### Task Execution Statistics

```python
stats = scheduler.get_statistics()

print(f"Total executions: {stats['total_executions']}")
print(f"Successful: {stats['successful_executions']}")
print(f"Failed: {stats['failed_executions']}")
print(f"Average times: {stats['average_execution_times']}")
```

### View Upcoming Tasks

```python
tasks = scheduler.get_scheduled_tasks()

for task_id, task_info in tasks.items():
    print(f"{task_id}: {task_info['name']}")
    print(f"  Next run: {task_info['next_run_time']}")
```

## Best Practices

1. **Schedule During Low Traffic**: Run maintenance at off-peak hours
2. **Stagger Tasks**: Don't run all tasks at the same time
3. **Monitor Execution**: Track task success/failure rates
4. **Test Schedules**: Verify cron expressions before deploying
5. **Keep Logs**: Retain execution logs for troubleshooting
6. **Set Alerts**: Notify on task failures
7. **Regular Review**: Update schedules as system grows

## Production Schedules

Recommended production maintenance schedule:

```json
{
  "tasks": {
    "cleanup_expired_memories": {
      "enabled": true,
      "schedule": "0 2 * * *",
      "age_days": 90
    },
    "archive_old_sessions": {
      "enabled": true,
      "schedule": "0 3 * * 0",
      "age_days": 365
    },
    "optimize_indexes": {
      "enabled": true,
      "schedule": "0 4 * * 0"
    },
    "clear_cache": {
      "enabled": true,
      "schedule": "0 5 * * *"
    },
    "backup_verification": {
      "enabled": true,
      "schedule": "0 6 * * *"
    }
  }
}
```

This schedule:
- Runs cleanup daily at 2 AM
- Archives sessions weekly (Sunday 3 AM)
- Optimizes indexes weekly (Sunday 4 AM)
- Clears cache daily at 5 AM
- Verifies backups daily at 6 AM

## Troubleshooting

### Task Not Running

**Problem**: Scheduled task doesn't execute

**Solution**:
```python
# Check if scheduler is running
print(scheduler.get_statistics()['running'])

# Check task is scheduled
tasks = scheduler.get_scheduled_tasks()
print(tasks)
```

### Task Fails Repeatedly

**Problem**: Task fails every time it runs

**Solution**:
```python
# View task history
history = scheduler.get_task_history(limit=10)

# Find failed executions
for execution in history:
    if execution['status'] == 'failed':
        print(f"Task: {execution['task_name']}")
        print(f"Error: {execution.get('error', 'Unknown')}")
```

### Cron Expression Invalid

**Problem**: Cron expression not accepted

**Solution**:
```python
# Validate cron expression
from apscheduler.triggers.cron import CronTrigger

try:
    trigger = CronTrigger.from_crontab("0 2 * * *")
    print("Valid cron expression")
except Exception as e:
    print(f"Invalid: {e}")
```

## Next Steps

- Read [Deduplication Guide](DEDUPLICATION_GUIDE.md)
- Review [Summarization Guide](SUMMARIZATION_GUIDE.md)
- Check [Backup & Restore](BACKUP_RESTORE_GUIDE.md)

---

**Maintenance Scheduling** - Automated maintenance for healthy Enhanced Cognee deployments.
