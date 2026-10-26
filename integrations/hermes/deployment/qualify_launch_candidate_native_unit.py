"""Finite hardened native-constructor check of the backed-up real candidate.

Use the one inactive candidate and its ordinary scoped memory credential.
No chat model, platform starts, fleet policy changes or scheduled renewal.
Transient completed units are inspected before stopping; evidence is retained.
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
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
EXECUTABLE = str(RELEASE / 'venv/bin/python')
PROVIDER = Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659')
ARTIFACT = BASE / 'operator-candidate-native-unit-probe'
CANDIDATE = BASE / 'operator-evidence/candidate-provider-f8uifc8j'
RECOVERY = BASE / 'operator-evidence/candidate-profile-backup-tjfy2101'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
GATEWAY_SHA = 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2'
FLAGS = {'complete', 'restricted_identity', 'native_gateway_constructed', 'native_agent_constructed',
         'unchanged_agent_reused', 'pinned_provider_bound', 'candidate_token_bound', 'no_platform_adapters', 'non_memory_network_blocked'}
PHASE = 'identity'
PHASES = {'identity', 'fixture_files', 'native_imports', 'gateway_constructor', 'agent_constructor', 'provider_validation'}


def require(value):
    if not value:
        raise ValueError('isolated_native_unit_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_isolated_native_support', '__file__': str(path)}
    exec(compile(raw, '<verified-isolated-native-support>', 'exec'), namespace)
    return namespace


def candidate_config(config):
    require(isinstance(config, dict) and isinstance(config.get('memory'), dict)
        and config['memory'].get('provider') == 'enhanced_cognee'
        and isinstance(config.get('gateway'), dict) and config['gateway'].get('multiplex_profiles') is True)
    secrets = config.get('secrets') or {}
    require(isinstance(secrets, dict) and not any(isinstance(v, dict) and v.get('enabled') is True for v in secrets.values()))
    return config


def restricted_status(account, uid, groups, fields):
    # systemd may include the account's primary GID in initgroups(). It confers
    # no extra group authority; every different supplementary GID is refused.
    require(uid == account.pw_uid and uid != 0 and set(groups) <= {account.pw_gid}
            and fields['NoNewPrivs'].strip() == '1'
            and all(fields[key].strip() == '0000000000000000' for key in ('CapEff', 'CapAmb')))


def stop_units(units):
    outcomes = []
    for unit in units:
        try:
            outcomes.append(subprocess.run(['/usr/bin/systemctl', 'stop', unit],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15).returncode == 0)
        except (OSError, subprocess.TimeoutExpired):
            outcomes.append(False)
    return all(outcomes)


def child(ident):
    global PHASE
    require(re.fullmatch(r'[a-f0-9]{32}', ident) and Path(__file__).parent == ARTIFACT)
    account = pwd.getpwuid(os.geteuid())
    require(re.fullmatch(r'ecbot_[a-f0-9]{16}', account.pw_name))
    require(account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:])
    invocation = os.environ.get('INVOCATION_ID', '')
    require(re.fullmatch(r'[a-f0-9]{32}', invocation))
    profile = Path(account.pw_dir) / '.hermes'
    expected = {key: os.environ['EC_EXPECTED_' + key.upper()] for key in ('project_id', 'tenant_id', 'subject')}
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    restricted_status(account, os.geteuid(), os.getgroups(), fields)
    require(os.environ.get('HOME') == str(profile) and os.environ.get('HERMES_HOME') == str(profile))
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=str(profile), HERMES_HOME=str(profile),
                      LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    PHASE = 'fixture_files'
    os.chdir(profile)
    # Read only fixed private configuration; never print its contents.
    import yaml
    config = candidate_config(yaml.safe_load((profile / 'config.yaml').read_bytes()))
    require(not Path('/etc/hermes').exists())  # Managed secret sources need separate review.
    require(set(os.listdir(profile / 'plugins')) == {'enhanced_cognee'}
        and (profile / 'plugins/enhanced_cognee').is_symlink()
        and os.readlink(profile / 'plugins/enhanced_cognee') == str(PROVIDER))
    preserved = {name: hashlib.sha256((profile / name).read_bytes()).hexdigest()
        for name in ('.env', 'config.yaml', 'enhanced_cognee.json')}
    if (profile / 'auth.json').exists():
        preserved['auth.json'] = hashlib.sha256((profile / 'auth.json').read_bytes()).hexdigest()
    gateway_support = definitions(ARTIFACT / 'qualify_launch_gateway_renewal_v2.py', GATEWAY_SHA)
    counts = gateway_support['network_guard']()
    PHASE = 'native_imports'
    sys.path.insert(0, str(RELEASE / 'repo'))
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionSource
    from gateway.turn_context import TurnContext
    from gateway.run_turn_runner import TurnRunner
    from agent.secret_scope import current_secret_scope_home, load_env_file
    from run_agent import AIAgent
    PHASE = 'gateway_constructor'
    runner = GatewayRunner(GatewayConfig(multiplex_profiles=True, sessions_dir=Path(account.pw_dir) / ('native-unit-sessions-' + ident)))
    source = SessionSource(platform=Platform.TELEGRAM, chat_id='qualification', user_id='qualification')
    ctx = TurnContext(source=source, session_id='unit_' + ident, session_key='unit_' + ident,
        user_config={'memory': {'provider': 'enhanced_cognee'}, 'gateway': {'multiplex_profiles': True}},
        enabled_toolsets=['memory'], disabled_toolsets=None, AIAgent=AIAgent)
    turn = TurnRunner(runner, ctx)
    route = {'model': 'gpt-6.1-sol', 'runtime': {'provider': 'openai-codex', 'api_mode': 'codex_responses',
        'api_key': 'invented-unused-model-credential', 'base_url': 'https://chatgpt.com/backend-api/codex', 'credential_pool': None}}
    def resolve():
        with runner._profile_scope_for_source(source):
            require(current_secret_scope_home() == str(profile))
            return turn._resolve_turn_agent(route, 'telegram', '', 6, {'enabled': True, 'effort': 'low'}, {})
    PHASE = 'agent_constructor'
    first, reused = resolve()
    require(not reused and isinstance(first, AIAgent))
    again, reused = resolve()
    require(reused and again is first)
    PHASE = 'provider_validation'
    providers = [provider for provider in first._memory_manager._providers if provider.name == 'enhanced_cognee']
    require(len(providers) == 1 and Path(sys.modules[type(providers[0]).__module__].__file__).resolve() == PROVIDER / '__init__.py'
            and isinstance(providers[0]._client.token, str) and len(providers[0]._client.token) > 40
            and providers[0]._client.token == load_env_file(profile / '.env').get('ENHANCED_COGNEE_ACCESS_TOKEN'))
    status = providers[0]._client.request('GET', '/v1/memories/status')
    require(status.get('ready') is True and all(status.get(k) == v for k, v in expected.items()))
    require(all(hashlib.sha256((profile / name).read_bytes()).hexdigest() == digest for name, digest in preserved.items()))
    require(not runner.adapters and counts['forbidden'] == 0)
    return dict(dict.fromkeys(FLAGS, True), invocation_id=invocation, uid=account.pw_uid,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def properties(unit):
    fields = 'LoadState,ActiveState,SubState,Result,ExecMainStatus,User,Group,InvocationID,NoNewPrivileges,CapabilityBoundingSet,AmbientCapabilities,ProtectSystem,ProtectHome,PrivateTmp,ProtectProc,RestrictSUIDSGID,ReadWritePaths,SupplementaryGroups'
    process = subprocess.run(['/usr/bin/systemctl', 'show', unit, '--property=' + fields],
        capture_output=True, timeout=10, check=True)
    require(len(process.stdout) <= 16384)
    return dict(line.split('=', 1) for line in process.stdout.decode().splitlines() if '=' in line)


def verified_metadata(value, account):
    expected = dict(LoadState='loaded', ActiveState='active', SubState='exited', Result='success', ExecMainStatus='0',
        User=account.pw_name, Group=account.pw_name, NoNewPrivileges='yes', CapabilityBoundingSet='',
        AmbientCapabilities='', ProtectSystem='strict', ProtectHome='yes', PrivateTmp='yes',
        ProtectProc='invisible', RestrictSUIDSGID='yes', ReadWritePaths=account.pw_dir, SupplementaryGroups='')
    require(all(value.get(key) == expected_value for key, expected_value in expected.items())
            and re.fullmatch(r'[a-f0-9]{32}', value.get('InvocationID', '')))


def verified_receipt(value, metadata, uid, digest):
    require(isinstance(value, dict) and set(value) == FLAGS | {'invocation_id', 'uid', 'source_sha256'}
            and all(value[key] is True for key in FLAGS) and type(value['uid']) is int and value['uid'] == uid
            and value['invocation_id'] == metadata['InvocationID'] and value['source_sha256'] == digest)
    return value


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    shared = definitions(Path(__file__).with_name('recover_launch_graph_operator.py'), SUPPORT_SHA)
    read, write = shared['read_file'], shared['private_write']
    accepted = json.loads(read(CANDIDATE / 'summary.json', 0))
    backup = json.loads(read(RECOVERY / 'summary.json', 0))
    require(accepted.get('complete') is True and accepted.get('candidate_provider_api_qualified') is True
        and accepted.get('operator_helper_sha256') == 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67'
        and backup.get('complete') is True and backup.get('post_configuration_backup_qualified') is True
        and backup.get('operator_helper_sha256') == 'cf10aba63a529bdfffa392fdce2cbc68860133626b1871831e9f60238ab5326c')
    binding = json.loads(read(CANDIDATE / 'binding.private.json', 0))
    account = pwd.getpwnam(binding['user'])
    rows = [dict(user=account.pw_name, uid=binding['uid'], home=account.pw_dir)]
    require(binding['profile'] == str(Path(account.pw_dir) / '.hermes'))
    gateway = definitions(Path(__file__).with_name('qualify_launch_gateway_renewal_v2.py'), GATEWAY_SHA)
    driver = definitions(BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path, digest in [(RELEASE / 'repo' / name, digest) for name, digest in gateway['NATIVE'].items()] + [
            (PROVIDER / name, digest) for name, digest in gateway['PROVIDER_FILES'].items()]:
        driver['protected'](path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest)
    driver['protected'](Path(EXECUTABLE), final_link=True)
    driver['protected'](Path(EXECUTABLE).resolve())
    accounts = []
    for row in rows:
        account = pwd.getpwnam(row['user'])
        require(re.fullmatch(r'ecbot_[a-f0-9]{16}', account.pw_name)
                and account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:]
                and account.pw_uid == row['uid'] and account.pw_dir == row['home']
                and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
        accounts.append(account)
    require(len(accounts) == 1)
    driver['protected'](ARTIFACT.parent)
    write(CANDIDATE / 'candidate-native-unit.started.json', json.dumps(dict(recovery=str(RECOVERY))).encode())
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)
    source = Path(__file__).read_bytes()
    target = ARTIFACT / Path(__file__).name
    write(target, source)
    target.chmod(0o644)
    write(ARTIFACT / 'qualify_launch_gateway_renewal_v2.py', Path(__file__).with_name('qualify_launch_gateway_renewal_v2.py').read_bytes())
    (ARTIFACT / 'qualify_launch_gateway_renewal_v2.py').chmod(0o644)
    evidence = Path(tempfile.mkdtemp(prefix='candidate-native-unit-', dir=BASE / 'operator-evidence'))
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), qualified_unit_count=0,
        real_profiles_copied=0, credentials_issued=0, keys_read=False, chat_model_called=False, memory_records_written=False,
        chat_model_route_verified=False, profile_settings_and_oauth_preserved=False,
        platform_adapters_started=0, existing_launchers_changed=False, actual_profile_admission_qualified=False,
        scheduled_renewal_qualified=False, fleet_launch_approved=False)
    write(evidence / 'started.json', json.dumps(result).encode())
    units = []
    try:
        for account in accounts:
            ident = uuid.uuid4().hex
            unit = 'ec-candidate-native-' + ident + '.service'
            profile = account.pw_dir + '/.hermes'
            args = ['/usr/bin/systemd-run', '--quiet', '--unit=' + unit]
            for key, value in dict(Type='oneshot', RemainAfterExit='yes', User=account.pw_name, Group=account.pw_name,
                SupplementaryGroups='', UMask='0077', NoNewPrivileges='yes', CapabilityBoundingSet='', AmbientCapabilities='',
                ProtectHome='yes', ProtectSystem='strict', PrivateTmp='yes', ProtectProc='invisible',
                RestrictSUIDSGID='yes',
                ReadWritePaths=account.pw_dir, WorkingDirectory=account.pw_dir, Restart='no', LimitCORE='0', TimeoutStartSec='90').items():
                args.append('--property=' + key + '=' + value)
            for field, scope_key in (('project_id', 'project_id'), ('tenant_id', 'tenant'), ('subject', 'sub')):
                args.append('--setenv=EC_EXPECTED_' + field.upper() + '=' + binding['scope'][scope_key])
            args.extend(['--setenv=HOME=' + profile, '--setenv=HERMES_HOME=' + profile,
                         EXECUTABLE, '-I', '-B', str(target), '--child', ident])
            units.append(unit)
            subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=True)
            deadline = time.monotonic() + 95
            while True:
                metadata = properties(unit)
                if metadata.get('SubState') == 'exited' or metadata.get('ActiveState') in {'failed', 'inactive'}:
                    break
                require(time.monotonic() < deadline)
                time.sleep(1)
            write(evidence / (unit + '.metadata.json'), json.dumps(metadata).encode())
            journal = subprocess.run(['/usr/bin/journalctl', '--unit=' + unit, '--no-pager', '--lines=12', '--output=json'],
                capture_output=True, check=True, timeout=10)
            require(len(journal.stdout) <= 65536)
            receipts = []
            for line in journal.stdout.splitlines():
                event = json.loads(line)
                if event.get('_SYSTEMD_INVOCATION_ID') != metadata['InvocationID'] or event.get('_UID') != str(account.pw_uid):
                    continue
                try:
                    value = json.loads(event.get('MESSAGE', ''))
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict) and value.get('complete') is False and value.get('category') == 'isolated_native_child_refused':
                    diagnostic = dict(category='isolated_native_child_refused')
                    if value.get('phase') in PHASES:
                        diagnostic['phase'] = value['phase']
                    if value.get('error_kind') in {'ValueError', 'RuntimeError', 'PermissionError', 'FileNotFoundError', 'ImportError', 'ModuleNotFoundError', 'MemoryError', 'other'}:
                        diagnostic['error_kind'] = value['error_kind']
                    write(evidence / (unit + '.failure.json'), json.dumps(diagnostic).encode())
                    result['child_failure'] = diagnostic
                    continue
                receipts.append(verified_receipt(value, metadata, account.pw_uid, result['operator_helper_sha256']))
            verified_metadata(metadata, account)
            require(len(receipts) == 1)
            write(evidence / (unit + '.receipt.json'), json.dumps(receipts[0]).encode())
            result['qualified_unit_count'] += 1
        result.update(complete=True, candidate_headless_native_unit_qualified=True, profile_settings_and_oauth_preserved=True)
    except Exception:
        result['category'] = 'isolated_native_unit_incomplete_preserve_evidence_no_automatic_retry'
    finally:
        result['transient_units_stopped'] = stop_units(units)
        if not result['transient_units_stopped']:
            result.update(complete=False, category='isolated_native_unit_stop_incomplete_preserve_evidence')
    write(evidence / 'summary.json', json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        logging.disable(logging.CRITICAL)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                value = child(sys.argv[2])
            print(json.dumps(value))
        except Exception as error:
            kind = type(error).__name__
            print(json.dumps(dict(complete=False, category='isolated_native_child_refused', phase=PHASE,
                error_kind=kind if kind in {'ValueError', 'RuntimeError', 'PermissionError', 'FileNotFoundError', 'ImportError', 'ModuleNotFoundError', 'MemoryError'} else 'other')))
            raise SystemExit(1)
    else:
        try:
            raise SystemExit(main())
        except Exception:
            print('{"complete":false,"category":"isolated_native_preflight_refused_no_secret_output"}')
            raise SystemExit(1)
