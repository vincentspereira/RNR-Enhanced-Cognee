"""One finite candidate renewal batch: scheduled publication, reload, recovery.

Operator qualification explicitly refreshes the valid candidate credential;
this is not the production due-time loop and never enables either fleet policy.
Root alone signs. One retained headless native gateway observes replacement.
No chat model, platform adapter, memory edit or production timer is started.
"""
from __future__ import annotations
import base64
import contextlib
import fcntl
import hashlib
import hmac
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE = BASE / 'operator-isolated-issuer-candidate-v3'
ARTIFACT = BASE / 'operator-candidate-renewal-probe'
CANDIDATE = BASE / 'operator-evidence/candidate-provider-f8uifc8j'
BACKUPS = Path('/var/backups/enhanced-cognee')
PINS = {'provision_pilot_access.py':'cbee340fcca3f6cb946e0593b2bb0b7b8edcc6f13ccf4850ee5ba2830273533e',
    'renew_fleet_credentials.py':'945ed77d3791b7bdaefbabc79b7c6e146d4129aefbec881488472f6bffdbd77e',
    'renew_pilot_access.py':'8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567',
    'fleet_credential_lifecycle.py':'f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62',
    'fleet_credential_policy.py':'6cbda2192ad6040a8043de53eac1fc2c7ad2191dd9175322e1608d285bab8102'}
GATEWAY_SHA = 'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2'
NATIVE_SHA = 'f085298baabc75b801ff82a79fcde97244a129b87146c87c48f72c5f7da0acd0'
BACKUP_SHA = 'cf10aba63a529bdfffa392fdce2cbc68860133626b1871831e9f60238ab5326c'
SUPPORT_SHA = 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
PHASE = 'identity'
CHILD_METADATA = {}
PHASES = {'identity','profile_preflight','native_imports','native_constructor','await_publication','native_reload','owner_publication'}


def require(value):
    if not value:
        raise ValueError('candidate_renewal_qualification_refused')


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == digest)
    namespace = {'__name__':'verified_candidate_renewal_support','__file__':str(path)}
    exec(compile(raw,'<verified-public-support>','exec'),namespace)
    return namespace


def components():
    return {name: definitions(PACKAGE / name, digest) for name,digest in PINS.items()}


def scoped_core(modules, entry):
    core = modules['provision_pilot_access.py']
    core['IDENTITY'] = dict(sub=entry['subject'],agent_id=entry['agent_id'],tenant=entry['tenant'],
        project_id=entry['project_id'],roles=['api_client'],capture_policy='selected')
    return core


def restricted_entry(entry):
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and account.pw_uid == entry['uid'] and account.pw_name == entry['user']
        and account.pw_dir == entry['home'] and not os.getgroups()
        and fields['NoNewPrivs'].strip() == '1'
        and all(fields[key].strip() == '0000000000000000' for key in ('CapEff','CapAmb'))
        and entry['profile'] == str(Path(account.pw_dir) / '.hermes'))
    return account


def owner_publish(packet):
    global PHASE
    PHASE = 'owner_publication'
    entry = packet['entry']
    account = restricted_entry(entry)
    modules = components()
    modules['fleet_credential_policy.py']['validate'](dict(schema=1,profiles=[entry]))
    require(entry['enabled'] is False)
    core = scoped_core(modules, entry)
    directory = core['open_directory'](Path(entry['profile']),{0,account.pw_uid})
    try:
        lock = os.open('.cognee-renewal.lock',os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,0o600,dir_fd=directory)
        try:
            core['read_private_fd'](lock,account.pw_uid)
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            return modules['fleet_credential_lifecycle.py']['publish'](core,modules['renew_pilot_access.py'],
                directory,packet['bundle'],account.pw_uid)
        finally:
            os.close(lock)
    finally:
        os.close(directory)


