"""Prepare and recover a NEW inactive main candidate; reuse completed REA proof."""
from __future__ import annotations
import hashlib
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
V3=BASE/'operator-rea-main-programs-v3'
ARTIFACT=BASE/'operator-main-rea-reviewed-candidate-v1'
UNIT='ec-main-rea-reviewed-candidate-v1-20261028.service'
V3_SHA='914ae91644bebb8e07094fed59c176b1c02e043750d6fc286eef3a6624bbc5e9'
OWNER_SHA='23ae2a66c8bf3ee1c16fc116988894fb12f3b0c36212c341d3f5c8abc0853699'
LIB_SHA='12ea43d478806175719ae45d6ffcf35ed4aa0b51c4c5d6d7c8c18717d3964ea4'
REVIEW_SHA='049ad94d989b8c0039c967d65341338642483ad472f79b76604d380e7f216e3b'
PASSED=BASE/'operator-evidence/rea-owner-receipt-finish-zy8t6r38/summary.json'
FINISH_SHA='2efb314da94bdc813a58a32d6a0c2a8f2949b76d993db4a26d4418fc921abf5f'


def require(value):
    if not value:raise ValueError('reviewed_main_candidate_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    value={'__name__':'verified_reviewed_main_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-reviewed-main-support>','exec'),value)
    return value


def helpers():
    old=definitions(V3/'reconcile_rea_configuration.py',V3_SHA)
    c=old['common']();read,write=old['support'](c)
    return old,c,read,write


def retained_pass(read,parent):
    result=json.loads(read(PASSED,0))
    require(result.get('source_revision')==BASE.name and result.get('operator_helper_sha256')==FINISH_SHA
        and result.get('evidence')==str(PASSED.parent) and result.get('credentials_issued')==result.get('encrypted_generations_created')==0
        and all(result.get(k) is True for k in ('complete','owner_read_verified','receipt_unchanged_since_completion',
            'rea_dependency_execution_qualified','java_version_verified','ghidra_headless_import_passed',
            'retained_staging_and_readback_reused','retained_program_execution_reused','all_admission_policies_preserved_disabled'))
        and all(result.get(k) is False for k in ('programs_replayed','services_started','settings_accepted','source_profiles_changed',
            'previous_candidates_changed','candidate_promoted','canonical_memory_edits','memory_api_called','chat_model_called','fleet_launch_approved')))
    proof=result.get('journal_execution_proof',{})
    require(proof.get('verified') is True and proof.get('invocation_id')=='e88c25dbc8bc44728c107fcd307f47f9'
        and isinstance(proof.get('predicates'),dict) and set(proof['predicates'])=={'unique_start_completion_and_stop','same_invocation','ordered_monotonic_events','same_current_boot','no_conflicting_start_failure'}
        and all(v is True for v in proof['predicates'].values()))
    snapshots=result.get('program_snapshots');require(isinstance(snapshots,dict) and set(snapshots)==set(parent['PROGRAMS']))
    for name,pin in parent['PROGRAMS'].items():
        item=snapshots[name];require(item.get('archive_sha256')==pin['sha256'] and item.get('archive_bytes')==pin['size']
            and item.get('protected_copy_verified') is True and item.get('disposable_program_restore_verified') is True)
    return result


def worker():
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    old,c,read,write=helpers();context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-rea-reviewed-'))
    parent=definitions(V3/'rea_candidate_owner_v3.py',old['OWNER_SHA']);retained_pass(read,parent)
    pass_bytes=read(PASSED,0);driver=c['legacy']();before=driver['policies'](read);entry,_=driver['fixed_entry'](read)
    account=pwd.getpwnam(entry['user']);source_account=pwd.getpwnam('vincentspereira');source=parent['_verified_source_bytes']
    result=dict(complete=False,source_revision=BASE.name,operator_helper_sha256=context['source_sha256'],evidence=str(evidence),
        reused_dependency_evidence=str(PASSED),rea_dependency_execution_qualified=True,programs_replayed=False,
        credentials_issued=0,encrypted_generations_created=0,candidate_promoted=False,source_profiles_changed=False,
        previous_candidates_changed=False,daily_backup_registry_changed=False,existing_launchers_changed=False,
        canonical_memory_edits=False,chat_model_called=False,rea_server_started=False,platform_adapters_started=0,
        private_keys_sent_to_owner=False,production_renewal_timer_enabled=False,actual_profile_admission_qualified=False,
        main_tool_program_coverage_qualified=False,fleet_settings_accepted=False,fleet_launch_approved=False,
        candidate_scope_pending_review=True,prior_live_snapshot_reused=True,current_source_operational_refresh_qualified=False,
        automatic_retry=False,invocation_id=os.environ.get('INVOCATION_ID',''))
    try:
        require(re.fullmatch('[a-f0-9]{32}',result['invocation_id']) is not None)
        def checkpoint(name):
            result['checkpoint']=name;write(evidence/(name+'.started.json'),canonical(dict(phase=name)))
        checkpoint('model_binding');model_key=c['runtime_model'](driver,read,write,evidence)
        checkpoint('source_capture');settings=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))
        current,body=c['owner'](source_account,source,c['packet'](source_account,'capture_source',recipient=settings['ENHANCED_BACKUP_RECIPIENT']))
        old['validate_current'](current,body);capsule=c['decrypt'](body,configuration=True)
        live=old['retained_live'](read);archive=old['authenticated_profile_archive'](c,read,live)
        checkpoint('settings_assessment');owner=definitions(ARTIFACT/'assess_rea_candidate_settings_owner.py',OWNER_SHA)
        assessed,empty=c['owner'](account,owner['_verified_source_bytes'],c['packet'](account,'assess_configuration',entry=entry,
            original=live['new_inactive_candidate'],capsule_bytes=len(capsule),archive_bytes=len(archive),fingerprints=current['fingerprints']),body=capsule+archive,limit=65536)
        require(not empty and set(assessed)=={'complete','review','inactive_preparation_allowed','allowed_preserved_changes','fleet_settings_accepted'}
            and assessed.get('complete') is True and type(assessed.get('inactive_preparation_allowed')) is bool
            and assessed.get('fleet_settings_accepted') is False and isinstance(assessed.get('allowed_preserved_changes'),list)
            and len(assessed['allowed_preserved_changes'])<=3 and all(k in {'approvals.timeout','known_builtin_toolsets','known_plugin_toolsets'} for k in assessed['allowed_preserved_changes']))
        reviewer=definitions(BASE/'operator-rea-settings-and-programs-v1/review_rea_settings_and_programs.py',REVIEW_SHA)
        reviewer['validate_review'](assessed['review'],owner)
        result['settings_assessment']=assessed
        if not assessed['inactive_preparation_allowed']:
            result['category']='unreviewed_setting_change_requires_review_no_credentials_issued'
            raise ValueError('unreviewed_setting_change')
        require(assessed['review']['critical_sections_equal'] is True)
        checkpoint('source_stability')
        checked,empty=c['owner'](source_account,source,c['packet'](source_account,'verify_source',fingerprints=current['fingerprints']),limit=65536)
        require(not empty and checked==dict(complete=True,current_source_settings_preserved=True))
        c['generation']('configuration',current,body,settings,read,write);result['encrypted_generations_created']+=1
        write(evidence/'source-configuration.private.json',canonical(current))
        checkpoint('new_candidate');programs={name:str(old['PROGRAM_ROOT']/('rea-'+name+'-'+pin['sha256'][:16])) for name,pin in parent['PROGRAMS'].items()}
        bundle=driver['fresh_bundle'](entry);result['credentials_issued']=2
        prepared,empty=c['owner'](account,source,c['packet'](account,'prepare',entry=entry,original=live['new_inactive_candidate'],programs=programs,
            bundle=bundle,archive_bytes=len(archive),capsule_bytes=len(capsule),fingerprints=current['fingerprints'],model_key=model_key,id=context['id']),body=capsule+archive,limit=65536)
        del capsule,archive,bundle,model_key
        require(not empty and prepared.get('complete') is True and prepared.get('remaining_reference_count')==0
            and all(prepared.get(k) is True for k in ('rea_definition_preserved','settings_and_oauth_preserved','scoped_status_authenticated','current_auth_snapshot_preserved','current_source_settings_refreshed')))
        destination=Path(prepared['destination']);require(destination.parent==Path(account.pw_dir) and re.fullmatch('ec-main-operational-restore-[A-Za-z0-9_-]{6,64}',destination.name))
        write(evidence/'candidate.private.json',canonical(prepared))
        checkpoint('configured_backup')
        captured,body=c['owner'](account,source,c['packet'](account,'capture_candidate',entry=entry,destination=str(destination),recipient=settings['ENHANCED_BACKUP_RECIPIENT']))
        validator=driver['definitions'](c['PACKAGE']/'continue_launch_main_operational.py',driver['PINS']['continue_launch_main_operational.py'])['validate_owner_result']
        validator(captured,body,'capture',account)
        generation,cipher=c['generation']('configured',captured,body,settings,read,write);result['encrypted_generations_created']+=1
        archive=c['decrypt'](cipher);checkpoint('configured_restore')
        restored,empty=c['owner'](account,source,c['packet'](account,'restore_candidate',entry=entry,destination=str(destination),archive_bytes=len(archive),fingerprints=current['fingerprints'],id=context['restore_id']),body=archive,limit=65536)
        del archive
        require(not empty and restored.get('mcp_definitions')==prepared['mcp_definitions']
            and all(restored.get(k) is True for k in ('workspace_rebased','restored_scope_authenticated','oauth_and_environment_preserved','current_auth_snapshot_preserved'))
            and restored['receipt'].get('pinned_provider_binding_reconstructed') is True
            and restored['receipt'].get('sqlite_databases_verified')==captured['receipt']['sqlite_databases'])
        write(evidence/'restored.private.json',canonical(restored));checkpoint('source_freshness')
        checked,empty=c['owner'](source_account,source,c['packet'](source_account,'verify_source',fingerprints=current['fingerprints']),limit=65536)
        require(not empty and checked==dict(complete=True,current_source_settings_preserved=True))
        result.update(complete=True,checkpoint='complete',new_inactive_candidate=str(destination),generation=str(generation),
            configured_candidate_restore_qualified=True,inactive_current_settings_preservation_qualified=True,
            current_auth_snapshot_preserved=True,current_source_settings_refreshed=True,source_current_at_completion=True,
            remaining_reference_count=0,mcp_definitions_preserved=prepared['mcp_definitions'],sqlite_databases_recovered=restored['receipt']['sqlite_databases_verified'])
    except Exception as error:
        result.setdefault('category','reviewed_main_candidate_incomplete_preserve_evidence')
        result.update(failure_phase=result.get('checkpoint','preflight'),error_kind=type(error).__name__ if type(error).__name__ in c['KINDS'] else 'other')
        if isinstance(getattr(error,'owner_diagnostic',None),dict):result['owner_diagnostic']=error.owner_diagnostic
    require(read(PASSED,0)==pass_bytes and all(read(path,0)==raw for path,raw in before.items()))
    result.update(prior_dependency_pass_preserved=True,all_admission_policies_preserved_disabled=True)
    write(evidence/'summary.json',canonical(result));return 0 if result['complete'] else 1


