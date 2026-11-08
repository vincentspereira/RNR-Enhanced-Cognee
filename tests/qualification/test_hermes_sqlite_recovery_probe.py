"""Invented restore contents and bounded child transport; no root/AGE use."""
import importlib.util
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/qualify_launch_sqlite_recovery.py'
spec = importlib.util.spec_from_file_location('sqlite_recovery_probe', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_actual_invented_history_and_index_contract():
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE invented_history(version integer primary key,payload blob)')
    connection.execute('CREATE INDEX invented_version_index ON invented_history(version)')
    connection.executemany('INSERT INTO invented_history VALUES (?,?)',
        [(1, b'invented-original'), (2, b'invented-correction'), (3, b'invented-retraction')])
    helper.check_database(connection)
    connection.execute('INSERT INTO invented_history VALUES (4,?)', (b'uncommitted-invented',))
    with pytest.raises(ValueError):
        helper.check_database(connection)
    connection.close()


@pytest.mark.parametrize('mutation', [dict(complete='true'), dict(new_disposable_disk_restore_verified=False),
    dict(private_key='invented-unexpected'), dict(invented_committed_history_verified=False)])
def test_restore_child_cannot_return_extra_fields_or_false_claims(monkeypatch, mutation):
    report = dict(dict.fromkeys(helper.FLAGS, True), new_disposable_disk_restore_verified=True)
    report.update(mutation)
    monkeypatch.setattr(helper.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=0, stdout=json.dumps(report).encode()))
    account = SimpleNamespace(pw_uid=900, pw_gid=900, pw_dir='/invented/home')
    support = dict(owner_program=lambda source: ('invented-public-code', b'invented-public-source\n'), EXECUTABLE='/invented/python')
    with pytest.raises(ValueError):
        helper.owner_report(support, account, b'public', {'mode': 'restore'}, 'restore')


def test_owner_transport_has_no_root_keys_or_inherited_environment(monkeypatch):
    account = SimpleNamespace(pw_uid=900, pw_gid=900, pw_dir='/invented/home')
    packet = dict(mode='restore', snapshot='invented-base64-snapshot')
    report = dict(dict.fromkeys(helper.FLAGS, True), new_disposable_disk_restore_verified=True)
    def run(args, **kwargs):
        assert args[:3] == ['/usr/bin/setpriv', '--no-new-privs', '--']
        assert kwargs['user'] == 900 and kwargs['group'] == 900 and kwargs['extra_groups'] == ()
        assert kwargs['stderr'] is helper.subprocess.DEVNULL
        assert set(kwargs['env']) == {'PATH', 'HOME', 'LANG', 'PYTHONDONTWRITEBYTECODE'}
        assert kwargs['input'] == b'public-code\n' + json.dumps(packet).encode() + b'\n'
        return SimpleNamespace(returncode=0, stdout=json.dumps(report).encode())
    monkeypatch.setattr(helper.subprocess, 'run', run)
    support = dict(owner_program=lambda source: ('public-launcher', b'public-code\n'), EXECUTABLE='/invented/python')
    assert helper.owner_report(support, account, b'public', packet, 'restore') == report


def test_snapshot_component_hash_matches():
    assert helper.hashlib.sha256(SOURCE.with_name('sqlite_profile_snapshot.py').read_bytes()).hexdigest() == helper.CORE_SHA


def test_unprivileged_root_entry_refused_before_any_key_or_file_read(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()
