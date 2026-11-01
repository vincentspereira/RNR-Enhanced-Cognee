"""Bounded encrypted main-state capture and restore into its inactive identity.

Private data crosses owner pipes as bounded binary frames, never command text,
logs or workspace files. Root handles only encrypted files and protected keys;
ordinary identities capture/restore their own files. Explicit omissions remain
in the encrypted manifest. Full coverage, dependency rebuild and admission stay
unqualified. Repeating the command attaches to the same finite job.
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
import subprocess
import sys
import tempfile
import time
import uuid

BASE = Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT = BASE / 'operator-main-operational-recovery-v2'
PLAN = BASE / 'operator-evidence/profile-isolation-plan-p2bahhlh/plan.private.json'
PLAN_SHA = 'b3baaccdda2f3fd7120bf75ff9e2fea7063c14e46bf66cd31277b9113cd2cd3b'
UNIT = 'ec-launch-main-operational-recovery-20261027.service'
BACKUPS = Path('/var/backups/enhanced-cognee')
AGE = Path('/usr/local/bin/age')
IDENTITY = Path('/etc/enhanced-cognee/age-recovery-identity.txt')
CORE_SHA = 'e32266d8a797eeaca2a32247f861cbf725341cce960eeb73d3db57987c99c106'
PINS = {
    'capture_main_operational_profile_v3.py': CORE_SHA,
    'qualify_launch_isolated_accounts.py': 'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94',
    'recover_launch_graph_operator.py': 'd7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef',
}
HEADER = 65536
ARCHIVE_LIMIT = 600 * 1024 * 1024
CIPHER_LIMIT = 650 * 1024 * 1024
PHASE = 'identity'
PHASES = {'identity', 'capture', 'encryption', 'restore'}
CORE_CHECKPOINTS = {'guard','source_walk','sqlite_snapshot','payload_read','stability_verification','archive_encoding'}
CORE_REASONS = {'capture_guard_refused','durable_file_changed_before_read','durable_file_changed_during_read',
    'durable_file_changed_after_read','durable_directory_changed','database_committed_during_capture','source_io_or_sqlite_error'}


def require(value):
    if not value:
        raise ValueError('main_operational_recovery_refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def definitions(path, digest):
    raw = path.read_bytes()
    require(len(raw) <= HEADER and hashlib.sha256(raw).hexdigest() == digest)
    value = {'__name__':'verified_main_recovery_support', '__file__':str(path), '_verified_source_bytes':raw}
    exec(compile(raw, '<verified-public-main-recovery>', 'exec'), value)
    return value


def packet_shape(packet):
    require(isinstance(packet, dict) and packet.get('mode') in {'capture','restore'})
    expected = {'mode','profile_id','core','recipient'} if packet['mode'] == 'capture' else {'mode','profile_id','core','archive_bytes'}
    require(set(packet) == expected and re.fullmatch('[a-f0-9]{16}', packet.get('profile_id',''))
        and isinstance(packet['core'],str) and hashlib.sha256(packet['core'].encode()).hexdigest() == CORE_SHA)
    if packet['mode'] == 'capture':
        require(isinstance(packet['recipient'],str) and re.fullmatch('age1[0-9a-z]{20,100}',packet['recipient']))
    else:
        require(type(packet['archive_bytes']) is int and 0 < packet['archive_bytes'] <= ARCHIVE_LIMIT)


def child():
    global PHASE
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    raw = sys.stdin.buffer.readline(HEADER+1)
    require(len(raw) <= HEADER)
    packet = json.loads(raw)
    packet_shape(packet)
    account = pwd.getpwuid(os.geteuid())
    status = dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_uid != 0 and not os.getgroups() and status['NoNewPrivs'].strip() == '1'
        and all(status[k].strip() == '0000000000000000' for k in ('CapEff','CapAmb')))
    core = {'__name__':'verified_main_operational_core'}
    exec(compile(packet['core'],'<verified-public-main-capture>','exec'),core)
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin',HOME=account.pw_dir,LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    if packet['mode'] == 'capture':
        profile = Path(account.pw_dir)/'.hermes'
        require(account.pw_name == 'vincentspereira' and account.pw_dir == '/home/vincentspereira'
            and hashlib.sha256((account.pw_name+'\0'+str(profile)).encode()).hexdigest()[:16] == packet['profile_id'])
        PHASE = 'capture'
        archive,receipt = core['capture'](profile,online_databases=True)
        require(0 < len(archive) <= ARCHIVE_LIMIT)
        PHASE = 'encryption'
        encrypted = subprocess.run([str(AGE),'--encrypt','--recipient',packet['recipient']],input=archive,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=90)
        require(0 < len(encrypted.stdout) <= CIPHER_LIMIT and encrypted.stdout.startswith(b'age-encryption.org/v1\n'))
        header = canonical(dict(complete=True,receipt=receipt,ciphertext_bytes=len(encrypted.stdout)))
        require(len(header) <= HEADER)
        sys.stdout.buffer.write(header+b'\n')
        sys.stdout.buffer.write(encrypted.stdout)
    else:
        require(account.pw_name == 'ecbot_'+packet['profile_id']
            and account.pw_dir == '/var/lib/enhanced-cognee-profiles/'+packet['profile_id'])
        PHASE = 'restore'
        archive = sys.stdin.buffer.read(packet['archive_bytes']+1)
        require(len(archive) == packet['archive_bytes'])
        destination,receipt = core['restore'](archive,owner_home=True)
        sys.stdout.buffer.write(canonical(dict(complete=True,destination=destination,receipt=receipt))+b'\n')


def owner(helper, account, source, packet, payload=b''):
    packet_shape(packet)
    require((packet['mode']=='capture' and payload == b'') or
        (packet['mode']=='restore' and isinstance(payload,bytes) and len(payload)==packet['archive_bytes']))
    _,public = helper['owner_program'](source)
    # The child can emit only a fixed error category; raw exception text is suppressed.
    program = ("import sys,json\nn={'__name__':'main_operational_owner'}\n"
        "exec(compile(sys.stdin.buffer.readline(65537),'<verified-public-owner>','exec'),n)\n"
        "try:\n n['child']()\n"
        "except Exception as e:\n"
        " k=type(e).__name__\n"
        " v={'complete':False,'phase':n.get('PHASE','identity'),"
        "'error_kind':k if k in {'CaptureError','ValueError','PermissionError','FileNotFoundError','CalledProcessError','TimeoutExpired','MemoryError'} else 'other'}\n"
        " if getattr(e,'checkpoint',None) in n['CORE_CHECKPOINTS']: v['capture_checkpoint']=e.checkpoint\n"
        " if getattr(e,'reason',None) in n['CORE_REASONS']: v['capture_reason']=e.reason\n"
        " print(json.dumps(v))\n"
        " raise SystemExit(1)\n")
    header = canonical(packet)
    require(len(public) <= HEADER and len(header) <= HEADER)
    result = subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',program],
        input=public+header+b'\n'+payload,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=300,cwd='/',
        user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    limit = CIPHER_LIMIT+HEADER+1 if packet['mode']=='capture' else HEADER
    require(0 < len(result.stdout) <= limit)
    head,separator,body = result.stdout.partition(b'\n')
    require(len(head) <= HEADER)
    value = json.loads(head)
    if result.returncode != 0 or value.get('complete') is not True:
        error = ValueError('owner_stopped_preserve_evidence')
        error.owner_phase = value.get('phase') if value.get('phase') in PHASES else 'identity'
        error.owner_kind = value.get('error_kind') if value.get('error_kind') in {
            'CaptureError','ValueError','PermissionError','FileNotFoundError','CalledProcessError','TimeoutExpired','MemoryError'} else 'other'
        if value.get('capture_checkpoint') in CORE_CHECKPOINTS:error.capture_checkpoint=value['capture_checkpoint']
        if value.get('capture_reason') in CORE_REASONS:error.capture_reason=value['capture_reason']
        raise error
    validate_owner_result(value,body,packet['mode'],account)
    return value,body


def validate_owner_result(value,body,mode,account):
    require(isinstance(value,dict) and value.get('complete') is True and isinstance(value.get('receipt'),dict))
    receipt=value['receipt']
    if mode == 'capture':
        require(set(value)=={'complete','receipt','ciphertext_bytes'} and type(value['ciphertext_bytes']) is int
            and value['ciphertext_bytes']==len(body) and 0 < len(body) <= CIPHER_LIMIT
            and body.startswith(b'age-encryption.org/v1\n'))
        require(set(receipt)=={'files','source_bytes','sqlite_databases','sidecars_rebuilt','database_versions_stable',
            'plain_files_stable','plaintext_archive_written','omitted_entries','source_profiles_preserved',
            'source_logical_writes_performed','sqlite_read_bookkeeping_may_change','full_profile_recovery_qualified','executable_rebuild_qualified',
            'database_snapshots_consistent','database_snapshot_mode','live_database_changes_observed','global_atomic_snapshot_qualified'}
            and all(receipt[k] is True for k in ('database_snapshots_consistent','plain_files_stable','source_profiles_preserved','sqlite_read_bookkeeping_may_change'))
            and type(receipt['database_versions_stable']) is bool
            and receipt['database_snapshot_mode']=='read_transaction_per_database'
            and type(receipt['live_database_changes_observed']) is int
            and 0 <= receipt['live_database_changes_observed'] <= receipt['sqlite_databases']
            and all(receipt[k] is False for k in ('plaintext_archive_written','source_logical_writes_performed','full_profile_recovery_qualified',
                'executable_rebuild_qualified','global_atomic_snapshot_qualified')))
        for field,maximum in [('files',20000),('source_bytes',512*1024*1024),('sqlite_databases',20000),('sidecars_rebuilt',40000),('omitted_entries',20000)]:
            require(type(receipt[field]) is int and 0 <= receipt[field] <= maximum)
    else:
        require(set(value)=={'complete','receipt','destination'} and not body
            and isinstance(value['destination'],str) and Path(value['destination']).parent == Path(account.pw_dir)
            and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}',Path(value['destination']).name))
        require(set(receipt)=={'complete','archived_files_verified','private_restore_verified','sqlite_databases_verified',
            'restored_profile_executed','operational_restore_qualified','full_profile_recovery_qualified','executable_rebuild_qualified',
            'database_snapshot_mode','global_atomic_snapshot_qualified'}
            and all(receipt[k] is True for k in ('complete','archived_files_verified','private_restore_verified','operational_restore_qualified'))
            and receipt['database_snapshot_mode']=='read_transaction_per_database'
            and all(receipt[k] is False for k in ('restored_profile_executed','full_profile_recovery_qualified','executable_rebuild_qualified',
                'global_atomic_snapshot_qualified'))
            and type(receipt['sqlite_databases_verified']) is int and 0 <= receipt['sqlite_databases_verified'] <= 20000)


def selected(read):
    raw=read(PLAN,0)
    require(hashlib.sha256(raw).hexdigest()==PLAN_SHA)
    plans=json.loads(raw)['profiles']
    require(len(plans)==45)
    account=pwd.getpwnam('vincentspereira')
    rows=[r for r in plans if r['source_user']==account.pw_name and r['source_profile']==str(Path(account.pw_dir)/'.hermes')]
    require(len(rows)==1)
    row=rows[0]
    require(row['enabled'] is False and row['existing_binding'] is None and row['source_uid']==account.pw_uid
        and row['profile_id']==hashlib.sha256((account.pw_name+'\0'+row['source_profile']).encode()).hexdigest()[:16]
        and row['proposed_user']=='ecbot_'+row['profile_id']
        and row['proposed_home']=='/var/lib/enhanced-cognee-profiles/'+row['profile_id'])
    target=pwd.getpwnam(row['proposed_user'])
    require(target.pw_uid>0 and target.pw_dir==row['proposed_home'] and target.pw_shell=='/usr/sbin/nologin'
        and os.getgrouplist(target.pw_name,target.pw_gid)==[target.pw_gid])
    return row,account,target


def properties(unit=None):
    result=subprocess.run(['/usr/bin/systemctl','show',unit or UNIT,'--property=LoadState,ActiveState,SubState,MainPID,ControlPID'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True)
    require(len(result.stdout)<=8192)
    return dict(line.split('=',1) for line in result.stdout.decode().splitlines() if '=' in line)


def quiescent(value):
    return (value.get('ActiveState'),value.get('SubState')) in {('inactive','dead'),('failed','failed')} and value.get('MainPID')==value.get('ControlPID')=='0'


def finish():
    if not quiescent(properties()):
        subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=True)
    return quiescent(properties())


def retained_failure(read,write=None,evidence=None):
    prior=BASE/'operator-evidence/main-operational-recovery-pi4m1pnq'
    result=json.loads(read(prior/'summary.json',0))
    require(result.get('complete') is False and result.get('failure_phase')=='capture'
        and result.get('owner_error_kind')=='CaptureError' and result.get('owner_phase')=='capture'
        and result.get('encrypted_generations_created')==result.get('disposable_restores_qualified')==0
        and result.get('generation_write_started') is False and result.get('restored_candidate_may_exist') is False
        and result.get('all_admission_policies_preserved_disabled') is True)
    require(quiescent(properties('ec-launch-main-operational-recovery-20261026.service')))
    frozen=json.loads(read(BASE/'operator-main-operational-recovery-v1/sources.json',0))
    require(frozen.get('backup_launch_main_operational.py')=='a91b128650b80acf8bcc4d369365daad8d0bba8fdd298e80ffa08e6e4d3e0f9a'
        and frozen.get('capture_main_operational_profile_v2.py')=='52838907100b39dc689efb82afea7097b1002283c511d690ffd8d4cdc0b723e3')
    if write is not None:
        write(evidence/'retained-zero-generation-failure.json',canonical(dict(previous=str(prior),
            failure_preserved=True,prior_generation_count=0,prior_restore_count=0,prior_job_quiescent=True)))


def worker(read,write):
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('main-operational-recovery-[A-Za-z0-9_-]{6,64}',evidence.name))
    row,source_account,target=selected(read)
    retained_failure(read,write,evidence)
    helper=definitions(ARTIFACT/'qualify_launch_isolated_accounts.py',PINS['qualify_launch_isolated_accounts.py'])
    core=(ARTIFACT/'capture_main_operational_profile_v3.py').read_bytes()
    require(hashlib.sha256(core).hexdigest()==CORE_SHA)
    code=Path(__file__).read_bytes()
    policies=[Path('/etc/enhanced-cognee/fleet-credentials.json'),BASE/'operator-isolated-issuer-candidate-v3/candidate-policy.json']
    before={path:read(path,0) for path in policies}
    require(all(r['enabled'] is False for raw in before.values() for r in json.loads(raw)['profiles']))
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,source_profiles_changed=False,
        source_logical_writes=False,sqlite_read_bookkeeping_may_change=True,credentials_issued=0,model_called=False,
        existing_launchers_changed=False,production_renewal_timer_enabled=False,main_profile_backup_qualified=False,
        full_profile_recovery_qualified=False,executable_rebuild_qualified=False,actual_profile_admission_qualified=False,
        global_atomic_snapshot_qualified=False,
        fleet_launch_approved=False,encrypted_generations_created=0,disposable_restores_qualified=0,
        operator_helper_sha256=hashlib.sha256(code).hexdigest(),
        generation_write_started=False,restored_candidate_may_exist=False)
    write(evidence/'started.json',canonical(result))
    phase='capture'
    try:
        settings=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))
        recipient,key,key_id=(settings[k] for k in ('ENHANCED_BACKUP_RECIPIENT','ENHANCED_BACKUP_SIGNING_KEY','ENHANCED_BACKUP_SIGNING_KEY_ID'))
        require(isinstance(key,str) and len(key.encode())>=32 and isinstance(key_id,str) and re.fullmatch('[A-Za-z0-9_-]{1,64}',key_id))
        key=key.encode();del settings
        packet=dict(mode='capture',profile_id=row['profile_id'],core=core.decode(),recipient=recipient)
        captured,ciphertext=owner(helper,source_account,code,packet)
        phase='signed_generation'
        generation=BACKUPS/('hermes_main_operational_'+uuid.uuid4().hex+'.tar.age')
        write(evidence/'generation.started.json',canonical({'generation':str(generation)}))
        manifest=dict(format='hermes-main-operational-profile-sqlite+age-v2',complete=True,source_profile_id=row['profile_id'],
            created_utc=datetime.now(timezone.utc).isoformat(),ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),
            capture_component_sha256=CORE_SHA,signing_key_id=key_id,receipt=captured['receipt'])
        manifest['signature']=hmac.new(key,canonical(manifest),hashlib.sha256).hexdigest()
        result['generation_write_started']=True
        write(generation,ciphertext);write(generation.with_name(generation.name+'.json'),canonical(manifest));sync(BACKUPS)
        result['encrypted_generations_created']=1
        del ciphertext
        saved=read(generation,0,CIPHER_LIMIT)
        signed=json.loads(read(generation.with_name(generation.name+'.json'),0))
        require(signed==manifest and signed['ciphertext_sha256']==hashlib.sha256(saved).hexdigest()
            and hmac.compare_digest(signed['signature'],hmac.new(key,canonical({k:v for k,v in signed.items() if k!='signature'}),hashlib.sha256).hexdigest()))
        del key
        phase='decryption'
        decrypted=subprocess.run([str(AGE),'--decrypt','--identity',str(IDENTITY)],input=saved,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,timeout=90,check=True,cwd='/',env={'PATH':'/usr/bin:/bin','HOME':'/'})
        del saved
        require(0 < len(decrypted.stdout)<=ARCHIVE_LIMIT)
        phase='disposable_restore'
        result['restored_candidate_may_exist']=True
        restored,_=owner(helper,target,code,dict(mode='restore',profile_id=row['profile_id'],core=core.decode(),archive_bytes=len(decrypted.stdout)),decrypted.stdout)
        require(restored['receipt']['sqlite_databases_verified']==captured['receipt']['sqlite_databases'])
        write(evidence/'restore.private.json',canonical(restored))
        result.update(complete=True,disposable_restores_qualified=1,main_operational_snapshot_restore_qualified=True,
            generation=str(generation),sqlite_databases_recovered=restored['receipt']['sqlite_databases_verified'],
            omitted_entries=captured['receipt']['omitted_entries'])
        result.update(database_snapshots_consistent=captured['receipt']['database_snapshots_consistent'],
            live_database_changes_observed=captured['receipt']['live_database_changes_observed'],
            database_snapshot_mode=captured['receipt']['database_snapshot_mode'])
    except Exception as error:
        result.update(category='main_operational_recovery_incomplete_preserve_evidence',failure_phase=phase)
        if getattr(error,'owner_phase',None) in PHASES:
            result.update(owner_phase=error.owner_phase,owner_error_kind=error.owner_kind)
        if getattr(error,'capture_checkpoint',None) in CORE_CHECKPOINTS:result['capture_checkpoint']=error.capture_checkpoint
        if getattr(error,'capture_reason',None) in CORE_REASONS:result['capture_reason']=error.capture_reason
    require(all(read(path,0)==raw for path,raw in before.items()))
    result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result));sync(evidence)
    return 0 if result['complete'] else 1


def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def watch(read):
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('main-operational-recovery-[A-Za-z0-9_-]{6,64}',evidence.name))
    last=0;began=time.monotonic()
    try:
        while True:
            value=properties()
            try:result=json.loads(read(evidence/'summary.json',0))
            except FileNotFoundError:result=None
            if result is not None or value.get('ActiveState')=='failed' or value.get('SubState')=='exited':
                result=result or dict(complete=False,evidence=str(evidence),category='main_worker_exited_preserve_evidence')
                result['operator_job_stopped']=finish()
                result['complete']=result.get('complete') is True and result['operator_job_stopped']
                print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            if quiescent(value) and time.monotonic()-began > 30:
                print(json.dumps(dict(complete=False,evidence=str(evidence),category='main_worker_not_running_preserve_evidence')),flush=True)
                return 1
            if time.monotonic()-last>=15:
                print('{"event":"main_operational_recovery_running","note":"Ctrl+C detaches; repeat continue-main-backup to reattach."}',flush=True)
                last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True,job_continues=True,evidence=str(evidence))),flush=True);return 0


def launch():
    require(os.geteuid()==0)
    directory=Path(__file__).parent
    shared=definitions(directory/'recover_launch_graph_operator.py',PINS['recover_launch_graph_operator.py'])
    read,write=shared['read_file'],shared['private_write']
    if os.path.lexists(ARTIFACT):return watch(read)
    retained_failure(read)
    row,_,target=selected(read)
    require(properties().get('LoadState')=='not-found' and quiescent(properties()))
    driver=definitions(BASE/'operator-issuer-candidate-v2/renew_fleet_credentials.py','a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    for path in (AGE,IDENTITY,BACKUPS):driver['protected'](path)
    sources={Path(__file__).name:globals()['_verified_source_bytes']}
    for name,digest in PINS.items():sources[name]=definitions(directory/name,digest)['_verified_source_bytes']
    evidence=Path(tempfile.mkdtemp(prefix='main-operational-recovery-',dir=BASE/'operator-evidence'))
    ARTIFACT.mkdir(mode=0o700)
    for name,raw in sources.items():write(ARTIFACT/name,raw)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    write(ARTIFACT/'context.json',canonical({'evidence':str(evidence)}));sync(ARTIFACT);sync(evidence)
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='',ProtectHome='no',ProtectSystem='strict',
        PrivateTmp='no',ReadWritePaths=' '.join([str(BASE/'operator-evidence'),str(BACKUPS),target.pw_dir,'/home/vincentspereira/.hermes']),
        Restart='no',TimeoutStartSec='900',MemoryMax='8G',LimitAS=str(6*1024**3),LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+k+'='+v for k,v in settings.items()]
    args += [str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/Path(__file__).name),'--worker']
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=True)
    return watch(read)


if __name__=='__main__':
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        require(sys.argv[1:]==['--worker'])
        shared=definitions(ARTIFACT/'recover_launch_graph_operator.py',PINS['recover_launch_graph_operator.py'])
        raise SystemExit(worker(shared['read_file'],shared['private_write']))
    except Exception:
        print('{"complete":false,"category":"main_operational_recovery_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
