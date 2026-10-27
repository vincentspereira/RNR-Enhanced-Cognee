"""Restricted owner operations for the consolidated inactive launch batch.

Public code is read only from the frozen root package with exact hashes. Root
keys never enter packets. Candidate data and raw library output stay private.
"""
from __future__ import annotations
import contextlib
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

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-launch-completion-batch-v2'
PROVIDER = '/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659'
MAX_ARCHIVE = 600 * 1024 * 1024
MAX_CIPHER = 650 * 1024 * 1024
PHASE = 'identity'
PINS = {
    'provision_pilot_access.py': 'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e',
    'fleet_credential_policy.py': '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102',
    'main_candidate_environment.py': '1e9e463b524639a28faa1ef17393c8dd16afe2b06cf2c632c8aeb0ebde922bb4',
    'main_candidate_configuration.py': 'f2f4ae7cb317c9cb914ceb5bc690b6612d9290fb3161e147a2d810813e62b68f',
    'model_delivery_readiness.py': '1352ab6d2148b169bfdf9c72f3fca4e19ce878d292e0d889d4fffd86ed850eed',
    'main_memory_profile_recovery.py': '6b69674dacfcedafc6bcdad0a11e353265a19705b950e1ca3a492351d5cf78b5',
    'capture_main_operational_profile_v3.py': 'e32266d8a797eeaca2a32247f861cbf725341cce960eeb73d3db57987c99c106',
    'prepare_launch_candidate_provider_v2.py': 'e54da1d75c89677fe01cd173c965367e2b5ca47fbb7a2cbff4d9ed766d13fc67',
    'bind_launch_model_route.py': 'edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52',
    'qualify_launch_gateway_renewal_v2.py': 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2',
    'renew_pilot_access.py': '8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567',
    'fleet_credential_lifecycle.py': 'f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62',
    'expired_candidate_recovery.py': 'ac9a1db18ef021475ca41b8f3ff3fe52aa6ce108ae37a640ec96753ff1b8ebbb',
    'qualify_launch_candidate_native_unit.py': 'f085298baabc75b801ff82a79fcde97244a129b87146c87c48f72c5f7da0acd0',
    'observe_launch_native_runtime.py': '2488f9255af9cefd9230a22eae062c49c845e7a57c366da628937f2a50e7af27',
    'complete_launch_named_runtime.py': '6dbf807c3c4eb4cc9da1834fc3cfc13747f9b7a456997a0e66ce076e6b5fe625',
    'launch_fleet_reload_owner.py': '5b6c936be7ace4792a9e0512a35551b53466c75b95d7331dafd6d330ad5594f5',
}


def require(value):
    if not value:
        raise ValueError('launch_completion_owner_refused')


def public(name):
    raw = (ARTIFACT / name).read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == PINS[name])
    scope = {'__name__': 'verified_completion_owner_support'}
    exec(compile(raw, '<verified-completion-support>', 'exec'), scope)
    return scope


def identity(entry):
    return dict(sub=entry['subject'], agent_id=entry['agent_id'], tenant=entry['tenant'],
                project_id=entry['project_id'], roles=['api_client'], capture_policy='selected')


def guard(entry):
    public('fleet_credential_policy.py')['validate'](dict(schema=1, profiles=[entry]))
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid > 0 and account.pw_gid > 0 and account.pw_uid == entry['uid'] and account.pw_name == entry['user']
            and re.fullmatch('ecbot_[a-f0-9]{16}', account.pw_name) and entry['enabled'] is False
            and account.pw_dir == entry['home'] == '/var/lib/enhanced-cognee-profiles/' + account.pw_name[6:]
            and entry['profile'] == str(Path(account.pw_dir) / '.hermes') and not os.getgroups()
            and os.getgid() == os.getegid() == account.pw_gid and account.pw_shell == '/usr/sbin/nologin'
            and fields['NoNewPrivs'].strip() == '1'
            and all(fields[name].strip() == '0000000000000000' for name in ('CapEff', 'CapAmb')))
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=account.pw_dir, LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    os.chdir('/')
    return account


