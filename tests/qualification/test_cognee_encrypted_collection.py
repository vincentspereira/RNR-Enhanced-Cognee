"""Real encrypted/tar fixtures; root ownership is simulated, never host keys."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def collector(monkeypatch):
    path = Path('scripts/windows/backup-v12/capture_cognee.py')
    spec = importlib.util.spec_from_file_location('encrypted_collection', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    real = os.fstat
    def root_stat(fd):
        value = real(fd)
        return NS(**{key: (0 if key == 'st_uid' else getattr(value, key)) for key in
            ('st_uid', 'st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime', 'st_mtime_ns', 'st_ctime_ns')})
    monkeypatch.setattr(module.os, 'fstat', root_stat)
    monkeypatch.setattr(module, 'open_root', lambda root: os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
    return module


@pytest.fixture(scope='module')
def ciphertext(tmp_path_factory):
    root = tmp_path_factory.mktemp('encrypted-collection-key')
    key = root / 'synthetic.key'
    subprocess.run(['/usr/bin/age-keygen', '-o', str(key)], check=True, capture_output=True)
    recipient = subprocess.check_output(['/usr/bin/age-keygen', '-y', str(key)]).decode().strip()
    cipher = subprocess.run(['/usr/bin/age', '-r', recipient], input=b'SYNTHETIC_PROFILE_OR_DATABASE_ONLY',
        check=True, capture_output=True).stdout
    return key, cipher


def pair(root, ciphertext, family, suffix='1234abcd'):
    name = ('memory_' if family == 'database' else 'hermes_profile_') + '20261023T200000Z_' + suffix + ('.dump.age' if family == 'database' else '.tar.age')
    archive = root / name; archive.write_bytes(ciphertext); archive.chmod(0o600)
    value = dict(format='postgres-custom+age' if family == 'database' else 'hermes-home-tar+age',
        complete=True, ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(), signature='a' * 64,
        signing_key_id='synthetic_not_authentic', created_utc='2026-10-23T20:00:00+00:00')
    if family == 'database': value['plaintext_dump_written'] = False
    else: value.update(plaintext_archive_written=False, scope='restricted-hermes-home', source_files=60, source_bytes=205571)
    manifest = root / (name + '.json'); manifest.write_text(json.dumps(value)); manifest.chmod(0o600)
    return archive, manifest


def stream(collector, root, monkeypatch):
    output = io.BytesIO()
    monkeypatch.setattr(sys, 'stdout', NS(buffer=output))
    collector.capture(root, 48)
    return output.getvalue()


def test_both_families_exact_encrypted_bytes_recover_no_keys_and_unchanged_stream_reused(collector, ciphertext, tmp_path, monkeypatch):
    key, cipher = ciphertext
    paths = [pair(tmp_path, cipher, family) for family in ('database', 'hermes_profile')]
    (tmp_path / 'age-recovery-identity.txt').write_text('PRIVATE_KEY_MUST_NOT_BE_COLLECTED')
    (tmp_path / 'backup.json').write_text('PRIVATE_SIGNING_KEY_MUST_NOT_BE_COLLECTED')
    raw = stream(collector, tmp_path, monkeypatch)
    assert stream(collector, tmp_path, monkeypatch) == raw
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        assert set(archive.getnames()) == {p.name for pair_paths in paths for p in pair_paths} | {'collection-coverage.json'}
        metadata = json.load(archive.extractfile('collection-coverage.json'))
        assert metadata['database_completed_pairs'] == metadata['profile_completed_pairs'] == 1
        assert metadata['completed_pairs'] == 2 and not metadata['signed_authenticity_and_decryption_verified']
        recovered = archive.extractfile(paths[1][0].name).read()
        assert recovered == cipher
        result = subprocess.run(['/usr/bin/age', '-d', '-i', str(key)], input=recovered, check=True, capture_output=True)
        assert result.stdout == b'SYNTHETIC_PROFILE_OR_DATABASE_ONLY'
    assert b'PRIVATE_KEY' not in raw


@pytest.mark.parametrize('mutation', ['database-missing', 'profile-missing', 'database-stale', 'profile-stale',
    'bad-hash', 'bad-format', 'unknown-metadata', 'private-scope', 'plaintext', 'key-id', 'signature',
    'date', 'boolean-count', 'wrong-envelope', 'symlink', 'hardlink', 'public-file', 'incomplete-profile'])
def test_invalid_or_missing_family_refuses_before_any_archive_output(collector, ciphertext, tmp_path, monkeypatch, mutation):
    _, cipher = ciphertext
    if mutation != 'database-missing': database = pair(tmp_path, cipher, 'database')
    if mutation != 'profile-missing': profile = pair(tmp_path, cipher, 'hermes_profile')
    if mutation in {'database-stale', 'profile-stale'}:
        p = database[0] if mutation == 'database-stale' else profile[0]
        os.utime(p, (time.time() - 49 * 3600,) * 2)
    if mutation in {'bad-hash', 'bad-format', 'unknown-metadata', 'private-scope', 'plaintext', 'key-id', 'signature', 'date', 'boolean-count'}:
        value = json.loads(profile[1].read_text())
        changes = {'bad-hash': ('ciphertext_sha256', '0' * 64), 'bad-format': ('format', 'postgres-custom+age'),
            'unknown-metadata': ('PRIVATE', 'SECRET'), 'private-scope': ('scope', 'wrong'),
            'plaintext': ('plaintext_archive_written', True), 'key-id': ('signing_key_id', 'PRIVATE SECRET'),
            'signature': ('signature', 'not-a-signature'), 'date': ('created_utc', 'PRIVATE_SECRET'),
            'boolean-count': ('source_files', True)}
        key, value2 = changes[mutation]; value[key] = value2; profile[1].write_text(json.dumps(value))
    if mutation == 'wrong-envelope': profile[0].write_bytes(b'PLAINTEXT_PRIVATE')
    if mutation == 'symlink':
        profile[0].rename(tmp_path / 'retained-cipher'); profile[0].symlink_to('retained-cipher')
    if mutation == 'hardlink': os.link(profile[0], tmp_path / 'retained-alias')
    if mutation == 'public-file': profile[0].chmod(0o644)
    if mutation == 'incomplete-profile': profile[1].rename(tmp_path / 'incomplete.json.partial')
    output = io.BytesIO(); monkeypatch.setattr(sys, 'stdout', NS(buffer=output))
    with pytest.raises((collector.CollectionError, ValueError, OSError)): collector.capture(tmp_path, 48)
    assert not output.getvalue()


def test_changed_ciphertext_during_stream_stops_producer_without_completion_marker(collector, ciphertext, tmp_path, monkeypatch):
    _, cipher = ciphertext
    pair(tmp_path, cipher, 'database'); profile, _ = pair(tmp_path, cipher, 'hermes_profile')
    original = collector.add_file
    def add(*args, **kwargs):
        if args[2] == profile.name: profile.write_bytes(cipher + b'CHANGED')
        return original(*args, **kwargs)
    monkeypatch.setattr(collector, 'add_file', add)
    output = io.BytesIO(); monkeypatch.setattr(sys, 'stdout', NS(buffer=output))
    with pytest.raises(collector.CollectionError): collector.capture(tmp_path, 48)
    assert b'collection-coverage.json' not in output.getvalue()


def test_verify_only_reports_both_families_without_export_or_secret_values(collector, ciphertext, tmp_path, capsys):
    _, cipher = ciphertext
    pair(tmp_path, cipher, 'database'); pair(tmp_path, cipher, 'hermes_profile')
    collector.capture(tmp_path, 48, verify_only=True)
    output = capsys.readouterr().out
    value = json.loads(output)
    assert value['complete'] and value['profile_completed_pairs'] == value['database_completed_pairs'] == 1
    assert not value['files_written'] and not value['backup_started'] and not value['cloud_upload']
    assert not value['signed_authenticity_and_decryption_verified'] and not value['credentials_read']
    assert '.tar.age' not in output and '.dump.age' not in output


@pytest.mark.parametrize('mutation', [None, 'public-root', 'writable-parent', 'ancestor-link'])
def test_root_descriptor_walk_refuses_links_and_unprotected_directories(collector, tmp_path, monkeypatch, mutation):
    spec = importlib.util.spec_from_file_location('collector_root_guard', Path('scripts/windows/backup-v12/capture_cognee.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    virtual = tmp_path / 'virtual-root'; (virtual / 'protected/backup').mkdir(parents=True)
    (virtual / 'protected').chmod(0o755); (virtual / 'protected/backup').chmod(0o700)
    path = Path('/protected/backup')
    if mutation == 'public-root': (virtual / 'protected/backup').chmod(0o755)
    if mutation == 'writable-parent': (virtual / 'protected').chmod(0o777)
    if mutation == 'ancestor-link':
        (virtual / 'alias').symlink_to('protected'); path = Path('/alias/backup')
    original = os.open
    monkeypatch.setattr(os, 'open', lambda name, flags, *a, **kw: original(virtual if name == '/' else name, flags, *a, **kw))
    if mutation:
        with pytest.raises((module.CollectionError, OSError)): module.open_root(path)
    else:
        fd = module.open_root(path)
        try: assert os.listdir(fd) == []
        finally: os.close(fd)


def test_future_ciphertext_timestamp_refused_before_output(collector, ciphertext, tmp_path, monkeypatch):
    _, cipher = ciphertext
    pair(tmp_path, cipher, 'database'); profile, _ = pair(tmp_path, cipher, 'hermes_profile')
    os.utime(profile, (time.time() + 3600,) * 2)
    output = io.BytesIO(); monkeypatch.setattr(sys, 'stdout', NS(buffer=output))
    with pytest.raises(collector.CollectionError): collector.capture(tmp_path, 48)
    assert output.getvalue() == b''


def test_actual_restic_rejects_missing_profile_producer_then_restores_both_encrypted_families(collector, ciphertext, tmp_path):
    _, cipher = ciphertext
    source = tmp_path / 'source'; source.mkdir()
    database = pair(source, cipher, 'database')
    helper = Path('scripts/windows/backup-v12/capture_cognee.py').resolve()
    producer = tmp_path / 'synthetic-root-producer.py'
    producer.write_text('''import importlib.util, os, sys
from pathlib import Path
class RootMetadata:
    def __init__(self, value): self.value = value
    def __getattr__(self, name): return 0 if name == "st_uid" else getattr(self.value, name)
spec=importlib.util.spec_from_file_location("collector", sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
real=os.fstat
module.os.fstat=lambda fd: RootMetadata(real(fd))
module.open_root=lambda root: os.open(root, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try: module.capture(Path(sys.argv[2]), 48)
except Exception: raise SystemExit(9) from None
''')
    restic = Path(os.environ.get('RNR_RESTIC', str(Path.home() / '.local/share/rnr-backup-tools/restic/0.19.1/restic')))
    environment = {k: v for k, v in os.environ.items() if not k.startswith('RESTIC_')}
    environment['RESTIC_PASSWORD'] = 'synthetic-profile-collection-test-only'
    repository = tmp_path / 'repo'
    def run(*args):
        return subprocess.run([str(restic), '-r', str(repository), '--no-cache', *args],
            env=environment, capture_output=True, timeout=60)
    assert run('init').returncode == 0
    args = ('backup', '--stdin-from-command', '--stdin-filename', 'encrypted-services.tar', '--',
        sys.executable, '-I', str(producer), str(helper), str(source))
    assert run(*args).returncode != 0
    assert json.loads(run('snapshots', '--json').stdout) == []
    profile = pair(source, cipher, 'hermes_profile')
    assert run(*args).returncode == 0
    restored = tmp_path / 'restored'
    assert run('restore', 'latest', '--target', str(restored), '--verify').returncode == 0
    with tarfile.open(restored / 'encrypted-services.tar') as archive:
        assert archive.extractfile(database[0].name).read() == cipher
        assert archive.extractfile(profile[0].name).read() == cipher
        value = json.load(archive.extractfile('collection-coverage.json'))
        assert value['database_completed_pairs'] == value['profile_completed_pairs'] == 1
    assert run('check', '--read-data').returncode == 0


@pytest.mark.parametrize('mutation', ['missing-profile', 'stale-database', 'private-parser-error'])
def test_inventory_failure_returns_safe_family_counts_or_category_without_raw_values(collector, ciphertext, tmp_path, capsys, monkeypatch, mutation):
    _, cipher = ciphertext
    database, _ = pair(tmp_path, cipher, 'database')
    if mutation != 'missing-profile': pair(tmp_path, cipher, 'hermes_profile')
    if mutation == 'stale-database': os.utime(database, (time.time() - 49 * 3600,) * 2)
    if mutation == 'private-parser-error':
        def parse(*a, **kw): raise ValueError('PRIVATE_KEY_AND_PATH')
        monkeypatch.setattr(collector, 'capture', parse)
    with pytest.raises(SystemExit): collector.verify_inventory(tmp_path)
    output = capsys.readouterr().out; result = json.loads(output)
    assert 'PRIVATE' not in output
    assert not result['complete'] and not result['files_written'] and not result['backup_started']
    if mutation == 'missing-profile': assert result['diagnostics']['profile_pairs'] == 0 and not result['diagnostics']['profile_recent']
    if mutation == 'stale-database': assert not result['diagnostics']['database_recent']
    if mutation == 'private-parser-error': assert result['category'] == 'collection_read_or_parse_failed'
