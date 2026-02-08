# Enhanced Cognee - Rollback Procedures

Procedures for rolling back failed operations in Enhanced Cognee.

## Overview

Enhanced Cognee includes comprehensive rollback capabilities:
- Automatic rollback on failed restore
- Manual rollback of operations
- Transaction-based operations
- Undo manager for critical operations
- Audit trail for all changes

## Rollback Scenarios

### 1. Failed Backup Restore

Automatic rollback when restore validation fails:

```bash
# Restore with validation
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.restore_from_backup(
    backup_id='abc-123',
    validate=True  # Triggers rollback on validation failure
)
print(result)
"
```

If validation fails:
1. Automatic rollback initiated
2. Previous state restored
3. Error logged with details
4. User notified of failure

### 2. Manual Restore Rollback

Manually rollback last restore:

```bash
# Rollback last restore
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.rollback_last_restore()
print(result)
"
```

### 3. Deduplication Undo

Undo last deduplication:

```bash
# Using MCP tool
python -c "
from src.scheduled_deduplication import ScheduledDeduplication
dedup = ScheduledDeduplication(postgres_pool, qdrant_client)
result = await dedup.undo_deduplication('deduplication_id')
print(result)
"
```

**WARNING**: Deduplication undo is limited. Requires backup for full restore.

### 4. Memory Operation Undo

Undo memory operations using undo manager:

```bash
# Using MCP tool
python -c "
from src.undo_manager import UndoManager
undo = UndoManager(postgres_pool)

# List undoable operations
operations = undo.list_undoable_operations(user_id='default')

# Undo last operation
result = undo.undo_last(user_id='default')
print(result)
"
```

## Rollback Procedures by Operation

### Backup Restore Rollback

**Trigger**: Validation failure after restore

**Process**:
1. Validation detects data inconsistency
2. Automatic rollback triggered
3. Restore from previous backup (if available)
4. Mark restore as failed
5. Log detailed error

**Manual Procedure**:
```bash
# 1. Identify failed restore
restores = manager.list_restores()
failed_restore = [r for r in restores if r['status'] == 'validation_failed']

# 2. Rollback
rollback_result = manager.rollback_last_restore()

# 3. Verify system state
validation = manager.validate_restored_data(['postgresql', 'qdrant'])
print(validation)
```

### Deduplication Rollback

**Trigger**: User request after incorrect deduplication

**Process**:
1. Identify deduplication to undo
2. Retrieve deleted memories from backup
3. Restore deleted memories
4. Remove merged memory
5. Update audit trail

**Manual Procedure**:
```bash
# 1. Find deduplication
report = dedup.deduplication_report()
deduplication_id = report['recent_deduplications'][0]['deduplication_id']

# 2. Undo (limited - may require backup restore)
result = await dedup.undo_deduplication(deduplication_id)

# 3. If limited, restore from backup
backup_id = get_backup_before_deduplication(deduplication_id)
manager.restore_from_backup(backup_id)
```

### Summarization Rollback

**Trigger**: Incorrect or poor quality summaries

**Process**:
1. Identify memories to restore
2. Retrieve original from metadata
3. Replace summary with original
4. Update metadata
5. Track restoration

**Manual Procedure**:
```sql
-- Find summarized memories
SELECT id, content, metadata->>'original_length' as original_length
FROM shared_memory.documents
WHERE metadata->>'summarized' = 'true'
AND created_at > '2025-02-01';

-- Restore from backup if needed
-- Or restore individual memories
```

### Memory Deletion Rollback

**Trigger**: Accidental memory deletion

**Process**:
1. Check undo manager for operation
2. Restore from recycle bin if available
3. Or restore from backup

**Manual Procedure**:
```bash
# 1. Check undo manager
from src.undo_manager import UndoManager
undo = UndoManager(postgres_pool)

# 2. List recent deletions
deletions = undo.list_operations_by_type('delete')

# 3. Restore
for deletion in deletions:
    result = undo.undo_operation(deletion['operation_id'])
```

