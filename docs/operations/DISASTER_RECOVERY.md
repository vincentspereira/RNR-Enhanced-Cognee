# Enhanced Cognee - Disaster Recovery Guide

Complete disaster recovery procedures for Enhanced Cognee memory stack.

## Overview

Enhanced Cognee includes comprehensive disaster recovery capabilities:
- Automated backups of all databases
- On-demand backup creation
- Full or partial database restore
- Data integrity validation
- Automatic rollback on failure

## Recovery Procedures

### 1. Full System Restore

Restore all databases from a backup:

```bash
# Using script
./scripts/restore_all.sh <backup_id>

# Using Python
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.restore_from_backup('<backup_id>')
print(result)
"
```

### 2. Individual Database Restore

Restore specific databases:

```bash
# PostgreSQL
./scripts/restore_postgres.sh <backup_id>

# Qdrant
./scripts/restore_qdrant.sh <backup_id>

# Neo4j
./scripts/restore_neo4j.sh <backup_id>

# Redis
./scripts/restore_redis.sh <backup_id>
```

### 3. Restore with Validation

Validate data after restore:

```python
from src.recovery_manager import RecoveryManager

manager = RecoveryManager()
result = manager.restore_from_backup(
    backup_id='<backup_id>',
    databases=['postgresql', 'qdrant'],
    validate=True  # Validates after restore
)

if result['status'] == 'success':
    print('[OK] Restore validated successfully')
    print(result['validation'])
```

### 4. Rollback on Failure

If validation fails, automatic rollback is triggered:

```python
result = manager.restore_from_backup(
    backup_id='<backup_id>',
    validate=True
)

if result['status'] == 'validation_failed':
    print('[WARN] Validation failed, rolling back...')
    print(result['rollback'])
```

## Manual Rollback

Manually rollback a failed restore:

```python
from src.recovery_manager import RecoveryManager

manager = RecoveryManager()
rollback_result = manager.rollback_last_restore()
print(rollback_result)
```

## Validation Checks

The system validates each database after restore:

- **PostgreSQL**: Connection check + document count
- **Qdrant**: Connection check + collection count
- **Neo4j**: Connection check + node count
- **Redis**: Connection check + key count

## Error Handling

All restore operations include:

- Pre-restore validation
- Progress tracking
- Detailed error logging
- Automatic rollback on failure
- User-friendly error messages (ASCII-only)

## Best Practices

1. **Test Backups Regularly**: Verify backups can be restored
2. **Keep Multiple Backups**: Don't rely on a single backup
3. **Monitor Restore Operations**: Track restore progress
4. **Document Restores**: Keep records of all restore operations
5. **Use Validation**: Always validate after restore

## Troubleshooting

### Restore Fails

1. Check backup exists:
   ```python
   backup = manager.get_backup('<backup_id>')
   print(backup)
   ```

2. Verify backup files:
   ```bash
   ls -la backups/manual/backup_<timestamp>_<backup_id>/
   ```

3. Check database connections:
   ```bash
   docker ps | grep enhanced
   ```

### Validation Fails

1. Check individual database status:
   ```python
   results = manager.validate_restored_data(['postgresql', 'qdrant'])
   print(results)
   ```

2. Review validation errors:
   ```python
   for db, result in results.items():
       if not result.get('valid', True):
           print(f'[ERROR] {db}: {result.get("error")}')
   ```

### Rollback Issues

If rollback fails:

1. Check restore history:
   ```python
   restores = manager.list_restores()
   print(restores)
   ```

2. Manually restore from previous backup
3. Contact support with logs

## Recovery Time Objectives

- **Full Restore**: 10-30 minutes (depending on data size)
- **Single Database**: 2-10 minutes
- **Validation**: 1-2 minutes
- **Rollback**: 5-15 minutes

## Emergency Contacts

For critical recovery issues:
- Check logs: `logs/recovery_manager.log`
- Review backup metadata: `backups/metadata.db`
- Verify database status: `docker ps`

---

**Enhanced Cognee Recovery System** - Comprehensive disaster recovery for production deployments.
