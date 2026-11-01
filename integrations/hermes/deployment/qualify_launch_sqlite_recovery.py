"""Encrypted invented WAL snapshots and disposable owner restores, two accounts.

No real profiles, service state, memory API, models, root-key transport or key
rotation. Root AGE alone uses the existing protected recovery identity. Source,
restored invented databases, ciphertext generations and evidence are retained.
"""
from __future__ import annotations

import base64
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
AGE = Path('/usr/local/bin/age')
IDENTITY = Path('/etc/enhanced-cognee/age-recovery-identity.txt')
BACKUPS = Path('/var/backups/enhanced-cognee')
CORE_SHA = '991de9f5f3e3982641985e60f63a904f4b92c38903639f21b62ad9f4c4ac8912'
FLAGS = {'complete', 'invented_committed_history_verified', 'uncommitted_change_excluded', 'private_permissions_verified'}
MAX_PACKET = 2 * 1024 * 1024


def require(value):
    if not value:
        raise ValueError('sqlite_recovery_qualification_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_sqlite_recovery_support', '__file__': str(path)}
    exec(compile(raw, '<verified-sqlite-recovery-support>', 'exec'), namespace)
    return namespace


def check_database(connection):
    require(connection.execute('PRAGMA quick_check').fetchall() == [('ok',)])
    require(connection.execute('SELECT version,payload FROM invented_history ORDER BY version').fetchall()
            == [(1, b'invented-original'), (2, b'invented-correction'), (3, b'invented-retraction')])
    require(connection.execute("SELECT count(*) FROM sqlite_schema WHERE name='invented_version_index'").fetchone() == (1,))


