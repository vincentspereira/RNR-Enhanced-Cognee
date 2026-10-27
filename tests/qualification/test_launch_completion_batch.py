"""Consolidated job contracts, no-replay controls and per-profile checkpoints."""
import ast
import hashlib
import io
import json
import os
import urllib.request
from urllib.error import HTTPError
from pathlib import Path
import runpy
import time
from types import SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
BATCH = runpy.run_path(str(DIRECTORY / 'launch_completion_batch.py'), run_name='batch_unit_tests')
OWNER = runpy.run_path(str(DIRECTORY / 'launch_completion_owner.py'), run_name='batch_owner_unit_tests')
OLD = runpy.run_path(str(DIRECTORY / 'qualify_launch_candidate_reload.py'), run_name='retained_reload_contract')


def entry(index=1):
    ident = format(index, '016x')
    return dict(name='candidate_' + ident, user='ecbot_' + ident, uid=2000 + index,
        home='/var/lib/enhanced-cognee-profiles/' + ident, profile='/var/lib/enhanced-cognee-profiles/' + ident + '/.hermes',
        subject='candidate_' + ident, agent_id='candidate_' + ident, tenant='qualification', project_id='p_' + ident,
        enabled=False, reload_qualified=False, launch_binding_qualified=False)


def test_frozen_owner_sources_and_root_driver_match_reviewed_public_derivations():
    for name, digest in dict(BATCH['PINS'], **OWNER['PINS']).items():
        if name in {'provision_pilot_access.py', 'renew_fleet_credentials.py'}: continue
        assert hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() == digest, name
    stage = runpy.run_path(str(DIRECTORY / 'stage_launch_candidate_issuer.py'), run_name='derive_fleet_public')
    review = runpy.run_path(str(DIRECTORY / 'prepare_launch_fleet_review.py'), run_name='derive_fleet_review')
    core, driver = stage['build_sources']((DIRECTORY / 'provision_pilot_access.py').read_bytes(),
        (DIRECTORY / 'renew_fleet_credentials.py').read_bytes(), (DIRECTORY / 'prepare_launch_candidate_provider_v2.py').read_bytes())
    assert hashlib.sha256(core).hexdigest() == OWNER['PINS']['provision_pilot_access.py']
    assert hashlib.sha256(review['rebind_driver'](driver)).hexdigest() == BATCH['DRIVER_SHA']
    helper = runpy.run_path(str(DIRECTORY / 'qualify_launch_isolated_accounts.py'), run_name='batch_protocol')
    helper['owner_program']((DIRECTORY / 'launch_completion_owner.py').read_bytes())
    controller = runpy.run_path(str(DIRECTORY / 'launch_control.py'), run_name='completion_controller_pin')
    assert controller['COMPLETION_BATCH_SHA'] == hashlib.sha256((DIRECTORY / 'launch_completion_batch.py').read_bytes()).hexdigest()


@pytest.mark.parametrize('mode', ['implementation', 'qualification'])
def test_finished_job_returns_retained_receipt_without_service_or_owner_action(tmp_path, monkeypatch, capsys, mode):
    artifact = tmp_path / 'artifact'; artifact.mkdir()
    evidence = BATCH['BASE'] / 'operator-evidence' / ('launch-' + mode + '-invented')
    result = dict(complete=True, source_revision=BATCH['BASE'].name, evidence=str(evidence), phase=mode, operator_job_stopped=True)
    read = lambda path, *args: json.dumps({'evidence': str(evidence)} if path.name.endswith('-context.json') else result).encode()
    scope = BATCH['watch'].__globals__
    monkeypatch.setitem(scope, 'ARTIFACT', artifact)
    monkeypatch.setattr(BATCH['os'].path, 'lexists', lambda p: str(p).endswith('finish.summary.json'))
    monkeypatch.setitem(scope, 'metadata', lambda *a: pytest.fail('completed unit queried again'))
    assert BATCH['watch'](mode, read, lambda *a: pytest.fail('completed evidence rewritten')) == 0
    assert json.loads(capsys.readouterr().out) == result


