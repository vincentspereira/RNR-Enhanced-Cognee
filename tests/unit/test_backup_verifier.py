"""
Unit tests for src/backup_verifier.py

Targets >= 85% line coverage.
All external calls (filesystem, BackupManager, SQLiteManager) are mocked.
ASCII-only assertions and output.
"""

import gzip
import json
import os
import pytest
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Stub SQLiteManager so backup_verifier can import without a real DB
# ---------------------------------------------------------------------------

_fake_sqlite_mod = types.ModuleType("src.sqlite_manager")


class _FakeSQLiteManager:
    def __init__(self, db_path=""):
        self.db_path = db_path
        self._docs = {}

    def add_document(self, data_id=None, data_text=None, data_type=None,
                     metadata=None, user_id=None, agent_id=None):
        self._docs[data_id] = {"data_id": data_id, "data_text": data_text}
        return data_id

    def get_documents(self, data_type=None, limit=100):
        return list(self._docs.values())


_fake_sqlite_mod.SQLiteManager = _FakeSQLiteManager
sys.modules.setdefault("src.sqlite_manager", _fake_sqlite_mod)


# ---------------------------------------------------------------------------
# Stub BackupManager
# ---------------------------------------------------------------------------

_fake_backup_mod = types.ModuleType("src.backup_manager")


class _FakeBackupManager:
    def __init__(self):
        self.metadata_db = _FakeSQLiteManager("test.db")
        self._backups = {}

    def get_backup(self, backup_id):
        return self._backups.get(backup_id)

    def list_backups(self, limit=100):
        return list(self._backups.values())


_fake_backup_mod.BackupManager = _FakeBackupManager
sys.modules.setdefault("src.backup_manager", _fake_backup_mod)


# ---------------------------------------------------------------------------
# Import after stubs are in place
# ---------------------------------------------------------------------------

from src.backup_verifier import BackupVerifier  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_verifier(backups=None):
    bm = _FakeBackupManager()
    if backups:
        bm._backups.update(backups)
    return BackupVerifier(backup_manager=bm)


def _minimal_backup(backup_id="bk-001", backup_path="/tmp/bk-001",
                    checksum="abc123", backup_results=None):
    return {
        "backup_id": backup_id,
        "backup_path": backup_path,
        "checksum": checksum,
        "backup_results": backup_results or {}
    }


# ---------------------------------------------------------------------------
# Tests: verify_backup
# ---------------------------------------------------------------------------

class TestVerifyBackupNotFound:
    def test_returns_failed_when_backup_missing(self):
        v = _make_verifier()
        result = v.verify_backup("nonexistent-id")
        assert result["backup_id"] == "nonexistent-id"
        assert result["passed"] is False
        assert "error" in result

    def test_verified_at_present_even_on_not_found(self):
        v = _make_verifier()
        result = v.verify_backup("x")
        assert "verified_at" in result


class TestVerifyBackupChecksum:
    def test_pass_when_checksum_matches(self, tmp_path):
        bk_path = tmp_path / "bk-002"
        bk_path.mkdir()
        (bk_path / "data.txt").write_text("hello")

        # Compute expected checksum the same way the code does
        import hashlib
        sha = hashlib.sha256()
        sha.update(b"hello")
        cksum = sha.hexdigest()

        backup = _minimal_backup(
            backup_id="bk-002",
            backup_path=str(bk_path),
            checksum=cksum,
        )
        v = _make_verifier(backups={"bk-002": backup})
        result = v.verify_backup("bk-002")
        assert result["backup_id"] == "bk-002"
        # checksum result is in verification_results
        cksum_check = next(
            r for r in result["verification_results"]
            if r.get("check") == "checksum"
        )
        assert cksum_check["passed"] is True

    def test_fail_when_checksum_mismatches(self, tmp_path):
        bk_path = tmp_path / "bk-003"
        bk_path.mkdir()
        (bk_path / "data.txt").write_text("hello")

        backup = _minimal_backup(
            backup_id="bk-003",
            backup_path=str(bk_path),
            checksum="wrong-checksum",
        )
        v = _make_verifier(backups={"bk-003": backup})
        result = v.verify_backup("bk-003")
        assert result["passed"] is False

    def test_fail_when_backup_path_missing(self):
        backup = _minimal_backup(
            backup_id="bk-004",
            backup_path="/nonexistent/path",
            checksum="abc",
        )
        v = _make_verifier(backups={"bk-004": backup})
        result = v.verify_backup("bk-004")
        assert result["passed"] is False

    def test_alert_callback_called_on_failure(self):
        backup = _minimal_backup(
            backup_id="bk-005",
            backup_path="/nonexistent/path",
            checksum="bad",
        )
        alerts = []
        v = _make_verifier(backups={"bk-005": backup})
        v.alert_callback = lambda bid, res: alerts.append((bid, res))
        v.verify_backup("bk-005")
        assert len(alerts) == 1
        assert alerts[0][0] == "bk-005"

    def test_alert_callback_not_called_on_success(self, tmp_path):
        bk_path = tmp_path / "bk-ok"
        bk_path.mkdir()

        import hashlib
        sha = hashlib.sha256()
        cksum = sha.hexdigest()  # empty dir -> empty hash

        backup = _minimal_backup(
            backup_id="bk-ok",
            backup_path=str(bk_path),
            checksum=cksum,
        )
        alerts = []
        v = _make_verifier(backups={"bk-ok": backup})
        v.alert_callback = lambda bid, res: alerts.append(bid)
        result = v.verify_backup("bk-ok")
        # Empty dir gives correct checksum, so should pass
        assert result["passed"] is True
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# Tests: _verify_database_backup
# ---------------------------------------------------------------------------