## Backup Strategy for Rollback

### Pre-Operation Backups

Create backup before major operations:

```bash
# Create backup before operation
backup_id = manager.create_backup(
    backup_type='manual',
    description='Pre-operation backup before deduplication'
)

# Perform operation
operation_result = perform_operation()

# If operation fails, restore
if operation_result['status'] == 'failed':
    manager.restore_from_backup(backup_id)
```

### Point-in-Time Recovery

For critical operations, use point-in-time recovery:

1. **PostgreSQL**: WAL archiving for PITR
2. **Qdrant**: Snapshots at regular intervals
3. **Neo4j**: Transaction logs
4. **Redis**: AOF persistence

## Rollback Verification

After rollback, verify system state:

```bash
# Verify all databases
validation = manager.validate_restored_data([
    'postgresql',
    'qdrant',
    'neo4j',
    'redis'
])

print(validation)
# Expected: {"all_valid": true, ...}
```

## Emergency Rollback

### Complete System Restore

If rollback fails, restore entire system:

```bash
# 1. Stop all services
docker stop postgres-enhanced qdrant-enhanced neo4j-enhanced redis-enhanced

# 2. Identify last known good backup
backups = manager.list_backups(backup_type='daily')
last_good = backups[0]

# 3. Restore all databases
manager.restore_from_backup(
    backup_id=last_good['backup_id'],
    validate=False  # Skip validation for emergency restore
)

# 4. Start services
docker start postgres-enhanced qdrant-enhanced neo4j-enhanced redis-enhanced

# 5. Verify
manager.validate_restored_data(['postgresql', 'qdrant', 'neo4j', 'redis'])
```

### Emergency Recovery Checklist

- [ ] Stop all Enhanced Cognee services
- [ ] Identify last known good backup
- [ ] Verify backup integrity
- [ ] Restore all databases
- [ ] Restart services
- [ ] Verify system health
- [ ] Run diagnostics
- [ ] Monitor for errors

## Rollback Monitoring

### Track Rollback Operations

```bash
# View rollback history
restores = manager.list_restores()
rollbacks = [r for r in restores if 'rollback' in r]

for rollback in rollbacks:
    print(f"{rollback['restore_id']}: {rollback['status']}")
```

### Alert on Rollback

Configure alerts for rollback operations:

```json
// automation_config.json
{
  "notifications": {
    "on_rollback": true,
    "alert_channels": ["email", "slack"],
    "severity": "critical"
  }
}
```

## Best Practices

1. **Always Backup Before Major Operations**: Create pre-operation backup
2. **Test Rollback Procedures**: Regularly test rollback in staging
3. **Document Rollback Steps**: Keep updated runbooks
4. **Monitor Rollback Success**: Track rollback success rate
5. **Use Transactions**: Enable transactions for all operations
6. **Verify After Rollback**: Always validate after rollback
7. **Have Emergency Plan**: Know emergency restore procedure

## Troubleshooting

### Rollback Fails

**Problem**: Rollback operation fails

**Solutions**:
```bash
# 1. Check backup exists
backup = manager.get_backup(backup_id)

# 2. Verify backup files
ls -la backups/manual/backup_*/

# 3. Try manual restore
manager.restore_postgres(backup_id)
manager.restore_qdrant(backup_id)
```

### Validation Fails After Rollback

**Problem**: System state invalid after rollback

**Solutions**:
```bash
# 1. Try different backup
backups = manager.list_backups()
for backup in backups:
    result = manager.restore_from_backup(backup['backup_id'])
    if result['status'] == 'success':
        break

# 2. Or use emergency restore
# (see Emergency Rollback section)
```

## Next Steps

- Read [Disaster Recovery Guide](DISASTER_RECOVERY.md)
- Review [Backup & Restore](BACKUP_RESTORE_GUIDE.md)
- Check [Emergency Recovery](EMERGENCY_RECOVERY.md)

---

**Rollback Procedures** - Safely undo operations when things go wrong.
