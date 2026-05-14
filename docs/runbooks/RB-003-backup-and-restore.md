# Runbook RB-003: Backup and Restore

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Operators and developers

---

## Overview

Enhanced Cognee's BackupManager covers all four databases:

- PostgreSQL: pg_dump (SQL format, gzip-compressed)
- Qdrant: snapshot API (collection-level snapshots)
- Neo4j: backup API or export via cypher-shell
- Redis: RDB snapshot (BGSAVE)

Backups are stored in the backups/ directory at the project root and tracked in a
SQLite metadata database at backups/metadata.db.

---

## Creating a Backup

Call the create_backup MCP tool from your MCP client:

    Tool: create_backup
    Parameters: (none required; all are optional)

The tool runs backup operations for all available databases, compresses the output,
and returns a backup_id:

    [OK] Backup created: backup_20260213_140532
    PostgreSQL:  [OK] 14.2 MB
    Qdrant:      [OK] 3.1 MB (2 collections)
    Neo4j:       [OK] 1.8 MB
    Redis:       [OK] 0.4 MB
    Total size:  19.5 MB

Note the backup_id. You will need it for verification and restore.

---

## Verifying a Backup

Call verify_backup with the backup_id returned from create_backup:

    Tool: verify_backup
    Parameters:
      backup_id: "backup_20260213_140532"

The tool confirms that backup files are present, checksums match, and the backup
metadata is intact:

    [OK] Backup backup_20260213_140532 verified
    [OK] PostgreSQL checksum valid
    [OK] Qdrant snapshot present
    [OK] Neo4j export present
    [OK] Redis RDB present

A [FAIL] result on any line means that file is corrupt or missing. Re-run
create_backup to produce a fresh backup before proceeding.

---

## Restoring from a Backup

Warning: restore overwrites current database contents. Take a fresh backup of the
current state before restoring from an older one.

    Tool: restore_backup
    Parameters:
      backup_id: "backup_20260213_140532"

The tool stops writes, restores each database in sequence, and restarts connections:

    [INFO] Restoring backup_20260213_140532 ...
    [OK] PostgreSQL restored
    [OK] Qdrant restored (2 collections)
    [OK] Neo4j restored
    [OK] Redis restored
    [DONE] Restore complete. Run enhanced-cognee health to verify.

Run enhanced-cognee health after restore to confirm all databases are reachable.

---

## Rolling Back a Failed Restore

If restore_backup fails partway through (for example, Neo4j restoration fails after
PostgreSQL has already been overwritten), call rollback_restore:

    Tool: rollback_restore
    Parameters:
      backup_id: "backup_20260213_140532"

The tool restores the pre-restore snapshot that BackupManager takes automatically
before beginning any restore operation:

    [OK] Pre-restore snapshot applied
    [DONE] Rollback complete

If rollback_restore also fails, contact the maintainers and provide the contents
of backups/metadata.db and the server log from the restore attempt.

---

## Backup Retention

By default, BackupManager retains:
- Daily backups for 7 days
- Weekly backups for 4 weeks
- Monthly backups for 12 months

Older backups are rotated automatically. To change retention periods, edit the
BACKUP_DAILY_RETENTION, BACKUP_WEEKLY_RETENTION, and BACKUP_MONTHLY_RETENTION
values in .env.

---

## Scheduled Backups

To schedule automatic daily backups, use the schedule_task MCP tool:

    Tool: schedule_task
    Parameters:
      task: "backup"
      cron: "0 2 * * *"     # daily at 02:00

Scheduled tasks are managed by the maintenance_scheduler module and appear in the
output of list_tasks.
