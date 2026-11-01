"""Repair existing model bindings and run only unqualified native constructions.

No model request, adapter start, token issuance or canonical write. The existing
model key moves only over private owner pipes, never terminal/evidence output.
Repeating the command attaches to the same finite job; it never repeats probes.
Actual chat, multiplex dispatch, main migration and fleet admission stay gated.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.parse import urlsplit

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-named-runtime-model-binding-v2'
RESUMED = BASE / 'operator-evidence/provider-resume-_6q81u24'
FIRST = BASE / 'operator-evidence/candidate-provider-f8uifc8j'
PLAN = BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json'
PLAN_SHA = 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b'
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
EXECUTABLE = str(RELEASE / 'venv/bin/python')
UNIT = 'ec-launch-named-runtime-models-20261026.service'
PINS = {
    'bind_launch_model_credential.py': 'bf24f095bc8ccfb037a4278e3f5efd72c33de14195367d1bb727fc809b454b01',
    'recover_launch_graph_operator.py': 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef',
    'qualify_launch_candidate_native_unit.py': 'f085298baabc75b801ff82a79fcde97244a129b87146c87c48f72c5f7da0acd0',
    'qualify_launch_gateway_renewal_v2.py': 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2',
}
ROUTE_PINS = {
    'hermes_cli/runtime_provider.py': 'd60a99f56c55f1d0b41f7d9f0b812625eb0339fe96b6ac19861831ca1c4aaa43',
    'hermes_cli/auth.py': '19c14865f2e8cf549182fcb6cc15f3cd91c2f71b2d1bd8d8e1f6f102f6b6e3d8',
    'agent/credential_pool.py': 'f7f8501b68485b1437b3365f6451b10cc35bffa815d303c9db3c81ca9a89f943',
}
PHASE = 'identity'
PHASES = {'identity', 'configuration', 'native_imports', 'configured_route_resolution',
          'native_agent_construction', 'scoped_memory_status', 'preservation'}
TRUE_FLAGS = {'complete', 'native_gateway_constructed', 'native_agent_constructed',
              'unchanged_agent_reused', 'configured_route_resolved', 'configured_credential_present',
              'pinned_memory_provider_bound', 'own_scope_authenticated', 'settings_and_auth_preserved'}
FALSE_FLAGS = {'chat_model_called', 'platform_adapters_started', 'canonical_memory_edits',
               'actual_profile_admission_qualified', 'fleet_launch_approved'}


def require(value):
    if not value:
        raise ValueError('named_runtime_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_named_runtime_support', '__file__': str(path), '_verified_source_bytes': raw}
    exec(compile(raw, '<verified-public-runtime-support>', 'exec'), namespace)
    return namespace


def route_metadata(config, runtime):
    """Validate the exact configured production route without returning secrets."""
    model = config.get('model') or {}
    require(isinstance(model, dict) and model.get('provider') == 'zai'
            and model.get('default') in {'glm-5.3-flash', 'GLM-5.3-Flash'})
    requested = urlsplit(model.get('base_url', ''))
    resolved = urlsplit(runtime.get('base_url', ''))
    require(requested.scheme == resolved.scheme == 'https'
            and requested.hostname == resolved.hostname == 'open.bigmodel.cn'
            and requested.port in {None, 443} and resolved.port in {None, 443}
            and not requested.username and not requested.password
            and not resolved.username and not resolved.password
            and not requested.query and not requested.fragment
            and not resolved.query and not resolved.fragment
            and requested.path.rstrip('/') == resolved.path.rstrip('/')
            and runtime.get('provider') == 'zai' and runtime.get('api_mode') == 'chat_completions'
            and isinstance(runtime.get('api_key'), str) and len(runtime['api_key']) >= 16)
    return dict(provider='zai', model=model['default'], host='open.bigmodel.cn', api_mode='chat_completions')


def child(ident):
    global PHASE
    require(Path(__file__).parent == ARTIFACT and re.fullmatch('[a-f0-9]{32}', ident))
    native = definitions(ARTIFACT / 'qualify_launch_candidate_native_unit.py', PINS['qualify_launch_candidate_native_unit.py'])
    gateway = definitions(ARTIFACT / 'qualify_launch_gateway_renewal_v2.py', PINS['qualify_launch_gateway_renewal_v2.py'])
    account = pwd.getpwuid(os.geteuid())
    require(re.fullmatch('ecbot_[a-f0-9]{16}', account.pw_name)
            and account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:])
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    native['restricted_status'](account, os.geteuid(), os.getgroups(), fields)
    invocation = os.environ.get('INVOCATION_ID', '')
    require(re.fullmatch('[a-f0-9]{32}', invocation))
    expected = {key: os.environ['EC_EXPECTED_' + key.upper()] for key in ('project_id', 'tenant_id', 'subject')}
    profile = Path(account.pw_dir) / '.hermes'
    require(os.environ.get('HOME') == str(profile) and os.environ.get('HERMES_HOME') == str(profile))
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=str(profile), HERMES_HOME=str(profile),
                      LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    os.chdir(profile)
    PHASE = 'configuration'
    import yaml
    config = native['candidate_config'](yaml.safe_load((profile / 'config.yaml').read_bytes()))
    require(not Path('/etc/hermes').exists())
    require(set(os.listdir(profile / 'plugins')) == {'enhanced_cognee'}
            and (profile / 'plugins/enhanced_cognee').is_symlink()
            and os.readlink(profile / 'plugins/enhanced_cognee') == str(native['PROVIDER']))
    preserved = {name: hashlib.sha256((profile / name).read_bytes()).hexdigest()
                 for name in ('.env', 'config.yaml', 'enhanced_cognee.json', 'auth.json')}
    counts = gateway['network_guard']()  # Memory loopback only; model resolution cannot call out.
    PHASE = 'native_imports'
    sys.path.insert(0, str(RELEASE / 'repo'))
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionSource
    from gateway.turn_context import TurnContext
    from gateway.run_turn_runner import TurnRunner
    from agent.secret_scope import current_secret_scope_home, load_env_file
    from hermes_cli.runtime_provider import frozen_runtime_config, resolve_runtime_provider
    from run_agent import AIAgent
    runner = GatewayRunner(GatewayConfig(multiplex_profiles=True,
        sessions_dir=Path(account.pw_dir) / ('runtime-check-sessions-' + ident)))
    source = SessionSource(platform=Platform.TELEGRAM, chat_id='qualification', user_id='qualification')
    ctx = TurnContext(source=source, session_id='route_' + ident, session_key='route_' + ident,
        user_config=config, enabled_toolsets=['memory'], disabled_toolsets=None, AIAgent=AIAgent)
    turn = TurnRunner(runner, ctx)
    PHASE = 'configured_route_resolution'
    with runner._profile_scope_for_source(source):
        require(current_secret_scope_home() == str(profile))
        with frozen_runtime_config(config):
            runtime = resolve_runtime_provider(requested=config['model']['provider'], target_model=config['model']['default'])
        metadata = route_metadata(config, runtime)
        # Use the native turn-route builder so configured request overrides and
        # provider identity stay paired with the resolved credential.
        route = runner._resolve_turn_agent_config('', config['model']['default'], runtime)
        PHASE = 'native_agent_construction'
        first, reused = turn._resolve_turn_agent(route, 'telegram', '', 6, {'enabled': True, 'effort': 'low'}, {})
        require(not reused and isinstance(first, AIAgent))
        again, reused = turn._resolve_turn_agent(route, 'telegram', '', 6, {'enabled': True, 'effort': 'low'}, {})
        require(reused and again is first)
        PHASE = 'scoped_memory_status'
        providers = [p for p in first._memory_manager._providers if p.name == 'enhanced_cognee']
        require(len(providers) == 1 and Path(sys.modules[type(providers[0]).__module__].__file__).resolve()
                == native['PROVIDER'] / '__init__.py')
        require(providers[0]._client.token == load_env_file(profile / '.env').get('ENHANCED_COGNEE_ACCESS_TOKEN'))
        status = providers[0]._client.request('GET', '/v1/memories/status')
        require(status.get('ready') is True and all(status.get(k) == v for k, v in expected.items()))
    PHASE = 'preservation'
    require(all(hashlib.sha256((profile / name).read_bytes()).hexdigest() == digest for name, digest in preserved.items()))
    require(not runner.adapters and counts['forbidden'] == 0)
    return dict(dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), route=metadata,
        invocation_id=invocation, uid=account.pw_uid,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def validate_rows(plans, manifest):
    require(len(plans) == 45 and len(manifest) == 39
            and len({r['profile_id'] for r in plans}) == 45
            and len({r['profile_id'] for r in manifest}) == 39)
    rows = []
    for item in manifest:
        ident = item['profile_id']
        require(re.fullmatch('[a-f0-9]{16}', ident))
        matches = [p for p in plans if p['profile_id'] == ident]
        require(len(matches) == 1)
        plan = matches[0]
        require(plan['existing_binding'] is None and plan['enabled'] is False
                and Path(plan['source_profile']).parent == Path('/home/vincentspereira/.hermes/profiles')
                and plan['proposed_user'] == 'ecbot_' + ident
                and plan['proposed_home'] == '/var/lib/enhanced-cognee-profiles/' + ident)
        evidence = Path(item['evidence'])
        require(evidence.name == ident and evidence.parent in {
            BASE / 'operator-evidence/named-provider-batch-wa_1extn', RESUMED})
        rows.append(dict(profile_id=ident, user=plan['proposed_user'],
            home=plan['proposed_home'], scope=plan['proposed_binding'], evidence=str(evidence)))
    return rows


def selected(read):
    result = json.loads(read(RESUMED / 'summary.json', 0))
    require(result.get('complete') is True and result.get('qualified_new_private_profiles_total') == 39
            and result.get('operator_helper_sha256') == '9d1d87ad5e8695494f2f184b9e32d4112b0aae70315fedf3f0167e1467a1501c')
    raw = read(PLAN, 0)
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA)
    plans = json.loads(raw)['profiles']
    rows = validate_rows(plans, json.loads(read(RESUMED / 'qualified-profiles.private.json', 0)))
    for row in rows:
        done = json.loads(read(Path(row['evidence']) / 'summary.json', 0))
        require(done.get('profile_id') == row['profile_id'] and all(done.get(k) is True for k in
            ('complete', 'candidate_provider_api_qualified', 'peer_history_denied', 'post_configuration_backup_qualified')))
        binding = json.loads(read(Path(row['evidence']) / 'binding.private.json', 0))
        require(binding['scope'] == row['scope'] and binding['user'] == row['user']
                and binding['profile'] == row['home'] + '/.hermes' and type(binding['uid']) is int)
        row['uid'] = binding['uid']
    first = json.loads(read(FIRST / 'binding.private.json', 0))
    matches = [p for p in plans if p['proposed_user'] == first['user']]
    require(len(matches) == 1 and matches[0]['existing_binding'] is None
            and matches[0]['proposed_binding'] == first['scope'])
    plan = matches[0]
    require(plan['enabled'] is False and Path(plan['source_profile']).parent == Path('/home/vincentspereira/.hermes/profiles'))
    prior = json.loads(read(BASE / 'operator-evidence/candidate-live-reload-o40ee8a4/summary.json', 0))
    require(prior.get('complete') is True and prior.get('candidate_headless_gateway_reload_qualified') is True)
    rows.insert(0, dict(profile_id=plan['profile_id'], user=first['user'], home=plan['proposed_home'],
        scope=first['scope'], evidence=str(FIRST), uid=first['uid']))
    require(len(rows) == 40 and len({r['profile_id'] for r in rows}) == 40)
    for row in rows:
        account = pwd.getpwnam(row['user'])
        require(account.pw_uid > 0 and account.pw_uid == row['uid'] and account.pw_dir == row['home']
                and account.pw_shell == '/usr/sbin/nologin'
                and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
    require(len({row['uid'] for row in rows}) == 40)
    return rows


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def properties(unit):
    r = subprocess.run(['/usr/bin/systemctl', 'show', unit,
        '--property=LoadState,ActiveState,SubState,Result,ExecMainStatus,MainPID,ControlPID'], capture_output=True, timeout=10, check=True)
    require(len(r.stdout) <= 8192)
    return dict(line.split('=', 1) for line in r.stdout.decode().splitlines() if '=' in line)


def quiescent(value):
    # Preserve failed states. Failed with no main/control PID is stopped, not a
    # successful test and not a reason to reset-failed or replay anything.
    return (value.get('ActiveState'), value.get('SubState')) in {
        ('inactive', 'dead'), ('failed', 'failed')} and value.get('MainPID') == '0' and value.get('ControlPID') == '0'


def retained_failure(read, write=None, evidence=None):
    prior = BASE / 'operator-evidence/named-runtime-pisfj9fe'
    result = json.loads(read(prior / 'summary.json', 0))
    require(result.get('complete') is False and result.get('selected_profiles') == 40
        and result.get('qualified_profiles') == 0 and result.get('failed_profiles') == 3
        and result.get('unattempted_profiles') == 37 and result.get('credentials_issued') == 0
        and result.get('all_admission_policies_preserved_disabled') is True)
    require(quiescent(properties('ec-launch-named-runtime-20261026.service')))
    failures = []
    for path in sorted(prior.glob('*/child.failure.json')):
        require(re.fullmatch('[a-f0-9]{16}', path.parent.name))
        failure = json.loads(read(path, 0))
        require(failure.get('phase') == 'configured_route_resolution' and failure.get('error_kind') == 'AuthError')
        unit = json.loads(read(path.with_name('unit.started.json'), 0))['unit']
        require(re.fullmatch(r'ec-named-runtime-[a-f0-9]{32}\.service', unit) and quiescent(properties(unit)))
        failures.append(dict(profile_id=path.parent.name, phase=failure['phase'], error_kind='AuthError', quiescent=True))
    require(len(failures) == 3)
    if write is not None:
        write(evidence / 'retained-failure-reconciliation.json', json.dumps(dict(previous=str(prior),
            original_failures_preserved=True, prior_operator_job_quiescent=True, failures=failures)).encode())


def stopped(unit):
    value = properties(unit)
    return quiescent(value)


def finish_unit(unit):
    if stopped(unit):
        return True
    subprocess.run(['/usr/bin/systemctl', 'stop', unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    return stopped(unit)


def verify_receipt(value, metadata, row, digest):
    require(set(value) == TRUE_FLAGS | FALSE_FLAGS | {'route', 'invocation_id', 'uid', 'source_sha256'}
            and all(value.get(k) is True for k in TRUE_FLAGS)
            and all(value.get(k) is False for k in FALSE_FLAGS)
            and value.get('invocation_id') == metadata['InvocationID']
            and type(value.get('uid')) is int and value['uid'] == row['uid']
            and value.get('source_sha256') == digest)
    require(value['route'] == dict(provider='zai', model='glm-5.3-flash', host='open.bigmodel.cn', api_mode='chat_completions'))
    return value


def native_probe(row, evidence, native, write):
    ident = uuid.uuid4().hex
    unit = 'ec-named-runtime-' + ident + '.service'
    write(evidence / 'unit.started.json', json.dumps(dict(unit=unit)).encode())
    sync_directory(evidence)
    profile = row['home'] + '/.hermes'
    args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + unit]
    settings = dict(Type='oneshot', RemainAfterExit='yes', User=row['user'], Group=row['user'],
        SupplementaryGroups='', UMask='0077', NoNewPrivileges='yes', CapabilityBoundingSet='', AmbientCapabilities='',
        ProtectHome='yes', ProtectSystem='strict', PrivateTmp='yes', ProtectProc='invisible', RestrictSUIDSGID='yes',
        ReadWritePaths=row['home'], WorkingDirectory=row['home'], Restart='no', LimitCORE='0', TimeoutStartSec='90')
    args += ['--property=' + k + '=' + v for k, v in settings.items()]
    for field, key in [('PROJECT_ID', 'project_id'), ('TENANT_ID', 'tenant'), ('SUBJECT', 'sub')]:
        args += ['--setenv=EC_EXPECTED_' + field + '=' + row['scope'][key]]
    args += ['--setenv=HOME=' + profile, '--setenv=HERMES_HOME=' + profile,
        EXECUTABLE, '-I', '-B', str(ARTIFACT / Path(__file__).name), '--child', ident]
    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
        deadline = time.monotonic() + 100
        while True:
            metadata = native['properties'](unit)
            if metadata.get('SubState') == 'exited' or metadata.get('ActiveState') == 'failed':
                break
            require(time.monotonic() < deadline)
            time.sleep(1)
        write(evidence / 'unit.metadata.json', json.dumps(metadata).encode())
        journal = subprocess.run(['/usr/bin/journalctl', '--unit=' + unit, '--no-pager', '--lines=12', '--output=json'],
            capture_output=True, check=True, timeout=10)
        require(len(journal.stdout) <= 65536)
        receipts = []
        for line in journal.stdout.splitlines():
            event = json.loads(line)
            if event.get('_SYSTEMD_INVOCATION_ID') != metadata.get('InvocationID') or event.get('_UID') != str(row['uid']):
                continue
            try:
                value = json.loads(event.get('MESSAGE', ''))
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and value.get('complete') is False and value.get('phase') in PHASES:
                write(evidence / 'child.failure.json', json.dumps(dict(phase=value['phase'],
                    http_status=value.get('http_status') if type(value.get('http_status')) is int and 100 <= value['http_status'] <= 599 else None,
                    error_kind=value.get('error_kind') if value.get('error_kind') in {'ValueError', 'PermissionError', 'FileNotFoundError', 'AuthError', 'RuntimeError'} else 'other')).encode())
                continue
            receipts.append(verify_receipt(value, metadata, row, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        native['verified_metadata'](metadata, pwd.getpwnam(row['user']))
        require(len(receipts) == 1)
        write(evidence / 'native.receipt.json', json.dumps(receipts[0]).encode())
    finally:
        require(finish_unit(unit))


def worker(read, write):
    require(os.geteuid() == 0 and Path(__file__).parent == ARTIFACT)
    context = json.loads(read(ARTIFACT / 'context.json', 0))
    evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence' and evidence.name.startswith('named-runtime-models-'))
    native = definitions(ARTIFACT / 'qualify_launch_candidate_native_unit.py', PINS['qualify_launch_candidate_native_unit.py'])
    rows = selected(read)
    retained_failure(read, write, evidence)
    model = definitions(ARTIFACT / 'bind_launch_model_credential.py', PINS['bind_launch_model_credential.py'])
    model_source = (ARTIFACT / 'bind_launch_model_credential.py').read_bytes()
    model_context = model['prepare'](model_source, definitions)
    policies = [BASE / 'operator-isolated-issuer-candidate-v3/candidate-policy.json',
                Path('/etc/enhanced-cognee/fleet-credentials.json')]
    before = {p: read(p, 0) for p in policies}
    require(all(row['enabled'] is False for raw in before.values() for row in json.loads(raw)['profiles']))
    result = dict(complete=False, phase='repair_model_bindings', evidence=str(evidence), source_revision=BASE.name,
        selected_profiles=40, qualified_profiles=0, failed_profiles=0, credentials_issued=0,
        existing_model_bindings_localized=0, refreshed_candidate_restores_qualified=0,
        model_binding_attempts=0, candidate_model_credentials_may_have_changed=False,
        canonical_memory_edits=False, chat_model_called=False, platform_adapters_started=0,
        existing_launchers_changed=False, production_renewal_timer_enabled=False,
        actual_profile_admission_qualified=False, fleet_launch_approved=False)
    write(evidence / 'started.json', json.dumps(result).encode())
    for index, row in enumerate(rows, 1):
        per = evidence / row['profile_id']
        per.mkdir(mode=0o700)
        write(per / 'binding.private.json', json.dumps(row).encode())
        progress = dict(event='native_runtime_progress', current=index, total=40,
                        qualified=result['qualified_profiles'], failed=result['failed_profiles'])
        write(evidence / ('progress-' + str(index).zfill(4) + '.json'), json.dumps(progress).encode())
        try:
            result['model_binding_attempts'] += 1
            result['candidate_model_credentials_may_have_changed'] = True
            model['bind_and_backup'](row, per, model_source, model_context, read, write)
            result['existing_model_bindings_localized'] += 1
            result['refreshed_candidate_restores_qualified'] += 1
            native_probe(row, per, native, write)
            result['qualified_profiles'] += 1
            write(per / 'summary.json', b'{"complete":true,"configured_route_constructor_qualified":true}')
        except Exception as error:
            result['failed_profiles'] += 1
            failure_phase = getattr(error, 'phase', None)
            if failure_phase in model['PHASES']:
                result['failure_phase'] = failure_phase
            write(per / 'summary.json', json.dumps(dict(complete=False, category='native_runtime_incomplete_preserve_evidence',
                failure_phase=failure_phase if failure_phase in model['PHASES'] else 'native_construction_or_backup',
                error_kind=type(error).__name__ if type(error).__name__ in {'ValueError', 'PermissionError', 'FileNotFoundError', 'TimeoutExpired'} else 'other')).encode())
            # A shared failure must be investigated rather than repeated forty times.
            if result['failed_profiles'] >= 1:
                break
    require(all(read(p, 0) == raw for p, raw in before.items()))
    result.update(complete=result['qualified_profiles'] == 40, all_admission_policies_preserved_disabled=True,
                  unattempted_profiles=40-result['qualified_profiles']-result['failed_profiles'])
    if not result['complete']:
        result['category'] = 'native_runtime_batch_incomplete_preserve_evidence_no_automatic_retry'
    write(evidence / 'summary.json', json.dumps(result).encode())
    return 0 if result['complete'] else 1


def watch(read):
    context = json.loads(read(ARTIFACT / 'context.json', 0))
    evidence = Path(context['evidence'])
    require(context.get('unit') == UNIT and evidence.parent == BASE / 'operator-evidence'
            and re.fullmatch('named-runtime-models-[A-Za-z0-9_-]{6,64}', evidence.name))
    latest, emitted, began = None, 0, time.monotonic()
    try:
        while True:
            paths = sorted(evidence.glob('progress-*.json'))
            if paths and paths[-1].name != latest:
                print(read(paths[-1], 0).decode(), flush=True)
                latest, emitted = paths[-1].name, time.monotonic()
            metadata = properties(UNIT)
            try:
                result = json.loads(read(evidence / 'summary.json', 0))
            except FileNotFoundError:
                result = None
            if result is not None or metadata.get('ActiveState') == 'failed' or metadata.get('SubState') == 'exited':
                if result is None:
                    result = dict(complete=False, category='worker_exited_before_receipt_preserve_evidence', evidence=str(evidence))
                result['operator_job_stopped'] = finish_unit(UNIT)
                result['complete'] = result.get('complete') is True and result['operator_job_stopped']
                print(json.dumps(result), flush=True)
                return 0 if result['complete'] else 1
            if stopped(UNIT) and time.monotonic()-began > 30:
                print(json.dumps(dict(complete=False, category='operator_job_not_running_preserve_evidence', evidence=str(evidence))), flush=True)
                return 1
            if time.monotonic()-emitted >= 15:
                print(json.dumps(dict(event='native_runtime_running', last_checkpoint=latest,
                    note='Ctrl+C detaches; repeat repair-model-bindings to reattach without repeating probes.')), flush=True)
                emitted = time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True, job_continues=True, evidence=str(evidence))), flush=True)
        return 0


def launch():
    require(os.geteuid() == 0)
    directory = Path(__file__).parent
    shared = definitions(directory / 'recover_launch_graph_operator.py', PINS['recover_launch_graph_operator.py'])
    read, write = shared['read_file'], shared['private_write']
    if os.path.lexists(ARTIFACT):
        return watch(read)
    selected(read)
    retained_failure(read)
    native = definitions(directory / 'qualify_launch_candidate_native_unit.py', PINS['qualify_launch_candidate_native_unit.py'])
    gateway = definitions(directory / 'qualify_launch_gateway_renewal_v2.py', PINS['qualify_launch_gateway_renewal_v2.py'])
    # Use the already protected verifier; none of these files contains credentials.
    driver = native['definitions'](BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path, digest in [(RELEASE / 'repo' / name, digest) for name, digest in dict(gateway['NATIVE'], **ROUTE_PINS).items()] + [
        (gateway['PROVIDER'] / name, digest) for name, digest in gateway['PROVIDER_FILES'].items()]:
        driver['protected'](path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest)
    driver['protected'](Path(EXECUTABLE), final_link=True)
    driver['protected'](Path(EXECUTABLE).resolve())
    require(stopped(UNIT) and properties(UNIT).get('LoadState') == 'not-found')
    raw_sources = {Path(__file__).name: globals()['_verified_source_bytes']}
    for name, digest in PINS.items():
        raw_sources[name] = definitions(directory / name, digest)['_verified_source_bytes']
    evidence = Path(tempfile.mkdtemp(prefix='named-runtime-models-', dir=BASE / 'operator-evidence'))
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)
    for name, raw in raw_sources.items():
        write(ARTIFACT / name, raw)
        (ARTIFACT / name).chmod(0o644)
    write(ARTIFACT / 'context.json', json.dumps(dict(evidence=str(evidence), unit=UNIT)).encode())
    write(ARTIFACT / 'sources.json', json.dumps({n: hashlib.sha256(r).hexdigest() for n, r in raw_sources.items()}).encode())
    sync_directory(ARTIFACT)
    sync_directory(evidence)
    args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + UNIT]
    settings = operator_properties(selected(read))
    args += ['--property=' + k + '=' + v for k, v in settings.items()]
    args += [str(BASE / 'runtime/bin/python'), '-I', '-B', str(ARTIFACT / Path(__file__).name), '--worker']
    subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
    return watch(read)


def operator_properties(rows):
    homes = [r['home'] for r in rows]
    require(len(homes) == 40 and len(set(homes)) == 40 and all(
        re.fullmatch('/var/lib/enhanced-cognee-profiles/[a-f0-9]{16}', h) for h in homes))
    # Only the trusted owner reader needs the main .env. Original HOME stays
    # read-only; actual native agent units still use ProtectHome=yes.
    return dict(Type='oneshot', RemainAfterExit='yes', User='root', Group='root', UMask='0077',
        NoNewPrivileges='yes', CapabilityBoundingSet='CAP_SETUID CAP_SETGID', AmbientCapabilities='',
        ProtectHome='no', ProtectSystem='strict', ReadOnlyPaths='/home/vincentspereira/.hermes', PrivateTmp='no',
        ReadWritePaths=' '.join([str(BASE / 'operator-evidence'), '/var/backups/enhanced-cognee', '/tmp'] + homes),
        Restart='no', TimeoutStartSec='3600', LimitCORE='0')


if __name__ == '__main__':
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        if len(sys.argv) == 3 and sys.argv[1] == '--child':
            logging.disable(logging.CRITICAL)
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    value = child(sys.argv[2])
            except Exception as error:
                value = dict(complete=False, phase=PHASE, error_kind=type(error).__name__ if type(error).__name__ in {
                    'ValueError', 'PermissionError', 'FileNotFoundError', 'AuthError', 'RuntimeError'} else 'other')
                status = getattr(error, 'status_code', None)
                if type(status) is int and 100 <= status <= 599:
                    value['http_status'] = status
            print(json.dumps(value))
            raise SystemExit(0 if value.get('complete') is True else 1)
        require(sys.argv[1:] == ['--worker'])
        shared = definitions(ARTIFACT / 'recover_launch_graph_operator.py', PINS['recover_launch_graph_operator.py'])
        raise SystemExit(worker(shared['read_file'], shared['private_write']))
    except Exception:
        print('{"complete":false,"category":"named_runtime_preflight_refused_preserve_evidence"}', flush=True)
        raise SystemExit(1)