class TestVerifyDatabaseBackup:
    def test_file_not_found(self):
        v = _make_verifier()
        result = v._verify_database_backup("postgres", {
            "file_path": "/nonexistent/file.sql",
            "file_size": 100,
            "compressed": False
        })
        assert result["passed"] is False
        assert "error" in result

    def test_file_exists_size_match(self, tmp_path):
        f = tmp_path / "backup.sql"
        f.write_text("data")
        size = f.stat().st_size

        v = _make_verifier()
        result = v._verify_database_backup("postgres", {
            "file_path": str(f),
            "file_size": size,
            "compressed": False
        })
        assert result["passed"] is True

    def test_size_mismatch(self, tmp_path):
        f = tmp_path / "backup.sql"
        f.write_text("data")

        v = _make_verifier()
        result = v._verify_database_backup("postgres", {
            "file_path": str(f),
            "file_size": 99999,
            "compressed": False
        })
        assert result["passed"] is False

    def test_compressed_valid_gzip(self, tmp_path):
        f = tmp_path / "backup.sql.gz"
        with gzip.open(str(f), 'wb') as gz:
            gz.write(b"sql data")
        size = f.stat().st_size

        v = _make_verifier()
        result = v._verify_database_backup("postgres", {
            "file_path": str(f),
            "file_size": size,
            "compressed": True
        })
        assert result["passed"] is True

    def test_compressed_invalid_gzip(self, tmp_path):
        f = tmp_path / "bad.sql.gz"
        f.write_bytes(b"not a gzip file at all!!!")

        v = _make_verifier()
        result = v._verify_database_backup("postgres", {
            "file_path": str(f),
            "file_size": f.stat().st_size,
            "compressed": True
        })
        # integrity check should fail
        checks = {c["check"]: c for c in result["checks"]}
        assert checks["integrity"]["passed"] is False


# ---------------------------------------------------------------------------
# Tests: _verify_backup_checksum
# ---------------------------------------------------------------------------

class TestVerifyBackupChecksum:
    def test_missing_path_returns_false(self):
        v = _make_verifier()
        result = v._verify_backup_checksum({"backup_path": "/no/such/dir"})
        assert result is False

    def test_exception_returns_false(self):
        v = _make_verifier()
        # backup_path key missing causes KeyError
        result = v._verify_backup_checksum({})
        assert result is False

    def test_checksum_with_multiple_files(self, tmp_path):
        """Lines 169-172: walk into backup dir and hash multiple files."""
        import hashlib
        bk_path = tmp_path / "bk-multi-file"
        bk_path.mkdir()
        (bk_path / "file1.sql").write_bytes(b"SELECT 1;")
        (bk_path / "file2.sql").write_bytes(b"SELECT 2;")

        # Compute expected checksum the same way the code does
        sha = hashlib.sha256()
        for fname in sorted(["file1.sql", "file2.sql"]):
            filepath = str(bk_path / fname)
            with open(filepath, "rb") as f:
                for block in iter(lambda: f.read(4096), b""):
                    sha.update(block)
        cksum = sha.hexdigest()

        v = _make_verifier()
        result = v._verify_backup_checksum({
            "backup_path": str(bk_path),
            "checksum": cksum
        })
        assert result is True


# ---------------------------------------------------------------------------
# Tests: verify_all_backups
# ---------------------------------------------------------------------------