def test_owner_process_drops_identity_and_sends_no_credentials_in_environment_or_arguments(tmp_path, monkeypatch):
    (tmp_path / 'launch_completion_owner.py').write_bytes((DIRECTORY / 'launch_completion_owner.py').read_bytes())
    helper = runpy.run_path(str(DIRECTORY / 'qualify_launch_isolated_accounts.py'), run_name='owner_launch_frame')
    seen = []
    def popen(args, **kwargs):
        ast.parse(args[-1]); seen.append((args, kwargs)); return object()
    monkeypatch.setitem(BATCH['owner_process'].__globals__, 'ARTIFACT', tmp_path)
    monkeypatch.setitem(BATCH['owner_process'].__globals__, 'definitions', lambda *a: helper)
    row = entry()
    monkeypatch.setattr(BATCH['pwd'], 'getpwnam', lambda name: SimpleNamespace(pw_name=name, pw_uid=row['uid'], pw_gid=row['uid'], pw_dir=row['home'], pw_shell='/usr/sbin/nologin'))
    monkeypatch.setattr(BATCH['os'], 'getgrouplist', lambda *a: [row['uid']])
    monkeypatch.setattr(BATCH['subprocess'], 'Popen', popen)
    _, line = BATCH['owner_process'](row)
    args, kwargs = seen[0]
    assert args[:3] == ['/usr/bin/setpriv', '--no-new-privs', '--']
    assert kwargs['user'] == kwargs['group'] == row['uid'] and kwargs['extra_groups'] == ()
    assert set(kwargs['env']) == {'PATH', 'HOME', 'LANG', 'PYTHONDONTWRITEBYTECODE'}
    assert b'load_signing_key()' not in line  # It is called only by the root coordinator.


def test_owner_failure_projection_rejects_private_text():
    failure = BATCH['owner_failure'](dict(complete=False, phase='credential_publish', error_kind='PermissionError', errno=13,
        private_message='invented-private-material', raw_env='invented-private-material'))
    assert failure.owner_diagnostic == dict(phase='credential_publish', error_kind='PermissionError', errno=13)
    assert 'invented-private-material' not in str(failure.owner_diagnostic)


@pytest.mark.parametrize('failure_index', [None, 5])
def test_bulk_batch_stops_at_failure_and_preserves_completed_profile_checkpoints(tmp_path, monkeypatch, capsys, failure_index):
    rows = [entry(i) for i in range(40)]; seen = []
    def module(path, digest):
        if path.name == 'fleet_credential_policy.py': return {'load': lambda *a: {'profiles': rows}}
        if path.name == 'qualify_launch_gateway_renewal_v2.py': return {'NATIVE': {}, 'PROVIDER_FILES': {}}
        raise AssertionError('unexpected dependency')
    def qualify(row, per, read, write, model_key_digest):
        assert model_key_digest == 'd' * 64
        seen.append(row['uid'])
        return dict(complete=len(seen) != failure_index, credentials_issued=2, expired_candidate_recovered=False)
    scope = BATCH['qualification'].__globals__
    monkeypatch.setitem(scope, 'definitions', module); monkeypatch.setitem(scope, 'qualify_profile', qualify)
    monkeypatch.setitem(scope, 'main_probe', lambda *a: {'credentials_issued': 0})
    def read(path, *args):
        if path.name == 'implementation-context.json':
            return json.dumps({'evidence': str(BATCH['BASE'] / 'operator-evidence/launch-implementation-invented')}).encode()
        return json.dumps(dict(complete=True, model_key_sha256='d' * 64, fixture_unchanged_since_receipt=True)).encode()
    if failure_index:
        with pytest.raises(ValueError) as failed: BATCH['qualification'](read, lambda *a: None, tmp_path)
        assert failed.value.batch_progress['qualified_profiles'] == 4
        assert failed.value.batch_progress['unattempted_profiles'] == 35
        assert len(seen) == 5
    else:
        value = BATCH['qualification'](read, lambda *a: None, tmp_path)
        assert value['qualified_profiles'] == 40 and value['credentials_issued'] == 80
        assert value['named_post_renewal_restores_qualified'] is True
    assert len({*seen}) == len(seen) and len([path for path in tmp_path.iterdir() if path.is_dir()]) == len(seen)


@pytest.mark.parametrize('expired,damage', [(False, None), (True, None), (False, 'metadata'),
    (False, 'gateway'), (True, 'gateway'), (False, 'extra_receipt'), (False, 'backup')])
