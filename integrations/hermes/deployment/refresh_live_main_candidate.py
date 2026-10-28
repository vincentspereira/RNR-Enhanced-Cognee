"""One detached, immutable job: refresh live main state into a NEW inactive copy.

Preserve source, previous candidate, policies and all completed qualifications.
Retain the original strict V3 refusal. V4 excludes only reviewed display/log
outputs; durable files and per-database read transactions stay strict.
Root handles protected signing/recovery only;
owners alone open their profile files and return bounded encrypted payloads.
"""
from __future__ import annotations
from datetime import datetime,timezone
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

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
PACKAGE=BASE/'operator-launch-completion-batch-v2'
ARTIFACT=BASE/'operator-main-live-reconciliation-v2'
BACKUPS=Path('/var/backups/enhanced-cognee')
UNIT='ec-main-live-reconciliation-v2-20261028.service'
OWNER_SHA='291f6e5f81a027c89473fedfc7bdf3275d2f00678bd3f655e47e74df7725b2b2'
DELIVERY_SHA='d325f3f4f5c82aa672cc7f390491a0ee2018729e63c9a1576878bec2f402790d'
SUPPORT_SHA='d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
DRIVER_SHA='d99a819e0c64a5e0d60632f15c8ff3fb57cbf294c4ed33865605702b5796becc'
HELPER_SHA='d0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94'
PHASES=('current_configuration_capture','live_source_capture','model_binding','new_candidate_prepare',
 'configured_candidate_capture','configured_candidate_restore','source_freshness')
MAX_CIPHER=650*1024**2
KINDS={'ValueError','PermissionError','FileNotFoundError','CaptureError','ProvisionError','CalledProcessError',
 'TimeoutExpired','OSError','RuntimeError','TypeError','KeyError','AuthError'}


