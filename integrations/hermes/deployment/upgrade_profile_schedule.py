"""One human-operated upgrade of the exact failed daily profile backup job.

Only fixed hash-verified public definitions execute as root. Preserve old units,
runner, generations and failures; never automatically retry or roll back.
"""
from __future__ import annotations

import fcntl
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import uuid

BASE = 'integrations/hermes/deployment/'
HASHES = {
    BASE + 'provision_pilot_access.py': 'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6',
    BASE + 'inspect_pilot_recovery.py': '83eb9f2caafdc8fc8a79edf5643fa67b87b475bc98a69f37845d01a54cf59009',
    BASE + 'backup_pilot_profile.py': 'c9f96685c32b3fc76249465137282135f0f68fb347f938bc18e71b1ff48044b4',
}
ROOT = Path('/opt/enhanced-cognee-profile-backup')
UNITS = Path('/etc/systemd/system')
SERVICE = 'enhanced-cognee-profile-backup.service'
TIMER = 'enhanced-cognee-profile-backup.timer'
OLD_RUNNER = ROOT / '57b8a79716f67331/run.py'
OLD = {
    OLD_RUNNER: (175004, '57b8a79716f67331fe093dd8d698f0feda6b480cf1131c60c86d92303a780a86'),
    UNITS / SERVICE: (913, 'a83b1f5ff166b4a1de8e40065305e523d8a01185982b6d228cfbe8a72fdf219c'),
    UNITS / TIMER: (213, 'e4647f8177721961d5419d29a785bab5a74dc097a70273768bfceba9fa365b94'),
}


class UpgradeError(RuntimeError):
    """Fixed public categories; private subprocess errors stay private."""


def definitions(sources):
    if not isinstance(sources, dict) or set(sources) != set(HASHES):
        raise UpgradeError('published_sources_mismatch')
    result = []
    for name in ('provision_pilot_access.py', 'inspect_pilot_recovery.py', 'backup_pilot_profile.py'):
        raw = sources[BASE + name]
        if not isinstance(raw, bytes) or len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != HASHES[BASE + name]:
            raise UpgradeError('published_sources_mismatch')
        namespace = {'__name__': 'verified_upgrade_definitions'}
        exec(compile(raw, '<verified-public-source>', 'exec'), namespace)
        result.append(namespace)
    return result


def read_at(directory, name, *, limit=262144):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_nlink != 1
                or before.st_mode & 0o022 or before.st_size > limit):
            raise UpgradeError('protected_public_file_required')
        with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(limit + 1)
        after = os.fstat(fd)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or stamp(before) != stamp(after):
            raise UpgradeError('public_file_changed')
        return raw
    finally: os.close(fd)


def public_file(core, path):
    directory = core['open_directory'](path.parent, {0})
    try: return read_at(directory, path.name)
    finally: os.close(directory)


def write_new(directory, name, raw, *, mode=0o644):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=directory)
    with os.fdopen(fd, 'wb') as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(directory)


def fields(command, name, keys):
    raw = command(['/usr/bin/systemctl', 'show', name, '--all', *('--property=' + key for key in keys)])
    value = dict(line.split('=', 1) for line in raw.decode('ascii').splitlines() if '=' in line)
    if set(value) != set(keys): raise UpgradeError('unit_state_incomplete')
    return value


def idle_original(command):
    for name in (SERVICE, TIMER):
        value = fields(command, name, ('FragmentPath', 'DropInPaths', 'ActiveState', 'UnitFileState', 'Job'))
        if (value['FragmentPath'] != str(UNITS / name) or value['DropInPaths'] or value['Job']
                or value['ActiveState'] not in ({'inactive', 'failed'} if name == SERVICE else {'inactive'})
                or value['UnitFileState'] != ('static' if name == SERVICE else 'disabled')):
            raise UpgradeError('existing_schedule_needs_review')


