"""Exercise native ZAI gateway/cache reload with invented in-memory API only.

Run with pinned native Python. Temporary profile path adaptation is fixture-only;
this proves neither installed per-UID isolation nor real API/model acceptance.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import time
from types import SimpleNamespace

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PHASE = 'fixture'


def main():
    global PHASE
    def denied(*args, **kwargs): raise AssertionError('offline_reload_real_network_refused')
    socket.socket.connect = socket.socket.connect_ex = socket.getaddrinfo = denied
    sys.path.insert(0, str(RELEASE / 'repo'))
    profile = Path(tempfile.mkdtemp(prefix='ec-fleet-reload-offline-', dir='/tmp'))
    provider = Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659')
    (profile / 'plugins').mkdir(mode=0o700); (profile / 'plugins/enhanced_cognee').symlink_to(provider)
    core = runpy.run_path(str(DIRECTORY / 'provision_pilot_access.py'), run_name='offline_fleet_core')
    renewal = runpy.run_path(str(DIRECTORY / 'renew_pilot_access.py'), run_name='offline_fleet_renewal')
    lifecycle = runpy.run_path(str(DIRECTORY / 'fleet_credential_lifecycle.py'), run_name='offline_fleet_lifecycle')
    observer = runpy.run_path(str(DIRECTORY / 'observe_launch_native_runtime.py'), run_name='offline_fleet_observer')
    identity = dict(sub='invented_fleet', agent_id='invented_fleet', tenant='qualification', project_id='invented_fleet', roles=['api_client'], capture_policy='selected')
    core['IDENTITY'] = identity; now = int(time.time()); key = b'invented-offline-signing-key-only'
    old = core['sign_claims'](dict(identity, iat=now - 10, exp=now + 86390), key)
    new = core['sign_claims'](dict(identity, iat=now, exp=now + 86400), key)
    config = dict(model=dict(provider='zai', default='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/coding/paas/v4', key_env='GLM_API_KEY'),
                  memory=dict(provider='enhanced_cognee'), gateway=dict(multiplex_profiles=True))
    (profile / 'config.yaml').write_text(json.dumps(config))
    (profile / 'enhanced_cognee.json').write_text(json.dumps(dict(base_url='http://127.0.0.1:28080', capture_policy='selected', include_shared=True)))
    (profile / 'auth.json').write_text('{"synthetic_marker":"preserve"}')
    (profile / '.env').write_text('GLM_API_KEY=invented-unused-model-key\nGLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4\nENHANCED_COGNEE_ACCESS_TOKEN=' + old + '\n')
    for name in ('.env', 'config.yaml', 'enhanced_cognee.json', 'auth.json'): (profile / name).chmod(0o600)
    # Fixture-only path adaptation. Production uses the actual protected owner path.
    core['open_directory'] = lambda path, owners: os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    status = dict(ready=True, schema_version=3, encryption='AES-256-GCM', active_records=0, pending_change_events=0,
                  tenant_id=identity['tenant'], project_id=identity['project_id'], subject=identity['sub'])
    core['api_status'] = lambda token=None: (200, status) if token in {old, new} else (401, {})
    from agent.secret_scope import set_secret_scope, reset_secret_scope, build_profile_secret_scope
    from hermes_cli.runtime_provider import frozen_runtime_config, resolve_runtime_provider
    os.environ['HOME'] = os.environ['HERMES_HOME'] = str(profile)
    scope = set_secret_scope(build_profile_secret_scope(profile), profile_home=str(profile))
    try:
        with frozen_runtime_config(config): resolve_runtime_provider(requested='zai', target_model='glm-5.3-flash')
    finally: reset_secret_scope(scope)
    from plugins import memory as loader
    load = loader.load_memory_provider; counts = {}; api_calls = [0]
    def wrapped_load(*args, **kwargs):
        instance = load(*args, **kwargs); initialize = instance.initialize
        def initialize_only_memory(*a, **kw):
            initialize(*a, **kw)
            def request(method, path, body=None):
                assert method == 'GET' and path == '/v1/memories/status'
                api_calls[0] += 1; counts['network']['memory'] += 1
                return status
            instance._client.request = request
        instance.initialize = initialize_only_memory
        return instance
    loader.load_memory_provider = wrapped_load
    original_guard = observer['network_guard']
    def network_guard():
        counts['network'] = original_guard()
        return counts['network']
    observer['network_guard'] = network_guard
    validate = observer['validate_observation']
    def validate_observation(value):
        try: return validate(value)
        except Exception as error:
            error.offline_observation = value
            raise
    observer['validate_observation'] = validate_observation
    support = {'provision_pilot_access.py': core, 'renew_pilot_access.py': renewal,
               'fleet_credential_lifecycle.py': lifecycle, 'observe_launch_native_runtime.py': observer}
    fix = runpy.run_path(str(DIRECTORY / 'prepare_launch_candidate_provider_v2.py'), run_name='offline_reload_path_fixture')
    fix['open_candidate_directory'] = core['open_directory']
    support['prepare_launch_candidate_provider_v2.py'] = fix
    def public(name):
        return support[name] if name in support else runpy.run_path(str(DIRECTORY / name), run_name='offline_reload_public_support')
    class Check:
        def readline(self, limit):
            assert limit == 32
            raw = (profile / '.env').read_bytes()
            (profile / '.env-before-offline-publication').write_bytes(raw)
            staged = profile / '.env-offline-publication'
            staged.write_bytes(renewal['environment'](core, raw, new)); staged.chmod(0o600)
            os.replace(staged, profile / '.env')
            return b'check\n'
    old_stdin, old_stdout = sys.stdin, sys.__stdout__
    sys.stdin = SimpleNamespace(buffer=Check()); sys.__stdout__ = io.StringIO()
    entry = dict(subject=identity['sub'], agent_id=identity['agent_id'], tenant=identity['tenant'], project_id=identity['project_id'],
                 uid=os.geteuid(), profile=str(profile), home=str(profile.parent))
    try:
        PHASE = 'native_gateway_reload'
        module = runpy.run_path(str(DIRECTORY / 'launch_fleet_reload_owner.py'), run_name='native_reload_offline_fixture')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = module['run'](dict(entry=entry, id='a' * 32,
                model_key_digest=hashlib.sha256(b'invented-unused-model-key').hexdigest()), public)
    finally:
        sys.stdin, sys.__stdout__ = old_stdin, old_stdout
    assert result['complete'] and result['renewed_agent_rebuilt'] and result['actual_configured_zai_route_used']
    assert result['chat_model_called'] is False and api_calls[0] >= 1
    print(json.dumps(dict(complete=True, synthetic_only=True, native_zai_gateway_cache_exercised=True,
        real_network_operations=0, model_requests=0, memory_calls_simulated=api_calls[0],
        installed_identity_qualified=False, real_api_qualified=False, fixture_preserved=str(profile))))


if __name__ == '__main__':
    try: main()
    except Exception as error:
        import traceback
        print(json.dumps(dict(complete=False, synthetic_only=True, phase=PHASE, error_kind=type(error).__name__,
            observation=getattr(error, 'offline_observation', None),
            public_frames=[dict(file=Path(frame.filename).name, line=frame.lineno) for frame in traceback.extract_tb(error.__traceback__)[-8:]])))
        raise SystemExit(1)