def main_configuration(packet, account):
    global PHASE
    require(set(packet) == {'mode', 'entry', 'candidate', 'config_sha256', 'bundle', 'model_key', 'id'})
    entry = packet['entry']; home = Path(account.pw_dir); old = Path(packet['candidate'])
    require(old.parent == home and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}', old.name)
            and re.fullmatch('[a-f0-9]{32}', packet['id']) and re.fullmatch('[a-f0-9]{64}', packet['config_sha256']))
    key = packet['model_key']
    require(isinstance(key, str) and 16 <= len(key) <= 4096 and not any(char in key for char in '\r\n\x00'))
    core = public('provision_pilot_access.py'); core['IDENTITY'] = identity(entry)
    fix = public('prepare_launch_candidate_provider_v2.py')
    core['open_directory'] = fix['open_candidate_directory']
    PHASE = 'main_configuration_preflight'
    descriptor = core['open_directory'](old, {0, account.pw_uid})
    try:
        saved = {name: core['read_private_at'](descriptor, name, account.pw_uid)[0]
                 for name in ('config.yaml', '.env', 'auth.json')}
        require(hashlib.sha256(saved['config.yaml']).hexdigest() == packet['config_sha256'])
        require(not os.path.lexists(old / 'enhanced_cognee.json') and not os.path.lexists(old / 'plugins/enhanced_cognee'))
        import yaml
        original_config = yaml.safe_load(saved['config.yaml'])
        updated_config = public('main_candidate_configuration.py')['transform'](original_config, home)
        route = public('bind_launch_model_route.py')
        key_name, endpoint = route['pointer'](updated_config)
        require(endpoint == '/api/coding/paas/v4')
        PHASE = 'main_environment_preflight'
        updated_env = core['prepare_environment'](saved['.env'], packet['bundle']['token'])
        updated_env = public('main_candidate_environment.py')['prepare'](updated_env, key_name, key, endpoint)
        serialized = yaml.safe_dump(updated_config, sort_keys=False).encode()
        require(yaml.safe_load(serialized) == updated_config)
        require(all(core['read_private_at'](descriptor, name, account.pw_uid)[0] == raw for name, raw in saved.items()))
    finally:
        os.close(descriptor)
    PHASE = 'main_placeholder_preflight'
    placeholder = home / '.hermes'
    descriptor = core['open_directory'](placeholder, {0, account.pw_uid})
    try:
        require(set(os.listdir(descriptor)) == {'.isolation-marker'}
                and core['read_private_at'](descriptor, '.isolation-marker', account.pw_uid)[0] == b'invented-isolation-marker-v1')
    finally:
        os.close(descriptor)
    public('qualify_launch_gateway_renewal_v2.py')['network_guard']()
    core['qualify_access'](packet['bundle'])
    PHASE = 'main_candidate_publication'
    fix['rename_new'](placeholder, home / ('.hermes-before-main-integration-' + packet['id']))
    fix['rename_new'](old, placeholder)
    home_descriptor = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(home_descriptor)
    finally: os.close(home_descriptor)
    descriptor = core['open_directory'](placeholder, {0, account.pw_uid})
    try:
        for name in ('.env', 'config.yaml'):
            require(core['read_private_at'](descriptor, name, account.pw_uid)[0] == saved[name])
            core['create_private_at'](descriptor, name + '-before-main-' + packet['id'], saved[name])
        core['create_private_at'](descriptor, '.main-integration-' + packet['id'] + '.json',
            json.dumps(dict(prepared=True, config_before_sha256=packet['config_sha256'])).encode())
        os.fsync(descriptor)
        for name, raw in (('.env', updated_env), ('config.yaml', serialized)):
            candidate = name + '-main-' + packet['id']
            core['create_private_at'](descriptor, candidate, raw)
            os.replace(candidate, name, src_dir_fd=descriptor, dst_dir_fd=descriptor)
        core['create_private_at'](descriptor, 'enhanced_cognee.json', json.dumps(dict(
            base_url='http://127.0.0.1:28080', capture_policy='selected', include_shared=True)).encode())
        plugins = placeholder / 'plugins'
        if not os.path.lexists(plugins): plugins.mkdir(mode=0o700)
        info = plugins.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == account.pw_uid and not info.st_mode & 0o077)
        (plugins / 'enhanced_cognee').symlink_to(PROVIDER)
        workspace = placeholder / 'workspace'
        if not os.path.lexists(workspace): workspace.mkdir(mode=0o700)
        info = workspace.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == account.pw_uid and not info.st_mode & 0o077)
        require(core['read_private_at'](descriptor, 'auth.json', account.pw_uid)[0] == saved['auth.json']
                and core['read_private_at'](descriptor, '.env', account.pw_uid)[0] == updated_env
                and core['read_private_at'](descriptor, 'config.yaml', account.pw_uid)[0] == serialized)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    PHASE = 'main_scoped_status'
    core['qualify_access'](packet['bundle'])
    return dict(complete=True, main_candidate_provider_configured=True, main_filesystem_reference_rebound=True,
        mcp_definitions_preserved=4, unrelated_settings_and_oauth_preserved=True,
        main_scope_authenticated=True, source_profiles_changed=False, chat_model_called=False,
        platform_adapters_started=0, actual_profile_admission_qualified=False, fleet_launch_approved=False)


