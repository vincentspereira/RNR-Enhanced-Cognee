#!/usr/bin/env python3
"""Build independent public PM/Fetch artifacts; never change a host runtime.

Run as the ordinary deployment owner. Hermes' own PM owns every dependency
operation. Only a new build HOME/store/project is selected in its child process.
Failed outputs and logs are retained. This is not a protected installation or
an admission/production qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
FETCH_VERSION = '2026.10.24'
FETCH_WHEEL_SHA256 = '3dbcb37801a037b29d486f791328a38354f6b2a8ab54ada8064ecf7268a826bf'
FETCH_LOCK_SHA256 = '78647ee83c9b32ba3cd170b75367a7d171818b67e1dc4d929962d7463f095fdc'
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_SOURCE_FILES = 4000


def copy_public_sources(source: Path, destination: Path) -> dict:
    """Copy a bounded public PM closure without following links or .pyc files."""
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(mode=0o700)
    rows = []
    total = 0
    names = [source / 'hermes_constants.py']
    for name in ('pm', 'hermes_cli'):
        names.extend(sorted((source / name).rglob('*')))
    for path in names:
        relative = path.relative_to(source)
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode):
            raise ValueError('public_source_link_refused')
        if stat.S_ISDIR(before.st_mode) or path.suffix not in ('.py', '.json', '.toml', '.lock'):
            continue
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('public_source_type_refused')
        if before.st_uid != 0 or before.st_mode & 0o022:
            raise ValueError('public_source_protection_refused')
        if before.st_size > 4 * 1024 * 1024:
            raise ValueError('public_source_size_refused')
        total += before.st_size
        if total > MAX_SOURCE_BYTES or len(rows) >= MAX_SOURCE_FILES:
            raise ValueError('public_source_budget_refused')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            data = stream.read(4 * 1024 * 1024 + 1)
            after = os.fstat(stream.fileno())
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if not identity(before) == identity(opened) == identity(after) == identity(path.lstat()):
            raise ValueError('public_source_changed')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open('xb') as stream:
            stream.write(data)
        target.chmod(0o600)
        rows.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    receipt = {'files': rows, 'total_bytes': total, 'unchanged_public_sources': True}
    (destination.parent / 'source-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def build_environment(root: Path) -> dict[str, str]:
    """No original HOME, profiles, credentials or package-index credentials."""
    return {
        'HOME': str(root / 'home'),
        'HERMES_HOME': str(root / 'home' / '.hermes'),
        'HERMES_RUNTIME_DIR': str(root / 'tools'),
        'XDG_CACHE_HOME': str(root / 'cache'),
        'TMPDIR': str(root / 'tmp'),
        'PATH': '/usr/bin:/bin',
        'LANG': 'C.UTF-8',
        'PYTHONDONTWRITEBYTECODE': '1',
        'UV_DEFAULT_INDEX': 'https://pypi.org/simple',
        'UV_NO_BUILD': '1',
        'UV_LINK_MODE': 'copy',
    }


WORKER = r'''
import hashlib,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'repo'))
import pm
from pm.build_operations import verified_tools
from pm.store import current_target
def event(phase):
    print(json.dumps({'event':'managed_mcp_build','phase':phase}),flush=True)
event('pinned_tools_and_package_manager')
pm.prepare_tools(['uv'],out=root/'tools',target=current_target(),cache=root/'cache'/'uv')
verified=verified_tools(['uv'],source_store=root/'tools',target=current_target())
event('independent_manager_runtime')
python=verified.entries['python'].binary
pm.stage_manager_runtime(python=python,destination=root/'pm-runtime',cache=root/'cache'/'uv')
event('fetch_frozen_lock_validation')
project=root/'fetch-project'
pm.check_project_lock(project,python=python,cache=root/'cache'/'uv',explicit=True)
event('fetch_frozen_environment')
executable=pm.build_environment(source=project,out=root/'fetch',python=python,
    cache=root/'cache'/'uv',frozen=True,no_install_project=True,explicit=True)
event('complete')
(root/'build-result.json').write_text(json.dumps({'complete':True,'fetch_python':str(executable),
    'tools_verified':list(verified.entries),'lock_sha256':hashlib.sha256((project/'uv.lock').read_bytes()).hexdigest(),
    'protected_runtime_changed':False,'profiles_changed':False,'fleet_launch_approved':False},indent=2)+'\n')
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-parent', type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() == 0:
        raise SystemExit('ERR: build as the ordinary owner, never root')
    os.umask(0o077)
    parent = args.output_parent.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix='managed-mcp-build-', dir=parent))
    result = {'complete': False, 'build': str(root), 'protected_runtime_changed': False,
              'profiles_changed': False, 'fleet_launch_approved': False}
    try:
        sources = copy_public_sources(RELEASE / 'repo', root / 'repo')
        for name in ('home', 'cache', 'tmp', 'fetch-project'):
            (root / name).mkdir(mode=0o700)
        import tomllib
        project = Path(__file__).with_name('fetch-candidate')
        lock = (project / 'uv.lock').read_bytes()
        if hashlib.sha256(lock).hexdigest() != FETCH_LOCK_SHA256:
            raise ValueError('reviewed_fetch_lock_changed')
        packages = tomllib.loads(lock.decode())['package']
        selected = [p for p in packages if p['name'] == 'mcp-server-fetch']
        if not (len(selected) == 1 and selected[0]['version'] == FETCH_VERSION
                and any(w['hash'] == 'sha256:' + FETCH_WHEEL_SHA256 for w in selected[0]['wheels'])):
            raise ValueError('reviewed_fetch_wheel_changed')
        for name in ('pyproject.toml', 'uv.lock'):
            (root / 'fetch-project' / name).write_bytes((project / name).read_bytes())
        (root / 'worker.py').write_text(WORKER)
        with (root / 'build.log').open('xb') as log:
            process = subprocess.run(
                ['/usr/bin/setpriv', '--no-new-privs', '--', str(RELEASE / 'venv/bin/python'),
                 '-I', '-B', str(root / 'worker.py'), str(root)],
                env=build_environment(root), cwd=root, stdout=log, stderr=log, timeout=1500,
                check=False)
        result.update(source_files=len(sources['files']), source_bytes=sources['total_bytes'],
                      child_exit_code=process.returncode)
        if process.returncode == 0:
            result.update(json.loads((root / 'build-result.json').read_text()))
    except Exception as exc:
        result['error_kind'] = type(exc).__name__
    (root / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
