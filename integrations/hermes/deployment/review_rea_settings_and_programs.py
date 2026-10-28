"""One detached job: safe settings review plus independent offline REA proof.

No setting is accepted or rewritten. Preserve the stopped configuration refusal;
qualify exact public dependencies without enabling any profile or gateway.
"""
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
FROZEN=BASE/'operator-rea-main-programs-v3'
SOURCE_SHA='914ae91644bebb8e07094fed59c176b1c02e043750d6fc286eef3a6624bbc5e9'
OWNER_SHA='f939d2a152e249149cb432e9678a7fdb4e6faada883f1c7c3205494fa0497c3e'
EXPECTED=BASE/'operator-evidence/rea-main-programs-1oj9htt6'
ARTIFACT=BASE/'operator-rea-settings-and-programs-v1'
UNIT='ec-rea-settings-and-programs-v1-20261028.service'
PHASES=('settings_review','public_programs','isolated_program_execution','source_freshness')


def require(value):
    if not value:raise ValueError('rea_settings_programs_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    value={'__name__':'verified_rea_review_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-rea-review-support>','exec'),value)
    return value


def helpers():
    old=definitions(FROZEN/'reconcile_rea_configuration.py',SOURCE_SHA)
    c=old['common']();read,write=old['support'](c)
    return old,c,read,write


def retained(old,read):
    context=json.loads(read(FROZEN/'context.private.json',0))
    require(context.get('source_sha256')==SOURCE_SHA and context.get('evidence')==str(EXPECTED)
        and old['stopped'](old['metadata'](old['UNIT'])))
    result=json.loads(read(EXPECTED/'finish.summary.json',0))
    require(result.get('source_revision')==BASE.name and result.get('operator_helper_sha256')==SOURCE_SHA
        and result.get('evidence')==str(EXPECTED) and result.get('complete') is False
        and result.get('operator_job_stopped') is True and result.get('credentials_issued')==0
        and result.get('encrypted_generations_created')==0 and result.get('previous_configuration_bytes_equal') is False
        and result.get('category')=='rea_configuration_changed_requires_review_no_effectful_retry'
        and result.get('checkpoint')==result.get('failure_phase')=='configuration_equivalence'
        and result.get('configuration_comparison')==dict(complete=True,source_capsule_verified=True,
            configuration_semantically_equivalent=False,changed_sections=['other_settings'])
        and result.get('all_admission_policies_preserved_disabled') is True
        and all(result.get(key) is False for key in ('source_profiles_changed','source_programs_changed',
            'previous_candidates_changed','candidate_promoted','daily_backup_registry_changed','canonical_memory_edits',
            'chat_model_called','rea_server_started','fleet_launch_approved','production_renewal_timer_enabled')))
    for phase in old['PHASES']:
        path=EXPECTED/(phase+'.started.json')
        if phase in {'model_binding','current_settings_capture','configuration_equivalence'}:
            require(json.loads(read(path,0))==dict(phase=phase))
        else:require(not os.path.lexists(path))
    require(not any(os.path.lexists(FROZEN/(name+'.tar')) for name in ('ghidra','java')))
    return result


def validate_review(value,owner):
    require(isinstance(value,dict) and set(value)=={'changed_public_fields','redacted_changed_fields','additional_public_changes',
        'values_policy','complete','critical_sections_equal','source_capsule_verified','configuration_semantically_equivalent','settings_accepted'}
        and value.get('complete') is True and value.get('source_capsule_verified') is True and value.get('settings_accepted') is False
        and type(value.get('critical_sections_equal')) is bool and type(value.get('configuration_semantically_equivalent')) is bool
        and value.get('values_policy')=='only_fixed_nonsecret_numeric_boolean_and_display_enum_fields'
        and isinstance(value.get('changed_public_fields'),list) and len(value['changed_public_fields'])<=128
        and all(type(value.get(k)) is int and 0<=value[k]<=10000 for k in ('redacted_changed_fields','additional_public_changes')))
    schema=owner['public_schema']();seen=set()
    for row in value['changed_public_fields']:
        require(isinstance(row,dict) and set(row)=={'path','previous','current'} and isinstance(row['path'],list)
            and 1<=len(row['path'])<=32 and all(isinstance(part,str) for part in row['path']))
        path=tuple(row['path']);require(path not in seen and path[0] not in {'model','memory','gateway','mcp_servers'});seen.add(path)
        public=schema
        for part in path:require(part in public);public=public[part]
        for side in ('previous','current'):
            item=row[side];require(isinstance(item,dict) and set(item) in ({'kind'},{'kind','value'})
                and item.get('kind') in {'absent','null','boolean','integer','number','string','list','mapping'})
            if 'value' in item:
                require(owner['safe_value'](path,item['value'],True)=={'value':item['value']}
                    and item['kind']==owner['setting_kind'](item['value'],True))
    if value['configuration_semantically_equivalent']:
        require(value['critical_sections_equal'] and not seen and value['redacted_changed_fields']==value['additional_public_changes']==0)


def qualify_programs(old,c,read,write,context,account,*,checkpoint=None):
    parent=definitions(FROZEN/'rea_candidate_owner_v3.py',old['OWNER_SHA'])
    snapshot=definitions(ARTIFACT/'public_program_snapshot.py',old['SNAPSHOT_SHA'])
    source=parent['_verified_source_bytes'];programs={};receipts={}
    source_account=pwd.getpwnam('vincentspereira')
    for name,pin in parent['PROGRAMS'].items():
        value,body=c['owner'](source_account,source,c['packet'](source_account,'program_archive',program=name),limit=snapshot['MAX_ARCHIVE']+65537)
        require(value==dict(complete=True,program=name,archive_bytes=pin['size'],archive_sha256=pin['sha256'])
            and len(body)==pin['size'] and hashlib.sha256(body).hexdigest()==pin['sha256'])
        destination=old['PROGRAM_ROOT']/('rea-'+name+'-'+pin['sha256'][:16])
        proof=old['PROGRAM_ROOT']/('proof-'+name+'-'+context['id'])
        reused=os.path.lexists(destination)
        if reused:snapshot['verify'](destination,snapshot['validate'](body,name))
        else:snapshot['restore'](body,name,destination)
        snapshot['restore'](body,name,proof)
        programs[name]=str(proof)
        receipts[name]=dict(archive_sha256=pin['sha256'],archive_bytes=len(body),protected_copy_verified=True,
            existing_copy_reused=reused,disposable_program_restore_verified=True)
        del body
    write(Path(context['evidence'])/'programs.json',canonical(receipts))
    # Only this freshly loaded namespace changes its proof-driver directory.
    # Frozen files and their failed contexts remain byte-for-byte unchanged.
    old['ARTIFACT']=ARTIFACT
    if checkpoint:checkpoint('isolated_program_execution')
    try:
        probe=old['program_probe'](context,account,programs,read,write)
    except Exception as error:
        diagnostic=dict(receipt_available=False)
        try:
            receipt=json.loads(read(Path('/run')/('ec-rea-program-proof-'+context['id'])/'receipt.json',account.pw_uid,65536))
            require(isinstance(receipt,dict) and type(receipt.get('complete')) is bool)
            for key in ('complete','java_version_verified','ghidra_headless_import_passed','real_profiles_read','rea_server_started','model_called'):
                require(type(receipt.get(key)) is bool);diagnostic[key]=receipt[key]
            kind=receipt.get('error_kind');diagnostic['error_kind']=kind if kind in {'ValueError','TimeoutExpired','OSError','PermissionError'} else 'other'
            diagnostic['receipt_available']=True
        except Exception:
            diagnostic=dict(receipt_available=False)
        error.program_diagnostic=diagnostic
        raise
    require(probe.get('complete') is True and probe.get('qualification_unit_stopped') is True)
    return receipts,probe


def worker():
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    old,c,read,write=helpers();retained(old,read)
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('rea-settings-programs-'))
    unchanged={name:read(EXPECTED/name,0) for name in ('summary.json','finish.summary.json')}
    driver=c['legacy']();before=driver['policies'](read);entry,_=driver['fixed_entry'](read)
    account=pwd.getpwnam(entry['user']);source_account=pwd.getpwnam('vincentspereira')
    result=dict(complete=False,source_revision=BASE.name,operator_helper_sha256=context['source_sha256'],evidence=str(evidence),
        continued_from=str(EXPECTED),credentials_issued=0,encrypted_generations_created=0,settings_accepted=False,
        settings_review_source_current=False,configuration_review_required=True,source_profiles_changed=False,
        source_programs_changed=False,previous_candidates_changed=False,
        candidate_promoted=False,canonical_memory_edits=False,memory_api_called=False,chat_model_called=False,
        private_keys_sent_to_owner=False,rea_server_started=False,platform_adapters_started=0,existing_launchers_changed=False,
        daily_backup_registry_changed=False,production_renewal_timer_enabled=False,actual_profile_admission_qualified=False,
        main_tool_program_coverage_qualified=False,fleet_launch_approved=False,automatic_retry=False,
        invocation_id=os.environ.get('INVOCATION_ID',''))
    try:
        require(re.fullmatch('[a-f0-9]{32}',result['invocation_id']) is not None)
        def checkpoint(name):
            result['checkpoint']=name
            write(evidence/(name+'.started.json'),canonical(dict(phase=name)))
        checkpoint('settings_review')
        parent=definitions(FROZEN/'rea_candidate_owner_v3.py',old['OWNER_SHA'])
        recipient=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))['ENHANCED_BACKUP_RECIPIENT']
        current,body=c['owner'](source_account,parent['_verified_source_bytes'],c['packet'](source_account,'capture_source',recipient=recipient))
        old['validate_current'](current,body);capsule=c['decrypt'](body,configuration=True)
        live=old['retained_live'](read);archive=old['authenticated_profile_archive'](c,read,live)
        owner=definitions(ARTIFACT/'review_rea_configuration_owner.py',OWNER_SHA)
        review,empty=c['owner'](account,owner['_verified_source_bytes'],c['packet'](account,'review_configuration',entry=entry,
            original=live['new_inactive_candidate'],capsule_bytes=len(capsule),archive_bytes=len(archive),fingerprints=current['fingerprints']),
            body=capsule+archive,limit=65536)
        require(not empty);validate_review(review,owner)
        result['settings_review']=review
        write(evidence/'settings-review.json',canonical(review))
        del capsule,archive,body
        checkpoint('public_programs')
        receipts,probe=qualify_programs(old,c,read,write,context,account,checkpoint=checkpoint)
        result.update(rea_dependencies_staged=True,rea_dependency_execution_qualified=True,program_snapshots=receipts,
            java_version_verified=probe.get('java_version_verified') is True,
            ghidra_headless_import_passed=probe.get('ghidra_headless_import_passed') is True,qualification_unit_stopped=True)
        write(evidence/'program-execution.json',canonical(probe))
        checkpoint('source_freshness')
        checked,empty=c['owner'](source_account,parent['_verified_source_bytes'],c['packet'](source_account,'verify_source',fingerprints=current['fingerprints']),limit=65536)
        require(not empty and checked==dict(complete=True,current_source_settings_preserved=True))
        result.update(complete=True,checkpoint='complete',settings_review_source_current=True,
            configuration_review_required=not review['configuration_semantically_equivalent'])
    except Exception as error:
        result.update(category='rea_settings_or_program_component_incomplete_preserve_evidence',failure_phase=result.get('checkpoint','preflight'),
            error_kind=type(error).__name__ if type(error).__name__ in c['KINDS'] else 'other')
        if isinstance(getattr(error,'owner_diagnostic',None),dict):result['owner_diagnostic']=error.owner_diagnostic
        if isinstance(getattr(error,'program_diagnostic',None),dict):result['program_diagnostic']=error.program_diagnostic
    require(all(read(path,0)==raw for path,raw in before.items()) and all(read(EXPECTED/name,0)==raw for name,raw in unchanged.items()))
    result.update(all_admission_policies_preserved_disabled=True,prior_failure_preserved=True)
    write(evidence/'summary.json',canonical(result));return 0 if result['complete'] else 1


