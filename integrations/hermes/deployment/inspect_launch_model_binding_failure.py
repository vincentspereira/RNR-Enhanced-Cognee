"""Print only allowlisted metadata from the stopped named-runtime repair."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
SUPPORT = BASE / 'operator-named-runtime-model-binding-v2/recover_launch_graph_operator.py'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
EVIDENCE = BASE / 'operator-evidence/named-runtime-models-grkvr08r'


def require(value):
    if not value:
        raise ValueError('inspection_refused')


def read_support():
    for parent in reversed(SUPPORT.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)
    fd = os.open(SUPPORT, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                and info.st_nlink == 1 and info.st_size <= 65536)
        raw = stream.read(65537)
        require(len(raw) == info.st_size)
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == SUPPORT_SHA)
    namespace = {'__name__': 'verified_failure_inspection_support', '__file__': str(SUPPORT)}
    exec(compile(raw, '<verified-public-support>', 'exec'), namespace)
    return namespace['read_file']


def read_json(read, path):
    return json.loads(read(path, 0))


def main():
    require(os.geteuid() == 0 and sys.argv[1:] == [])
    read = read_support()
    summary = read_json(read, EVIDENCE / 'summary.json')
    require(summary.get('phase') == 'repair_model_bindings'
            and summary.get('complete') is False
            and summary.get('selected_profiles') == 40
            and summary.get('failed_profiles') == 1
            and summary.get('unattempted_profiles') == 39)
    attempted = []
    for directory in EVIDENCE.iterdir():
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or not re.fullmatch('[a-f0-9]{16}', directory.name):
            continue
        failure_path = directory / 'child.failure.json'
        if failure_path.exists():
            attempted.append(directory)
    require(len(attempted) == 1)
    per = attempted[0]
    failure = read_json(read, per / 'child.failure.json')
    allowed = {'identity', 'configuration', 'native_imports', 'configured_route_resolution',
               'native_agent_construction', 'scoped_memory_status', 'preservation'}
    require(failure.get('phase') in allowed)
    unit = read_json(read, per / 'unit.started.json').get('unit', '')
    require(re.fullmatch(r'ec-named-runtime-[a-f0-9]{32}\.service', unit))
    command = ['/usr/bin/systemctl', 'show', unit,
               '--property=LoadState,ActiveState,SubState,Result,ExecMainStatus,MainPID,ControlPID']
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=10, check=True)
    require(len(result.stdout) <= 8192)
    properties = dict(line.split('=', 1) for line in result.stdout.decode().splitlines() if '=' in line)
    require(set(properties) <= {'LoadState', 'ActiveState', 'SubState', 'Result',
                                'ExecMainStatus', 'MainPID', 'ControlPID'})
    require(properties.get('MainPID') == '0' and properties.get('ControlPID') == '0')
    receipt = read_json(read, per / 'model-binding.receipt.json')
    require(set(receipt) == {'complete', 'existing_model_credential_bound', 'configured_primary_route_resolved',
            'unrelated_environment_and_oauth_preserved', 'candidate_model_auth_metadata_may_change',
            'source_profile_changed', 'model_called', 'credentials_generated'}
            and receipt.get('complete') is True
            and receipt.get('existing_model_credential_bound') is True
            and receipt.get('configured_primary_route_resolved') is True
            and receipt.get('unrelated_environment_and_oauth_preserved') is True
            and receipt.get('source_profile_changed') is False
            and receipt.get('model_called') is False
            and receipt.get('credentials_generated') == 0)
    recovery = read_json(read, per / 'model-profile-recovery.json')
    generation = Path(recovery.get('generation', ''))
    require(recovery.get('complete') is True and generation.parent == Path('/var/backups/enhanced-cognee')
            and re.fullmatch(r'hermes_candidate_renewed_[a-f0-9]{32}\.tar\.age', generation.name))
    output = dict(
        complete=True,
        stage='retained_named_runtime_model_binding_failure',
        source_revision=BASE.name,
        failed_count=1,
        untouched_count=39,
        failure_phase=failure['phase'],
        failure_kind=failure.get('error_kind') if failure.get('error_kind') in {
            'ValueError', 'PermissionError', 'FileNotFoundError', 'AuthError', 'RuntimeError'} else 'other',
        http_status=failure.get('http_status') if type(failure.get('http_status')) is int
            and 100 <= failure['http_status'] <= 599 else None,
        model_binding_receipt_complete=receipt.get('complete') is True,
        configured_primary_route_resolved=receipt.get('configured_primary_route_resolved') is True,
        source_profile_preserved=receipt.get('source_profile_changed') is False,
        model_called=receipt.get('model_called') is True,
        encrypted_restore_qualified=recovery.get('complete') is True,
        service_state={key: properties.get(key) for key in
                       ('LoadState', 'ActiveState', 'SubState', 'Result', 'ExecMainStatus', 'MainPID', 'ControlPID')},
        candidate_generation_recorded=True,
        credentials_printed=False,
        fleet_launch_approved=False,
    )
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"failure_inspection_refused_no_secret_output"}')
        raise SystemExit(1)
