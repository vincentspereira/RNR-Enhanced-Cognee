"""Actual invented profile/WAL archive and disposable restore behavior."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import tarfile

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/capture_named_profile.py'
spec = importlib.util.spec_from_file_location('named_profile_capture', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_real_wal_state_plain_files_and_private_disposable_restore(tmp_path):
    (tmp_path / '.env').write_bytes(b'INVENTED_UNRELATED=preserved\n')
    (tmp_path / 'workspace').mkdir()
    (tmp_path / 'workspace/invented.txt').write_bytes(b'invented-workspace')
    writer = sqlite3.connect(tmp_path / 'state.db')
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE invented(version integer primary key,payload blob)')
    writer.executemany('INSERT INTO invented VALUES (?,?)', [(1, b'original'), (2, b'corrected'), (3, b'retracted')])
    writer.commit()
    writer.execute('INSERT INTO invented VALUES (4,?)', (b'not-committed',))
    payload, receipt = helper.capture(tmp_path)
    destination, restored = helper.restore(payload)
    assert receipt['sqlite_databases'] == 1 and receipt['sidecars_rebuilt'] == 2
    assert receipt['database_versions_stable'] and receipt['plain_files_stable']
    assert restored['restored_profile_executed'] is False
    target = Path(destination)
    assert (target / '.env').read_bytes() == (tmp_path / '.env').read_bytes()
    assert (target / 'workspace/invented.txt').read_bytes() == b'invented-workspace'
    with sqlite3.connect(target / 'state.db') as recovered:
        assert recovered.execute('SELECT count(*) FROM invented').fetchone() == (3,)
    assert not (target / 'state.db-wal').exists()
    assert writer.execute('SELECT count(*) FROM invented').fetchone() == (4,)
    writer.rollback()
    writer.close()


@pytest.mark.parametrize('kind', ['symlink', 'hardlink', 'orphan_sidecar', 'reserved_manifest'])
def test_unsupported_source_is_refused(tmp_path, kind):
    (tmp_path / 'invented').write_bytes(b'invented')
    if kind == 'symlink':
        (tmp_path / 'redirect').symlink_to('/invented/unrelated')
    elif kind == 'hardlink':
        os.link(tmp_path / 'invented', tmp_path / 'alias')
    elif kind == 'orphan_sidecar':
        (tmp_path / 'orphan-wal').write_bytes(b'invented')
    else:
        (tmp_path / 'profile-manifest.json').write_text('{}')
    with pytest.raises(helper.CaptureError):
        helper.capture(tmp_path)


def test_committed_database_change_during_capture_refuses_generation(tmp_path, monkeypatch):
    writer = sqlite3.connect(tmp_path / 'state.db')
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE invented(x)')
    writer.commit()
    original_connect = sqlite3.connect
    class MonitoredConnection:
        def __init__(self, connection): self.connection = connection
        def execute(self, *args): return self.connection.execute(*args)
        def close(self): self.connection.close()
        def backup(self, *args, **kwargs):
            self.connection.backup(*args, **kwargs)
            writer.execute('INSERT INTO invented VALUES (1)')
            writer.commit()
    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        return MonitoredConnection(connection) if 'mode=ro' in str(args[0]) else connection
    monkeypatch.setattr(helper.sqlite3, 'connect', connect)
    with pytest.raises(helper.CaptureError):
        helper.capture(tmp_path)
    writer.close()


@pytest.mark.parametrize('kind', ['traversal', 'symlink'])
def test_archive_cannot_escape_restore_root_or_write_before_validation(monkeypatch, kind):
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo('../escape' if kind == 'traversal' else 'link')
        member.mode = 0o600
        if kind == 'symlink':
            member.type = tarfile.SYMTYPE
            member.linkname = '/invented/unrelated'
        archive.addfile(member, io.BytesIO(b''))
    monkeypatch.setattr(helper.tempfile, 'mkdtemp', lambda **kw: pytest.fail('restore wrote before admission'))
    with pytest.raises(helper.CaptureError):
        helper.restore(payload.getvalue())


def test_root_cannot_capture_profiles(monkeypatch, tmp_path):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 0)
    with pytest.raises(helper.CaptureError):
        helper.capture(tmp_path)


def test_new_plain_file_during_database_open_is_not_silently_omitted(tmp_path, monkeypatch):
    writer = sqlite3.connect(tmp_path / 'state.db')
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE invented(x)')
    writer.commit()
    original_connect = sqlite3.connect
    def connect(*args, **kwargs):
        if 'mode=ro' in str(args[0]):
            (tmp_path / 'new-invented-file').write_bytes(b'invented-change')
        return original_connect(*args, **kwargs)
    monkeypatch.setattr(helper.sqlite3, 'connect', connect)
    with pytest.raises(helper.CaptureError):
        helper.capture(tmp_path)
    writer.close()


def test_cold_wal_reader_bookkeeping_is_captured_without_raw_sidecar_members(tmp_path):
    path = tmp_path / 'cold.db'
    writer = sqlite3.connect(path)
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE invented(x)')
    writer.execute('INSERT INTO invented VALUES (7)')
    writer.commit()
    writer.close()
    assert not (tmp_path / 'cold.db-wal').exists()
    payload, receipt = helper.capture(tmp_path)
    destination, report = helper.restore(payload)
    with sqlite3.connect(Path(destination) / 'cold.db') as database:
        assert database.execute('SELECT x FROM invented').fetchall() == [(7,)]
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:') as archive:
        assert not any(member.name.endswith(('-wal', '-shm')) for member in archive)


def test_new_unrelated_sidecar_is_not_admitted(tmp_path, monkeypatch):
    path = tmp_path / 'cold.db'
    writer = sqlite3.connect(path)
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE invented(x)')
    writer.commit()
    writer.close()
    original_connect = sqlite3.connect
    def connect(*args, **kwargs):
        if 'mode=ro' in str(args[0]):
            (tmp_path / 'unrelated-wal').write_bytes(b'invented')
        return original_connect(*args, **kwargs)
    monkeypatch.setattr(helper.sqlite3, 'connect', connect)
    with pytest.raises(helper.CaptureError):
        helper.capture(tmp_path)


def test_candidate_restore_is_new_private_directory_in_its_owners_home(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir(mode=0o700)
    (source / '.env').write_bytes(b'INVENTED_PREFERENCE=preserved\n')
    payload, receipt = helper.capture(source)
    import tempfile
    # An account HOME must have protected ancestors. /tmp is intentionally
    # rejected by the production owner-home guard, so use ignored test scratch
    # under this checkout instead of relaxing that guard for a temp fixture.
    home = Path(tempfile.mkdtemp(prefix='candidate-home-', dir=SOURCE.parents[3] / '.pytest_cache'))
    from types import SimpleNamespace
    monkeypatch.setattr(helper.pwd, 'getpwuid', lambda uid: SimpleNamespace(pw_dir=str(home)))
    destination, proof = helper.restore(payload, owner_home=True)
    assert Path(destination).parent == home
    assert (Path(destination) / '.env').read_bytes() == (source / '.env').read_bytes()
    assert proof['private_restore_verified'] and not proof['restored_profile_executed']


def test_caller_cannot_supply_destination_path_via_owner_home(tmp_path):
    with pytest.raises(helper.CaptureError):
        helper.restore(b'invented', owner_home='/invented/another-home')