def require(value):
    if not value:raise ValueError('current_main_reconciliation_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    scope={'__name__':'verified_current_main_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-current-main-support>','exec'),scope)
    return scope


def legacy():
    scope=definitions(BASE/'operator-launch-completion-batch-v1/launch_completion_batch.py',DRIVER_SHA)
    scope['ARTIFACT']=PACKAGE
    return scope


def metadata():
    result=subprocess.run(['/usr/bin/systemctl','show',UNIT,
        '--property=LoadState,ActiveState,SubState,MainPID,ControlPID,User,Result,ExecMainStatus,InvocationID'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=10)
    require(len(result.stdout)<=8192)
    return dict(line.split('=',1) for line in result.stdout.decode().splitlines() if '=' in line)


def stopped(value):return value.get('MainPID')==value.get('ControlPID')=='0' and value.get('ActiveState') in {'inactive','failed'}


def owner(account,source,packet,*,body=b'',limit=MAX_CIPHER+65537):
    helper=definitions(PACKAGE/'qualify_launch_isolated_accounts.py',HELPER_SHA)
    code,line=helper['owner_program'](source)
    require(code.count("n['child']()")==1 and code.count('import sys\n')==1)
    # The wrapper projects failures, never raw exceptions/private paths.
    code=code.replace("n['child']()", "try: n['child']()\nexcept Exception as e:\n"
        " k=type(e).__name__;v={'complete':False,'phase':n.get('PHASE','identity'),'error_kind':k if k in "+repr(KINDS)+" else 'other'}\n"
        " print(json.dumps(v));raise SystemExit(1)")
    require('import sys\n' in code);code=code.replace('import sys\n','import sys,json\n',1)
    process=subprocess.Popen(['/usr/bin/setpriv','--no-new-privs','--inh-caps=-all','--ambient-caps=-all','--',
        helper['EXECUTABLE'],'-I','-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        user=account.pw_uid,group=account.pw_gid,extra_groups=(),cwd='/',
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    try:
        result,_=process.communicate(line+canonical(packet)+b'\n'+body,timeout=360)
        require(0<len(result)<=limit)
        head,separator,payload=result.partition(b'\n')
        require(len(head)<=65536)
        value=json.loads(head)
        if process.returncode!=0 or not isinstance(value,dict) or value.get('complete') is not True:
            error=ValueError('current_main_owner_incomplete')
            projected=dict(error_kind='other',phase='other')
            if isinstance(value,dict):
                if isinstance(value.get('error_kind'),str) and value['error_kind'] in KINDS:projected['error_kind']=value['error_kind']
                if isinstance(value.get('phase'),str) and value['phase'] in {
                    'identity','source_configuration','source_encryption','source_operational_capture','source_operational_encryption','previous_candidate_restore','current_configuration_prepare',
                    'new_candidate_configuration','configured_candidate_capture','configured_candidate_encryption','configured_candidate_restore'}:
                    projected['phase']=value['phase']
            error.owner_diagnostic=projected;raise error
        if limit==65536:require(not payload)
        return value,payload
    finally:
        if process.poll() is None:process.kill()
        process.wait(timeout=10)


def packet(account,mode,**values):return dict(mode=mode,uid=account.pw_uid,gid=account.pw_gid,**values)


def generation(kind,value,body,settings,read,write):
    require(kind in {'configuration','live_source','configured'} and isinstance(value,dict) and value.get('complete') is True
        and type(value.get('ciphertext_bytes')) is int and value['ciphertext_bytes']==len(body)
        and 0<len(body)<=MAX_CIPHER and body.startswith(b'age-encryption.org/v1\n'))
    key=settings['ENHANCED_BACKUP_SIGNING_KEY'].encode()
    require(len(key)>=32 and re.fullmatch('[A-Za-z0-9_-]{1,64}',settings['ENHANCED_BACKUP_SIGNING_KEY_ID']))
    manifest=dict(format='hermes-live-main-'+kind+'+age-v1',source_revision=BASE.name,
        created_utc=datetime.now(timezone.utc).isoformat(),ciphertext_sha256=hashlib.sha256(body).hexdigest(),
        signing_key_id=settings['ENHANCED_BACKUP_SIGNING_KEY_ID'],receipt=value['receipt'])
    manifest['signature']=hmac.new(key,canonical(manifest),hashlib.sha256).hexdigest()
    destination=BACKUPS/('hermes_main_live_'+kind+'_'+uuid.uuid4().hex+('.json.age' if kind=='configuration' else '.tar.age'))
    write(destination,body);write(destination.with_name(destination.name+'.json'),canonical(manifest))
    fd=os.open(BACKUPS,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    saved=read(destination,0,MAX_CIPHER);signed=json.loads(read(destination.with_name(destination.name+'.json'),0))
    require(signed==manifest and hashlib.sha256(saved).hexdigest()==signed['ciphertext_sha256']
        and hmac.compare_digest(signed['signature'],hmac.new(key,canonical({k:v for k,v in signed.items() if k!='signature'}),hashlib.sha256).hexdigest()))
    return destination,saved


def decrypt(ciphertext,*,configuration=False):
    result=subprocess.run(['/usr/local/bin/age','--decrypt','--identity','/etc/enhanced-cognee/age-recovery-identity.txt'],
        input=ciphertext,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=90,
        cwd='/',env={'PATH':'/usr/bin:/bin','HOME':'/'})
    require(0<len(result.stdout)<=(1100*1024 if configuration else 600*1024**2))
    return result.stdout


def retained_delivery(read):
    context=json.loads(read(BASE/'operator-isolated-delivery-recovery-v1/context.private.json',0))
    require(context.get('source_sha256')==DELIVERY_SHA)
    evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('isolated-delivery-'))
    passed=json.loads(read(evidence/'summary.json',0))
    require(passed.get('complete') is True and passed.get('source_revision')==BASE.name
        and passed.get('operator_helper_sha256')==DELIVERY_SHA and passed.get('completed_phases')==4
        and passed.get('binding_manifest_sha256')==context.get('bindings_sha256')
        and all(passed.get(key) is True for key in ('durable_no_replay_component_qualified',
            'native_base_adapter_text_component_qualified','peer_journal_os_denial_qualified',
            'two_actual_forced_process_exits','all_admission_policies_preserved_disabled'))
        and all(passed.get(key) is False for key in ('fleet_launch_approved','source_profiles_changed',
            'real_profile_contents_read','keys_read','model_called','memory_api_called','services_installed','canonical_memory_edits'))
        and passed.get('credentials_issued')==passed.get('external_platform_sends')==0)
    return str(evidence)



def retained_configuration(read):
    """Reuse the owner's completed six-definition settings/recovery receipt."""
    artifact=BASE/'operator-main-current-reconciliation-v1'
    context=json.loads(read(artifact/'context.private.json',0))
    require(context.get('source_sha256')=='a97d14c49ca7ebc41b9935e2f296479226c76f37d690eee0203ccb3e5cb7efea')
    evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-current-'))
    result=json.loads(read(evidence/'finish.summary.json',0))
    require(result.get('source_revision')==BASE.name and result.get('operator_helper_sha256')==context['source_sha256']
        and result.get('complete') is True and result.get('operator_job_stopped') is True
        and result.get('main_current_configuration_reconciled') is True
        and result.get('configured_candidate_restore_qualified') is True
        and result.get('current_settings_and_oauth_preserved') is True
        and result.get('all_admission_policies_preserved_disabled') is True
        and all(result.get(k) is False for k in ('candidate_promoted','daily_backup_registry_changed',
            'fleet_launch_approved','source_profiles_changed','production_renewal_timer_enabled')))
    return str(evidence)


def runtime_model(driver,read,write,evidence):
    driver['verify_runtime']()
    account=pwd.getpwnam('vincentspereira')
    route_source=(PACKAGE/'bind_launch_model_route.py').read_bytes()
    require(hashlib.sha256(route_source).hexdigest()=='edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52')
    authority,body=owner(account,route_source,dict(mode='read_source'),limit=65536)
    require(not body and set(authority)=={'complete','key','endpoint_path'} and authority['endpoint_path']=='/api/coding/paas/v4')
    source=(PACKAGE/'inspect_qualified_model_key.py').read_bytes()
    require(hashlib.sha256(source).hexdigest()=='fc739ef3ba7fc9f670a618242769fb3ddafa2c191b384eb28bd0ea1684862ea9')
    previous=BASE/'operator-evidence/model-recall-finish-fdu97vca/summary.json'
    passed=json.loads(read(previous,0))
    require(passed.get('complete') is True and passed.get('operator_helper_sha256')=='ddf3b82e294b7b723463a82a66098fb6d52edd370f9fd1344696368b500a0123'
        and passed.get('current_configured_model_fresh_process_recall_qualified') is True)
    binding,body=owner(pwd.getpwnam('hermes-runtime'),source,dict(completed_ns=previous.stat().st_mtime_ns),limit=65536)
    require(not body and set(binding)=={'complete','model_key_sha256','fixture_unchanged_since_receipt'}
        and binding.get('fixture_unchanged_since_receipt') is True
        and binding['model_key_sha256']==hashlib.sha256(authority['key'].encode()).hexdigest())
    write(evidence/'qualified-model-binding.private.json',canonical(binding))
    return authority['key']


def worker():
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    support=definitions(PACKAGE/'recover_launch_graph_operator.py',SUPPORT_SHA);read,write=support['read_file'],support['private_write']
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-live-'))
    owner_source=(ARTIFACT/'main_live_reconciliation_owner.py').read_bytes();require(hashlib.sha256(owner_source).hexdigest()==OWNER_SHA)
    driver=legacy();before=driver['policies'](read);entry,row=driver['fixed_entry'](read)
    account=pwd.getpwnam(entry['user']);source_account=pwd.getpwnam('vincentspereira')
    result=dict(complete=False,source_revision=BASE.name,evidence=str(evidence),operator_helper_sha256=context['source_sha256'],
        source_profiles_changed=False,previous_candidate_changed=False,candidate_promoted=False,daily_backup_registry_changed=False,
        source_read_bookkeeping_may_change=True,sqlite_read_bookkeeping_may_change=True,
        credentials_issued=0,encryption_or_recovery_keys_changed=False,private_keys_sent_to_owner=False,
        chat_model_called=False,mcp_servers_started=0,platform_adapters_started=0,canonical_memory_edits=False,
        production_renewal_timer_enabled=False,production_dispatch_qualified=False,main_tool_program_coverage_qualified=False,
        current_source_operational_refresh_qualified=False,actual_profile_admission_qualified=False,fleet_launch_approved=False,
        full_profile_recovery_qualified=False,executable_rebuild_qualified=False,global_atomic_snapshot_qualified=False,
        encrypted_generations_created=0,automatic_retry=False,invocation_id=os.environ.get('INVOCATION_ID',''))
    try:
        require(re.fullmatch('[a-f0-9]{32}',result['invocation_id']) is not None)
        settings=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0));recipient=settings['ENHANCED_BACKUP_RECIPIENT']
        def checkpoint(name):write(evidence/(name+'.started.json'),canonical(dict(phase=name)))
        checkpoint('current_configuration_capture')
        current,body=owner(source_account,owner_source,packet(source_account,'capture_source',recipient=recipient))
        require(set(current)=={'complete','receipt','fingerprints','mcp_definitions','source_configuration_preserved','ciphertext_bytes'}
            and current['source_configuration_preserved'] is True and type(current['mcp_definitions']) is int and 1<=current['mcp_definitions']<=128
            and current['receipt'].get('files')==3 and current['receipt'].get('plaintext_archive_written') is False)
        require(isinstance(current['fingerprints'],dict) and set(current['fingerprints'])=={'config.yaml','.env','auth.json'}
            and all(isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) for value in current['fingerprints'].values()))
        path,ciphertext=generation('configuration',current,body,settings,read,write);result['encrypted_generations_created']+=1
        write(evidence/'source-configuration.private.json',canonical(current));capsule=decrypt(ciphertext,configuration=True)
        checkpoint('live_source_capture')
        prior,body=owner(source_account,owner_source,packet(source_account,'capture_live_source',recipient=recipient,fingerprints=current['fingerprints']))
        driver['definitions'](PACKAGE/'continue_launch_main_operational.py',driver['PINS']['continue_launch_main_operational.py'])['validate_owner_result'](prior,body,'capture',source_account)
        path,ciphertext=generation('live_source',prior,body,settings,read,write);result['encrypted_generations_created']+=1
        result['source_generation']=str(path)
        result['source_sqlite_databases']=prior['receipt']['sqlite_databases']
        archive=decrypt(ciphertext)
        checkpoint('model_binding');key=runtime_model(driver,read,write,evidence)
        bundle=driver['fresh_bundle'](entry);result['credentials_issued']=2
        checkpoint('new_candidate_prepare')
        prepared,empty=owner(account,owner_source,packet(account,'prepare',entry=entry,archive_bytes=len(archive),capsule_bytes=len(capsule),
            fingerprints=current['fingerprints'],bundle=bundle,model_key=key,id=context['id']),body=capsule+archive,limit=65536)
        del key,bundle,archive,capsule
        require(not empty and prepared.get('mcp_definitions')==current['mcp_definitions']
            and prepared.get('current_settings_and_oauth_preserved') is True and prepared.get('source_fingerprints_match') is True
            and prepared.get('scoped_status_authenticated') is True and prepared.get('previous_operational_state_reused') is False
            and prepared.get('current_source_operational_refresh_qualified') is True)
        destination=Path(prepared['destination']);require(destination.parent==Path(account.pw_dir)
            and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}',destination.name))
        write(evidence/'new-candidate.private.json',canonical(prepared))
        checkpoint('configured_candidate_capture')
        captured,body=owner(account,owner_source,packet(account,'capture_candidate',entry=entry,destination=str(destination),recipient=recipient))
        capture_validator=driver['definitions'](PACKAGE/'continue_launch_main_operational.py',driver['PINS']['continue_launch_main_operational.py'])['validate_owner_result']
        capture_validator(captured,body,'capture',account)
        generation_path,ciphertext=generation('configured',captured,body,settings,read,write);result['encrypted_generations_created']+=1
        archive=decrypt(ciphertext)
        checkpoint('configured_candidate_restore')
        restored,empty=owner(account,owner_source,packet(account,'restore_candidate',entry=entry,destination=str(destination),
            archive_bytes=len(archive),id=context['restore_id']),body=archive,limit=65536)
        del archive
        require(not empty and restored.get('mcp_definitions')==current['mcp_definitions']
            and all(restored.get(key) is True for key in ('workspace_rebased','restored_scope_authenticated','oauth_and_environment_preserved'))
            and restored.get('receipt',{}).get('operational_restore_qualified') is True
            and restored['receipt'].get('pinned_provider_binding_reconstructed') is True
            and restored['receipt'].get('sqlite_databases_verified')==captured['receipt']['sqlite_databases'])
        write(evidence/'configured-restore.private.json',canonical(restored))
        checkpoint('source_freshness')
        verified,empty=owner(source_account,owner_source,packet(source_account,'verify_source',fingerprints=current['fingerprints']),limit=65536)
        require(not empty and verified==dict(complete=True,source_current_at_completion=True))
        result.update(complete=True,main_current_configuration_reconciled=True,mcp_definitions_preserved=current['mcp_definitions'],
            current_settings_and_oauth_preserved=True,source_current_at_completion=True,scoped_status_authenticated=True,
            configured_candidate_restore_qualified=True,sqlite_databases_recovered=restored['receipt']['sqlite_databases_verified'],
            new_inactive_candidate=str(destination),generation=str(generation_path),previous_operational_state_reused=False,
            current_source_operational_refresh_qualified=True,telemetry_display_projection_reviewed=True,
            durable_plain_files_stable=prior['receipt']['plain_files_stable'],
            database_snapshot_mode=prior['receipt']['database_snapshot_mode'],
            global_atomic_snapshot_qualified=False,
            remaining_reference_count=prepared['remaining_reference_count'])
    except Exception as error:
        result.update(category='main_current_reconciliation_incomplete_preserve_evidence_no_automatic_retry',
            error_kind=type(error).__name__ if type(error).__name__ in KINDS else 'other',
            new_candidate_may_exist=os.path.lexists(evidence/'new_candidate_prepare.started.json'))
        if isinstance(getattr(error,'owner_diagnostic',None),dict):result['owner_diagnostic']=error.owner_diagnostic
    require(all(read(path,0)==raw for path,raw in before.items()))
    result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result))
    return 0 if result['complete'] else 1


