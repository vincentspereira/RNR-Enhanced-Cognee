"""Main operational recovery: real invented SQLite, omissions and refusal behavior."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import socket
import tarfile

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/capture_main_operational_profile_v3.py'
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


def test_online_database_read_transaction_preserves_snapshot_during_live_wal_commit(tmp_path,monkeypatch):
    path=tmp_path/'state.db'
    writer=sqlite3.connect(path)
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE invented(x)')
    writer.execute('INSERT INTO invented VALUES (1)')
    writer.commit()
    original=sqlite3.connect
    class ReadSnapshot:
        def __init__(self, connection): self.connection=connection
        def __getattr__(self,name): return getattr(self.connection,name)
        def backup(self,*args,**kwargs):
            self.connection.backup(*args,**kwargs)
            writer.execute('INSERT INTO invented VALUES (2)')
            writer.commit()
    def connect(*args,**kwargs):
        connection=original(*args,**kwargs)
        return ReadSnapshot(connection) if 'mode=ro' in str(args[0]) else connection
    monkeypatch.setattr(helper.sqlite3,'connect',connect)
    payload,receipt=helper.capture(tmp_path,online_databases=True)
    destination,proof=helper.restore(payload)
    with original(Path(destination)/'state.db') as restored:
        assert restored.execute('SELECT x FROM invented').fetchall()==[(1,)]
    assert writer.execute('SELECT x FROM invented').fetchall()==[(1,),(2,)]
    assert receipt['database_snapshots_consistent'] is True
    assert receipt['database_versions_stable'] is False and receipt['live_database_changes_observed']==1
    assert receipt['database_snapshot_mode']==proof['database_snapshot_mode']=='read_transaction_per_database'
    assert receipt['global_atomic_snapshot_qualified'] is proof['global_atomic_snapshot_qualified'] is False
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


def test_large_sqlite_and_explicit_omissions_preserve_sources(tmp_path):
    profile = tmp_path / 'main'
    profile.mkdir()
    (profile / 'config.yaml').write_bytes(b'invented: preserved\n')
    (profile / 'backups').mkdir()
    (profile / 'backups/older-generation').write_bytes(b'invented-retained-generation')
    (profile / 'cache').mkdir()
    (profile / 'cache/redirect').symlink_to('/invented/not-readable')
    (profile / 'bot-desktop').mkdir()
    ipc = socket.socket(socket.AF_UNIX)
    ipc.bind(str(profile / 'bot-desktop/rfb.sock'))
    writer = sqlite3.connect(profile / 'state.db')
    try:
        writer.execute('CREATE TABLE invented(id integer primary key, payload blob)')
        writer.execute('INSERT INTO invented VALUES (1, zeroblob(20971520))')
        writer.commit()
        assert (profile / 'state.db').stat().st_size > 16 * 1024 * 1024
        payload, receipt = helper.capture(profile)
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            manifest = json.load(archive.extractfile('profile-manifest.json'))
            assert not any(name.startswith(('backups/', 'cache/')) for name in archive.getnames())
            assert 'bot-desktop/rfb.sock' not in archive.getnames()
        assert {row['path'] for row in manifest['omitted']} == {'backups', 'cache', 'bot-desktop/rfb.sock'}
        assert manifest['full_profile_recovery_qualified'] is False
        assert manifest['executable_rebuild_qualified'] is False
        restored, proof = helper.restore(payload)
        assert proof['operational_restore_qualified'] is True
        assert proof['full_profile_recovery_qualified'] is False
        with sqlite3.connect(Path(restored) / 'state.db') as db:
            assert db.execute('SELECT length(payload) FROM invented').fetchone() == (20971520,)
        assert (profile / 'backups/older-generation').read_bytes() == b'invented-retained-generation'
        assert (profile / 'cache/redirect').is_symlink()
        assert receipt['source_logical_writes_performed'] is False
    finally:
        writer.close()
        ipc.close()


def test_unexpected_socket_in_durable_data_is_refused(tmp_path):
    ipc = socket.socket(socket.AF_UNIX)
    try:
        ipc.bind(str(tmp_path / 'unexpected.sock'))
        with pytest.raises(helper.CaptureError): helper.capture(tmp_path)
    finally:
        ipc.close()


@pytest.mark.parametrize('kind', ['socket', 'regular'])
def test_only_the_known_live_gateway_socket_is_omitted(tmp_path, kind):
    gateway = tmp_path / 'gateway.sock'
    ipc = None
    if kind == 'socket':
        ipc = socket.socket(socket.AF_UNIX)
        ipc.bind(str(gateway))
    else:
        gateway.write_bytes(b'invented-durable-regular-data')
    try:
        payload, receipt = helper.capture(tmp_path)
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            manifest = json.load(archive.extractfile('profile-manifest.json'))
            if kind == 'socket':
                assert 'gateway.sock' not in archive.getnames()
                assert manifest['omitted'] == [{'path':'gateway.sock','reason':'runtime_socket_not_restored'}]
                assert gateway.exists()
            else:
                assert archive.extractfile('gateway.sock').read() == b'invented-durable-regular-data'
                assert manifest['omitted'] == []
        original = SOURCE.with_name('capture_main_operational_profile.py')
        assert hashlib.sha256(original.read_bytes()).hexdigest() == 'dba83feebf9ca9ff40125bc76bcc62bbb4876d27007b91cf0ffcd35895ff9677'
    finally:
        if ipc is not None: ipc.close()


def test_excluded_project_is_not_opened_or_archived(tmp_path, monkeypatch):
    excluded = tmp_path / 'lswa-invented-exclusion'
    excluded.mkdir()
    original_open = helper.os.open
    def guarded(path, *args, **kwargs):
        if path == excluded.name:
            pytest.fail('excluded project was opened')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(helper.os, 'open', guarded)
    payload, receipt = helper.capture(tmp_path)
    assert receipt['omitted_entries'] == 1
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        manifest = json.load(archive.extractfile('profile-manifest.json'))
    assert manifest['omitted'] == [{'path':excluded.name, 'reason':'excluded_project_not_traversed'}]


def test_live_coordination_updates_do_not_invalidate_durable_state(tmp_path, monkeypatch):
    (tmp_path/'state').mkdir()
    paths=['spawn-ledger.json','gateway_state.json','state/gateway.heartbeat','state/dashboard_clients.heartbeat']
    for name in paths:(tmp_path/name).write_bytes(b'invented-original-runtime-identity')
    with sqlite3.connect(tmp_path/'state.db') as db:
        db.execute('CREATE TABLE invented(x)')
        db.execute('INSERT INTO invented VALUES (7)')
    original=sqlite3.connect
    def connect(*args, **kwargs):
        if 'mode=ro' in str(args[0]):
            for name in paths:
                target=tmp_path/name
                stage=target.with_name('.'+target.stem+'_abcdefgh.tmp')
                stage.write_bytes(b'invented-replaced-runtime-identity')
                os.replace(stage,target)
        return original(*args,**kwargs)
    monkeypatch.setattr(helper.sqlite3,'connect',connect)
    archive,receipt=helper.capture(tmp_path)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        manifest=json.load(bundle.extractfile('profile-manifest.json'))
        assert all(name not in bundle.getnames() for name in paths)
        assert {row['path'] for row in manifest['omitted']}==set(paths)
        assert {row['reason'] for row in manifest['omitted']}=={'live_process_coordination_not_restored'}
    assert receipt['database_versions_stable'] and receipt['plain_files_stable']
    assert all((tmp_path/name).read_bytes()==b'invented-replaced-runtime-identity' for name in paths)


def test_durable_change_is_refused_even_when_coordination_changes_too(tmp_path,monkeypatch):
    (tmp_path/'spawn-ledger.json').write_bytes(b'invented-pid')
    (tmp_path/'config.yaml').write_bytes(b'invented-original-setting')
    with sqlite3.connect(tmp_path/'state.db') as db:db.execute('CREATE TABLE invented(x)')
    original=sqlite3.connect
    def connect(*args,**kwargs):
        if 'mode=ro' in str(args[0]):
            (tmp_path/'spawn-ledger.json').write_bytes(b'invented-new-pid')
            (tmp_path/'config.yaml').write_bytes(b'invented-changed-setting')
        return original(*args,**kwargs)
    monkeypatch.setattr(helper.sqlite3,'connect',connect)
    with pytest.raises(helper.CaptureError) as result:helper.capture(tmp_path)
    assert result.value.checkpoint=='payload_read'
    assert result.value.reason=='durable_file_changed_before_read'
    assert str(result.value)=='main_operational_capture_refused'


@pytest.mark.parametrize('name',['spawn-ledger.json','.spawn-ledger_abcdefgh.tmp','state/gateway.heartbeat'])
def test_runtime_omissions_never_follow_links(tmp_path,name):
    (tmp_path/'state').mkdir()
    (tmp_path/name).symlink_to('/invented/not-readable')
    with pytest.raises(helper.CaptureError):helper.capture(tmp_path)


def test_valid_long_filename_round_trips_without_weakening_path_validation(tmp_path):
    name='invented-'+('x'*141)
    (tmp_path/name).write_bytes(b'invented-durable-long-name')
    payload,receipt=helper.capture(tmp_path)
    destination,proof=helper.restore(payload)
    assert (Path(destination)/name).read_bytes()==b'invented-durable-long-name'
    assert proof['private_restore_verified'] and receipt['plaintext_archive_written'] is False


def test_oversized_gnu_long_name_refuses_before_any_restore_write(monkeypatch):
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w',format=tarfile.GNU_FORMAT) as archive:
        entry=tarfile.TarInfo('x'*256);entry.mode=0o600;archive.addfile(entry,io.BytesIO(b''))
    monkeypatch.setattr(helper.tempfile,'mkdtemp',lambda **kw:pytest.fail('invalid long name wrote a restore'))
    with pytest.raises(helper.CaptureError):helper.restore(payload.getvalue())


@pytest.mark.parametrize('field', ['full_profile_recovery_qualified', 'executable_rebuild_qualified', 'sqlite_databases',
                                  'snapshot_database_count','global_atomic_snapshot_qualified'])
def test_archive_cannot_inflate_coverage_or_database_count(tmp_path, monkeypatch, field):
    (tmp_path / 'invented.txt').write_bytes(b'invented')
    payload, _ = helper.capture(tmp_path)
    changed = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(payload)) as source, tarfile.open(fileobj=changed, mode='w', format=tarfile.USTAR_FORMAT) as target:
        for member in source:
            raw = source.extractfile(member).read() if member.isfile() else None
            if member.name == 'profile-manifest.json':
                manifest = json.loads(raw)
                manifest[field] = 1 if field == 'sqlite_databases' else True
                raw = json.dumps(manifest).encode()
                member.size = len(raw)
            target.addfile(member, io.BytesIO(raw) if raw is not None else None)
    monkeypatch.setattr(helper.tempfile, 'mkdtemp', lambda **kw:pytest.fail('restore wrote before admission'))
    with pytest.raises(helper.CaptureError): helper.restore(changed.getvalue())