def completed_report(raw, invocation):
    if len(raw) > 65536: raise UpgradeError('journal_budget')
    lines, messages = raw.decode('utf-8').splitlines(), []
    if len(lines) > 160: raise UpgradeError('journal_budget')
    for line in lines:
        item = json.loads(line)
        if (isinstance(item, dict) and item.get('_SYSTEMD_UNIT') == SERVICE
                and item.get('_SYSTEMD_INVOCATION_ID') == invocation and isinstance(item.get('MESSAGE'), str)):
            messages.append(item['MESSAGE'])
    text, decoder, found, attempts = '\n'.join(messages), json.JSONDecoder(), [], 0
    for index, char in enumerate(text):
        if char != '{': continue
        attempts += 1
        if attempts > 256: raise UpgradeError('journal_budget')
        try: value, _ = decoder.raw_decode(text[index:])
        except ValueError: continue
        if not isinstance(value, dict) or value.get('stage') != 'profile_backup_only': continue
        if (value.get('complete') is not True or value.get('signed_ciphertext_verified') is not True
                or any(value.get(key) is not False for key in ('decryption_tested', 'recovery_identity_read',
                    'plaintext_archive_written', 'model_called', 'memory_records_written'))
                or type(value.get('source_files')) is not int or not 1 <= value['source_files'] <= 2048
                or type(value.get('source_bytes')) is not int or not 1 <= value['source_bytes'] <= 16777216
                or not isinstance(value.get('encrypted_backup'), str)
                or not re.fullmatch(r'/var/backups/enhanced-cognee/hermes_profile_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}\.tar\.age', value['encrypted_backup'])):
            raise UpgradeError('completed_backup_report_required')
        found.append(value)
    if len(found) != 1: raise UpgradeError('unique_completed_backup_report_required')
    return found[0]


def qualify(command):
    previous = fields(command, SERVICE, ('InvocationID',))['InvocationID']
    command(['/usr/bin/systemctl', 'start', SERVICE])
    value = fields(command, SERVICE, ('Result', 'ExecMainStatus', 'ActiveState', 'InvocationID'))
    if (value['Result'] != 'success' or value['ExecMainStatus'] != '0' or value['ActiveState'] != 'inactive'
            or not re.fullmatch('[0-9a-f]{32}', value['InvocationID'])
            or value['InvocationID'] in {previous, '0' * 32}):
        raise UpgradeError('service_not_successful')
    raw = command(['/usr/bin/journalctl', '--no-pager', '--output=json', '--lines=160',
        '_SYSTEMD_UNIT=' + SERVICE, '_SYSTEMD_INVOCATION_ID=' + value['InvocationID']])
    return completed_report(raw, value['InvocationID'])


def authenticate(core, backup, report):
    directory = core['open_directory'](Path('/etc/enhanced-cognee'), {0})
    try: config = json.loads(core['read_private_at'](directory, 'backup.json', 0)[0])
    finally: os.close(directory)
    key, key_id = config['ENHANCED_BACKUP_SIGNING_KEY'], config['ENHANCED_BACKUP_SIGNING_KEY_ID']
    if not isinstance(key, str) or len(key.encode()) < 32 or not isinstance(key_id, str):
        raise UpgradeError('backup_signing_configuration_needs_review')
    directory = core['open_directory'](backup['DESTINATION'], {0})
    try:
        if stat.S_IMODE(os.fstat(directory).st_mode) != 0o700: raise UpgradeError('backup_directory_protection')
        name = Path(report['encrypted_backup']).name
        backup['verify_completed'](core, directory, name, key.encode(), key_id)
        manifest = json.loads(core['read_private_at'](directory, name + '.json', 0)[0])
        if any(manifest.get(k) != report[k] for k in ('source_files', 'source_bytes')):
            raise UpgradeError('backup_counts_mismatch')
    finally: os.close(directory)


