"""Create two planned permanent runtime identities; invented OS boundary probe.

No real profile copy, memory credential, model call, gateway start or unit
installation. Collisions refuse before changes. Partial creation is retained
for operator review, never retried or removed automatically.
"""
from __future__ import annotations

import errno
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import selectors
import stat
import subprocess
import sys
import tempfile
import time

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PLAN = BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json'
PLAN_SHA = 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b'
PARENT = Path('/var/lib/enhanced-cognee-profiles')
EXECUTABLE = '/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
FLAGS = {'identity_restricted', 'own_marker_read', 'peer_marker_denied', 'peer_process_environment_denied',
         'operator_configuration_denied', 'recovery_identity_denied', 'sudo_under_runtime_restrictions_denied'}


def require(value):
    if not value:
        raise ValueError('isolated_account_qualification_refused')


def selection(document):
    require(isinstance(document, dict) and document.get('schema') == 1
            and document.get('qualification_scope') == 'inert_isolation_drafts_only'
            and document.get('fleet_launch_approved') is False)
    rows = document.get('profiles')
    require(isinstance(rows, list) and len(rows) <= 256)
    chosen = [row for row in rows if row.get('source_user') == 'vincentspereira'][:2]
    require(len(chosen) == 2)
    for row in chosen:
        ident = row.get('profile_id')
        require(isinstance(ident, str) and re.fullmatch(r'[a-f0-9]{16}', ident))
        require(row.get('proposed_user') == 'ecbot_' + ident
                and row.get('proposed_home') == str(PARENT / ident)
                and row.get('enabled') is False and row.get('proposed_uid') is None
                and isinstance(row.get('gates'), dict) and row['gates']
                and all(value is False for value in row['gates'].values()))
    require(chosen[0]['proposed_user'] != chosen[1]['proposed_user'])
    return chosen


def protected_parent(path):
    for item in [path, *path.parents]:
        info = item.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)


