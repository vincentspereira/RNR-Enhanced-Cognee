#!/usr/bin/env python3
"""Inspect the live main profile's memory provider selection, read-only.

The operator unit verifies unchanged disabled policies and stages the pinned
probe publicly; a hardened transient unit runs it as the actual restricted
main identity, which reads only its own Hermes config. The receipt carries
the provider name, memory key names, definition names and counts only.
Nothing is executed, launched, switched or written beyond this evidence.
"""
from __future__ import annotations
import hashlib
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
ARTIFACT = BASE / 'operator-main-memory-selection-v2'
OPERATOR_UNIT = 'ec-main-memory-selection-v2-20261029.service'
SUPPORT = BASE / 'operator-main-rea-reviewed-candidate-v2/prepare_main_with_telegram.py'
SUPPORT_SHA = 'fc389e21e8f13dd9feb54e35a760ccf482fc0bcf6d79c76ffa13bf3e47bd1d51'
DEPLOY = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment')
PROBE = DEPLOY / 'probe_main_memory_selection.py'
BINDING_DRIVER = DEPLOY / 'probe_native_mcp_binding.py'
BINDING_DRIVER_SHA = 'a54f321c30b64924a3b72d0b779f90997ec89674f65e192d6643cd02c3e062d5'
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROGRAM_ROOT = Path('/opt/hermes-runtime/programs')
FIELDS = ['LoadState', 'ActiveState', 'SubState', 'Result', 'ExecMainStatus', 'ExecMainPID',
          'InvocationID', 'User', 'NoNewPrivileges', 'CapabilityBoundingSet']


