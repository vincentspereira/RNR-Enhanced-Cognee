"""
Unit tests for src/recovery_manager.py

Coverage targets:
- RecoveryManager.__init__ / _load_config
- restore_from_backup: success, backup not found, per-db failure+rollback,
  validation failure+rollback, outer exception+rollback
- restore_database: dispatcher for all four databases, unknown database
- restore_postgres: success (plain and gzip), file not found, psql failure, timeout
- restore_qdrant: success (plain and gzip), file not found, HTTP failure
- restore_neo4j: JSON import, native backup skip, file not found
- restore_redis: success (plain and gzip), docker failure, file not found
- validate_restored_data: per-db success, per-db failure, unknown db skipped
- _validate_postgres / _validate_qdrant / _validate_neo4j / _validate_redis
- rollback_last_restore: success, nothing to rollback, exception
- get_backup: found, not found
- list_restores: populated, empty
- _store_restore_metadata
"""

import os
import sys
import gzip
import json
import shutil
import subprocess
import pytest
import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import (
    patch, MagicMock, AsyncMock, Mock, call
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ---------------------------------------------------------------------------
# Snapshot sys.modules BEFORE we install stubs, so we can restore later
# ---------------------------------------------------------------------------

_MODULES_TO_PROTECT = ["src.sqlite_manager", "src.recovery_manager"]
_SYS_MODULES_SNAPSHOT = {k: sys.modules.get(k) for k in _MODULES_TO_PROTECT}


@pytest.fixture(scope="module", autouse=True)
def _restore_sys_modules_after_module():
    """Restore stubbed sys.modules entries so downstream tests see real classes."""
    yield
    for k, original in _SYS_MODULES_SNAPSHOT.items():
        if original is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = original


# ---------------------------------------------------------------------------
# Stub out SQLiteManager before recovery_manager imports it
# ---------------------------------------------------------------------------
import types

_fake_sqlite_module = types.ModuleType("src.sqlite_manager")


class _FakeSQLiteManager:
    """In-memory stand-in for SQLiteManager."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._docs: dict = {}  # data_id -> row dict

    def add_document(self, data_id=None, data_text=None, data_type=None,
                     metadata=None, user_id=None, agent_id=None):
        row_id = data_id or "row-id"
        self._docs[data_id] = {
            "id": row_id,
            "data_id": data_id,
            "data_text": data_text,
            "data_type": data_type,
            "metadata": metadata or {},
            "user_id": user_id,
            "agent_id": agent_id,
        }
        return row_id

    def search_documents(self, query, user_id=None, limit=50):
        results = []
        for row in self._docs.values():
            if (row.get("data_id") == query or
                    (row.get("data_text") and query in row["data_text"]) or
                    row.get("data_type") == query):
                if user_id is None or row.get("user_id") == user_id:
                    results.append(row)
        return results[:limit]

    def get_document(self, doc_id):
        return self._docs.get(doc_id)


_fake_sqlite_module.SQLiteManager = _FakeSQLiteManager
sys.modules["src.sqlite_manager"] = _fake_sqlite_module

from src.recovery_manager import RecoveryManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(tmp_path):
    """Create a RecoveryManager pointing at a temp directory."""
    backup_dir = str(tmp_path / "backups")
    metadata_db = str(tmp_path / "backups" / "metadata.db")
    with patch("src.recovery_manager.SQLiteManager", _FakeSQLiteManager):
        manager = RecoveryManager(backup_dir=backup_dir, metadata_db=metadata_db)
    return manager


def _register_backup(manager, backup_id: str, backup_path: str,
                     databases: list = None):
    """Insert a fake backup record into the manager's metadata_db."""
    if databases is None:
        databases = ["postgresql", "qdrant", "neo4j", "redis"]
    record = {
        "backup_id": backup_id,
        "backup_path": backup_path,
        "databases_backed_up": databases,
        "started_at": datetime.now().isoformat(),
    }
    manager.metadata_db.add_document(
        data_id=backup_id,
        data_text=json.dumps(record),
        data_type="backup_metadata",
        metadata=record,
        user_id="backup_system",
        agent_id="backup_manager",
    )
    return record


def _write_pg_sql(backup_path: Path, filename="postgresql_dump.sql",
                  content="SELECT 1;", gz=False):
    """Write a fake PostgreSQL backup file."""
    backup_path.mkdir(parents=True, exist_ok=True)
    if gz:
        filepath = backup_path / (filename + ".gz")
        with gzip.open(filepath, "wb") as f:
            f.write(content.encode())
    else:
        filepath = backup_path / filename
        filepath.write_text(content)
    return filepath


def _write_qdrant_snapshot(backup_path: Path, gz=False):
    backup_path.mkdir(parents=True, exist_ok=True)
    if gz:
        filepath = backup_path / "qdrant_snapshot.snapshot.gz"
        with gzip.open(filepath, "wb") as f:
            f.write(b"snapshot data")
    else:
        filepath = backup_path / "qdrant_snapshot.snapshot"
        filepath.write_bytes(b"snapshot data")
    return filepath


def _write_neo4j_json(backup_path: Path, data=None, gz=False):
    backup_path.mkdir(parents=True, exist_ok=True)
    data = data or [{"labels": ["Entity"], "properties": {"name": "test"}}]
    content = json.dumps(data)
    if gz:
        filepath = backup_path / "neo4j_backup.json.gz"
        with gzip.open(filepath, "wb") as f:
            f.write(content.encode())
    else:
        filepath = backup_path / "neo4j_backup.json"
        filepath.write_text(content)
    return filepath


def _write_redis_rdb(backup_path: Path, gz=False):
    backup_path.mkdir(parents=True, exist_ok=True)
    if gz:
        filepath = backup_path / "redis_dump.rdb.gz"
        with gzip.open(filepath, "wb") as f:
            f.write(b"REDIS RDB data")
    else:
        filepath = backup_path / "redis_dump.rdb"
        filepath.write_bytes(b"REDIS RDB data")
    return filepath


def _write_neo4j_native(backup_path: Path):
    """Write a non-JSON neo4j backup to test the 'skipped' path."""
    backup_path.mkdir(parents=True, exist_ok=True)
    filepath = backup_path / "neo4j_backup.dump"
    filepath.write_bytes(b"binary neo4j backup")
    return filepath


# ===========================================================================
# __init__ and _load_config
# ===========================================================================

class TestInit:
    def test_creates_backup_dir(self, tmp_path):
        m = _make_manager(tmp_path)
        assert (tmp_path / "backups").is_dir()

    def test_load_config_reads_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("POSTGRES_HOST", "pghost")
        monkeypatch.setenv("POSTGRES_PORT", "9999")
        monkeypatch.setenv("QDRANT_HOST", "qdranthost")
        monkeypatch.setenv("NEO4J_URI", "bolt://neo4jhost:9999")
        monkeypatch.setenv("REDIS_HOST", "redishost")
        m = _make_manager(tmp_path)
        assert m.config["postgresql"]["host"] == "pghost"
        assert m.config["postgresql"]["port"] == "9999"
        assert m.config["qdrant"]["host"] == "qdranthost"
        assert m.config["neo4j"]["uri"] == "bolt://neo4jhost:9999"
        assert m.config["redis"]["host"] == "redishost"

    def test_restore_history_starts_empty(self, tmp_path):
        m = _make_manager(tmp_path)
        assert m.restore_history == []
        assert m.current_restore is None


# ===========================================================================
# get_backup
# ===========================================================================

class TestGetBackup:
    def test_returns_none_when_not_found(self, tmp_path):
        m = _make_manager(tmp_path)
        assert m.get_backup("nonexistent-id") is None

    def test_returns_metadata_when_found(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "bp-1", bp)
        result = m.get_backup("bp-1")
        assert result is not None
        assert result["backup_id"] == "bp-1"


# ===========================================================================
# restore_database dispatcher
# ===========================================================================

class TestRestoreDatabase:
    def test_dispatches_postgresql(self, tmp_path):
        m = _make_manager(tmp_path)
        with patch.object(m, "restore_postgres", return_value={"status": "success"}) as mock_pg:
            result = m.restore_database("postgresql", "bid")
        mock_pg.assert_called_once_with("bid")
        assert result["status"] == "success"

    def test_dispatches_qdrant(self, tmp_path):
        m = _make_manager(tmp_path)
        with patch.object(m, "restore_qdrant", return_value={"status": "success"}) as mock_q:
            result = m.restore_database("qdrant", "bid")
        mock_q.assert_called_once_with("bid")

    def test_dispatches_neo4j(self, tmp_path):
        m = _make_manager(tmp_path)
        with patch.object(m, "restore_neo4j", return_value={"status": "success"}) as mock_n:
            result = m.restore_database("neo4j", "bid")
        mock_n.assert_called_once_with("bid")

    def test_dispatches_redis(self, tmp_path):
        m = _make_manager(tmp_path)
        with patch.object(m, "restore_redis", return_value={"status": "success"}) as mock_r:
            result = m.restore_database("redis", "bid")
        mock_r.assert_called_once_with("bid")

    def test_unknown_database_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        with pytest.raises(ValueError, match="Unknown database"):
            m.restore_database("mongodb", "bid")


# ===========================================================================
# restore_from_backup
# ===========================================================================

class TestRestoreFromBackup:
    def test_returns_error_when_backup_not_found(self, tmp_path):
        m = _make_manager(tmp_path)
        result = m.restore_from_backup("nonexistent-backup")
        assert result["status"] == "error"
        assert "not found" in result["error"]

    def test_success_all_databases(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b1", bp, databases=["postgresql"])

        success_result = {"status": "success"}
        validation_result = {"postgresql": {"valid": True}, "all_valid": True}

        with (
            patch.object(m, "restore_database", return_value=success_result),
            patch.object(m, "validate_restored_data", return_value=validation_result),
        ):
            result = m.restore_from_backup("b1", validate=True)

        assert result["status"] == "success"
        assert "postgresql" in result["databases_restored"]
        assert result["validation"]["all_valid"] is True
        assert len(m.restore_history) == 1

    def test_success_without_validation(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b2", bp, databases=["redis"])

        with patch.object(m, "restore_database", return_value={"status": "success"}):
            result = m.restore_from_backup("b2", validate=False)

        assert result["status"] == "success"
        assert result["validation"] == {}

    def test_database_failure_triggers_rollback(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b3", bp, databases=["postgresql"])

        with patch.object(m, "restore_database",
                          side_effect=RuntimeError("psql crashed")):
            result = m.restore_from_backup("b3", validate=False)

        assert result["status"] == "failed"
        assert "rollback" in result

    def test_validation_failure_triggers_rollback(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b4", bp, databases=["postgresql"])

        validation_result = {"postgresql": {"valid": False}, "all_valid": False}

        with (
            patch.object(m, "restore_database", return_value={"status": "success"}),
            patch.object(m, "validate_restored_data", return_value=validation_result),
        ):
            result = m.restore_from_backup("b4", validate=True)

        assert result["status"] == "validation_failed"
        assert "rollback" in result

    def test_outer_exception_triggers_rollback(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b5", bp, databases=["postgresql"])

        def _fake_validate(_):
            raise RuntimeError("unexpected crash")

        with (
            patch.object(m, "restore_database", return_value={"status": "success"}),
            patch.object(m, "validate_restored_data", side_effect=_fake_validate),
        ):
            result = m.restore_from_backup("b5", validate=True)

        assert result["status"] == "failed"
        assert "rollback" in result

    def test_defaults_to_backup_databases_list(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b6", bp, databases=["neo4j", "redis"])

        called_with = []

        def _fake_restore(db, bid):
            called_with.append(db)
            return {"status": "success"}

        with (
            patch.object(m, "restore_database", side_effect=_fake_restore),
            patch.object(m, "validate_restored_data",
                         return_value={"all_valid": True}),
        ):
            m.restore_from_backup("b6", validate=True)

        assert "neo4j" in called_with
        assert "redis" in called_with

    def test_metadata_stored_on_success(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp1")
        _register_backup(m, "b7", bp, databases=["postgresql"])

        with (
            patch.object(m, "restore_database", return_value={"status": "success"}),
            patch.object(m, "validate_restored_data",
                         return_value={"all_valid": True}),
            patch.object(m, "_store_restore_metadata") as mock_store,
        ):
            result = m.restore_from_backup("b7", validate=True)

        mock_store.assert_called_once()


# ===========================================================================
# restore_postgres
# ===========================================================================

class TestRestorePostgres:
    def test_backup_not_found_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        with pytest.raises(ValueError, match="Backup not found"):
            m.restore_postgres("nonexistent")

    def test_no_pg_file_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp_empty")
        Path(bp).mkdir(parents=True, exist_ok=True)
        _register_backup(m, "b-empty", bp)
        with pytest.raises(ValueError, match="PostgreSQL backup file not found"):
            m.restore_postgres("b-empty")

    def test_success_plain_sql(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_pg"
        _write_pg_sql(bp)
        _register_backup(m, "b-pg", str(bp))

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = m.restore_postgres("b-pg")

        assert result["status"] == "success"
        assert result["database"] == "postgresql"

    def test_success_gzip_sql(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_pg_gz"
        _write_pg_sql(bp, gz=True)
        _register_backup(m, "b-pg-gz", str(bp_gz := bp))

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = m.restore_postgres("b-pg-gz")

        assert result["status"] == "success"

    def test_psql_nonzero_returncode_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_pg_fail"
        _write_pg_sql(bp)
        _register_backup(m, "b-pg-fail", str(bp))

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: table not found"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="psql restore failed"):
                m.restore_postgres("b-pg-fail")

    def test_timeout_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_pg_timeout"
        _write_pg_sql(bp)
        _register_backup(m, "b-pg-timeout", str(bp))

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("psql", 600)):
            with pytest.raises(RuntimeError, match="timeout"):
                m.restore_postgres("b-pg-timeout")

    def test_pgpassword_set_in_env(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_pg_env"
        _write_pg_sql(bp)
        _register_backup(m, "b-pg-env", str(bp))

        captured_env = {}

        def _capture_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            r = MagicMock()
            r.returncode = 0
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=_capture_run):
            m.restore_postgres("b-pg-env")

        assert "PGPASSWORD" in captured_env


# ===========================================================================
# restore_qdrant
# ===========================================================================

class TestRestoreQdrant:
    def test_backup_not_found_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        with pytest.raises(ValueError, match="Backup not found"):
            m.restore_qdrant("nonexistent")

    def test_no_qdrant_file_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp_empty_q")
        Path(bp).mkdir(parents=True, exist_ok=True)
        _register_backup(m, "b-empty-q", bp)
        with pytest.raises(ValueError, match="Qdrant backup file not found"):
            m.restore_qdrant("b-empty-q")

    def test_success_plain_snapshot(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_qdrant"
        _write_qdrant_snapshot(bp, gz=False)
        _register_backup(m, "b-qdrant", str(bp))

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response):
            result = m.restore_qdrant("b-qdrant")

        assert result["status"] == "success"
        assert result["database"] == "qdrant"

    def test_success_gzip_snapshot(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_qdrant_gz"
        _write_qdrant_snapshot(bp, gz=True)
        _register_backup(m, "b-qdrant-gz", str(bp))

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response):
            result = m.restore_qdrant("b-qdrant-gz")

        assert result["status"] == "success"

    def test_upload_failure_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_qdrant_fail"
        _write_qdrant_snapshot(bp, gz=False)
        _register_backup(m, "b-qdrant-fail", str(bp))

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "internal error"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Qdrant snapshot upload failed"):
                m.restore_qdrant("b-qdrant-fail")

    def test_requests_exception_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_qdrant_exc"
        _write_qdrant_snapshot(bp, gz=False)
        _register_backup(m, "b-qdrant-exc", str(bp))

        with patch("requests.post", side_effect=ConnectionError("network down")):
            with pytest.raises(RuntimeError, match="Qdrant restore failed"):
                m.restore_qdrant("b-qdrant-exc")


# ===========================================================================
# restore_neo4j
# ===========================================================================

class TestRestoreNeo4j:
    def test_backup_not_found_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        with pytest.raises(ValueError, match="Backup not found"):
            m.restore_neo4j("nonexistent")

    def test_no_neo4j_file_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp_empty_n")
        Path(bp).mkdir(parents=True, exist_ok=True)
        _register_backup(m, "b-empty-n", bp)
        with pytest.raises(ValueError, match="Neo4j backup file not found"):
            m.restore_neo4j("b-empty-n")

    def test_success_json_import(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_neo4j"
        nodes = [{"labels": ["Entity"], "properties": {"name": "node1"}}]
        _write_neo4j_json(bp, data=nodes)
        _register_backup(m, "b-neo4j", str(bp))

        mock_session = MagicMock()
        mock_session.run = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_driver.close = MagicMock()

        mock_neo4j_mod = MagicMock()
        mock_neo4j_mod.GraphDatabase.driver = MagicMock(return_value=mock_driver)

        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            result = m.restore_neo4j("b-neo4j")

        assert result["status"] == "success"
        assert result["nodes_restored"] == 1
        assert result["method"] == "cypher_import"

    def test_success_gzip_json_import(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_neo4j_gz"
        nodes = [{"labels": ["Node"], "properties": {"id": "1"}}]
        _write_neo4j_json(bp, data=nodes, gz=True)
        _register_backup(m, "b-neo4j-gz", str(bp))

        mock_session = MagicMock()
        mock_session.run = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_driver.close = MagicMock()

        mock_neo4j_mod = MagicMock()
        mock_neo4j_mod.GraphDatabase.driver = MagicMock(return_value=mock_driver)

        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            result = m.restore_neo4j("b-neo4j-gz")

        assert result["status"] == "success"

    def test_native_backup_skipped(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_neo4j_native"
        _write_neo4j_native(bp)
        _register_backup(m, "b-neo4j-native", str(bp))

        result = m.restore_neo4j("b-neo4j-native")

        assert result["status"] == "skipped"
        assert "not implemented" in result["reason"].lower()

    def test_neo4j_exception_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_neo4j_exc"
        nodes = [{"labels": ["N"], "properties": {}}]
        _write_neo4j_json(bp, data=nodes)
        _register_backup(m, "b-neo4j-exc", str(bp))

        mock_neo4j_mod = MagicMock()
        mock_neo4j_mod.GraphDatabase.driver = MagicMock(
            side_effect=RuntimeError("neo4j down")
        )

        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            with pytest.raises(RuntimeError, match="Neo4j restore failed"):
                m.restore_neo4j("b-neo4j-exc")


# ===========================================================================
# restore_redis
# ===========================================================================

class TestRestoreRedis:
    def test_backup_not_found_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        with pytest.raises(ValueError, match="Backup not found"):
            m.restore_redis("nonexistent")

    def test_no_redis_file_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = str(tmp_path / "bp_empty_r")
        Path(bp).mkdir(parents=True, exist_ok=True)
        _register_backup(m, "b-empty-r", bp)
        with pytest.raises(ValueError, match="Redis backup file not found"):
            m.restore_redis("b-empty-r")

    def test_success_plain_rdb(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_redis"
        _write_redis_rdb(bp, gz=False)
        _register_backup(m, "b-redis", str(bp))

        docker_copy = MagicMock(returncode=0, stderr="")
        docker_restart = MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=[docker_copy, docker_restart]):
            result = m.restore_redis("b-redis")

        assert result["status"] == "success"
        assert result["database"] == "redis"

    def test_success_gzip_rdb(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_redis_gz"
        _write_redis_rdb(bp, gz=True)
        _register_backup(m, "b-redis-gz", str(bp))

        docker_copy = MagicMock(returncode=0, stderr="")
        docker_restart = MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=[docker_copy, docker_restart]):
            result = m.restore_redis("b-redis-gz")

        assert result["status"] == "success"

    def test_docker_copy_failure_raises(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_redis_fail"
        _write_redis_rdb(bp, gz=False)
        _register_backup(m, "b-redis-fail", str(bp))

        docker_copy = MagicMock(returncode=1, stderr="container not found")

        with patch("subprocess.run", return_value=docker_copy):
            with pytest.raises(RuntimeError, match="Redis restore failed"):
                m.restore_redis("b-redis-fail")

    def test_exception_wraps_in_runtime_error(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_redis_exc"
        _write_redis_rdb(bp, gz=False)
        _register_backup(m, "b-redis-exc", str(bp))

        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            with pytest.raises(RuntimeError, match="Redis restore failed"):
                m.restore_redis("b-redis-exc")


# ===========================================================================
# validate_restored_data
# ===========================================================================

class TestValidateRestoredData:
    def test_all_valid(self, tmp_path):
        m = _make_manager(tmp_path)

        with (
            patch.object(m, "_validate_postgres", return_value={"valid": True}),
            patch.object(m, "_validate_qdrant", return_value={"valid": True}),
            patch.object(m, "_validate_neo4j", return_value={"valid": True}),
            patch.object(m, "_validate_redis", return_value={"valid": True}),
        ):
            result = m.validate_restored_data(
                ["postgresql", "qdrant", "neo4j", "redis"]
            )

        assert result["all_valid"] is True
        assert result["postgresql"]["valid"] is True

    def test_one_invalid_makes_all_invalid(self, tmp_path):
        m = _make_manager(tmp_path)

        with (
            patch.object(m, "_validate_postgres", return_value={"valid": True}),
            patch.object(m, "_validate_qdrant",
                         return_value={"valid": False, "error": "bad connection"}),
        ):
            result = m.validate_restored_data(["postgresql", "qdrant"])

        assert result["all_valid"] is False
        assert result["qdrant"]["valid"] is False

    def test_exception_in_validator_handled(self, tmp_path, caplog):
        m = _make_manager(tmp_path)

        with patch.object(m, "_validate_postgres",
                          side_effect=RuntimeError("pg crashed")):
            with caplog.at_level(logging.ERROR):
                result = m.validate_restored_data(["postgresql"])

        assert result["all_valid"] is False
        assert "error" in result["postgresql"]

    def test_unknown_db_skipped(self, tmp_path):
        m = _make_manager(tmp_path)
        result = m.validate_restored_data(["unknown_db"])
        # No key for 'unknown_db', all_valid should be True (no failures added)
        assert result["all_valid"] is True
        assert "unknown_db" not in result

    def test_empty_list(self, tmp_path):
        m = _make_manager(tmp_path)
        result = m.validate_restored_data([])
        assert result["all_valid"] is True


# ===========================================================================
# _validate_* (unit tests that mock the DB clients)
# ===========================================================================

class TestValidatePostgres:
    def test_returns_valid_on_success(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[1, 42])  # SELECT 1 then COUNT
        mock_conn.close = AsyncMock()

        with patch.object(m, "_connect_postgres", new=AsyncMock(return_value=mock_conn)):
            result = m._validate_postgres()

        assert result["valid"] is True
        assert result["document_count"] == 42

    def test_returns_invalid_on_exception(self, tmp_path, caplog):
        m = _make_manager(tmp_path)

        with patch.object(m, "_connect_postgres",
                          new=AsyncMock(side_effect=ConnectionError("pg down"))):
            result = m._validate_postgres()

        assert result["valid"] is False
        assert "error" in result


class TestValidateQdrant:
    def test_returns_valid_on_success(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_collections = MagicMock()
        mock_collections.collections = [MagicMock(), MagicMock()]

        mock_client = MagicMock()
        mock_client.get_collections = MagicMock(return_value=mock_collections)

        # QdrantClient is imported inside _validate_qdrant via 'from qdrant_client import ...'
        mock_qc_mod = MagicMock()
        mock_qc_mod.QdrantClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"qdrant_client": mock_qc_mod}):
            result = m._validate_qdrant()

        assert result["valid"] is True
        assert result["collection_count"] == 2

    def test_returns_invalid_on_exception(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_qc_mod = MagicMock()
        mock_qc_mod.QdrantClient = MagicMock(side_effect=ConnectionError("qdrant down"))

        with patch.dict("sys.modules", {"qdrant_client": mock_qc_mod}):
            result = m._validate_qdrant()

        assert result["valid"] is False
        assert "error" in result


class TestValidateNeo4j:
    def test_returns_valid_on_success(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_result1 = MagicMock()
        mock_result1.single = MagicMock(return_value=[1])
        mock_result2 = MagicMock()
        mock_result2.single = MagicMock(return_value=[5])

        mock_session = MagicMock()
        mock_session.run = MagicMock(side_effect=[mock_result1, mock_result2])
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_driver.close = MagicMock()

        mock_neo4j_mod = MagicMock()
        mock_neo4j_mod.GraphDatabase.driver = MagicMock(return_value=mock_driver)

        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            result = m._validate_neo4j()

        assert result["valid"] is True
        assert result["node_count"] == 5

    def test_returns_invalid_on_exception(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_neo4j_mod = MagicMock()
        mock_neo4j_mod.GraphDatabase.driver = MagicMock(
            side_effect=ConnectionError("neo4j down")
        )

        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            result = m._validate_neo4j()

        assert result["valid"] is False
        assert "error" in result


class TestValidateRedis:
    def test_returns_valid_on_success(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_redis_instance = MagicMock()
        mock_redis_instance.ping = MagicMock(return_value=True)
        mock_redis_instance.keys = MagicMock(return_value=["key1", "key2", "key3"])

        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis = MagicMock(return_value=mock_redis_instance)

        # 'redis' is imported inside _validate_redis via 'import redis'
        with patch.dict("sys.modules", {"redis": mock_redis_mod}):
            result = m._validate_redis()

        assert result["valid"] is True
        assert result["key_count"] == 3

    def test_returns_invalid_on_exception(self, tmp_path):
        m = _make_manager(tmp_path)

        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis = MagicMock(side_effect=ConnectionError("redis down"))

        with patch.dict("sys.modules", {"redis": mock_redis_mod}):
            result = m._validate_redis()

        assert result["valid"] is False
        assert "error" in result


# ===========================================================================
# rollback_last_restore
# ===========================================================================

class TestRollbackLastRestore:
    def test_no_current_restore_returns_skipped(self, tmp_path):
        m = _make_manager(tmp_path)
        result = m.rollback_last_restore()
        assert result["status"] == "skipped"
        assert "No restore operation" in result["reason"]

    def test_success_marks_rolled_back(self, tmp_path):
        m = _make_manager(tmp_path)
        m.current_restore = {
            "restore_id": "restore-123",
            "backup_id": "backup-abc",
            "status": "in_progress",
        }
        result = m.rollback_last_restore()
        assert result["status"] == "success"
        assert m.current_restore["status"] == "rolled_back"
        assert result["restore_id"] == "restore-123"

    def test_exception_during_rollback_returns_failed(self, tmp_path, caplog):
        m = _make_manager(tmp_path)
        # Simulate current_restore that raises when accessed
        bad_restore = MagicMock()
        bad_restore.__getitem__ = MagicMock(side_effect=RuntimeError("corrupt state"))
        m.current_restore = bad_restore

        with caplog.at_level(logging.ERROR):
            result = m.rollback_last_restore()

        assert result["status"] == "failed"
        assert "error" in result


# ===========================================================================
# list_restores
# ===========================================================================

class TestListRestores:
    def test_empty_list(self, tmp_path):
        m = _make_manager(tmp_path)
        result = m.list_restores()
        assert result == []

    def test_returns_stored_restores(self, tmp_path):
        m = _make_manager(tmp_path)
        restore_record = {
            "restore_id": "rest-001",
            "backup_id": "bk-001",
            "started_at": "2026-01-01T00:00:00",
            "status": "completed",
        }
        m.metadata_db.add_document(
            data_id="rest-001",
            data_text=json.dumps(restore_record),
            data_type="restore_metadata",
            metadata=restore_record,
            user_id="recovery_system",
            agent_id="recovery_manager",
        )
        result = m.list_restores()
        assert len(result) >= 1
        ids = [r["restore_id"] for r in result]
        assert "rest-001" in ids


# ===========================================================================
# _store_restore_metadata
# ===========================================================================

class TestStoreRestoreMetadata:
    def test_stores_successfully(self, tmp_path):
        m = _make_manager(tmp_path)
        metadata = {
            "restore_id": "rest-store-001",
            "backup_id": "bk-store-001",
            "started_at": "2026-01-01T00:00:00",
            "status": "completed",
        }
        m._store_restore_metadata(metadata)

        # Verify it was stored in the metadata db
        stored = m.metadata_db.search_documents(
            "rest-store-001", user_id="recovery_system"
        )
        assert len(stored) == 1
        stored_data = json.loads(stored[0]["data_text"])
        assert stored_data["restore_id"] == "rest-store-001"


# ===========================================================================
# _load_config defaults
# ===========================================================================

class TestLoadConfig:
    def test_default_values_when_env_not_set(self, tmp_path, monkeypatch):
        # Remove all relevant env vars so defaults kick in
        for var in ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
                    "POSTGRES_USER", "POSTGRES_PASSWORD",
                    "QDRANT_HOST", "QDRANT_PORT", "QDRANT_API_KEY",
                    "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD",
                    "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]:
            monkeypatch.delenv(var, raising=False)

        m = _make_manager(tmp_path)
        cfg = m.config

        assert cfg["postgresql"]["host"] == "localhost"
        assert cfg["postgresql"]["port"] == "25432"
        assert cfg["qdrant"]["host"] == "localhost"
        assert cfg["neo4j"]["uri"] == "bolt://localhost:27687"
        assert cfg["redis"]["host"] == "localhost"


# ===========================================================================
# Integration-style: full restore_from_backup with mocked subprocess
# ===========================================================================

class TestRestoreFromBackupIntegration:
    def test_restore_postgresql_full_flow(self, tmp_path):
        """Full restore flow for postgresql using a real temp backup file."""
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_full"
        _write_pg_sql(bp, content="SELECT 1;")
        _register_backup(m, "b-full", str(bp), databases=["postgresql"])

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc):
            result = m.restore_from_backup("b-full", validate=False)

        assert result["status"] == "success"
        assert result["databases_restored"] == ["postgresql"]

    def test_restore_multiple_databases_in_sequence(self, tmp_path):
        m = _make_manager(tmp_path)
        bp = tmp_path / "bp_multi"
        _write_pg_sql(bp)
        _write_redis_rdb(bp, gz=False)
        _register_backup(m, "b-multi", str(bp), databases=["postgresql", "redis"])

        pg_result = MagicMock(returncode=0, stderr="")
        docker_copy = MagicMock(returncode=0, stderr="")
        docker_restart = MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=[pg_result, docker_copy, docker_restart]):
            result = m.restore_from_backup("b-multi", validate=False)

        assert result["status"] == "success"
        assert "postgresql" in result["results"]
        assert "redis" in result["results"]