def denied(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except PermissionError as error:
        return error.errno == errno.EACCES
    else:
        os.close(fd)
        return False


def child():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    packet = sys.stdin.buffer.readline(8193)
    require(len(packet) <= 8192)
    data = json.loads(packet)
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_name == data['user'] and account.pw_dir == data['home']
            and not os.getgroups() and fields['NoNewPrivs'].strip() == '1'
            and all(fields[key].strip() == '0000000000000000' for key in ('CapEff', 'CapAmb')))
    own = Path(account.pw_dir) / '.hermes/.isolation-marker'
    own_ok = own.read_bytes() == b'invented-isolation-marker-v1'
    result = dict(identity_restricted=True, own_marker_read=own_ok,
        peer_marker_denied=denied(Path(data['peer_home']) / '.hermes/.isolation-marker'),
        peer_process_environment_denied=denied('/proc/' + str(data['peer_pid']) + '/environ'),
        operator_configuration_denied=denied('/etc/enhanced-cognee/operator.json'),
        recovery_identity_denied=denied('/etc/enhanced-cognee/age-recovery-identity.txt'),
        sudo_under_runtime_restrictions_denied=subprocess.run(['/usr/bin/sudo', '-n', '/usr/bin/true'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5).returncode != 0)
    print(json.dumps(result), flush=True)
    # Keep both peer processes alive until the parent has collected both proofs.
    require(sys.stdin.buffer.read(1) == b'!')


def receipt(value):
    require(isinstance(value, dict) and set(value) == FLAGS and all(value[key] is True for key in FLAGS))
    return value


def owner_program(source):
    require(isinstance(source, bytes) and 0 < len(source) <= 32768)
    code = "import sys\nn={'__name__':'isolated_owner_child'}\nexec(compile(sys.stdin.buffer.readline(65537),'<isolated-owner>','exec'),n)\nn['child']()\n"
    public_line = ('exec(' + repr(source.decode()) + ')\n').encode()
    require(len(public_line) <= 65536)
    return code, public_line


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    source = Path(__file__).read_bytes()
    raw = Path(__file__).with_name('recover_launch_graph_operator.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == SUPPORT_SHA)
    support = {'__name__': 'verified_isolated_account_files'}
    exec(compile(raw, '<verified-isolated-account-files>', 'exec'), support)
    read, write = support['read_file'], support['private_write']
    raw_plan = read(PLAN, 0)
    require(hashlib.sha256(raw_plan).hexdigest() == PLAN_SHA)
    chosen = selection(json.loads(raw_plan))
    code, public_line = owner_program(source)
    protected_parent(Path(EXECUTABLE).parent)
    require(Path(EXECUTABLE).lstat().st_uid == 0)
    protected_parent(PARENT.parent)
    if PARENT.exists():
        protected_parent(PARENT)
        require(stat.S_IMODE(PARENT.stat().st_mode) == 0o711)
    for row in chosen:
        for lookup in (pwd.getpwnam, grp.getgrnam):
            try:
                lookup(row['proposed_user'])
            except KeyError:
                pass
            else:
                raise ValueError('existing_identity_preserved')
        require(not os.path.lexists(row['proposed_home']))
    # Verify public execution paths without reading any agent-owned path as root.
    for path in (Path(EXECUTABLE).resolve(strict=True), Path('/usr/sbin/useradd'), Path('/usr/bin/setpriv')):
        protected_parent(path.parent)
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)
    evidence = Path(tempfile.mkdtemp(prefix='isolated-accounts-', dir=BASE / 'operator-evidence'))
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), account_creation_count=0,
        real_profiles_copied=0, credentials_issued=0, keys_read=False, gateways_started=0,
        units_installed=0, existing_profiles_changed=False, existing_launchers_changed=False,
        actual_profile_admission_qualified=False, fleet_launch_approved=False)
    write(evidence / 'started.json', json.dumps(result).encode())
    children = []
    selector = selectors.DefaultSelector()
    try:
        if not PARENT.exists():
            PARENT.mkdir(mode=0o711)
            PARENT.chmod(0o711)
        accounts = []
        for row in chosen:
            subprocess.run(['/usr/sbin/useradd', '--system', '--user-group', '--no-create-home',
                '--home-dir', row['proposed_home'], '--shell', '/usr/sbin/nologin', '--password', '!', row['proposed_user']],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            result['account_creation_count'] += 1
            account = pwd.getpwnam(row['proposed_user'])
            require(account.pw_uid != 0 and account.pw_dir == row['proposed_home']
                    and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
            write(evidence / ('created-' + row['profile_id'] + '.private.json'), json.dumps(dict(
                user=account.pw_name, uid=account.pw_uid, gid=account.pw_gid, home=account.pw_dir,
                profile_id=row['profile_id'], real_profile_copy_started=False)).encode())
            home = Path(row['proposed_home'])
            home.mkdir(mode=0o700)
            (home / '.hermes').mkdir(mode=0o700)
            write(home / '.hermes/.isolation-marker', b'invented-isolation-marker-v1', account.pw_uid)
            os.chown(home / '.hermes', account.pw_uid, account.pw_gid)
            os.chown(home, account.pw_uid, account.pw_gid)
            accounts.append(account)
        # Code is public, no configuration/key material is included in this pipe.
        for account in accounts:
            process = subprocess.Popen(['/usr/bin/setpriv', '--no-new-privs', '--', EXECUTABLE, '-I', '-B', '-c', code],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd='/',
                env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
            children.append(process)
        for index, process in enumerate(children):
            other = 1 - index
            data = dict(user=accounts[index].pw_name, home=accounts[index].pw_dir,
                        peer_home=accounts[other].pw_dir, peer_pid=children[other].pid)
            process.stdin.write(public_line + json.dumps(data).encode() + b'\n')
            process.stdin.flush()
            os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ, index)
        buffers = [bytearray(), bytearray()]
        reports = {}
        deadline = time.monotonic() + 30
        while len(reports) != 2:
            require(time.monotonic() < deadline)
            for selected, _ in selector.select(max(0.01, deadline - time.monotonic())):
                index = selected.data
                block = os.read(selected.fileobj.fileno(), 8193 - len(buffers[index]))
                require(bool(block))
                buffers[index].extend(block)
                require(len(buffers[index]) <= 8192)
                if b'\n' in buffers[index]:
                    reports[index] = receipt(json.loads(buffers[index]))
                    selector.unregister(selected.fileobj)
        for process in children:
            process.stdin.write(b'!')
            process.stdin.flush()
            process.stdin.close()
        require(all(process.wait(timeout=10) == 0 for process in children))
        write(evidence / 'accounts.private.json', json.dumps([dict(user=account.pw_name,
            uid=account.pw_uid, home=account.pw_dir, profile_id=chosen[index]['profile_id'],
            boundary_receipt=reports[index]) for index, account in enumerate(accounts)]).encode())
        result.update(complete=True, invented_os_boundary_qualified=True, restricted_identity_count=2)
    except Exception:
        result['category'] = 'isolated_accounts_incomplete_preserve_evidence_no_automatic_retry'
    finally:
        selector.close()
        for process in children:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()
    write(evidence / 'summary.json', json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"isolated_account_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
