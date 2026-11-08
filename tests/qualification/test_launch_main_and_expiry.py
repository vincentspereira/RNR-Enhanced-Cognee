"""Real archive behavior and explicit expiry recovery, using invented data."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import sqlite3
import tempfile
import time

import pytest

ROOT = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
CONFIG = runpy.run_path(str(ROOT / 'main_candidate_configuration.py'), run_name='main_configuration_tests')
RECOVERY = runpy.run_path(str(ROOT / 'main_memory_profile_recovery.py'), run_name='main_link_recovery_tests')
EXPIRED = runpy.run_path(str(ROOT / 'expired_candidate_recovery.py'), run_name='expired_recovery_tests')
ISSUER = runpy.run_path(str(ROOT / 'provision_pilot_access.py'), run_name='expired_issuer_tests')
RENEW = runpy.run_path(str(ROOT / 'renew_pilot_access.py'), run_name='expired_renewal_tests')
LIFECYCLE = runpy.run_path(str(ROOT / 'fleet_credential_lifecycle.py'), run_name='unchanged_lifecycle_tests')


def settings():
    return dict(model=dict(provider='zai', default='glm-5.3-flash'), gateway=dict(multiplex_profiles=True, keep='invented'),
                mcp_servers=dict(files=dict(command='npx', args=['-y', '@modelcontextprotocol/server-filesystem', CONFIG['ORIGINAL_WORKSPACE']]),
                                 two={'invented': 2}, three={'invented': 3}, four={'invented': 4}),
                browser=dict(invented='preserve'), platforms=dict(invented='preserve'))


def test_only_main_filesystem_root_and_memory_selection_change():
    original = settings(); before = copy.deepcopy(original)
    home = Path('/var/lib/enhanced-cognee-profiles/' + 'a' * 16)
    changed = CONFIG['transform'](original, home)
    assert original == before and changed['memory'] == {'provider': 'enhanced_cognee'}
    changed.pop('memory')
    changed['mcp_servers']['files']['args'][-1] = CONFIG['ORIGINAL_WORKSPACE']
    assert changed == original


@pytest.mark.parametrize('damage', ['duplicate', 'command', 'package', 'selected', 'gateway', 'count'])
def test_ambiguous_or_changed_main_config_refuses(damage):
    value = settings()
    if damage == 'duplicate': value['mcp_servers']['two'] = copy.deepcopy(value['mcp_servers']['files'])
    elif damage == 'command': value['mcp_servers']['files']['command'] = 'shell'
    elif damage == 'package': value['mcp_servers']['files']['args'][1] = 'unreviewed-server'
    elif damage == 'selected': value['memory'] = {'provider': 'already-selected'}
    elif damage == 'gateway': value['gateway']['multiplex_profiles'] = False
    else: value['mcp_servers'].pop('four')
    with pytest.raises(ValueError): CONFIG['transform'](value, Path('/var/lib/enhanced-cognee-profiles/' + 'a' * 16))


def test_main_archive_rebuilds_only_fixed_provider_with_sqlite_and_long_names(tmp_path):
    core = runpy.run_path(str(ROOT / 'capture_main_operational_profile_v3.py'), run_name='main_memory_core_test')
    profile = tmp_path / 'profile'; (profile / 'plugins').mkdir(parents=True, mode=0o700)
    (profile / RECOVERY['LINK']).symlink_to(RECOVERY['TARGET'])
    (profile / 'enhanced_cognee.json').write_text(json.dumps(dict(base_url='http://127.0.0.1:28080', capture_policy='selected', include_shared=True)))
    (profile / ('long-' + 'a' * 110)).write_bytes(b'invented-durable-data')
    with sqlite3.connect(profile / 'state.db') as connection:
        connection.execute('CREATE TABLE invented(x)'); connection.execute('INSERT INTO invented VALUES(7)')
    original_omission = core['capture'].__globals__['omission_reason']
    archive, captured = RECOVERY['capture'](core, profile)
    assert captured['sqlite_databases'] == 1 and captured['omitted_entries'] == 1
    assert captured['database_snapshot_mode'] == 'read_transaction_per_database'
    assert core['capture'].__globals__['omission_reason'] is original_omission
    # Restore path adaptation is ONLY a test fixture; production keeps owner_home=True.
    old = core['restore']; core['restore'] = lambda data, owner_home: old(data)
    destination, receipt = RECOVERY['restore'](core, archive)
    restored = Path(destination)
    assert (restored / RECOVERY['LINK']).is_symlink()
    assert os.readlink(restored / RECOVERY['LINK']) == RECOVERY['TARGET']
    assert receipt['pinned_provider_binding_reconstructed'] is True
    with sqlite3.connect(restored / 'state.db') as connection:
        assert connection.execute('SELECT x FROM invented').fetchall() == [(7,)]


def test_wrong_provider_target_is_refused_before_capture(tmp_path):
    profile = tmp_path / 'profile'; (profile / 'plugins').mkdir(parents=True)
    (profile / RECOVERY['LINK']).symlink_to('/invented/unreviewed')
    with pytest.raises(ValueError): RECOVERY['capture']({}, profile)


def expiry_fixture(tmp_path, monkeypatch, *, expired=True):
    core = dict(ISSUER); now = int(time.time()); key = b'invented-signing-key-for-tests-only'
    old = dict(core['IDENTITY'], iat=now - (90000 if expired else 10), exp=now - (3600 if expired else -86390))
    token = core['sign_claims'](old, key); bundle = core['make_bundle'](key, now)
    raw = ('UNCHANGED=invented\nENHANCED_COGNEE_ACCESS_TOKEN=' + token + '\n').encode()
    (tmp_path / '.env').write_bytes(raw)
    for name, value in [('config.yaml', b'preserve'), ('auth.json', b'preserve'), ('enhanced_cognee.json',
        json.dumps(dict(base_url='http://127.0.0.1:28080', capture_policy='selected', include_shared=True)).encode())]:
        (tmp_path / name).write_bytes(value)
    for path in tmp_path.iterdir(): path.chmod(0o600)
    accepted = dict(ready=True, schema_version=3, encryption='AES-256-GCM', active_records=0, pending_change_events=0,
        tenant_id=core['IDENTITY']['tenant'], project_id=core['IDENTITY']['project_id'], subject=core['IDENTITY']['sub'])
    core['api_status'] = lambda value=None: (200, accepted) if value == bundle['token'] else (401, {})
    entry = dict(uid=os.geteuid(), enabled=False, reload_qualified=False, launch_binding_qualified=False,
        subject=core['IDENTITY']['sub'], agent_id=core['IDENTITY']['agent_id'], tenant=core['IDENTITY']['tenant'], project_id=core['IDENTITY']['project_id'])
    return core, bundle, entry, raw


def test_expired_recovery_is_atomic_preserves_settings_and_closes_journal(tmp_path, monkeypatch):
    core, bundle, entry, original = expiry_fixture(tmp_path, monkeypatch)
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY); phases = []
    try:
        result = EXPIRED['recover'](core, RENEW, LIFECYCLE, descriptor, bundle, os.geteuid(), entry, checkpoint=phases.append)
    finally: os.close(descriptor)
    assert result['expired_candidate_recovered'] is True and result['unattended_renewal_qualified'] is False
    assert (tmp_path / 'config.yaml').read_bytes() == (tmp_path / 'auth.json').read_bytes() == b'preserve'
    assert RENEW['environment'](core, (tmp_path / '.env').read_bytes()) == bundle['token']
    assert next(tmp_path.glob('.env-before-cognee-renew-*')).read_bytes() == original
    assert phases == ['prepared', 'published'] and len(list(tmp_path.glob('.cognee-renewal-*.done.json'))) == 1


@pytest.mark.parametrize('damage', ['enabled', 'reload', 'scope', 'unexpired', 'old_accepted', 'new_denied', 'stale', 'root'])
def test_expiry_recovery_refuses_unapproved_paths_before_environment_change(tmp_path, monkeypatch, damage):
    core, bundle, entry, original = expiry_fixture(tmp_path, monkeypatch, expired=damage != 'unexpired')
    if damage == 'enabled': entry['enabled'] = True
    elif damage == 'reload': entry['reload_qualified'] = True
    elif damage == 'scope': entry['subject'] = 'other'
    elif damage == 'old_accepted': core['api_status'] = lambda *a: (200, {})
    elif damage == 'new_denied': core['api_status'] = lambda *a: (401, {})
    elif damage == 'stale': bundle['claims']['iat'] -= 1000
    elif damage == 'root': monkeypatch.setattr(EXPIRED['os'], 'geteuid', lambda: 0)
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(Exception): EXPIRED['recover'](core, RENEW, LIFECYCLE, descriptor, bundle, entry['uid'], entry)
    finally: os.close(descriptor)
    assert (tmp_path / '.env').read_bytes() == original
    assert not list(tmp_path.glob('.env-before-cognee-renew-*'))


def test_unattended_lifecycle_still_refuses_expired_profile(tmp_path, monkeypatch):
    core, bundle, entry, original = expiry_fixture(tmp_path, monkeypatch)
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ValueError, match='expired_profile_requires_operator_recovery'):
            LIFECYCLE['publish'](core, RENEW, descriptor, bundle, os.geteuid())
    finally: os.close(descriptor)
    assert (tmp_path / '.env').read_bytes() == original


@pytest.mark.parametrize('interruption', ['prepared', 'published'])
def test_interrupted_expired_recovery_retains_journal_and_does_not_replay(tmp_path, monkeypatch, interruption):
    core, bundle, entry, original = expiry_fixture(tmp_path, monkeypatch)
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    def checkpoint(phase):
        if phase == interruption: raise RuntimeError('invented interruption')
    try:
        with pytest.raises(RuntimeError): EXPIRED['recover'](core, RENEW, LIFECYCLE, descriptor, bundle, os.geteuid(), entry, checkpoint=checkpoint)
        journals = list(tmp_path.glob('.cognee-renewal-*.json'))
        assert len(journals) == 1 and not list(tmp_path.glob('.cognee-renewal-*.done.json'))
        current = (tmp_path / '.env').read_bytes()
        assert (current == original) is (interruption == 'prepared')
        # Reconcile only the retained journal; no new credential is published.
        assert RENEW['reconcile'](core, descriptor, os.geteuid(), current) == 1
        assert (tmp_path / '.env').read_bytes() == current
        assert len(list(tmp_path.glob('.cognee-renewal-*.done.json'))) == 1
    finally: os.close(descriptor)


@pytest.mark.parametrize('damage', [None, 'after_receipt', 'symlink'])
def test_qualified_key_inspection_is_readonly_and_rejects_changed_fixture(damage):
    inspector = runpy.run_path(str(ROOT / 'inspect_qualified_model_key.py'), run_name='qualified_model_key_test')
    archive = ROOT.parents[2] / '.archive'
    archive.mkdir(mode=0o700, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix='qualified-key-fixture-', dir=archive))
    path = profile / '.env'; key = 'invented-model-key-never-returned'
    if damage == 'symlink':
        path.symlink_to('/invented/never-follow')
        with pytest.raises(OSError): inspector['digest'](profile, os.geteuid(), time.time_ns())
        return
    path.write_text('GLM_API_KEY=' + key + '\nGLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4\n')
    path.chmod(0o600)
    before = path.stat(); boundary = time.time_ns()
    if damage == 'after_receipt':
        with pytest.raises(ValueError): inspector['digest'](profile, os.geteuid(), before.st_ctime_ns - 1)
    else:
        result = inspector['digest'](profile, os.geteuid(), boundary)
        assert result == dict(complete=True, model_key_sha256=hashlib.sha256(key.encode()).hexdigest(), fixture_unchanged_since_receipt=True)
        assert key not in str(result)
    assert path.stat().st_atime_ns == before.st_atime_ns
