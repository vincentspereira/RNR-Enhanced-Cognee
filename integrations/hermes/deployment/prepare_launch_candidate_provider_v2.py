"""Prepare one inactive candidate's provider and qualify scoped memory API.

Original profiles/launchers stay untouched. Preserve the test placeholder and
archived candidate settings. Root alone signs; only ordinary credentials reach
the owner. No chat model, gateway, scheduler or unreviewed profile code runs.
"""
from __future__ import annotations

import ctypes
import copy
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import resource
import stat
import subprocess
import sys
import tempfile
import time
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
STAGE = BASE / 'operator-evidence/named-candidate-stage-w_ydvbvr'
RELEASE = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROVIDER = Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659')
ISSUER_SHA = 'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6'
NETWORK_SHA = 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2'
CLIENT_SHA = '8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64'
PHASES = {'identity', 'preflight', 'scope_controls', 'candidate_layout', 'provider_configuration',
          'provider_binding', 'invented_record', 'semantic_graph', 'retraction'}


def require(value):
    if not value:
        raise ValueError('candidate_provider_preparation_refused')


def definitions(raw, digest):
    require(isinstance(raw, bytes) and len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_candidate_provider_support', '__file__': '<verified-public-support>'}
    exec(compile(raw, '<verified-public-support>', 'exec'), namespace)
    return namespace


def scope_binding(plan):
    # Existing bindings need their own non-widening renewal plan. This batch
    # is strictly the new, ordinary private scope already proposed for this bot.
    require(plan.get('existing_binding') is None and plan.get('enabled') is False)
    scope = plan.get('proposed_binding')
    require(isinstance(scope, dict) and set(scope) == {'sub', 'agent_id', 'tenant', 'project_id', 'roles', 'capture_policy'}
            and scope['roles'] == ['api_client'] and scope['capture_policy'] == 'selected')
    for key in ('sub', 'agent_id', 'tenant', 'project_id'):
        require(isinstance(scope[key], str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', scope[key]))
    require(len(scope['tenant']) <= 32 and len(scope['project_id']) <= 32)
    return dict(scope)


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def provider_settings(config):
    require(isinstance(config, dict) and isinstance(config.get('memory', {}), dict)
            and isinstance(config.get('gateway', {}), dict))
    result = copy.deepcopy(config)
    # Detach these two maps so YAML aliases cannot accidentally change model
    # settings or another consumer of the original memory/gateway dictionary.
    result['memory'] = dict(result.get('memory', {}), provider='enhanced_cognee')
    result['gateway'] = dict(result.get('gateway', {}), multiplex_profiles=True)
    return result


def rename_new(source, target):
    # Linux RENAME_NOREPLACE; never replace even an empty destination directory.
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.renameat2
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(-100, os.fsencode(source), -100, os.fsencode(target), 1):
        raise OSError(ctypes.get_errno(), 'candidate_rename_refused')


def owner_launcher(code):
    require(code.count("n['child']()") == 1)
    return 'import json,contextlib,io\n' + code.replace("n['child']()", """packet=json.loads(sys.stdin.buffer.readline(262145))
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 value=n['child'](packet)
print(json.dumps(value),flush=True)""")


def open_candidate_directory(path, allowed_owners):
    """Traverse non-listable protected ancestors; read only the final directory."""
    require(isinstance(path, Path) and path.is_absolute())
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in (None, *path.parts[1:]):
            if name is not None:
                next_fd = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            info = os.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in allowed_owners and not info.st_mode & 0o022)
        # Open the already pinned final directory, never resolve the path again.
        final_fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        info, final = os.fstat(fd), os.fstat(final_fd)
        if (info.st_dev, info.st_ino) != (final.st_dev, final.st_ino):
            os.close(final_fd)
            raise ValueError('candidate_directory_identity_changed')
        return final_fd
    finally:
        os.close(fd)


def continuation_receipts(prior, diagnostic):
    require(prior.get('complete') is False and prior.get('candidate_modified') is False
        and prior.get('ordinary_credential_published') is False and prior.get('owner_failure_phase') == 'preflight'
        and prior.get('operator_helper_sha256') == 'a21eec3cef6bd37c71467f0c867aaf392700519de2e24aacf837c8fe07d2a175')
    require(diagnostic.get('stage') == 'retained_candidate_preflight_inspection'
        and diagnostic.get('phase') == 'directory_open' and diagnostic.get('error_kind') == 'PermissionError'
        and diagnostic.get('errno') == 13 and diagnostic.get('profiles_changed') is False
        and diagnostic.get('credentials_issued') == 0 and diagnostic.get('store_connections') is False)


def child(packet):
    account = pwd.getpwuid(os.geteuid())
    result = dict(complete=False, checkpoint='identity', record_id=None, candidate_modified=False,
                  ordinary_credential_published=False, chat_model_called=False, gateways_started=0)
    try:
        fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
        require(account.pw_uid != 0 and account.pw_uid == packet['uid'] and account.pw_name == packet['user']
                and account.pw_dir == packet['home'] and not os.getgroups() and fields['NoNewPrivs'].strip() == '1'
                and all(fields[key].strip() == '0000000000000000' for key in ('CapEff', 'CapAmb')))
        home, old = Path(account.pw_dir), Path(packet['candidate'])
        require(old.parent == home and re.fullmatch(r'ec-named-profile-restore-[a-zA-Z0-9_-]{6,64}', old.name))
        require(stat.S_ISDIR(old.lstat().st_mode) and old.stat().st_uid == account.pw_uid
                and stat.S_IMODE(old.stat().st_mode) == 0o700)
        core = definitions(packet['issuer_source'].encode(), ISSUER_SHA)
        core['IDENTITY'] = packet['scope']
        core['open_directory'] = open_candidate_directory
        network = definitions(packet['network_source'].encode(), NETWORK_SHA)
        counts = network['network_guard']()
        result['checkpoint'] = 'preflight'
        placeholder = home / '.hermes'
        require(stat.S_ISDIR(placeholder.lstat().st_mode) and placeholder.stat().st_uid == account.pw_uid
                and stat.S_IMODE(placeholder.stat().st_mode) == 0o700 and set(os.listdir(placeholder)) == {'.isolation-marker'}
                and (placeholder / '.isolation-marker').read_bytes() == b'invented-isolation-marker-v1')
        require(not os.path.lexists(old / 'enhanced_cognee.json') and not os.path.lexists(old / 'plugins/enhanced_cognee'))
        directory = core['open_directory'](old, {0, account.pw_uid})
        try:
            env = core['read_private_at'](directory, '.env', account.pw_uid)[0]
            config_raw = core['read_private_at'](directory, 'config.yaml', account.pw_uid)[0]
        finally:
            os.close(directory)
        import yaml
        config = yaml.safe_load(config_raw)
        config = provider_settings(config)
        updated_env = core['prepare_environment'](env, packet['bundle']['token'])
        auth = (old / 'auth.json').read_bytes() if (old / 'auth.json').exists() else None
        result['checkpoint'] = 'scope_controls'
        core['qualify_access'](packet['bundle'])
        result['checkpoint'] = 'candidate_layout'
        rename_new(placeholder, home / ('.hermes-before-provider-' + packet['nonce']))
        rename_new(old, placeholder)
        result['candidate_modified'] = True
        result['checkpoint'] = 'provider_configuration'
        write_new(placeholder / ('.env-before-provider-' + packet['nonce']), env)
        write_new(placeholder / ('.config-before-provider-' + packet['nonce'] + '.yaml'), config_raw)
        updated_config = yaml.safe_dump(config, sort_keys=False).encode()
        require(yaml.safe_load(updated_config) == config)
        for name, raw in (('.env', updated_env), ('config.yaml', updated_config)):
            proposed = placeholder / (name + '.provider-' + packet['nonce'])
            write_new(proposed, raw)
            os.replace(proposed, placeholder / name)
        result['ordinary_credential_published'] = True
        write_new(placeholder / 'enhanced_cognee.json', json.dumps(dict(base_url='http://127.0.0.1:28080',
            capture_policy='selected', include_shared=True)).encode())
        plugins = placeholder / 'plugins'
        if not plugins.exists():
            plugins.mkdir(mode=0o700)
        require(stat.S_ISDIR(plugins.lstat().st_mode) and plugins.stat().st_uid == account.pw_uid)
        (plugins / 'enhanced_cognee').symlink_to(PROVIDER)
        require(((placeholder / 'auth.json').read_bytes() if (placeholder / 'auth.json').exists() else None) == auth)
        os.environ.clear()
        os.environ.update(PATH='/usr/bin:/bin', HOME=str(home), HERMES_HOME=str(placeholder), LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
        sys.path.insert(0, str(RELEASE / 'repo'))
        from agent.secret_scope import load_env_file, set_secret_scope, reset_secret_scope, current_secret_scope_home
        scoped = set_secret_scope(load_env_file(placeholder / '.env'), profile_home=str(placeholder))
        try:
            result['checkpoint'] = 'provider_binding'
            spec = importlib.util.spec_from_file_location('qualified_candidate_provider', PROVIDER / '__init__.py',
                submodule_search_locations=[str(PROVIDER)])
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            provider = module.EnhancedCogneeProvider()
            client = provider._configured_client(placeholder)
            require(provider.is_available() and current_secret_scope_home() == str(placeholder)
                    and client.token == packet['bundle']['token'])
            status = client.request('GET', '/v1/memories/status')
            require(status.get('ready') is True and all(status.get(field) == packet['scope'][key]
                for field, key in (('tenant_id', 'tenant'), ('project_id', 'project_id'), ('subject', 'sub'))))
            result['checkpoint'] = 'invented_record'
            cedar, birch = 'Cedar-' + packet['nonce'][:8], 'Birch-' + packet['nonce'][:8]
            text = 'Invented candidate qualification: ' + cedar + ' references ' + birch + '.'
            record = client.request('POST', '/v1/memories', dict(content=text, idempotency_key='candidate-' + packet['nonce'],
                knowledge_links=[dict(subject=cedar, predicate='references', object=birch, span_start=0, span_end=len(text))]))
            ident = record.get('id')
            require(isinstance(ident, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', ident) and record.get('version') == 1)
            result['record_id'] = ident
            require(client.request('GET', '/v1/memories/' + ident).get('content') == text)
            result['checkpoint'] = 'semantic_graph'
            deadline = time.monotonic() + 90
            while True:
                recall = client.request('POST', '/v1/memories/recall', dict(query=cedar + ' ' + birch, limit=5))
                graph = client.request('POST', '/v1/memories/connections', dict(entity=cedar, depth=1))
                if recall.get('vector_index') == 'queried' and any(row.get('id') == ident for row in recall.get('results', [])) and graph.get('paths'):
                    break
                require(time.monotonic() < deadline)
                time.sleep(1)
            result['checkpoint'] = 'retraction'
            changed = client.request('POST', '/v1/memories/' + ident + '/retract', dict(expected_version=1))
            require(changed.get('state') == 'retracted' and changed.get('version') == 2)
            history = client.request('GET', '/v1/memories/' + ident + '/history')
            require(history.get('record_state') == 'retracted' and sorted(row['version'] for row in history.get('versions', [])) == [1, 2])
            require(counts['forbidden'] == 0)
            result.update(complete=True, native_profile_file_scope_bound=True, own_scoped_api_verified=True,
                semantic_graph_verified=True, invented_probe_retracted_history_preserved=True,
                unrelated_settings_and_oauth_preserved=True, forbidden_network_attempts=0)
        finally:
            reset_secret_scope(scoped)
    except Exception as error:
        result['category'] = 'candidate_provider_incomplete_preserve_evidence'
        result['error_kind'] = type(error).__name__ if type(error).__name__ in {
            'ValueError', 'OSError', 'PermissionError', 'FileNotFoundError', 'ProvisionError', 'MemoryTransportError'} else 'other'
    return result


def main():
    require(os.geteuid() == 0 and sys.argv[1:] == ['--continue-after-directory-fix'])
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    issuer_raw = Path(__file__).with_name('provision_pilot_access.py').read_bytes()
    issuer = definitions(issuer_raw, ISSUER_SHA)
    network_raw = Path(__file__).with_name('qualify_launch_gateway_renewal_v2.py').read_bytes()
    network = definitions(network_raw, NETWORK_SHA)
    helper = definitions(Path(__file__).with_name('qualify_launch_isolated_accounts.py').read_bytes(),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    shared = definitions(Path(__file__).with_name('recover_launch_graph_operator.py').read_bytes(), helper['SUPPORT_SHA'])
    read, write = shared['read_file'], shared['private_write']
    prior_path = BASE / 'operator-evidence/candidate-provider-3ffd_uk3/summary.json'
    diagnostic_path = BASE / 'operator-evidence/candidate-preflight-inspection-65ac2fcff7b1467cab358366d84efe4c.json'
    continuation_receipts(json.loads(read(prior_path, 0)), json.loads(read(diagnostic_path, 0)))
    accepted = json.loads(read(STAGE / 'summary.json', 0))
    require(accepted.get('complete') is True and accepted.get('authenticated_candidate_copy_verified') is True
            and accepted.get('operator_helper_sha256') == '3bfc6b324ba8ba9e0f80cf7c90bcd605f68649a50c00a7e8d47914400f858f0b')
    files = list(STAGE.glob('*.candidate.private.json'))
    require(len(files) == 1)
    staged = json.loads(read(files[0], 0))
    plan_raw = read(BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json', 0)
    require(hashlib.sha256(plan_raw).hexdigest() == 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b')
    plans = [row for row in json.loads(plan_raw)['profiles'] if row['profile_id'] == staged['profile_id']]
    require(len(plans) == 1)
    scope = scope_binding(plans[0])
    account = pwd.getpwnam(staged['user'])
    require(account.pw_uid == staged['uid'] and account.pw_dir == plans[0]['proposed_home']
            and account.pw_name == plans[0]['proposed_user'] and account.pw_gid != 0
            and grp.getgrgid(account.pw_gid).gr_name == account.pw_name
            and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
    driver = definitions((BASE / 'operator-issuer-candidate-v2/renew_fleet_credentials.py').read_bytes(),
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    native = dict(network['NATIVE'], **{
        'agent/memory_provider.py': 'ac81dcf489c698891f0edebfe26845a75c50d2bde77ec3be8d7938a85c79f1fc',
        'hermes_constants.py': '870ad9935a62968636d6a14d160c0269dfbefd8091ab3cb71be78b30bef6360f'})
    for path, digest in [(RELEASE / 'repo' / name, digest) for name, digest in native.items()] + [
            (PROVIDER / name, digest) for name, digest in network['PROVIDER_FILES'].items()]:
        driver['protected'](path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest)
    source = Path(__file__).read_bytes()
    code, public_line = helper['owner_program'](source)
    evidence = Path(tempfile.mkdtemp(prefix='candidate-provider-', dir=BASE / 'operator-evidence'))
    nonce = uuid.uuid4().hex[:16]
    write(STAGE / 'provider-preparation-directory-fix.started.json', json.dumps(dict(evidence=str(evidence), nonce=nonce)).encode())
    result = dict(complete=False, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(source).hexdigest(), candidate_scope_pending_review=True,
        continued_from=str(prior_path), directory_traversal_fix=True,
        source_profiles_changed=False, private_signing_key_sent_to_owner=False, chat_model_called=False,
        gateways_started=0, units_installed=0, scheduled_renewal_qualified=False,
        post_configuration_backup_qualified=False, actual_profile_admission_qualified=False, fleet_launch_approved=False)
    write(evidence / 'started.json', json.dumps(result).encode())
    try:
        issuer['IDENTITY'] = scope
        key = issuer['load_signing_key']()
        now = int(time.time())
        bundle = issuer['make_bundle'](key, now)
        peer_claims = dict(scope, sub='candidate_peer', agent_id='candidate_peer', project_id='peer_' + nonce, iat=now, exp=now + 600)
        peer = issuer['sign_claims'](peer_claims, key)
        del key
        result['signed_credentials_generated'] = 3
        write(evidence / 'binding.private.json', json.dumps(dict(profile_id=staged['profile_id'], user=account.pw_name,
            uid=account.pw_uid, profile=str(Path(account.pw_dir) / '.hermes'), scope=scope,
            token_expires_at=bundle['claims']['exp'], probe_idempotency_key='candidate-' + nonce)).encode())
        packet = dict(uid=account.pw_uid, user=account.pw_name, home=account.pw_dir, candidate=staged['candidate'],
            scope=scope, bundle=bundle, nonce=nonce, issuer_source=issuer_raw.decode(), network_source=network_raw.decode())
        raw = public_line + json.dumps(packet).encode() + b'\n'
        require(len(raw) <= 262144)
        # The public owner-program launcher calls child() with no arguments.
        owner_code = owner_launcher(code)
        process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', owner_code],
            input=raw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=210, cwd='/',
            user=account.pw_uid, group=account.pw_gid, extra_groups=(),
            env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
        require(process.returncode == 0 and 0 < len(process.stdout) <= 16384)
        value = json.loads(process.stdout)
        write(evidence / 'owner-result.private.json', json.dumps(value).encode())
        result['candidate_modified'] = value.get('candidate_modified') is True
        result['ordinary_credential_published'] = value.get('ordinary_credential_published') is True
        if isinstance(value.get('record_id'), str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value['record_id']):
            result['invented_record_id'] = value['record_id']
        if value.get('complete') is not True:
            if value.get('checkpoint') in PHASES:
                result['owner_failure_phase'] = value['checkpoint']
            raise ValueError('candidate_owner_qualification_incomplete')
        for flag in ('native_profile_file_scope_bound', 'own_scoped_api_verified', 'semantic_graph_verified',
                     'invented_probe_retracted_history_preserved', 'unrelated_settings_and_oauth_preserved'):
            require(value.get(flag) is True)
        require(type(value.get('forbidden_network_attempts')) is int and value['forbidden_network_attempts'] == 0
                and value.get('chat_model_called') is False and type(value.get('gateways_started')) is int
                and value['gateways_started'] == 0)
        client = definitions((PROVIDER / 'client.py').read_bytes(), CLIENT_SHA)
        peer_client = client['MemoryClient']('http://127.0.0.1:28080', peer)
        peer_status = peer_client.request('GET', '/v1/memories/status')
        require(peer_status.get('ready') is True and peer_status.get('project_id') == peer_claims['project_id']
                and peer_status.get('subject') == peer_claims['sub'])
        try:
            peer_client.request('GET', '/v1/memories/' + value['record_id'] + '/history')
        except Exception as error:
            require(getattr(error, 'status_code', None) == 404)
        else:
            raise ValueError('peer_history_boundary_failed')
        result.update(complete=True, candidate_provider_api_qualified=True, peer_history_denied=True,
            invented_probe_retracted_history_preserved=True, candidate_ordinary_credential_published=True)
    except Exception:
        result['category'] = 'candidate_provider_incomplete_preserve_evidence_no_automatic_retry'
    write(evidence / 'summary.json', json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"candidate_provider_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
