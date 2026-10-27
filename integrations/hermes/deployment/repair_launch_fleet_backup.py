"""Diagnose first-child permission refusal and admit only a proven root-cap fix.

No profile content, credential, recovery key or archive is read by the probe.
The failed package stays blocked. Only missing effective identity-switching
capabilities, restored by root-only ambient SETUID/SETGID with zero-capability
owner children, can admit a NEW daily job. Every other cause stops for review.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PREVIOUS = BASE / 'operator-fleet-daily-backups-v1'
STATE = BASE / 'operator-fleet-daily-backups-v2'
UNIT_DIRECTORY = Path('/etc/systemd/system')
DIAGNOSTIC = BASE / 'operator-fleet-backup-permission-probe-v1'
FAILED = PREVIOUS / 'run-9suhwfa3'
OLD_SHA = 'cfd9eb39d10951d56235b25d111352d6bebe527360007f0fff8bbc65f7a77a13'
UNIT = 'enhanced-cognee-qualified-fleet-backup-v2'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
PROBE_UNIT = 'ec-fleet-backup-permission'

OWNER_SOURCE = b'''
import json,os,pwd
from pathlib import Path
def child():
 packet=json.loads(__import__('sys').stdin.buffer.readline(1025))
 account=pwd.getpwuid(os.geteuid())
 status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
 valid=(set(packet)=={'uid'} and account.pw_uid==packet['uid'] and account.pw_uid>0
   and not os.getgroups() and status['NoNewPrivs'].strip()=='1'
   and all(status[key].strip()=='0000000000000000' for key in ('CapEff','CapAmb','CapInh')))
 if not valid: raise ValueError('identity_probe_refused')
 print(json.dumps({'complete':True,'receipt':{'identity_restricted':True,'profile_contents_read':False}}))
'''


def require(value):
    if not value: raise ValueError('backup_permission_repair_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def old_driver():
    require(os.geteuid() == 0)
    source = (PREVIOUS / 'install_launch_fleet_backups.py').read_bytes()
    require(0 < len(source) <= 65536 and hashlib.sha256(source).hexdigest() == OLD_SHA)
    scope = {'__name__': 'verified_failed_backup', '__file__': str(PREVIOUS / 'install_launch_fleet_backups.py'),
        '_verified_source_bytes': source}
    exec(compile(source, '<verified-failed-backup>', 'exec'), scope)
    return scope


def retained_failure(old, driver, read):
    value = json.loads(read(FAILED / 'summary.json', 0))
    require(value.get('complete') is False and value.get('error_kind') == 'PermissionError'
            and value.get('operator_helper_sha256') == OLD_SHA and value.get('source_revision') == BASE.name
            and value.get('evidence') == str(FAILED) and value.get('completed_profiles') == 0
            and value.get('selected_profiles') == 41
            and all(value.get(key) is False for key in ('source_profiles_changed', 'keys_changed', 'model_called',
                'memory_api_called', 'recovery_key_read', 'plaintext_archive_written', 'fleet_launch_approved'))
            and value.get('credentials_issued') == 0)
    require(json.loads(read(PREVIOUS / 'blocked.json', 0)) == {'evidence': str(FAILED)})
    require(json.loads(read(PREVIOUS / 'installed.summary.json', 0)) == value)
    require(driver['stopped'](driver['metadata'](old['UNIT'] + '.service'))
            and driver['metadata'](old['UNIT'] + '.timer').get('ActiveState') in {'inactive', 'failed'})
    for suffix in ('.service', '.timer'):
        process = subprocess.run(['/usr/bin/systemctl', 'show', old['UNIT'] + suffix, '--property=DropInPaths'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=10)
        require(process.stdout.strip() == b'DropInPaths=')
    require(not any(os.path.lexists(FAILED / ('completed-' + str(i).zfill(3) + '.json')) for i in range(1, 42)))
    return value


def capabilities():
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    mask = (1 << 6) | (1 << 7)
    return dict(identity_switch_effective=int(status['CapEff'].strip(), 16) & mask == mask,
        identity_switch_permitted=int(status['CapPrm'].strip(), 16) & mask == mask,
        bounding_only_identity_switch=int(status['CapBnd'].strip(), 16) == mask,
        no_new_privileges=status['NoNewPrivs'].strip() == '1')


class OwnerSubprocess:
    """Clear inheritable/ambient authority before any restricted owner code."""
    def __getattr__(self, name):
        return getattr(subprocess, name)

    @staticmethod
    def arguments(args):
        if isinstance(args, list) and args and args[0] == '/usr/bin/setpriv':
            require(args[:3] == ['/usr/bin/setpriv', '--no-new-privs', '--']
                    and len(args) >= 4 and args[3] == '/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python')
            return args[:2] + ['--inh-caps=-all', '--ambient-caps=-all'] + args[2:]
        return args

    def run(self, args, **kwargs):
        return subprocess.run(self.arguments(args), **kwargs)

    def Popen(self, args, **kwargs):
        return subprocess.Popen(self.arguments(args), **kwargs)


def diagnose_spawn(old, driver, row, clear_owner_caps=False):
    result = dict(complete=False, parent_capabilities=capabilities(), child_started=False,
        profile_contents_read=False, backups_created=0, credentials_issued=0, model_called=False)
    phase = 'public_capture_preflight'
    original = driver['definitions']
    class ProbeCompleted(Exception): pass
    def definitions(path, digest):
        scope = original(path, digest)
        if path.name == 'backup_launch_candidate_profile.py':
            if clear_owner_caps: scope['subprocess'] = OwnerSubprocess()
            previous_owner = scope['owner']
            def owner(helper, account, source, packet):
                nonlocal phase
                phase = 'restricted_child_spawn'
                reply = previous_owner(helper, account, OWNER_SOURCE, {})
                require(reply == dict(complete=True, receipt=dict(identity_restricted=True, profile_contents_read=False)))
                result.update(complete=True, child_started=True, child_identity_restricted=True)
                raise ProbeCompleted()
            scope['owner'] = owner
        return scope
    # The exact failed root capture preflight is reused up to child execution.
    # Its owner body is replaced BEFORE invocation with content-free code.
    original_definitions = driver['definitions']
    driver['definitions'] = definitions
    try:
        # capture() uses driver definitions for public helpers, not its local
        # definitions; only the verified delegate above is intercepted.
        old['capture'](driver, row, 'age1' + 'a' * 30)
        require(False)
    except ProbeCompleted:
        result['failure_phase'] = 'none'
    except Exception as error:
        result.update(failure_phase=phase,
            error_kind=type(error).__name__ if type(error).__name__ in {'PermissionError', 'ValueError', 'FileNotFoundError', 'OSError'} else 'other')
        number = getattr(error, 'errno', None)
        if type(number) is int and number in {1, 2, 13, 20, 30, 40}: result['errno'] = number
        filename = getattr(error, 'filename', None)
        if filename == '/usr/bin/setpriv': result['failed_path_kind'] = 'identity_launcher'
        elif filename == row['entry']['executable']: result['failed_path_kind'] = 'native_executable'
        result['helper_lines'] = []
        trace = error.__traceback__
        while trace is not None and len(result['helper_lines']) < 8:
            result['helper_lines'].append(trace.tb_lineno); trace = trace.tb_next
    finally:
        driver['definitions'] = original_definitions
    return result


def probe_worker(kind):
    require(kind in {'baseline', 'ambient'} and Path(__file__).parent == DIAGNOSTIC)
    old = old_driver(); driver, read, write = old['components']()
    rows = old['membership'](driver, read)
    require(rows[0]['kind'] == 'named')
    result = diagnose_spawn(old, driver, rows[0], clear_owner_caps=kind == 'ambient')
    result.update(probe=kind, invocation_id=os.environ.get('INVOCATION_ID', ''),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(DIAGNOSTIC / (kind + '.summary.json'), canonical(result))
    return 0


def probe_properties(old, rows, ambient):
    service = old['unit_text'](rows)[0].decode()
    result = {}
    for line in service.splitlines():
        if '=' not in line: continue
        key, value = line.split('=', 1)
        if key in {'Description', 'ExecStart'}: continue
        result[key] = value
    # Keep the failed unit's protections and writable paths for the reproduction,
    # but no probe code writes to profiles, backup directories or old state.
    result['ReadWritePaths'] += ' ' + str(DIAGNOSTIC)
    result['RemainAfterExit'] = 'yes'
    if ambient: result['AmbientCapabilities'] = 'CAP_SETUID CAP_SETGID'
    return result


def run_probe(kind, old, driver, read, write, rows):
    path = DIAGNOSTIC / (kind + '.summary.json')
    finished = DIAGNOSTIC / (kind + '.finish.json')
    if os.path.lexists(finished):
        result = json.loads(read(finished, 0))
        require(result.get('probe_unit_stopped') is True and result.get('probe') == kind
                and result.get('source_sha256') == hashlib.sha256((DIAGNOSTIC / 'repair_launch_fleet_backup.py').read_bytes()).hexdigest())
        return result
    stem = PROBE_UNIT + '-' + kind + '-20261027'
    if not os.path.lexists(path):
        marker = DIAGNOSTIC / (kind + '.started.json')
        if not os.path.lexists(marker):
            require(driver['metadata'](stem + '.service').get('LoadState') == 'not-found')
            write(marker, canonical(dict(probe=kind)))
            args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + stem]
            args += ['--property=' + key + '=' + value for key, value in probe_properties(old, rows, kind == 'ambient').items()]
            args += [str(BASE / 'runtime/bin/python'), '-I', '-B', str(DIAGNOSTIC / 'repair_launch_fleet_backup.py'), '--probe', kind]
            subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
        deadline = time.monotonic() + 90
        while not os.path.lexists(path):
            require(time.monotonic() < deadline and driver['metadata'](stem + '.service').get('ActiveState') != 'failed')
            time.sleep(1)
    result = json.loads(read(path, 0))
    require(result.get('probe') == kind and result.get('source_sha256') == hashlib.sha256((DIAGNOSTIC / 'repair_launch_fleet_backup.py').read_bytes()).hexdigest()
            and result.get('profile_contents_read') is False and result.get('backups_created') == result.get('credentials_issued') == 0)
    deadline = time.monotonic() + 15
    value = driver['metadata'](stem + '.service')
    while value.get('SubState') != 'exited' and not driver['stopped'](value):
        require(time.monotonic() < deadline)
        time.sleep(1); value = driver['metadata'](stem + '.service')
    require(value.get('User') == 'root' and value.get('ExecMainStatus') == '0' and value.get('Result') == 'success'
            and value.get('InvocationID') == result.get('invocation_id'))
    subprocess.run(['/usr/bin/systemctl', 'stop', stem + '.service'], stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=True, timeout=20)
    require(driver['stopped'](driver['metadata'](stem + '.service')))
    result['probe_unit_stopped'] = True
    write(finished, canonical(result))
    return result


def proven_capability_fix(baseline, ambient):
    return (baseline.get('complete') is False and baseline.get('failure_phase') == 'restricted_child_spawn'
        and baseline.get('error_kind') == 'PermissionError' and baseline.get('errno') == 1
        and baseline.get('parent_capabilities', {}).get('identity_switch_effective') is False
        and ambient.get('complete') is True and ambient.get('child_started') is True
        and ambient.get('child_identity_restricted') is True
        and all(ambient.get('parent_capabilities', {}).get(key) is True for key in
            ('identity_switch_effective', 'identity_switch_permitted', 'bounding_only_identity_switch', 'no_new_privileges')))


def repaired_driver(old):
    old.update(STATE=STATE, UNIT=UNIT, __file__=str(STATE / 'install_launch_fleet_backups.py'),
        _verified_source_bytes=globals().get('_verified_source_bytes', Path(__file__).read_bytes()))
    previous = old['unit_text']
    def unit_text(rows):
        service, timer = previous(rows)
        require(service.count(b'AmbientCapabilities=\n') == 1)
        return service.replace(b'AmbientCapabilities=\n', b'AmbientCapabilities=CAP_SETUID CAP_SETGID\n'), timer
    old['unit_text'] = unit_text
    original_components = old['components']
    def components():
        driver, read, write = original_components()
        driver['subprocess'] = OwnerSubprocess()
        original_definitions = driver['definitions']
        def definitions(path, digest):
            scope = original_definitions(path, digest)
            if path.name == 'backup_launch_candidate_profile.py': scope['subprocess'] = OwnerSubprocess()
            return scope
        driver['definitions'] = definitions
        return driver, read, write
    old['components'] = components
    return old


def disable_failed_schedule(old, driver, write, rows):
    protected = driver['definitions'](old['PACKAGE'] / 'renew_fleet_credentials.py', driver['DRIVER_SHA'])['protected']
    # Preserve exact original unit files. Only systemd's enablement link is
    # retired; no unit, generation, failed receipt or blocking marker is removed.
    for suffix, expected in zip(('.service', '.timer'), old['unit_text'](rows)):
        path = UNIT_DIRECTORY / (old['UNIT'] + suffix)
        protected(path)
        raw = path.read_bytes(); require(raw == expected)
        saved = DIAGNOSTIC / ('original' + suffix)
        if not os.path.lexists(saved): write(saved, raw)
        else: require(saved.read_bytes() == raw)
    subprocess.run(['/usr/bin/systemctl', 'disable', '--now', old['UNIT'] + '.timer'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
    timer = old['timer_properties']()
    require(timer.get('ActiveState') in {'inactive', 'failed'} and timer.get('UnitFileState') == 'disabled')


def repair():
    old = old_driver(); driver, read, write = old['components']()
    if os.path.lexists(STATE / 'installation.started.json'):
        return repaired_driver(old)['watch'](driver, read, write)
    retained_failure(old, driver, read)
    rows = old['membership'](driver, read)
    if not os.path.lexists(DIAGNOSTIC):
        DIAGNOSTIC.mkdir(mode=0o700)
        write(DIAGNOSTIC / 'repair_launch_fleet_backup.py', globals()['_verified_source_bytes'])
    else:
        require(hashlib.sha256(read(DIAGNOSTIC / 'repair_launch_fleet_backup.py', 0)).hexdigest()
            == hashlib.sha256(globals()['_verified_source_bytes']).hexdigest())
    baseline = run_probe('baseline', old, driver, read, write, rows)
    missing = (baseline.get('complete') is False and baseline.get('failure_phase') == 'restricted_child_spawn'
        and baseline.get('error_kind') == 'PermissionError' and baseline.get('errno') == 1
        and baseline.get('parent_capabilities', {}).get('identity_switch_effective') is False)
    ambient = run_probe('ambient', old, driver, read, write, rows) if missing else {}
    if not proven_capability_fix(baseline, ambient):
        result = dict(complete=False, category='backup_permission_diagnosed_no_automatic_repair',
            baseline=baseline, ambient=ambient, previous_failure_preserved=True, profile_contents_read=False,
            backups_created=0, services_installed=False, fleet_launch_approved=False)
        print(json.dumps(result), flush=True); return 1
    # A newly proven root-only identity switch is the sole repair admitted here.
    # The failed package, blocked marker, units and every old generation stay.
    disable_failed_schedule(old, driver, write, rows)
    print('{"event":"root_identity_switch_repair_qualified","owner_capabilities_zero":true}', flush=True)
    return repaired_driver(old)['install']()


if __name__ == '__main__':
    os.umask(0o077); resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        require(len(sys.argv) in {2, 3})
        if sys.argv[1:] == ['--worker']: raise SystemExit(repaired_driver(old_driver())['worker']())
        require(len(sys.argv) == 3 and sys.argv[1] == '--probe')
        raise SystemExit(probe_worker(sys.argv[2]))
    except KeyboardInterrupt:
        print('{"detached":true,"evidence_preserved":true}', flush=True)
    except Exception:
        print('{"complete":false,"category":"backup_permission_repair_refused_no_secret_output"}', flush=True)
        raise SystemExit(1)
