#!/usr/bin/env python3
"""Owner-run, root-staged renewal upgrade. Never issue tokens or start a job.

Stage this file, both job sources and roles.json in a new root-owned directory
first. Installation preserves old bytes and state, accepts reviewed predecessors
only, and reloads unit definitions without starting/restarting any service/timer.
"""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid

DEPLOY = Path(__file__).resolve().parent
RENEWAL_ROOT = Path('/opt/enhanced-cognee-memory/fleet-renewal')
SERVICE = Path('/etc/systemd/system/ec-hermes-memory-token-renew.service')
UNIT_NAME = 'ec-hermes-memory-token-renew'
PROVISIONER_PYTHON = Path('/opt/enhanced-cognee-memory/candidates/'
    '21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime/bin/python')
PREDECESSORS = {
    'renew_fleet_memory_tokens.py': {'ea50b522303ca415382e4339af5bb686dc511b015580be5f7108a0bbc24405fd'},
    'provision_gateway_profile_access.py': {'93679a24d12ef88f6d71d9b9733b2fcc28f2c58c6897cc20a78440618fd8ca94'},
}


def require(value, category='renewal_upgrade_refused'):
    if not value:
        raise ValueError(category)


def trusted_path(path):
    path = Path(path).absolute()
    for current in [path] + list(path.parents):
        info = current.lstat()
        require(not stat.S_ISLNK(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o022, 'untrusted_root_path')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def approved_predecessor(name, current, desired):
    require(current == desired or digest(current) in PREDECESSORS.get(name, set()),
            'unknown_predecessor')


def unit_text():
    return f'''[Unit]
Description=Renew Enhanced Cognee fleet memory tokens (7-day window)
After=network.target enhanced-cognee-api.service

[Service]
Type=oneshot
User=root
ExecStart=/usr/bin/python3 -I -B {RENEWAL_ROOT / 'renew_fleet_memory_tokens.py'}
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/home/vincentspereira/.hermes {RENEWAL_ROOT}
ProtectHome=no
UMask=0077
LimitCORE=0
'''


def legacy_unit_text():
    return '''[Unit]
Description=Renew Enhanced Cognee fleet memory tokens (7-day window)
After=network.target enhanced-cognee-api.service

[Service]
Type=oneshot
User=root
ExecStart=/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -I /opt/enhanced-cognee-memory/fleet-renewal/renew_fleet_memory_tokens.py
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/home/vincentspereira/.hermes /opt/enhanced-cognee-memory/fleet-renewal
ProtectHome=no
'''


def atomic_replace(path, body, mode=0o644):
    stage = path.with_name('.' + path.name + '-upgrade-' + uuid.uuid4().hex)
    fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stage, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    require(path.read_bytes() == body, 'readback_mismatch')


def systemctl(*args):
    result = subprocess.run(['/usr/bin/systemctl', *args], capture_output=True,
                            timeout=30, check=False)
    return result.returncode, result.stdout.decode('ascii', errors='replace').strip()


def main():
    require(sys.argv[1:] == ['--upgrade'], 'usage_upgrade_only')
    require(os.geteuid() == 0 and os.uname().nodename == 'Ubuntu-Hermes', 'owner_root_on_hermes_only')
    trusted_path(Path(__file__))
    trusted_path(Path('/usr/bin/python3').parent)
    trusted_path(Path('/usr/bin/python3').resolve())
    trusted_path(PROVISIONER_PYTHON.parent)
    trusted_path(PROVISIONER_PYTHON.resolve())
    trusted_path(PROVISIONER_PYTHON.parent.parent / 'pyvenv.cfg')
    trusted_path(RENEWAL_ROOT)
    trusted_path(SERVICE)
    raw = {}
    for name in ['provision_gateway_profile_access.py', 'renew_fleet_memory_tokens.py', 'roles.json']:
        path = DEPLOY / name
        trusted_path(path)
        raw[name] = path.read_bytes()
        require(0 < len(raw[name]) <= 65536, 'source_size')
    inventory = json.loads(raw['roles.json'])
    roles = inventory.get('profiles') if isinstance(inventory, dict) else None
    require(isinstance(inventory, dict) and set(inventory) == {'schema', 'profiles'}
            and type(inventory['schema']) is int and inventory['schema'] == 1
            and isinstance(roles, list) and len(roles) == 45
            and all(isinstance(name, str) and re.fullmatch('[a-z][a-z0-9-]{0,31}', name)
                    and not name.startswith('enhanced-cognee-test') for name in roles)
            and roles == sorted(set(roles)) and 'default' in roles, 'inventory_shape')
    old = {}
    for name in PREDECESSORS:
        target = RENEWAL_ROOT / name
        trusted_path(target)
        old[name] = target.read_bytes()
        approved_predecessor(name, old[name], raw[name])
    old_unit = SERVICE.read_text()
    require(old_unit in {legacy_unit_text(), unit_text()}, 'unknown_service_predecessor')
    if (RENEWAL_ROOT / 'roles.json').exists():
        trusted_path(RENEWAL_ROOT / 'roles.json')
        old['roles.json'] = (RENEWAL_ROOT / 'roles.json').read_bytes()
        approved_predecessor('roles.json', old['roles.json'], raw['roles.json'])
    code, active = systemctl('is-active', UNIT_NAME + '.service')
    require(active not in {'active', 'activating', 'reloading'}, 'renewal_job_must_be_idle')
    # Installation must not race a scheduled invocation. The owner first stops
    # the TIMER only; this does not revoke existing credentials or run renewal.
    _, timer_active = systemctl('is-active', UNIT_NAME + '.timer')
    require(timer_active == 'inactive', 'stop_renewal_timer_before_upgrade')
    # Verify the protected child can locate dotenv without touching a profile.
    check = subprocess.run([str(PROVISIONER_PYTHON), '-I', '-B', '-c',
        'import importlib.util; raise SystemExit(0 if importlib.util.find_spec("dotenv") else 1)'],
        capture_output=True, timeout=30, check=False)
    require(check.returncode == 0, 'protected_runtime_dotenv_unavailable')
    lock_fd = os.open(RENEWAL_ROOT / 'upgrade.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        backup = RENEWAL_ROOT / ('before-audit-upgrade-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8])
        backup.mkdir(mode=0o700)
        for name, body in old.items():
            atomic_replace(backup / name, body, 0o600)
        atomic_replace(backup / 'service.unit', old_unit.encode('ascii'), 0o600)
        # Inventory first, then job, then unit; a mid-install invocation fails
        # closed. Timer remains stopped until the owner reviews the receipt.
        for name in ['roles.json', 'provision_gateway_profile_access.py', 'renew_fleet_memory_tokens.py']:
            atomic_replace(RENEWAL_ROOT / name, raw[name])
        atomic_replace(SERVICE, unit_text().encode('ascii'))
        code, _ = systemctl('daemon-reload')
        require(code == 0, 'daemon_reload_failed_timer_remains_stopped')
        _, command = systemctl('show', UNIT_NAME + '.service', '-p', 'ExecStart', '--value')
        require('/usr/bin/python3 -I -B /opt/enhanced-cognee-memory/fleet-renewal/' in command,
                'loaded_unit_mismatch_timer_remains_stopped')
        print(json.dumps({'complete': True, 'installed_not_exercised': True,
            'source_hashes': {name: digest(body) for name, body in raw.items()},
            'backup': str(backup), 'inventory_profiles': len(roles),
            'credentials_issued': 0, 'renewal_ran': False, 'timer_started': False,
            'next_owner_action': 'Review receipt, then enable timer at an approved window; expiry catch-up may invoke renewal.'}, sort_keys=True))
        return 0
    finally:
        os.close(lock_fd)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        print(json.dumps({'complete': False, 'category': 'renewal_upgrade_refused',
                          'error_kind': type(error).__name__,
                          'timer_must_remain_stopped': True}), flush=True)
        raise SystemExit(1)
