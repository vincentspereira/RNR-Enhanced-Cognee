"""Signed generation binding and root/owner transport, no real profile data."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/backup_launch_named_profiles.py'
spec = importlib.util.spec_from_file_location('named_backup', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def manifest():
    return dict(format='hermes-named-profile-sqlite-tar+age', complete=True,
                source_profile_id='a' * 16, ciphertext_sha256='b' * 64)


@pytest.mark.parametrize('field,value', [('complete', False), ('source_profile_id', 'c' * 16),
    ('ciphertext_sha256', 'c' * 64), ('format', 'other'), ('extra', 'invented')])
def test_signed_generation_cannot_be_changed_or_rebound(field, value):
    key = b'invented-signing-key-never-an-owner-packet'
    value_set = manifest()
    value_set['signature'] = helper.signature(value_set, key)
    helper.verify_manifest(value_set, key, 'a' * 16, 'b' * 64)
    value_set[field] = value
    with pytest.raises(ValueError):
        helper.verify_manifest(value_set, key, 'a' * 16, 'b' * 64)


def test_root_keys_are_not_accepted_as_owner_packet_fields():
    with pytest.raises(ValueError):
        helper.owner({}, None, b'public', dict(mode='capture', profile='/invented', recipient='invented',
            core='public', private_key='invented-secret'))


def test_fixed_owner_transport_uses_only_public_code_recipient_and_profile(monkeypatch):
    core = SOURCE.with_name('capture_named_profile.py').read_text()
    packet = dict(mode='capture', core=core, recipient='age1inventedpublicrecipient', profile='/invented/profile')
    report = dict(complete=True, ciphertext='invented-base64', receipt=dict(files=3, source_bytes=4000,
        sqlite_databases=1, sidecars_rebuilt=2, database_versions_stable=True,
        plain_files_stable=True, plaintext_archive_written=False))
    def run(args, **kwargs):
        assert args[:3] == ['/usr/bin/setpriv', '--no-new-privs', '--']
        assert kwargs['user'] == 1000 and kwargs['group'] == 1000 and kwargs['extra_groups'] == ()
        assert set(kwargs['env']) == {'PATH', 'HOME', 'LANG', 'PYTHONDONTWRITEBYTECODE'}
        assert kwargs['input'] == b'public-source\n' + json.dumps(packet).encode() + b'\n'
        assert kwargs['stderr'] is helper.subprocess.DEVNULL
        return SimpleNamespace(returncode=0, stdout=json.dumps(report).encode())
    monkeypatch.setattr(helper.subprocess, 'run', run)
    support = dict(EXECUTABLE='/invented/python', owner_program=lambda source: ('public-launcher', b'public-source\n'))
    assert helper.owner(support, SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_dir='/invented'), b'public', packet) == report


def test_component_source_pin_matches():
    assert hashlib.sha256(SOURCE.with_name('capture_named_profile.py').read_bytes()).hexdigest() == helper.CORE_SHA


def test_unprivileged_parent_cannot_read_keys_or_publish(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()


def test_actual_source_and_packet_pipe_protocol_without_privileged_identity_changes(monkeypatch):
    support_spec = importlib.util.spec_from_file_location('owner_program_support', SOURCE.with_name('qualify_launch_isolated_accounts.py'))
    support_module = importlib.util.module_from_spec(support_spec)
    support_spec.loader.exec_module(support_module)
    support = dict(EXECUTABLE=sys.executable, owner_program=support_module.owner_program)
    core = SOURCE.with_name('capture_named_profile.py').read_text()
    packet = dict(mode='capture', core=core, recipient='age1invented', profile='/invented')
    source = b'''import json,sys
def child():
    p=json.loads(sys.stdin.buffer.readline(33554433))
    assert set(p)=={'mode','core','recipient','profile'}
    print(json.dumps({'complete':True,'ciphertext':'invented', 'receipt':{'files':3,'source_bytes':4096,
        'sqlite_databases':1,'sidecars_rebuilt':2,'database_versions_stable':True,
        'plain_files_stable':True,'plaintext_archive_written':False}}))
'''
    real_run = subprocess.run
    def run(args, **kwargs):
        # Only the pipe framing executes here. Identity transitions themselves
        # remain protected host checks, not falsely simulated by this test.
        for key in ('user', 'group', 'extra_groups'):
            kwargs.pop(key)
        return real_run(args, **kwargs)
    monkeypatch.setattr(helper.subprocess, 'run', run)
    account = SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_dir='/invented')
    assert helper.owner(support, account, source, packet)['receipt']['files'] == 3


def failed_attempt():
    return dict(complete=False, source_revision=helper.BASE.name,
        operator_helper_sha256='33a2081c9e83d71875c00ddda94e20007e31bc029051f53a44e3076c061acec5',
        selected_named_profiles=42, failure_phase='owner_capture', owner_failure_kind='CaptureError',
        current_profile_id='534e43407c192971', encrypted_signed_generations_created=0,
        disposable_restores_qualified=0, sqlite_databases_recovered=0)


@pytest.mark.parametrize('field,value', [('complete', True), ('encrypted_signed_generations_created', 1),
    ('disposable_restores_qualified', 1), ('sqlite_databases_recovered', 1),
    ('encrypted_signed_generations_created', False), ('current_profile_id', 'other'),
    ('operator_helper_sha256', 'other')])
def test_continuation_refuses_completed_work_and_wrong_attempt(field, value):
    report = failed_attempt()
    helper.zero_generation_attempt(report)
    report[field] = value
    with pytest.raises(ValueError):
        helper.zero_generation_attempt(report)