def test_profile_lifecycle_scopes_publication_and_backups_partial_effects(tmp_path, monkeypatch, expired, damage):
    row = entry(); events = []; writes = {}; process_state = {'finished': False}
    class Pipe:
        def __init__(self): self.data = b''
        def write(self, data): self.data += data
        def flush(self): pass
        def close(self): pass
    process = SimpleNamespace(stdin=Pipe(), wait=lambda **kw: 0)
    def bounded(proc, seconds):
        ident = json.loads(proc.stdin.data.splitlines()[1])['id']
        if not proc.stdin.data.endswith(b'check\n'):
            if damage == 'gateway': return dict(complete=False, phase='retained_gateway_reload', error_kind='ValueError')
            return dict(ready=True, id=ident)
        value = dict(complete=True, id=ident, actual_configured_zai_route_used=True,
            retained_native_gateway=True, unchanged_agent_reused=True, renewed_agent_rebuilt=True,
            candidate_token_bound=True, replacement_authenticated=True, settings_and_oauth_preserved=True,
            non_memory_network_attempts=0, chat_model_called=False, platform_adapters_started=0)
        if damage == 'extra_receipt': value['private_extra'] = 'invented-not-retained'
        return value
    def owner(row, packet):
        mode = packet['mode']; events.append(mode)
        if mode == 'credential_metadata':
            value = dict(complete=True, expired=expired, token_iat=int(time.time()) - 10, token_sha256='a' * 64,
                scope_shape_verified=True, api_status_http=401 if expired else 200, credentials_changed=False)
            if damage == 'metadata': value['private_extra'] = 'invented-not-retained'
            return value, b''
        if mode == 'recover_expired':
            return dict(complete=True, expired_candidate_recovered=True, preserved_settings_and_oauth=True,
                preserved_previous_environment=True, interrupted_attempts_reconciled=0,
                unattended_renewal_qualified=False, timer_activation_approved=False), b''
        assert mode == 'credential_publish'
        return dict(complete=True, credential_published=True, preserved_settings_and_oauth=True,
            preserved_previous_environment=True, interrupted_attempts_reconciled=0,
            native_reload_qualified=False, timer_activation_approved=False), b''
    core = {'open_directory': lambda path, owners: os.open(path, os.O_RDONLY | os.O_DIRECTORY)}
    def ledger_write(descriptor, name, value):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=descriptor)
        with os.fdopen(fd, 'wb') as stream: stream.write(json.dumps(value).encode())
    driver = {'SOURCES': {}, 'binding_digest': lambda *a: 'b' * 64, 'ledger_write': ledger_write,
              'receipt': json.loads, 'attempt_closed': lambda *a: True}
    def module(path, digest):
        if path.name == 'qualify_launch_candidate_renewal.py': return {'bounded_line': bounded}
        if path.name == 'qualify_launch_candidate_reload.py': return dict(accepted_reload=OLD['accepted_reload'], terminate=lambda *a: events.append('stop') or True)
        if path.name == 'renew_fleet_credentials.py': return driver
        if path.name == 'provision_pilot_access.py': return core
        raise AssertionError('unexpected dependency')
    def backup(*args):
        events.append('backup')
        if damage == 'backup': raise ValueError('invented backup failure')
        return '/invented/encrypted-generation.age'
    def write(path, raw):
        writes[path] = raw
        with path.open('xb') as stream: stream.write(raw)
    scope = BATCH['qualify_profile'].__globals__
    for name, value in dict(definitions=module, owner=owner, owner_process=lambda *a: (process, b'public-line\n'),
        fresh_bundle=lambda *a: dict(token='invented-new-token', claims={'iat': int(time.time()) - 2}), named_backup=backup).items():
        monkeypatch.setitem(scope, name, value)
    result = BATCH['qualify_profile'](row, tmp_path, object(), write, 'd' * 64)
    assert result['complete'] is (damage is None)
    assert result['qualification_process_stopped'] is True
    assert 'invented-not-retained' not in str(writes)
    changed_or_started = expired and damage != 'metadata' or damage not in {'metadata', 'gateway'}
    assert ('backup' in events) is bool(changed_or_started)
    if damage is None:
        assert result['credentials_issued'] == (4 if expired else 2)
        assert result['native_gateway_reload_qualified'] is True
        assert events[-2:] == ['stop', 'backup']
    if damage == 'backup': assert result['backup_incomplete_preserve_evidence'] is True


