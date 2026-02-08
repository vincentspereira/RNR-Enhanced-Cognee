#!/bin/bash
################################################################################
# Enhanced Cognee - Manual Backup Script
#
# Manually backup all databases in the Enhanced Cognee stack.
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "[INFO] Enhanced Cognee - Manual Backup"
echo "======================================="
echo ""

# Run backup manager
python -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/..')

from src.backup_manager import BackupManager
import logging

logging.basicConfig(level=logging.INFO)

manager = BackupManager()
backup_id = manager.create_backup(
    backup_type='manual',
    databases=['postgresql', 'qdrant', 'neo4j', 'redis'],
    compress=True,
    description='Manual backup'
)

print(f'[OK] Backup created: {backup_id}')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "[OK] Backup complete!"
    echo ""
    echo "To list backups:"
    echo "  python -c 'from src.backup_manager import BackupManager; print(BackupManager().list_backups())'"
    echo ""
else
    echo "[ERR] Backup failed!"
    exit 1
fi
