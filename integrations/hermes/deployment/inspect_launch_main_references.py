"""Owner-only configuration reference checks; no profile code is executed.

Return fixed classifications and digests only. Never follow a configured path,
import a profile plugin, start an MCP server or print a configuration value.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import sys
from urllib.parse import urlsplit


SECTIONS = {'model', 'memory', 'gateway', 'platforms', 'mcp_servers', 'browser', 'terminal', 'agent'}
REFERENCE_KINDS = {'original_owner_home', 'restored_profile', 'pinned_runtime', 'other_absolute',
                   'home_relative', 'windows_path', 'excluded_project'}
PHASE = 'identity'


def require(value):
    if not value:
        raise ValueError('main_reference_inspection_refused')


def classify(config, profile, original_home):
    """Inspect values in memory, retaining no raw values, keys or target paths."""
    require(isinstance(config, dict) and isinstance(profile, Path) and isinstance(original_home, Path))
    counts = dict.fromkeys(sorted(REFERENCE_KINDS), 0)
    sections = {key: dict.fromkeys(sorted(REFERENCE_KINDS), 0) for key in sorted(SECTIONS | {'other'})}
    visited = set()
    entries = [0]

    def walk(value, section, depth=0):
        entries[0] += 1
        require(entries[0] <= 10000 and depth <= 32)
        if isinstance(value, (dict, list)):
            require(id(value) not in visited)
            visited.add(id(value))
            try:
                for item in value.values() if isinstance(value, dict) else value:
                    walk(item, section, depth + 1)
            finally:
                visited.remove(id(value))
        elif isinstance(value, str):
            kind = None
            if value.startswith(('/', '~/')) or re.match(r'^[A-Za-z]:[\\/]', value):
                if any('lswa' in part.lower() or 'legal-social-frameworks' in part.lower()
                       for part in value.replace('\\', '/').split('/')):
                    kind = 'excluded_project'
                elif value.startswith('/mnt/') or re.match(r'^[A-Za-z]:[\\/]', value):
                    kind = 'windows_path'
                elif value.startswith('~/'):
                    kind = 'home_relative'
                elif Path(value).is_relative_to(profile):
                    kind = 'restored_profile'
                elif Path(value).is_relative_to(original_home):
                    kind = 'original_owner_home'
                elif value.startswith('/opt/hermes-runtime/'):
                    kind = 'pinned_runtime'
                else:
                    kind = 'other_absolute'
            if kind:
                counts[kind] += 1
                sections[section][kind] += 1

    for key, value in config.items():
        walk(value, key if key in SECTIONS else 'other')
    model, gateway, memory = (config.get(key) or {} for key in ('model', 'gateway', 'memory'))
    require(all(isinstance(value, dict) for value in (model, gateway, memory)))
    endpoint = urlsplit(model.get('base_url', ''))
    model_ok = (model.get('provider') == 'zai' and str(model.get('default', '')).lower() == 'glm-5.3-flash'
                and endpoint.scheme == 'https' and endpoint.hostname == 'open.bigmodel.cn'
                and endpoint.path.rstrip('/') == '/api/coding/paas/v4'
                and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment
                and endpoint.port in {None, 443})
    mcp, platforms = config.get('mcp_servers') or {}, config.get('platforms') or {}
    require(isinstance(mcp, dict) and isinstance(platforms, dict) and len(mcp) <= 128 and len(platforms) <= 128)
    unresolved = sum(counts[k] for k in REFERENCE_KINDS - {'restored_profile', 'pinned_runtime'})
    return dict(reference_counts=counts, reference_sections=sections, unresolved_reference_count=unresolved,
                configured_model_matches=model_ok, enhanced_memory_selected=memory.get('provider') == 'enhanced_cognee',
                multiplex_enabled=gateway.get('multiplex_profiles') is True,
                mcp_definition_count=len(mcp), platform_definition_count=len(platforms),
                reference_targets_followed=False, profile_code_executed=False, raw_values_returned=False,
                reference_coverage_qualified=False)


def open_profile(profile, uid):
    require(uid != 0 and profile.is_absolute() and '..' not in profile.parts)
    descriptor = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for part in profile.parts[1:]:
            require('lswa' not in part.lower() and 'legal-social-frameworks' not in part.lower())
            child = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            info = os.fstat(descriptor)
            require(info.st_uid in {0, uid} and not info.st_mode & 0o022)
        require(os.fstat(descriptor).st_uid == uid)
        result = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        return result
    finally:
        os.close(descriptor)


def read_at(directory, name, uid):
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid == uid and before.st_nlink == 1
                and before.st_size <= 262144 and not before.st_mode & 0o022
                and (name == 'config.yaml' or not before.st_mode & 0o077))
        raw = stream.read(262145)
        after = os.fstat(stream.fileno())
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        fields = ('st_dev', 'st_ino', 'st_uid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(len(raw) == before.st_size and all(getattr(before, k) == getattr(after, k) for k in fields)
                and (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino))
        return raw


def inspect(profile, uid):
    global PHASE
    require(uid == os.geteuid() and uid > 0)
    PHASE = 'directory_open'
    directory = open_profile(profile, uid)
    try:
        PHASE = 'configuration_read'
        raw = read_at(directory, 'config.yaml', uid)
        import yaml
        PHASE = 'configuration_classification'
        result = classify(yaml.safe_load(raw), profile, Path('/home/vincentspereira'))
        # Configuration comparison needs no environment or OAuth file read.
        fingerprints = {'config.yaml': hashlib.sha256(raw).hexdigest()}
        PHASE = 'configuration_preservation'
        require(read_at(directory, 'config.yaml', uid) == raw)
        result.update(complete=True, fingerprints=fingerprints, source_files_written=False,
                      model_called=False, credentials_issued=0)
        return result
    finally:
        os.close(directory)


def child():
    packet = json.loads(sys.stdin.buffer.readline(8193))
    require(set(packet) == {'mode', 'profile'} and packet['mode'] in {'source', 'restored'})
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid > 0 and not os.getgroups() and fields['NoNewPrivs'].strip() == '1'
            and all(fields[k].strip() == '0000000000000000' for k in ('CapEff', 'CapAmb')))
    profile = Path(packet['profile'])
    if packet['mode'] == 'source':
        require(account.pw_name == 'vincentspereira' and profile == Path(account.pw_dir) / '.hermes')
    else:
        require(re.fullmatch('ecbot_[a-f0-9]{16}', account.pw_name)
                and account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:]
                and profile.parent == Path(account.pw_dir)
                and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}', profile.name))
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=account.pw_dir, LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    os.chdir('/')
    def denied(*args, **kwargs):
        raise ValueError('reference_inspection_network_refused')
    socket.socket.connect = socket.socket.connect_ex = socket.getaddrinfo = denied
    print(json.dumps(inspect(profile, account.pw_uid), sort_keys=True))
