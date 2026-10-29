"""One finite protected job: REA dependencies, isolated execution and new recovery.

Retain completed live-state qualification. Root never reads an owner program or
profile tree; owner children hand off exact pinned public archives/private pipes.
No candidate promotion, live REA server, platform adapter or renewal is enabled.
"""
from __future__ import annotations
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
LIVE=BASE/'operator-main-live-reconciliation-v2'
ARTIFACT=BASE/'operator-rea-main-programs-v1'
PROGRAM_ROOT=Path('/opt/hermes-runtime/programs')
UNIT='ec-rea-main-programs-v1-20261028.service'
LIVE_SHA='eab1072a0906d6bf48d6bc6e7450948130187abf88fd591fb3f8db286971387a'
OWNER_SHA='25ed007609af9d86b6f0386e340ef7265ef325e3f8d295185bfd809f7468128f'
SNAPSHOT_SHA='b180a6e83e9a00a7e287645adb3ea82db4455319029c44e2dc2d20e10087a42c'
PROBE_SHA='e8d5f1b1478f40bac936c7227fcad35a41978865f78bae585c0fd4ad3a2fd9d9'
PHASES=('public_programs','isolated_program_execution','new_candidate','configured_backup','configured_restore')


def require(value):
    if not value:raise ValueError('rea_main_programs_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    value={'__name__':'verified_rea_operator_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-rea-operator-support>','exec'),value)
    return value


def common():return definitions(LIVE/'refresh_live_main_candidate.py',LIVE_SHA)


def support(c):
    value=c['definitions'](c['PACKAGE']/'recover_launch_graph_operator.py',c['SUPPORT_SHA'])
    return value['read_file'],value['private_write']


def metadata(unit):
    out=subprocess.run(['/usr/bin/systemctl','show',unit,'--property=LoadState,ActiveState,SubState,MainPID,ControlPID,User,Result,ExecMainStatus,InvocationID,PrivateNetwork,ProtectHome,NoNewPrivileges'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=15)
    require(len(out.stdout)<=8192)
    return dict(line.split('=',1) for line in out.stdout.decode().splitlines() if '=' in line)


def stopped(value):return value.get('MainPID')==value.get('ControlPID')=='0' and value.get('ActiveState') in {'inactive','failed'}


def retained_live(read):
    context=json.loads(read(LIVE/'context.private.json',0));require(context['source_sha256']==LIVE_SHA)
    evidence=Path(context['evidence']);require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-live-'))
    result=json.loads(read(evidence/'finish.summary.json',0))
    require(result.get('operator_helper_sha256')==LIVE_SHA and result.get('source_revision')==BASE.name
        and all(result.get(k) is True for k in ('complete','operator_job_stopped','current_source_operational_refresh_qualified',
            'configured_candidate_restore_qualified','current_settings_and_oauth_preserved','all_admission_policies_preserved_disabled'))
        and all(result.get(k) is False for k in ('candidate_promoted','daily_backup_registry_changed','fleet_launch_approved',
            'source_profiles_changed','production_renewal_timer_enabled','previous_operational_state_reused')))
    return result


def authenticated_profile_archive(c,read,result):
    path=Path(result['generation']);require(path.parent==c['BACKUPS']
        and re.fullmatch(r'hermes_main_live_configured_[a-f0-9]{32}\.tar\.age',path.name))
    manifest=json.loads(read(path.with_name(path.name+'.json'),0))
    key=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))['ENHANCED_BACKUP_SIGNING_KEY'].encode()
    signature=manifest.pop('signature');require(isinstance(signature,str)
        and hmac.compare_digest(signature,hmac.new(key,canonical(manifest),hashlib.sha256).hexdigest())
        and manifest.get('format')=='hermes-live-main-configured+age-v1' and manifest.get('source_revision')==BASE.name)
    body=read(path,0,c['MAX_CIPHER']);require(hashlib.sha256(body).hexdigest()==manifest['ciphertext_sha256'])
    return c['decrypt'](body)