def gateway_child(packet):
    global PHASE
    entry = packet['entry']
    account = restricted_entry(entry)
    modules = components()
    core = scoped_core(modules,entry)
    profile = Path(entry['profile'])
    require(os.environ.get('HOME') == str(profile) and os.environ.get('HERMES_HOME') == str(profile))
    PHASE = 'profile_preflight'
    CHILD_METADATA['auth_file_present'] = os.path.lexists(profile / 'auth.json')
    directory = core['open_directory'](profile,{0,account.pw_uid})
    try:
        saved = {name:core['read_private_at'](directory,name,account.pw_uid)[0]
            for name in ('config.yaml','auth.json','enhanced_cognee.json')}
        original = core['read_private_at'](directory,'.env',account.pw_uid)[0]
    finally:
        os.close(directory)
    original_token = modules['renew_pilot_access.py']['environment'](core,original)
    original_claims = modules['renew_pilot_access.py']['token_claims'](core,original_token)
    CHILD_METADATA['seconds_remaining'] = max(-86400,min(86400,original_claims['exp'] - int(time.time())))
    modules['fleet_credential_lifecycle.py']['accepted_status'](core,original_token)
    native = definitions(ARTIFACT / 'qualify_launch_candidate_native_unit.py',NATIVE_SHA)
    gateway = definitions(ARTIFACT / 'qualify_launch_gateway_renewal_v2.py',GATEWAY_SHA)
    import yaml
    native['candidate_config'](yaml.safe_load(saved['config.yaml']))
    require(not Path('/etc/hermes').exists() and set(os.listdir(profile / 'plugins')) == {'enhanced_cognee'}
        and (profile / 'plugins/enhanced_cognee').is_symlink()
        and os.readlink(profile / 'plugins/enhanced_cognee') == str(gateway['PROVIDER']))
    os.chdir(profile)
    counts = gateway['network_guard']()
    PHASE = 'native_imports'
    sys.path.insert(0,str(gateway['RELEASE'] / 'repo'))
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionSource
    from gateway.turn_context import TurnContext
    from gateway.run_turn_runner import TurnRunner
    from agent.secret_scope import current_secret_scope_home
    from run_agent import AIAgent
    PHASE = 'native_constructor'
    runner = GatewayRunner(GatewayConfig(multiplex_profiles=True,
        sessions_dir=Path(account.pw_dir) / ('renewal-unit-sessions-' + packet['id'])))
    source = SessionSource(platform=Platform.TELEGRAM,chat_id='qualification',user_id='qualification')
    context = TurnContext(source=source,session_id='renew_' + packet['id'],session_key='renew_' + packet['id'],
        user_config={'memory':{'provider':'enhanced_cognee'},'gateway':{'multiplex_profiles':True}},
        enabled_toolsets=['memory'],disabled_toolsets=None,AIAgent=AIAgent)
    turn = TurnRunner(runner,context)
    route = {'model':'gpt-6.1-sol','runtime':{'provider':'openai-codex','api_mode':'codex_responses',
        'api_key':'invented-unused-model-credential','base_url':'https://chatgpt.com/backend-api/codex','credential_pool':None}}
    def resolve():
        with runner._profile_scope_for_source(source):
            require(current_secret_scope_home() == str(profile))
            return turn._resolve_turn_agent(route,'telegram','',6,{'enabled':True,'effort':'low'},{})
    first,reused = resolve()
    require(not reused and isinstance(first,AIAgent))
    again,reused = resolve()
    require(reused and again is first and gateway['provider_of'](first)._client.token == original_token and not runner.adapters)
    PHASE = 'await_publication'
    # Emit only the bounded handshake outside redirected library output.
    sys.__stdout__.write(json.dumps(dict(ready=True,id=packet['id'])) + '\n')
    sys.__stdout__.flush()
    require(sys.stdin.buffer.readline(32) == b'check\n')
    PHASE = 'native_reload'
    replacement = modules['renew_pilot_access.py']['environment'](core,(profile / '.env').read_bytes())
    require(replacement != original_token)
    second,reused = resolve()
    require(not reused and second is not first and isinstance(second,AIAgent)
        and gateway['provider_of'](second)._client.token == replacement)
    again,reused = resolve()
    require(reused and again is second)
    modules['fleet_credential_lifecycle.py']['accepted_status'](core,replacement)
    require(all((profile / name).read_bytes() == raw for name,raw in saved.items())
        and not runner.adapters and counts['forbidden'] == 0)
    return dict(complete=True,id=packet['id'],retained_native_gateway=True,unchanged_agent_reused=True,
        renewed_agent_rebuilt=True,candidate_token_bound=True,replacement_authenticated=True,
        settings_and_oauth_preserved=True,non_memory_network_attempts=0,chat_model_called=False,
        platform_adapters_started=0,old_expiry_retested=False)