def watch(old,read,write):
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('main-rea-reviewed-'))
    if os.path.lexists(evidence/'finish.summary.json'):
        result=json.loads(read(evidence/'finish.summary.json',0));require(result.get('operator_job_stopped') is True and result.get('operator_helper_sha256')==context['source_sha256'])
        print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
    try:
        last=0;deadline=time.monotonic()+1900
        while time.monotonic()<deadline:
            state=old['metadata'](UNIT)
            if os.path.lexists(evidence/'summary.json') and (state.get('SubState')=='exited' or old['stopped'](state)):
                result=json.loads(read(evidence/'summary.json',0));require(result.get('operator_helper_sha256')==context['source_sha256'])
                if result['complete']:require(state.get('Result')=='success' and state.get('ExecMainStatus')=='0' and state.get('InvocationID')==result['invocation_id'] and state.get('User')=='root')
                subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
                require(old['stopped'](old['metadata'](UNIT)));result['operator_job_stopped']=True
                write(evidence/'finish.summary.json',canonical(result));print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            require(not old['stopped'](state))
            if time.monotonic()-last>=10:
                phases=[p.stem.removesuffix('.started') for p in evidence.glob('*.started.json')]
                print(json.dumps(dict(event='main_rea_candidate_running',completed_checkpoints=len(phases),note='Ctrl+C detaches; repeat the same command to reattach.')),flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print('{"detached":true,"job_continues":true}',flush=True);return 0
    raise ValueError('main_rea_watch_deadline')


def launch():
    require(os.geteuid()==0);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    source=Path(__file__).read_bytes();digest=hashlib.sha256(source).hexdigest();old,c,read,write=helpers()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0));require(context['source_sha256']==digest)
        for name,pin in json.loads(read(ARTIFACT/'sources.json',0)).items():
            require(re.fullmatch(r'[a-z0-9_]+\.py',name) and hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==pin)
        return watch(old,read,write)
    parent=definitions(V3/'rea_candidate_owner_v3.py',old['OWNER_SHA']);retained_pass(read,parent)
    driver=c['legacy']();before=driver['policies'](read);entry,_=driver['fixed_entry'](read)
    require(not os.path.lexists(ARTIFACT) and old['metadata'](UNIT).get('LoadState')=='not-found' and shutil.disk_usage(c['BACKUPS']).free>=3*1024**3)
    directory=Path(__file__).parent
    owner=definitions(directory/'assess_rea_candidate_settings_owner.py',OWNER_SHA);owner['platform_names']()
    lib=definitions(directory/'finish_rea_review_owner.py',LIB_SHA);lib['public_schema']()
    sources={'prepare_main_after_rea.py':source,'assess_rea_candidate_settings_owner.py':owner['_verified_source_bytes'],'finish_rea_review_owner.py':lib['_verified_source_bytes']}
    ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    for name,raw in sources.items():write(ARTIFACT/name,raw);(ARTIFACT/name).chmod(0o644)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    evidence=Path(tempfile.mkdtemp(prefix='main-rea-reviewed-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=digest,evidence=str(evidence),id=uuid.uuid4().hex,restore_id=uuid.uuid4().hex)))
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',CapabilityBoundingSet='CAP_SETUID CAP_SETGID',
        AmbientCapabilities='CAP_SETUID CAP_SETGID',ProtectSystem='strict',ProtectHome='no',PrivateTmp='yes',
        ReadWritePaths=' '.join([str(BASE/'operator-evidence'),str(c['BACKUPS']),str(ARTIFACT),entry['home']]),Restart='no',TimeoutStartSec='1800',MemoryMax='8G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+key+'='+value for key,value in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/'prepare_main_after_rea.py'),'--worker']
    require(all(read(path,0)==raw for path,raw in before.items()))
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    return watch(old,read,write)


if __name__=='__main__':
    try:
        require(sys.argv[1:] in ([],['--worker']))
        raise SystemExit(worker() if sys.argv[1:]==['--worker'] else launch())
    except Exception:
        print('{"complete":false,"category":"reviewed_main_candidate_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