def program_probe(context,account,programs,read,write):
    unit='ec-rea-program-proof-'+context['id']+'.service'
    home=Path('/run')/('ec-rea-program-proof-'+context['id'])
    source=(ARTIFACT/'probe_rea_public_programs.py').read_bytes();require(hashlib.sha256(source).hexdigest()==PROBE_SHA)
    public=PROGRAM_ROOT/('proof-driver-'+context['id']);public.mkdir(mode=0o755);public.chmod(0o755)
    write(public/'probe.py',source);(public/'probe.py').chmod(0o644)
    require(metadata(unit).get('LoadState')=='not-found')
    settings=dict(Type='oneshot',RemainAfterExit='yes',User=account.pw_name,Group=account.pw_gid,
        NoNewPrivileges='yes',CapabilityBoundingSet='',AmbientCapabilities='',UMask='0077',
        PrivateNetwork='yes',IPAddressDeny='any',RestrictAddressFamilies='AF_UNIX',ProtectHome='yes',
        ProtectSystem='strict',PrivateTmp='yes',RuntimeDirectory=home.name,RuntimeDirectoryMode='0700',
        RuntimeDirectoryPreserve='yes',ReadWritePaths=str(home),TimeoutStartSec='240',MemoryMax='3G',
        InaccessiblePaths='/var/lib/enhanced-cognee-profiles /etc/enhanced-cognee /var/backups/enhanced-cognee /opt/enhanced-cognee-memory',
        Restart='no',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+unit]
    args+=['--property='+key+'='+str(value) for key,value in settings.items()]
    args+=['/usr/bin/python3','-I','-B',str(public/'probe.py'),programs['ghidra'],programs['java'],str(home)]
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    try:
        deadline=time.monotonic()+260
        while time.monotonic()<deadline:
            state=metadata(unit)
            if state.get('SubState')=='exited' or stopped(state):break
            time.sleep(2)
        else:raise ValueError('rea_program_probe_deadline')
        require(state.get('Result')=='success' and state.get('ExecMainStatus')=='0' and state.get('User')==account.pw_name
            and state.get('PrivateNetwork')==state.get('ProtectHome')==state.get('NoNewPrivileges')=='yes')
        result=json.loads(read(home/'receipt.json',account.pw_uid))
        require(set(result)=={'complete','java_version_verified','ghidra_headless_import_passed','real_profiles_read',
            'rea_server_started','model_called','external_sends'} and all(result[k] is True for k in
                ('complete','java_version_verified','ghidra_headless_import_passed'))
            and all(result[k] is False for k in ('real_profiles_read','rea_server_started','model_called'))
            and result['external_sends']==0)
    finally:
        subprocess.run(['/usr/bin/systemctl','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
        require(stopped(metadata(unit)))

    return dict(result,qualification_unit_stopped=True,network_isolated=True)


def worker():
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    c=common();read,write=support(c);context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('rea-main-programs-'))
    source=(ARTIFACT/'rea_candidate_owner.py').read_bytes();require(hashlib.sha256(source).hexdigest()==OWNER_SHA)
    owned=definitions(ARTIFACT/'rea_candidate_owner.py',OWNER_SHA)
    snapshot=definitions(ARTIFACT/'public_program_snapshot.py',SNAPSHOT_SHA)
    driver=c['legacy']();before=driver['policies'](read);entry,row=driver['fixed_entry'](read)
    account=pwd.getpwnam(entry['user']);source_account=pwd.getpwnam('vincentspereira');live=retained_live(read)
    result=dict(complete=False,source_revision=BASE.name,operator_helper_sha256=context['source_sha256'],evidence=str(evidence),
        source_programs_changed=False,source_profiles_changed=False,previous_candidates_changed=False,candidate_promoted=False,
        daily_backup_registry_changed=False,production_dispatch_qualified=False,production_renewal_timer_enabled=False,
        main_tool_program_coverage_qualified=False,actual_profile_admission_qualified=False,fleet_launch_approved=False,
        private_keys_sent_to_owner=False,chat_model_called=False,rea_server_started=False,platform_adapters_started=0,
        canonical_memory_edits=False,credentials_issued=0,automatic_retry=False,invocation_id=os.environ.get('INVOCATION_ID',''))
    try:
        require(re.fullmatch('[a-f0-9]{32}',result['invocation_id']) is not None)
        def checkpoint(name):write(evidence/(name+'.started.json'),canonical(dict(phase=name)))
        previous_context=json.loads(read(LIVE/'context.private.json',0))
        source_binding=json.loads(read(Path(previous_context['evidence'])/'source-configuration.private.json',0))['fingerprints']
        verified,empty=c['owner'](source_account,source,c['packet'](source_account,'verify_source',fingerprints=source_binding),limit=65536)
        require(not empty and verified==dict(complete=True,current_source_settings_preserved=True))
        checkpoint('public_programs');programs={};proofs={};receipts={}
        for name,pin in owned['PROGRAMS'].items():
            value,body=c['owner'](source_account,source,c['packet'](source_account,'program_archive',program=name),limit=snapshot['MAX_ARCHIVE']+65537)
            require(value==dict(complete=True,program=name,archive_bytes=pin['size'],archive_sha256=pin['sha256'])
                and len(body)==pin['size'] and hashlib.sha256(body).hexdigest()==pin['sha256'])
            destination=PROGRAM_ROOT/('rea-'+name+'-'+pin['sha256'][:16]);proof=PROGRAM_ROOT/('proof-'+name+'-'+context['id'])
            snapshot['restore'](body,name,destination);snapshot['restore'](body,name,proof)
            write(ARTIFACT/(name+'.tar'),body)
            programs[name]=str(destination);proofs[name]=str(proof)
            receipts[name]=dict(archive_sha256=pin['sha256'],archive_bytes=len(body),protected_copy_verified=True,disposable_program_restore_verified=True)
            del body
        write(evidence/'programs.json',canonical(receipts))
        checkpoint('isolated_program_execution');probe=program_probe(context,account,proofs,read,write)
        write(evidence/'program-execution.json',canonical(probe))
        checkpoint('new_candidate');archive=authenticated_profile_archive(c,read,live)
        bundle=driver['fresh_bundle'](entry);result['credentials_issued']=2
        prepared,empty=c['owner'](account,source,c['packet'](account,'prepare',entry=entry,original=live['new_inactive_candidate'],
            programs=programs,bundle=bundle,archive_bytes=len(archive),id=context['id']),body=archive,limit=65536)
        del archive,bundle
        require(not empty and prepared.get('complete') is True and prepared.get('remaining_reference_count')==0
            and all(prepared.get(k) is True for k in ('rea_definition_preserved','settings_and_oauth_preserved','scoped_status_authenticated')))
        destination=Path(prepared['destination']);require(destination.parent==Path(account.pw_dir)
            and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}',destination.name))
        write(evidence/'candidate.private.json',canonical(prepared))
        checkpoint('configured_backup');settings=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))
        captured,body=c['owner'](account,source,c['packet'](account,'capture_candidate',entry=entry,destination=str(destination),recipient=settings['ENHANCED_BACKUP_RECIPIENT']))
        validator=driver['definitions'](c['PACKAGE']/'continue_launch_main_operational.py',driver['PINS']['continue_launch_main_operational.py'])['validate_owner_result']
        validator(captured,body,'capture',account)
        generation,cipher=c['generation']('configured',captured,body,settings,read,write)
        archive=c['decrypt'](cipher);checkpoint('configured_restore')
        restored,empty=c['owner'](account,source,c['packet'](account,'restore_candidate',entry=entry,destination=str(destination),
            archive_bytes=len(archive),id=context['restore_id']),body=archive,limit=65536)
        del archive
        require(not empty and restored.get('mcp_definitions')==prepared['mcp_definitions']
            and all(restored.get(k) is True for k in ('workspace_rebased','restored_scope_authenticated','oauth_and_environment_preserved'))
            and restored['receipt'].get('pinned_provider_binding_reconstructed') is True
            and restored['receipt'].get('sqlite_databases_verified')==captured['receipt']['sqlite_databases'])
        write(evidence/'restored.private.json',canonical(restored))
        verified,empty=c['owner'](source_account,source,c['packet'](source_account,'verify_source',fingerprints=source_binding),limit=65536)
        require(not empty and verified==dict(complete=True,current_source_settings_preserved=True))
        result.update(complete=True,rea_dependencies_staged=True,rea_dependency_execution_qualified=True,
            new_inactive_candidate=str(destination),generation=str(generation),remaining_reference_count=0,
            mcp_definitions_preserved=prepared['mcp_definitions'],sqlite_databases_recovered=restored['receipt']['sqlite_databases_verified'],
            configured_candidate_restore_qualified=True,rea_definition_preserved=True,settings_and_oauth_preserved=True,
            program_disposable_restores_verified=2,program_snapshots=receipts,qualification_unit_stopped=True)
    except Exception as error:
        result.update(category='rea_main_programs_incomplete_preserve_evidence_no_automatic_retry',error_kind=type(error).__name__
            if type(error).__name__ in c['KINDS'] else 'other')
        if isinstance(getattr(error,'owner_diagnostic',None),dict):result['owner_diagnostic']=error.owner_diagnostic
    require(all(read(path,0)==raw for path,raw in before.items()));result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result));return 0 if result['complete'] else 1


