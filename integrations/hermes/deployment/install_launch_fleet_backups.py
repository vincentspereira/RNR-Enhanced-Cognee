"""Install one daily encrypted backup job for the 41 qualified candidates.

No agent launch, signing/renewal, model/API calls, deletion or upload. Root
authenticates ciphertext; private trees are read only by their own restricted
owners using the exact capture code already proven recoverable. A failed run
preserves every generation and blocks later effects pending reconciliation.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import pwd
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE = BASE / 'operator-launch-completion-batch-v2'
STATE = BASE / 'operator-fleet-daily-backups-v1'
IMPLEMENTATION = BASE / 'operator-evidence/launch-implementation-gtiy7pmb'
QUALIFICATION = BASE / 'operator-evidence/launch-qualification-5hdczb81'
BACKUPS = Path('/var/backups/enhanced-cognee')
UNIT = 'enhanced-cognee-qualified-fleet-backup'
V2_SHA = '409de8a25e773489874167f325865c11239ef756e0fa342f1396dcf3f0201a5c'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'


def require(value):
    if not value:
        raise ValueError('qualified_fleet_backup_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(path, digest):
    raw = path.read_bytes()
    require(0 < len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    scope = {'__name__': 'verified_daily_backup_support', '__file__': str(path), '_verified_source_bytes': raw}
    exec(compile(raw, '<verified-daily-backup-support>', 'exec'), scope)
    return scope


def components():
    require(os.geteuid() == 0)
    shared = definitions(PACKAGE / 'recover_launch_graph_operator.py', SUPPORT_SHA)
    driver = definitions(PACKAGE / 'launch_completion_batch_v2.py', V2_SHA)['verified_driver']()
    read = shared['read_file']
    manifest = json.loads(read(PACKAGE / 'sources.json', 0))
    require(manifest.get('launch_completion_batch_v2.py') == V2_SHA)
    for name, digest in manifest.items():
        require(re.fullmatch(r'[a-z0-9_]+\.py', name) and re.fullmatch('[a-f0-9]{64}', digest))
        definitions(PACKAGE / name, digest)
    driver['verify_runtime']()
    return driver, read, shared['private_write']


def membership(driver, read):
    implemented = json.loads(read(IMPLEMENTATION / 'finish.summary.json', 0))
    qualified = json.loads(read(QUALIFICATION / 'finish.summary.json', 0))
    for result, phase, path in ((implemented, 'implementation', IMPLEMENTATION), (qualified, 'qualification', QUALIFICATION)):
        require(result.get('complete') is True and result.get('phase') == phase
                and result.get('source_revision') == BASE.name and result.get('operator_helper_sha256') == V2_SHA
                and result.get('evidence') == str(path) and result.get('operator_job_stopped') is True
                and result.get('all_admission_policies_preserved_disabled') is True
                and all(result.get(key) is False for key in ('source_profiles_changed', 'existing_launchers_changed',
                    'chat_model_called', 'private_keys_sent_to_owner', 'fleet_launch_approved')))
    require(implemented.get('main_candidate_backup_restore_qualified') is True
            and implemented.get('candidate_backup_membership_count') == 41
            and qualified.get('qualified_profiles') == qualified.get('selected_profiles') == 40
            and qualified.get('failed_profiles') == qualified.get('unattempted_profiles') == 0
            and qualified.get('named_post_renewal_restores_qualified') is True
            and qualified.get('scheduled_candidate_fleet_publication_qualified') is True
            and qualified.get('journal_scheduling_proof', {}).get('verified') is True)
    main, _ = driver['fixed_entry'](read)
    entries = json.loads(read(driver['FLEET'] / 'candidate-policy.json', 0))['profiles']
    policy = driver['definitions'](PACKAGE / 'fleet_credential_policy.py',
        '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102')
    policy['validate'](dict(schema=1, profiles=entries + [main]))
    require(len(entries) == 40 and len({row['uid'] for row in entries + [main]}) == 41
            and len({row['home'] for row in entries + [main]}) == 41
            and all(row['enabled'] is False for row in entries + [main]))
    rows = [dict(kind='named', entry=row) for row in entries] + [dict(kind='main', entry=main)]
    draft = json.loads(read(IMPLEMENTATION / 'backup-membership.private.json', 0))
    expected = [dict(user=row['entry']['user'], uid=row['entry']['uid'], home=row['entry']['home'],
        profile=row['entry']['profile'], kind=row['kind'], admission_ready=False) for row in rows]
    require(draft == dict(schema=1, enabled=False, interval_seconds=86400, members=expected))
    return rows


def validate_named_capture(value):
    require(isinstance(value, dict) and set(value) == {'complete', 'receipt', 'ciphertext'} and value['complete'] is True)
    receipt = value['receipt']
    require(isinstance(receipt, dict) and set(receipt) == {'files', 'source_bytes', 'sqlite_databases',
        'sidecars_rebuilt', 'database_versions_stable', 'plain_files_stable', 'plaintext_archive_written'}
        and receipt['database_versions_stable'] is True and receipt['plain_files_stable'] is True
        and receipt['plaintext_archive_written'] is False)
    for field, maximum in [('files', 512), ('source_bytes', 16 * 1024**2), ('sqlite_databases', 512), ('sidecars_rebuilt', 1024)]:
        require(type(receipt[field]) is int and 0 <= receipt[field] <= maximum)
    ciphertext = base64.b64decode(value['ciphertext'], validate=True)
    require(0 < len(ciphertext) < 22 * 1024**2 and ciphertext.startswith(b'age-encryption.org/v1\n'))
    return ciphertext, receipt


def capture(driver, row, recipient):
    entry = row['entry']; account = pwd.getpwnam(entry['user'])
    require(account.pw_uid == entry['uid'] and account.pw_uid > 0 and account.pw_gid > 0
            and account.pw_dir == entry['home'] and account.pw_shell == '/usr/sbin/nologin'
            and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
    if row['kind'] == 'main':
        value, body = driver['owner'](entry, dict(mode='capture_main', entry=entry, recipient=recipient))
        core = driver['definitions'](PACKAGE / 'continue_launch_main_operational.py',
            '547e5bd40aec13c85b3524e15d5732adbfd59b507464182c47f760f7b20c3a25')
        core['validate_owner_result'](value, body, 'capture', account)
        return body, value['receipt']
    require(row['kind'] == 'named')
    backup = driver['definitions'](PACKAGE / 'backup_launch_candidate_profile.py',
        'cf10aba63a529bdfffa392fdce2cbc68860133626b1871831e9f60238ab5326c')
    helper = driver['definitions'](PACKAGE / 'qualify_launch_isolated_accounts.py',
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    source = (PACKAGE / 'backup_launch_candidate_profile.py').read_bytes()
    raw = (PACKAGE / 'capture_candidate_profile.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == backup['CORE_SHA'])
    result = backup['owner'](helper, account, source,
        dict(mode='capture', profile=entry['profile'], recipient=recipient, core=raw.decode()))
    return validate_named_capture(result)


def save_generation(row, ciphertext, receipt, key, key_id, invocation, read, write):
    require(isinstance(ciphertext, bytes) and 0 < len(ciphertext) <= 650 * 1024**2
            and ciphertext.startswith(b'age-encryption.org/v1\n'))
    entry = row['entry']; ident = entry['user'][6:]
    require(re.fullmatch('[a-f0-9]{16}', ident) and re.fullmatch('[a-f0-9]{32}', invocation))
    destination = BACKUPS / ('hermes_fleet_profile_' + ident + '_' + uuid.uuid4().hex + '.tar.age')
    manifest = dict(format='hermes-qualified-fleet-profile+age-v1', complete=True,
        source_revision=BASE.name, profile_id=ident, profile_kind=row['kind'], invocation_id=invocation,
        created_utc=datetime.now(timezone.utc).isoformat(), ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),
        capture_package_sha256=V2_SHA, signing_key_id=key_id, receipt=receipt)
    manifest['signature'] = hmac.new(key, canonical(manifest), hashlib.sha256).hexdigest()
    write(destination, ciphertext); write(destination.with_name(destination.name + '.json'), canonical(manifest))
    sync(BACKUPS)
    saved = read(destination, 0, 650 * 1024**2)
    signed = json.loads(read(destination.with_name(destination.name + '.json'), 0))
    require(signed == manifest and hashlib.sha256(saved).hexdigest() == manifest['ciphertext_sha256']
            and hmac.compare_digest(signed['signature'], hmac.new(key,
                canonical({name: value for name, value in signed.items() if name != 'signature'}), hashlib.sha256).hexdigest()))
    return dict(profile_id=ident, kind=row['kind'], generation=str(destination), signed_ciphertext_verified=True,
        sqlite_databases=receipt['sqlite_databases'], complete=True)


def sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def execute(rows, driver, read, write, evidence, invocation):
    settings = json.loads(read(Path('/etc/enhanced-cognee/backup.json'), 0))
    recipient, key, key_id = [settings[name] for name in
        ('ENHANCED_BACKUP_RECIPIENT', 'ENHANCED_BACKUP_SIGNING_KEY', 'ENHANCED_BACKUP_SIGNING_KEY_ID')]
    require(isinstance(recipient, str) and re.fullmatch('age1[0-9a-z]{20,100}', recipient)
            and isinstance(key, str) and len(key.encode()) >= 32
            and isinstance(key_id, str) and re.fullmatch('[A-Za-z0-9_-]{1,64}', key_id))
    key = key.encode(); del settings
    completed = 0
    for index, row in enumerate(rows, 1):
        require(shutil.disk_usage(BACKUPS).free >= 2 * 1024**3)
        print(json.dumps(dict(event='daily_fleet_backup_progress', current=index, total=41, completed=completed)), flush=True)
        write(evidence / ('started-' + str(index).zfill(3) + '.json'), canonical(dict(profile_id=row['entry']['user'][6:])))
        body, receipt = capture(driver, row, recipient)
        saved = save_generation(row, body, receipt, key, key_id, invocation, read, write)
        write(evidence / ('completed-' + str(index).zfill(3) + '.json'), canonical(saved))
        completed += 1
    del key
    return completed


def worker():
    require(os.geteuid() == 0 and Path(__file__) == STATE / 'install_launch_fleet_backups.py')
    driver, read, write = components()
    lock = os.open(STATE / 'job.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        require(os.fstat(lock).st_uid == 0 and os.fstat(lock).st_nlink == 1)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not os.path.lexists(STATE / 'blocked.json'))
        rows = membership(driver, read)
        require(json.loads(read(STATE / 'members.private.json', 0)) == rows)
        invocation = os.environ.get('INVOCATION_ID', '')
        require(re.fullmatch('[a-f0-9]{32}', invocation))
        evidence = Path(tempfile.mkdtemp(prefix='run-', dir=STATE))
        result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
            operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            invocation_id=invocation, selected_profiles=41, completed_profiles=0,
            credentials_issued=0, keys_changed=False, source_profiles_changed=False,
            source_logical_writes=False, sqlite_read_bookkeeping_may_change=True,
            private_keys_sent_to_owner=False, recovery_key_read=False, plaintext_archive_written=False,
            model_called=False, memory_api_called=False, existing_launchers_changed=False, fleet_launch_approved=False)
        write(evidence / 'started.json', canonical(result))
        if not os.path.lexists(STATE / 'first-run.private.json'):
            write(STATE / 'first-run.private.json', canonical(result))
        before = driver['policies'](read)
        try:
            result['completed_profiles'] = execute(rows, driver, read, write, evidence, invocation)
            require(result['completed_profiles'] == 41 and all(read(path, 0) == raw for path, raw in before.items()))
            result.update(complete=True, signed_encrypted_generations_created=41,
                all_admission_policies_preserved_disabled=True, daily_job_capture_qualified=True,
                prior_disposable_restore_evidence_reused=True, new_restore_replayed=False)
        except Exception as error:
            result['completed_profiles'] = sum(os.path.lexists(evidence / ('completed-' + str(i).zfill(3) + '.json')) for i in range(1, 42))
            result.update(category='daily_fleet_backup_failed_preserve_evidence_reconciliation_required',
                error_kind=type(error).__name__ if type(error).__name__ in {'ValueError', 'OSError', 'PermissionError', 'TimeoutExpired'} else 'other')
            write(STATE / 'blocked.json', canonical(dict(evidence=str(evidence))))
            subprocess.run(['/usr/bin/systemctl', 'stop', UNIT + '.timer'], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=20, check=False)
        write(evidence / 'summary.json', canonical(result)); sync(evidence)
        return 0 if result['complete'] else 1
    finally: os.close(lock)


def unit_text(rows):
    homes = [row['entry']['home'] for row in rows]
    require(len(homes) == len(set(homes)) == 41 and all(re.fullmatch('/var/lib/enhanced-cognee-profiles/[a-f0-9]{16}', value) for value in homes))
    service = '\n'.join(['[Unit]', 'Description=Daily encrypted backups of qualified inactive Hermes candidates',
        '[Service]', 'Type=oneshot', 'User=root', 'Group=root', 'UMask=0077', 'WorkingDirectory=/',
        'ExecStart=' + str(BASE / 'runtime/bin/python') + ' -I -B ' + str(STATE / 'install_launch_fleet_backups.py') + ' --worker',
        'NoNewPrivileges=yes', 'CapabilityBoundingSet=CAP_SETUID CAP_SETGID', 'AmbientCapabilities=',
        'ProtectSystem=strict', 'ProtectHome=yes', 'PrivateTmp=yes', 'PrivateDevices=yes',
        'ProtectKernelTunables=yes', 'ProtectKernelModules=yes', 'ProtectControlGroups=yes',
        'RestrictSUIDSGID=yes', 'RestrictAddressFamilies=AF_UNIX', 'IPAddressDeny=any',
        'InaccessiblePaths=/etc/enhanced-cognee/age-recovery-identity.txt /etc/enhanced-cognee/operator.json /etc/enhanced-cognee/api.json /etc/enhanced-cognee/worker.json',
        'ReadWritePaths=' + ' '.join([str(STATE), str(BACKUPS)] + homes),
        'Restart=no', 'TimeoutStartSec=3600', 'MemoryMax=8G', 'LimitCORE=0', ''])
    timer = '\n'.join(['[Unit]', 'Description=Daily schedule for qualified Hermes candidate backups',
        '[Timer]', 'OnActiveSec=15s', 'OnUnitActiveSec=1d', 'AccuracySec=1s', 'Unit=' + UNIT + '.service',
        '[Install]', 'WantedBy=timers.target', ''])
    return service.encode(), timer.encode()


def timer_properties():
    command = ['/usr/bin/systemctl', 'show', UNIT + '.timer',
        '--property=LoadState,ActiveState,SubState,Result,LastTriggerUSecMonotonic,NextElapseUSecMonotonic,UnitFileState']
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=10)
    require(len(process.stdout) <= 8192)
    return dict(line.split('=', 1) for line in process.stdout.decode().splitlines() if '=' in line)


def watch(driver, read, write):
    final = STATE / 'installed.summary.json'
    if os.path.lexists(final):
        result = json.loads(read(final, 0)); print(json.dumps(result), flush=True)
        return 0 if result.get('complete') is True else 1
    began = time.monotonic(); last = 0
    while True:
        initial = json.loads(read(STATE / 'first-run.private.json', 0)) if os.path.lexists(STATE / 'first-run.private.json') else None
        evidence = Path(initial['evidence']) if initial else None
        if evidence: require(evidence.parent == STATE and evidence.name.startswith('run-'))
        summary = json.loads(read(evidence / 'summary.json', 0)) if evidence and os.path.lexists(evidence / 'summary.json') else None
        value = driver['metadata'](UNIT + '.service')
        if summary and driver['stopped'](value):
            if summary.get('complete') is True:
                require(value.get('Result') == 'success' and value.get('ExecMainStatus') == '0'
                        and value.get('User') == 'root' and value.get('InvocationID') in {'', summary['invocation_id']})
                journal = subprocess.run(['/usr/bin/journalctl', '--no-pager', '--output=json', '--lines=128',
                    '--unit=' + UNIT + '.service', '--unit=' + UNIT + '.timer'],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=15)
                require(len(journal.stdout) <= 262144)
                verifier = definitions(PACKAGE / 'qualify_launch_issuer_publication.py',
                    '70869e40df75df755b16ddc894e560256087a8ec4b84ba3af63ebc1b9f93c072')
                proof = verifier['journal_scheduling_proof']([json.loads(line) for line in journal.stdout.splitlines()], UNIT, summary['invocation_id'])
                require(proof.get('verified') is True)
                timer = timer_properties()
                require(timer.get('LoadState') == 'loaded' and timer.get('ActiveState') == 'active'
                        and timer.get('UnitFileState') == 'enabled' and timer.get('Result') == 'success'
                        and timer.get('NextElapseUSecMonotonic') not in {None, '', '0', 'infinity'})
                summary.update(scheduled_fleet_profile_backup_qualified=True, installed_daily_timer_enabled=True,
                    journal_scheduling_proof=proof, backup_interval_seconds=86400,
                    operator_job_stopped=True, backup_service_remains_scheduled=True)
            write(final, canonical(summary)); sync(STATE)
            print(json.dumps(summary), flush=True); return 0 if summary.get('complete') is True else 1
        if not summary and value.get('ActiveState') == 'failed':
            subprocess.run(['/usr/bin/systemctl', 'stop', UNIT + '.timer'], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, check=True, timeout=20)
            print('{"complete":false,"category":"daily_backup_service_failed_preserve_evidence"}'); return 1
        if not initial and time.monotonic() - began > 45 and timer_properties().get('ActiveState') != 'active':
            print('{"complete":false,"category":"daily_backup_installation_incomplete_preserve_evidence"}'); return 1
        require(time.monotonic() - began <= 3700)
        if time.monotonic() - last >= 15:
            completed = sum(os.path.lexists(evidence / ('completed-' + str(i).zfill(3) + '.json')) for i in range(1, 42)) if evidence else 0
            print(json.dumps(dict(event='scheduled_daily_fleet_backup_running', completed=completed, total=41,
                note='Ctrl+C detaches; repeat install-fleet-backups to reattach.')), flush=True)
            last = time.monotonic()
        time.sleep(2)


def install():
    require(os.geteuid() == 0)
    driver, read, write = components()
    if os.path.lexists(STATE / 'installation.started.json'):
        return watch(driver, read, write)
    rows = membership(driver, read)
    require(not os.path.lexists(STATE) and shutil.disk_usage(BACKUPS).free >= 2 * 1024**3)
    paths = [Path('/etc/systemd/system') / (UNIT + suffix) for suffix in ('.service', '.timer')]
    require(all(not os.path.lexists(path) for path in paths)
            and driver['metadata'](UNIT + '.service').get('LoadState') == 'not-found')
    protected = driver['definitions'](PACKAGE / 'renew_fleet_credentials.py', driver['DRIVER_SHA'])['protected']
    for path in [PACKAGE, BACKUPS, Path('/etc/systemd/system'), Path('/usr/local/bin/age'), BASE / 'runtime/bin/python']:
        protected(path, final_link=path == BASE / 'runtime/bin/python')
    protected((BASE / 'runtime/bin/python').resolve(strict=True))
    STATE.mkdir(mode=0o700)
    source = globals()['_verified_source_bytes']
    write(STATE / 'install_launch_fleet_backups.py', source)
    write(STATE / 'members.private.json', canonical(rows))
    write(STATE / 'installation.started.json', canonical(dict(source_sha256=hashlib.sha256(source).hexdigest(), selected_profiles=41)))
    for path, raw in zip(paths, unit_text(rows)):
        write(path, raw); path.chmod(0o644)
    sync(STATE); sync(Path('/etc/systemd/system'))
    subprocess.run(['/usr/bin/systemctl', 'daemon-reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
    subprocess.run(['/usr/bin/systemctl', 'enable', '--now', UNIT + '.timer'], stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=True, timeout=20)
    return watch(driver, read, write)


if __name__ == '__main__':
    os.umask(0o077); resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        require(sys.argv[1:] == ['--worker'])
        raise SystemExit(worker())
    except KeyboardInterrupt:
        print('{"detached":true,"backup_schedule_preserved":true}', flush=True)
    except Exception:
        print('{"complete":false,"category":"qualified_daily_backup_preflight_refused_no_secret_output"}', flush=True)
        raise SystemExit(1)