def main(sources):
    phase, published, enabled, preservation = 'operator_preflight', False, False, None
    try:
        if (os.geteuid() != 0 or os.environ.get('WSL_DISTRO_NAME') != 'Ubuntu-Hermes'
                or os.environ.get('SUDO_USER') != 'vincentspereira'
                or Path('/proc/1/comm').read_text().strip() != 'systemd'):
            raise UpgradeError('approved_host_operator_required')
        core, inspector, backup = definitions(sources)
        command = backup['schedule_command']
        phase = 'exact_existing_schedule_review'
        old = {path: public_file(core, path) for path in OLD}
        if any(len(raw) != OLD[path][0] or hashlib.sha256(raw).hexdigest() != OLD[path][1] for path, raw in old.items()):
            raise UpgradeError('exact_old_artifacts_required')
        idle_original(command)
        runner, program, service, timer = backup['schedule_payloads'](sources)
        if runner.parent.parent != ROOT or timer != old[UNITS / TIMER]: raise UpgradeError('candidate_scope_mismatch')
        root = core['open_directory'](ROOT, {0})
        try:
            lock = os.open('.schedule-upgrade.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=root)
            try:
                core['read_private_fd'](lock, 0)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Recheck after acquiring the sole operator-update lock.
                idle_original(command)
                phase = 'protected_candidate_preparation'
                os.mkdir(runner.parent.name, 0o755, dir_fd=root)
                edition = core['open_directory'](runner.parent, {0})
                try:
                    for name, raw in (('run.py', program), (SERVICE, service), (TIMER, timer)):
                        write_new(edition, name, raw)
                finally: os.close(edition)
                command(['/usr/bin/systemd-analyze', 'verify', str(runner.parent / SERVICE), str(runner.parent / TIMER)], unit_path=runner.parent)
                phase = 'preserve_and_replace_exact_service'
                preservation = 'before-upgrade-' + uuid.uuid4().hex
                os.mkdir(preservation, 0o700, dir_fd=root)
                kept = core['open_directory'](ROOT / preservation, {0})
                try:
                    for path, raw in old.items(): write_new(kept, 'old-runner.py' if path == OLD_RUNNER else path.name, raw, mode=0o600)
                finally: os.close(kept)
                units = core['open_directory'](UNITS, {0})
                try:
                    idle_original(command)
                    for path, raw in old.items():
                        if public_file(core, path) != raw: raise UpgradeError('original_changed_before_publication')
                    temporary = '.' + SERVICE + '-' + uuid.uuid4().hex
                    write_new(units, temporary, service)
                    # The protected directory and update lock exclude ordinary
                    # agent writers; require the exact original again at commit.
                    if read_at(units, SERVICE) != old[UNITS / SERVICE]: raise UpgradeError('original_changed_before_publication')
                    os.replace(temporary, SERVICE, src_dir_fd=units, dst_dir_fd=units)
                    os.fsync(units)
                    published = True
                finally: os.close(units)
                phase = 'reloaded_candidate_verification'
                command(['/usr/bin/systemctl', 'daemon-reload'])
                idle_original(command)
                policy = fields(command, SERVICE, ('AmbientCapabilities', 'CapabilityBoundingSet', 'NoNewPrivileges', 'PrivateNetwork'))
                if (policy['AmbientCapabilities'].split() != ['cap_setuid']
                        or set(policy['CapabilityBoundingSet'].split()) != {'cap_setuid', 'cap_setgid'}
                        or policy['NoNewPrivileges'] != 'yes' or policy['PrivateNetwork'] != 'yes'):
                    raise UpgradeError('effective_candidate_policy_mismatch')
                phase = 'real_encrypted_backup_qualification'
                report = qualify(command)
                authenticate(core, backup, report)
                if public_file(core, UNITS / SERVICE) != service or public_file(core, UNITS / TIMER) != timer:
                    raise UpgradeError('units_changed_after_qualification')
                phase = 'daily_timer_enable'
                command(['/usr/bin/systemctl', 'enable', '--now', TIMER])
                enabled = True
                if (command(['/usr/bin/systemctl', 'is-enabled', TIMER]).strip() != b'enabled'
                        or command(['/usr/bin/systemctl', 'is-active', TIMER]).strip() != b'active'):
                    raise UpgradeError('daily_timer_not_ready')
                deadline = command(['/usr/bin/systemctl', 'show', TIMER, '--property=NextElapseUSecRealtime', '--value']).strip()
                if not deadline or deadline == b'n/a': raise UpgradeError('daily_timer_has_no_next_run')
                print(json.dumps(dict(complete=True, stage='profile_backup_schedule_upgrade',
                    protected_runner=str(runner), preserved_originals=str(ROOT / preservation),
                    profile_backup_service_passed=True, signed_ciphertext_verified=True,
                    encrypted_backup=report['encrypted_backup'], source_files=report['source_files'], source_bytes=report['source_bytes'],
                    daily_profile_timer_enabled=True, daily_profile_timer_active=True, next_daily_run_scheduled=True,
                    recovery_identity_read=False, plaintext_archive_written=False, previous_generations_preserved=True,
                    existing_database_schedule_changed=False, windows_collection_qualified=False,
                    model_called=False, memory_records_written=False, runtime_qualified=False), indent=2))
            finally: os.close(lock)
        finally: os.close(root)
    except Exception:
        print(json.dumps(dict(complete=False, stage='profile_backup_schedule_upgrade', failure_stage=phase,
            category='upgrade_incomplete_preserve_evidence_do_not_repeat', service_replaced=published,
            timer_enable_command_completed=enabled, preserved_originals=str(ROOT / preservation) if preservation else None,
            existing_database_schedule_changed=False, model_called=False, memory_records_written=False,
            runtime_qualified=False), indent=2))
        raise SystemExit(1) from None


PRESERVED = ROOT / 'before-upgrade-3facdc095f4b49e6ba6c00b000c7e1e7'


def bound_retained_report(raw, runner, publication_ns):
    """Admit only root journal output from this exact runner after publication."""
    if len(raw) > 65536: raise UpgradeError('journal_budget')
    lines = raw.splitlines()
    if len(lines) > 160: raise UpgradeError('journal_budget')
    rows = [json.loads(line) for line in lines]
    latest = None
    for row in rows:
        if not isinstance(row, dict) or row.get('_SYSTEMD_UNIT') != SERVICE: continue
        invocation = row.get('_SYSTEMD_INVOCATION_ID')
        if isinstance(invocation, str) and re.fullmatch('[0-9a-f]{32}', invocation) and invocation != '0' * 32:
            latest = invocation
    if latest is None: raise UpgradeError('retained_invocation_missing')
    selected = []
    for row in rows:
        if not isinstance(row, dict) or row.get('_SYSTEMD_UNIT') != SERVICE or row.get('_SYSTEMD_INVOCATION_ID') != latest: continue
        timestamp = row.get('__REALTIME_TIMESTAMP')
        if (row.get('_UID') != '0' or row.get('_CMDLINE') != '/usr/bin/python3 -I -B ' + str(runner)
                or not isinstance(timestamp, str) or not re.fullmatch('[0-9]{1,20}', timestamp)
                or int(timestamp) * 1000 < publication_ns):
            continue
        selected.append(row)
    if not selected: raise UpgradeError('upgraded_root_runner_journal_binding_missing')
    # MESSAGE text cannot claim identity, command line, timestamp or invocation.
    bound = b'\n'.join(json.dumps(row).encode() for row in selected)
    return completed_report(bound, latest)


def published_snapshot(core, path, expected):
    directory = core['open_directory'](path.parent, {0})
    try:
        before = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if read_at(directory, path.name) != expected: raise UpgradeError('installed_candidate_drift')
        after = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if stamp(before) != stamp(after): raise UpgradeError('installed_candidate_drift')
        return stamp(after), after.st_mtime_ns
    finally: os.close(directory)


def main_resume(sources):
    """Verify retained upgraded output/ciphertext, then enable only its timer.

    Does not start the service, replace files or repeat the successful restore.
    Starting a persistent timer may trigger its normal scheduled catch-up run.
    """
    phase, enabled, binding, authenticated = 'operator_preflight', False, False, False
    try:
        if (os.geteuid() != 0 or os.environ.get('WSL_DISTRO_NAME') != 'Ubuntu-Hermes'
                or os.environ.get('SUDO_USER') != 'vincentspereira'
                or Path('/proc/1/comm').read_text().strip() != 'systemd'):
            raise UpgradeError('approved_host_operator_required')
        core, inspector, backup = definitions(sources)
        command = backup['schedule_command']
        phase = 'verify_installed_and_preserved_artifacts'
        runner, program, service, timer = backup['schedule_payloads'](sources)
        if runner.parent.parent != ROOT: raise UpgradeError('candidate_scope_mismatch')
        snapshots = {path: published_snapshot(core, path, raw) for path, raw in
            ((runner, program), (UNITS / SERVICE, service), (UNITS / TIMER, timer))}
        kept = core['open_directory'](PRESERVED, {0})
        try:
            if stat.S_IMODE(os.fstat(kept).st_mode) != 0o700: raise UpgradeError('preserved_originals_protection')
            for path, (size, expected) in OLD.items():
                name = 'old-runner.py' if path == OLD_RUNNER else path.name
                if stat.S_IMODE(os.stat(name, dir_fd=kept, follow_symlinks=False).st_mode) != 0o600:
                    raise UpgradeError('preserved_originals_protection')
                raw = read_at(kept, name)
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected: raise UpgradeError('preserved_originals_drift')
        finally: os.close(kept)
        root = core['open_directory'](ROOT, {0})
        try:
            lock = os.open('.schedule-upgrade.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
            try:
                core['read_private_fd'](lock, 0)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                phase = 'verify_idle_schedule_and_policy'
                idle_original(command)
                policy = fields(command, SERVICE, ('AmbientCapabilities', 'CapabilityBoundingSet',
                    'NoNewPrivileges', 'PrivateNetwork', 'ProtectHome', 'ProtectSystem'))
                if (policy['AmbientCapabilities'].split() != ['cap_setuid']
                        or set(policy['CapabilityBoundingSet'].split()) != {'cap_setuid', 'cap_setgid'}
                        or policy['NoNewPrivileges'] != 'yes' or policy['PrivateNetwork'] != 'yes'
                        or policy['ProtectHome'] != 'yes' or policy['ProtectSystem'] != 'strict'):
                    raise UpgradeError('effective_candidate_policy_mismatch')
                phase = 'bind_retained_upgraded_run'
                raw = command(['/usr/bin/journalctl', '--no-pager', '--output=json', '--lines=160', '_SYSTEMD_UNIT=' + SERVICE])
                report = bound_retained_report(raw, runner, snapshots[UNITS / SERVICE][1])
                binding = True
                phase = 'authenticate_retained_ciphertext'
                authenticate(core, backup, report)
                authenticated = True
                directory = core['open_directory'](backup['DESTINATION'], {0})
                try: manifest = json.loads(core['read_private_at'](directory, Path(report['encrypted_backup']).name + '.json', 0)[0])
                finally: os.close(directory)
                created = datetime.fromisoformat(manifest['created_utc'])
                if (created.tzinfo is None or created.astimezone(timezone.utc).timestamp() * 1e9 < snapshots[UNITS / SERVICE][1]
                        or created > datetime.now(timezone.utc)):
                    raise UpgradeError('signed_generation_predates_service_publication')
                phase = 'final_candidate_and_schedule_recheck'
                idle_original(command)
                for path, raw in ((runner, program), (UNITS / SERVICE, service), (UNITS / TIMER, timer)):
                    if published_snapshot(core, path, raw) != snapshots[path]: raise UpgradeError('installed_candidate_drift')
                phase = 'daily_timer_enable'
                command(['/usr/bin/systemctl', 'enable', '--now', TIMER])
                enabled = True
                if (command(['/usr/bin/systemctl', 'is-enabled', TIMER]).strip() != b'enabled'
                        or command(['/usr/bin/systemctl', 'is-active', TIMER]).strip() != b'active'):
                    raise UpgradeError('daily_timer_not_ready')
                deadline = command(['/usr/bin/systemctl', 'show', TIMER, '--property=NextElapseUSecRealtime', '--value']).strip()
                if not deadline or deadline == b'n/a': raise UpgradeError('daily_timer_has_no_next_run')
                print(json.dumps(dict(complete=True, stage='profile_backup_schedule_resume',
                    protected_runner=str(runner), retained_upgraded_runner_binding_verified=True,
                    signed_ciphertext_verified=True, encrypted_backup=report['encrypted_backup'],
                    source_files=report['source_files'], source_bytes=report['source_bytes'],
                    daily_profile_timer_enabled=True, daily_profile_timer_active=True, next_daily_run_scheduled=True,
                    new_backup_manually_started=False, scheduled_catchup_may_run=True,
                    recovery_identity_read=False, decryption_tested=False, previous_generations_preserved=True,
                    existing_database_schedule_changed=False, windows_collection_qualified=False,
                    model_called=False, memory_records_written=False, runtime_qualified=False), indent=2))
            finally: os.close(lock)
        finally: os.close(root)
    except Exception as error:
        reasons = {'retained_invocation_missing', 'upgraded_root_runner_journal_binding_missing',
            'completed_backup_report_required', 'unique_completed_backup_report_required',
            'signed_generation_predates_service_publication', 'installed_candidate_drift',
            'existing_schedule_needs_review', 'effective_candidate_policy_mismatch', 'journal_budget',
            'preserved_originals_protection', 'preserved_originals_drift', 'daily_timer_not_ready',
            'daily_timer_has_no_next_run', 'schedule_command_failed_private_output_suppressed'}
        reason = str(error) if isinstance(error, UpgradeError) and str(error) in reasons else 'guard_or_command_incomplete'
        print(json.dumps(dict(complete=False, stage='profile_backup_schedule_resume', failure_stage=phase,
            category=reason, retained_upgraded_runner_binding_verified=binding,
            signed_ciphertext_verified=authenticated, timer_enable_command_completed=enabled,
            new_backup_manually_started=False, existing_database_schedule_changed=False,
            recovery_identity_read=False, model_called=False, memory_records_written=False,
            runtime_qualified=False), indent=2))
        raise SystemExit(1) from None


if __name__ == '__main__':
    raise SystemExit('Use the published hash-verified operator bundle.')