def child():
    raw = sys.stdin.buffer.readline(MAX_PACKET + 1)
    require(len(raw) <= MAX_PACKET)
    data = json.loads(raw)
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_name == data['user'] and account.pw_dir == data['home']
            and not os.getgroups() and fields['NoNewPrivs'].strip() == '1'
            and all(fields[key].strip() == '0000000000000000' for key in ('CapEff', 'CapAmb')))
    require(len(data['ident']) == 32 and all(char in '0123456789abcdef' for char in data['ident']))
    source = data['core'].encode()
    require(hashlib.sha256(source).hexdigest() == CORE_SHA)
    core = {'__name__': 'verified_owner_sqlite_snapshot'}
    exec(compile(source, '<verified-owner-sqlite-snapshot>', 'exec'), core)
    home = Path(account.pw_dir)
    result = dict.fromkeys(FLAGS, True)
    if data['mode'] == 'snapshot':
        directory = home / ('sqlite-qualification-' + data['ident'])
        directory.mkdir(mode=0o700)
        path = directory / 'invented.db'
        writer = sqlite3.connect(path)
        try:
            require(writer.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal')
            writer.execute('CREATE TABLE invented_history(version integer primary key,payload blob)')
            writer.execute('CREATE INDEX invented_version_index ON invented_history(version)')
            writer.executemany('INSERT INTO invented_history VALUES (?,?)',
                [(1, b'invented-original'), (2, b'invented-correction'), (3, b'invented-retraction')])
            writer.commit()
            os.chmod(path, 0o600)
            require(path.with_name(path.name + '-wal').stat().st_size > 0)
            writer.execute('INSERT INTO invented_history VALUES (4,?)', (b'uncommitted-invented',))
            snapshot = core['snapshot'](path)
            restored = core['memory_restore'](snapshot)
            try:
                check_database(restored)
            finally:
                restored.close()
            writer.rollback()
            check_database(writer)
        finally:
            writer.close()
        recipient = data['recipient']
        require(isinstance(recipient, str) and recipient.startswith('age1') and len(recipient) == 62 and recipient.isalnum())
        encrypted = subprocess.run([str(AGE), '--encrypt', '--recipient', recipient], input=snapshot,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=True)
        require(0 < len(encrypted.stdout) <= MAX_PACKET // 2)
        result.update(ciphertext=base64.b64encode(encrypted.stdout).decode(), snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),
            committed_wal_snapshot_verified=True, plaintext_snapshot_archive_written=False)
    elif data['mode'] == 'restore':
        snapshot = base64.b64decode(data['snapshot'], validate=True)
        restored = core['memory_restore'](snapshot)
        try:
            check_database(restored)
        finally:
            restored.close()
        directory = home / ('sqlite-restored-' + data['ident'])
        directory.mkdir(mode=0o700)
        path = directory / 'invented.db'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(snapshot)
            stream.flush()
            os.fsync(stream.fileno())
        disk = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        try:
            disk.execute('PRAGMA query_only=ON')
            disk.execute('PRAGMA trusted_schema=OFF')
            check_database(disk)
        finally:
            disk.close()
        require(stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_uid == account.pw_uid
                and stat.S_IMODE(directory.stat().st_mode) == 0o700)
        result.update(new_disposable_disk_restore_verified=True)
    else:
        raise ValueError('fixed_sqlite_qualification_mode_required')
    print(json.dumps(result), flush=True)


def owner_report(helper, account, source, packet, mode):
    code, public_line = helper['owner_program'](source)
    raw = public_line + json.dumps(packet).encode() + b'\n'
    require(len(raw) <= MAX_PACKET)
    process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
        input=raw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=40, cwd='/',
        user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    require(process.returncode == 0 and 0 < len(process.stdout) <= MAX_PACKET)
    value = json.loads(process.stdout)
    extra = {'ciphertext', 'snapshot_sha256', 'committed_wal_snapshot_verified', 'plaintext_snapshot_archive_written'} if mode == 'snapshot' else {'new_disposable_disk_restore_verified'}
    require(isinstance(value, dict) and set(value) == FLAGS | extra and all(value[key] is True for key in FLAGS))
    if mode == 'snapshot':
        require(value['committed_wal_snapshot_verified'] is True and value['plaintext_snapshot_archive_written'] is False
                and isinstance(value['snapshot_sha256'], str) and len(value['snapshot_sha256']) == 64)
    else:
        require(value['new_disposable_disk_restore_verified'] is True)
    return value


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    helper = definitions(Path(__file__).with_name('qualify_launch_isolated_accounts.py'),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    shared = definitions(Path(__file__).with_name('recover_launch_graph_operator.py'), helper['SUPPORT_SHA'])
    read, write = shared['read_file'], shared['private_write']
    accepted = json.loads(read(BASE / 'operator-evidence/isolated-native-units-cj7kqg0b/summary.json', 0))
    require(accepted.get('complete') is True and accepted.get('invented_isolated_native_launch_qualified') is True
            and accepted.get('transient_units_stopped') is True
            and accepted.get('operator_helper_sha256') == 'df3c585821a19a6e7ef978f52d1259c380255b005453fc845c5b487b30f02442')
    driver = definitions(BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path in (AGE, IDENTITY, BACKUPS):
        driver['protected'](path)
    require(stat.S_ISREG(AGE.stat().st_mode) and stat.S_ISREG(IDENTITY.stat().st_mode)
            and stat.S_IMODE(IDENTITY.stat().st_mode) == 0o600 and BACKUPS.is_dir())
    core = Path(__file__).with_name('sqlite_profile_snapshot.py').read_bytes()
    require(hashlib.sha256(core).hexdigest() == CORE_SHA)
    operator = json.loads(read(Path('/etc/enhanced-cognee/operator.json'), 0))
    recipient = operator['ENHANCED_BACKUP_RECIPIENT']
    del operator
    rows = json.loads(read(BASE / 'operator-evidence/isolated-accounts-2eq6h4nn/accounts.private.json', 0))
    require(isinstance(rows, list) and len(rows) == 2)
    accounts = []
    for row in rows:
        account = pwd.getpwnam(row['user'])
        require(account.pw_uid == row['uid'] and account.pw_dir == row['home'] and account.pw_uid != 0
                and re.fullmatch(r'ecbot_[a-f0-9]{16}', account.pw_name)
                and account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:]
                and grp.getgrgid(account.pw_gid).gr_name == account.pw_name
                and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
        accounts.append(account)
    require(len({account.pw_uid for account in accounts}) == 2)
    evidence = Path(tempfile.mkdtemp(prefix='sqlite-profile-recovery-', dir=BASE / 'operator-evidence'))
    source = Path(__file__).read_bytes()
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), qualified_account_count=0,
        encrypted_generations_created=0, real_profiles_changed=False, real_profile_backup_qualified=False,
        private_recovery_key_sent_to_children=False, private_recovery_key_used_by_root_age=False,
        keys_changed=False, credentials_issued=0, services_changed=False, model_called=False,
        canonical_memory_edits=False, fleet_launch_approved=False)
    write(evidence / 'started.json', json.dumps(result).encode())
    try:
        for account in accounts:
            ident = uuid.uuid4().hex
            packet = dict(mode='snapshot', user=account.pw_name, home=account.pw_dir, ident=ident,
                          recipient=recipient, core=core.decode())
            snapshot_report = owner_report(helper, account, source, packet, 'snapshot')
            ciphertext = base64.b64decode(snapshot_report.pop('ciphertext'), validate=True)
            require(0 < len(ciphertext) <= MAX_PACKET // 2)
            generation = BACKUPS / ('profile_sqlite_qualification_' + ident + '.db.age')
            write(generation, ciphertext)
            result['encrypted_generations_created'] += 1
            result['private_recovery_key_used_by_root_age'] = True
            command = [str(AGE), '--decrypt', '--identity', str(IDENTITY)]
            decrypted = subprocess.run(command, input=ciphertext, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                check=True, timeout=15, cwd='/', env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8'})
            require(len(decrypted.stdout) <= MAX_PACKET // 2 and hashlib.sha256(decrypted.stdout).hexdigest() == snapshot_report['snapshot_sha256'])
            altered = bytearray(ciphertext)
            altered[len(altered) // 2] ^= 1
            tamper = subprocess.run(command, input=bytes(altered), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=15, cwd='/', env={'PATH': '/usr/bin:/bin', 'HOME': '/', 'LANG': 'C.UTF-8'})
            require(tamper.returncode != 0)
            packet = dict(mode='restore', user=account.pw_name, home=account.pw_dir, ident=ident,
                          snapshot=base64.b64encode(decrypted.stdout).decode(), core=core.decode())
            restored = owner_report(helper, account, source, packet, 'restore')
            write(evidence / (ident + '.receipt.json'), json.dumps(dict(snapshot=snapshot_report, restore=restored,
                ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(), generation=str(generation),
                authenticated_tamper_denied=True)).encode())
            result['qualified_account_count'] += 1
        result.update(complete=True, invented_encrypted_sqlite_recovery_qualified=True)
    except Exception:
        result['category'] = 'sqlite_profile_recovery_incomplete_preserve_evidence_no_automatic_retry'
    write(evidence / 'summary.json', json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"sqlite_recovery_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
