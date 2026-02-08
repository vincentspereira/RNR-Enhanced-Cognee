#!/bin/bash
# Enhanced Cognee - Restore All Databases
#
# Restores all databases from the specified backup.
# Usage: ./scripts/restore_all.sh <backup_id>
#
# Author: Enhanced Cognee Team
# Version: 1.0.0

set -e

# Get backup ID from command line
BACKUP_ID=$1

if [ -z "$BACKUP_ID" ]; then
    echo "[ERROR] Usage: $0 <backup_id>"
    exit 1
fi

echo "[INFO] Starting restore from backup: $BACKUP_ID"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "[INFO] Activating virtual environment..."
    source venv/bin/activate
fi

# Run Python restore script
python -c "
import sys
sys.path.insert(0, '.')

from src.recovery_manager import RecoveryManager
import logging

logging.basicConfig(level=logging.INFO)

manager = RecoveryManager()
result = manager.restore_from_backup('$BACKUP_ID')

if result['status'] == 'success':
    print('[OK] Restore completed successfully')
    print(f\"[INFO] Databases restored: {result['databases_restored']}\")
    sys.exit(0)
else:
    print('[ERROR] Restore failed')
    print(f\"[ERROR] {result.get('error', 'Unknown error')}\")
    sys.exit(1)
"
