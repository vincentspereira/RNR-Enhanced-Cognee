"""Bounded temporary systemd probe of the published restricted snapshot launcher.

The original service/timer/runner are never changed or rerun. A collected
transient unit tests retaining CAP_SETUID in the root parent's ambient set,
then clearing ambient/inheritable capabilities before the restricted child.
Other selected protections remain, with no persistent write path.
An ordinary profile snapshot is discarded in RAM. No service secrets are read.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import uuid

RUNNER = Path('/opt/enhanced-cognee-profile-backup/57b8a79716f67331/run.py')
RUNNER_HASH = '57b8a79716f67331fe093dd8d698f0feda6b480cf1131c60c86d92303a780a86'
BASE = 'integrations/hermes/deployment/'
HASHES = {
    BASE + 'backup_pilot_profile.py': '6e8baaef8a56b67aee49789b665e913ba110339a7736a25b2df2a7abf428363a',
    BASE + 'inspect_pilot_recovery.py': '83eb9f2caafdc8fc8a79edf5643fa67b87b475bc98a69f37845d01a54cf59009',
    BASE + 'provision_pilot_access.py': 'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6',
}
PROPERTIES = [
    'User=root', 'Group=root', 'UMask=0077', 'NoNewPrivileges=yes', 'PrivateTmp=yes',
    'PrivateDevices=yes', 'PrivateNetwork=yes', 'ProtectHome=yes', 'ProtectSystem=strict',
    'ReadOnlyPaths=/var/lib/hermes-runtime',
    'InaccessiblePaths=-/etc/enhanced-cognee/age-recovery-identity.txt -/etc/enhanced-cognee/operator.json -/etc/enhanced-cognee/api.json -/etc/enhanced-cognee/worker.json',
    'ProtectKernelTunables=yes', 'ProtectKernelModules=yes', 'ProtectControlGroups=yes',
    'RestrictSUIDSGID=yes', 'RestrictNamespaces=yes', 'RestrictAddressFamilies=AF_UNIX',
    'CapabilityBoundingSet=CAP_SETUID CAP_SETGID', 'AmbientCapabilities=CAP_SETUID',
    'MemoryMax=512M', 'CPUQuota=100%', 'TasksMax=32', 'RuntimeMaxSec=120s', 'WorkingDirectory=/tmp',
]
EXCEPTIONS = {'PermissionError', 'FileNotFoundError', 'OSError', 'TimeoutExpired', 'ValueError',
              'RuntimeError', 'ImportError', 'ModuleNotFoundError', 'SyntaxError', 'TypeError', 'BackupError'}
FLAGS = {'launch_attempted', 'launch_returned', 'stderr_present', 'snapshot_completed',
         'parent_setuid_capability', 'parent_setgid_capability', 'parent_no_new_privileges',
         'launch_error_has_filename', 'error_after_timeout_window', 'process_created'}
COUNTS = {'child_exit_status', 'popen_errno', 'stderr_errno'}
FIELDS = FLAGS | COUNTS | {'exception_type', 'stderr_exception_type', 'failure_category', 'child_phase', 'child_category', 'setpriv_failure_stage'}
SWITCH_STAGES = {'setgroups', 'setresgid', 'setresuid', 'setregid', 'setreuid', 'execute', None}
CATEGORIES = {'launch_exception', 'child_program_budget', 'restricted_child_refused', 'unexpected_snapshot_failure', None}
CHILD_PHASES = {'identity', 'provider', 'profile_lock', 'source_snapshot', 'source_contract',
    'archive_decode', 'source_comparison', 'restore_write', 'restore_verify', 'restored_settings', 'restored_api_status', 'source_recheck'}
CHILD_CATEGORIES = {'permission_denied', 'entry_missing', 'path_type_refused', 'parse_failed',
    'protected_guard_refused', 'unexpected_check_failure', 'protected_provider_mismatch',
    'required_source_file_missing', 'required_source_file_permissions', 'required_provider_link_missing',
    'live_source_changed_since_snapshot', 'live_source_changed_during_restore', 'restore_destination_not_empty',
    'recovery_directory_protection', 'restored_owner_mismatch', 'restored_file_mismatch', 'restored_directory_mismatch',
    'restored_provider_link_mismatch', 'restored_provider_settings_mismatch', 'restored_credential_assignment',
    'restored_scoped_access_not_accepted', 'restored_membership_mismatch'}


class ProbeError(RuntimeError):
    """Fixed public category only."""


def read_runner():
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for part in RUNNER.parts[1:-1]:
            opened = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = opened
            info = os.fstat(fd)
            if info.st_uid != 0 or info.st_mode & 0o022: raise ProbeError('protected_runner_path')
        opened = os.open(RUNNER.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(opened)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_nlink != 1
                    or before.st_mode & 0o022 or before.st_size != 175004): raise ProbeError('protected_runner_metadata')
            with os.fdopen(opened, 'rb', closefd=False) as handle: raw = handle.read(175005)
            after = os.fstat(opened)
            stamp = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_uid,
                                   value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
            if stamp(before) != stamp(after): raise ProbeError('protected_runner_changed')
        finally: os.close(opened)
    finally: os.close(fd)
    return raw


def verified_sources(raw):
    if not isinstance(raw, bytes) or len(raw) != 175004 or hashlib.sha256(raw).hexdigest() != RUNNER_HASH:
        raise ProbeError('published_runner_mismatch')
    tree = ast.parse(raw)
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'sources']
    if len(values) != 1: raise ProbeError('published_source_table')
    sources = ast.literal_eval(values[0])
    if not isinstance(sources, dict) or set(sources) != set(HASHES): raise ProbeError('published_source_table')
    for name, expected in HASHES.items():
        value = sources[name]
        if not isinstance(value, bytes) or len(value) > 65536 or hashlib.sha256(value).hexdigest() != expected:
            raise ProbeError('published_source_mismatch')
    return sources


# Public instrumentation only. All stdout/stderr from the snapshot child stays
# in its root parent and is discarded. Only these bounded scalar fields return.
INSTRUMENT = r'''
import json, pwd, re, subprocess, time
from types import SimpleNamespace
stats = dict(launch_attempted=False, launch_returned=False, stderr_present=False,
    snapshot_completed=False, child_exit_status=None, popen_errno=None,
    stderr_errno=None, exception_type=None, stderr_exception_type=None, failure_category=None, child_phase=None, child_category=None, setpriv_failure_stage=None,
    parent_setuid_capability=False, parent_setgid_capability=False, parent_no_new_privileges=False,
    launch_error_has_filename=False, error_after_timeout_window=False, process_created=False)
with open('/proc/self/status') as handle:
    process_fields = dict(line.split(':', 1) for line in handle.read().splitlines())
effective = int(process_fields.get('CapEff', '0').strip(), 16)
stats['parent_setuid_capability'] = bool(effective & (1 << 7))
stats['parent_setgid_capability'] = bool(effective & (1 << 6))
stats['parent_no_new_privileges'] = process_fields.get('NoNewPrivs', '').strip() == '1'
original_run = subprocess.run
allowed_errors = {'PermissionError','FileNotFoundError','OSError','TimeoutExpired','ValueError',
    'RuntimeError','ImportError','ModuleNotFoundError','SyntaxError','TypeError','BackupError'}
def observed(argv, **kwargs):
    stats['launch_attempted'] = True
    uid, gid, groups = kwargs.pop('user'), kwargs.pop('group'), kwargs.pop('extra_groups')
    if type(uid) is not int or uid <= 0 or type(gid) is not int or gid <= 0 or groups != ():
        raise RuntimeError('restricted_identity_required')
    argv = ['/usr/bin/setpriv', '--reuid=' + str(uid), '--regid=' + str(gid),
            '--clear-groups', '--ambient-caps=-all', '--inh-caps=-all', '--no-new-privs', '--', *argv]
    original_popen = subprocess.Popen
    def tracked_popen(*args, **options):
        process = original_popen(*args, **options)
        stats['process_created'] = True
        return process
    subprocess.Popen = tracked_popen
    started = time.monotonic()
    try:
        result = original_run(argv, **kwargs)
    except Exception as error:
        timeout = kwargs.get('timeout')
        stats['error_after_timeout_window'] = (type(timeout) in (int, float) and timeout > 0
            and time.monotonic() - started >= timeout)
        stats['launch_error_has_filename'] = getattr(error, 'filename', None) is not None
        stats['exception_type'] = type(error).__name__ if type(error).__name__ in allowed_errors else None
        number = getattr(error, 'errno', None)
        stats['popen_errno'] = number if type(number) is int and 0 < number < 4096 else None
        stats['failure_category'] = 'launch_exception'
        raise
    finally:
        subprocess.Popen = original_popen
    stats['launch_returned'] = True
    stats['child_exit_status'] = result.returncode if type(result.returncode) is int and -255 <= result.returncode <= 255 else None
    stats['stderr_present'] = bool(result.stderr)
    if len(result.stderr) <= 4096:
        text = result.stderr.decode('utf-8', errors='replace')
        if text.startswith('setpriv:'):
            for operation in ('setgroups', 'setresgid', 'setresuid', 'setregid', 'setreuid'):
                if operation in text: stats['setpriv_failure_stage'] = operation
            if 'failed to execute' in text: stats['setpriv_failure_stage'] = 'execute'
        try: child = json.loads(text)
        except ValueError: child = None
        if (isinstance(child, dict) and child.get('complete') is False
                and isinstance(child.get('phase'), str) and child['phase'] in backup.get('CHILD_PHASES', set())
                and isinstance(child.get('category'), str) and child['category'] in backup.get('CHILD_CATEGORIES', set())):
            stats['child_phase'], stats['child_category'] = child['phase'], child['category']
        for line in text.splitlines():
            match = re.match(r'^([A-Za-z]+Error):', line)
            if match and match[1] in allowed_errors: stats['stderr_exception_type'] = match[1]
            number = re.search(r'\[Errno ([0-9]{1,4})\]', line)
            if number and 0 < int(number[1]) < 4096: stats['stderr_errno'] = int(number[1])
    return result
backup['subprocess'] = SimpleNamespace(run=observed, PIPE=subprocess.PIPE)
try:
    account = pwd.getpwnam('hermes-runtime')
    if account.pw_uid == 0 or account.pw_dir != '/var/lib/hermes-runtime':
        raise RuntimeError('restricted_account_required')
    payload, receipt = backup['run_child'](core, inspector, sources, account, 'snapshot')
    stats['snapshot_completed'] = True
    del payload, receipt
except Exception as error:
    if stats['failure_category'] is None:
        stats['failure_category'] = ('child_program_budget' if isinstance(error, backup['BackupError'])
            and str(error) == 'child_program_budget' else 'restricted_child_refused' if isinstance(error, backup['BackupError'])
            else 'unexpected_snapshot_failure')
    if stats['exception_type'] is None:
        stats['exception_type'] = type(error).__name__ if type(error).__name__ in allowed_errors else None
print(json.dumps(stats, sort_keys=True))
'''


def program(sources):
    code = 'sources=' + repr(sources) + '\n'
    for variable, name in (('core', 'provision_pilot_access.py'), ('inspector', 'inspect_pilot_recovery.py'), ('backup', 'backup_pilot_profile.py')):
        code += variable + "={'__name__':'verified_probe_definitions'}\nexec(compile(sources[" + repr(BASE + name) + "],'verified-public-source','exec')," + variable + ')\n'
    code += INSTRUMENT
    if len(code.encode()) > 120000: raise ProbeError('probe_program_budget')
    compile(code, '<public-snapshot-probe>', 'exec')
    return code


def safe_result(raw):
    if len(raw) > 4096: return None
    try: value = json.loads(raw)
    except ValueError: return None
    if not isinstance(value, dict) or set(value) != FIELDS: return None
    if any(type(value[key]) is not bool for key in FLAGS): return None
    if any(value[key] is not None and (type(value[key]) is not int or not -255 <= value[key] <= 4095) for key in COUNTS): return None
    for key in ('exception_type', 'stderr_exception_type'):
        if value[key] is not None and (not isinstance(value[key], str) or value[key] not in EXCEPTIONS): return None
    if value['failure_category'] is not None and (not isinstance(value['failure_category'], str) or value['failure_category'] not in CATEGORIES): return None
    for key, allowed in (('child_phase', CHILD_PHASES), ('child_category', CHILD_CATEGORIES)):
        if value[key] is not None and (not isinstance(value[key], str) or value[key] not in allowed): return None
    if value['setpriv_failure_stage'] is not None and (not isinstance(value['setpriv_failure_stage'], str) or value['setpriv_failure_stage'] not in SWITCH_STAGES): return None
    return value


def main():
    phase = 'operator_preflight'
    try:
        if (os.geteuid() != 0 or os.environ.get('WSL_DISTRO_NAME') != 'Ubuntu-Hermes'
                or os.environ.get('SUDO_USER') != 'vincentspereira'
                or Path('/proc/1/comm').read_text().strip() != 'systemd'):
            raise ProbeError('approved_host_operator_required')
        phase = 'published_runner_verification'
        sources = verified_sources(read_runner())
        phase = 'bounded_transient_probe'
        unit = 'enhanced-cognee-profile-probe-' + uuid.uuid4().hex[:12]
        arguments = ['/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--collect', '--expand-environment=no', '--unit=' + unit]
        for value in PROPERTIES: arguments.append('--property=' + value)
        arguments += ['/usr/bin/python3', '-I', '-B', '-c', program(sources)]
        result = subprocess.run(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, close_fds=True, timeout=135)
        report = safe_result(result.stdout)
        print(json.dumps({'complete': report is not None, 'stage': 'profile_snapshot_launch_probe',
            'identity_launcher': 'setpriv_clear_groups',
            'candidate_parent_ambient_setuid_requested': True,
            'child_capability_clear_requested': True,
            'probe_report_found': report is not None, 'launch_diagnostics': report,
            'transient_command_exit_status': result.returncode if -255 <= result.returncode <= 255 else None,
            'installed_job_rerun': False, 'installed_units_changed': False, 'timer_changed': False,
            'backup_created': False, 'service_signing_or_recovery_keys_read': False,
            'ordinary_snapshot_discarded_in_memory': bool(report and report['snapshot_completed']),
            'model_called': False, 'memory_records_written': False, 'runtime_qualified': False}, indent=2))
        if report is None: raise SystemExit(1)
    except Exception:
        print(json.dumps({'complete': False, 'stage': 'profile_snapshot_launch_probe', 'failure_stage': phase,
            'category': 'snapshot_probe_incomplete_private_output_suppressed', 'installed_job_rerun': False,
            'installed_units_changed': False, 'timer_changed': False, 'backup_created': False,
            'model_called': False, 'runtime_qualified': False}, indent=2))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
