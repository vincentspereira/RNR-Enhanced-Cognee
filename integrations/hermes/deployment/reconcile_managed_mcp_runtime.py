#!/usr/bin/env python3
"""Reconcile the retained partial managed-MCP-runtime installation.

The retained v1 attempt published every archive member and the merged facts,
then failed its restricted-identity proof: the operator umask stripped the
group/other bits from directories created by mkdir, leaving payload
directories at 0700, so the UID-992 proof child could not read
pm-runtime/pm-runtime.json. This helper verifies the whole live tree against
the sealed archive, corrects only payload directory modes to their archived
values, reruns the same restricted-identity proof with captured output, and
records a v2 receipt. The v1 artifact and every retained failure stay
untouched. No service, profile, credential, policy or bot is changed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile

RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARCHIVE = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/.archive/managed-mcp-build-vyy1g3gk/managed-pm-payload.tar')
ARCHIVE_BYTES = 464097280
ARCHIVE_SHA = '68a0325fec51b2922b379cec51b8d80a202f2e7783e3c8561154d8a9eb52f521'
V1_HELPER = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment/install_managed_mcp_runtime.py')
V1_SHA = 'a877fd6dd3688ea77d42ae02c94b060340b5a3c217f85df85ec035f987822711'
V1_ARTIFACT = BASE / 'operator-managed-mcp-runtime-v1'
V2_ARTIFACT = BASE / 'operator-managed-mcp-runtime-v2'
UNPUBLISHED = {'python/.install.lock'}


def require(value):
    if not value:
        raise ValueError('managed_mcp_runtime_reconciliation_refused')


def load_v1():
    raw = V1_HELPER.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == V1_SHA)
    spec = importlib.util.spec_from_file_location('install_v1', V1_HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_rows(v1):
    """Re-admit and digest the sealed archive exactly as publication did."""
    digest = hashlib.sha256()
    with ARCHIVE.open('rb') as stream:
        size = 0
        for block in iter(lambda: stream.read(1 << 20), b''):
            size += len(block)
            digest.update(block)
    require(size == ARCHIVE_BYTES and digest.hexdigest() == ARCHIVE_SHA)
    with tarfile.open(ARCHIVE, 'r:') as archive:
        rows = v1.validate_archive(archive)
        contents = {}
        for name, member in rows.items():
            if member.isfile() and name not in UNPUBLISHED:
                source = archive.extractfile(member)
                require(source is not None)
                data = source.read()
                require(len(data) == member.size)
                contents[name] = hashlib.sha256(data).hexdigest()
    return rows, contents


def plan_mode_corrections(rows, observed_modes):
    """Pure decision core: archive rows plus observed dir modes -> fixes."""
    corrections = []
    for name, member in sorted(rows.items()):
        if member.isdir() and name not in UNPUBLISHED:
            require(name in observed_modes)
            if observed_modes[name] != member.mode:
                corrections.append((name, member.mode))
    return corrections


def merged_facts_bytes(before: dict, staged: dict) -> bytes:
    """Pure merge core: original facts plus the staged python/uv packages."""
    require(staged.get('schema') == 1 and set(staged['packages']) == {'uv', 'python'})
    merged = json.loads(json.dumps(before))
    merged['packages'].update(staged['packages'])
    return (json.dumps(merged, indent=2, sort_keys=True) + '\n').encode()


def expected_facts(v1):
    """Reconstruct the merged facts bytes the v1 installer published."""
    before = json.loads(v1.public_read(V1_ARTIFACT / 'facts.before.json'))
    with tarfile.open(ARCHIVE, 'r:') as archive:
        staged = json.loads(archive.extractfile('python/facts.json').read())
    return merged_facts_bytes(before, staged)


def live_state(rows):
    """Verify every published member against the archive; collect dir modes."""
    observed_modes, hashes = {}, {}
    for name, member in sorted(rows.items()):
        if name in UNPUBLISHED:
            continue
        path = RELEASE / name
        info = path.lstat()
        require(info.st_uid == 0 and info.st_gid == 0)
        if member.isdir():
            require(stat.S_ISDIR(info.st_mode))
            observed_modes[name] = stat.S_IMODE(info.st_mode)
        elif member.isfile():
            require(stat.S_ISREG(info.st_mode) and info.st_size == member.size)
            require(stat.S_IMODE(info.st_mode) == member.mode)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            require(member.issym() and stat.S_ISLNK(info.st_mode)
                    and os.readlink(path) == member.linkname)
    expected = {name for name in rows if name not in UNPUBLISHED}
    for top in ('python', 'pm-runtime'):
        for dirpath, dirnames, filenames in os.walk(RELEASE / top):
            for entry in dirnames + filenames:
                relative = (Path(dirpath) / entry).relative_to(RELEASE).as_posix()
                require(relative in expected)
    return observed_modes, hashes


def proof(home: Path, v1, artifact: Path):
    """The v1 restricted-identity proof, with its output captured this time."""
    home.mkdir(mode=0o700)
    os.chown(home, 992, 984)
    result = subprocess.run(
        ['/usr/bin/unshare', '--net', '--', '/usr/bin/setpriv', '--reuid=992', '--regid=984',
         '--clear-groups', '--no-new-privs', '--inh-caps=-all', '--ambient-caps=-all', '--',
         str(RELEASE / 'venv/bin/python'), '-I', '-B', '-c', v1.PROOF, str(RELEASE)],
        env={'HOME': str(home), 'HERMES_HOME': str(home), 'PATH': '/usr/bin:/bin',
             'LANG': 'C.UTF-8', 'HERMES_DISABLE_LAZY_INSTALLS': '1',
             'PYTHONDONTWRITEBYTECODE': '1'},
        stdin=subprocess.DEVNULL, capture_output=True, cwd='/', timeout=120, check=False)
    (artifact / 'proof-stdout.txt').write_text(result.stdout[:8192].decode('utf-8', 'replace'))
    (artifact / 'proof-stderr.txt').write_text(result.stderr[-65536:].decode('utf-8', 'replace'))
    (artifact / 'proof-returncode.txt').write_text(str(result.returncode) + '\n')
    require(result.returncode == 0 and len(result.stdout) <= 8192)
    value = json.loads(result.stdout)
    require(value.get('complete') is True
            and value.get('native_managed_launcher_selection_qualified') is True)
    return value


def main():
    require(os.geteuid() == 0 and sys.argv[1:] == [])
    os.umask(0o022)
    summary_path = V2_ARTIFACT / 'summary.json'
    if summary_path.exists():
        value = json.loads(summary_path.read_text())
        print(json.dumps(value))
        return 0 if value.get('complete') else 1
    v1 = load_v1()
    retained = json.loads(v1.public_read(V1_ARTIFACT / 'summary.json'))
    require(retained.get('complete') is False
            and retained.get('checkpoint') == 'restricted_native_pm_proof'
            and retained.get('archive_members_validated') == 5005
            and retained.get('managed_launcher_packaging_changed') is True)
    v1.protected(RELEASE, directory=True)
    v1.no_active_candidates()
    require((RELEASE / 'pm-runtime/pm-runtime.json').is_file())
    require(not (RELEASE / 'python/.install.lock').exists())
    require((RELEASE / 'python/facts.json').read_bytes() == expected_facts(v1))
    V2_ARTIFACT.mkdir(mode=0o700)
    result = {'complete': False, 'evidence': str(V2_ARTIFACT),
              'reconciled_from': str(V1_ARTIFACT), 'source_revision': BASE.name,
              'backend_runtime_changed': False, 'services_restarted': False,
              'profiles_changed': False, 'credentials_issued': 0,
              'keys_read': False, 'existing_interpreter_or_source_replaced': False,
              'native_mcp_server_binding_qualified': False,
              'fleet_launch_approved': False}
    try:
        result['checkpoint'] = 'archive_and_live_tree_verification'
        rows, contents = archive_rows(v1)
        observed_modes, hashes = live_state(rows)
        require(hashes == contents)
        corrections = plan_mode_corrections(rows, observed_modes)
        result['checkpoint'] = 'directory_mode_correction'
        result['directories_corrected'] = len(corrections)
        for name, mode in corrections:
            os.chmod(RELEASE / name, mode)
        require(not plan_mode_corrections(rows, live_state(rows)[0]))
        result['checkpoint'] = 'restricted_native_pm_proof'
        home = Path('/var/tmp') / ('ec-managed-pm-reconcile-' + os.urandom(12).hex())
        result['proof_home'] = str(home)
        result['proof'] = proof(home, v1, V2_ARTIFACT)
        result.update(complete=True, checkpoint='complete',
                      public_archive_sha256=ARCHIVE_SHA,
                      helper_reused_sha256=V1_SHA)
    except Exception as exc:
        result.update(category='managed_pm_reconciliation_incomplete_preserve_evidence_no_automatic_retry',
                      error_kind=type(exc).__name__)
    with summary_path.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'complete': False, 'category': 'managed_pm_reconciliation_preflight_refused_preserve_evidence',
                          'error_kind': type(exc).__name__, 'fleet_launch_approved': False}))
        raise SystemExit(1)
