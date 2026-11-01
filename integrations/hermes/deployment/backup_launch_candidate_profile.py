"""Back up and restore ONLY the newly configured inactive candidate.

Root alone authenticates/decrypts. Owner alone traverses private profile data.
No previous capture is replayed, no source startup code or model is executed.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
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
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PASS = BASE / 'operator-evidence/candidate-provider-f8uifc8j'
BACKUPS = Path('/var/backups/enhanced-cognee')
AGE = Path('/usr/local/bin/age')
IDENTITY = Path('/etc/enhanced-cognee/age-recovery-identity.txt')
CORE_SHA = '40bbfab7605c3e26d5e075265dc251ca5cb08487c3d84d4b908839ba161ab92a'
LIMIT = 32 * 1024 * 1024


def require(value):
    if not value:
        raise ValueError('candidate_backup_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(raw, digest):
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    value = {'__name__': 'verified_candidate_backup_support'}
    exec(compile(raw, '<verified-public-support>', 'exec'), value)
    return value


def child():
    packet = json.loads(sys.stdin.buffer.readline(LIMIT + 1))
    account = pwd.getpwuid(os.geteuid())
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_uid == packet['uid'] and not os.getgroups()
        and status['NoNewPrivs'].strip() == '1' and status['CapEff'].strip() == '0000000000000000'
        and status['CapAmb'].strip() == '0000000000000000')
    core = definitions(packet['core'].encode(), CORE_SHA)
    if packet['mode'] == 'capture':
        profile = Path(packet['profile'])
        require(profile == Path(account.pw_dir) / '.hermes')
        # Bound only the new candidate settings, without executing them or
        # consulting external/managed secret providers.
        require(json.loads((profile / 'enhanced_cognee.json').read_bytes()) == dict(
            base_url='http://127.0.0.1:28080', capture_policy='selected', include_shared=True))
        archive, receipt = core['capture'](profile)
        require(re.fullmatch(r'age1[0-9a-z]{20,100}', packet['recipient']))
        encrypted = subprocess.run([str(AGE), '--encrypt', '--recipient', packet['recipient']],
            input=archive, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20, check=True)
        require(0 < len(encrypted.stdout) < 22 * 1024 * 1024)
        value = dict(complete=True, receipt=receipt, ciphertext=base64.b64encode(encrypted.stdout).decode())
    else:
        require(packet['mode'] == 'restore')
        archive = base64.b64decode(packet['archive'], validate=True)
        destination, receipt = core['restore'](archive)
        value = dict(complete=True, destination=destination, receipt=receipt)
    print(json.dumps(value), flush=True)


def owner(helper, account, source, packet):
    _, line = helper['owner_program'](source)
    code = "import sys,json\nn={'__name__':'candidate_backup_owner'}\nexec(compile(sys.stdin.buffer.readline(65537),'<owner>','exec'),n)\ntry:\n n['child']()\nexcept Exception:\n print('{\"complete\":false}');sys.exit(1)\n"
    raw = line + canonical(dict(packet, uid=account.pw_uid)) + b'\n'
    require(len(raw) <= LIMIT)
    process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
        input=raw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=75, cwd='/',
        user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'})
    require(process.returncode == 0 and 0 < len(process.stdout) <= LIMIT)
    result = json.loads(process.stdout)
    require(result.get('complete') is True and isinstance(result.get('receipt'), dict))
    return result


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    directory = Path(__file__).parent
    shared = definitions((directory / 'recover_launch_graph_operator.py').read_bytes(),
        'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef')
    read, write = shared['read_file'], shared['private_write']
    prior = json.loads(read(PASS / 'summary.json', 0))
    require(prior.get('complete') is True and prior.get('candidate_provider_api_qualified') is True
        and prior.get('operator_helper_sha256') == 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67'
        and prior.get('gateways_started') == 0 and prior.get('fleet_launch_approved') is False)
    binding = json.loads(read(PASS / 'binding.private.json', 0))
    account = pwd.getpwnam(binding['user'])
    require(account.pw_uid == binding['uid'] and account.pw_uid != 0
        and binding['profile'] == str(Path(account.pw_dir) / '.hermes'))
    helper = definitions((directory / 'qualify_launch_isolated_accounts.py').read_bytes(),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    driver = definitions((BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py').read_bytes(),
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    network = definitions((directory / 'qualify_launch_gateway_renewal_v2.py').read_bytes(),
        'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2')
    for path in (AGE, IDENTITY, BACKUPS):
        driver['protected'](path)
    for name, digest in network['PROVIDER_FILES'].items():
        path = network['PROVIDER'] / name
        driver['protected'](path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest)
    core = (directory / 'capture_candidate_profile.py').read_bytes()
    definitions(core, CORE_SHA)
    config = json.loads(read(Path('/etc/enhanced-cognee/backup.json'), 0))
    recipient, key, key_id = (config[name] for name in ('ENHANCED_BACKUP_RECIPIENT', 'ENHANCED_BACKUP_SIGNING_KEY', 'ENHANCED_BACKUP_SIGNING_KEY_ID'))
    require(isinstance(key, str) and len(key.encode()) >= 32 and isinstance(key_id, str)
        and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key_id))
    key = key.encode()
    del config
    source = Path(__file__).read_bytes()
    helper['owner_program'](source)
    require(min(shutil.disk_usage(BACKUPS).free, shutil.disk_usage('/tmp').free) >= 128 * 1024 * 1024)
    evidence = Path(tempfile.mkdtemp(prefix='candidate-profile-backup-', dir=BASE / 'operator-evidence'))
    write(PASS / 'post-configuration-backup.started.json', canonical(dict(evidence=str(evidence))))
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), private_keys_sent_to_owner=False,
        existing_configuration_changed=False, services_changed=False, chat_model_called=False,
        source_logical_writes=False, sqlite_read_bookkeeping_may_change=True,
        scheduled_renewal_qualified=False, actual_profile_admission_qualified=False, fleet_launch_approved=False)
    phase = 'owner_capture'
    write(evidence / 'started.json', canonical(result))
    try:
        captured = owner(helper, account, source, dict(mode='capture', profile=binding['profile'], recipient=recipient, core=core.decode()))
        ciphertext = base64.b64decode(captured['ciphertext'], validate=True)
        require(0 < len(ciphertext) < 22 * 1024 * 1024)
        generation = BACKUPS / ('hermes_candidate_profile_' + uuid.uuid4().hex + '.tar.age')
        phase = 'signed_ciphertext_publication'
        manifest = dict(format='hermes-candidate-profile-sqlite-tar+age-v2', complete=True,
            source_profile_id=binding['profile_id'], created_utc=datetime.now(timezone.utc).isoformat(),
            ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(), capture_component_sha256=CORE_SHA,
            signing_key_id=key_id, receipt=captured['receipt'], provider_files=network['PROVIDER_FILES'])
        manifest['signature'] = hmac.new(key, canonical(manifest), hashlib.sha256).hexdigest()
        write(generation, ciphertext)
        write(generation.with_name(generation.name + '.json'), canonical(manifest))
        directory_fd = os.open(BACKUPS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        result['generation'] = str(generation)
        saved = read(generation, 0, LIMIT)
        metadata = json.loads(read(generation.with_name(generation.name + '.json'), 0))
        signed = {k:v for k,v in metadata.items() if k != 'signature'}
        require(hmac.compare_digest(metadata['signature'], hmac.new(key, canonical(signed), hashlib.sha256).hexdigest())
            and metadata['ciphertext_sha256'] == hashlib.sha256(saved).hexdigest())
        phase = 'root_authenticated_decryption'
        decrypted = subprocess.run([str(AGE), '--decrypt', '--identity', str(IDENTITY)], input=saved,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=20, cwd='/',
            env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8'})
        require(len(decrypted.stdout) <= 20 * 1024 * 1024)
        phase = 'owner_disposable_restore'
        restored = owner(helper, account, source, dict(mode='restore', archive=base64.b64encode(decrypted.stdout).decode(), core=core.decode()))
        report = restored['receipt']
        require(all(report.get(k) is True for k in ('complete', 'archived_files_verified', 'private_restore_verified', 'pinned_provider_binding_reconstructed'))
            and report.get('restored_profile_executed') is False
            and report.get('sqlite_databases_verified') == captured['receipt']['sqlite_databases'])
        write(evidence / 'restored.private.json', canonical(restored))
        result.update(complete=True, post_configuration_backup_qualified=True,
            signed_ciphertext_verified=True, pinned_provider_binding_reconstructed=True,
            sqlite_databases_recovered=report['sqlite_databases_verified'])
    except Exception:
        result.update(category='candidate_profile_backup_incomplete_preserve_evidence_no_automatic_retry', failure_phase=phase)
    write(evidence / 'summary.json', canonical(result))
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"candidate_backup_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
