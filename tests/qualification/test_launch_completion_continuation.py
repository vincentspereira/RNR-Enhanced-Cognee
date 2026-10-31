"""Real inactive-copy publication and fail-closed endpoint continuation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest
import yaml

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
ENV = runpy.run_path(str(DIRECTORY / 'main_candidate_environment.py'), run_name='main_endpoint_tests')
V2 = runpy.run_path(str(DIRECTORY / 'launch_completion_batch_v2.py'), run_name='continuation_tests')
OWNER = runpy.run_path(str(DIRECTORY / 'launch_completion_owner_v2.py'), run_name='continued_owner_tests')
OLD_ROUTE = runpy.run_path(str(DIRECTORY / 'bind_launch_model_route.py'), run_name='old_route_refusal')
KEY = 'invented-key-for-alias-qualification'


def environment(origin=ENV['ALIAS']):
    return ('# Preserve comments and OAuth settings\nOTHER="invented preserved value"\n'
            'GLM_API_KEY="' + KEY + '"\nGLM_BASE_URL="' + origin + '" # endpoint\n').encode()


def test_known_alias_reproduces_previous_refusal_then_preserves_other_bytes_and_key():
    raw = environment()
    with pytest.raises(ValueError):
        OLD_ROUTE['environment_update']({'GLM_API_KEY': KEY, 'GLM_BASE_URL': ENV['ALIAS']}, 'GLM_API_KEY', KEY, '/api/coding/paas/v4')
    changed = ENV['prepare'](raw, 'GLM_API_KEY', KEY, '/api/coding/paas/v4')
    assert changed == raw.replace(ENV['ALIAS'].encode(), ENV['TARGET'].encode())
    assert ENV['prepare'](changed, 'GLM_API_KEY', KEY, '/api/coding/paas/v4') == changed


@pytest.mark.parametrize('origin', ['https://example.invalid/api/coding/paas/v4',
    'http://api.z.ai/api/coding/paas/v4', 'https://api.z.ai/api/paas/v4',
    'https://api.z.ai:443/api/coding/paas/v4', 'https://api.z.ai/api/coding/paas/v4?other=1',
    'https://user:password@api.z.ai/api/coding/paas/v4'])
def test_unreviewed_endpoint_refused(origin):
    with pytest.raises(ValueError): ENV['prepare'](environment(origin), 'GLM_API_KEY', KEY, '/api/coding/paas/v4')


@pytest.mark.parametrize('damage', ['key_conflict', 'duplicate_base', 'duplicate_key', 'parse_error', 'wrong_key_name'])
def test_conflicting_credentials_or_ambiguous_bindings_refuse(damage):
    raw = environment(); key = KEY; name = 'GLM_API_KEY'
    if damage == 'key_conflict': key += '-changed'
    elif damage == 'duplicate_base': raw += b'GLM_BASE_URL="https://api.z.ai/api/coding/paas/v4"\n'
    elif damage == 'duplicate_key': raw += ('GLM_API_KEY="' + KEY + '"\n').encode()
    elif damage == 'parse_error': raw += b'BROKEN="unterminated\n'
    else: name = 'HOME'
    with pytest.raises(ValueError): ENV['prepare'](raw, name, key, '/api/coding/paas/v4')


def test_missing_fields_and_custom_key_are_supported_without_touching_other_bindings():
    raw = b'OTHER="preserve"\n'
    changed = ENV['prepare'](raw, 'HERMES_CUSTOM_INVENTED_API_KEY', KEY, '/api/coding/paas/v4')
    assert changed.startswith(raw)
    assert ENV['TARGET'].encode() in changed and KEY.encode() in changed


def test_real_main_configuration_publication_preserves_source_backups_auth_and_key(tmp_path, monkeypatch):
    home = tmp_path / 'isolated-home'; home.mkdir(mode=0o700)
    restored = home / 'ec-main-operational-restore-invented'; restored.mkdir(mode=0o700)
    marker = home / '.hermes'; marker.mkdir(mode=0o700)
    (marker / '.isolation-marker').write_bytes(b'invented-isolation-marker-v1')
    (marker / '.isolation-marker').chmod(0o600)
    config = dict(model=dict(provider='zai', default='glm-5.3-flash', key_env='GLM_API_KEY', base_url=ENV['TARGET']),
        gateway=dict(multiplex_profiles=True), mcp_servers=dict(
            files=dict(command='npx', args=['-y', '@modelcontextprotocol/server-filesystem', '/home/vincentspereira/agent-workspace']),
            two={}, three={}, four={}))
    config_raw = yaml.safe_dump(config).encode(); env_raw = environment(); auth = b'{"invented":"preserve"}'
    for name, raw in [('config.yaml', config_raw), ('.env', env_raw), ('auth.json', auth)]:
        (restored / name).write_bytes(raw); (restored / name).chmod(0o600)
    stage = runpy.run_path(str(DIRECTORY / 'stage_launch_candidate_issuer.py'), run_name='derive_continued_core')
    core_raw, _ = stage['build_sources']((DIRECTORY / 'provision_pilot_access.py').read_bytes(),
        (DIRECTORY / 'renew_fleet_credentials.py').read_bytes(), (DIRECTORY / 'prepare_launch_candidate_provider_v2.py').read_bytes())
    core = {'__name__': 'continued_owner_core_test'}; exec(compile(core_raw, '<test-core>', 'exec'), core)
    core['qualify_access'] = lambda bundle: None
    fix = runpy.run_path(str(DIRECTORY / 'prepare_launch_candidate_provider_v2.py'), run_name='real_candidate_rename')
    # Only fixture ancestor traversal is adapted; publication/read/rename/fsync
    # behavior uses the real reviewed functions and real private files.
    fix['open_candidate_directory'] = lambda path, owners: os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    transform = runpy.run_path(str(DIRECTORY / 'main_candidate_configuration.py'), run_name='continued_main_transform')
    real_transform = transform['transform']
    transform['transform'] = lambda cfg, dest: real_transform(cfg, Path('/var/lib/enhanced-cognee-profiles/' + 'a' * 16))
    modules = {'provision_pilot_access.py': core, 'prepare_launch_candidate_provider_v2.py': fix,
        'main_candidate_configuration.py': transform, 'bind_launch_model_route.py': OLD_ROUTE,
        'main_candidate_environment.py': ENV,
        'qualify_launch_gateway_renewal_v2.py': {'network_guard': lambda: None}}
    monkeypatch.setitem(OWNER['main_configuration'].__globals__, 'public', lambda name: modules[name])
    uid = os.geteuid(); entry = dict(uid=uid, tenant='invented', project_id='invented', subject='invented', agent_id='invented')
    packet = dict(mode='configure_main', entry=entry, candidate=str(restored), config_sha256=hashlib.sha256(config_raw).hexdigest(),
        bundle={'token': 'invented.unpublished.token'}, model_key=KEY, id='a' * 32)
    result = OWNER['main_configuration'](packet, SimpleNamespace(pw_dir=str(home), pw_uid=uid))
    assert result['main_scope_authenticated'] is True and result['source_profiles_changed'] is False
    assert not restored.exists() and marker.is_dir()
    assert (home / ('.hermes-before-main-integration-' + 'a' * 32) / '.isolation-marker').is_file()
    assert (marker / ('.env-before-main-' + 'a' * 32)).read_bytes() == env_raw
    assert (marker / ('config.yaml-before-main-' + 'a' * 32)).read_bytes() == config_raw
    assert (marker / 'auth.json').read_bytes() == auth
    after = (marker / '.env').read_bytes()
    assert after.startswith(env_raw.replace(ENV['ALIAS'].encode(), ENV['TARGET'].encode()))
    assert after.count(KEY.encode()) == 1 and (core['TOKEN_NAME'] + '=invented.unpublished.token').encode() in after
    assert (marker / 'plugins/enhanced_cognee').is_symlink()


def test_v1_bytes_unchanged_and_new_pins_protocol_are_consistent():
    assert hashlib.sha256((DIRECTORY / 'launch_completion_batch.py').read_bytes()).hexdigest() == V2['DRIVER_SHA']
    assert hashlib.sha256((DIRECTORY / 'launch_completion_owner_v2.py').read_bytes()).hexdigest() == V2['OWNER_SHA']
    assert hashlib.sha256((DIRECTORY / 'main_candidate_environment.py').read_bytes()).hexdigest() == OWNER['PINS']['main_candidate_environment.py']
    old = runpy.run_path(str(DIRECTORY / 'launch_completion_batch.py'), run_name='continued_freeze_source_test')
    scope = V2['adapt'](old, (DIRECTORY / 'launch_completion_batch_v2.py').read_bytes(), DIRECTORY / 'launch_completion_batch_v2.py')
    for name, digest in dict(scope['PINS'], **OWNER['PINS']).items():
        if name in {'provision_pilot_access.py', 'renew_fleet_credentials.py'}: continue
        assert hashlib.sha256(scope['definitions'](DIRECTORY / name, digest)['_verified_source_bytes']).hexdigest() == digest
    frozen = V2['adapt'](runpy.run_path(str(DIRECTORY / 'launch_completion_batch.py'), run_name='continued_frozen_test'),
        b'invented', V2['ARTIFACT'] / 'launch_completion_batch_v2.py')
    assert frozen['ARTIFACT'] == V2['ARTIFACT']
    helper = runpy.run_path(str(DIRECTORY / 'qualify_launch_isolated_accounts.py'), run_name='continued_owner_protocol')
    helper['owner_program']((DIRECTORY / 'launch_completion_owner_v2.py').read_bytes())
    controller = runpy.run_path(str(DIRECTORY / 'launch_control.py'), run_name='continued_controller_pin')
    assert controller['COMPLETION_CONTINUE_SHA'] == hashlib.sha256((DIRECTORY / 'launch_completion_batch_v2.py').read_bytes()).hexdigest()


def test_root_adapter_selects_new_frozen_owner_without_mutating_old_driver_namespace(tmp_path):
    old = runpy.run_path(str(DIRECTORY / 'launch_completion_batch.py'), run_name='old_driver_adapter_test')
    pins = copy.deepcopy(old['PINS']); seen = []
    old['definitions'] = lambda path, digest: seen.append((path, digest))
    scope = V2['adapt'](old, b'invented-wrapper-source', tmp_path / 'launch_completion_batch_v2.py')
    scope['definitions'](tmp_path / 'launch_completion_owner.py', V2['OWNER_SHA'])
    assert seen == [(tmp_path / 'launch_completion_owner_v2.py', V2['OWNER_SHA'])]
    assert pins['launch_completion_owner.py'] != scope['PINS']['launch_completion_owner.py']
    assert scope['ARTIFACT'] == V2['ARTIFACT'] and scope['ARTIFACT'] != V2['PREVIOUS']
    assert scope['units']('implementation') != 'ec-launch-completion-implementation-20261027'
    assert scope['_verified_source_bytes'] == b'invented-wrapper-source'


@pytest.mark.parametrize('damage', [None, 'complete', 'phase', 'running', 'partial_effects', 'qualification_started'])
def test_continuation_admits_only_stopped_original_prepublication_refusal(monkeypatch, damage):
    prior = dict(complete=False, phase='implementation', operator_helper_sha256=V2['DRIVER_SHA'],
        source_revision=V2['BASE'].name, evidence=str(V2['PRIOR_EVIDENCE']), operator_job_stopped=True,
        credentials_issued=2, owner_diagnostic={'error_kind': 'ValueError', 'phase': 'main_configuration_preflight'},
        all_admission_policies_preserved_disabled=True, canonical_memory_edits=False, source_profiles_changed=False,
        existing_launchers_changed=False, chat_model_called=False, fleet_launch_approved=False)
    if damage == 'complete': prior['complete'] = True
    if damage == 'phase': prior['owner_diagnostic']['phase'] = 'main_candidate_publication'
    read = lambda path, *args: json.dumps({'evidence': str(V2['PRIOR_EVIDENCE'])}
        if path.name == 'implementation-context.json' else prior).encode()
    scope = dict(SUPPORT_SHA='invented', definitions=lambda *a: {'read_file': read},
        metadata=lambda name: {'stopped': damage != 'running'}, stopped=lambda value: value['stopped'])
    monkeypatch.setattr(V2['os'].path, 'lexists', lambda p:
        (damage == 'partial_effects' and p.name == 'main-configuration.receipt.json')
        or (damage == 'qualification_started' and p.name == 'qualification-context.json'))
    if damage:
        with pytest.raises(ValueError): V2['previous_attempt'](scope)
    else: V2['previous_attempt'](scope)
