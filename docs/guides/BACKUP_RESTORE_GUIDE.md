# Enhanced Cognee - Backup & Restore Guide

Complete guide to backing up and restoring Enhanced Cognee memory stack.

## Overview

Enhanced Cognee includes comprehensive backup and restore capabilities:
- Automated scheduled backups
- On-demand manual backups
- Full or partial database backups
- Backup compression
- Backup verification
- Restore with validation

## Backup Architecture

Enhanced Cognee backs up four databases:

1. **PostgreSQL** - Relational memory storage (via pg_dump)
2. **Qdrant** - Vector embeddings (via snapshot API)
3. **Neo4j** - Graph relationships (via backup API)
4. **Redis** - Cache layer (via RDB snapshot)

## Creating Backups

### Manual Backup

Create a manual backup of all databases:

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import create_backup

async def backup():
    result = await create_backup(
        backup_type='manual',
        databases='postgresql,qdrant,neo4j,redis',
        compress=True,
        description='Manual backup before changes'
    )
    print(result)

asyncio.run(backup())
"
```

### Backup Specific Databases

```bash
# Backup only PostgreSQL
python -c "
from src.backup_manager import BackupManager
manager = BackupManager()
backup_id = manager.create_backup(
    backup_type='manual',
    databases=['postgresql'],
    compress=True
)
print(f'Backup ID: {backup_id}')
"
```

### Scheduled Backups

Configure automated backups:

```json
// automation_config.json
{
  "backup_schedule": {
    "enabled": true,
    "daily_backup_time": "02:00",
    "weekly_backup_day": "sunday",
    "weekly_backup_time": "03:00",
    "monthly_backup_day": 1,
    "monthly_backup_time": "04:00",
    "retention_days": {
      "daily": 7,
      "weekly": 28,
      "monthly": 365
    }
  }
}
```

## Backup Storage

### Directory Structure

```
backups/
├── manual/
│   └── backup_20250206_120000_abc123/
│       ├── postgresql_20250206_120000.sql.gz
│       ├── qdrant_20250206_120000.snapshot.gz
│       ├── neo4j_20250206_120000.backup.gz
│       └── redis_20250206_120000.rdb.gz
├── daily/
├── weekly/
├── monthly/
└── metadata.db
```

### Backup Metadata

Each backup includes metadata:

```json
{
  "backup_id": "abc123-def456",
  "backup_type": "manual",
  "created_at": "2025-02-06T12:00:00",
  "databases_backed_up": ["postgresql", "qdrant", "neo4j", "redis"],
  "total_size_bytes": 1234567890,
  "compressed": true,
  "checksum": "sha256:abc123...",
  "status": "completed"
}
```

## Restoring Backups

### Full Restore

Restore all databases from a backup:

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import restore_backup

async def restore():
    result = await restore_backup(
        backup_id='abc123-def456',
        databases='postgresql,qdrant,neo4j,redis',
        validate=True
    )
    print(result)

asyncio.run(restore())
"
```

### Partial Restore

Restore specific databases:

```bash
# Restore only PostgreSQL
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.restore_from_backup(
    backup_id='abc123-def456',
    databases=['postgresql'],
    validate=True
)
print(result)
"
```

### Restore with Scripts

```bash
# Restore all databases
./scripts/restore_all.sh abc123-def456

# Restore specific database
./scripts/restore_postgres.sh abc123-def456
./scripts/restore_qdrant.sh abc123-def456
./scripts/restore_neo4j.sh abc123-def456
./scripts/restore_redis.sh abc123-def456
```

## Backup Verification

### Manual Verification

Verify backup integrity:

```bash
# Using MCP tool
python -c "
import asyncio
from enhanced_cognee_mcp_server import verify_backup

async def verify():
    result = await verify_backup(backup_id='abc123-def456')
    print(result)

asyncio.run(verify())
"
```

### Automated Verification

Enable scheduled verification:

```json
// maintenance_config.json
{
  "tasks": {
    "backup_verification": {
      "enabled": true,
      "schedule": "0 6 * * *",
      "description": "Verify backup integrity daily at 6 AM"
    }
  }
}
```

## Troubleshooting

### Backup Fails

**Problem**: PostgreSQL backup fails with "password authentication failed"

**Solution**:
```bash
# Check .env file
cat .env | grep POSTGRES

# Verify password is correct
psql -h localhost -p 25432 -U cognee_user -d cognee_db
```

**Problem**: Qdrant snapshot creation fails

**Solution**:
```bash
# Check Qdrant is running
curl http://localhost:26333/collections

# Verify API key (if set)
curl -H "api-key: YOUR_KEY" http://localhost:26333/collections
```

### Restore Fails

**Problem**: Restore fails validation

**Solution**:
```bash
# Check validation errors
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
results = manager.validate_restored_data(['postgresql', 'qdrant'])
print(results)
"

# Individual database validation
python -c "
manager = RecoveryManager()
print(manager._validate_postgres())
print(manager._validate_qdrant())
"
```

**Problem**: Restore partially succeeds

**Solution**:
```bash
# Rollback and retry
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
rollback = manager.rollback_last_restore()
print(rollback)
"

# Then retry with individual databases
manager.restore_postgres('backup_id')
manager.restore_qdrant('backup_id')
```

## Best Practices

1. **Test Backups Regularly**: Verify backups can be restored monthly
2. **Keep Multiple Backups**: Don't rely on a single backup
3. **Offsite Storage**: Store backups in multiple locations
4. **Encrypt Backups**: Use encryption for sensitive data
5. **Monitor Backup Jobs**: Set up alerts for backup failures
6. **Document Restore Procedures**: Keep updated runbooks
7. **Retention Policy**: Regularly delete old backups per policy

## Backup Automation

### Cron Jobs

```bash
# Daily backup at 2 AM
0 2 * * * /path/to/enhanced-cognee/scripts/backup_all.sh daily

# Weekly backup on Sunday at 3 AM
0 3 * * 0 /path/to/enhanced-cognee/scripts/backup_all.sh weekly

# Monthly backup on 1st at 4 AM
0 4 1 * * /path/to/enhanced-cognee/scripts/backup_all.sh monthly
```

### Systemd Timer

```ini
# /etc/systemd/system/enhanced-cognee-backup.timer
[Unit]
Description=Enhanced Cognee Backup Timer
Requires=enhanced-cognee-backup.service

[Timer]
OnCalendar=daily
OnCalendar=Sun *-*-* 03:00:00
OnCalendar=*-*-01 04:00:00

[Install]
WantedBy=timers.target
```

## Performance Considerations

- **Backup Duration**: 5-30 minutes depending on data size
- **Compression**: Adds 10-20% overhead but reduces size by 70-90%
- **Parallel Backups**: All databases backed up in parallel
- **Impact**: Minimal impact on running system (uses snapshots)

## Recovery Time Objectives

- **RPO (Recovery Point Objective)**: Up to 24 hours (last backup)
- **RTO (Recovery Time Objective)**: 30-60 minutes for full restore

## Next Steps

- Read [Disaster Recovery Guide](DISASTER_RECOVERY.md)
- Review [Maintenance Scheduling](MAINTENANCE_SCHEDULING.md)
- Check [Rollback Procedures](ROLLBACK_PROCEDURES.md)

---

**Backup & Restore** - Comprehensive data protection for Enhanced Cognee deployments.
