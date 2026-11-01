#!/usr/bin/env python3
"""Install missing public PM packaging, preserving the existing Hermes runtime.

No package manager or downloaded code runs as root. The exact archive is read
by its ordinary owner, fully validated, and unpacked without tar extraction.
Only two NEW pinned tool directories, a NEW pm-runtime, and the public tool
facts are published. Original facts and every failed attempt are retained.
No services, profiles, provider settings, policies or credentials are changed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import selectors
import stat
import subprocess
import sys
import tarfile
import time

RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-managed-mcp-runtime-v1'
ARCHIVE = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/.archive/managed-mcp-build-vyy1g3gk/managed-pm-payload.tar')
ARCHIVE_BYTES = 464097280
ARCHIVE_SHA = '68a0325fec51b2922b379cec51b8d80a202f2e7783e3c8561154d8a9eb52f521'
TOOLS = {'python-3.14.7+20260901-linux-x64', 'uv-0.12.3-linux-x64'}
PINS = {
    'manifest.json': 'd04ecb6202f3bcabbbc09145d315fb4e73d315da9958638d0acd6817b3b0b566',
    'python/facts.json': 'b09d171749e43c4c000aae24b4a0273e9254a7f6a9b584049606f6cd867da0ea',
    'repo/pm/lock.json': '172dbe11404b0305e81c2cea4597cb8d680e642ea7f0591a79d7a305af5a0661',
    'repo/pm/runtime.py': '68d6ae47d2e0143f3cc377e462e3588abbb0e857bbc9f22442a3f66ebe54c478',
}
MAX_MEMBERS = 20000
MAX_PAYLOAD = 600 * 1024 * 1024


def require(value):
    if not value:
        raise ValueError('managed_mcp_runtime_refused')


def protected(path: Path, *, directory=False):
    for parent in reversed(path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)
    info = path.lstat()
    require(info.st_uid == 0 and not info.st_mode & 0o022)
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1)


def public_read(path: Path, limit=65536) -> bytes:
    protected(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(len(raw) <= limit and stamp(before) == stamp(after) == stamp(path.lstat()))
    return raw


def no_active_candidates():
    identities = {p.pw_uid for p in pwd.getpwall() if p.pw_name.startswith('ecbot_')}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            require(proc.stat().st_uid not in identities)
        except FileNotFoundError:
            continue


def preflight():
    protected(RELEASE, directory=True)
    protected(RELEASE / 'python', directory=True)
    protected(BASE, directory=True)
    for name, digest in PINS.items():
        require(hashlib.sha256(public_read(RELEASE / name)).hexdigest() == digest)
    require(not os.path.lexists(RELEASE / 'pm-runtime'))
    require(all(not os.path.lexists(RELEASE / 'python' / name) for name in TOOLS))
    old = json.loads(public_read(RELEASE / 'python/facts.json'))
    require(old.get('schema') == 1 and old['packages'].get('python') == {'entry': '.'}
            and 'uv' not in old['packages'])
    account = pwd.getpwnam('vincentspereira')
    require(account.pw_uid == 1000 and account.pw_gid == 1000)
    main = pwd.getpwnam('ecbot_5592956882ea9a13')
    require(main.pw_uid == 992 and main.pw_gid == 984)
    no_active_candidates()
    return old


OWNER_READER = r'''
import os,stat,sys
p=sys.argv[1];fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd,'rb') as f:
    before=os.fstat(f.fileno())
    if not (stat.S_ISREG(before.st_mode) and before.st_uid==1000 and before.st_nlink==1
            and before.st_mode&0o777==0o600 and before.st_size==int(sys.argv[2])):raise SystemExit(1)
    for block in iter(lambda:f.read(65536),b''):sys.stdout.buffer.write(block)
    sys.stdout.buffer.flush()
    after=os.fstat(f.fileno())
    if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise SystemExit(1)
'''


def receive_archive(destination: Path):
    process = subprocess.Popen(
        ['/usr/bin/setpriv', '--reuid=1000', '--regid=1000', '--clear-groups',
         '--no-new-privs', '--inh-caps=-all', '--ambient-caps=-all', '--',
         '/usr/bin/python3', '-I', '-B', '-c', OWNER_READER, str(ARCHIVE), str(ARCHIVE_BYTES)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, cwd='/')
    deadline = time.monotonic() + 180
    sha = hashlib.sha256()
    used = 0
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        with destination.open('xb') as output:
            while True:
                require(time.monotonic() < deadline)
                if not selector.select(min(5, max(0, deadline - time.monotonic()))):
                    continue
                data = os.read(process.stdout.fileno(), 65536)
                if not data:
                    break
                used += len(data)
                require(used <= ARCHIVE_BYTES)
                sha.update(data)
                output.write(data)
            output.flush()
            os.fsync(output.fileno())
        require(process.wait(timeout=10) == 0 and used == ARCHIVE_BYTES and sha.hexdigest() == ARCHIVE_SHA)
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stdout.close()


def member_name(name):
    require(isinstance(name, str) and name.isascii() and 0 < len(name) < 512
            and '\\' not in name and all(32 <= ord(c) < 127 for c in name))
    parts = name.split('/')
    require(all(p not in ('', '.', '..') for p in parts) and parts[0] in {'python', 'pm-runtime'})
    if parts[0] == 'python' and len(parts) > 1:
        require(parts[1] in TOOLS | {'facts.json', '.install.lock'})
        if parts[1] == '.install.lock':
            require(len(parts) == 2)
    return parts


def validate_archive(archive):
    rows = {}
    total = 0
    for member in archive:
        require(len(rows) < MAX_MEMBERS and member.name not in rows)
        member_name(member.name)
        require(member.uid == member.gid == 0 and not member.pax_headers)
        require(member.isdir() or member.isreg() or member.issym())
        require(member.mode in ({0o777} if member.issym() else {0o644, 0o755}))
        if member.name == 'python/.install.lock':
            # Native PM leaves this empty build lock. It is retained only in
            # private staging and is never published into the live tool store.
            require(member.isreg() and member.size == 0 and member.mode == 0o644)
        if member.isreg():
            if member.name == 'python/python-3.14.7+20260901-linux-x64/lib/libpython3.14.so.1.0':
                require(member.size == 248404536)
            else:
                require(0 <= member.size <= 150 * 1024 * 1024)
            total += member.size
            require(total <= MAX_PAYLOAD)
        if member.issym():
            require(member.linkname.isascii() and 0 < len(member.linkname) < 512
                    and not member.linkname.startswith('/') and '\\' not in member.linkname)
        rows[member.name] = member
    require(set(p.split('/')[0] for p in rows) == {'python', 'pm-runtime'})
    for name, member in rows.items():
        parts = name.split('/')
        for end in range(1, len(parts)):
            require('/'.join(parts[:end]) in rows and rows['/'.join(parts[:end])].isdir())
        if member.issym():
            pending = parts[:-1] + member.linkname.split('/')
            for _ in range(32):
                normal = []
                for part in pending:
                    if part in ('', '.'):
                        continue
                    if part == '..':
                        require(bool(normal));normal.pop()
                    else:
                        normal.append(part)
                require(bool(normal))
                pending = normal
                for end in range(1, len(pending) + 1):
                    target = rows.get('/'.join(pending[:end]))
                    require(target is not None)
                    if target.issym():
                        pending = pending[:end - 1] + target.linkname.split('/') + pending[end:]
                        break
                    require(end == len(pending) or target.isdir())
                else:
                    break
            else:
                require(False)
    return rows


def unpack(archive_path: Path, destination: Path):
    destination.mkdir(mode=0o700)
    with tarfile.open(archive_path, 'r:') as archive:
        rows = validate_archive(archive)
        for name, member in sorted(rows.items(), key=lambda item: (item[0].count('/'), item[0])):
            target = destination / name
            if member.isdir():
                target.mkdir(mode=0o755)
            elif member.issym():
                target.symlink_to(member.linkname)
            else:
                source = archive.extractfile(member)
                require(source is not None)
                with source, target.open('xb') as output:
                    left = member.size
                    while left:
                        block = source.read(min(65536, left))
                        require(bool(block))
                        output.write(block)
                        left -= len(block)
                target.chmod(member.mode)
    return len(rows)


PROOF = r'''
import json,os,sys,subprocess
from pathlib import Path
release=Path(sys.argv[1]);sys.path.insert(0,str(release/'repo'))
assert os.getresuid()==(992,)*3 and os.getresgid()==(984,)*3 and not os.getgroups()
status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
assert status['NoNewPrivs'].strip()=='1' and all(int(status[k],16)==0 for k in ('CapEff','CapInh','CapAmb'))
from pm.runtime import _resident_runtime
from pm.build_operations import verified_tools
from pm.store import current_target
import pm
resident=_resident_runtime();assert resident and resident[0].is_relative_to(release)
tools=verified_tools(['uv'],source_store=release/'python',target=current_target())
from tools.mcp_tool_config import _managed_launcher
uvx=_managed_launcher('uvx');npx=_managed_launcher('npx')
assert uvx and npx and all(Path(r[0]).is_relative_to(release) for r in (uvx,npx))
cmd=[str(resident[0]),'-I','-S','-B','-c',
    'import sys;sys.path.insert(0,sys.argv[1]);import packaging,tomli_w,truststore;from ruamel.yaml import YAML',str(resident[1])]
assert subprocess.run(cmd,env=dict(os.environ),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30).returncode==0
print(json.dumps({'complete':True,'resident_pm_runtime_qualified':True,'native_managed_launcher_selection_qualified':True,
    'tool_digests_verified':list(tools.entries),'restricted_identity_verified':True,'network_namespace_isolated':True,
    'native_mcp_server_binding_qualified':False,'profiles_read':False,'model_called':False,'memory_api_called':False}))
'''


def proof(home: Path):
    home.mkdir(mode=0o700)
    os.chown(home, 992, 984)
    result = subprocess.run(
        ['/usr/bin/unshare', '--net', '--', '/usr/bin/setpriv', '--reuid=992', '--regid=984',
         '--clear-groups', '--no-new-privs', '--inh-caps=-all', '--ambient-caps=-all', '--',
         str(RELEASE / 'venv/bin/python'), '-I', '-B', '-c', PROOF, str(RELEASE)],
        env={'HOME': str(home), 'HERMES_HOME': str(home), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
             'HERMES_DISABLE_LAZY_INSTALLS': '1', 'PYTHONDONTWRITEBYTECODE': '1'},
        stdin=subprocess.DEVNULL, capture_output=True, cwd='/', timeout=120, check=False)
    require(result.returncode == 0 and len(result.stdout) <= 8192)
    value = json.loads(result.stdout)
    require(value.get('complete') is True and value.get('native_managed_launcher_selection_qualified') is True)
    return value


def main():
    require(os.geteuid() == 0 and sys.argv[1:] == [])
    os.umask(0o077)
    if ARTIFACT.exists():
        summary = ARTIFACT / 'summary.json'
        if summary.exists():
            value = json.loads(public_read(summary))
            print(json.dumps(value))
            return 0 if value.get('complete') else 1
        raise ValueError('retained_attempt_requires_reconciliation')
    old = preflight()
    descriptor = os.open(Path(__file__).absolute(), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid in {0, 1000}
                and info.st_nlink == 1 and not info.st_mode & 0o022)
        source = stream.read(65537)
        require(0 < len(source) <= 65536)
    ARTIFACT.mkdir(mode=0o700)
    with (ARTIFACT / 'operator.source.py').open('xb') as output:
        output.write(source)
    result = {'complete': False, 'evidence': str(ARTIFACT), 'source_revision': BASE.name,
              'managed_launcher_packaging_changed': False, 'backend_runtime_changed': False,
              'services_restarted': False, 'profiles_changed': False, 'credentials_issued': 0,
              'keys_read': False, 'existing_interpreter_or_source_replaced': False,
              'fleet_launch_approved': False}
    try:
        result['checkpoint'] = 'public_archive_transfer'
        receive_archive(ARTIFACT / 'payload.tar')
        result['checkpoint'] = 'public_archive_validation'
        stage = ARTIFACT / 'payload'
        result['archive_members_validated'] = unpack(ARTIFACT / 'payload.tar', stage)
        facts = json.loads((stage / 'python/facts.json').read_text())
        marker = json.loads((stage / 'pm-runtime/pm-runtime.json').read_text())
        require(facts.get('schema') == 1 and set(facts['packages']) == {'uv', 'python'})
        require(marker == {'python': '../python/python-3.14.7+20260901-linux-x64/bin/python3.14',
                           'sitePackages': 'lib/python3.14/site-packages'})
        for key, entry in [('python', 'python-3.14.7+20260901-linux-x64'), ('uv', 'uv-0.12.3-linux-x64')]:
            require(facts['packages'][key]['entry'] == entry)
        preflight()  # Reject concurrent activation or changed metadata before publishing.
        previous = public_read(RELEASE / 'python/facts.json')
        with (ARTIFACT / 'facts.before.json').open('xb') as output:
            output.write(previous)
        result['checkpoint'] = 'publish_missing_public_components'
        result['managed_launcher_packaging_changed'] = True
        for entry in sorted(TOOLS):
            os.rename(stage / 'python' / entry, RELEASE / 'python' / entry)
        os.rename(stage / 'pm-runtime', RELEASE / 'pm-runtime')
        old['packages'].update(facts['packages'])
        require(hashlib.sha256(public_read(RELEASE / 'python/facts.json')).hexdigest() == PINS['python/facts.json'])
        new = RELEASE / 'python/facts.managed-mcp-v1.new'
        with new.open('xb') as output:
            output.write((json.dumps(old, indent=2, sort_keys=True) + '\n').encode())
            output.flush();os.fsync(output.fileno())
        new.chmod(0o644)
        os.replace(new, RELEASE / 'python/facts.json')
        result['checkpoint'] = 'restricted_native_pm_proof'
        # The temporary HOME is outside all profile trees and has no credentials.
        home = Path('/var/tmp') / ('ec-managed-pm-proof-' + os.urandom(12).hex())
        result['proof'] = proof(home)
        result.update(complete=True, checkpoint='complete', original_facts_retained=True,
                      public_archive_sha256=ARCHIVE_SHA,
                      helper_sha256=hashlib.sha256(source).hexdigest())
    except Exception as exc:
        result.update(category='managed_pm_install_incomplete_preserve_evidence_no_automatic_retry',
                      error_kind=type(exc).__name__)
    with (ARTIFACT / 'summary.json').open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'complete': False, 'category': 'managed_pm_preflight_refused_preserve_evidence',
                          'error_kind': type(exc).__name__, 'fleet_launch_approved': False}))
        raise SystemExit(1)
