"""Recover retained REA proof as its owner; review current fields without replay."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
FROZEN=BASE/'operator-rea-settings-and-programs-v1'
SOURCE_SHA='049ad94d989b8c0039c967d65341338642483ad472f79b76604d380e7f216e3b'
OWNER_SHA='12ea43d478806175719ae45d6ffcf35ed4aa0b51c4c5d6d7c8c18717d3964ea4'
EXPECTED=BASE/'operator-evidence/rea-settings-programs-x1l5absn'
PROOF_ID='03053e75993f4b73aa063fc2890e5970'
PROOF_SOURCE_SHA='e8d5f1b1478f40bac936c7227fcad35a41978865f78bae585c0fd4ad3a2fd9d9'


def require(value):
    if not value:raise ValueError('retained_rea_finish_refused')


def definitions(path,digest):
    raw=path.read_bytes();require(0<len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    result={'__name__':'verified_retained_rea_finish','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-retained-rea-finish>','exec'),result)
    return result


def retained(prior,old,read):
    context=json.loads(read(FROZEN/'context.private.json',0))
    require(context.get('source_sha256')==SOURCE_SHA and context.get('evidence')==str(EXPECTED)
        and context.get('id')==PROOF_ID and old['stopped'](old['metadata'](prior['UNIT'])))
    result=json.loads(read(EXPECTED/'finish.summary.json',0))
    require(result.get('source_revision')==BASE.name and result.get('operator_helper_sha256')==SOURCE_SHA
        and result.get('evidence')==str(EXPECTED) and result.get('complete') is False
        and result.get('operator_job_stopped') is True and result.get('credentials_issued')==result.get('encrypted_generations_created')==0
        and result.get('category')=='rea_settings_or_program_component_incomplete_preserve_evidence'
        and result.get('checkpoint')==result.get('failure_phase')=='isolated_program_execution'
        and result.get('error_kind')=='PermissionError' and result.get('program_diagnostic')==dict(receipt_available=False)
        and result.get('all_admission_policies_preserved_disabled') is True
        and all(result.get(k) is False for k in ('settings_accepted','settings_review_source_current','source_profiles_changed','source_programs_changed',
            'previous_candidates_changed','candidate_promoted','canonical_memory_edits','memory_api_called','chat_model_called','private_keys_sent_to_owner',
            'existing_launchers_changed','daily_backup_registry_changed','production_renewal_timer_enabled','actual_profile_admission_qualified','fleet_launch_approved')))
    for phase in ('settings_review','public_programs','isolated_program_execution'):
        require(json.loads(read(EXPECTED/(phase+'.started.json'),0))==dict(phase=phase))
    require(not os.path.lexists(EXPECTED/'source_freshness.started.json'))
    return result


def journal_proof(rows,unit,boot):
    """PID-1 metadata only; never infer success from human-readable messages."""
    require(re.fullmatch('[a-f0-9]{32}',boot) is not None)
    events={'start':{},'complete':{},'stop':{}};conflicts=False
    for row in rows:
        if not isinstance(row,dict) or (row.get('_PID'),row.get('_UID'),row.get('_COMM'))!=('1','0','systemd') or row.get('UNIT')!=unit:continue
        if row.get('_BOOT_ID')!=boot:continue
        invocation=row.get('INVOCATION_ID');stamp=row.get('__MONOTONIC_TIMESTAMP');wall=row.get('__REALTIME_TIMESTAMP')
        if not (isinstance(invocation,str) and re.fullmatch('[a-f0-9]{32}',invocation)
            and isinstance(stamp,str) and stamp.isdecimal() and 0<int(stamp)<2**64
            and isinstance(wall,str) and wall.isdecimal() and 0<int(wall)<2**64):continue
        message=row.get('MESSAGE_ID');job=row.get('JOB_TYPE')
        if job=='start' and 'JOB_RESULT' in row and row.get('JOB_RESULT')!='done':conflicts=True
        kind=None
        if job=='start' and message=='7d4958e842da4a758f6c1cdc7b36dcc5' and 'JOB_RESULT' not in row:kind='start'
        if job=='start' and message=='39f53479d3a045ac8e11786248231fbf' and row.get('JOB_RESULT')=='done':kind='complete'
        if job=='stop' and message=='9d1aaa27d60140bd96365438aad20286' and row.get('JOB_RESULT')=='done':kind='stop'
        if kind:events[kind][(invocation,int(stamp),int(wall))]=True
    unique=all(len(value)==1 for value in events.values())
    matched=ordered=False;deadline=None;invocation=None
    if unique:
        start,complete,stop=(next(iter(events[k])) for k in ('start','complete','stop'))
        matched=start[0]==complete[0]==stop[0];ordered=start[1]<complete[1]<=stop[1]
        deadline=(complete[2]+1)*1000-1;invocation=complete[0]
    predicates=dict(unique_start_completion_and_stop=unique,same_invocation=matched,ordered_monotonic_events=ordered,
        same_current_boot=True,no_conflicting_start_failure=not conflicts)
    return dict(verified=all(predicates.values()),predicates=predicates,invocation_id=invocation),deadline


def proof_from_journal(old,context):
    unit='ec-rea-program-proof-'+context['id']+'.service'
    require(context['id']==PROOF_ID and old['stopped'](old['metadata'](unit)))
    source=old['PROGRAM_ROOT']/('proof-driver-'+PROOF_ID)/'probe.py'
    require(hashlib.sha256(source.read_bytes()).hexdigest()==PROOF_SOURCE_SHA)
    process=subprocess.run(['/usr/bin/journalctl','--no-pager','--output=json','--lines=128','--unit='+unit],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=15)
    require(0<len(process.stdout)<=262144)
    rows=[json.loads(line) for line in process.stdout.splitlines()]
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip().replace('-','')
    proof,deadline=journal_proof(rows,unit,boot);require(proof['verified'] and type(deadline) is int)
    return proof,deadline


def main():
    require(os.geteuid()==0 and sys.argv[1:]==[]);os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    prior=definitions(FROZEN/'review_rea_settings_and_programs.py',SOURCE_SHA)
    old,c,read,write=prior['helpers']();prior['retained'](old,read);retained(prior,old,read)
    before={name:read(EXPECTED/name,0) for name in ('summary.json','finish.summary.json','programs.json','settings-review.json')}
    source=Path(__file__).read_bytes();digest=hashlib.sha256(source).hexdigest()
    # A completed finish is immutable. A later settings change needs a new review.
    ticket=EXPECTED/'owner-receipt-finish.summary.json'
    if os.path.lexists(ticket):
        result=json.loads(read(ticket,0));require(result.get('operator_helper_sha256')==digest and result.get('complete') is True)
        print(json.dumps(result,sort_keys=True),flush=True);return 0
    context=json.loads(read(FROZEN/'context.private.json',0));driver=c['legacy']();policies=driver['policies'](read)
    entry,_=driver['fixed_entry'](read);account=prior['pwd'].getpwnam(entry['user']);source_account=prior['pwd'].getpwnam('vincentspereira')
    owner=definitions(Path(__file__).with_name('finish_rea_review_owner.py'),OWNER_SHA)
    evidence=Path(tempfile.mkdtemp(prefix='rea-owner-receipt-finish-',dir=BASE/'operator-evidence'))
    result=dict(complete=False,source_revision=BASE.name,operator_helper_sha256=digest,evidence=str(evidence),continued_from=str(EXPECTED),
        credentials_issued=0,encrypted_generations_created=0,programs_replayed=False,services_started=False,
        settings_accepted=False,configuration_review_required=True,source_profiles_changed=False,previous_candidates_changed=False,
        candidate_promoted=False,canonical_memory_edits=False,memory_api_called=False,chat_model_called=False,private_keys_sent_to_owner=False,
        existing_launchers_changed=False,daily_backup_registry_changed=False,production_renewal_timer_enabled=False,
        main_tool_program_coverage_qualified=False,actual_profile_admission_qualified=False,fleet_launch_approved=False)
    try:
        result['checkpoint']='trusted_manager_completion';proof,deadline=proof_from_journal(old,context)
        result['journal_execution_proof']=proof
        result['checkpoint']='owner_receipt_read'
        observed,body=c['owner'](account,owner['_verified_source_bytes'],c['packet'](account,'read_retained_receipt',entry=entry,proof_id=PROOF_ID,completed_ns=deadline),limit=65536)
        require(not body and set(observed)=={'complete','receipt','owner_read_verified','receipt_unchanged_since_completion'}
            and all(observed.get(k) is True for k in ('complete','owner_read_verified','receipt_unchanged_since_completion')))
        receipt=observed['receipt'];require(receipt==dict(complete=True,java_version_verified=True,ghidra_headless_import_passed=True,
            real_profiles_read=False,rea_server_started=False,model_called=False,external_sends=0)
            and all(type(receipt[k]) is bool for k in receipt if k!='external_sends') and type(receipt['external_sends']) is int)
        programs=json.loads(before['programs.json'])
        parent=prior['definitions'](prior['FROZEN']/'rea_candidate_owner_v3.py',old['OWNER_SHA'])
        require(set(programs)==set(parent['PROGRAMS']))
        for name,pin in parent['PROGRAMS'].items():
            value=programs[name];require(isinstance(value,dict) and set(value)=={'archive_sha256','archive_bytes','protected_copy_verified','existing_copy_reused','disposable_program_restore_verified'}
                and value.get('archive_sha256')==pin['sha256'] and value.get('archive_bytes')==pin['size'] and type(value.get('existing_copy_reused')) is bool
                and value.get('protected_copy_verified') is True and value.get('disposable_program_restore_verified') is True)
        result.update(rea_dependencies_staged=True,rea_dependency_execution_qualified=True,java_version_verified=True,
            ghidra_headless_import_passed=True,owner_read_verified=True,receipt_unchanged_since_completion=True,
            retained_staging_and_readback_reused=True,retained_program_execution_reused=True,program_snapshots=programs)
        write(evidence/'dependency-component.summary.json',json.dumps(result,sort_keys=True).encode())
        result['checkpoint']='current_settings_review'
        original=prior['definitions'](prior['FROZEN']/'rea_candidate_owner_v3.py',old['OWNER_SHA'])['_verified_source_bytes']
        recipient=json.loads(read(Path('/etc/enhanced-cognee/backup.json'),0))['ENHANCED_BACKUP_RECIPIENT']
        current,cipher=c['owner'](source_account,original,c['packet'](source_account,'capture_source',recipient=recipient))
        old['validate_current'](current,cipher);capsule=c['decrypt'](cipher,configuration=True)
        live=old['retained_live'](read);archive=old['authenticated_profile_archive'](c,read,live)
        review,body=c['owner'](account,owner['_verified_source_bytes'],c['packet'](account,'review_configuration',entry=entry,
            original=live['new_inactive_candidate'],capsule_bytes=len(capsule),archive_bytes=len(archive),fingerprints=current['fingerprints']),body=capsule+archive,limit=65536)
        require(not body);prior['validate_review'](review,owner);result['settings_review']=review
        del capsule,archive,cipher
        checked,body=c['owner'](source_account,original,c['packet'](source_account,'verify_source',fingerprints=current['fingerprints']),limit=65536)
        require(not body and checked==dict(complete=True,current_source_settings_preserved=True))
        result.update(complete=True,checkpoint='complete',settings_review_source_current=True)
    except Exception as error:
        result.update(category='retained_rea_finish_incomplete_preserve_evidence',failure_phase=result.get('checkpoint','preflight'),
            error_kind=type(error).__name__ if type(error).__name__ in c['KINDS'] else 'other')
        if isinstance(getattr(error,'owner_diagnostic',None),dict):result['owner_diagnostic']=error.owner_diagnostic
    require(all(read(EXPECTED/name,0)==raw for name,raw in before.items()) and all(read(path,0)==raw for path,raw in policies.items()))
    result.update(prior_failure_preserved=True,all_admission_policies_preserved_disabled=True)
    write(evidence/'summary.json',json.dumps(result,sort_keys=True).encode())
    if result['complete']:write(ticket,json.dumps(result,sort_keys=True).encode())
    print(json.dumps(result,sort_keys=True),flush=True);return 0 if result['complete'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"retained_rea_finish_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
