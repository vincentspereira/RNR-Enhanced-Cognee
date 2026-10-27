"""Read-only owner digest of the preserved, completed model fixture key.

Compare kernel change time to the protected receipt's completion boundary.
No model/credential is replayed, no key value is returned, and O_NOATIME keeps
the fixture's read bookkeeping unchanged. Only its original owner opens it.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import sys

PROFILE = Path('/var/lib/hermes-renewal-qualification/zai_recall_b5ceda49da6343159db0687cd0529045')


def require(value):
    if not value: raise ValueError('qualified_model_key_binding_refused')


def digest(profile, uid, completed_ns):
    require(os.geteuid() == uid and uid > 0 and type(completed_ns) is int and completed_ns > 0
            and isinstance(profile, Path) and profile.is_absolute() and '..' not in profile.parts)
    descriptor = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for part in profile.parts[1:]:
            child = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor); descriptor = child
            info = os.fstat(descriptor)
            require(info.st_uid in {0, uid} and not info.st_mode & 0o022)
        require(os.fstat(descriptor).st_uid == uid)
        fd = os.open('.env', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOATIME, dir_fd=descriptor)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == uid and before.st_nlink == 1
                    and stat.S_IMODE(before.st_mode) == 0o600 and before.st_size <= 65536
                    and 0 < before.st_mtime_ns <= completed_ns and 0 < before.st_ctime_ns <= completed_ns)
            raw = stream.read(65537)
            after = os.fstat(stream.fileno()); named = os.stat('.env', dir_fd=descriptor, follow_symlinks=False)
            fields = ('st_dev', 'st_ino', 'st_uid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_atime_ns')
            require(len(raw) == before.st_size and all(getattr(before, key) == getattr(after, key) for key in fields)
                    and (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino))
    finally: os.close(descriptor)
    from dotenv.parser import parse_stream
    rows = list(parse_stream(io.StringIO(raw.decode())))
    require(not any(row.error for row in rows))
    keys = [row.value for row in rows if row.key == 'GLM_API_KEY']
    origins = [row.value for row in rows if row.key == 'GLM_BASE_URL']
    require(len(keys) == 1 and isinstance(keys[0], str) and 16 <= len(keys[0]) <= 4096
            and origins == ['https://open.bigmodel.cn/api/coding/paas/v4'])
    return dict(complete=True, model_key_sha256=hashlib.sha256(keys[0].encode()).hexdigest(), fixture_unchanged_since_receipt=True)


def child():
    packet = json.loads(sys.stdin.buffer.readline(1025))
    require(isinstance(packet, dict) and set(packet) == {'completed_ns'})
    account = pwd.getpwuid(os.geteuid())
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_name == 'hermes-runtime' and not os.getgroups() and status['NoNewPrivs'].strip() == '1'
            and all(status[field].strip() == '0000000000000000' for field in ('CapEff', 'CapAmb')))
    os.environ.clear(); os.environ.update(PATH='/usr/bin:/bin', HOME=account.pw_dir, LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    os.chdir('/')
    print(json.dumps(digest(PROFILE, account.pw_uid, packet['completed_ns'])))