def require(value):
    if not value:
        raise ValueError('main_memory_selection_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(path, digest):
    raw = Path(path).read_bytes()
    require(0 < len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    scope = {'__name__': 'verified_memory_selection_support', '__file__': str(path)}
    exec(compile(raw, '<verified-memory-selection-support>', 'exec'), scope)
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


def validate(value, invocation):
    require(isinstance(value, dict) and value.get('stage') == 'inspect'
            and value.get('invocation_id') == invocation
            and value.get('complete') is True
            and isinstance(value.get('config_path'), str)
            and re.fullmatch('[a-f0-9]{64}', str(value.get('config_sha256')))
            and isinstance(value.get('memory'), dict)
            and set(value['memory']) == {'provider', 'selected', 'keys'}
            and (value['memory']['provider'] is None
                 or isinstance(value['memory']['provider'], str))
            and type(value['memory']['selected']) is bool
            and value['memory']['selected'] == (value['memory']['provider'] == 'enhanced_cognee')
            and isinstance(value.get('mcp_definition_count'), int)
            and isinstance(value.get('mcp_definition_names'), list))
    return value


def journal_receipt(rows, state, account_uid, invocation):
    candidates = [row for row in rows if isinstance(row, dict)
                  and row.get('_SYSTEMD_INVOCATION_ID') == state.get('InvocationID')
                  and row.get('_PID') == state.get('ExecMainPID')
                  and row.get('_UID') == str(account_uid)
                  and row.get('_TRANSPORT') == 'stdout' and isinstance(row.get('MESSAGE'), str)]
    require(len(candidates) == 1 and len(candidates[0]['MESSAGE']) <= 8192)
    receipt = validate(json.loads(candidates[0]['MESSAGE']), invocation)
    require((state.get('Result') == 'success' and state.get('ExecMainStatus') == '0') is True)
    return receipt


def watch(read, write):
    context = json.loads(read(ARTIFACT / 'context.private.json', 0))
    evidence = Path(context['evidence'])
    if os.path.lexists(evidence / 'finish.summary.json'):
        result = json.loads(read(evidence / 'finish.summary.json', 0))
        require(result.get('operator_helper_sha256') == context['source_sha256'])
        print(json.dumps(result), flush=True)
        return 0 if result['complete'] else 1
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state = metadata(OPERATOR_UNIT)
        if os.path.lexists(evidence / 'summary.json') and (state.get('SubState') == 'exited'
                                                           or state.get('ActiveState') in {'inactive', 'failed'}):
            result = json.loads(read(evidence / 'summary.json', 0))
            require(result.get('operator_helper_sha256') == context['source_sha256'])
            subprocess.run(['/usr/bin/systemctl', 'stop', OPERATOR_UNIT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
            require(stopped(metadata(OPERATOR_UNIT)))
            result['operator_job_stopped'] = True
            write(evidence / 'finish.summary.json', canonical(result))
            print(json.dumps(result), flush=True)
            return 0 if result['complete'] else 1
        time.sleep(2)
    raise TimeoutError('memory_selection_watch_deadline')


def worker():
    require(os.geteuid() == 0 and Path(__file__).parent == ARTIFACT)
    support, old, c, read, write = helpers()
    context = json.loads(read(ARTIFACT / 'context.private.json', 0))
    evidence = Path(context['evidence'])
    driver_before = c['legacy']()['policies'](read)
    entry, _ = c['legacy']()['fixed_entry'](read)
    require(entry['user'] == 'ecbot_5592956882ea9a13' and entry['enabled'] is False)
    account = pwd.getpwnam(entry['user'])
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
                  operator_helper_sha256=context['source_sha256'],
                  invocation_id=os.environ.get('INVOCATION_ID', ''),
                  keys_read=False, model_called=False, memory_api_called=False,
                  credentials_issued=0, external_platform_sends=0, platform_adapters_started=0,
                  source_profiles_changed=False, previous_candidates_changed=False,
                  provider_switched=False, fleet_launch_approved=False, automatic_retry=False,
                  qualification_surface='read_only_memory_selection_actual_main_identity')
    try:
        require(re.fullmatch('[a-f0-9]{32}', result['invocation_id']))
        unit = 'ec-main-memory-sel-' + context['id'] + '.service'
        require(metadata(unit).get('LoadState') == 'not-found')
        public = PROGRAM_ROOT / ('memory-selection-' + uuid.uuid4().hex)
        require(not os.path.lexists(public))
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        probe = (ARTIFACT / 'probe_main_memory_selection.py').read_bytes()
        (public / 'probe.py').write_bytes(probe)
        (public / 'probe.py').chmod(0o644)
        # The child cannot read the artifact tree; stage the pinned binding
        # support beside the probe in the public directory.
        (public / 'binding_support.py').write_bytes((ARTIFACT / 'probe_native_mcp_binding.py').read_bytes())
        (public / 'binding_support.py').chmod(0o644)
        home = Path('/run') / ('ec-main-memory-sel-' + uuid.uuid4().hex[:16])
        settings = dict(Type='oneshot', RemainAfterExit='yes', User=account.pw_name,
                        Group=str(account.pw_gid), NoNewPrivileges='yes',
                        CapabilityBoundingSet='', AmbientCapabilities='', UMask='0077',
                        ProtectHome='yes', ProtectSystem='strict', PrivateTmp='yes',
                        Environment='HOME=' + str(home),
                        RuntimeDirectory=home.name, RuntimeDirectoryMode='0700',
                        ReadWritePaths=str(home),
                        InaccessiblePaths='/etc/enhanced-cognee /var/backups/enhanced-cognee /opt/enhanced-cognee-memory',
                        StandardOutput='journal', StandardError='null', KillMode='control-group',
                        Restart='no', TimeoutStartSec='120', MemoryMax='1G', LimitCORE='0')
        args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + unit]
        args += ['--property=' + key + '=' + value for key, value in settings.items()]
        args += [str(RELEASE / 'venv/bin/python'), '-I', '-B', str(public / 'probe.py'),
                 'inspect', str(home), str(public / 'binding_support.py')]
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            state = metadata(unit)
            if state.get('SubState') == 'exited' or state.get('ActiveState') in {'inactive', 'failed'}:
                break
            time.sleep(2)
        else:
            raise TimeoutError('memory_selection_stage_deadline')
        invocation = state.get('InvocationID', '')
        require(re.fullmatch('[a-f0-9]{32}', invocation))
        require(state.get('User') == account.pw_name and state.get('NoNewPrivileges') == 'yes')
        process = subprocess.run(['/usr/bin/journalctl', '--no-pager', '--output=json',
                                  '--lines=16', '--unit=' + unit],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=15)
        require(len(process.stdout) <= 65536)
        rows = [json.loads(row) for row in process.stdout.splitlines()]
        receipt = journal_receipt(rows, state, account.pw_uid, invocation)
        subprocess.run(['/usr/bin/systemctl', 'stop', unit],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
        require(stopped(metadata(unit)))
        write(evidence / 'selection-receipt.json', canonical(receipt))
        result['memory_selection'] = receipt
        result['complete'] = True
        result['checkpoint'] = 'complete'
        result['qualification_unit_stopped'] = True
    except Exception as error:
        result.update(category='main_memory_selection_incomplete_preserve_evidence',
                      error_kind=type(error).__name__ if type(error).__name__ in
                      {'ValueError', 'TimeoutError', 'TimeoutExpired', 'OSError',
                       'PermissionError', 'subprocess.CalledProcessError'} else 'other')
    require(all(read(path, 0) == raw for path, raw in driver_before.items()))
    result['all_admission_policies_preserved_disabled'] = True
    write(evidence / 'summary.json', canonical(result))
    return 0 if result['complete'] else 1


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
    probe_bytes = PROBE.read_bytes()
    binding_bytes = BINDING_DRIVER.read_bytes()
    require(hashlib.sha256(binding_bytes).hexdigest() == BINDING_DRIVER_SHA)
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)
    sources = {'inspect_main_memory_selection.py': source,
               'probe_main_memory_selection.py': probe_bytes,
               'probe_native_mcp_binding.py': binding_bytes}
    for name, raw in sources.items():
        write(ARTIFACT / name, raw)
        (ARTIFACT / name).chmod(0o644)
    write(ARTIFACT / 'sources.json', canonical({name: hashlib.sha256(raw).hexdigest()
                                                for name, raw in sources.items()}))
    evidence = Path(tempfile.mkdtemp(prefix='main-memory-selection-', dir=BASE / 'operator-evidence'))
    write(ARTIFACT / 'context.private.json',
          canonical(dict(source_sha256=digest, evidence=str(evidence), id=uuid.uuid4().hex)))
    settings = dict(Type='oneshot', RemainAfterExit='yes', User='root', Group='root', UMask='0077',
                    NoNewPrivileges='yes', CapabilityBoundingSet='', AmbientCapabilities='',
                    ProtectSystem='strict', ProtectHome='no', PrivateTmp='yes',
                    ReadWritePaths=' '.join([str(ARTIFACT), str(BASE / 'operator-evidence'), str(PROGRAM_ROOT)]),
                    Restart='no', TimeoutStartSec='300', MemoryMax='2G', LimitCORE='0')
    args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + OPERATOR_UNIT]
    args += ['--property=' + key + '=' + value for key, value in settings.items()]
    args += [str(BASE / 'runtime/bin/python'), '-I', '-B', str(ARTIFACT / 'inspect_main_memory_selection.py'), '--worker']
    require(all(read(path, 0) == raw for path, raw in driver_before.items()))
    subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
    return watch(read, write)


if __name__ == '__main__':
    try:
        require(sys.argv[1:] in ([], ['--worker']))
        raise SystemExit(worker() if sys.argv[1:] == ['--worker'] else launch())
    except Exception:
        print('{"complete":false,"category":"main_memory_selection_preflight_refused_no_secret_output"}', flush=True)
        raise SystemExit(1)