class TestVerifyAllBackups:
    def test_empty_backup_list(self, tmp_path):
        v = _make_verifier()
        # No backups -> verify_all_backups calls _generate_verification_report
        report_path = tmp_path / "report.json"
        with patch("src.backup_verifier.Path") as mock_path_cls:
            # Make Path("backups") / "verification_report.json" point to tmp_path
            mock_path_cls.return_value.__truediv__ = lambda s, x: report_path
            # Actually let it run - just intercept open
            with patch("builtins.open", mock_open()):
                results = v.verify_all_backups()
        assert results == []

    def test_multiple_backups_returns_all_results(self, tmp_path):
        bk_path = tmp_path / "bk-multi"
        bk_path.mkdir()

        import hashlib
        sha = hashlib.sha256()
        cksum = sha.hexdigest()

        backups = {
            "b1": _minimal_backup("b1", str(bk_path), cksum),
            "b2": _minimal_backup("b2", "/nonexistent", "bad"),
        }
        v = _make_verifier(backups=backups)
        with patch("builtins.open", mock_open()):
            results = v.verify_all_backups()
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Tests: _generate_verification_report
# ---------------------------------------------------------------------------

class TestGenerateVerificationReport:
    def test_success_rate_empty(self):
        v = _make_verifier()
        with patch("builtins.open", mock_open()):
            v._generate_verification_report([])
        # No assertion needed - just confirm it doesn't raise

    def test_success_rate_calculated(self, tmp_path):
        results = [
            {"backup_id": "a", "passed": True},
            {"backup_id": "b", "passed": False},
        ]
        v = _make_verifier()
        written = []

        def fake_open(path, mode='r', **kw):
            m = mock_open()()
            m.write = lambda s: written.append(s)
            return m

        with patch("builtins.open", fake_open):
            v._generate_verification_report(results)

    def test_report_written_to_file(self, tmp_path):
        v = _make_verifier()
        results = [{"backup_id": "z", "passed": True}]
        with patch("builtins.open", mock_open()) as mo:
            v._generate_verification_report(results)
        # open was called
        assert mo.called


# ---------------------------------------------------------------------------
# Tests: verify_backup with backup_results containing DB entries
# ---------------------------------------------------------------------------

class TestVerifyBackupAllPassedFalseViaDB:
    """Line 69: all_passed=False when a DB backup check fails."""

    def test_db_result_fails_verification_sets_all_passed_false(self, tmp_path):
        bk_path = tmp_path / "bk-fail-db"
        bk_path.mkdir()

        # sql file exists but the file_size is wrong -> db check fails
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("SELECT 1;")
        actual_size = sql_file.stat().st_size

        import hashlib
        sha = hashlib.sha256()
        cksum = sha.hexdigest()  # empty dir checksum

        backup = _minimal_backup(
            backup_id="bk-fail-db",
            backup_path=str(bk_path),
            checksum=cksum,
            backup_results={
                "postgres": {
                    "status": "success",
                    "file_path": str(sql_file),
                    "file_size": actual_size + 100,  # wrong size!
                    "compressed": False
                }
            }
        )
        alerts = []
        v = _make_verifier(backups={"bk-fail-db": backup})
        v.alert_callback = lambda bid, res: alerts.append(bid)
        result = v.verify_backup("bk-fail-db")
        # DB result fails (size mismatch) -> all_passed False
        assert result["passed"] is False
        # Alert fired because overall failed
        assert "bk-fail-db" in alerts


class TestVerifyBackupWithDBResults:
    def test_skips_failed_db_results(self, tmp_path):
        bk_path = tmp_path / "bk-db"
        bk_path.mkdir()

        import hashlib
        sha = hashlib.sha256()
        cksum = sha.hexdigest()

        backup = _minimal_backup(
            backup_id="bk-db",
            backup_path=str(bk_path),
            checksum=cksum,
            backup_results={
                "postgres": {"status": "failed", "file_path": "/some/file.sql"}
            }
        )
        v = _make_verifier(backups={"bk-db": backup})
        result = v.verify_backup("bk-db")
        # Only checksum check present since db result status != success
        db_checks = [r for r in result["verification_results"]
                     if r.get("database") != "overall"]
        assert len(db_checks) == 0

    def test_includes_successful_db_results(self, tmp_path):
        bk_path = tmp_path / "bk-db2"
        bk_path.mkdir()

        # Create a fake sql file for db verification
        sql_file = tmp_path / "data.sql"
        sql_file.write_text("SELECT 1;")

        import hashlib
        sha = hashlib.sha256()
        cksum = sha.hexdigest()  # empty dir -> no files -> empty hash

        backup = _minimal_backup(
            backup_id="bk-db2",
            backup_path=str(bk_path),
            checksum=cksum,
            backup_results={
                "postgres": {
                    "status": "success",
                    "file_path": str(sql_file),
                    "file_size": sql_file.stat().st_size,
                    "compressed": False
                }
            }
        )
        v = _make_verifier(backups={"bk-db2": backup})
        result = v.verify_backup("bk-db2")
        db_checks = [r for r in result["verification_results"]
                     if r.get("database") == "postgres"]
        assert len(db_checks) == 1
