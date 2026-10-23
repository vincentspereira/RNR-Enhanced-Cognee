"""Read-only, allowlisted diagnostics for the first installed profile backup job.

Never execute/restart the runner, change units/timer state, or open credentials.
Only fixed public program/unit bytes and bounded journal/status data are read.
Raw log messages, traceback text and arbitrary values never leave this helper.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

SERVICE = 'enhanced-cognee-profile-backup.service'
TIMER = 'enhanced-cognee-profile-backup.timer'
RUNNER = Path('/opt/enhanced-cognee-profile-backup/57b8a79716f67331/run.py')
EXPECTED = {
    RUNNER: ('runner', 175004, '57b8a79716f67331fe093dd8d698f0feda6b480cf1131c60c86d92303a780a86'),
    Path('/etc/systemd/system') / SERVICE: ('service', 913, 'a83b1f5ff166b4a1de8e40065305e523d8a01185982b6d228cfbe8a72fdf219c'),
    Path('/etc/systemd/system') / TIMER: ('timer', 213, 'e4647f8177721961d5419d29a785bab5a74dc097a70273768bfceba9fa365b94'),
}
PHASES = {'operator_preflight', 'restricted_snapshot', 'encrypted_snapshot', 'published_ciphertext_authentication'}
CHILD_PHASES = {'identity', 'provider', 'profile_lock', 'source_snapshot', 'source_contract',
    'archive_decode', 'source_comparison', 'restore_write', 'restore_verify',
    'restored_settings', 'restored_api_status', 'source_recheck'}
CATEGORIES = {'permission_denied', 'entry_missing', 'path_type_refused', 'parse_failed',
    'protected_guard_refused', 'unexpected_check_failure', 'protected_provider_mismatch',
    'required_source_file_missing', 'required_source_file_permissions', 'required_provider_link_missing',
    'live_source_changed_since_snapshot', 'live_source_changed_during_restore',
    'restore_destination_not_empty', 'recovery_directory_protection', 'restored_owner_mismatch',
    'restored_file_mismatch', 'restored_directory_mismatch', 'restored_provider_link_mismatch',
    'restored_provider_settings_mismatch', 'restored_credential_assignment',
    'restored_scoped_access_not_accepted', 'restored_membership_mismatch'}
CHECKS = {'archive_validated', 'archive_matches_live_source', 'recovered_files_verified',
    'recovered_settings_verified', 'recovered_api_status_passed'}
STATES = {'active', 'inactive', 'failed', 'activating', 'deactivating', 'maintenance', 'reloading'}
RESULTS = {'success', 'exit-code', 'signal', 'core-dump', 'timeout', 'resources', 'start-limit-hit', 'oom-kill', 'protocol'}


class InspectionError(RuntimeError):
    """No raw error details are returned."""


def command(arguments, limit=524288):
    # -n on journalctl bounds the selected entries; size caps reject oversized
    # records. No shell, proxy/environment inheritance, journal file or log copy.
    result = subprocess.run(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=20, close_fds=True)
    if result.returncode or len(result.stdout) > limit or len(result.stderr) > 4096:
        raise InspectionError('bounded_read_failed')
    return result.stdout


def public_file(path, size, expected):
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            opened = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = opened
            info = os.fstat(fd)
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise InspectionError('public_path_changed')
        opened = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(opened)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                    or info.st_mode & 0o022 or info.st_size != size): return False
            raw = os.read(opened, size + 1)
            after = os.fstat(opened)
            stamp = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_nlink,
                                   value.st_size, value.st_mtime_ns, value.st_ctime_ns)
            return stamp(info) == stamp(after) and len(raw) == size and hashlib.sha256(raw).hexdigest() == expected
        finally: os.close(opened)
    finally: os.close(fd)


def safe_report(value):
    if (not isinstance(value, dict) or value.get('stage') != 'profile_backup_only'
            or type(value.get('complete')) is not bool): return None
    report = {'complete': value['complete'], 'stage': 'profile_backup_only'}
    if not value['complete']:
        phase = value.get('failure_stage')
        if phase not in PHASES: return None
        if value.get('category') != 'profile_backup_or_restore_incomplete_preserve_evidence': return None
        report['failure_stage'] = phase
        if type(value.get('encrypted_backup_created')) is bool:
            report['encrypted_backup_created'] = value['encrypted_backup_created']
        child = value.get('restricted_diagnostics')
        if isinstance(child, dict) and child.get('complete') is False:
            if (isinstance(child.get('phase'), str) and child['phase'] in CHILD_PHASES
                    and isinstance(child.get('category'), str) and child['category'] in CATEGORIES):
                report['restricted_phase'] = child['phase']
                report['restricted_category'] = child['category']
                checks = child.get('checks')
                if isinstance(checks, dict):
                    report['checks'] = {key: checks[key] for key in CHECKS
                                       if key in checks and (checks[key] is None or type(checks[key]) is bool)}
    else:
        for key in ('source_files', 'source_bytes'):
            if type(value.get(key)) is int and 0 <= value[key] <= 16777216: report[key] = value[key]
        for key in ('signed_ciphertext_verified', 'decryption_tested', 'recovery_identity_read'):
            if type(value.get(key)) is bool: report[key] = value[key]
    return report


def journal_report(raw, invocation):
    if not re.fullmatch(r'[0-9a-f]{32}', invocation) or len(raw) > 524288:
        raise InspectionError('journal_budget_or_invocation')
    messages = []
    lines = raw.splitlines()
    if len(lines) > 160: raise InspectionError('journal_entry_budget')
    for line in lines:
        value = json.loads(line)
        if (not isinstance(value, dict) or value.get('_SYSTEMD_UNIT') != SERVICE
                or value.get('_SYSTEMD_INVOCATION_ID') != invocation): continue
        message = value.get('MESSAGE')
        if isinstance(message, str) and len(message) <= 65536:
            messages.append(message)
    # journald may preserve a multi-line MESSAGE or split stdout at newlines.
    text = '\n'.join(messages)
    decoder = json.JSONDecoder()
    found = None
    attempts = 0
    for index, char in enumerate(text):
        if char != '{': continue
        attempts += 1
        if attempts > 256: raise InspectionError('journal_parse_budget')
        try: candidate, _ = decoder.raw_decode(text[index:])
        except ValueError: continue
        cleaned = safe_report(candidate)
        if cleaned is not None: found = cleaned
    return found


def main():
    phase = 'operator_preflight'
    try:
        if (os.geteuid() != 0 or os.environ.get('WSL_DISTRO_NAME') != 'Ubuntu-Hermes'
                or os.environ.get('SUDO_USER') != 'vincentspereira'):
            raise InspectionError('approved_human_operator_required')
        if Path('/proc/1/comm').read_text().strip() != 'systemd':
            raise InspectionError('host_systemd_required')
        phase = 'public_artifact_verification'
        hashes = {label + '_matches_published': public_file(path, size, expected)
                  for path, (label, size, expected) in EXPECTED.items()}
        phase = 'service_state'
        raw = command(['/usr/bin/systemctl', 'show', SERVICE, '--property=InvocationID',
            '--property=Result', '--property=ExecMainStatus', '--property=ActiveState'], limit=4096)
        fields = dict(line.split('=', 1) for line in raw.decode('ascii').splitlines() if '=' in line)
        state = {key: value for key, value in fields.items()
                 if key == 'Result' and value in RESULTS or key == 'ActiveState' and value in STATES
                 or key == 'ExecMainStatus' and re.fullmatch(r'[0-9]{1,3}', value)}
        policy = command(['/usr/bin/systemctl', 'show', SERVICE, '--property=NoNewPrivileges',
            '--property=PrivateNetwork', '--property=ProtectHome', '--property=ProtectSystem',
            '--property=CapabilityBoundingSet', '--property=DropInPaths'], limit=4096)
        policy = dict(line.split('=', 1) for line in policy.decode('ascii').splitlines() if '=' in line)
        effective = {key: policy.get(key) == expected for key, expected in (
            ('NoNewPrivileges', 'yes'), ('PrivateNetwork', 'yes'), ('ProtectHome', 'yes'), ('ProtectSystem', 'strict'))}
        effective['only_identity_switch_capabilities'] = set(policy.get('CapabilityBoundingSet', '').split()) == {'cap_setuid', 'cap_setgid'}
        effective['no_service_drop_ins'] = policy.get('DropInPaths') == ''
        invocation = fields.get('InvocationID', '')
        if not re.fullmatch(r'[0-9a-f]{32}', invocation) or invocation == '0' * 32:
            raise InspectionError('no_retained_service_invocation')
        phase = 'retained_journal_inspection'
        raw = command(['/usr/bin/journalctl', '--no-pager', '--output=json', '--lines=160',
            '_SYSTEMD_UNIT=' + SERVICE, '_SYSTEMD_INVOCATION_ID=' + invocation])
        report = journal_report(raw, invocation)
        timer = command(['/usr/bin/systemctl', 'show', TIMER,
            '--property=ActiveState', '--property=UnitFileState'], limit=4096)
        timer = dict(line.split('=', 1) for line in timer.decode('ascii').splitlines() if '=' in line)
        print(json.dumps({'complete': True, 'stage': 'profile_backup_schedule_inspection',
            'published_artifacts': hashes, 'service_state': state, 'effective_policy': effective,
            'retained_backup_report_found': report is not None, 'retained_backup_report': report,
            'timer_active': timer.get('ActiveState') == 'active',
            'timer_enabled': timer.get('UnitFileState') in {'enabled', 'enabled-runtime'},
            'files_written': False, 'service_started_or_restarted': False, 'timer_changed': False,
            'credentials_read': False, 'model_called': False, 'memory_records_written': False,
            'runtime_qualified': False}, indent=2))
    except Exception:
        print(json.dumps({'complete': False, 'stage': 'profile_backup_schedule_inspection',
            'failure_stage': phase, 'category': 'retained_schedule_inspection_incomplete',
            'files_written': False, 'service_started_or_restarted': False, 'timer_changed': False,
            'credentials_read': False, 'model_called': False, 'runtime_qualified': False}, indent=2))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