def child():
    global PHASE
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    logging.disable(logging.CRITICAL)
    head = sys.stdin.buffer.readline(65537)
    require(0 < len(head) <= 65536)
    packet = json.loads(head)
    require(isinstance(packet, dict) and packet.get('mode') in {
        'configure_main', 'capture_main', 'restore_main', 'credential_metadata', 'credential_publish', 'recover_expired', 'gateway',
        'main_api_probe', 'peer_history_denial', 'main_probe_withdrawal'})
    account = guard(packet['entry'])
    body = b''
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        if packet['mode'] == 'configure_main':
            value = main_configuration(packet, account)
        elif packet['mode'] in {'credential_metadata', 'credential_publish', 'recover_expired', 'gateway'}:
            value = credential_operation(packet, account)
        elif packet['mode'] in {'main_api_probe', 'peer_history_denial', 'main_probe_withdrawal'}:
            PHASE = packet['mode']
            value = memory_probe(packet, account)
        else:
            core = public('capture_main_operational_profile_v3.py')
            recovery = public('main_memory_profile_recovery.py')
            if packet['mode'] == 'capture_main':
                require(set(packet) == {'mode', 'entry', 'recipient'} and re.fullmatch('age1[0-9a-z]{20,100}', packet['recipient']))
                PHASE = 'main_candidate_capture'
                archive, receipt = recovery['capture'](core, Path(packet['entry']['profile']))
                PHASE = 'main_candidate_encryption'
                encrypted = subprocess.run(['/usr/local/bin/age', '--encrypt', '--recipient', packet['recipient']],
                    input=archive, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=90, check=True)
                body = encrypted.stdout
                require(0 < len(body) <= MAX_CIPHER and body.startswith(b'age-encryption.org/v1\n'))
                value = dict(complete=True, receipt=receipt, ciphertext_bytes=len(body))
            else:
                require(set(packet) == {'mode', 'entry', 'archive_bytes'} and type(packet['archive_bytes']) is int
                        and 0 < packet['archive_bytes'] <= MAX_ARCHIVE)
                PHASE = 'main_candidate_restore'
                archive = sys.stdin.buffer.read(packet['archive_bytes'] + 1)
                require(len(archive) == packet['archive_bytes'])
                destination, receipt = recovery['restore'](core, archive)
                public('qualify_launch_gateway_renewal_v2.py')['network_guard']()
                issuer = public('provision_pilot_access.py'); issuer['IDENTITY'] = identity(packet['entry'])
                issuer['open_directory'] = public('prepare_launch_candidate_provider_v2.py')['open_candidate_directory']
                descriptor = issuer['open_directory'](Path(destination), {0, account.pw_uid})
                try:
                    token = public('renew_pilot_access.py')['environment'](issuer,
                        issuer['read_private_at'](descriptor, '.env', account.pw_uid)[0])
                    public('fleet_credential_lifecycle.py')['accepted_status'](issuer, token)
                finally: os.close(descriptor)
                receipt = dict(receipt, restored_scope_authenticated=True)
                value = dict(complete=True, destination=destination, receipt=receipt)
    sys.stdout.buffer.write(json.dumps(value, sort_keys=True).encode() + b'\n' + body)


