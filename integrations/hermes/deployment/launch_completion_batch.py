"""Two finite consolidated jobs for inactive main setup and named renewal.

Preserve all prior passes and failures. Repeat commands attach to their original
job. No production dispatcher, adapter or renewal timer is activated. Root keys
stay root-only; restricted owner children handle their private profile trees.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import pwd
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-launch-completion-batch-v1'
FLEET = BASE / 'operator-named-fleet-issuer-review-v1'
REVIEW = BASE / 'operator-evidence/fleet-review-mpynoz8c'
BACKUPS = Path('/var/backups/enhanced-cognee')
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
OWNER_SHA = 'e876366823d118048d7cea88996bd4e97ee6ae3e6b5df870032fc382703b8310'
DRIVER_SHA = '146f340ad9258179bf3555f8949ce08ba66aff5554264537603244018d4e7495'
PINS = {
    'inspect_qualified_model_key.py': 'fc739ef3ba7fc9f670a618242769fb3ddafa2c191b384eb28bd0ea1684862ea9',
    'launch_completion_owner.py': OWNER_SHA,
    'prepare_launch_fleet_review.py': '554ac7b170a2d9e1a98557fc7c943cac27e2f23f3569d6bbccb899629cc2ec69',
    'continue_launch_main_operational.py': '547e5bd40aec13c85b3524e15d5732adbfd59b507464182c47f760f7b20c3a25',
    'stage_launch_candidate_issuer.py': 'b12a126bd28c89097e96e2b7fc1e2a9189d41c9dbcc6a1baeebb7841404f37d6',
    'qualify_launch_isolated_accounts.py': 'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94',
    'qualify_launch_candidate_renewal.py': 'f7ce4e8616a323dfecdfd02a5843811bb3812b06941ef7ac214e1de623440e3d',
    'qualify_launch_candidate_reload.py': 'e345caf292465cf126c08c2e0b2825048c62a0bee13592446d7fa9a82d0f16ac',
    'backup_launch_candidate_profile.py': 'cf10aba63a529bdfffa392fdce2cbc68860133626b1871831e9f60238ab5326c',
    'capture_candidate_profile.py': '40bbfab7605c3e26d5e075265dc251ca5cb08487c3d84d4b908839ba161ab92a',
    'qualify_launch_issuer_publication.py': '70869e40df75df755b16ddc894e560256087a8ec4b84ba3af63ebc1b9f93c072',
    'recover_launch_graph_operator.py': SUPPORT_SHA,
    'renew_fleet_credentials.py': DRIVER_SHA,
}
KINDS = {'ValueError', 'PermissionError', 'FileNotFoundError', 'TimeoutExpired', 'MemoryError', 'ProvisionError',
         'MemoryTransportError', 'CaptureError', 'CalledProcessError', 'OSError', 'AuthError', 'RuntimeError', 'KeyError', 'TypeError'}
PHASES = {'identity', 'main_configuration_preflight', 'main_candidate_publication', 'main_scoped_status',
          'main_candidate_capture', 'main_candidate_encryption', 'main_candidate_restore',
          'credential_metadata', 'credential_publish', 'recover_expired', 'retained_gateway_reload',
          'main_api_probe', 'peer_history_denial', 'main_probe_withdrawal'}


def require(value):
    if not value: raise ValueError('launch_completion_batch_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(path, digest):
    raw = path.read_bytes()
    require(0 < len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__': 'verified_completion_batch_support', '__file__': str(path), '_verified_source_bytes': raw}
    exec(compile(raw, '<verified-completion-batch-support>', 'exec'), namespace)
    return namespace


def units(mode):
    require(mode in {'implementation', 'qualification'})
    return 'ec-launch-completion-' + mode + '-20261027'


def metadata(unit):
    result = subprocess.run(['/usr/bin/systemctl', 'show', unit,
        '--property=LoadState,ActiveState,SubState,MainPID,ControlPID,User,Result,ExecMainStatus,InvocationID'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=10)
    require(len(result.stdout) <= 8192)
    return dict(line.split('=', 1) for line in result.stdout.decode().splitlines() if '=' in line)


def stopped(value):
    return value.get('ActiveState') in {'inactive', 'failed'} and value.get('MainPID') == value.get('ControlPID') == '0'


def sync(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def owner_process(entry):
    helper = definitions(ARTIFACT / 'qualify_launch_isolated_accounts.py', PINS['qualify_launch_isolated_accounts.py'])
    source = (ARTIFACT / 'launch_completion_owner.py').read_bytes()
    require(hashlib.sha256(source).hexdigest() == OWNER_SHA)
    _, line = helper['owner_program'](source)
    code = ("import sys,json\nn={'__name__':'completion_owner'}\n"
            "exec(compile(sys.stdin.buffer.readline(65537),'<completion-owner>','exec'),n)\n"
            "try: n['child']()\n"
            "except Exception as e:\n"
            " k=type(e).__name__; number=getattr(e,'errno',None)\n"
            " v={'complete':False,'phase':n.get('PHASE','identity'),'error_kind':k if k in " + repr(KINDS) + " else 'other'}\n"
            " if type(number) is int and number in {1,2,13,20,30,40}: v['errno']=number\n"
            " status=getattr(e,'status_code',None)\n"
            " if type(status) is int and 100<=status<=599: v['http_status']=status\n"
            " print(json.dumps(v)); raise SystemExit(1)\n")
    account = pwd.getpwnam(entry['user'])
    require(account.pw_uid == entry['uid'] and account.pw_uid > 0 and account.pw_dir == entry['home']
            and account.pw_gid > 0 and account.pw_shell == '/usr/sbin/nologin'
            and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid])
    process = subprocess.Popen(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd='/',
        user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    return process, line


def owner_failure(value):
    diagnostic = {'phase': 'other', 'error_kind': 'other'}
    if isinstance(value, dict):
        if isinstance(value.get('phase'), str) and value['phase'] in PHASES: diagnostic['phase'] = value['phase']
        if isinstance(value.get('error_kind'), str) and value['error_kind'] in KINDS: diagnostic['error_kind'] = value['error_kind']
        if type(value.get('errno')) is int and value['errno'] in {1, 2, 13, 20, 30, 40}: diagnostic['errno'] = value['errno']
        if type(value.get('http_status')) is int and 100 <= value['http_status'] <= 599: diagnostic['http_status'] = value['http_status']
    error = ValueError('completion_owner_incomplete_preserve_evidence'); error.owner_diagnostic = diagnostic
    return error


def owner(entry, packet, payload=b''):
    process, line = owner_process(entry)
    require(len(canonical(packet)) <= 65536)
    try:
        output, _ = process.communicate(line + canonical(packet) + b'\n' + payload, timeout=300)
        require(0 < len(output) <= 650 * 1024 * 1024 + 65537)
        header, _, body = output.partition(b'\n'); require(len(header) <= 65536)
        value = json.loads(header)
        if process.returncode != 0 or not isinstance(value, dict) or value.get('complete') is not True:
            raise owner_failure(value)
        if packet['mode'] not in {'capture_main', 'restore_main'}: require(not body)
        return value, body
    finally:
        if process.poll() is None: process.kill()
        process.wait(timeout=15)


def fixed_entry(read):
    main = definitions(ARTIFACT / 'continue_launch_main_operational.py', PINS['continue_launch_main_operational.py'])
    row, _, account = main['selected'](read)
    named = json.loads(read(FLEET / 'candidate-policy.json', 0))['profiles']
    require(len(named) == 40 and account.pw_uid != row['source_uid']
            and account.pw_uid not in {entry['uid'] for entry in named}
            and account.pw_dir not in {entry['home'] for entry in named})
    scope = row['proposed_binding']
    require(scope['roles'] == ['api_client'] and scope['capture_policy'] == 'selected')
    policy = definitions(ARTIFACT / 'fleet_credential_policy.py', '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102')
    entry = dict(name='main_' + row['profile_id'], user=account.pw_name, uid=account.pw_uid,
        home=account.pw_dir, profile=str(Path(account.pw_dir) / '.hermes'), tenant=scope['tenant'], project_id=scope['project_id'],
        subject=scope['sub'], agent_id=scope['agent_id'], roles=['api_client'], lifetime_seconds=86400,
        origin=policy['ORIGIN'], executable=policy['EXECUTABLE'], enabled=False, reload_qualified=False,
        launch_binding_qualified=False, backup_qualified=False, os_boundary_qualified=False)
    policy['validate'](dict(schema=1, profiles=[entry]))
    return entry, row


def fresh_bundle(entry):
    core = definitions(ARTIFACT / 'provision_pilot_access.py', 'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e')
    core['IDENTITY'] = dict(sub=entry['subject'], agent_id=entry['agent_id'], tenant=entry['tenant'],
        project_id=entry['project_id'], roles=['api_client'], capture_policy='selected')
    key = core['load_signing_key']()
    bundle = core['make_bundle'](key, int(time.time())); del key
    return bundle


def main_backup(entry, evidence, read, write):
    settings = json.loads(read(Path('/etc/enhanced-cognee/backup.json'), 0))
    recipient, key, key_id = (settings[k] for k in ('ENHANCED_BACKUP_RECIPIENT', 'ENHANCED_BACKUP_SIGNING_KEY', 'ENHANCED_BACKUP_SIGNING_KEY_ID'))
    require(isinstance(key, str) and len(key.encode()) >= 32 and isinstance(key_id, str) and re.fullmatch('[A-Za-z0-9_-]{1,64}', key_id))
    key = key.encode(); del settings
    captured, ciphertext = owner(entry, dict(mode='capture_main', entry=entry, recipient=recipient))
    main = definitions(ARTIFACT / 'continue_launch_main_operational.py', PINS['continue_launch_main_operational.py'])
    account = pwd.getpwnam(entry['user'])
    main['validate_owner_result'](captured, ciphertext, 'capture', account)
    generation = BACKUPS / ('hermes_main_memory_candidate_' + uuid.uuid4().hex + '.tar.age')
    write(evidence / 'main-generation.started.json', canonical(dict(generation=str(generation))))
    manifest = dict(format='hermes-main-memory-candidate+age-v1', complete=True, source_revision=BASE.name,
        source_profile_id=entry['user'][6:], created_utc=datetime.now(timezone.utc).isoformat(),
        ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(), signing_key_id=key_id, receipt=captured['receipt'])
    manifest['signature'] = hmac.new(key, canonical(manifest), hashlib.sha256).hexdigest()
    write(generation, ciphertext); write(generation.with_name(generation.name + '.json'), canonical(manifest))
    sync(BACKUPS)
    saved = read(generation, 0, 650 * 1024 * 1024)
    signed = json.loads(read(generation.with_name(generation.name + '.json'), 0))
    require(signed == manifest and hashlib.sha256(saved).hexdigest() == signed['ciphertext_sha256']
            and hmac.compare_digest(signed['signature'], hmac.new(key, canonical({k: v for k, v in signed.items() if k != 'signature'}), hashlib.sha256).hexdigest()))
    del key, ciphertext
    decrypted = subprocess.run(['/usr/local/bin/age', '--decrypt', '--identity', '/etc/enhanced-cognee/age-recovery-identity.txt'],
        input=saved, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=90, cwd='/', env={'PATH': '/usr/bin:/bin', 'HOME': '/'})
    require(0 < len(decrypted.stdout) <= 600 * 1024 * 1024)
    restored, body = owner(entry, dict(mode='restore_main', entry=entry, archive_bytes=len(decrypted.stdout)), decrypted.stdout)
    require(restored.get('receipt', {}).get('pinned_provider_binding_reconstructed') is True
            and restored['receipt'].get('restored_scope_authenticated') is True)
    projected = dict(restored, receipt={k: v for k, v in restored['receipt'].items()
                                       if k not in {'pinned_provider_binding_reconstructed', 'restored_scope_authenticated'}})
    main['validate_owner_result'](projected, body, 'restore', account)
    require(restored['receipt']['sqlite_databases_verified'] == captured['receipt']['sqlite_databases'])
    write(evidence / 'main-restored.private.json', canonical(restored))
    return dict(main_candidate_backup_restore_qualified=True, generation=str(generation),
                sqlite_databases_recovered=restored['receipt']['sqlite_databases_verified'],
                pinned_provider_binding_reconstructed=True, restored_main_scope_authenticated=True)


def policies(read):
    paths = [Path('/etc/enhanced-cognee/fleet-credentials.json'),
             BASE / 'operator-isolated-issuer-candidate-v3/candidate-policy.json', FLEET / 'candidate-policy.json']
    result = {path: read(path, 0) for path in paths}
    require(all(row['enabled'] is False for raw in result.values() for row in json.loads(raw)['profiles']))
    return result


def model_key_binding(read, write, evidence, ordinary_key):
    # Root alone reads the protected completion boundary. The fixture owner
    # reads its own file and returns a digest, never its key or token values.
    receipt_path = BASE / 'operator-evidence/model-recall-finish-fdu97vca/summary.json'
    receipt = json.loads(read(receipt_path, 0))
    require(receipt.get('complete') is True and receipt.get('current_configured_model_fresh_process_recall_qualified') is True
            and receipt.get('operator_helper_sha256') == 'ddf3b82e294b7b723463a82a66098fb6d52edd370f9fd1344696368b500a0123')
    boundary = receipt_path.stat().st_mtime_ns
    helper = definitions(ARTIFACT / 'qualify_launch_isolated_accounts.py', PINS['qualify_launch_isolated_accounts.py'])
    source = (ARTIFACT / 'inspect_qualified_model_key.py').read_bytes()
    require(hashlib.sha256(source).hexdigest() == PINS['inspect_qualified_model_key.py'])
    code, line = helper['owner_program'](source)
    account = pwd.getpwnam('hermes-runtime')
    require(account.pw_uid > 0 and account.pw_gid > 0)
    process = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', helper['EXECUTABLE'], '-I', '-B', '-c', code],
        input=line + canonical(dict(completed_ns=boundary)) + b'\n', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=20, cwd='/', user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    require(process.returncode == 0 and 0 < len(process.stdout) <= 1024)
    value = json.loads(process.stdout)
    require(set(value) == {'complete', 'model_key_sha256', 'fixture_unchanged_since_receipt'}
            and value.get('complete') is True and value.get('fixture_unchanged_since_receipt') is True
            and value.get('model_key_sha256') == hashlib.sha256(ordinary_key.encode()).hexdigest())
    write(evidence / 'model-key-binding.private.json', canonical(value))
    return value['model_key_sha256']


def implementation(read, write, evidence):
    entry, row = fixed_entry(read)
    review = definitions(ARTIFACT / 'prepare_launch_fleet_review.py', PINS['prepare_launch_fleet_review.py'])
    snapshot = json.loads(read(REVIEW / 'main-restored-reference.private.json', 0)); review['validate_inspection'](snapshot)
    original = json.loads(read(BASE / 'operator-evidence/main-operational-recovery-0xjyrv2b/restore.private.json', 0))
    route = definitions(ARTIFACT / 'bind_launch_model_route.py', 'edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52')
    _, _, authority = route['prepare']((ARTIFACT / 'bind_launch_model_route.py').read_bytes(), definitions)
    require(authority['endpoint_path'] == '/api/coding/paas/v4')
    model_key_binding(read, write, evidence, authority['key'])
    write(evidence / 'main-binding.private.json', canonical(dict(entry=entry, profile_id=row['profile_id'])))
    bundle = fresh_bundle(entry)
    write(evidence / 'main-configuration.started.json', canonical(dict(credentials_issued=2)))
    sync(evidence)
    result, _ = owner(entry, dict(mode='configure_main', entry=entry, candidate=original['destination'],
        config_sha256=snapshot['fingerprints']['config.yaml'], bundle=bundle, model_key=authority['key'], id=uuid.uuid4().hex))
    require(set(result) == {'complete', 'main_candidate_provider_configured', 'main_filesystem_reference_rebound',
            'mcp_definitions_preserved', 'unrelated_settings_and_oauth_preserved', 'main_scope_authenticated',
            'source_profiles_changed', 'chat_model_called', 'platform_adapters_started', 'actual_profile_admission_qualified', 'fleet_launch_approved'}
            and all(result[k] is False for k in ('source_profiles_changed', 'chat_model_called', 'actual_profile_admission_qualified', 'fleet_launch_approved'))
            and type(result['platform_adapters_started']) is int and result['platform_adapters_started'] == 0
            and result.get('main_candidate_provider_configured') is True and result.get('main_scope_authenticated') is True
            and result.get('main_filesystem_reference_rebound') is True and result.get('unrelated_settings_and_oauth_preserved') is True
            and result.get('mcp_definitions_preserved') == 4)
    write(evidence / 'main-configuration.receipt.json', canonical(result))
    result.update(main_backup(entry, evidence, read, write)); result['credentials_issued'] = 2
    result['qualified_model_key_reused'] = True
    members = json.loads(read(FLEET / 'candidate-policy.json', 0))['profiles'] + [entry]
    require(len(members) == len({row['uid'] for row in members}) == len({row['home'] for row in members}) == 41)
    write(evidence / 'backup-membership.private.json', canonical(dict(schema=1, enabled=False, interval_seconds=86400,
        members=[dict(user=row['user'], uid=row['uid'], home=row['home'], profile=row['profile'],
                      kind='main' if row['user'] == entry['user'] else 'named', admission_ready=False) for row in members])))
    result.update(candidate_backup_membership_count=41, scheduled_fleet_profile_backup_qualified=False)
    return result


def named_backup(entry, evidence, read, write):
    previous = definitions(ARTIFACT / 'qualify_launch_candidate_renewal.py', PINS['qualify_launch_candidate_renewal.py'])
    previous['fresh_backup'].__globals__['ARTIFACT'] = ARTIFACT
    helper = definitions(ARTIFACT / 'qualify_launch_isolated_accounts.py', PINS['qualify_launch_isolated_accounts.py'])
    return previous['fresh_backup'](entry, evidence, helper, read, write)


def qualify_profile(entry, per, read, write, model_key_digest):
    require(isinstance(model_key_digest, str) and re.fullmatch('[a-f0-9]{64}', model_key_digest))
    previous = definitions(ARTIFACT / 'qualify_launch_candidate_renewal.py', PINS['qualify_launch_candidate_renewal.py'])
    termination = definitions(ARTIFACT / 'qualify_launch_candidate_reload.py', PINS['qualify_launch_candidate_reload.py'])
    driver = definitions(ARTIFACT / 'renew_fleet_credentials.py', DRIVER_SHA)
    core = definitions(ARTIFACT / 'provision_pilot_access.py', 'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e')
    result = dict(complete=False, credential_changed=False, credentials_issued=0,
                  expired_candidate_recovered=False, named_candidate_backup_restore_qualified=False)
    phase = 'credential_metadata'; retained = None
    write(per / 'started.json', canonical(result))
    try:
        state, _ = owner(entry, dict(mode='credential_metadata', entry=entry))
        require(set(state) == {'complete', 'expired', 'token_iat', 'token_sha256', 'scope_shape_verified', 'api_status_http', 'credentials_changed'}
                and type(state['expired']) is bool and type(state['token_iat']) is int
                and re.fullmatch('[a-f0-9]{64}', state['token_sha256'])
                and state['scope_shape_verified'] is True and state['credentials_changed'] is False
                and state['api_status_http'] == (401 if state['expired'] else 200))
        write(per / 'credential-metadata.json', canonical(state))
        if state['expired']:
            phase = 'operator_expired_candidate_recovery'
            bundle = fresh_bundle(entry); result['credentials_issued'] += 2
            write(per / 'expired-recovery.started.json', canonical(dict(
                issued_token_sha256=hashlib.sha256(bundle['token'].encode()).hexdigest(),
                fixed_scope=dict(subject=entry['subject'], tenant=entry['tenant'], project_id=entry['project_id']))))
            sync(per)
            report, _ = owner(entry, dict(mode='recover_expired', entry=entry, bundle=bundle))
            require(set(report) == {'complete', 'expired_candidate_recovered', 'preserved_settings_and_oauth',
                    'preserved_previous_environment', 'interrupted_attempts_reconciled', 'unattended_renewal_qualified', 'timer_activation_approved'}
                    and report.get('expired_candidate_recovered') is True and report.get('preserved_settings_and_oauth') is True
                    and report.get('preserved_previous_environment') is True and report.get('unattended_renewal_qualified') is False
                    and report.get('timer_activation_approved') is False and type(report['interrupted_attempts_reconciled']) is int
                    and 0 <= report['interrupted_attempts_reconciled'] <= 128)
            result.update(credential_changed=True, expired_candidate_recovered=True)
            write(per / 'expired-recovery.receipt.json', canonical(report))
            state['token_iat'] = bundle['claims']['iat']
        phase = 'retained_native_gateway_preflight'
        retained, line = owner_process(entry); ident = uuid.uuid4().hex
        retained.stdin.write(line + canonical(dict(mode='gateway', entry=entry, id=ident, model_key_digest=model_key_digest)) + b'\n'); retained.stdin.flush()
        ready = previous['bounded_line'](retained, 90)
        if ready != dict(ready=True, id=ident): raise owner_failure(ready)
        phase = 'ordinary_credential_publication'
        # HS256 tokens use integer seconds. A new iat must differ from the
        # bootstrap credential; this is bounded clock waiting, not a retry.
        deadline = time.monotonic() + 3
        while int(time.time()) <= state['token_iat']:
            require(time.monotonic() < deadline); time.sleep(0.1)
        bundle = fresh_bundle(entry); result['credentials_issued'] += 2
        ledger = per / 'root-ledger'; ledger.mkdir(mode=0o700)
        driver['LEDGER'] = ledger; root_id = entry['name'] + '-' + ident
        descriptor = core['open_directory'](ledger, {0})
        try:
            driver['ledger_write'](descriptor, root_id + '.started.json', dict(
                profile=entry['name'], state='started', source_hashes=driver['SOURCES']))
            driver['ledger_write'](descriptor, root_id + '.issued.json', dict(schema=1, profile=entry['name'],
                entry_sha256=driver['binding_digest'](entry), source_hashes=driver['SOURCES'], driver_sha256=DRIVER_SHA,
                issued_token_sha256=hashlib.sha256(bundle['token'].encode()).hexdigest()))
        finally: os.close(descriptor)
        report, _ = owner(entry, dict(mode='credential_publish', entry=entry, bundle=bundle))
        report = driver['receipt'](canonical(report)); require(report['credential_published'] is True)
        result['credential_changed'] = True
        write(ledger / (root_id + '.done.json'), canonical(report))
        require(driver['attempt_closed'](core, entry, ledger / (root_id + '.started.json')))
        phase = 'retained_native_gateway_reload'
        retained.stdin.write(b'check\n'); retained.stdin.flush(); retained.stdin.close()
        observed = previous['bounded_line'](retained, 90)
        require(retained.wait(timeout=15) == 0)
        require(isinstance(observed, dict) and set(observed) == {'complete', 'id', 'actual_configured_zai_route_used',
                'retained_native_gateway', 'unchanged_agent_reused', 'renewed_agent_rebuilt', 'candidate_token_bound',
                'replacement_authenticated', 'settings_and_oauth_preserved', 'non_memory_network_attempts',
                'chat_model_called', 'platform_adapters_started'} and observed.get('actual_configured_zai_route_used') is True)
        compatible = {key: value for key, value in observed.items() if key != 'actual_configured_zai_route_used'}
        termination['accepted_reload'](compatible, ident)
        write(per / 'native-reload.receipt.json', canonical(observed))
        result.update(complete=True, actual_configured_zai_route_used=True, native_gateway_reload_qualified=True,
                      fixed_scope_publication_qualified=True, bound_root_completion_verified=True)
    except Exception as error:
        result.update(failure_phase=phase, error_kind=type(error).__name__ if type(error).__name__ in KINDS else 'other')
        if isinstance(getattr(error, 'owner_diagnostic', None), dict): result['owner_diagnostic'] = error.owner_diagnostic
    finally:
        result['qualification_process_stopped'] = termination['terminate'](retained)
        if not result['qualification_process_stopped']: result['complete'] = False
        # Even an interrupted publication can have changed the credential.
        # Once publication started, preserve that state with a new backup.
        needs_backup = result['credential_changed'] or os.path.lexists(per / 'expired-recovery.started.json') or os.path.lexists(per / 'root-ledger')
        if needs_backup:
            try:
                result['generation'] = named_backup(entry, per, read, write)
                result['named_candidate_backup_restore_qualified'] = True
            except Exception:
                result.update(complete=False, backup_incomplete_preserve_evidence=True)
        if not result['named_candidate_backup_restore_qualified']: result['complete'] = False
    write(per / 'summary.json', canonical(result))
    return result


def qualification(read, write, evidence):
    policy = definitions(ARTIFACT / 'fleet_credential_policy.py', '6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102')
    entries = policy['load'](FLEET / 'candidate-policy.json')['profiles']
    require(len(entries) == len({entry['uid'] for entry in entries}) == 40 and all(entry['enabled'] is False for entry in entries))
    context = json.loads(read(ARTIFACT / 'implementation-context.json', 0))
    implementation_evidence = Path(context['evidence'])
    require(implementation_evidence.parent == BASE / 'operator-evidence' and implementation_evidence.name.startswith('launch-implementation-'))
    model = json.loads(read(implementation_evidence / 'model-key-binding.private.json', 0))
    require(set(model) == {'complete', 'model_key_sha256', 'fixture_unchanged_since_receipt'}
            and model.get('complete') is True and model.get('fixture_unchanged_since_receipt') is True
            and isinstance(model.get('model_key_sha256'), str) and re.fullmatch('[a-f0-9]{64}', model['model_key_sha256']))
    main = main_probe(read, write, evidence, entries[0])
    completed = 0; issued = main['credentials_issued']; recovered = 0
    for index, entry in enumerate(entries, 1):
        per = evidence / entry['user'][6:]; per.mkdir(mode=0o700)
        write(per / 'binding.private.json', canonical(entry))
        progress = dict(event='fleet_qualification_progress', current=index, total=40, completed=completed)
        write(evidence / ('progress-' + str(index).zfill(4) + '.json'), canonical(progress))
        print(json.dumps(progress), flush=True)
        receipt = qualify_profile(entry, per, read, write, model['model_key_sha256'])
        issued += receipt['credentials_issued']; recovered += int(receipt['expired_candidate_recovered'])
        if receipt['complete'] is not True:
            error = ValueError('fleet_profile_incomplete_preserve_evidence')
            error.batch_progress = dict(selected_profiles=40, qualified_profiles=completed, failed_profiles=1,
                unattempted_profiles=40 - index, credentials_issued=issued, expired_candidates_recovered=recovered,
                failed_profile_id=entry['user'][6:])
            raise error
        completed += 1
    return dict(selected_profiles=40, qualified_profiles=completed, failed_profiles=0, unattempted_profiles=0,
        credentials_issued=issued, expired_candidates_recovered=recovered,
        named_native_gateway_reload_components_qualified=True, named_post_renewal_restores_qualified=True,
        main_scope_api_and_index_probe_qualified=True, main_peer_scope_and_os_denials_qualified=True,
        main_invented_probe_retracted_history_preserved=True, canonical_memory_edits=True,
        live_private_memory_edits=False)


def main_probe(read, write, evidence, peer):
    context = json.loads(read(ARTIFACT / 'implementation-context.json', 0))
    implementation_evidence = Path(context['evidence'])
    require(implementation_evidence.parent == BASE / 'operator-evidence' and implementation_evidence.name.startswith('launch-implementation-'))
    binding = json.loads(read(implementation_evidence / 'main-binding.private.json', 0)); entry = binding['entry']
    require(entry == fixed_entry(read)[0] and entry['uid'] != peer['uid'])
    nonce = uuid.uuid4().hex
    write(evidence / 'main-probe.started.json', canonical(dict(id=nonce, project_id=entry['project_id'], subject=entry['subject'])))
    sync(evidence)
    own, _ = owner(entry, dict(mode='main_api_probe', entry=entry, id=nonce, peer_profile=peer['profile']))
    require(set(own) == {'complete', 'record_id', 'own_scope_write_read_qualified', 'actual_semantic_graph_qualified', 'main_os_peer_and_operator_denials_qualified'}
            and all(own[k] is True for k in ('complete', 'own_scope_write_read_qualified', 'actual_semantic_graph_qualified', 'main_os_peer_and_operator_denials_qualified'))
            and isinstance(own['record_id'], str) and re.fullmatch('[A-Za-z0-9_-]{1,64}', own['record_id']))
    write(evidence / 'main-probe.receipt.json', canonical(own))
    bundle = fresh_bundle(peer)
    write(evidence / 'peer-probe.started.json', canonical(dict(credentials_issued=2, subject=peer['subject'])))
    sync(evidence)
    denied, _ = owner(peer, dict(mode='peer_history_denial', entry=peer, record_id=own['record_id'], token=bundle['token']))
    require(denied == dict(complete=True, peer_history_denied=True, peer_credential_scope_authenticated=True))
    write(evidence / 'peer-probe.receipt.json', canonical(denied))
    done, _ = owner(entry, dict(mode='main_probe_withdrawal', entry=entry, id=nonce, record_id=own['record_id']))
    require(done == dict(complete=True, invented_record_retracted_history_preserved=True, actual_withdrawal_verified=True))
    write(evidence / 'main-withdrawal.receipt.json', canonical(done))
    return dict(complete=True, credentials_issued=2)


def worker(mode):
    require(os.geteuid() == 0 and Path(__file__).parent == ARTIFACT)
    support = definitions(ARTIFACT / 'recover_launch_graph_operator.py', SUPPORT_SHA)
    read, write = support['read_file'], support['private_write']
    context = json.loads(read(ARTIFACT / (mode + '-context.json'), 0)); evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence' and evidence.name.startswith('launch-' + mode + '-'))
    before = policies(read)
    result = dict(complete=False, phase=mode, evidence=str(evidence), source_revision=BASE.name,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_profiles_changed=False, existing_launchers_changed=False, chat_model_called=False,
        canonical_memory_edits=False,
        platform_adapters_started=0, private_keys_sent_to_owner=False, production_renewal_timer_enabled=False,
        actual_profile_admission_qualified=False, production_dispatch_qualified=False, fleet_launch_approved=False,
        automatic_retry=False, credentials_issued=0, candidate_scope_pending_review=True,
        main_tool_program_coverage_qualified=False, transient_qualification_timer_created=mode == 'qualification',
        invocation_id=os.environ.get('INVOCATION_ID', ''))
    write(evidence / 'started.json', canonical(result))
    try:
        require(re.fullmatch('[a-f0-9]{32}', result['invocation_id']))
        verify_runtime()
        result.update(implementation(read, write, evidence) if mode == 'implementation' else qualification(read, write, evidence))
        result['complete'] = True
    except Exception as error:
        result.update(category='launch_batch_incomplete_preserve_evidence_no_automatic_retry',
            error_kind=type(error).__name__ if type(error).__name__ in KINDS else 'other')
        if isinstance(getattr(error, 'owner_diagnostic', None), dict): result['owner_diagnostic'] = error.owner_diagnostic
        if isinstance(getattr(error, 'batch_progress', None), dict): result.update(error.batch_progress)
        if mode == 'implementation' and os.path.lexists(evidence / 'main-configuration.started.json'):
            result.update(credentials_issued=2, inactive_main_candidate_may_have_changed=True)
        if mode == 'qualification' and os.path.lexists(evidence / 'main-probe.started.json'):
            result.update(canonical_memory_edits_may_have_occurred=True, live_private_memory_edits=False)
            if os.path.lexists(evidence / 'main-probe.receipt.json'): result['canonical_memory_edits'] = True
            else: result.pop('canonical_memory_edits', None)
            if 'qualified_profiles' not in result:
                result.update(selected_profiles=40, qualified_profiles=0, unattempted_profiles=40)
                if os.path.lexists(evidence / 'peer-probe.started.json'): result['credentials_issued'] = 2
    require(all(read(path, 0) == raw for path, raw in before.items()))
    result['all_admission_policies_preserved_disabled'] = True
    write(evidence / 'summary.json', canonical(result))
    return 0 if result['complete'] else 1


def verify_runtime():
    gateway = definitions(ARTIFACT / 'qualify_launch_gateway_renewal_v2.py', 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2')
    routes = definitions(ARTIFACT / 'complete_launch_named_runtime.py', '6dbf807c3c4eb4cc9da1834fc3cfc13747f9b7a456997a0e66ce076e6b5fe625')
    for name, digest in dict(gateway['NATIVE'], **routes['ROUTE_PINS']).items():
        require(hashlib.sha256((gateway['RELEASE'] / 'repo' / name).read_bytes()).hexdigest() == digest)
    for name, digest in gateway['PROVIDER_FILES'].items():
        require(hashlib.sha256((gateway['PROVIDER'] / name).read_bytes()).hexdigest() == digest)


def watch(mode, read, write):
    context = json.loads(read(ARTIFACT / (mode + '-context.json'), 0)); evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence' and evidence.name.startswith('launch-' + mode + '-'))
    finished = evidence / 'finish.summary.json'
    if os.path.lexists(finished):
        result = json.loads(read(finished, 0))
        require(result.get('source_revision') == BASE.name and result.get('evidence') == str(evidence)
                and result.get('phase') == mode and result.get('operator_job_stopped') is True)
        print(json.dumps(result), flush=True); return 0 if result.get('complete') is True else 1
    stem = units(mode); last = 0; began = time.monotonic()
    try:
        while True:
            value = metadata(stem + '.service')
            try: summary = json.loads(read(evidence / 'summary.json', 0))
            except FileNotFoundError: summary = None
            if summary is not None and (value.get('SubState') == 'exited' or stopped(value)):
                if mode == 'qualification' and summary.get('complete') is True:
                    require(value.get('LoadState') == 'not-found' or (value.get('Result') == 'success' and value.get('ExecMainStatus') == '0'
                            and value.get('User') == 'root' and value.get('InvocationID') == summary['invocation_id']))
                    journal = subprocess.run(['/usr/bin/journalctl', '--no-pager', '--output=json', '--lines=128',
                        '--unit=' + stem + '.service', '--unit=' + stem + '.timer'], stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL, check=True, timeout=15)
                    require(len(journal.stdout) <= 262144)
                    verifier = definitions(ARTIFACT / 'qualify_launch_issuer_publication.py', PINS['qualify_launch_issuer_publication.py'])
                    proof = verifier['journal_scheduling_proof']([json.loads(line) for line in journal.stdout.splitlines()], stem, summary['invocation_id'])
                    require(proof.get('verified') is True); summary['journal_scheduling_proof'] = proof
                    summary['scheduled_candidate_fleet_publication_qualified'] = True
                for suffix in (('timer', 'service') if mode == 'qualification' else ('service',)):
                    if metadata(stem + '.' + suffix).get('ActiveState') not in {'inactive', 'failed'}:
                        subprocess.run(['/usr/bin/systemctl', 'stop', stem + '.' + suffix], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, check=True, timeout=20)
                summary['operator_job_stopped'] = stopped(metadata(stem + '.service'))
                summary['complete'] = summary.get('complete') is True and summary['operator_job_stopped']
                saved = evidence / 'finish.summary.json'
                if not os.path.lexists(saved): write(saved, canonical(summary))
                print(json.dumps(summary), flush=True); return 0 if summary['complete'] else 1
            if summary is None and value.get('ActiveState') == 'failed':
                if mode == 'qualification' and metadata(stem + '.timer').get('ActiveState') not in {'inactive', 'failed'}:
                    subprocess.run(['/usr/bin/systemctl', 'stop', stem + '.timer'], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, check=True, timeout=20)
                print(json.dumps(dict(complete=False, evidence=str(evidence), category='launch_batch_exited_without_receipt',
                    effects_require_reconciliation=True, operator_job_stopped=stopped(value))), flush=True); return 1
            if summary is None and stopped(value) and value.get('LoadState') == 'not-found' and (mode == 'implementation' or time.monotonic() - began > 45):
                print(json.dumps(dict(complete=False, evidence=str(evidence), category='launch_batch_not_running_preserve_evidence')), flush=True); return 1
            if time.monotonic() - last >= 15:
                progress = dict(event='launch_batch_running', phase=mode, note='Ctrl+C detaches; repeat the same command to reattach.')
                if mode == 'qualification':
                    for index in range(40, 0, -1):
                        path = evidence / ('progress-' + str(index).zfill(4) + '.json')
                        if os.path.lexists(path):
                            value = json.loads(read(path, 0))
                            require(value.get('current') == index and value.get('total') == 40
                                    and type(value.get('completed')) is int and 0 <= value['completed'] < index)
                            progress.update(current=index, total=40, completed=value['completed']); break
                else:
                    progress['checkpoint'] = 'main_backup_restore' if os.path.lexists(evidence / 'main-configuration.receipt.json') else 'main_configuration'
                print(json.dumps(progress), flush=True); last = time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True, job_continues=True, evidence=str(evidence))), flush=True); return 0


def launch(mode):
    require(os.geteuid() == 0 and mode in {'implementation', 'qualification'})
    directory = Path(__file__).parent
    support = definitions(directory / 'recover_launch_graph_operator.py', SUPPORT_SHA)
    read, write = support['read_file'], support['private_write']
    if os.path.lexists(ARTIFACT / (mode + '-context.json')): return watch(mode, read, write)
    if mode == 'implementation':
        accepted = json.loads(read(REVIEW / 'summary.json', 0))
        require(accepted.get('complete') is True and accepted.get('operator_helper_sha256') == PINS['prepare_launch_fleet_review.py']
                and accepted.get('staged_policy_entries') == 40 and accepted.get('admitted_policy_entries') == 0
                and accepted.get('main_configuration_matches_retained_snapshot') is True
                and accepted.get('main_restored_unresolved_references') == 1)
        require(not os.path.lexists(ARTIFACT))
        review = definitions(directory / 'prepare_launch_fleet_review.py', PINS['prepare_launch_fleet_review.py'])
        review['retained'](read)
        owner_code = definitions(directory / 'launch_completion_owner.py', OWNER_SHA)
        hashes = dict(PINS, **owner_code['PINS'])
        sources = {Path(__file__).name: globals()['_verified_source_bytes']}
        for name, digest in hashes.items():
            origin = FLEET / name if name in {'provision_pilot_access.py', 'renew_fleet_credentials.py'} else directory / name
            sources[name] = definitions(origin, digest)['_verified_source_bytes']
        require(shutil.disk_usage(BACKUPS).free >= 2 * 1024**3)
        ARTIFACT.mkdir(mode=0o755); ARTIFACT.chmod(0o755)
        for name, raw in sources.items(): write(ARTIFACT / name, raw); (ARTIFACT / name).chmod(0o644)
        write(ARTIFACT / 'sources.json', canonical({name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()}))
        sync(ARTIFACT)
    else:
        implementation_context = json.loads(read(ARTIFACT / 'implementation-context.json', 0))
        passed = json.loads(read(Path(implementation_context['evidence']) / 'finish.summary.json', 0))
        require(passed.get('complete') is True and passed.get('main_candidate_backup_restore_qualified') is True
                and passed.get('operator_job_stopped') is True)
        manifest = json.loads(read(ARTIFACT / 'sources.json', 0))
        require(manifest.get(Path(__file__).name) == hashlib.sha256(globals()['_verified_source_bytes']).hexdigest())
        for name, digest in manifest.items():
            require(re.fullmatch(r'[a-z0-9_]+\.py', name) and re.fullmatch('[a-f0-9]{64}', digest)
                    and hashlib.sha256((ARTIFACT / name).read_bytes()).hexdigest() == digest)
    before = policies(read)
    driver = definitions(ARTIFACT / 'renew_fleet_credentials.py', DRIVER_SHA)
    executable = Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python')
    for path in (ARTIFACT, BACKUPS, Path('/usr/local/bin/age'), Path('/etc/enhanced-cognee/age-recovery-identity.txt')):
        driver['protected'](path)
    driver['protected'](executable, final_link=True)
    driver['protected'](executable.resolve(strict=True))
    stem = units(mode)
    require(metadata(stem + '.service').get('LoadState') == 'not-found')
    evidence = Path(tempfile.mkdtemp(prefix='launch-' + mode + '-', dir=BASE / 'operator-evidence'))
    write(ARTIFACT / (mode + '-context.json'), canonical(dict(evidence=str(evidence))))
    sync(ARTIFACT)
    homes = [json.loads(raw)['profiles'] for path, raw in before.items() if path == FLEET / 'candidate-policy.json'][0]
    write_paths = [str(BASE / 'operator-evidence'), str(BACKUPS)]
    write_paths += [fixed_entry(read)[0]['home']] if mode == 'implementation' else [row['home'] for row in homes]
    settings = dict(Type='oneshot', RemainAfterExit='yes', User='root', Group='root', UMask='0077',
        NoNewPrivileges='yes', CapabilityBoundingSet='CAP_SETUID CAP_SETGID', AmbientCapabilities='',
        ProtectSystem='strict', ProtectHome='no' if mode == 'implementation' else 'yes', PrivateTmp='yes',
        ReadWritePaths=' '.join(write_paths), Restart='no', TimeoutStartSec='3600', MemoryMax='8G', LimitCORE='0')
    args = ['/usr/bin/systemd-run', '--quiet', '--no-block', '--unit=' + stem]
    if mode == 'qualification': args += ['--on-active=15s', '--timer-property=RemainAfterElapse=yes']
    args += ['--property=' + key + '=' + value for key, value in settings.items()]
    args += [str(BASE / 'runtime/bin/python'), '-I', '-B', str(ARTIFACT / Path(__file__).name), '--worker', mode]
    subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
    return watch(mode, read, write)


if __name__ == '__main__':
    os.umask(0o077); resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        require(len(sys.argv) == 3 and sys.argv[1] == '--worker' and sys.argv[2] in {'implementation', 'qualification'})
        raise SystemExit(worker(sys.argv[2]))
    except Exception:
        print('{"complete":false,"category":"launch_completion_worker_preflight_refused_no_secret_output"}', flush=True)
        raise SystemExit(1)
