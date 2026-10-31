"""Actual SQLite WAL/rollback snapshots and refusal boundaries, invented data."""
import importlib.util
from pathlib import Path
import sqlite3

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/sqlite_profile_snapshot.py'
spec = importlib.util.spec_from_file_location('sqlite_profile_snapshot', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.mark.parametrize('mode', ['WAL', 'DELETE'])
def test_committed_data_history_schema_and_blobs_recover_without_sidecars(tmp_path, mode):
    path = tmp_path / 'state.db'
    writer = sqlite3.connect(path)
    writer.execute('PRAGMA journal_mode=' + mode)
    writer.execute('CREATE TABLE invented(id integer primary key, version integer, payload blob)')
    writer.execute('CREATE INDEX invented_version ON invented(version)')
    writer.executemany('INSERT INTO invented(version,payload) VALUES (?,?)', [(1, b'invented-original'), (2, b'invented-correction')])
    writer.commit()
    if mode == 'WAL':
        assert path.with_name(path.name + '-wal').stat().st_size > 0
    writer.execute('INSERT INTO invented(version,payload) VALUES (3,?)', (b'uncommitted',))
    raw = helper.snapshot(path)
    restored = helper.memory_restore(raw)
    assert restored.execute('SELECT version,payload FROM invented ORDER BY id').fetchall() == [(1, b'invented-original'), (2, b'invented-correction')]
    assert restored.execute("SELECT count(*) FROM sqlite_schema WHERE name='invented_version'").fetchone() == (1,)
    assert raw[18:20] == b'\x01\x01'
    assert writer.execute('SELECT count(*) FROM invented').fetchone() == (3,)
    with pytest.raises(sqlite3.OperationalError):
        restored.execute('DELETE FROM invented')
    restored.close()
    writer.rollback()
    writer.close()


def test_symlink_and_non_sqlite_source_refused(tmp_path):
    ordinary = tmp_path / 'ordinary'
    ordinary.write_bytes(b'not a database and not a credential')
    link = tmp_path / 'linked.db'
    link.symlink_to(ordinary)
    for path in (ordinary, link):
        with pytest.raises(helper.SnapshotError):
            helper.snapshot(path)


def test_root_and_outside_or_excluded_source_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 0)
    with pytest.raises(helper.SnapshotError):
        helper.snapshot(tmp_path / 'missing')
    with pytest.raises(helper.SnapshotError):
        helper.open_parent(Path('/tmp/lswa/state.db'), 1000)


def test_malformed_or_live_wal_image_is_not_accepted_as_standalone_restore():
    for raw in (b'', b'SQLite format 3\0' + b'\0' * 1000):
        with pytest.raises(helper.SnapshotError):
            helper.memory_restore(raw)


def test_symlinked_sidecar_refused_before_sqlite_connection(tmp_path):
    path = tmp_path / 'state.db'
    with sqlite3.connect(path) as database:
        database.execute('CREATE TABLE invented(x)')
    path.with_name(path.name + '-wal').symlink_to('/invented/unrelated')
    with pytest.raises(helper.SnapshotError):
        helper.snapshot(path)


def test_snapshot_size_limit_is_enforced(tmp_path, monkeypatch):
    path = tmp_path / 'state.db'
    with sqlite3.connect(path) as database:
        database.execute('CREATE TABLE invented(x)')
        database.execute('INSERT INTO invented VALUES (zeroblob(10000))')
    monkeypatch.setattr(helper, 'MAX_BYTES', 512)
    with pytest.raises(helper.SnapshotError):
        helper.snapshot(path)
