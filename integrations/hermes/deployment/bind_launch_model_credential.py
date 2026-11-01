"""Localize the existing approved ZAI credential into inactive candidates.

Only ordinary model credentials cross restricted owner pipes. No root signing,
encryption or recovery key crosses. Original profiles are never modified. No
model request occurs. Root never opens a profile tree or logs an owner packet.
"""
from __future__ import annotations
import contextlib
import copy
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import stat
import subprocess
import sys
from urllib.parse import urlsplit

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
HELPER_SHA = 'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94'
BATCH_SHA = 'f7ce4e8616a323dfecdfd02a5843811bb3812b06941ef7ac214e1de623440e3d'
PHASE = 'identity'
PHASES = {'identity','configuration','source_read','environment_publication','model_auth_normalization','preservation'}


class BindingError(RuntimeError):
    def __init__(self, phase, kind):
        super().__init__('model_binding_incomplete_preserve_evidence')
        self.phase = phase if phase in PHASES else 'identity'
        self.kind = kind if kind in {'ValueError','PermissionError','FileNotFoundError','AuthError','RuntimeError'} else 'other'


def require(value):
    if not value:
        raise ValueError('model_binding_refused')


def pointer(config):
    model = config.get('model') or {}
    url = urlsplit(model.get('base_url', ''))
    key = model.get('key_env', '')
    secrets = config.get('secrets') or {}
    require(isinstance(secrets, dict) and not any(isinstance(v, dict) and v.get('enabled') is True for v in secrets.values()))
    require(model.get('provider') == 'zai' and model.get('default') in {'GLM-5.3-Flash', 'glm-5.3-flash'}
            and url.scheme == 'https' and url.hostname == 'open.bigmodel.cn' and url.port in {None, 443}
            and not url.username and not url.password and not url.query and not url.fragment
            and isinstance(key, str) and (key in {'GLM_API_KEY', 'ZAI_API_KEY', 'Z_AI_API_KEY'}
                or re.fullmatch(r'HERMES_CUSTOM_[A-Z0-9_]{1,100}_API_KEY', key)))
    return key, url.path.rstrip('/')


def owner_file(profile, name):
    directory = os.open('/', os.O_PATH | os.O_DIRECTORY)
    try:
        for part in profile.parts[1:]:
            require(part not in {'.', '..'} and 'lswa' not in part.lower() and 'legal-social-frameworks' not in part.lower())
            child = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            require(info.st_uid in {0, os.geteuid()} and not info.st_mode & 0o022)
        require(os.fstat(directory).st_uid == os.geteuid())
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid() and before.st_nlink == 1
                    and before.st_size <= 262144 and not before.st_mode & 0o022)
            require(name not in {'.env','auth.json'} or stat.S_IMODE(before.st_mode) == 0o600)
            raw = stream.read(262145)
            after = os.fstat(stream.fileno())
            require(len(raw) == before.st_size and (before.st_ino, before.st_mtime_ns, before.st_ctime_ns)
                    == (after.st_ino, after.st_mtime_ns, after.st_ctime_ns))
            return raw
    finally:
        os.close(directory)


def auth_without_zai_metadata(value):
    result = copy.deepcopy(value)
    pool = result.get('credential_pool')
    if isinstance(pool, dict):
        pool.pop('zai', None)
    result.pop('updated_at', None)
    return result