def watch(read,write):
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('rea-main-programs-'))
    if os.path.lexists(evidence/'finish.summary.json'):
        result=json.loads(read(evidence/'finish.summary.json',0));require(result.get('operator_job_stopped') is True
            and result.get('operator_helper_sha256')==context['source_sha256'])
        print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
    try:
        last=0;deadline=time.monotonic()+1900
        while time.monotonic()<deadline:
            state=metadata(UNIT)
            if os.path.lexists(evidence/'summary.json') and (state.get('SubState')=='exited' or stopped(state)):
                result=json.loads(read(evidence/'summary.json',0));require(result.get('operator_helper_sha256')==context['source_sha256'])
                if result['complete']:require(state.get('Result')=='success' and state.get('ExecMainStatus')=='0'
                    and state.get('InvocationID')==result['invocation_id'] and state.get('User')=='root')
                subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
                require(stopped(metadata(UNIT)));result['operator_job_stopped']=True
                write(evidence/'finish.summary.json',canonical(result));print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            require(not stopped(state))
            if time.monotonic()-last>=10:
                phases=[x for x in PHASES if os.path.lexists(evidence/(x+'.started.json'))]
                print(json.dumps(dict(event='rea_main_programs_running',checkpoint=phases[-1] if phases else 'starting',
                    note='Ctrl+C detaches; repeat qualify-rea-programs to reattach.')),flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print('{"detached":true,"job_continues":true}',flush=True);return 0
    raise ValueError('rea_main_watch_deadline')


def launch():
    require(os.geteuid()==0);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    c=common();read,write=support(c);source=globals()['_verified_source_bytes'];digest=hashlib.sha256(source).hexdigest()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0));require(context['source_sha256']==digest)
        for name,pin in json.loads(read(ARTIFACT/'sources.json',0)).items():
            require(re.fullmatch(r'[a-z0-9_]+\.py',name) and hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==pin)
        return watch(read,write)
    retained_live(read);driver=c['legacy']();before=driver['policies'](read);entry,row=driver['fixed_entry'](read)
    require(metadata(UNIT).get('LoadState')=='not-found' and not os.path.lexists(ARTIFACT)
        and shutil.disk_usage(c['BACKUPS']).free>=8*1024**3)
    directory=Path(__file__).parent
    owned=definitions(directory/'rea_candidate_owner.py',OWNER_SHA)
    prior=definitions(LIVE/'main_live_reconciliation_owner.py',owned['OWNER_SHA'])
    sources={'stage_rea_main_programs.py':source,'rea_candidate_owner.py':owned['_verified_source_bytes'],
        'main_live_reconciliation_owner.py':prior['_verified_source_bytes'],
        'public_program_snapshot.py':definitions(directory/'public_program_snapshot.py',SNAPSHOT_SHA)['_verified_source_bytes'],
        'probe_rea_public_programs.py':definitions(directory/'probe_rea_public_programs.py',PROBE_SHA)['_verified_source_bytes']}
    for name,pin in prior['PINS'].items():sources[name]=definitions(LIVE/name,pin)['_verified_source_bytes']
    if not os.path.lexists(PROGRAM_ROOT):PROGRAM_ROOT.mkdir(mode=0o755);PROGRAM_ROOT.chmod(0o755)
    protected=driver['definitions'](c['PACKAGE']/'renew_fleet_credentials.py',driver['DRIVER_SHA'])['protected']
    protected(PROGRAM_ROOT)
    ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    for name,raw in sources.items():write(ARTIFACT/name,raw);(ARTIFACT/name).chmod(0o644)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    evidence=Path(tempfile.mkdtemp(prefix='rea-main-programs-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=digest,evidence=str(evidence),id=uuid.uuid4().hex,restore_id=uuid.uuid4().hex)))
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='CAP_SETUID CAP_SETGID',ProtectSystem='strict',
        ProtectHome='no',PrivateTmp='yes',ReadWritePaths=' '.join([str(BASE/'operator-evidence'),str(c['BACKUPS']),
            str(ARTIFACT),str(PROGRAM_ROOT),entry['home']]),Restart='no',TimeoutStartSec='1800',MemoryMax='8G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+key+'='+value for key,value in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/'stage_rea_main_programs.py'),'--worker']
    require(all(read(path,0)==raw for path,raw in before.items()))
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    return watch(read,write)


if __name__=='__main__':
    try:
        require(sys.argv[1:]==['--worker']);raise SystemExit(worker())
    except Exception:
        print('{"complete":false,"category":"rea_main_worker_preflight_refused"}',flush=True);raise SystemExit(1)