@pytest.mark.parametrize('tamper', [False, True])
def test_main_backup_uses_exact_existing_receipt_contract_and_authenticates_before_decryption(tmp_path, monkeypatch, tamper):
    main = runpy.run_path(str(DIRECTORY / 'continue_launch_main_operational.py'), run_name='main_protocol_contract')
    core = runpy.run_path(str(DIRECTORY / 'capture_main_operational_profile_v3.py'), run_name='main_protocol_snapshot')
    profile = tmp_path / 'profile'; profile.mkdir(); (profile / 'invented').write_bytes(b'preserve')
    _, captured_receipt = core['capture'](profile, online_databases=True)
    row = entry(); evidence = tmp_path / 'evidence'; evidence.mkdir(); backups = tmp_path / 'backups'; backups.mkdir()
    secret = 'invented-root-backup-signing-material'
    writes = {}; events = []
    receipt = dict(complete=True, archived_files_verified=True, private_restore_verified=True, sqlite_databases_verified=0,
        restored_profile_executed=False, operational_restore_qualified=True, full_profile_recovery_qualified=False,
        executable_rebuild_qualified=False, database_snapshot_mode='read_transaction_per_database',
        global_atomic_snapshot_qualified=False, pinned_provider_binding_reconstructed=True, restored_scope_authenticated=True)
    def owner(entry, packet, payload=b''):
        assert secret.encode() not in payload and secret not in json.dumps(packet)
        events.append(packet['mode'])
        if packet['mode'] == 'capture_main':
            body = b'age-encryption.org/v1\ninvented-ciphertext'
            return dict(complete=True, receipt=captured_receipt, ciphertext_bytes=len(body)), body
        assert payload == b'invented-private-archive'
        return dict(complete=True, destination='/invented/home/ec-main-operational-restore-invented', receipt=receipt), b''
    def read(path, *args):
        if path.name == 'backup.json': return json.dumps(dict(ENHANCED_BACKUP_RECIPIENT='age1invented',
            ENHANCED_BACKUP_SIGNING_KEY=secret, ENHANCED_BACKUP_SIGNING_KEY_ID='invented')).encode()
        if tamper and path.suffix == '.age': return writes[path] + b'tampered'
        return writes[path]
    def write(path, raw):
        writes[path] = raw
    def run(args, **kwargs):
        assert args == ['/usr/local/bin/age', '--decrypt', '--identity', '/etc/enhanced-cognee/age-recovery-identity.txt']
        assert set(kwargs['env']) == {'PATH', 'HOME'} and secret not in str(args) + str(kwargs['env'])
        events.append('authenticated_decryption')
        return SimpleNamespace(stdout=b'invented-private-archive')
    namespace = BATCH['main_backup'].__globals__
    monkeypatch.setattr(BATCH['pwd'], 'getpwnam', lambda *a: SimpleNamespace(pw_dir='/invented/home'))
    monkeypatch.setattr(BATCH['subprocess'], 'run', run)
    for name, value in dict(BACKUPS=backups, definitions=lambda *a: main, owner=owner, sync=lambda *a: None).items():
        monkeypatch.setitem(namespace, name, value)
    if tamper:
        with pytest.raises(ValueError): BATCH['main_backup'](row, evidence, read, write)
        assert events == ['capture_main']
    else:
        result = BATCH['main_backup'](row, evidence, read, write)
        assert result['main_candidate_backup_restore_qualified'] is True and result['restored_main_scope_authenticated'] is True
        assert events == ['capture_main', 'authenticated_decryption', 'restore_main']
    assert secret not in str(writes) and b'invented-private-archive' not in writes.values()