def perform_child():
    global PHASE
    logging.disable(logging.CRITICAL)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    packet = json.loads(sys.stdin.buffer.readline(16385))
    require(set(packet) in ({'mode'}, {'mode', 'key', 'endpoint_path', 'nonce'}))
    account = pwd.getpwuid(os.geteuid())
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and not os.getgroups() and status['NoNewPrivs'].strip() == '1'
            and all(status[k].strip() == '0000000000000000' for k in ('CapEff', 'CapAmb')))
    profile = Path(account.pw_dir) / '.hermes'
    require(profile.is_absolute())
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=str(profile), HERMES_HOME=str(profile),
                      LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    os.chdir('/')
    sys.path.insert(0, str(RELEASE / 'repo'))
    import socket
    def denied(*args, **kwargs): raise RuntimeError('model_binding_network_refused')
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.getaddrinfo = denied
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        PHASE = 'configuration'
        import yaml
        from agent.secret_scope import _parse_env_text, _decode_env_bytes
        config_raw = owner_file(profile, 'config.yaml')
        config = yaml.safe_load(config_raw)
        key_env, endpoint = pointer(config)
        env_raw = owner_file(profile, '.env')
        env = _parse_env_text(_decode_env_bytes(env_raw))
        if packet['mode'] == 'read_source':
            PHASE = 'source_read'
            require(account.pw_name == 'vincentspereira' and account.pw_dir == '/home/vincentspereira')
            key = env.get(key_env)
            require(isinstance(key, str) and 16 <= len(key) <= 4096 and not any(c in key for c in '\r\n\x00'))
            require(owner_file(profile, '.env') == env_raw and owner_file(profile, 'config.yaml') == config_raw)
            value = dict(complete=True, key=key, endpoint_path=endpoint)
        else:
            require(packet['mode'] == 'bind' and re.fullmatch('ecbot_[a-f0-9]{16}', account.pw_name)
                    and account.pw_dir == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:]
                    and re.fullmatch('[a-f0-9]{32}', packet['nonce']) and packet['endpoint_path'] == endpoint)
            key = packet['key']
            require(isinstance(key, str) and 16 <= len(key) <= 4096 and not any(c in key for c in '\r\n\x00'))
            require(not env.get(key_env))  # Never replace an independently configured model key.
            before_auth = json.loads(owner_file(profile, 'auth.json'))
            PHASE = 'environment_publication'
            # Retain the original candidate environment before atomic publication.
            suffix = packet['nonce']
            original = profile / ('.env-before-model-binding-' + suffix)
            fd = os.open(original, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(env_raw); stream.flush(); os.fsync(stream.fileno())
            # Quoted dotenv syntax; validate with the native parser before writing.
            quoted = '"' + key.replace('\\', '\\\\').replace('"', '\\"') + '"'
            updated = env_raw + (b'' if not env_raw or env_raw.endswith(b'\n') else b'\n') + (key_env+'='+quoted+'\n').encode()
            parsed = _parse_env_text(_decode_env_bytes(updated))
            require(parsed.get(key_env) == key and {k:v for k,v in parsed.items() if k != key_env}
                    == {k:v for k,v in env.items() if k != key_env})
            temporary = profile / ('.env-model-binding-' + suffix)
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(updated); stream.flush(); os.fsync(stream.fileno())
            require(owner_file(profile, '.env') == env_raw)
            os.replace(temporary, profile / '.env')
            directory = os.open(profile, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fsync(directory)
            finally: os.close(directory)
            # Let native pool code reconcile only ZAI metadata before the new
            # encrypted generation. All other OAuth/provider state must match.
            from agent.secret_scope import build_profile_secret_scope, set_secret_scope, reset_secret_scope
            from hermes_cli.runtime_provider import frozen_runtime_config, resolve_runtime_provider
            PHASE = 'model_auth_normalization'
            token = set_secret_scope(build_profile_secret_scope(profile), profile_home=str(profile))
            try:
                with frozen_runtime_config(config):
                    runtime = resolve_runtime_provider(requested='zai', target_model=config['model']['default'])
                resolved = urlsplit(runtime.get('base_url', ''))
                require(runtime.get('provider') == 'zai' and runtime.get('api_key') == key
                        and resolved.scheme == 'https' and resolved.hostname == 'open.bigmodel.cn'
                        and resolved.path.rstrip('/') == endpoint)
            finally:
                reset_secret_scope(token)
            after_auth = json.loads(owner_file(profile, 'auth.json'))
            PHASE = 'preservation'
            require(auth_without_zai_metadata(before_auth) == auth_without_zai_metadata(after_auth)
                    and owner_file(profile, 'config.yaml') == config_raw and owner_file(profile, '.env') == updated)
            value = dict(complete=True, existing_model_credential_bound=True, configured_primary_route_resolved=True,
                unrelated_environment_and_oauth_preserved=True, candidate_model_auth_metadata_may_change=True,
                source_profile_changed=False, model_called=False, credentials_generated=0)
    # Source-mode stdout is a PRIVATE owner->root pipe, never a terminal/log.
    print(json.dumps(value))


def child():
    try:
        perform_child()
    except Exception as error:
        kind = type(error).__name__
        print(json.dumps(dict(complete=False, phase=PHASE, error_kind=kind if kind in {
            'ValueError','PermissionError','FileNotFoundError','AuthError','RuntimeError'} else 'other')))
        raise SystemExit(1)


def owner(helper, account, source, packet):
    require(account.pw_uid != 0 and ((set(packet) == {'mode'} and packet['mode'] == 'read_source')
            or (set(packet) == {'mode','key','endpoint_path','nonce'} and packet['mode'] == 'bind')))
    code, line = helper['owner_program'](source)
    frame = line + json.dumps(packet).encode() + b'\n'
    require(len(frame) <= 65536)
    process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', str(RELEASE / 'venv/bin/python'), '-I', '-B', '-c', code],
        input=frame, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=40, cwd='/',
        user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    require(0 < len(process.stdout) <= 8192)
    value = json.loads(process.stdout)
    if process.returncode != 0 or value.get('complete') is not True:
        raise BindingError(value.get('phase'), value.get('error_kind'))
    return value


def prepare(source, definitions):
    require(os.geteuid() == 0)
    frozen = BASE / 'operator-consolidated-provider-resume'
    helper = definitions(frozen / 'qualify_launch_isolated_accounts.py', HELPER_SHA)
    batch = definitions(frozen / 'qualify_launch_candidate_renewal.py', BATCH_SHA)
    authority = owner(helper, pwd.getpwnam('vincentspereira'), source, {'mode':'read_source'})
    require(set(authority) == {'complete','key','endpoint_path'})
    return helper, batch, authority


def bind_and_backup(row, evidence, source, context, read, write):
    helper, batch, authority = context
    # Random batch directory names are not fixed-size identities; issue a fresh
    # public nonce and record it before any candidate write.
    import uuid
    nonce = uuid.uuid4().hex
    write(evidence / 'model-binding.started.json', json.dumps(dict(nonce=nonce)).encode())
    sync_directory(evidence)
    packet = dict(mode='bind', key=authority['key'], endpoint_path=authority['endpoint_path'], nonce=nonce)
    result = owner(helper, pwd.getpwnam(row['user']), source, packet)
    require(set(result) == {'complete','existing_model_credential_bound','configured_primary_route_resolved',
        'unrelated_environment_and_oauth_preserved','candidate_model_auth_metadata_may_change',
        'source_profile_changed','model_called','credentials_generated'}
        and all(result.get(k) is True for k in ('existing_model_credential_bound','configured_primary_route_resolved',
            'unrelated_environment_and_oauth_preserved')) and result['source_profile_changed'] is False
        and result['model_called'] is False and result['credentials_generated'] == 0)
    write(evidence / 'model-binding.receipt.json', json.dumps(result).encode())
    entry = dict(user=row['user'], profile=row['home']+'/.hermes')
    generation = batch['fresh_backup'](entry, evidence, helper, read, write)
    write(evidence / 'model-profile-recovery.json', json.dumps(dict(complete=True, generation=generation)).encode())
    sync_directory(evidence)
    sync_directory(Path('/var/backups/enhanced-cognee'))


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
