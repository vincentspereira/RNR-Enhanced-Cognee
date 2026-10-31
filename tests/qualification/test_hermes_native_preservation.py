"""Native pool bookkeeping, outbound denial and reuse of completed recovery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
OBS = runpy.run_path(str(DIRECTORY / 'observe_launch_native_runtime.py'), run_name='native_observation_tests')
FINISH = runpy.run_path(str(DIRECTORY / 'finish_launch_named_runtime.py'), run_name='native_finish_tests')


def auth():
    return dict(version=1, updated_at='2026-10-26T12:00:00+00:00',
        providers={'nous': {'access_token': 'invented-oauth', 'refresh_token': 'invented-refresh'}},
        credential_pool={'other': [{'id': 'unchanged', 'access_token': 'invented-other'}], 'zai': [
            dict(id='one', source='env', secret_fingerprint='invented-fingerprint-one',
                 priority=0, request_count=12, status='ready', base_url='https://open.bigmodel.cn/api/paas/v4'),
            dict(id='two', source='env', secret_fingerprint='invented-fingerprint-two',
                 priority=1, request_count=10, status='ready', base_url='https://open.bigmodel.cn/api/paas/v4')]})


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


def bookkeeping(value):
    result = deepcopy(value)
    result['updated_at'] = '2026-10-26T12:00:03+00:00'
    rows = result['credential_pool']['zai']
    rows[0]['request_count'] += 1
    rows[0]['priority'], rows[1]['priority'] = 1, 0
    result['credential_pool']['zai'] = rows[::-1]
    return result


def test_native_round_robin_counter_and_order_do_not_change_credentials_or_oauth():
    before = auth()
    assert OBS['auth_preserved'](encoded(before), encoded(bookkeeping(before)))
    # Whitespace/key-order changes alone also preserve the same state.
    assert OBS['auth_preserved'](encoded(before), json.dumps(before, indent=4).encode())


@pytest.mark.parametrize('change', ['oauth', 'refresh', 'fingerprint', 'source', 'status', 'endpoint',
    'other_provider', 'new_field', 'new_row', 'removed_row', 'negative_count', 'too_many',
    'priority_values', 'backward_time', 'nan_time', 'duplicate_identity'])
def test_credentials_oauth_scope_failure_state_and_unbounded_metadata_are_refused(change):
    before = auth()
    after = bookkeeping(before)
    row = after['credential_pool']['zai'][0]
    if change == 'oauth': after['providers']['nous']['access_token'] = 'invented-replacement'
    elif change == 'refresh': after['providers']['nous']['refresh_token'] = 'invented-replacement'
    elif change == 'fingerprint': row['secret_fingerprint'] = 'invented-replacement'
    elif change == 'source': row['source'] = 'another-source'
    elif change == 'status': row['status'] = 'exhausted'
    elif change == 'endpoint': row['base_url'] = 'https://invalid.example/'
    elif change == 'other_provider': after['credential_pool']['other'][0]['access_token'] = 'invented-replacement'
    elif change == 'new_field': row['access_token'] = 'invented-new-secret-field'
    elif change == 'new_row': after['credential_pool']['zai'].append(dict(row, id='third'))
    elif change == 'removed_row': after['credential_pool']['zai'].pop()
    elif change == 'negative_count': row['request_count'] = -1
    elif change == 'too_many': row['request_count'] += 9
    elif change == 'priority_values': row['priority'] = 3
    elif change == 'backward_time': after['updated_at'] = '2026-10-25T12:00:00+00:00'
    elif change == 'nan_time': after['updated_at'] = float('nan')
    elif change == 'duplicate_identity': after['credential_pool']['zai'][1]['id'] = row['id']
    assert not OBS['auth_preserved'](encoded(before), encoded(after))


def observation():
    return dict(files_equal={name: name != 'auth.json' for name in OBS['FILES']},
        auth_sensitive_state_preserved=True, auth_usage_metadata_changed=True, preserved=True,
        memory_operations=3, blocked_context_discovery_attempts=2,
        unexpected_network_attempts=0, network_denial_controls_passed=True)


@pytest.mark.parametrize('change', [None, 'environment', 'auth', 'network', 'control', 'extra', 'boolean_count'])
def test_preservation_receipt_cannot_hide_sensitive_changes_or_unexpected_network(change):
    value = observation()
    if change == 'environment': value['files_equal']['.env'] = False
    elif change == 'auth': value['auth_sensitive_state_preserved'] = False
    elif change == 'network': value['unexpected_network_attempts'] = 1
    elif change == 'control': value['network_denial_controls_passed'] = False
    elif change == 'extra': value['private_detail'] = 'invented-must-not-be-returned'
    elif change == 'boolean_count': value['memory_operations'] = True
    if change is None: assert OBS['validate_observation'](value) == value
    else:
        with pytest.raises(ValueError): OBS['validate_observation'](value)


def test_all_outbound_paths_remain_denied_and_expected_discovery_is_counted(monkeypatch):
    module = ModuleType('agent.models_dev')
    module.__file__ = OBS['DISCOVERY_MODULES']['agent.models_dev']
    exec(compile('def discover(socket, host):\n    return socket.getaddrinfo(host, 443)\n',
                 module.__file__, 'exec'), module.__dict__)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    sockmod = OBS['socket']
    actual = []
    class ProbeSocket:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def connect(self, address): actual.append(address)
        def connect_ex(self, address): actual.append(address); return 0
    monkeypatch.setattr(sockmod, 'socket', ProbeSocket)
    monkeypatch.setattr(sockmod, 'getaddrinfo', lambda host, port, *a, **kw: actual.append((host, port)) or [])
    # Record attributes so pytest restores the guard as well as the test doubles.
    with monkeypatch.context() as guard_patch:
        guard_patch.setattr(sockmod.socket, 'connect', sockmod.socket.connect)
        guard_patch.setattr(sockmod.socket, 'connect_ex', sockmod.socket.connect_ex)
        guard_patch.setattr(sockmod, 'getaddrinfo', sockmod.getaddrinfo)
        counts = OBS['network_guard']()
        assert counts['controls_blocked'] == 3 and actual == []
        with pytest.raises(RuntimeError): module.discover(sockmod, 'models.dev')
        assert counts['discovery_blocked'] == 1 and actual == []
        # A model host is never admitted as metadata solely by its host name.
        with pytest.raises(RuntimeError): sockmod.getaddrinfo('open.bigmodel.cn', 443)
        with pytest.raises(RuntimeError): module.discover(sockmod, 'invalid.example')
        with sockmod.socket() as sock:
            with pytest.raises(RuntimeError): sock.connect(('192.0.2.1', 443))
            with pytest.raises(RuntimeError): sock.connect_ex(('192.0.2.1', 443))
            sock.connect(('127.0.0.1', 28080))
        assert counts['unexpected_blocked'] == 4
        assert actual == [('127.0.0.1', 28080)]


def test_completed_binding_and_restore_are_checked_without_republication_or_extraction(tmp_path, monkeypatch):
    function = OBS['compare_generation']
    import hmac
    generation = Path('/var/backups/enhanced-cognee/hermes_candidate_renewed_' + 'b' * 32 + '.tar.age')
    signing_key = 'invented-backup-key-for-this-test-only'
    authority = {'key': 'invented-existing-model-key', 'endpoint_path': '/api/paas/v4'}
    signing_id = 'invented-signing-key-id'
    signed = dict(complete=True, source_profile_id='a'*16, format='hermes-candidate-profile-sqlite-tar+age-v2',
                  capture_component_sha256=OBS['CAPTURE_SHA'], signing_key_id=signing_id,
                  ciphertext_sha256=hashlib.sha256(b'invented-ciphertext').hexdigest())
    signed['signature'] = hmac.new(signing_key.encode(),
        json.dumps(signed,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode(),hashlib.sha256).hexdigest()
    comparison = dict(complete=True, files_equal={n: n != 'auth.json' for n in OBS['FILES']},
        auth_sensitive_state_preserved=True, auth_usage_metadata_changed=True, preserved=True,
        bound_model_key_matches=True, endpoint_matches=True, source_profile_changed=False)
    calls, writes = [], []
    def run(args, **kwargs):
        calls.append(args)
        if args[0] == '/usr/local/bin/age':
            assert kwargs['input'] == b'invented-ciphertext'
            return SimpleNamespace(stdout=b'invented-plaintext-archive', returncode=0)
        packet = json.loads(kwargs['input'].splitlines()[-1])
        assert set(packet) == {'archive', 'key', 'endpoint_path'}
        assert signing_key.encode() not in kwargs['input']
        assert authority['key'] not in repr(args) and authority['key'] not in repr(kwargs['env'])
        assert kwargs['user'] == 1234 and kwargs['extra_groups'] == ()
        return SimpleNamespace(stdout=encoded(comparison), returncode=0)
    def read(path, owner, *limits):
        if path.name == 'model-profile-recovery.json': return encoded(dict(complete=True,generation=str(generation)))
        if path == generation: return b'invented-ciphertext'
        if path.name == generation.name+'.json': return encoded(signed)
        if path.name == 'backup.json': return encoded(dict(ENHANCED_BACKUP_SIGNING_KEY=signing_key,
            ENHANCED_BACKUP_SIGNING_KEY_ID=signing_id))
        pytest.fail('unexpected file read')
    monkeypatch.setattr(OBS['pwd'], 'getpwnam', lambda name: SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/invented'))
    monkeypatch.setattr(subprocess, 'run', run)
    result = function(dict(profile_id='a'*16,user='ecbot_'+'a'*16),tmp_path,authority,
        {'owner_program':lambda source:('public-program', b'public-source\n')}, b'public-source',
        read, lambda path,raw:writes.append(raw), tmp_path)
    assert result == comparison
    assert len(calls) == 2 and all(b'invented-existing-model-key' not in raw for raw in writes)
    assert all(b'invented-backup-key' not in raw for raw in writes)
    # An unexplained file change is reported as safe booleans and blocks continuation.
    comparison['preserved'] = False
    with pytest.raises(OBS['ComparisonError']) as caught:
        function(dict(profile_id='a'*16,user='ecbot_'+'a'*16),tmp_path,authority,
            {'owner_program':lambda source:('public-program',b'public-source\n')},b'public-source',
            read,lambda path,raw:writes.append(raw),tmp_path)
    assert caught.value.phase == 'retained_profile_comparison'
    assert caught.value.observation['preserved'] is False


def test_frozen_sources_and_unchanged_failed_attempt_are_pinned():
    for name, digest in FINISH['PINS'].items():
        assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((DIRECTORY/'repair_launch_named_runtime.py').read_bytes()).hexdigest() == \
        '1e73ee58a276960130c7f118a63bfbd2e1ea1a81c0e2ab33bfd6b83abd936192'
    control = runpy.run_path(str(DIRECTORY/'launch_control.py'), run_name='finish_dispatch_test')
    assert hashlib.sha256((DIRECTORY/'finish_launch_named_runtime.py').read_bytes()).hexdigest() == control['FINISH_SHA']
    helper = runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'), run_name='finish_owner_protocol_test')
    helper['owner_program']((DIRECTORY/'observe_launch_native_runtime.py').read_bytes())


def test_repeat_command_reattaches_and_never_rebinds_or_reprobes(monkeypatch):
    function = FINISH['launch']
    monkeypatch.setattr(FINISH['os'], 'geteuid', lambda:0)
    monkeypatch.setattr(FINISH['os'].path, 'lexists', lambda path: True)
    monkeypatch.setitem(function.__globals__, 'definitions', lambda *a:dict(read_file=object(),private_write=object()))
    monkeypatch.setitem(function.__globals__, 'selected', lambda *a:pytest.fail('must not repeat selection'))
    monkeypatch.setitem(function.__globals__, 'watch', lambda *a:42)
    assert function() == 42


@pytest.mark.parametrize('comparison_passes', [True, False])
def test_batch_reuses_first_binding_and_backup_and_stops_before_any_new_write_on_changed_state(tmp_path, monkeypatch, comparison_passes):
    function = FINISH['worker']
    state = function.__globals__
    artifact = tmp_path / 'operator-named-runtime-finish-v3'
    artifact.mkdir()
    for name in ('observe_launch_native_runtime.py', 'bind_launch_model_credential.py'):
        (artifact / name).write_bytes(b'public-test-source')
    evidence = tmp_path / 'operator-evidence/named-runtime-finish-invented'
    evidence.mkdir(parents=True)
    prior = tmp_path / 'retained-prior'
    rows = [dict(profile_id=f'{n:016x}', user='ecbot_'+f'{n:016x}',
        home='/var/lib/enhanced-cognee-profiles/'+f'{n:016x}') for n in range(40)]
    comparison = dict(complete=True, files_equal={n: True for n in OBS['FILES']},
        auth_sensitive_state_preserved=True, auth_usage_metadata_changed=False, preserved=comparison_passes,
        bound_model_key_matches=True, endpoint_matches=True, source_profile_changed=False)
    bound, probed, writes = [], [], {}
    def compare(*args):
        if not comparison_passes: raise OBS['ComparisonError'](comparison)
        return comparison
    observer = {'compare_generation':compare, 'validate_comparison':OBS['validate_comparison']}
    model = {'prepare':lambda *args:({}, {}, {}), 'PHASES':{'identity'},
             'bind_and_backup':lambda row,*args:bound.append(row['profile_id'])}
    def definitions(path, digest):
        if path.name == 'observe_launch_native_runtime.py': return observer
        if path.name == 'bind_launch_model_credential.py': return model
        return {}
    def read(path, owner):
        if path.name == 'context.json': return encoded(dict(evidence=str(evidence)))
        if path.name == 'binding.private.json': return encoded(rows[0])
        return encoded({'profiles':[{'enabled':False}]})
    monkeypatch.setattr(FINISH['os'], 'geteuid', lambda:0)
    for key,value in dict(BASE=tmp_path, ARTIFACT=artifact, __file__=str(artifact/'finish_launch_named_runtime.py'),
        definitions=definitions, selected=lambda read:rows,
        retained_failure=lambda *args:(rows[0]['profile_id'],prior),
        sync_directory=lambda *args:None,
        native_probe=lambda row,*args:probed.append(row['profile_id']) or {'observation':{'blocked_context_discovery_attempts':1}}).items():
        monkeypatch.setitem(state,key,value)
    code = function(read, lambda path,raw:writes.setdefault(path,raw))
    result = json.loads(writes[evidence/'summary.json'])
    if comparison_passes:
        assert code == 0 and result['complete'] is True
        assert bound == [r['profile_id'] for r in rows[1:]]
        assert probed == [r['profile_id'] for r in rows]
        assert result['reused_model_bindings'] == result['reused_profile_restores'] == 1
        assert result['new_candidate_generations'] == 39
    else:
        assert code == 1 and not bound and not probed
        assert result['qualified_profiles'] == 0 and result['failed_profiles'] == 1
        assert result['failure_phase'] == 'retained_profile_comparison'
        assert result['retained_candidate_comparison']['preserved'] is False
        assert result['candidate_model_credentials_may_have_changed'] is False
    assert result['credentials_issued'] == 0 and result['canonical_memory_edits'] is False
    assert result['all_admission_policies_preserved_disabled'] is True
    assert result['fleet_launch_approved'] is False
