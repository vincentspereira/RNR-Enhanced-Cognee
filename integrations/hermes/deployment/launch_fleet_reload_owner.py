"""Retain one actual candidate's ZAI gateway across ordinary token replacement.

No model request or platform adapter. A fresh profile-secret scope must rebuild
the cached native agent while settings/OAuth remain preserved. Only fixed flags
and counts leave the owner process; all non-memory network access is refused.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import sys


def run(packet, public):
    def require(value):
        if not value: raise ValueError('fleet_gateway_reload_refused')
    entry = packet['entry']; profile = Path(entry['profile'])
    require(isinstance(packet.get('model_key_digest'), str) and len(packet['model_key_digest']) == 64)
    core = public('provision_pilot_access.py')
    core['IDENTITY'] = dict(sub=entry['subject'], agent_id=entry['agent_id'], tenant=entry['tenant'],
                            project_id=entry['project_id'], roles=['api_client'], capture_policy='selected')
    fix = public('prepare_launch_candidate_provider_v2.py')
    core['open_directory'] = fix['open_candidate_directory']
    renewal = public('renew_pilot_access.py'); lifecycle = public('fleet_credential_lifecycle.py')
    descriptor = core['open_directory'](profile, {0, entry['uid']})
    try:
        saved = {name: core['read_private_at'](descriptor, name, entry['uid'])[0]
                 for name in ('config.yaml', '.env', 'auth.json', 'enhanced_cognee.json')}
    finally: os.close(descriptor)
    original = renewal['environment'](core, saved['.env'])
    lifecycle['accepted_status'](core, original)
    native = public('qualify_launch_candidate_native_unit.py')
    observer = public('observe_launch_native_runtime.py')
    runtime_check = public('complete_launch_named_runtime.py')
    import yaml
    config = native['candidate_config'](yaml.safe_load(saved['config.yaml']))
    require(not Path('/etc/hermes').exists() and set(os.listdir(profile / 'plugins')) == {'enhanced_cognee'}
            and (profile / 'plugins/enhanced_cognee').is_symlink()
            and os.readlink(profile / 'plugins/enhanced_cognee') == str(native['PROVIDER']))
    os.environ.update(HOME=str(profile), HERMES_HOME=str(profile))
    os.chdir(profile)
    counts = observer['network_guard']()
    sys.path.insert(0, str(native['RELEASE'] / 'repo'))
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionSource
    from gateway.turn_context import TurnContext
    from gateway.run_turn_runner import TurnRunner
    from hermes_cli.runtime_provider import frozen_runtime_config, resolve_runtime_provider
    from agent.secret_scope import current_secret_scope_home
    from run_agent import AIAgent
    runner = GatewayRunner(GatewayConfig(multiplex_profiles=True,
        sessions_dir=Path(entry['home']) / ('fleet-reload-sessions-' + packet['id'])))
    source = SessionSource(platform=Platform.TELEGRAM, chat_id='qualification', user_id='qualification')
    context = TurnContext(source=source, session_id='fleet_' + packet['id'], session_key='fleet_' + packet['id'],
        user_config=config, enabled_toolsets=['memory'], disabled_toolsets=None, AIAgent=AIAgent)
    turn = TurnRunner(runner, context)
    def resolve():
        with runner._profile_scope_for_source(source):
            require(current_secret_scope_home() == str(profile))
            with frozen_runtime_config(config):
                runtime = resolve_runtime_provider(requested=config['model']['provider'], target_model=config['model']['default'])
            runtime_check['route_metadata'](config, runtime)
            require(hashlib.sha256(runtime['api_key'].encode()).hexdigest() == packet['model_key_digest'])
            route = runner._resolve_turn_agent_config('', config['model']['default'], runtime)
            return turn._resolve_turn_agent(route, 'telegram', '', 6, {'enabled': True, 'effort': 'low'}, {})
    def provider(agent):
        found = [item for item in agent._memory_manager._providers if item.name == 'enhanced_cognee']
        require(len(found) == 1 and Path(sys.modules[type(found[0]).__module__].__file__).resolve() == native['PROVIDER'] / '__init__.py')
        return found[0]
    def authenticated_provider(agent):
        status = provider(agent)._client.request('GET', '/v1/memories/status')
        require(status.get('ready') is True and status.get('schema_version') == 3
                and status.get('encryption') == 'AES-256-GCM'
                and all(status.get(field) == entry[claim] for field, claim in
                        [('tenant_id', 'tenant'), ('project_id', 'project_id'), ('subject', 'subject')]))
    first, reused = resolve()
    require(not reused and isinstance(first, AIAgent) and provider(first)._client.token == original)
    authenticated_provider(first)
    again, reused = resolve()
    require(reused and again is first and not runner.adapters)
    import json
    sys.__stdout__.write(json.dumps(dict(ready=True, id=packet['id'])) + '\n'); sys.__stdout__.flush()
    require(sys.stdin.buffer.readline(32) == b'check\n')
    replaced = (profile / '.env').read_bytes()
    replacement = renewal['environment'](core, replaced)
    require(replacement != original and renewal['environment'](core, saved['.env'], replacement) == replaced)
    second, reused = resolve()
    require(not reused and second is not first and isinstance(second, AIAgent) and provider(second)._client.token == replacement)
    authenticated_provider(second)
    again, reused = resolve()
    require(reused and again is second and not runner.adapters)
    lifecycle['accepted_status'](core, replacement)
    expected = dict(saved, **{'.env': replaced})
    observed = observer['preservation'](expected, {name: (profile / name).read_bytes() for name in expected})
    observed.update(memory_operations=counts['memory'], blocked_context_discovery_attempts=counts['discovery_blocked'],
                    unexpected_network_attempts=counts['unexpected_blocked'], network_denial_controls_passed=counts['controls_blocked'] == 3)
    observer['validate_observation'](observed)
    return dict(complete=True, id=packet['id'], actual_configured_zai_route_used=True,
        retained_native_gateway=True, unchanged_agent_reused=True, renewed_agent_rebuilt=True,
        candidate_token_bound=True, replacement_authenticated=True, settings_and_oauth_preserved=True,
        non_memory_network_attempts=0, chat_model_called=False, platform_adapters_started=0)
