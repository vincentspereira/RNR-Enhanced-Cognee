#!/usr/bin/env python3
"""Qualify native MCP binding of the preserved main-profile definitions.

The operator unit (root, hardened) verifies retained runtime and policy
state, stages the pinned driver and protocol publicly, then starts hardened
transient units running the driver as the actual restricted main identity.
The identity reads only its own Hermes config; launch values never cross the
boundary. Stage one catalogues every definition through the native managed
launcher resolution under production network conditions. Stage two, only if
a Fetch definition exists, performs the authorized public example.com
retrieval and its private-address refusals. No model, memory API, platform
adapter, credential or bot is touched and all admission stays disabled.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
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

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-native-mcp-binding-v4'
OPERATOR_UNIT = 'ec-native-mcp-binding-operator-v4-20261029.service'
SUPPORT = BASE / 'operator-main-rea-reviewed-candidate-v2/prepare_main_with_telegram.py'
SUPPORT_SHA = 'fc389e21e8f13dd9feb54e35a760ccf482fc0bcf6d79c76ffa13bf3e47bd1d51'
DEPLOY = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment')
INSTALLER = DEPLOY / 'install_managed_mcp_runtime.py'
INSTALLER_SHA = 'a877fd6dd3688ea77d42ae02c94b060340b5a3c217f85df85ec035f987822711'
RECONCILE_ARTIFACT = BASE / 'operator-managed-mcp-runtime-v3'
PROTOCOL = DEPLOY / 'probe_main_local_mcp.py'
PROTOCOL_SHA = '415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'
DRIVER = DEPLOY / 'probe_native_mcp_binding.py'
DRIVER_SHA = '0942dfdb33cc16b107b5fce407ac18513bf25c06f7e676c1b78bfaa18777ce11'
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROGRAM_ROOT = Path('/opt/hermes-runtime/programs')
FIELDS = ['LoadState', 'ActiveState', 'SubState', 'Result', 'ExecMainStatus', 'ExecMainPID',
          'InvocationID', 'User', 'PrivateNetwork', 'ProtectHome', 'NoNewPrivileges',
          'CapabilityBoundingSet', 'AmbientCapabilities', 'IPAddressDeny', 'RestrictAddressFamilies']


def require(value):
    if not value:
        raise ValueError('native_mcp_binding_qualification_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(path, digest):
    raw = Path(path).read_bytes()
    require(0 < len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    scope = {'__name__': 'verified_native_binding_support', '__file__': str(path)}
    exec(compile(raw, '<verified-native-binding-support>', 'exec'), scope)
    return scope


def helpers():
    support = definitions(SUPPORT, SUPPORT_SHA)
    old, c, read, write = support['helpers']()
    return support, old, c, read, write


def metadata(unit):
    process = subprocess.run(['/usr/bin/systemctl', 'show', unit, '--property=' + ','.join(FIELDS)],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=15)
    require(len(process.stdout) <= 32768)
    return dict(row.split('=', 1) for row in process.stdout.decode().splitlines() if '=' in row)


def stopped(state):
    return state.get('ActiveState') in {'inactive', 'failed'} and state.get('SubState') in {'dead', 'failed'}


def retained_runtime():
    """The managed-launch packaging gate closed with the completed reconciliation."""
    raw = (ARTIFACT / 'install_managed_mcp_runtime.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == INSTALLER_SHA)
    spec = importlib.util.spec_from_file_location('install_v1', ARTIFACT / 'install_managed_mcp_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary = json.loads(module.public_read(RECONCILE_ARTIFACT / 'summary.json'))
    require(summary.get('complete') is True
            and summary.get('checkpoint') == 'complete'
            and summary.get('directories_corrected', 0) >= 1
            and summary.get('proof', {}).get('complete') is True
            and summary.get('proof', {}).get('resident_pm_runtime_qualified') is True
            and summary.get('proof', {}).get('native_managed_launcher_selection_qualified') is True
            and summary.get('fleet_launch_approved') is False)
    require(module.no_active_candidates() is None)
    marker = (RELEASE / 'pm-runtime/pm-runtime.json').read_bytes()
    require(marker == b'{\n  "python": "../python/python-3.14.7+20260901-linux-x64/bin/python3.14",\n'
                      b'  "sitePackages": "lib/python3.14/site-packages"\n}\n')
    return summary


def validate_catalogue(value, invocation):
    require(isinstance(value, dict) and value.get('stage') == 'catalogue'
            and value.get('invocation_id') == invocation
            and type(value.get('complete')) is bool
            and isinstance(value.get('definition_count'), int)
            and 1 <= value['definition_count'] <= 8
            and isinstance(value.get('servers'), dict)
            and len(value['servers']) == value['definition_count']
            and re.fullmatch('[a-f0-9]{64}', str(value.get('config_sha256'))))
    for name, row in value['servers'].items():
        require(isinstance(name, str) and 0 < len(name) <= 64 and isinstance(row, dict)
                and type(row.get('complete')) is bool
                and row.get('resolved_via') in {'managed', 'passthrough', 'path', None}
                and type(row.get('env_key_count')) is int)
        if row['complete']:
            require(row['initialize_passed'] is row['tools_list_passed'] is True
                    and type(row['tools_count']) is int and 1 <= row['tools_count'] <= 512
                    and row.get('resolved_via') in {'managed', 'passthrough', 'path'}
                    and type(row.get('private_denials')) is int
                    and row['private_denials'] in {0, 2})
        else:
            require(set(row) <= {'complete', 'resolved_via', 'initialize_passed', 'tools_list_passed',
                                 'tools_count', 'private_denials', 'env_key_count', 'error_kind'}
                    and row.get('error_kind') in {'ValueError', 'TimeoutError', 'OSError',
                                                  'PermissionError', 'JSONDecodeError',
                                                  'BrokenPipeError', 'other'})
    require(value['complete'] == all(row['complete'] for row in value['servers'].values()))
    return value


def validate_fetch(value, invocation):
    require(isinstance(value, dict) and value.get('stage') == 'fetch-public'
            and value.get('invocation_id') == invocation
            and isinstance(value.get('server'), str) and 0 < len(value['server']) <= 64
            and type(value.get('complete')) is bool)
    if value['complete']:
        require(value['raw_passed'] is value['default_extraction_qualified'] is True
                and value['private_denials'] == 2)
    return value


def journal_receipt(rows, state, account_uid, validate, invocation):
    candidates = [row for row in rows if isinstance(row, dict)
                  and row.get('_SYSTEMD_INVOCATION_ID') == state.get('InvocationID')
                  and row.get('_PID') == state.get('ExecMainPID')
                  and row.get('_UID') == str(account_uid)
                  and row.get('_TRANSPORT') == 'stdout' and isinstance(row.get('MESSAGE'), str)]
    require(len(candidates) == 1 and len(candidates[0]['MESSAGE']) <= 8192)
    receipt = validate(json.loads(candidates[0]['MESSAGE']), invocation)
    require((state.get('Result') == 'success' and state.get('ExecMainStatus') == '0') == receipt['complete'])
    return receipt


def child_unit(unit, stage, account, networked):
    public = PROGRAM_ROOT / ('native-binding-' + uuid.uuid4().hex)
    require(not os.path.lexists(public))
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    staged = {}
    for name in ('probe_native_mcp_binding.py', 'probe_main_local_mcp.py'):
        staged[name] = hashlib.sha256((ARTIFACT / name).read_bytes()).hexdigest()
    (public / 'driver.py').write_bytes((ARTIFACT / 'probe_native_mcp_binding.py').read_bytes())
    (public / 'driver.py').chmod(0o644)
    (public / 'protocol.py').write_bytes((ARTIFACT / 'probe_main_local_mcp.py').read_bytes())
    (public / 'protocol.py').chmod(0o644)
    require(hashlib.sha256((public / 'protocol.py').read_bytes()).hexdigest() == PROTOCOL_SHA)
    home = Path('/run') / ('ec-native-mcp-' + stage + '-' + uuid.uuid4().hex[:16])
    settings = dict(Type='oneshot', RemainAfterExit='yes', User=account.pw_name, Group=str(account.pw_gid),
                    NoNewPrivileges='yes', CapabilityBoundingSet='', AmbientCapabilities='', UMask='0077',
                    ProtectHome='yes', ProtectSystem='strict', PrivateTmp='yes',
                    Environment='HOME=' + str(home),
                    RuntimeDirectory=home.name, RuntimeDirectoryMode='0700',
                    RuntimeDirectoryPreserve='yes', ReadWritePaths=str(home),
                    InaccessiblePaths='/etc/enhanced-cognee /var/backups/enhanced-cognee /opt/enhanced-cognee-memory',
                    StandardOutput='journal', StandardError='null', KillMode='control-group',
                    Restart='no', TimeoutStartSec='420', MemoryMax='2G', LimitCORE='0',
                    SystemCallFilter='~ptrace process_vm_writev', RestrictSUIDSGID='yes')
    if not networked:
        settings['PrivateNetwork'] = 'yes'
        settings['IPAddressDeny'] = 'any'
        settings['RestrictAddressFamilies'] = 'AF_UNIX'
    args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + unit]
    args += ['--property=' + key + '=' + value for key, value in settings.items()]
    args += [str(RELEASE / 'venv/bin/python'), '-I', '-B', str(public / 'driver.py'),
             stage, str(home), str(public / 'protocol.py')]
    subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
    return public, home, staged


def run_stage(unit, stage, account, validate, networked):
    require(metadata(unit).get('LoadState') == 'not-found')
    public, home, staged = child_unit(unit, stage, account, networked)
    try:
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline:
            state = metadata(unit)
            if state.get('SubState') == 'exited' or state.get('ActiveState') in {'inactive', 'failed'}:
                break
            time.sleep(2)
        else:
            raise TimeoutError('native_binding_stage_deadline')
        invocation = state.get('InvocationID', '')
        require(re.fullmatch('[a-f0-9]{32}', invocation))
        require(state.get('User') == account.pw_name
                and state.get('NoNewPrivileges') == 'yes'
                and state.get('CapabilityBoundingSet') == state.get('AmbientCapabilities') == ''
                and state.get('PrivateNetwork') == ('yes' if not networked else ''))
        process = subprocess.run(['/usr/bin/journalctl', '--no-pager', '--output=json',
                                  '--lines=16', '--unit=' + unit],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=15)
        require(len(process.stdout) <= 65536)
        rows = [json.loads(row) for row in process.stdout.splitlines()]
        receipt = journal_receipt(rows, state, account.pw_uid, validate, invocation)
    finally:
        subprocess.run(['/usr/bin/systemctl', 'stop', unit],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
        require(stopped(metadata(unit)))
    return receipt, dict(public=str(public), home=str(home), staged=staged, invocation=invocation)


def worker():
    require(os.geteuid() == 0 and Path(__file__).parent == ARTIFACT)
    support, old, c, read, write = helpers()
    context = json.loads(read(ARTIFACT / 'context.private.json', 0))
    evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence'
            and evidence.name.startswith('native-mcp-binding-'))
    driver_before = c['legacy']()['policies'](read)
    entry, _ = c['legacy']()['fixed_entry'](read)
    require(entry['user'] == 'ecbot_5592956882ea9a13' and entry['enabled'] is False)
    account = pwd.getpwnam(entry['user'])
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
                  operator_helper_sha256=context['source_sha256'],
                  invocation_id=os.environ.get('INVOCATION_ID', ''),
                  credentials_issued=0, keys_read=False, model_called=False,
                  memory_api_called=False, external_platform_sends=0, platform_adapters_started=0,
                  source_profiles_changed=False, previous_candidates_changed=False,
                  source_profile_config_read_by_root=False, config_values_crossed_identity_boundary=False,
                  definition_values_in_receipts=False, full_main_tool_coverage_qualified=False,
                  actual_profile_admission_qualified=False, production_dispatch_qualified=False,
                  production_renewal_timer_enabled=False, fleet_launch_approved=False,
                  automatic_retry=False, fetch_binding_deferred=False,
                  qualification_surface='native_launcher_binding_actual_main_identity')
    try:
        require(re.fullmatch('[a-f0-9]{32}', result['invocation_id']))
        result['checkpoint'] = 'retained_runtime_and_policies'
        retained_runtime()
        result['checkpoint'] = 'native_catalogue'
        # Native npx/uvx resolution fetches public MCP packages on cache miss,
        # exactly as production launches do; the networked posture is recorded.
        catalogue, stage_a = run_stage('ec-native-mcp-cat-' + context['id'] + '.service',
                                       'catalogue', account, validate_catalogue, networked=True)
        write(evidence / 'catalogue-receipt.json', canonical(catalogue))
        result['catalogue'] = catalogue
        result['stages'] = {'catalogue': stage_a}
        if catalogue.get('fetch_server'):
            result['checkpoint'] = 'native_fetch_public'
            fetch, stage_b = run_stage('ec-native-mcp-fetch-' + context['id'] + '.service',
                                       'fetch-public', account, validate_fetch, networked=True)
            write(evidence / 'fetch-public-receipt.json', canonical(fetch))
            result['fetch_public'] = fetch
            result['stages']['fetch-public'] = stage_b
            result['native_fetch_binding_qualified'] = fetch['complete']
        else:
            result['fetch_binding_deferred'] = True
            result['native_fetch_binding_qualified'] = False
        result['checkpoint'] = 'complete' if catalogue['complete'] else 'catalogue_failure'
        result['complete'] = bool(catalogue['complete'])
        result['native_mcp_binding_qualified'] = bool(catalogue['complete'])
        result['native_launch_network_used'] = True
        result['retained_copy_reuse'] = False
        result['qualification_unit_stopped'] = True
    except Exception as error:
        result.update(category='native_mcp_binding_incomplete_preserve_evidence',
                      error_kind=type(error).__name__ if type(error).__name__ in
                      {'ValueError', 'TimeoutError', 'TimeoutExpired', 'OSError',
                       'PermissionError', 'subprocess.CalledProcessError'} else 'other')
    require(all(read(path, 0) == raw for path, raw in driver_before.items()))
    result['all_admission_policies_preserved_disabled'] = True
    write(evidence / 'summary.json', canonical(result))
    return 0 if result['complete'] else 1


def watch(read, write):
    context = json.loads(read(ARTIFACT / 'context.private.json', 0))
    evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence'
            and evidence.name.startswith('native-mcp-binding-'))
    if os.path.lexists(evidence / 'finish.summary.json'):
        result = json.loads(read(evidence / 'finish.summary.json', 0))
        require(result.get('operator_helper_sha256') == context['source_sha256']
                and result.get('operator_job_stopped') is True)
        print(json.dumps(result), flush=True)
        return 0 if result['complete'] else 1
    try:
        last = 0
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            state = metadata(OPERATOR_UNIT)
            if os.path.lexists(evidence / 'summary.json') and (state.get('SubState') == 'exited'
                                                               or state.get('ActiveState') in {'inactive', 'failed'}):
                result = json.loads(read(evidence / 'summary.json', 0))
                require(result.get('operator_helper_sha256') == context['source_sha256'])
                if result['complete']:
                    require(state.get('Result') == 'success' and state.get('ExecMainStatus') == '0'
                            and state.get('InvocationID') == result['invocation_id'])
                subprocess.run(['/usr/bin/systemctl', 'stop', OPERATOR_UNIT],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
                require(metadata(OPERATOR_UNIT).get('ActiveState') in {'inactive', 'failed'})
                result['operator_job_stopped'] = True
                write(evidence / 'finish.summary.json', canonical(result))
                print(json.dumps(result), flush=True)
                return 0 if result['complete'] else 1
            require(state.get('ActiveState') not in {'inactive', 'failed'})
            if time.monotonic() - last >= 10:
                print('{"event":"native_binding_running","note":"Ctrl+C detaches; repeat the same command to reattach without replay."}', flush=True)
                last = time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print('{"detached":true,"job_continues":true}', flush=True)
        return 0
    raise TimeoutError('native_binding_watch_deadline')


def launch():
    require(os.geteuid() == 0)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    source = Path(__file__).read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    support, old, c, read, write = helpers()
    if os.path.lexists(ARTIFACT / 'context.private.json'):
        context = json.loads(read(ARTIFACT / 'context.private.json', 0))
        require(context['source_sha256'] == digest)
        for name, pin in json.loads(read(ARTIFACT / 'sources.json', 0)).items():
            require(re.fullmatch(r'[a-z0-9_.]+\.py', name)
                    and hashlib.sha256((ARTIFACT / name).read_bytes()).hexdigest() == pin)
        return watch(read, write)
    driver_before = c['legacy']()['policies'](read)
    entry, _ = c['legacy']()['fixed_entry'](read)
    require(entry['user'] == 'ecbot_5592956882ea9a13' and entry['enabled'] is False)
    require(not os.path.lexists(ARTIFACT) and metadata(OPERATOR_UNIT).get('LoadState') == 'not-found')
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)
    sources = {'qualify_native_mcp_binding.py': source,
               'probe_native_mcp_binding.py': DRIVER.read_bytes(),
               'probe_main_local_mcp.py': PROTOCOL.read_bytes(),
               'install_managed_mcp_runtime.py': INSTALLER.read_bytes()}
    require(hashlib.sha256(sources['probe_native_mcp_binding.py']).hexdigest() == DRIVER_SHA)
    require(hashlib.sha256(sources['probe_main_local_mcp.py']).hexdigest() == PROTOCOL_SHA)
    require(hashlib.sha256(sources['install_managed_mcp_runtime.py']).hexdigest() == INSTALLER_SHA)
    for name, raw in sources.items():
        write(ARTIFACT / name, raw)
        (ARTIFACT / name).chmod(0o644)
    write(ARTIFACT / 'sources.json', canonical({name: hashlib.sha256(raw).hexdigest()
                                                for name, raw in sources.items()}))
    # Now that the pinned installer is frozen into the artifact, verify the
    # retained runtime state and the inactive-bot guard before starting the unit.
    retained_runtime()
    evidence = Path(tempfile.mkdtemp(prefix='native-mcp-binding-', dir=BASE / 'operator-evidence'))
    write(ARTIFACT / 'context.private.json',
          canonical(dict(source_sha256=digest, evidence=str(evidence), id=uuid.uuid4().hex)))
    settings = dict(Type='oneshot', RemainAfterExit='yes', User='root', Group='root', UMask='0077',
                    NoNewPrivileges='yes', CapabilityBoundingSet='', AmbientCapabilities='',
                    ProtectSystem='strict', ProtectHome='no', PrivateTmp='yes',
                    ReadWritePaths=' '.join([str(ARTIFACT), str(BASE / 'operator-evidence'), str(PROGRAM_ROOT)]),
                    Restart='no', TimeoutStartSec='800', MemoryMax='3G', LimitCORE='0')
    args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + OPERATOR_UNIT]
    args += ['--property=' + key + '=' + value for key, value in settings.items()]
    args += [str(BASE / 'runtime/bin/python'), '-I', '-B', str(ARTIFACT / 'qualify_native_mcp_binding.py'), '--worker']
    require(all(read(path, 0) == raw for path, raw in driver_before.items()))
    subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
    return watch(read, write)


if __name__ == '__main__':
    try:
        require(sys.argv[1:] in ([], ['--worker']))
        raise SystemExit(worker() if sys.argv[1:] == ['--worker'] else launch())
    except Exception:
        print('{"complete":false,"category":"native_mcp_binding_preflight_refused_no_secret_output"}', flush=True)
        raise SystemExit(1)
