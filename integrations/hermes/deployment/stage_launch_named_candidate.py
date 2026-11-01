"""Stage the backed-up named profile into its existing isolated account.

Authenticate the retained generation; do not capture/replay backups. The main
account stays pending. Owner child writes one NEW inactive private directory;
no source/config edits, credentials issued, profile execution or unit changes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import pwd
import re
import resource
import subprocess
import sys
import tarfile
import tempfile

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
RECOVERY = BASE / 'operator-evidence/named-profile-backup-24br2v3u'
BACKUPS = Path('/var/backups/enhanced-cognee')
AGE = Path('/usr/local/bin/age')
IDENTITY = Path('/etc/enhanced-cognee/age-recovery-identity.txt')
CORE_SHA = 'e3dd6b934c6975b99d54f9042ed7aa7eb8204a6ba14f04e2d0364f6ecfdc0b48'
CAPTURE_SHA = '2d30a49d2286fce465b01446e7a0836884f9ae4cccac5fc06ebaad4d927373f4'
MAX_PACKET = 32 * 1024 * 1024
FORBIDDEN = {'ENCRYPTION_MASTER_KEY', 'ENHANCED_JWT_SECRET', 'ENHANCED_INDEX_KEY', 'ENHANCED_BACKUP_SIGNING_KEY',
    'ENHANCED_MEMORY_DATABASE_URL', 'ENHANCED_INDEX_DATABASE_URL', 'INDEX_ARCADEDB_PASSWORD',
    'INDEX_QDRANT_API_KEY', 'INDEX_VALKEY_URL', 'ARCADEDB_PASSWORD', 'POSTGRES_PASSWORD', 'QDRANT_API_KEY',
    'REDIS_PASSWORD', 'NEO4J_PASSWORD'}


def require(value):
    if not value:
        raise ValueError('named_candidate_staging_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    result = {'__name__': 'verified_candidate_support', '__file__': str(path)}
    exec(compile(raw, '<verified-candidate-support>', 'exec'), result)
    return result


def select_accounts(plans, rows):
    selected, deferred = [], []
    for row in rows:
        require(isinstance(row, dict) and re.fullmatch(r'[a-f0-9]{16}', row.get('profile_id', '')))
        matches = [plan for plan in plans if plan['profile_id'] == row['profile_id']]
        require(len(matches) == 1)
        plan = matches[0]
        require(plan['proposed_user'] == row['user'] and plan['proposed_home'] == row['home']
                and plan['enabled'] is False and row['user'] == 'ecbot_' + row['profile_id']
                and row['home'] == '/var/lib/enhanced-cognee-profiles/' + row['profile_id'])
        source = Path(plan['source_profile'])
        require(plan['source_user'] == 'vincentspereira')
        if str(source) == '/home/vincentspereira/.hermes':
            deferred.append(row)
        else:
            require(source.parent == Path('/home/vincentspereira/.hermes/profiles'))
            selected.append(row)
    require(len(selected) == 1 and len(deferred) == 1)
    return selected


def verify_manifest(value, key, profile_id, ciphertext):
    require(isinstance(value, dict) and value.get('complete') is True
            and value.get('format') == 'hermes-named-profile-sqlite-tar+age'
            and value.get('source_profile_id') == profile_id and value.get('capture_component_sha256') == CAPTURE_SHA
            and value.get('ciphertext_sha256') == hashlib.sha256(ciphertext).hexdigest())
    canonical = json.dumps({k: v for k, v in value.items() if k != 'signature'},
                           sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    require(isinstance(value.get('signature'), str)
            and hmac.compare_digest(value['signature'], hmac.new(key, canonical, hashlib.sha256).hexdigest()))


def privileged_environment_absent(payload):
    # Root checks known privilege-bearing names before forwarding plaintext to
    # another UID. Parse no values, expand nothing and execute no profile code.
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:') as archive:
        env = archive.getmember('.env')
        require(env.isfile() and env.size <= 65536)
        raw = archive.extractfile(env).read(65537).decode('utf-8')
    for line in raw.splitlines():
        match = re.match(r"^\s*(?:export\s+)?(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))\s*=", line)
        require(match is None or (match.group(1) or match.group(2)) not in FORBIDDEN)


def child():
    packet = sys.stdin.buffer.readline(MAX_PACKET + 1)
    require(len(packet) <= MAX_PACKET)
    data = json.loads(packet)
    require(set(data) == {'user', 'uid', 'home', 'archive', 'core'})
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_uid == data['uid'] and account.pw_name == data['user']
            and account.pw_dir == data['home'] and re.fullmatch(r'ecbot_[a-f0-9]{16}', account.pw_name)
            and account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:]
            and not os.getgroups() and fields['NoNewPrivs'].strip() == '1'
            and all(fields[k].strip() == '0000000000000000' for k in ('CapEff', 'CapAmb')))
    public = data['core'].encode()
    require(hashlib.sha256(public).hexdigest() == CORE_SHA)
    core = {'__name__': 'verified_candidate_restore'}
    exec(compile(public, '<verified-candidate-restore>', 'exec'), core)
    payload = base64.b64decode(data['archive'], validate=True)
    # Only archive bytes/data are interpreted by the validated restorer; copied
    # configs, plugins and instructions are never executed during staging.
    destination, receipt = core['restore'](payload, owner_home=True)
    from dotenv.parser import parse_stream
    with (Path(destination) / '.env').open() as stream:
        bindings = list(parse_stream(stream))
    require(not any(binding.error or binding.key in FORBIDDEN for binding in bindings))
    print(json.dumps(dict(complete=True, candidate=destination, receipt=receipt,
        known_privileged_environment_fields_absent=True, profile_started=False)), flush=True)


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    helper = definitions(Path(__file__).with_name('qualify_launch_isolated_accounts.py'),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    shared = definitions(Path(__file__).with_name('recover_launch_graph_operator.py'), helper['SUPPORT_SHA'])
    read, write = shared['read_file'], shared['private_write']
    accepted = json.loads(read(RECOVERY / 'summary.json', 0))
    require(accepted.get('complete') is True and accepted.get('named_profile_backup_restore_qualified') is True
            and accepted.get('operator_helper_sha256') == 'a684dc78a62c623598ea1529dad9d9c1f305c9212efcd6f6d71f517e50c7ffcf'
            and accepted.get('encrypted_signed_generations_created') == 42
            and accepted.get('disposable_restores_qualified') == 42)
    raw_plan = read(BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json', 0)
    require(hashlib.sha256(raw_plan).hexdigest() == 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b')
    accounts = select_accounts(json.loads(raw_plan)['profiles'], json.loads(read(
        BASE / 'operator-evidence/isolated-accounts-2eq6h4nn/accounts.private.json', 0)))
    driver = definitions(BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path in (AGE, IDENTITY, BACKUPS):
        driver['protected'](path)
    core = Path(__file__).with_name('capture_named_profile.py').read_bytes()
    require(hashlib.sha256(core).hexdigest() == CORE_SHA)
    key = json.loads(read(Path('/etc/enhanced-cognee/backup.json'), 0))['ENHANCED_BACKUP_SIGNING_KEY'].encode()
    require(len(key) >= 32)
    source = Path(__file__).read_bytes()
    evidence = Path(tempfile.mkdtemp(prefix='named-candidate-stage-', dir=BASE / 'operator-evidence'))
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), inactive_candidates_staged=0,
        main_account_deferred=True, source_profiles_changed=False, gateways_started=0, units_installed=0,
        credentials_issued=0, private_keys_sent_to_owner_children=False, actual_profile_admission_qualified=False,
        fleet_launch_approved=False)
    write(evidence / 'started.json', json.dumps(result).encode())
    try:
        for row in accounts:
            account = pwd.getpwnam(row['user'])
            require(account.pw_uid == row['uid'] and account.pw_dir == row['home']
                    and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
            # One-use root ticket: no second staging run or accidental replay.
            write(RECOVERY / (row['profile_id'] + '.candidate-stage.started.json'), json.dumps(dict(evidence=str(evidence))).encode())
            done = json.loads(read(RECOVERY / (row['profile_id'] + '.done.json'), 0))
            generation = Path(done['generation'])
            require(generation.parent == BACKUPS and re.fullmatch(r'hermes_named_profile_[a-f0-9]{32}\.tar\.age', generation.name))
            ciphertext = read(generation, 0, MAX_PACKET)
            manifest = json.loads(read(generation.with_name(generation.name + '.json'), 0))
            verify_manifest(manifest, key, row['profile_id'], ciphertext)
            plain = subprocess.run([str(AGE), '--decrypt', '--identity', str(IDENTITY)], input=ciphertext,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=20, cwd='/',
                env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8'})
            require(len(plain.stdout) <= 20 * 1024 * 1024)
            privileged_environment_absent(plain.stdout)
            code, public_line = helper['owner_program'](source)
            packet = dict(user=account.pw_name, uid=account.pw_uid, home=account.pw_dir,
                          archive=base64.b64encode(plain.stdout).decode(), core=core.decode())
            process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
                input=public_line + json.dumps(packet).encode() + b'\n', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=65, user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd='/',
                env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
            require(process.returncode == 0 and 0 < len(process.stdout) <= 16384)
            value = json.loads(process.stdout)
            require(set(value) == {'complete', 'candidate', 'receipt', 'known_privileged_environment_fields_absent', 'profile_started'}
                    and value['complete'] is True and value['known_privileged_environment_fields_absent'] is True
                    and value['profile_started'] is False and Path(value['candidate']).parent == Path(account.pw_dir)
                    and re.fullmatch(r'ec-named-profile-restore-[a-zA-Z0-9_-]{6,64}', Path(value['candidate']).name)
                    and value['receipt'].get('complete') is True and value['receipt'].get('archived_files_verified') is True
                    and value['receipt'].get('private_restore_verified') is True and value['receipt'].get('restored_profile_executed') is False
                    and value['receipt'].get('sqlite_databases_verified') == manifest['receipt']['sqlite_databases'])
            write(evidence / (row['profile_id'] + '.candidate.private.json'), json.dumps(dict(value,
                profile_id=row['profile_id'], user=account.pw_name, uid=account.pw_uid, generation=str(generation))).encode())
            result['inactive_candidates_staged'] += 1
        result.update(complete=True, authenticated_candidate_copy_verified=True)
    except Exception:
        result['category'] = 'named_candidate_staging_incomplete_preserve_evidence_no_automatic_retry'
    write(evidence / 'summary.json', json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"named_candidate_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