def test_scheduled_batch_reuses_pid1_journal_proof_before_stopping_units(tmp_path, monkeypatch, capsys):
    artifact = tmp_path / 'artifact'; artifact.mkdir(); base = tmp_path / 'base'; evidence = base / 'operator-evidence/launch-qualification-invented'; evidence.mkdir(parents=True)
    invocation = 'b' * 32; boot = 'c' * 32; stem = BATCH['units']('qualification'); stopped_units = set(); writes = {}
    summary = dict(complete=True, evidence=str(evidence), source_revision=base.name, phase='qualification', invocation_id=invocation)
    rows = [dict(_PID='1', _UID='0', _COMM='systemd', UNIT=stem + '.' + kind, JOB_TYPE='start', JOB_RESULT='done',
                 _BOOT_ID=boot, __MONOTONIC_TIMESTAMP=str(stamp), INVOCATION_ID=ident)
            for kind, stamp, ident in [('timer', 1000000, ''), ('service', 18000000, invocation)]]
    verifier = runpy.run_path(str(DIRECTORY / 'qualify_launch_issuer_publication.py'), run_name='batch_journal_contract')
    def read(path, *args):
        if path.name.endswith('-context.json'): return json.dumps({'evidence': str(evidence)}).encode()
        return json.dumps(summary).encode()
    def metadata(unit):
        if unit in stopped_units: return dict(ActiveState='inactive', MainPID='0', ControlPID='0', LoadState='not-found')
        return dict(ActiveState='active', SubState='exited', MainPID='0', ControlPID='0', LoadState='loaded',
                    Result='success', ExecMainStatus='0', User='root', InvocationID=invocation)
    def run(args, **kw):
        if args[0] == '/usr/bin/journalctl': return SimpleNamespace(stdout=b'\n'.join(json.dumps(row).encode() for row in rows))
        assert args[:2] == ['/usr/bin/systemctl', 'stop']; stopped_units.add(args[2]); return SimpleNamespace()
    monkeypatch.setattr(BATCH['subprocess'], 'run', run)
    namespace = BATCH['watch'].__globals__
    for name, value in dict(BASE=base, ARTIFACT=artifact, metadata=metadata, definitions=lambda *a: verifier).items():
        monkeypatch.setitem(namespace, name, value)
    assert BATCH['watch']('qualification', read, lambda path, raw: writes.setdefault(path, raw)) == 0
    value = json.loads(capsys.readouterr().out)
    assert value['journal_scheduling_proof']['verified'] is True
    assert value['scheduled_candidate_fleet_publication_qualified'] is True and value['operator_job_stopped'] is True
    assert stopped_units == {stem + '.timer', stem + '.service'}
    assert evidence / 'finish.summary.json' in writes


@pytest.mark.parametrize('damage', [None, 'peer', 'private_extra'])
def test_main_probe_uses_separate_owner_credentials_and_never_withdraws_before_peer_denial(tmp_path, monkeypatch, damage):
    main, peer = entry(42), entry(1); seen = []; writes = {}; nonce = []; record = 'invented-new-main-record'
    implementation = BATCH['BASE'] / 'operator-evidence/launch-implementation-invented'
    def read(path, *args):
        if path.name == 'implementation-context.json': return json.dumps({'evidence': str(implementation)}).encode()
        return json.dumps({'entry': main}).encode()
    def owner(row, packet):
        seen.append((row['uid'], packet['mode']))
        if packet['mode'] == 'main_api_probe':
            assert row == main and packet['peer_profile'] == peer['profile']
            assert 'token' not in packet
            nonce.append(packet['id'])
            result = dict(complete=True, record_id=record, own_scope_write_read_qualified=True,
                actual_semantic_graph_qualified=True, main_os_peer_and_operator_denials_qualified=True)
            if damage == 'private_extra': result['private_extra'] = 'invented-not-retained'
            return result, b''
        if packet['mode'] == 'peer_history_denial':
            assert row == peer and packet['token'] == 'invented-peer-token' and packet['record_id'] == record
            return dict(complete=True, peer_history_denied=damage != 'peer', peer_credential_scope_authenticated=True), b''
        assert row == main and packet['id'] == nonce[0] and packet['record_id'] == record
        return dict(complete=True, invented_record_retracted_history_preserved=True, actual_withdrawal_verified=True), b''
    namespace = BATCH['main_probe'].__globals__
    for name, value in dict(fixed_entry=lambda *a: (main, {}), owner=owner, fresh_bundle=lambda row: {'token': 'invented-peer-token'}, sync=lambda *a: None).items():
        monkeypatch.setitem(namespace, name, value)
    def write(path, raw): writes[path] = raw
    if damage is None:
        assert BATCH['main_probe'](read, write, tmp_path, peer)['credentials_issued'] == 2
        assert [mode for _, mode in seen] == ['main_api_probe', 'peer_history_denial', 'main_probe_withdrawal']
    else:
        with pytest.raises(ValueError): BATCH['main_probe'](read, write, tmp_path, peer)
        assert all(mode != 'main_probe_withdrawal' for _, mode in seen)
    assert 'invented-not-retained' not in str(writes)


