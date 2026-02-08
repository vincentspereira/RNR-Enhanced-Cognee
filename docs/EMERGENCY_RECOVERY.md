# Enhanced Cognee - Emergency Recovery Procedures

Emergency procedures for critical Enhanced Cognee failures.

## Overview

This document provides emergency recovery procedures for critical failures:
- Complete system failure
- Database corruption
- Data loss scenarios
- Service unavailability
- Catastrophic failures

## Emergency Contacts

For critical issues:
1. Check system logs: `logs/`
2. Review backup status: `backups/`
3. Contact database administrator
4. Follow procedures below

## Emergency Scenarios

### Scenario 1: Complete System Failure

**Symptoms**:
- All databases unreachable
- Services won't start
- No responses to queries

**Immediate Actions**:

```bash
# 1. Check Docker containers
docker ps -a | grep enhanced

# 2. Check system resources
free -h
df -h
top

# 3. Check database logs
docker logs postgres-enhanced --tail 100
docker logs qdrant-enhanced --tail 100
docker logs neo4j-enhanced --tail 100
docker logs redis-enhanced --tail 100
```

**Recovery Steps**:

```bash
# 1. Stop all services
docker-compose -f docker/docker-compose-enhanced-cognee.yml down

# 2. Restart services one by one
docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d postgres-enhanced
sleep 30

docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d qdrant-enhanced
sleep 15

docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d neo4j-enhanced
sleep 15

docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d redis-enhanced
sleep 10

# 3. Verify all services
docker ps | grep enhanced

# 4. Test connectivity
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
validation = manager.validate_restored_data(['postgresql', 'qdrant', 'neo4j', 'redis'])
print(validation)
"
```

### Scenario 2: Database Corruption

**Symptoms**:
- Queries fail with corruption errors
- Inconsistent results
- Database won't start

**Immediate Actions**:

```bash
# 1. Stop affected service
docker stop postgres-enhanced

# 2. Check corruption
docker logs postgres-enhanced --tail 200 | grep -i corrupt

# 3. Identify last good backup
python -c "
from src.backup_manager import BackupManager
manager = BackupManager()
backups = manager.list_backups(backup_type='daily', limit=7)
for backup in backups:
    print(f\"{backup['created_at']}: {backup['backup_id']}\")
"
```

**Recovery Steps**:

```bash
# 1. Stop all Enhanced services
docker-compose -f docker/docker-compose-enhanced-cognee.yml down

# 2. Remove corrupted database container
docker rm postgres-enhanced

# 3. Restore from last good backup
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.restore_from_backup(
    backup_id='LAST_GOOD_BACKUP_ID',
    databases=['postgresql'],
    validate=True
)
print(result)
"

# 4. Restart services
docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d
```

### Scenario 3: Data Loss

**Symptoms**:
- Missing records
- Incorrect data counts
- Data inconsistencies

**Immediate Actions**:

```bash
# 1. Assess data loss
python -c "
import asyncio
from asyncpg import create_pool

async def check():
    pool = await create_pool(
        host='localhost',
        port=25432,
        database='cognee_db',
        user='cognee_user',
        password='cognee_password'
    )
    async with pool.acquire() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM shared_memory.documents')
        print(f'Document count: {count}')
    await pool.close()

asyncio.run(check())
"

# 2. Identify when data was lost
python -c "
from src.backup_manager import BackupManager
manager = BackupManager()
backups = manager.list_backups()
for backup in backups[:5]:
    print(f\"{backup['created_at']}: {backup['total_size_bytes']} bytes\")
"
```

**Recovery Steps**:

```bash
# 1. Stop writes to prevent further loss
# (Stop Enhanced Cognee MCP server)

# 2. Identify backup before data loss
# Compare document counts in backups

# 3. Restore from identified backup
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.restore_from_backup(
    backup_id='BACKUP_BEFORE_LOSS',
    validate=True
)
print(result)
"

# 4. Verify data restored
# (Re-run count check from step 1)
```

### Scenario 4: Service Unavailability

**Symptoms**:
- Connection refused
- Timeout errors
- Service unreachable

**Immediate Actions**:

```bash
# 1. Check if service is running
docker ps | grep enhanced

# 2. Check service logs
docker logs postgres-enhanced --tail 50
docker logs qdrant-enhanced --tail 50

# 3. Check port availability
netstat -tuln | grep -E '25432|26333|27687|26379'
```

**Recovery Steps**:

