#!/usr/bin/env python3
"""Restore the sealed public PM payload and prove relocation without networking.

This runs as the ordinary owner in a new disposable build directory. It does
not qualify the actual main UID, change the protected release or start MCPs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


PROOF = r'''
import json,os,sys,subprocess
from pathlib import Path
root=Path(sys.argv[1]);old=Path(sys.argv[2]);sys.path[:0]=[str(root/'repo'),str(old/'repo')]
status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
assert status['NoNewPrivs'].strip()=='1' and all(int(status[k],16)==0 for k in ('CapEff','CapInh','CapAmb'))
import pm
from pm.runtime import _resident_runtime
from pm.build_operations import verified_tools
from pm.store import current_target
from tools.mcp_tool_config import _managed_launcher
resident=_resident_runtime();assert resident and resident[0].is_relative_to(root)
verified=verified_tools(['uv'],source_store=root/'python',target=current_target())
uvx=_managed_launcher('uvx');assert uvx and Path(uvx[0]).is_relative_to(root)
check=subprocess.run([str(resident[0]),'-I','-S','-B','-c',
    'import sys;sys.path.insert(0,sys.argv[1]);import packaging,tomli_w,truststore;from ruamel.yaml import YAML',
    str(resident[1])],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
assert check.returncode==0
print(json.dumps({'complete':True,'verified_tools':list(verified.entries),
    'relocated_resident_runtime_passed':True,'native_uvx_resolution_passed':True,
    'capabilities_zero':True,'profiles_read':False,'protected_runtime_changed':False,
    'qualification_surface':'ordinary_owner_relocated_public_payload'}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--finish-restored-probe', type=Path)
    args = parser.parse_args()
    if os.getuid() == 0:
        raise SystemExit('ERR: run as ordinary owner')
    os.umask(0o077)
    build = args.build.resolve(strict=True)
    path = Path(__file__).with_name('install_managed_mcp_runtime.py')
    spec = importlib.util.spec_from_file_location('public_archive_validator', path)
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    root = (args.finish_restored_probe.resolve(strict=True) if args.finish_restored_probe
            else Path(tempfile.mkdtemp(prefix='managed-pm-relocation-', dir=build.parent)))
    summary_path = root / ('finish-summary.json' if args.finish_restored_probe else 'summary.json')
    if summary_path.exists():
        previous = json.loads(summary_path.read_text())
        print(json.dumps(previous))
        return 0 if previous.get('complete') else 1
    result = {'complete': False, 'evidence': str(root), 'protected_runtime_changed': False,
              'profiles_changed': False, 'fleet_launch_approved': False}
    try:
        archive = build / 'managed-pm-payload.tar'
        sha = hashlib.sha256()
        with archive.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(block)
        if archive.stat().st_size != operator.ARCHIVE_BYTES or sha.hexdigest() != operator.ARCHIVE_SHA:
            raise ValueError('sealed_archive_mismatch')
        payload = root / 'restored'
        if args.finish_restored_probe:
            previous = json.loads((root / 'summary.json').read_text())
            if not (previous.get('complete') is False and previous.get('child_exit_code') == 127
                    and previous.get('archive_members_validated') == 5005
                    and not previous.get('protected_runtime_changed')
                    and not (root / 'finish-summary.json').exists()):
                raise ValueError('retained_zero_execution_probe_required')
            result.update(archive_members_validated=5005, prior_failure_preserved=True,
                          prior_disposable_restore_reused=True)
            manifest = json.loads((build / 'source-manifest.json').read_text())
            for row in manifest['files']:
                if hashlib.sha256((payload / 'repo' / row['path']).read_bytes()).hexdigest() != row['sha256']:
                    raise ValueError('restored_public_source_changed')
        else:
            result['archive_members_validated'] = operator.unpack(archive, payload)
            shutil.copytree(build / 'repo', payload / 'repo')
            (payload / 'manifest.json').write_text(json.dumps({
                'repo': 'repo', 'store': 'python', 'venv': 'unused',
                'runtime': {'storePython': 'python/python-3.14.7+20260901-linux-x64/bin/python3'}}))
        home = root / ('finish-empty-home' if args.finish_restored_probe else 'empty-home');home.mkdir(mode=0o700)
        env = {'HOME': str(home), 'HERMES_HOME': str(home), 'PATH': '/usr/bin:/bin',
               'LANG': 'C.UTF-8', 'HERMES_DISABLE_LAZY_INSTALLS': '1',
               'HERMES_RUNTIME_DIR': str(payload / 'python')}
        process = subprocess.run([
            '/usr/bin/unshare', '--user', '--map-current-user', '--net', '--',
            '/usr/bin/setpriv', '--inh-caps=-all', '--ambient-caps=-all',
            '--no-new-privs', '--', str(operator.RELEASE / 'venv/bin/python'), '-I', '-B',
            '-c', PROOF, str(payload), str(operator.RELEASE)], env=env, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=120, check=False)
        prefix = 'finish-proof' if args.finish_restored_probe else 'proof'
        (root / (prefix + '.stderr')).write_bytes(process.stderr)
        (root / (prefix + '.stdout')).write_bytes(process.stdout)
        result['child_exit_code'] = process.returncode
        if process.returncode == 0 and len(process.stdout) <= 8192:
            result.update(json.loads(process.stdout))
    except Exception as exc:
        result['error_kind'] = type(exc).__name__
    with summary_path.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
