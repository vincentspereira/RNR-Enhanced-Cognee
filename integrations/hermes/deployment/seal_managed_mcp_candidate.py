#!/usr/bin/env python3
"""Seal a NEW public PM payload with native Hermes packaging helpers.

The previous build, caches and Fetch environment are retained unchanged. This
creates no protected installation and changes no profiles, policies or launchers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
SEALER_SHA = 'ab2fb59a2face83a92121af5e09e68b04c3abe3301261248cdf0c8a2cca9ae98'

WORKER = r'''
from pathlib import Path
import hashlib,json,os,sys,tarfile
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'repo'))
import pm
from pm.build_operations import verified_tools
from pm.store import current_target
out=root/'sealed-payload';out.mkdir(mode=0o700)
pm.stage_tools(['uv'],source_store=root/'tools',out=out/'python',target=current_target())
verified=verified_tools(['uv'],source_store=out/'python',target=current_target())
python=verified.entries['python'].binary
pm.stage_manager_runtime(python=python,destination=out/'pm-runtime',cache=root/'cache'/'uv',offline=True)
source=Path(sys.argv[2]);raw=source.read_bytes()
if hashlib.sha256(raw).hexdigest()!=sys.argv[3]:raise ValueError('native_sealer_changed')
namespace={'__name__':'verified_native_sealer','__file__':str(source)}
exec(compile(raw,str(source),'exec'),namespace)
marker=namespace['seal_pm_runtime'](out,python)
for p in sorted(out.rglob('*')):
    if p.is_symlink():
        if not p.resolve().is_relative_to(out):raise ValueError('payload_link_escape')
        continue
    p.chmod(0o755 if p.is_dir() or p.stat().st_mode&0o100 else 0o644)
verified_tools(['uv'],source_store=out/'python',target=current_target())
archive=root/'managed-pm-payload.tar'
with tarfile.open(archive,'x',format=tarfile.GNU_FORMAT) as tar:
    def normalized(member):
        member.uid=member.gid=0;member.uname=member.gname='';member.mtime=0
        return member
    for name in ('python','pm-runtime'):tar.add(out/name,arcname=name,recursive=True,filter=normalized)
sha=hashlib.sha256()
with archive.open('rb') as f:
    for data in iter(lambda:f.read(1024*1024),b''):sha.update(data)
result={'complete':True,'archive':str(archive),'archive_bytes':archive.stat().st_size,
    'archive_sha256':sha.hexdigest(),'marker':marker,'tools_verified':['python','uv'],
    'native_sealing_helper_sha256':sys.argv[3], 'protected_runtime_changed':False,
    'profiles_changed':False,'fleet_launch_approved':False}
(root/'seal-result.json').write_text(json.dumps(result,indent=2)+'\n')
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() == 0:
        raise SystemExit('ERR: seal as ordinary owner, never root')
    root = args.build.resolve(strict=True)
    if not json.loads((root / 'summary.json').read_text()).get('complete'):
        raise SystemExit('ERR: completed independent build required')
    if any((root / name).exists() for name in ('sealed-payload', 'seal-result.json', 'seal-worker.py', 'seal.log')):
        raise SystemExit('ERR: existing payload preserved; no automatic reseal')
    os.umask(0o077)
    (root / 'seal-worker.py').write_text(WORKER)
    env = {'HOME': str(root / 'home'), 'HERMES_HOME': str(root / 'home/.hermes'),
           'HERMES_RUNTIME_DIR': str(root / 'tools'), 'PATH': '/usr/bin:/bin',
           'LANG': 'C.UTF-8', 'TMPDIR': str(root / 'tmp'), 'UV_OFFLINE': '1',
           'XDG_CACHE_HOME': str(root / 'cache'), 'PYTHONDONTWRITEBYTECODE': '1'}
    with (root / 'seal.log').open('xb') as log:
        process = subprocess.run(
            ['/usr/bin/setpriv', '--no-new-privs', '--', str(RELEASE / 'venv/bin/python'),
             '-I', '-B', str(root / 'seal-worker.py'), str(root),
             str(RELEASE / 'repo/scripts/bundles/payload.py'), SEALER_SHA],
            cwd=root, env=env, stdout=log, stderr=log, timeout=600, check=False)
    result = (json.loads((root / 'seal-result.json').read_text()) if process.returncode == 0
              else {'complete': False, 'child_exit_code': process.returncode,
                    'build': str(root), 'protected_runtime_changed': False})
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