```bash
# 1. Restart affected service
docker restart postgres-enhanced

# 2. If restart fails, recreate service
docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d --force-recreate postgres-enhanced

# 3. Verify service
docker ps | grep postgres-enhanced
```

## Emergency Restore Procedure

### Complete System Restore

When all else fails, restore entire system:

```bash
#!/bin/bash
# Emergency restore script

echo "=== EMERGENCY RESTORE ==="
echo "This will restore the entire system from backup"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 1
fi

# 1. Stop all services
echo "Stopping all services..."
docker-compose -f docker/docker-compose-enhanced-cognee.yml down

# 2. Get latest backup
echo "Finding latest backup..."
BACKUP_ID=$(python -c "
from src.backup_manager import BackupManager
manager = BackupManager()
backups = manager.list_backups(backup_type='daily', limit=1)
if backups:
    print(backups[0]['backup_id'])
else:
    print('ERROR')
")

if [ "$BACKUP_ID" == "ERROR" ]; then
    echo "ERROR: No backup found!"
    exit 1
fi

echo "Using backup: $BACKUP_ID"
read -p "Continue? (yes/no): " confirm2

if [ "$confirm2" != "yes" ]; then
    echo "Aborted"
    exit 1
fi

# 3. Restore all databases
echo "Restoring databases..."
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
result = manager.restore_from_backup(
    backup_id='$BACKUP_ID',
    validate=True
)
print(result)
"

# 4. Start all services
echo "Starting services..."
docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d

# 5. Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# 6. Verify
echo "Verifying system..."
python -c "
from src.recovery_manager import RecoveryManager
manager = RecoveryManager()
validation = manager.validate_restored_data(['postgresql', 'qdrant', 'neo4j', 'redis'])
print(validation)
"

echo "=== RESTORE COMPLETE ==="
```

## Disaster Recovery Checklist

Use this checklist during emergency recovery:

### Phase 1: Assessment (5 minutes)
- [ ] Identify failure scope
- [ ] Check all service status
- [ ] Review logs for errors
- [ ] Identify affected data
- [ ] Estimate data loss

### Phase 2: Containment (10 minutes)
- [ ] Stop all writes
- [ ] Isolate affected services
- [ ] Preserve evidence (logs, state)
- [ ] Notify stakeholders

### Phase 3: Recovery Planning (15 minutes)
- [ ] Identify last good backup
- [ ] Plan recovery steps
- [ ] Estimate recovery time
- [ ] Assign responsibilities

### Phase 4: Execution (30-60 minutes)
- [ ] Restore from backup
- [ ] Verify data integrity
- [ ] Restart services
- [ ] Test connectivity
- [ ] Validate functionality

### Phase 5: Verification (15 minutes)
- [ ] Run health checks
- [ ] Verify data counts
- [ ] Test critical operations
- [ ] Monitor for errors

### Phase 6: Documentation (ongoing)
- [ ] Document incident
- [ ] Timeline of events
- [ ] Root cause analysis
- [ ] Preventive measures

## Emergency Contacts

### Internal
- System Administrator: [Contact]
- Database Administrator: [Contact]
- DevOps Engineer: [Contact]

### External
- Docker Support: https://docs.docker.com/support/
- PostgreSQL: https://www.postgresql.org/support/
- Qdrant: https://qdrant.tech/contact/
- Neo4j: https://neo4j.com/support/
- Redis: https://redis.io/support/

## Post-Incident Actions

After emergency recovery:

1. **Root Cause Analysis**: Investigate why failure occurred
2. **Preventive Measures**: Implement safeguards
3. **Update Procedures**: Revise recovery procedures
4. **Training**: Train team on lessons learned
5. **Monitoring**: Enhance monitoring and alerts
6. **Testing**: Test recovery procedures regularly

## Prevention

Prevent emergencies by:

1. **Regular Backups**: Automated daily backups
2. **Monitoring**: Proactive monitoring and alerts
3. **Testing**: Regular disaster recovery drills
4. **Documentation**: Keep procedures updated
5. **Redundancy**: Use high-availability setup when possible
6. **Capacity Planning**: Monitor resource usage

## Next Steps

- Read [Disaster Recovery Guide](DISASTER_RECOVERY.md)
- Review [Rollback Procedures](ROLLBACK_PROCEDURES.md)
- Check [Backup & Restore](BACKUP_RESTORE_GUIDE.md)

---

**Emergency Recovery** - Be prepared for the worst with these emergency procedures.