def test_owner_api_probe_uses_real_transport_contract_and_retracts_only_matching_new_record(tmp_path, monkeypatch):
    row = entry(); row['uid'] = os.geteuid(); nonce = 'a' * 32; peer = entry(2)
    core = runpy.run_path(str(DIRECTORY / 'provision_pilot_access.py'), run_name='main_api_transport_core')
    renewal = runpy.run_path(str(DIRECTORY / 'renew_pilot_access.py'), run_name='main_api_transport_renewal')
    identity = OWNER['identity'](row); core['IDENTITY'] = identity
    token = core['sign_claims'](dict(identity, iat=int(time.time()), exp=int(time.time()) + 86400), b'invented-test-key')
    (tmp_path / '.env').write_text('ENHANCED_COGNEE_ACCESS_TOKEN=' + token + '\n'); (tmp_path / '.env').chmod(0o600)
    original_open = os.open
    def open_guard(path, *args, **kw):
        if str(path) in {peer['profile'] + '/.env', '/etc/enhanced-cognee/operator.json', '/etc/enhanced-cognee/age-recovery-identity.txt'}:
            raise PermissionError(13, 'invented-denial')
        return original_open(path, *args, **kw)
    core['open_directory'] = lambda *a: original_open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    delivery = runpy.run_path(str(DIRECTORY / 'model_delivery_readiness.py'), run_name='main_probe_nested_status')
    status = dict(ready=True, schema_version=3, encryption='AES-256-GCM', active_records=0, pending_change_events=0,
        tenant_id=row['tenant'], project_id=row['project_id'], subject=row['subject'],
        index=dict(worker_available=True, worker_state='running', pending_change_events=0, vector_index='available', graph='source_linked_graph'))
    state = {}; requests = []
    class Response:
        def __init__(self, value): self.value = value
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return json.dumps(self.value).encode()
    def transport(request, **kwargs):
        method, path = request.method, request.full_url.removeprefix('http://127.0.0.1:28080')
        requests.append((method, path))
        body = json.loads(request.data) if request.data else None
        if path.endswith('/status'): return Response(status)
        if path == '/v1/memories':
            assert method == 'POST' and nonce in body['content']
            state.update(id='new-invented-main-record', version=1, content=body['content'], state='active')
        elif path.endswith('/recall'):
            return Response(dict(vector_index='queried', results=[dict(state)] if state['state'] == 'active' else []))
        elif path.endswith('/connections'): return Response({'paths': [{'invented': True}]})
        elif path.endswith('/retract'):
            assert body == {'expected_version': 1}; state.update(version=2, state='retracted')
        elif path.endswith('/history'): return Response(dict(record_state=state['state'], versions=[{'version': 1}, {'version': 2}]))
        return Response(dict(state))
    def public(name):
        return {'provision_pilot_access.py': core,
            'prepare_launch_candidate_provider_v2.py': {'open_candidate_directory': core['open_directory']},
            'renew_pilot_access.py': renewal, 'qualify_launch_gateway_renewal_v2.py': {'network_guard': lambda: {}},
            'fleet_credential_lifecycle.py': {'accepted_status': lambda *a: None}, 'model_delivery_readiness.py': delivery}[name]
    monkeypatch.setattr(urllib.request, 'build_opener', lambda *a: SimpleNamespace(open=transport))
    monkeypatch.setattr(OWNER['os'], 'open', open_guard)
    monkeypatch.setitem(OWNER['memory_probe'].__globals__, 'public', public)
    monkeypatch.setitem(OWNER['memory_probe'].__globals__, 'PROVIDER', str(DIRECTORY.parent / 'enhanced_cognee'))
    account = SimpleNamespace(pw_uid=os.geteuid())
    created = OWNER['memory_probe'](dict(mode='main_api_probe', entry=row, id=nonce, peer_profile=peer['profile']), account)
    assert created['main_os_peer_and_operator_denials_qualified'] is True and state['version'] == 1
    with pytest.raises(ValueError):
        OWNER['memory_probe'](dict(mode='main_probe_withdrawal', entry=row, id=nonce[:8] + 'b' * 24, record_id=created['record_id']), account)
    assert state['version'] == 1 and not any(path.endswith('/retract') for _, path in requests)
    result = OWNER['memory_probe'](dict(mode='main_probe_withdrawal', entry=row, id=nonce, record_id=created['record_id']), account)
    assert result['actual_withdrawal_verified'] is True and state['version'] == 2