def credential_operation(packet, account):
    global PHASE
    entry = packet['entry']; mode = packet['mode']
    if mode == 'gateway':
        require(set(packet) == {'mode', 'entry', 'id', 'model_key_digest'} and re.fullmatch('[a-f0-9]{32}', packet['id'])
                and isinstance(packet['model_key_digest'], str) and re.fullmatch('[a-f0-9]{64}', packet['model_key_digest']))
        PHASE = 'retained_gateway_reload'
        return public('launch_fleet_reload_owner.py')['run'](packet, public)
    require(set(packet) == ({'mode', 'entry'} if mode == 'credential_metadata' else {'mode', 'entry', 'bundle'}))
    core = public('provision_pilot_access.py'); core['IDENTITY'] = identity(entry)
    core['open_directory'] = public('prepare_launch_candidate_provider_v2.py')['open_candidate_directory']
    renewal = public('renew_pilot_access.py'); lifecycle = public('fleet_credential_lifecycle.py')
    public('qualify_launch_gateway_renewal_v2.py')['network_guard']()
    PHASE = mode
    descriptor = core['open_directory'](Path(entry['profile']), {0, account.pw_uid})
    try:
        if mode == 'credential_metadata':
            token = renewal['environment'](core, core['read_private_at'](descriptor, '.env', account.pw_uid)[0])
            claims = renewal['token_claims'](core, token)
            import time
            seconds = claims['exp'] - int(time.time())
            code = core['api_status'](token)[0]
            require(code == (401 if seconds <= 0 else 200))
            if seconds > 0: lifecycle['accepted_status'](core, token)
            return dict(complete=True, expired=seconds <= 0, token_iat=claims['iat'],
                        token_sha256=hashlib.sha256(token.encode()).hexdigest(), scope_shape_verified=True,
                        api_status_http=code, credentials_changed=False)
        import fcntl
        lock = os.open('.cognee-renewal.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=descriptor)
        try:
            core['read_private_fd'](lock, account.pw_uid)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if mode == 'recover_expired':
                return public('expired_candidate_recovery.py')['recover'](core, renewal, lifecycle,
                    descriptor, packet['bundle'], account.pw_uid, entry)
            return lifecycle['publish'](core, renewal, descriptor, packet['bundle'], account.pw_uid)
        finally: os.close(lock)
    finally: os.close(descriptor)


def memory_probe(packet, account):
    mode = packet['mode']; entry = packet['entry']
    expected = {'mode', 'entry', 'id', 'peer_profile'} if mode == 'main_api_probe' else (
        {'mode', 'entry', 'record_id', 'token'} if mode == 'peer_history_denial' else {'mode', 'entry', 'record_id', 'id'})
    require(set(packet) == expected)
    if mode != 'peer_history_denial': require(re.fullmatch('[a-f0-9]{32}', packet['id']))
    if mode != 'main_api_probe': require(isinstance(packet['record_id'], str) and re.fullmatch('[A-Za-z0-9_-]{1,64}', packet['record_id']))
    if mode == 'main_api_probe':
        peer = Path(packet['peer_profile'])
        require(peer.name == '.hermes' and peer.parent.parent == Path('/var/lib/enhanced-cognee-profiles')
                and re.fullmatch('[a-f0-9]{16}', peer.parent.name) and peer != Path(entry['profile']))
        for path in (peer / '.env', Path('/etc/enhanced-cognee/operator.json'), Path('/etc/enhanced-cognee/age-recovery-identity.txt')):
            try: descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except PermissionError: continue
            else: os.close(descriptor); require(False)
    core = public('provision_pilot_access.py'); core['IDENTITY'] = identity(entry)
    core['open_directory'] = public('prepare_launch_candidate_provider_v2.py')['open_candidate_directory']
    renewal = public('renew_pilot_access.py')
    if mode == 'peer_history_denial':
        token = packet['token']; renewal['token_claims'](core, token)
    else:
        descriptor = core['open_directory'](Path(entry['profile']), {0, account.pw_uid})
        try: token = renewal['environment'](core, core['read_private_at'](descriptor, '.env', account.pw_uid)[0])
        finally: os.close(descriptor)
    public('qualify_launch_gateway_renewal_v2.py')['network_guard']()
    public('fleet_credential_lifecycle.py')['accepted_status'](core, token)
    raw = (Path(PROVIDER) / 'client.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == '8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64')
    transport = {'__name__': 'verified_main_candidate_client'}
    exec(compile(raw, '<verified-main-candidate-client>', 'exec'), transport)
    client = transport['MemoryClient']('http://127.0.0.1:28080', token)
    if mode == 'peer_history_denial':
        try: client.request('GET', '/v1/memories/' + packet['record_id'] + '/history')
        except Exception as error: require(getattr(error, 'status_code', None) == 404)
        else: require(False)
        return dict(complete=True, peer_history_denied=True, peer_credential_scope_authenticated=True)
    nonce = packet['id']; cedar, birch = 'MainCedar-' + nonce[:8], 'MainBirch-' + nonce[:8]
    text = 'Invented main qualification ' + nonce + ': ' + cedar + ' references ' + birch + '.'
    if mode == 'main_api_probe':
        status = client.request('GET', '/v1/memories/status'); require(status.get('active_records') == 0)
        row = client.request('POST', '/v1/memories', dict(content=text, idempotency_key='main-batch-' + nonce,
            knowledge_links=[dict(subject=cedar, predicate='references', object=birch, span_start=0, span_end=len(text))]))
        ident = row.get('id'); require(isinstance(ident, str) and re.fullmatch('[A-Za-z0-9_-]{1,64}', ident) and row.get('version') == 1)
        require(client.request('GET', '/v1/memories/' + ident).get('content') == text)
        import time
        deadline = time.monotonic() + 40
        while True:
            recall = client.request('POST', '/v1/memories/recall', dict(query=cedar + ' ' + birch, limit=5, include_shared=False))
            graph = client.request('POST', '/v1/memories/connections', dict(entity=cedar, depth=1))
            if recall.get('vector_index') == 'queried' and any(row.get('id') == ident for row in recall.get('results', [])) and graph.get('paths'): break
            require(time.monotonic() < deadline); time.sleep(2)
        return dict(complete=True, record_id=ident, own_scope_write_read_qualified=True,
                    actual_semantic_graph_qualified=True, main_os_peer_and_operator_denials_qualified=True)
    ident = packet['record_id']
    row = client.request('GET', '/v1/memories/' + ident)
    require(row.get('version') == 1 and row.get('content') == text)
    changed = client.request('POST', '/v1/memories/' + ident + '/retract', dict(expected_version=1))
    require(changed.get('state') == 'retracted' and changed.get('version') == 2)
    history = client.request('GET', '/v1/memories/' + ident + '/history')
    require(history.get('record_state') == 'retracted' and sorted(row['version'] for row in history.get('versions', [])) == [1, 2])
    public('model_delivery_readiness.py')['wait'](lambda: client.request('GET', '/v1/memories/status'), identity(entry))
    require(client.request('POST', '/v1/memories/recall', dict(query=cedar + ' ' + birch, limit=5, include_shared=False)).get('results') == [])
    return dict(complete=True, invented_record_retracted_history_preserved=True, actual_withdrawal_verified=True)