def child_process(entry, mode):
    # Root drops groups/UID before any private profile traversal.
    executable = entry['executable']
    return subprocess.Popen(['/usr/bin/setpriv','--no-new-privs','--',executable,'-I','-B',str(ARTIFACT / Path(__file__).name),mode],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd='/',
        user=entry['uid'],group=pwd.getpwnam(entry['user']).pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':entry['profile'],'HERMES_HOME':entry['profile'],'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'})


def bounded_line(process, seconds):
    selector = selectors.DefaultSelector()
    output = bytearray()
    deadline = time.monotonic() + seconds
    selector.register(process.stdout,selectors.EVENT_READ)
    try:
        while b'\n' not in output:
            require(time.monotonic() < deadline)
            require(selector.select(max(0.01,deadline - time.monotonic())))
            block = os.read(process.stdout.fileno(),1)
            require(block and len(output) < 4096)
            output.extend(block)
        return json.loads(output)
    finally:
        selector.close()


def failure_diagnostic(value):
    result = {}
    if isinstance(value,dict) and value.get('complete') is False:
        if value.get('phase') in PHASES:
            result['phase'] = value['phase']
        if value.get('error_kind') in {'ValueError','PermissionError','FileNotFoundError','ModuleNotFoundError','RuntimeError','other'}:
            result['error_kind'] = value['error_kind']
        if type(value.get('auth_file_present')) is bool:
            result['auth_file_present'] = value['auth_file_present']
        if type(value.get('seconds_remaining')) is int and -86400 <= value['seconds_remaining'] <= 86400:
            result['seconds_remaining'] = value['seconds_remaining']
    return result


def root_files():
    shared = definitions(ARTIFACT / 'recover_launch_graph_operator.py',SUPPORT_SHA)
    return shared['read_file'],shared['private_write']


def entry_policy(modules):
    policy = modules['fleet_credential_policy.py']['load'](PACKAGE / 'candidate-policy.json')
    require(len(policy['profiles']) == 1 and policy['profiles'][0]['enabled'] is False)
    return policy['profiles'][0]


def scheduled_job(ident):
    require(os.geteuid() == 0 and re.fullmatch(r'[a-f0-9]{32}',ident) and Path(__file__).parent == ARTIFACT)
    read,write = root_files()
    context = json.loads(read(ARTIFACT / ('context-' + ident + '.json'),0))
    evidence = Path(context['evidence'])
    require(evidence.parent == BASE / 'operator-evidence' and evidence.name.startswith('candidate-renewal-'))
    modules = components()
    entry = entry_policy(modules)
    driver = modules['renew_fleet_credentials.py']
    require(driver['binding_digest'](entry) == context['entry_sha256'])
    write(evidence / 'scheduled-job.started.json',json.dumps(dict(id=ident)).encode())
    result = dict(complete=False,id=ident,invocation_id=os.environ.get('INVOCATION_ID',''),credentials_issued=0)
    child = None
    try:
        require(re.fullmatch(r'[a-f0-9]{32}',result['invocation_id']))
        core = scoped_core(modules,entry)
        key = core['load_signing_key']()
        bundle = core['make_bundle'](key,int(time.time()))
        del key
        result['credentials_issued'] = 2
        ledger = evidence / 'root-ledger'
        ledger.mkdir(mode=0o700)
        driver['LEDGER'] = ledger
        root_id = entry['name'] + '-' + ident
        directory = core['open_directory'](ledger,{0})
        try:
            driver['ledger_write'](directory,root_id + '.started.json',dict(profile=entry['name'],state='started',source_hashes=driver['SOURCES']))
            driver['ledger_write'](directory,root_id + '.issued.json',dict(schema=1,profile=entry['name'],
                entry_sha256=driver['binding_digest'](entry),source_hashes=driver['SOURCES'],driver_sha256=PINS['renew_fleet_credentials.py'],
                issued_token_sha256=hashlib.sha256(bundle['token'].encode()).hexdigest()))
        finally:
            os.close(directory)
        child = child_process(entry,'--publish')
        raw = json.dumps(dict(entry=entry,bundle=bundle)).encode() + b'\n'
        require(len(raw) <= 16384)
        output,_ = child.communicate(raw,timeout=90)
        if 0 < len(output) <= 4096:
            diagnostic = failure_diagnostic(json.loads(output))
            if diagnostic:
                result['owner_failure'] = diagnostic
        require(child.returncode == 0 and 0 < len(output) <= 4096)
        report = driver['receipt'](output)
        require(report['credential_published'] is True)
        write(ledger / (root_id + '.done.json'),json.dumps(report).encode())
        require(driver['attempt_closed'](core,entry,ledger / (root_id + '.started.json')))
        result.update(complete=True,credential_published=True,bound_root_completion_verified=True,
            settings_and_oauth_preserved=True,private_keys_sent_to_owner=False)
    except Exception:
        result['category'] = 'scheduled_candidate_publication_incomplete_preserve_evidence'
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
    write(evidence / 'scheduled-job.summary.json',json.dumps(result).encode())
    return 0 if result['complete'] else 1


def metadata(unit):
    process = subprocess.run(['/usr/bin/systemctl','show',unit,
        '--property=LoadState,ActiveState,SubState,Result,ExecMainStatus,User,InvocationID,ExecMainStartTimestampMonotonic,LastTriggerUSecMonotonic,NoNewPrivileges,ProtectSystem,ProtectHome'],
        capture_output=True,check=True,timeout=10)
    require(len(process.stdout) <= 8192)
    return dict(line.split('=',1) for line in process.stdout.decode().splitlines() if '=' in line)


def scheduling_proof(service,timer,job):
    require(job.get('complete') is True and job.get('credential_published') is True
        and service.get('LoadState') == 'loaded' and service.get('ActiveState') == 'active'
        and service.get('SubState') == 'exited' and service.get('Result') == 'success'
        and service.get('ExecMainStatus') == '0' and service.get('User') == 'root'
        and service.get('InvocationID') == job.get('invocation_id')
        and re.fullmatch(r'[a-f0-9]{32}',job.get('invocation_id',''))
        and service.get('NoNewPrivileges') == 'yes' and service.get('ProtectSystem') == 'strict'
        and service.get('ProtectHome') == 'yes')
    start,trigger = int(service.get('ExecMainStartTimestampMonotonic','0')),int(timer.get('LastTriggerUSecMonotonic','0'))
    require(0 < trigger <= start and timer.get('LoadState') == 'loaded' and timer.get('Result') == 'success')


def service_finished(value):
    # A timer's not-yet-started service is normally inactive/dead. Wait for
    # actual execution; inactivity alone must never end scheduled polling.
    return (value.get('SubState') == 'exited' or value.get('ActiveState') == 'failed'
        or (value.get('ActiveState') == 'inactive' and int(value.get('ExecMainStartTimestampMonotonic','0')) > 0))


def fresh_backup(entry,evidence,helper,read,write):
    """New generation is justified by this batch's credential replacement."""
    backup = definitions(ARTIFACT / 'backup_launch_candidate_profile.py',BACKUP_SHA)
    core = (ARTIFACT / 'capture_candidate_profile.py').read_bytes()
    require(hashlib.sha256(core).hexdigest() == backup['CORE_SHA'])
    config = json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))
    recipient,key,key_id = (config[name] for name in ('ENHANCED_BACKUP_RECIPIENT','ENHANCED_BACKUP_SIGNING_KEY','ENHANCED_BACKUP_SIGNING_KEY_ID'))
    require(isinstance(key,str) and len(key.encode()) >= 32)
    key = key.encode()
    del config
    account = pwd.getpwnam(entry['user'])
    source = (ARTIFACT / 'backup_launch_candidate_profile.py').read_bytes()
    captured = backup['owner'](helper,account,source,dict(mode='capture',profile=entry['profile'],recipient=recipient,core=core.decode()))
    ciphertext = base64.b64decode(captured['ciphertext'],validate=True)
    require(0 < len(ciphertext) < 22 * 1024 * 1024)
    generation = BACKUPS / ('hermes_candidate_renewed_' + uuid.uuid4().hex + '.tar.age')
    write(evidence / 'renewed-backup.started.json',json.dumps(dict(generation=str(generation))).encode())
    manifest = dict(format='hermes-candidate-profile-sqlite-tar+age-v2',complete=True,
        source_profile_id=entry['user'][6:],created_utc=datetime.now(timezone.utc).isoformat(),
        ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),capture_component_sha256=backup['CORE_SHA'],
        signing_key_id=key_id,receipt=captured['receipt'])
    manifest['signature'] = hmac.new(key,backup['canonical'](manifest),hashlib.sha256).hexdigest()
    write(generation,ciphertext)
    write(generation.with_name(generation.name + '.json'),backup['canonical'](manifest))
    directory_fd = os.open(BACKUPS,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    saved = read(generation,0,backup['LIMIT'])
    signed = json.loads(read(generation.with_name(generation.name + '.json'),0))
    require(hmac.compare_digest(signed['signature'],hmac.new(key,backup['canonical']({k:v for k,v in signed.items() if k != 'signature'}),hashlib.sha256).hexdigest())
        and signed['ciphertext_sha256'] == hashlib.sha256(saved).hexdigest())
    decrypted = subprocess.run([str(backup['AGE']),'--decrypt','--identity',str(backup['IDENTITY'])],input=saved,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20,check=True,cwd='/',env={'PATH':'/usr/bin:/bin','HOME':'/'})
    require(len(decrypted.stdout) <= 20 * 1024 * 1024)
    restored = backup['owner'](helper,account,source,dict(mode='restore',archive=base64.b64encode(decrypted.stdout).decode(),core=core.decode()))
    report = restored['receipt']
    require(all(report.get(k) is True for k in ('complete','archived_files_verified','private_restore_verified','pinned_provider_binding_reconstructed'))
        and report.get('sqlite_databases_verified') == captured['receipt']['sqlite_databases'] and report.get('restored_profile_executed') is False)
    write(evidence / 'renewed-profile-restore.private.json',json.dumps(restored).encode())
    return str(generation)


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1)
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory = Path(__file__).parent
    shared = definitions(directory / 'recover_launch_graph_operator.py',SUPPORT_SHA)
    read,write = shared['read_file'],shared['private_write']
    accepted = json.loads(read(PACKAGE / 'staging.summary.json',0))
    require(accepted.get('complete') is True and accepted.get('disabled_candidate_policy_verified') is True
        and accepted.get('operator_helper_sha256') == 'b12a126bd28c89097e96e2b7fc1e2a9189d41c9dbcc6a1baeebb7841404f37d6'
        and accepted.get('public_component_hashes') == PINS)
    modules = components()
    driver = modules['renew_fleet_credentials.py']
    entry = entry_policy(modules)
    # Pin all public components and native/provider sources before any root job.
    gateway = definitions(directory / 'qualify_launch_gateway_renewal_v2.py',GATEWAY_SHA)
    for path,digest in [(gateway['RELEASE'] / 'repo' / name,digest) for name,digest in gateway['NATIVE'].items()] + [
        (gateway['PROVIDER'] / name,digest) for name,digest in gateway['PROVIDER_FILES'].items()]:
        driver['protected'](path)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest)
    for name,digest in PINS.items():
        driver['protected'](PACKAGE / name)
    source = Path(__file__).read_bytes()
    artifact_sources = {Path(__file__).name:source}
    for name,digest in {'recover_launch_graph_operator.py':SUPPORT_SHA,
        'qualify_launch_gateway_renewal_v2.py':GATEWAY_SHA,'qualify_launch_candidate_native_unit.py':NATIVE_SHA,
        'backup_launch_candidate_profile.py':BACKUP_SHA,
        'capture_candidate_profile.py':'40bbfab7605c3e26d5e075265dc251ca5cb08487c3d84d4b908839ba161ab92a'}.items():
        definitions(directory / name,digest)
        artifact_sources[name] = (directory / name).read_bytes()
    helper = definitions(directory / 'qualify_launch_isolated_accounts.py','d0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    for path in (BACKUPS,Path('/usr/local/bin/age'),Path('/etc/enhanced-cognee/age-recovery-identity.txt')):
        driver['protected'](path)
    require(min(shutil.disk_usage(BACKUPS).free,shutil.disk_usage('/tmp').free) >= 128 * 1024 * 1024)
    ident = uuid.uuid4().hex
    evidence = Path(tempfile.mkdtemp(prefix='candidate-renewal-',dir=BASE / 'operator-evidence'))
    write(PACKAGE / 'candidate-renewal-qualification.started.json',json.dumps(dict(evidence=str(evidence))).encode())
    ARTIFACT.mkdir(mode=0o755)
    ARTIFACT.chmod(0o755)
    for name,raw in artifact_sources.items():
        write(ARTIFACT / name,raw)
        (ARTIFACT / name).chmod(0o644)
    write(ARTIFACT / ('context-' + ident + '.json'),json.dumps(dict(evidence=str(evidence),entry_sha256=driver['binding_digest'](entry))).encode())
    policy_before = read(PACKAGE / 'candidate-policy.json',0)
    fleet_before = read(Path('/etc/enhanced-cognee/fleet-credentials.json'),0)
    fleet = modules['fleet_credential_policy.py']['validate'](json.loads(fleet_before))
    require(all(row['enabled'] is False for row in fleet['profiles']))
    result = dict(complete=False,evidence=str(evidence),source_revision=BASE.name,operator_helper_sha256=hashlib.sha256(source).hexdigest(),
        qualification_refresh_before_due=True,private_keys_sent_to_owner=False,chat_model_called=False,
        platform_adapters_started=0,canonical_memory_edits=False,existing_launchers_changed=False,
        production_renewal_timer_enabled=False,installed_issuer_qualified=False,scheduled_renewal_qualified=False,
        actual_profile_admission_qualified=False,fleet_launch_approved=False)
    write(evidence / 'started.json',json.dumps(result).encode())
    child = None
    unit = 'ec-candidate-renewal-' + ident
    units = []
    phase = 'native_gateway_preflight'
    try:
        child = child_process(entry,'--gateway')
        packet = json.dumps(dict(entry=entry,id=ident)).encode() + b'\n'
        require(len(packet) <= 16384)
        child.stdin.write(packet)
        child.stdin.flush()
        ready = bounded_line(child,75)
        diagnostic = failure_diagnostic(ready)
        if diagnostic:
            result['gateway_failure'] = diagnostic
        require(ready == dict(ready=True,id=ident))
        phase = 'scheduled_candidate_publication'
        args = ['/usr/bin/systemd-run','--quiet','--unit=' + unit,'--on-active=15s',
            '--timer-property=AccuracySec=1s','--timer-property=RemainAfterElapse=yes']
        properties = dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
            PrivateTmp='yes',ProtectHome='yes',ProtectSystem='strict',Restart='no',TimeoutStartSec='110',LimitCORE='0',
            CapabilityBoundingSet='CAP_SETUID CAP_SETGID CAP_CHOWN',ReadWritePaths=str(evidence) + ' ' + entry['home'])
        args += ['--property=' + key + '=' + value for key,value in properties.items()]
        args += ['/usr/bin/python3','-I','-B',str(ARTIFACT / Path(__file__).name),'--scheduled',ident]
        units = [unit + '.service',unit + '.timer']
        subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
        deadline = time.monotonic() + 135
        while True:
            service = metadata(unit + '.service')
            if service_finished(service):
                break
            require(time.monotonic() < deadline)
            time.sleep(1)
        job = json.loads(read(evidence / 'scheduled-job.summary.json',0))
        result['scheduled_publication_observed'] = job.get('credential_published') is True
        result['candidate_ordinary_credential_changed'] = job.get('credential_published') is True
        if isinstance(job.get('owner_failure'),dict):
            result['owner_failure'] = failure_diagnostic(dict(job['owner_failure'],complete=False))
        require(job.get('complete') is True)
        timer = metadata(unit + '.timer')
        write(evidence / 'service.metadata.json',json.dumps(service).encode())
        write(evidence / 'timer.metadata.json',json.dumps(timer).encode())
        scheduling_proof(service,timer,job)
        phase = 'retained_native_gateway_reload'
        child.stdin.write(b'check\n')
        child.stdin.flush()
        child.stdin.close()
        observed = bounded_line(child,75)
        diagnostic = failure_diagnostic(observed)
        if diagnostic:
            result['gateway_failure'] = diagnostic
        require(child.wait(timeout=10) == 0)
        write(evidence / 'gateway.receipt.json',json.dumps(observed).encode())
        require(observed.get('complete') is True and observed.get('id') == ident
            and all(observed.get(k) is True for k in ('retained_native_gateway','unchanged_agent_reused','renewed_agent_rebuilt',
                'candidate_token_bound','replacement_authenticated','settings_and_oauth_preserved'))
            and type(observed.get('non_memory_network_attempts')) is int and observed['non_memory_network_attempts'] == 0
            and observed.get('chat_model_called') is False and observed.get('platform_adapters_started') == 0)
        phase = 'renewed_configuration_recovery'
        result['generation'] = fresh_backup(entry,evidence,helper,read,write)
        require(read(PACKAGE / 'candidate-policy.json',0) == policy_before
            and read(Path('/etc/enhanced-cognee/fleet-credentials.json'),0) == fleet_before)
        result.update(complete=True,candidate_scheduled_publication_component_qualified=True,
            candidate_headless_gateway_reload_qualified=True,renewed_profile_recovery_qualified=True,
            candidate_ordinary_credential_changed=True,settings_and_oauth_preserved=True,
            all_admission_policies_preserved_disabled=True)
    except Exception:
        result.update(category='candidate_renewal_batch_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        if child is not None:
            child.stdout.close()
            if not child.stdin.closed:
                child.stdin.close()
        stopped = []
        for name in units:
            try:
                stopped.append(subprocess.run(['/usr/bin/systemctl','stop',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15).returncode == 0)
            except (OSError,subprocess.TimeoutExpired):
                stopped.append(False)
        result['qualification_units_stopped'] = all(stopped)
        if not result['qualification_units_stopped']:
            result.update(complete=False,category='candidate_renewal_unit_stop_incomplete_preserve_evidence')
    write(evidence / 'summary.json',json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    logging.disable(logging.CRITICAL)
    if len(sys.argv) == 2 and sys.argv[1] in {'--gateway','--publish'}:
        try:
            packet = json.loads(sys.stdin.buffer.readline(16385))
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                value = gateway_child(packet) if sys.argv[1] == '--gateway' else owner_publish(packet)
            print(json.dumps(value),flush=True)
        except Exception as error:
            kind = type(error).__name__
            print(json.dumps(dict(CHILD_METADATA,complete=False,phase=PHASE if PHASE in PHASES else 'unknown',
                error_kind=kind if kind in {'ValueError','PermissionError','FileNotFoundError','ModuleNotFoundError','RuntimeError'} else 'other')),flush=True)
            raise SystemExit(1)
    elif len(sys.argv) == 3 and sys.argv[1] == '--scheduled':
        try:
            raise SystemExit(scheduled_job(sys.argv[2]))
        except Exception:
            raise SystemExit(1)
    else:
        try:
            raise SystemExit(main())
        except Exception:
            print('{"complete":false,"category":"candidate_renewal_preflight_refused_preserve_evidence"}')
            raise SystemExit(1)