def watch(read,write):
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-live-'))
    if os.path.lexists(evidence/'finish.summary.json'):
        result=json.loads(read(evidence/'finish.summary.json',0));require(result.get('operator_job_stopped') is True
            and result.get('operator_helper_sha256')==context['source_sha256'] and result.get('source_revision')==BASE.name)
        print(json.dumps(result),flush=True);return 0 if result.get('complete') is True else 1
    last=0;start=time.monotonic()
    try:
        while time.monotonic()-start<1900:
            state=metadata()
            if os.path.lexists(evidence/'summary.json') and (state.get('SubState')=='exited' or stopped(state)):
                result=json.loads(read(evidence/'summary.json',0))
                require(result.get('source_revision')==BASE.name and result.get('operator_helper_sha256')==context['source_sha256'])
                if result['complete']:require(state.get('Result')=='success' and state.get('ExecMainStatus')=='0'
                    and state.get('User')=='root' and state.get('InvocationID')==result.get('invocation_id'))
                subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
                require(stopped(metadata()))
                result['operator_job_stopped']=True;write(evidence/'finish.summary.json',canonical(result))
                print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            require(not stopped(state))
            if time.monotonic()-last>=10:
                phases=[phase for phase in PHASES if os.path.lexists(evidence/(phase+'.started.json'))]
                print(json.dumps(dict(event='main_current_reconciliation_running',checkpoint=phases[-1] if phases else 'starting',
                    note='Ctrl+C detaches; repeat refresh-main-live-state to reattach.')),flush=True);last=time.monotonic()
            time.sleep(2)
        raise ValueError('current_main_watch_deadline')
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True,job_continues=True,evidence=str(evidence))),flush=True);return 0