def watch(old,read,write):
    context=json.loads(read(ARTIFACT/'context.private.json',0));evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and evidence.name.startswith('rea-settings-programs-'))
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
                print(json.dumps(dict(event='rea_settings_and_programs_running',note='Ctrl+C detaches; repeat the same command to reattach.')),flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print('{"detached":true,"job_continues":true}',flush=True);return 0
    raise ValueError('rea_review_watch_deadline')


def launch():
    require(os.geteuid()==0);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    raw=Path(__file__).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    old,c,read,write=helpers()
    if os.path.lexists(ARTIFACT/'context.private.json'):
        context=json.loads(read(ARTIFACT/'context.private.json',0));require(context.get('source_sha256')==digest)
        for name,pin in json.loads(read(ARTIFACT/'sources.json',0)).items():
            require(re.fullmatch(r'[a-z0-9_]+\.py',name) and hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()==pin)
        return watch(old,read,write)
    retained(old,read);driver=c['legacy']();before=driver['policies'](read)
    require(not os.path.lexists(ARTIFACT) and old['metadata'](UNIT).get('LoadState')=='not-found'
        and shutil.disk_usage(c['BACKUPS']).free>=8*1024**3)
    driver['definitions'](c['PACKAGE']/'renew_fleet_credentials.py',driver['DRIVER_SHA'])['protected'](old['PROGRAM_ROOT'])
    directory=Path(__file__).parent
    owner=definitions(directory/'review_rea_configuration_owner.py',OWNER_SHA)
    owner['public_schema']()  # Exact public-defaults pin before any new job.
    sources={'review_rea_settings_and_programs.py':raw,'review_rea_configuration_owner.py':owner['_verified_source_bytes'],
        'public_program_snapshot.py':definitions(FROZEN/'public_program_snapshot.py',old['SNAPSHOT_SHA'])['_verified_source_bytes'],
        'probe_rea_public_programs.py':definitions(FROZEN/'probe_rea_public_programs.py',old['PROBE_SHA'])['_verified_source_bytes']}
    ARTIFACT.mkdir(mode=0o755);ARTIFACT.chmod(0o755)
    for name,body in sources.items():write(ARTIFACT/name,body);(ARTIFACT/name).chmod(0o644)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(body).hexdigest() for name,body in sources.items()}))
    evidence=Path(tempfile.mkdtemp(prefix='rea-settings-programs-',dir=BASE/'operator-evidence'))
    write(ARTIFACT/'context.private.json',canonical(dict(source_sha256=digest,evidence=str(evidence),id=uuid.uuid4().hex)))
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='CAP_SETUID CAP_SETGID',ProtectSystem='strict',
        ProtectHome='no',PrivateTmp='yes',ReadWritePaths=' '.join([str(BASE/'operator-evidence'),str(ARTIFACT),str(old['PROGRAM_ROOT'])]),
        Restart='no',TimeoutStartSec='1800',MemoryMax='8G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+key+'='+value for key,value in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/'review_rea_settings_and_programs.py'),'--worker']
    require(all(read(path,0)==body for path,body in before.items()))
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15)
    return watch(old,read,write)


if __name__=='__main__':
    try:
        require(sys.argv[1:] in ([],['--worker']))
        raise SystemExit(worker() if sys.argv[1:]==['--worker'] else launch())
    except Exception:
        print('{"complete":false,"category":"rea_settings_programs_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
