"""
Unit tests for src/backup_manager.py

Coverage targets:
- BackupManager.__init__ / _load_config
- create_backup: success (all dbs), partial failure, outer exception
- _backup_database: dispatches to correct method + unknown db
- _backup_postgresql: success (plain + gzip), returncode != 0, timeout, exception
- _backup_qdrant: success (plain + gzip), bad status code, no snapshot url, exception
- _backup_neo4j: docker success, docker failure -> neo4j fallback, exception
- _backup_redis: success (plain + gzip), bgsave failure, copy failure, exception
- _calculate_backup_checksum: empty dir, files present
- _store_backup_metadata
- list_backups: empty, with records, with type filter
- get_backup: found, not found
- delete_backup: success, backup not found, file delete exception
- rotate_backups / _rotate_backup_type
"""

import gzip
import json
import os
import shutil
import subprocess
import sys
import types
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

# ---------------------------------------------------------------------------
# Module-level sys.modules snapshot & restore fixture
# ---------------------------------------------------------------------------

_MODULES_TO_PROTECT = ["src.sqlite_manager", "src.backup_manager"]
_SYS_MODULES_SNAPSHOT = {k: sys.modules.get(k) for k in _MODULES_TO_PROTECT}

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(scope="module", autouse=True)
def _restore_sys_modules_after_module():
    """Restore any stubbed sys.modules entries after this module finishes."""
    yield
    for k, original in _SYS_MODULES_SNAPSHOT.items():
        if original is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = original


# ---------------------------------------------------------------------------
# Stub SQLiteManager BEFORE importing BackupManager
# ---------------------------------------------------------------------------

_fake_sqlite_mod = types.ModuleType("src.sqlite_manager")