def launch():
    require(os.geteuid()==0);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory=Path(__file__).parent
    support=definitions(PACKAGE/'recover_launch_graph_operator.py',SUPPORT_SHA);read,write=support['read_file'],support['private_write']
    source=globals()['_verified_source_bytes'];source_sha=hashlib.sha256(source).hexdigest()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0));require(context.get('source_sha256')==source_sha)
        manifest=json.loads(read(ARTIFACT/'sources.json',0))
        require(manifest.get('refresh_live_main_candidate.py')==source_sha and manifest.get('main_live_reconciliation_owner.py')==OWNER_SHA)
        for name,digest in manifest.items():require(re.fullmatch(r'[a-z0-9_]+\.py',name)
            and hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==digest)
        return watch(read,write)
    previous=retained_delivery(read);configuration=retained_configuration(read)
    driver=legacy();before=driver['policies'](read);entry,row=driver['fixed_entry'](read)
    require(metadata().get('LoadState')=='not-found' and shutil.disk_usage(BACKUPS).free>=3*1024**3 and not os.path.lexists(ARTIFACT))
    owned=definitions(directory/'main_live_reconciliation_owner.py',OWNER_SHA)
    sources={'refresh_live_main_candidate.py':source,'main_live_reconciliation_owner.py':owned['_verified_source_bytes']}
    for name,digest in owned['PINS'].items():
        origin=directory if name in {'current_main_configuration.py','inspect_launch_main_references.py','capture_main_operational_profile_v4.py'} else PACKAGE
        sources[name]=definitions(origin/name,digest)['_verified_source_bytes']
    protected=driver['definitions'](PACKAGE/'renew_fleet_credentials.py',driver['DRIVER_SHA'])['protected']
    executable=BASE/'runtime/bin/python';protected(executable,final_link=True);protected(executable.resolve(strict=True))
    for path in (BACKUPS,Path('/usr/local/bin/age'),Path('/etc/enhanced-cognee/age-recovery-identity.txt'),Path('/usr/bin/setpriv')):protected(path)
    ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    for name,raw in sources.items():write(ARTIFACT/name,raw);(ARTIFACT/name).chmod(0o644)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    evidence=Path(tempfile.mkdtemp(prefix='main-live-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=source_sha,evidence=str(evidence),
        id=uuid.uuid4().hex,restore_id=uuid.uuid4().hex,reused_delivery_evidence=previous,
        reused_configuration_evidence=configuration)))
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='CAP_SETUID CAP_SETGID',ProtectSystem='strict',
        # The source owner's read-only SQLite connections may create WAL/SHM
        # bookkeeping. Query-only/read transactions still forbid logical edits.
        ProtectHome='no',PrivateTmp='yes',ReadWritePaths=' '.join([str(BASE/'operator-evidence'),str(BACKUPS),
            entry['home'],'/home/vincentspereira/.hermes']),
        Restart='no',TimeoutStartSec='1800',MemoryMax='8G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]
    args+=['--property='+key+'='+value for key,value in settings.items()]
    args+=[str(executable),'-I','-B',str(ARTIFACT/'refresh_live_main_candidate.py'),'--worker']
    require(all(read(path,0)==raw for path,raw in before.items()))
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    return watch(read,write)


if __name__=='__main__':
    try:
        require(sys.argv[1:]==['--worker']);raise SystemExit(worker())
    except Exception:
        print('{"complete":false,"category":"main_current_worker_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
