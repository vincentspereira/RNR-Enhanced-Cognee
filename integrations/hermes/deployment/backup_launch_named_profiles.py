"""One bounded batch: encrypted/signed named-profile captures and restores.

Only the 42 pinned named profiles; the main tree is explicitly excluded and
remains pending. Owner children alone traverse/capture/restore profile data.
Root signs ciphertext metadata and decrypts with existing protected keys.
No configuration switch, profile execution, model call or key rotation.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import pwd
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
BACKUPS = Path('/var/backups/enhanced-cognee')
AGE = Path('/usr/local/bin/age')
IDENTITY = Path('/etc/enhanced-cognee/age-recovery-identity.txt')
CORE_SHA = 'e3dd6b934c6975b99d54f9042ed7aa7eb8204a6ba14f04e2d0364f6ecfdc0b48'
MAX_PACKET = 32 * 1024 * 1024
PHASE = 'identity'
FAILED = BASE / 'operator-evidence/named-profile-backup-5ha0t0os'


def zero_generation_attempt(value):
    require(isinstance(value, dict) and value.get('complete') is False
            and value.get('source_revision') == BASE.name
            and value.get('operator_helper_sha256') == '33a2081c9e83d71875c00ddda94e20007e31bc029051f53a44e3076c061acec5'
            and value.get('selected_named_profiles') == 42
            and value.get('failure_phase') == 'owner_capture'
            and value.get('owner_failure_kind') == 'CaptureError'
            and value.get('current_profile_id') == '534e43407c192971'
            and all(type(value.get(key)) is int and value[key] == 0 for key in
                ('encrypted_signed_generations_created', 'disposable_restores_qualified', 'sqlite_databases_recovered')))


def require(value):
    if not value:
        raise ValueError('named_profile_backup_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def signature(value, key):
    return hmac.new(key, canonical({k: v for k, v in value.items() if k != 'signature'}), hashlib.sha256).hexdigest()


def verify_manifest(value, key, profile_id, digest):
    require(isinstance(value, dict) and value.get('format') == 'hermes-named-profile-sqlite-tar+age'
            and value.get('complete') is True and value.get('source_profile_id') == profile_id
            and value.get('ciphertext_sha256') == digest and isinstance(value.get('signature'), str)
            and hmac.compare_digest(value['signature'], signature(value, key)))


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_named_backup_support', '__file__': str(path)}
    exec(compile(raw, '<verified-named-backup-support>', 'exec'), namespace)
    return namespace


def child():
    global PHASE
    raw = sys.stdin.buffer.readline(MAX_PACKET + 1)
    require(len(raw) <= MAX_PACKET)
    packet = json.loads(raw)
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_name == 'vincentspereira' and not os.getgroups()
            and fields['NoNewPrivs'].strip() == '1'
            and all(fields[key].strip() == '0000000000000000' for key in ('CapEff', 'CapAmb')))
    public = packet['core'].encode()
    require(hashlib.sha256(public).hexdigest() == CORE_SHA)
    core = {'__name__': 'verified_named_capture'}
    exec(compile(public, '<verified-named-capture>', 'exec'), core)
    if packet['mode'] == 'capture':
        profile = Path(packet['profile'])
        require(profile.parent == Path(account.pw_dir) / '.hermes/profiles')
        PHASE = 'owner_capture'
        archive, receipt = core['capture'](profile)
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as bundle:
            require(all(bundle.getmember(name).isfile() for name in ('.env', 'config.yaml')))
        PHASE = 'owner_encryption'
        recipient = packet['recipient']
        require(isinstance(recipient, str) and re.fullmatch(r'age1[0-9a-z]{20,100}', recipient))
        encrypted = subprocess.run([str(AGE), '--encrypt', '--recipient', recipient], input=archive,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20, check=True)
        require(0 < len(encrypted.stdout) < 22 * 1024 * 1024)
        print(json.dumps(dict(complete=True, receipt=receipt,
            ciphertext=base64.b64encode(encrypted.stdout).decode())), flush=True)
    elif packet['mode'] == 'restore':
        PHASE = 'owner_disposable_restore'
        archive = base64.b64decode(packet['archive'], validate=True)
        require(len(archive) <= core['MAX_ARCHIVE'])
        destination, receipt = core['restore'](archive)
        print(json.dumps(dict(complete=True, destination=destination, receipt=receipt)), flush=True)
    else:
        raise ValueError('fixed_named_backup_mode_required')


def owner(helper, account, source, packet):
    require(isinstance(packet, dict) and packet.get('mode') in {'capture', 'restore'})
    expected = {'mode', 'profile', 'recipient', 'core'} if packet['mode'] == 'capture' else {'mode', 'archive', 'core'}
    require(set(packet) == expected and isinstance(packet['core'], str)
            and hashlib.sha256(packet['core'].encode()).hexdigest() == CORE_SHA)
    _, public_line = helper['owner_program'](source)
    code = ("import sys,json\nn={'__name__':'named_profile_owner'}\n"
            "exec(compile(sys.stdin.buffer.readline(65537),'<named-owner>','exec'),n)\n"
            "try:\n n['child']()\n"
            "except Exception as e:\n"
            " k=type(e).__name__\n"
            " print(json.dumps({'complete':False,'phase':n.get('PHASE','identity'),"
            "'error_kind':k if k in {'CaptureError','ValueError','KeyError','PermissionError','FileNotFoundError','CalledProcessError','TimeoutExpired'} else 'other'}))\n"
            " raise SystemExit(1)\n")
    raw = public_line + json.dumps(packet).encode() + b'\n'
    require(len(raw) <= MAX_PACKET)
    process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
        input=raw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=65,
        user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd='/',
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    require(0 < len(process.stdout) <= MAX_PACKET)
    value = json.loads(process.stdout)
    if process.returncode != 0:
        error = ValueError('named_owner_stopped_preserve_evidence')
        error.owner_phase = value.get('phase') if value.get('phase') in {'identity', 'owner_capture', 'owner_encryption', 'owner_disposable_restore'} else 'unknown'
        error.owner_error_kind = value.get('error_kind') if value.get('error_kind') in {'CaptureError', 'ValueError', 'KeyError', 'PermissionError', 'FileNotFoundError', 'CalledProcessError', 'TimeoutExpired'} else 'other'
        raise error
    require(isinstance(value, dict) and value.get('complete') is True and isinstance(value.get('receipt'), dict))
    if packet['mode'] == 'capture':
        require(set(value) == {'complete', 'receipt', 'ciphertext'})
        report = value['receipt']
        require(set(report) == {'files', 'source_bytes', 'sqlite_databases', 'sidecars_rebuilt',
            'database_versions_stable', 'plain_files_stable', 'plaintext_archive_written'}
            and report['database_versions_stable'] is True and report['plain_files_stable'] is True
            and report['plaintext_archive_written'] is False
            and all(type(report[k]) is int and 0 <= report[k] <= limit for k, limit in
                [('files', 512), ('source_bytes', 16 * 1024 * 1024), ('sqlite_databases', 512), ('sidecars_rebuilt', 512)]))
    else:
        require(set(value) == {'complete', 'receipt', 'destination'} and isinstance(value['destination'], str)
                and re.fullmatch(r'/tmp/ec-named-profile-restore-[a-zA-Z0-9_-]{6,64}', value['destination']))
        report = value['receipt']
        require(set(report) == {'complete', 'archived_files_verified', 'private_restore_verified', 'sqlite_databases_verified', 'restored_profile_executed'}
                and all(report[k] is True for k in ('complete', 'archived_files_verified', 'private_restore_verified'))
                and report['restored_profile_executed'] is False
                and type(report['sqlite_databases_verified']) is int and 0 <= report['sqlite_databases_verified'] <= 512)
    return value


def main():
    require(os.geteuid() == 0 and sys.argv[1:] == ['--continue-zero-generation-attempt'])
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    helper = definitions(Path(__file__).with_name('qualify_launch_isolated_accounts.py'),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    shared = definitions(Path(__file__).with_name('recover_launch_graph_operator.py'), helper['SUPPORT_SHA'])
    read, write = shared['read_file'], shared['private_write']
    failed = json.loads(read(FAILED / 'summary.json', 0))
    zero_generation_attempt(failed)
    prior = json.loads(read(BASE / 'operator-evidence/sqlite-profile-recovery-32r108dg/summary.json', 0))
    require(prior.get('complete') is True and prior.get('invented_encrypted_sqlite_recovery_qualified') is True
            and prior.get('operator_helper_sha256') == 'aae1ff7cbaf29f66ef10741198a55f3220e832542ba307c3bddfbdaa64af9be0')
    raw_plan = read(BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json', 0)
    require(hashlib.sha256(raw_plan).hexdigest() == 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b')
    account = pwd.getpwnam('vincentspereira')
    parent = Path(account.pw_dir) / '.hermes/profiles'
    selected = [row for row in json.loads(raw_plan)['profiles'] if row['source_user'] == account.pw_name
                and Path(row['source_profile']).parent == parent]
    require(len(selected) == 42 and all(row['source_uid'] == account.pw_uid and row['enabled'] is False
                and row['profile_id'] == hashlib.sha256((account.pw_name + '\0' + row['source_profile']).encode()).hexdigest()[:16]
                for row in selected))
    require(selected[0]['profile_id'] == failed['current_profile_id'])
    driver = definitions(BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path in (AGE, IDENTITY, BACKUPS):
        driver['protected'](path)
    core = Path(__file__).with_name('capture_named_profile.py').read_bytes()
    require(hashlib.sha256(core).hexdigest() == CORE_SHA)
    config = json.loads(read(Path('/etc/enhanced-cognee/backup.json'), 0))
    recipient, key, key_id = (config[name] for name in ('ENHANCED_BACKUP_RECIPIENT', 'ENHANCED_BACKUP_SIGNING_KEY', 'ENHANCED_BACKUP_SIGNING_KEY_ID'))
    require(isinstance(key, str) and len(key.encode()) >= 32 and isinstance(key_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key_id))
    key = key.encode()
    del config
    source = Path(__file__).read_bytes()
    helper['owner_program'](source)
    evidence = Path(tempfile.mkdtemp(prefix='named-profile-backup-', dir=BASE / 'operator-evidence'))
    # O_EXCL consumes a single operator continuation. Existing/completed work
    # cannot be replayed by calling this flag again, including after a failure.
    write(FAILED / 'zero-generation-continuation.started.json', canonical(dict(
        continuation_evidence=str(evidence), helper_sha256=hashlib.sha256(source).hexdigest(),
        capture_component_sha256=CORE_SHA, previous_summary_sha256=hashlib.sha256(canonical(failed)).hexdigest())))
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        continued_from=str(FAILED),
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), selected_named_profiles=42,
        encrypted_signed_generations_created=0, disposable_restores_qualified=0, sqlite_databases_recovered=0,
        private_keys_sent_to_owner_children=False, source_logical_writes_performed=False,
        sqlite_read_bookkeeping_may_change=True, existing_configurations_changed=False,
        models_called=False, services_changed=False, source_profiles_preserved=True,
        main_profile_backup_qualified=False, actual_profile_admission_qualified=False, fleet_launch_approved=False)
    write(evidence / 'started.json', canonical(result))
    phase = 'owner_capture'
    try:
        for row in selected:
            result['current_profile_id'] = row['profile_id']
            require(min(shutil.disk_usage(BACKUPS).free, shutil.disk_usage('/tmp').free) >= 128 * 1024 * 1024)
            ident = uuid.uuid4().hex
            write(evidence / (row['profile_id'] + '.started.json'), canonical(dict(profile_id=row['profile_id'], attempt=ident)))
            phase = 'owner_capture'
            captured = owner(helper, account, source, dict(mode='capture', profile=row['source_profile'], recipient=recipient, core=core.decode()))
            ciphertext = base64.b64decode(captured['ciphertext'], validate=True)
            require(0 < len(ciphertext) < 22 * 1024 * 1024)
            generation = BACKUPS / ('hermes_named_profile_' + ident + '.tar.age')
            phase = 'signed_ciphertext_publication'
            manifest = dict(format='hermes-named-profile-sqlite-tar+age', complete=True, source_profile_id=row['profile_id'],
                created_utc=datetime.now(timezone.utc).isoformat(), ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),
                signing_key_id=key_id, capture_component_sha256=CORE_SHA, receipt=captured['receipt'])
            manifest['signature'] = signature(manifest, key)
            write(generation, ciphertext)
            write(generation.with_name(generation.name + '.json'), canonical(manifest))
            directory = os.open(BACKUPS, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            saved = read(generation, 0, MAX_PACKET)
            saved_manifest = json.loads(read(generation.with_name(generation.name + '.json'), 0))
            verify_manifest(saved_manifest, key, row['profile_id'], hashlib.sha256(saved).hexdigest())
            result['encrypted_signed_generations_created'] += 1
            phase = 'root_authenticated_decryption'
            decrypted = subprocess.run([str(AGE), '--decrypt', '--identity', str(IDENTITY)], input=saved,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=20, cwd='/',
                env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8'})
            require(len(decrypted.stdout) <= 20 * 1024 * 1024)
            phase = 'owner_disposable_restore'
            restored = owner(helper, account, source, dict(mode='restore', archive=base64.b64encode(decrypted.stdout).decode(), core=core.decode()))
            require(restored['receipt']['sqlite_databases_verified'] == captured['receipt']['sqlite_databases'])
            write(evidence / (row['profile_id'] + '.done.json'), canonical(dict(profile_id=row['profile_id'],
                generation=str(generation), signed_ciphertext_verified=True, owner_restore=restored)))
            result['disposable_restores_qualified'] += 1
            result['sqlite_databases_recovered'] += restored['receipt']['sqlite_databases_verified']
        result.pop('current_profile_id', None)
        result.update(complete=True, named_profile_backup_restore_qualified=True)
    except Exception as error:
        result.update(category='named_profile_backup_stopped_preserve_evidence_no_automatic_retry', failure_phase=phase)
        if getattr(error, 'owner_phase', None):
            result['owner_failure_phase'] = error.owner_phase
            result['owner_failure_kind'] = error.owner_error_kind
    write(evidence / 'summary.json', canonical(result))
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps(dict(complete=False, category='named_backup_refused_no_secret_output', phase=PHASE)))
        raise SystemExit(1)