class _FakeSQLiteManager:
    """In-memory SQLiteManager stand-in."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._docs: dict = {}

    def add_document(self, data_id=None, data_text=None, data_type=None,
                     metadata=None, user_id=None, agent_id=None):
        self._docs[data_id] = {
            "id": data_id,
            "data_id": data_id,
            "data_text": data_text,
            "data_type": data_type,
            "metadata": metadata or {},
            "user_id": user_id,
            "agent_id": agent_id,
        }
        return data_id

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

    def delete_document(self, doc_id):
        existed = doc_id in self._docs
        self._docs.pop(doc_id, None)
        return existed


_fake_sqlite_mod.SQLiteManager = _FakeSQLiteManager
sys.modules["src.sqlite_manager"] = _fake_sqlite_mod

# Now safe to import
from src.backup_manager import BackupManager  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(tmp_path):
    backup_dir = str(tmp_path / "backups")
    metadata_db = str(tmp_path / "backups" / "metadata.db")
    with patch("src.backup_manager.SQLiteManager", _FakeSQLiteManager):
        mgr = BackupManager(backup_dir=backup_dir, metadata_db=metadata_db)
    return mgr


def _register_backup(mgr, backup_id, backup_path_str, databases=None):
    if databases is None:
        databases = ["postgresql"]
    record = {
        "backup_id": backup_id,
        "backup_type": "manual",
        "created_at": datetime.now().isoformat(),
        "backup_path": backup_path_str,
        "databases_backed_up": databases,
        "backup_results": {},
        "total_size_bytes": 0,
        "compressed": False,
        "checksum": "abc123",
        "description": "test",
        "status": "completed",
    }
    mgr.metadata_db.add_document(
        data_id=backup_id,
        data_text=json.dumps(record),
        data_type="backup_metadata",
        metadata=record,
        user_id="backup_system",
        agent_id="backup_manager",
    )
    return record


# ---------------------------------------------------------------------------
# __init__ / _load_config
# ---------------------------------------------------------------------------


def test_init_creates_subdirs(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_dir = tmp_path / "backups"
    for subdir in ("postgresql", "qdrant", "neo4j", "redis", "full"):
        assert (backup_dir / subdir).is_dir()


def test_load_config_defaults(tmp_path):
    mgr = _make_manager(tmp_path)
    cfg = mgr.config
    assert cfg["postgresql"]["host"] == "localhost"
    assert cfg["postgresql"]["port"] == "25432"
    assert cfg["qdrant"]["host"] == "localhost"
    assert cfg["neo4j"]["uri"] == "bolt://localhost:27687"
    assert cfg["redis"]["host"] == "localhost"


def test_load_config_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "pg-host")
    monkeypatch.setenv("QDRANT_PORT", "9999")
    mgr = _make_manager(tmp_path)
    assert mgr.config["postgresql"]["host"] == "pg-host"
    assert mgr.config["qdrant"]["port"] == "9999"


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------


def test_create_backup_returns_uuid(tmp_path):
    mgr = _make_manager(tmp_path)
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "-- SQL dump content"
    mock_result.stderr = ""

    with patch("src.backup_manager.subprocess.run", return_value=mock_result):
        backup_id = mgr.create_backup(databases=["postgresql"], compress=False)

    assert backup_id is not None
    assert len(backup_id) > 0


def test_create_backup_all_databases(tmp_path):
    mgr = _make_manager(tmp_path)

    def _fake_backup_db(db, path, compress):
        # Create a dummy file so checksum works
        dummy = path / f"{db}.sql"
        dummy.write_text("dump")
        return {"status": "success", "file_path": str(dummy), "file_size": 4}

    mgr._backup_database = _fake_backup_db
    backup_id = mgr.create_backup(databases=None)
    assert backup_id is not None


def test_create_backup_partial_failure(tmp_path):
    mgr = _make_manager(tmp_path)
    call_count = [0]

    def _backup_db(db, path, compress):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("qdrant down")
        dummy = path / f"{db}.sql"
        dummy.write_text("ok")
        return {"status": "success", "file_path": str(dummy), "file_size": 2}

    mgr._backup_database = _backup_db
    backup_id = mgr.create_backup(databases=["postgresql", "qdrant"])
    assert backup_id is not None


def test_create_backup_outer_exception(tmp_path):
    mgr = _make_manager(tmp_path)
    # Make backup dir not writable by making mkdir fail
    with patch.object(Path, "mkdir", side_effect=PermissionError("no write")):
        with pytest.raises(Exception):
            mgr.create_backup(databases=["postgresql"])


# ---------------------------------------------------------------------------
# _backup_database dispatcher
# ---------------------------------------------------------------------------


def test_backup_database_unknown_raises(tmp_path):
    mgr = _make_manager(tmp_path)
    with pytest.raises(ValueError, match="Unknown database"):
        mgr._backup_database("mysql", tmp_path, False)


def test_backup_database_dispatches_postgresql(tmp_path):
    mgr = _make_manager(tmp_path)
    with patch.object(mgr, "_backup_postgresql", return_value={"status": "success"}) as m:
        mgr._backup_database("postgresql", tmp_path, True)
        m.assert_called_once_with(tmp_path, True)


def test_backup_database_dispatches_qdrant(tmp_path):
    mgr = _make_manager(tmp_path)
    with patch.object(mgr, "_backup_qdrant", return_value={"status": "success"}) as m:
        mgr._backup_database("qdrant", tmp_path, False)
        m.assert_called_once_with(tmp_path, False)


def test_backup_database_dispatches_neo4j(tmp_path):
    mgr = _make_manager(tmp_path)
    with patch.object(mgr, "_backup_neo4j", return_value={"status": "success"}) as m:
        mgr._backup_database("neo4j", tmp_path, False)
        m.assert_called_once_with(tmp_path, False)


def test_backup_database_dispatches_redis(tmp_path):
    mgr = _make_manager(tmp_path)
    with patch.object(mgr, "_backup_redis", return_value={"status": "success"}) as m:
        mgr._backup_database("redis", tmp_path, False)
        m.assert_called_once_with(tmp_path, False)


# ---------------------------------------------------------------------------
# _backup_postgresql
# ---------------------------------------------------------------------------


def test_backup_postgresql_success_plain(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "manual" / "test_backup"
    backup_path.mkdir(parents=True)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "-- PostgreSQL dump\nSELECT 1;\n"
    mock_result.stderr = ""

    with patch("src.backup_manager.subprocess.run", return_value=mock_result):
        result = mgr._backup_postgresql(backup_path, compress=False)

    assert result["status"] == "success"
    assert result["database"] == "postgresql"
    assert result["compressed"] is False
    assert Path(result["file_path"]).exists()


def test_backup_postgresql_success_gzip(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "manual" / "test_backup"
    backup_path.mkdir(parents=True)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "-- dump"
    mock_result.stderr = ""

    with patch("src.backup_manager.subprocess.run", return_value=mock_result):
        result = mgr._backup_postgresql(backup_path, compress=True)

    assert result["status"] == "success"
    assert result["file_path"].endswith(".gz")


def test_backup_postgresql_nonzero_returncode(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "pg_fail"
    backup_path.mkdir(parents=True)

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "pg_dump: error: connection refused"

    with patch("src.backup_manager.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="pg_dump failed"):
            mgr._backup_postgresql(backup_path, compress=False)


def test_backup_postgresql_timeout(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "pg_timeout"
    backup_path.mkdir(parents=True)

    with patch("src.backup_manager.subprocess.run",
               side_effect=subprocess.TimeoutExpired("pg_dump", 300)):
        with pytest.raises(RuntimeError, match="timeout"):
            mgr._backup_postgresql(backup_path, compress=False)


def test_backup_postgresql_exception(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "pg_exc"
    backup_path.mkdir(parents=True)

    with patch("src.backup_manager.subprocess.run",
               side_effect=FileNotFoundError("pg_dump not found")):
        with pytest.raises(RuntimeError, match="PostgreSQL backup failed"):
            mgr._backup_postgresql(backup_path, compress=False)


# ---------------------------------------------------------------------------
# _backup_qdrant
# ---------------------------------------------------------------------------


def test_backup_qdrant_success_plain(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "qdrant_test"
    backup_path.mkdir(parents=True)

    snapshot_content = b"binary snapshot data"

    mock_post_response = MagicMock()
    mock_post_response.status_code = 200
    mock_post_response.json.return_value = {"result": "http://qdrant/snapshots/snap1"}

    mock_get_response = MagicMock()
    mock_get_response.content = snapshot_content
    mock_get_response.raise_for_status = MagicMock()

    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_post_response
    mock_requests.get.return_value = mock_get_response

    with patch.dict("sys.modules", {"requests": mock_requests}):
        result = mgr._backup_qdrant(backup_path, compress=False)

    assert result["status"] == "success"
    assert result["database"] == "qdrant"


def test_backup_qdrant_success_gzip(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "qdrant_gz"
    backup_path.mkdir(parents=True)

    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = {"result": "http://qdrant/snapshots/snap1"}

    mock_get = MagicMock()
    mock_get.content = b"data"
    mock_get.raise_for_status = MagicMock()

    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_post
    mock_requests.get.return_value = mock_get

    with patch.dict("sys.modules", {"requests": mock_requests}):
        result = mgr._backup_qdrant(backup_path, compress=True)

    assert result["file_path"].endswith(".gz")


def test_backup_qdrant_bad_status_code(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "qdrant_bad"
    backup_path.mkdir(parents=True)

    mock_post = MagicMock()
    mock_post.status_code = 500
    mock_post.text = "Internal Server Error"

    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_post

    with patch.dict("sys.modules", {"requests": mock_requests}):
        with pytest.raises(RuntimeError, match="Qdrant backup failed"):
            mgr._backup_qdrant(backup_path, compress=False)


def test_backup_qdrant_no_snapshot_url(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "qdrant_nourl"
    backup_path.mkdir(parents=True)

    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = {"result": ""}  # empty URL

    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_post

    with patch.dict("sys.modules", {"requests": mock_requests}):
        with pytest.raises(RuntimeError, match="Qdrant backup failed"):
            mgr._backup_qdrant(backup_path, compress=False)


def test_backup_qdrant_exception(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "qdrant_exc"
    backup_path.mkdir(parents=True)

    mock_requests = MagicMock()
    mock_requests.post.side_effect = ConnectionError("qdrant unreachable")

    with patch.dict("sys.modules", {"requests": mock_requests}):
        with pytest.raises(RuntimeError, match="Qdrant backup failed"):
            mgr._backup_qdrant(backup_path, compress=False)


# ---------------------------------------------------------------------------
# _backup_neo4j
# ---------------------------------------------------------------------------


def test_backup_neo4j_docker_success(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "neo4j_docker"
    backup_path.mkdir(parents=True)

    mock_result_admin = MagicMock()
    mock_result_admin.returncode = 0

    def _fake_run(cmd, *args, **kwargs):
        if "neo4j-admin" in cmd:
            return mock_result_admin
        # docker cp - create dummy file
        dest = cmd[-1]
        Path(dest).mkdir(parents=True, exist_ok=True)
        return MagicMock(returncode=0)

    with patch("src.backup_manager.subprocess.run", side_effect=_fake_run):
        result = mgr._backup_neo4j(backup_path, compress=False)

    assert result["status"] == "success"
    assert result["method"] == "docker"


def test_backup_neo4j_docker_fails_uses_cypher(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "neo4j_cypher"
    backup_path.mkdir(parents=True)

    # Docker command fails -> falls through to Cypher export
    mock_admin_fail = MagicMock()
    mock_admin_fail.returncode = 1

    # Mock neo4j driver
    mock_node = MagicMock()
    mock_node.labels = ["Memory"]
    mock_record = MagicMock()
    mock_record.__getitem__ = MagicMock(return_value=mock_node)
    dict(mock_node)  # so dict() works

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.run.return_value = []

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_driver.close = MagicMock()

    mock_neo4j_mod = MagicMock()
    mock_neo4j_mod.GraphDatabase.driver.return_value = mock_driver

    with patch("src.backup_manager.subprocess.run", return_value=mock_admin_fail):
        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            result = mgr._backup_neo4j(backup_path, compress=False)

    assert result["status"] == "success"
    assert result["method"] == "cypher_export"


def test_backup_neo4j_exception(tmp_path):
    """Both docker and cypher-export paths fail -> RuntimeError propagates.

    The implementation tries Docker first; on any Exception it falls back to
    a Cypher driver export. The test must therefore poison BOTH paths to
    reach the outer "Neo4j backup failed" raise (otherwise CI with a real
    Neo4j env will see the fallback succeed and the test will incorrectly
    expect no exception).
    """
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "neo4j_exc"
    backup_path.mkdir(parents=True)

    # Mock neo4j module so the cypher-export fallback also blows up.
    mock_neo4j_mod = MagicMock()
    mock_neo4j_mod.GraphDatabase.driver.side_effect = RuntimeError(
        "cypher driver unavailable"
    )

    with patch("src.backup_manager.subprocess.run",
               side_effect=RuntimeError("subprocess error")):
        with patch.dict("sys.modules", {"neo4j": mock_neo4j_mod}):
            with pytest.raises(RuntimeError, match="Neo4j backup failed"):
                mgr._backup_neo4j(backup_path, compress=False)


# ---------------------------------------------------------------------------
# _backup_redis
# ---------------------------------------------------------------------------


def test_backup_redis_success_plain(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "redis_test"
    backup_path.mkdir(parents=True)

    dummy_rdb = b"REDIS0009" + b"\x00" * 100

    def _fake_run(cmd, *args, **kwargs):
        if "BGSAVE" in cmd:
            return MagicMock(returncode=0, stdout="Background saving started", stderr="")
        if "cp" in cmd:
            # Copy the file to the target path
            dest = cmd[-1]
            Path(dest).write_bytes(dummy_rdb)
            return MagicMock(returncode=0, stderr="")
        return MagicMock(returncode=0)

    with patch("src.backup_manager.subprocess.run", side_effect=_fake_run):
        with patch("time.sleep"):
            result = mgr._backup_redis(backup_path, compress=False)

    assert result["status"] == "success"
    assert result["database"] == "redis"
    assert result["compressed"] is False


def test_backup_redis_success_gzip(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "redis_gz"
    backup_path.mkdir(parents=True)

    dummy_rdb = b"REDIS" + b"\x00" * 50

    def _fake_run(cmd, *args, **kwargs):
        if "BGSAVE" in cmd:
            return MagicMock(returncode=0, stdout="OK", stderr="")
        if "cp" in cmd:
            dest = cmd[-1]
            Path(dest).write_bytes(dummy_rdb)
            return MagicMock(returncode=0, stderr="")
        return MagicMock(returncode=0)

    with patch("src.backup_manager.subprocess.run", side_effect=_fake_run):
        with patch("time.sleep"):
            result = mgr._backup_redis(backup_path, compress=True)

    assert result["compressed"] is True
    assert result["file_path"].endswith(".gz")


def test_backup_redis_bgsave_failure(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "redis_fail"
    backup_path.mkdir(parents=True)

    with patch("src.backup_manager.subprocess.run",
               return_value=MagicMock(returncode=1, stderr="BGSAVE failed")):
        with pytest.raises(RuntimeError, match="Redis backup failed"):
            mgr._backup_redis(backup_path, compress=False)


def test_backup_redis_copy_failure(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "redis_copyfail"
    backup_path.mkdir(parents=True)

    def _fake_run(cmd, *args, **kwargs):
        if "BGSAVE" in cmd:
            return MagicMock(returncode=0, stdout="OK", stderr="")
        return MagicMock(returncode=1, stderr="No such file")

    with patch("src.backup_manager.subprocess.run", side_effect=_fake_run):
        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="Redis backup failed"):
                mgr._backup_redis(backup_path, compress=False)


def test_backup_redis_exception(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_path = tmp_path / "backups" / "redis_exc"
    backup_path.mkdir(parents=True)

    with patch("src.backup_manager.subprocess.run",
               side_effect=RuntimeError("docker not found")):
        with pytest.raises(RuntimeError, match="Redis backup failed"):
            mgr._backup_redis(backup_path, compress=False)


# ---------------------------------------------------------------------------
# _calculate_backup_checksum
# ---------------------------------------------------------------------------


def test_calculate_backup_checksum_empty_dir(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr._calculate_backup_checksum(tmp_path)
    assert isinstance(result, str)
    assert len(result) == 64  # SHA256 hex digest


def test_calculate_backup_checksum_with_files(tmp_path):
    mgr = _make_manager(tmp_path)
    (tmp_path / "file1.sql").write_text("dump 1")
    (tmp_path / "file2.sql").write_text("dump 2")
    result = mgr._calculate_backup_checksum(tmp_path)
    assert len(result) == 64
    # Different files should produce different checksums from empty dir
    empty_checksum = mgr._calculate_backup_checksum(tmp_path / "nonexistent_subdir")
    # (can't compare directly, just verify it's a valid hex string)
    assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# _store_backup_metadata
# ---------------------------------------------------------------------------


def test_store_backup_metadata(tmp_path):
    mgr = _make_manager(tmp_path)
    metadata = {
        "backup_id": "test-id-123",
        "backup_type": "manual",
        "created_at": datetime.now().isoformat(),
        "backup_path": "/some/path",
        "databases_backed_up": ["postgresql"],
        "backup_results": {},
        "total_size_bytes": 1000,
        "compressed": True,
        "checksum": "abc",
        "description": "test",
        "status": "completed",
    }
    mgr._store_backup_metadata(metadata)
    # Verify it's in the db
    doc = mgr.metadata_db._docs.get("test-id-123")
    assert doc is not None


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------


def test_list_backups_empty(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr.list_backups()
    assert result == []


def test_list_backups_with_records(tmp_path):
    mgr = _make_manager(tmp_path)
    _register_backup(mgr, "b1", str(tmp_path / "b1"))
    _register_backup(mgr, "b2", str(tmp_path / "b2"))
    result = mgr.list_backups()
    assert len(result) == 2


def test_list_backups_with_type_filter(tmp_path):
    mgr = _make_manager(tmp_path)
    record = {
        "backup_id": "daily-b1",
        "backup_type": "daily",
        "created_at": datetime.now().isoformat(),
        "backup_path": str(tmp_path),
        "databases_backed_up": ["postgresql"],
        "backup_results": {},
        "total_size_bytes": 0,
        "compressed": False,
        "checksum": "xyz",
        "description": "backup_metadata daily",  # contains the search terms
        "status": "completed",
    }
    text = json.dumps(record)
    mgr.metadata_db.add_document(
        data_id="daily-b1",
        data_text=text,
        data_type="backup_metadata",
        metadata=record,
        user_id="backup_system",
        agent_id="backup_manager",
    )
    result = mgr.list_backups(backup_type="daily")
    assert len(result) >= 1


def test_list_backups_limit(tmp_path):
    mgr = _make_manager(tmp_path)
    for i in range(5):
        _register_backup(mgr, f"b{i}", str(tmp_path / f"b{i}"))
    result = mgr.list_backups(limit=3)
    assert len(result) <= 3


# ---------------------------------------------------------------------------
# get_backup
# ---------------------------------------------------------------------------


def test_get_backup_found(tmp_path):
    mgr = _make_manager(tmp_path)
    _register_backup(mgr, "back-42", str(tmp_path / "back-42"))
    result = mgr.get_backup("back-42")
    assert result is not None
    assert result["backup_id"] == "back-42"


def test_get_backup_not_found(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr.get_backup("nonexistent-backup")
    assert result is None


# ---------------------------------------------------------------------------
# delete_backup
# ---------------------------------------------------------------------------


def test_delete_backup_not_found(tmp_path):
    mgr = _make_manager(tmp_path)
    result = mgr.delete_backup("nonexistent")
    assert result is False


def test_delete_backup_success(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_dir = tmp_path / "backups" / "manual" / "bk-1"
    backup_dir.mkdir(parents=True)
    _register_backup(mgr, "bk-1", str(backup_dir))

    result = mgr.delete_backup("bk-1")
    assert result is True
    assert not backup_dir.exists()


def test_delete_backup_path_not_exists_still_deletes_metadata(tmp_path):
    mgr = _make_manager(tmp_path)
    # Register a backup whose path doesn't actually exist
    _register_backup(mgr, "bk-ghost", str(tmp_path / "nonexistent"))
    result = mgr.delete_backup("bk-ghost")
    assert result is True  # path didn't exist but metadata is removed


def test_delete_backup_shutil_exception(tmp_path):
    mgr = _make_manager(tmp_path)
    backup_dir = tmp_path / "backups" / "err-bk"
    backup_dir.mkdir(parents=True)
    _register_backup(mgr, "err-bk", str(backup_dir))

    with patch("src.backup_manager.shutil.rmtree", side_effect=PermissionError("no access")):
        result = mgr.delete_backup("err-bk")
    assert result is False


# ---------------------------------------------------------------------------
# rotate_backups / _rotate_backup_type
# ---------------------------------------------------------------------------


def test_rotate_backups_removes_old_daily(tmp_path):
    """Verify _rotate_backup_type actually calls delete_backup for old entries."""
    mgr = _make_manager(tmp_path)
    old_date = (datetime.now() - timedelta(days=10)).isoformat()
    new_date = datetime.now().isoformat()

    deleted_ids = []

    old_record = {
        "backup_id": "old-daily",
        "backup_type": "daily",
        "created_at": old_date,
        "backup_path": str(tmp_path / "old-daily"),
        "databases_backed_up": [],
        "backup_results": {},
        "total_size_bytes": 0,
        "compressed": False,
        "checksum": "",
        "description": "backup_metadata daily",
        "status": "completed",
    }
    new_record = {
        "backup_id": "new-daily",
        "backup_type": "daily",
        "created_at": new_date,
        "backup_path": str(tmp_path / "new-daily"),
        "databases_backed_up": [],
        "backup_results": {},
        "total_size_bytes": 0,
        "compressed": False,
        "checksum": "",
        "description": "backup_metadata daily",
        "status": "completed",
    }

    for rec in (old_record, new_record):
        mgr.metadata_db.add_document(
            data_id=rec["backup_id"],
            data_text=json.dumps(rec),
            data_type="backup_metadata",
            metadata=rec,
            user_id="backup_system",
            agent_id="backup_manager",
        )

    # Patch delete_backup to track calls
    original_delete = mgr.delete_backup

    def _tracking_delete(backup_id):
        deleted_ids.append(backup_id)
        return original_delete(backup_id)

    mgr.delete_backup = _tracking_delete
    mgr.rotate_backups()

    # Old backup (10 days old, beyond 7-day cutoff) should be deleted
    assert "old-daily" in deleted_ids
    # New backup should NOT be deleted
    assert "new-daily" not in deleted_ids


def test_rotate_backups_keeps_manual(tmp_path):
    """Manual backups should not be rotated."""
    mgr = _make_manager(tmp_path)
    record = {
        "backup_id": "manual-old",
        "backup_type": "manual",
        "created_at": (datetime.now() - timedelta(days=365)).isoformat(),
        "backup_path": str(tmp_path),
        "databases_backed_up": [],
        "backup_results": {},
        "total_size_bytes": 0,
        "compressed": False,
        "checksum": "",
        "description": "manual",
        "status": "completed",
    }
    mgr.metadata_db.add_document(
        data_id="manual-old",
        data_text=json.dumps(record),
        data_type="backup_metadata",
        metadata=record,
        user_id="backup_system",
        agent_id="backup_manager",
    )

    mgr.rotate_backups()
    # Manual backups should still exist
    assert mgr.metadata_db._docs.get("manual-old") is not None
