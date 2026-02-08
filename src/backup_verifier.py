"""
Enhanced Cognee - Backup Verification System

Automated backup integrity verification for Enhanced Cognee backups.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import os
import sys
import json
import gzip
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lite_mode.sqlite_manager import SQLiteManager
from src.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class BackupVerifier:
    """Backup verification system for Enhanced Cognee."""

    def __init__(
        self,
        backup_manager: Optional[BackupManager] = None,
        alert_callback: Optional[callable] = None
    ):
        """Initialize backup verifier."""
        self.backup_manager = backup_manager or BackupManager()
        self.alert_callback = alert_callback
        logger.info("Backup Verifier initialized")

    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Verify a single backup."""
        logger.info(f"Verifying backup: {backup_id}")

        backup = self.backup_manager.get_backup(backup_id)

        if not backup:
            logger.error(f"Backup not found: {backup_id}")
            return {
                "backup_id": backup_id,
                "passed": False,
                "error": "Backup not found",
                "verified_at": datetime.now().isoformat()
            }

        verification_results = []
        all_passed = True

        for db, result in backup.get('backup_results', {}).items():
            if result.get('status') != 'success':
                continue

            db_result = self._verify_database_backup(db, result)
            verification_results.append(db_result)

            if not db_result['passed']:
                all_passed = False

        checksum_valid = self._verify_backup_checksum(backup)
        verification_results.append({
            "database": "overall",
            "check": "checksum",
            "passed": checksum_valid,
            "expected": backup.get('checksum'),
            "verified_at": datetime.now().isoformat()
        })

        if not checksum_valid:
            all_passed = False

        verification_result = {
            "backup_id": backup_id,
            "passed": all_passed,
            "verification_results": verification_results,
            "verified_at": datetime.now().isoformat()
        }

        self._store_verification_result(verification_result)

        if not all_passed and self.alert_callback:
            self.alert_callback(backup_id, verification_result)

        if all_passed:
            logger.info(f"Backup verified: {backup_id}")
        else:
            logger.warning(f"Backup verification failed: {backup_id}")

        return verification_result

    def _verify_database_backup(self, database: str, backup_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a specific database backup."""
        checks = []

        filepath = backup_result.get('file_path')
        exists = os.path.exists(filepath)

        checks.append({
            "check": "file_exists",
            "passed": exists,
            "filepath": filepath
        })

        if not exists:
            return {
                "database": database,
                "passed": False,
                "checks": checks,
                "error": "File not found"
            }

        file_size = os.path.getsize(filepath)
        expected_size = backup_result.get('file_size')
        size_match = file_size == expected_size

        checks.append({
            "check": "file_size",
            "passed": size_match,
            "expected": expected_size,
            "actual": file_size
        })

        integrity_ok = True
        if backup_result.get('compressed'):
            try:
                with gzip.open(filepath, 'rb') as f:
                    f.read(1)
            except Exception as e:
                integrity_ok = False
                logger.error(f"Decompression test failed for {database}: {e}")

        checks.append({
            "check": "integrity",
            "passed": integrity_ok,
            "compressed": backup_result.get('compressed')
        })

        all_passed = all(check['passed'] for check in checks)

        return {
            "database": database,
            "passed": all_passed,
            "checks": checks
        }

    def _verify_backup_checksum(self, backup: Dict[str, Any]) -> bool:
        """Verify overall backup checksum."""
        try:
            backup_path = Path(backup['backup_path'])

            if not backup_path.exists():
                return False

            sha256_hash = hashlib.sha256()

            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    filepath = os.path.join(root, file)
                    with open(filepath, "rb") as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)

            calculated_checksum = sha256_hash.hexdigest()
            expected_checksum = backup.get('checksum')

            return calculated_checksum == expected_checksum

        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False

    def _store_verification_result(self, result: Dict[str, Any]):
        """Store verification result in metadata database."""
        self.backup_manager.metadata_db.add_document(
            data_id=f"verification_{result['backup_id']}_{datetime.now().isoformat()}",
            data_text=json.dumps(result, indent=2),
            data_type="backup_verification",
            metadata=result,
            user_id="backup_system",
            agent_id="backup_verifier"
        )

    def verify_all_backups(self) -> List[Dict[str, Any]]:
        """Verify all backups."""
        logger.info("Verifying all backups...")

        backups = self.backup_manager.list_backups(limit=1000)
        results = []

        for backup in backups:
            backup_id = backup['backup_id']
            result = self.verify_backup(backup_id)
            results.append(result)

        self._generate_verification_report(results)

        return results

    def _generate_verification_report(self, results: List[Dict[str, Any]]):
        """Generate verification report."""
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        failed = total - passed

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_backups": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
            "failures": [r['backup_id'] for r in results if not r['passed']]
        }

        report_path = Path("backups") / "verification_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Verification report saved: {report_path}")
        logger.info(f"Total: {total}, Passed: {passed}, Failed: {failed}")
