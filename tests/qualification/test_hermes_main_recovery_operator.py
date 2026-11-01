"""Main-state recovery transport keeps root keys private and coverage honest."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sqlite3
from types import SimpleNamespace

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
MODULE=runpy.run_path(str(DIRECTORY/'continue_launch_main_operational.py'),run_name='main_recovery_operator_test')
CORE=runpy.run_path(str(DIRECTORY/'capture_main_operational_profile_v3.py'),run_name='main_recovery_core_contract_test')
PUBLIC=(DIRECTORY/'capture_main_operational_profile_v3.py').read_text()
IDENT='a'*16


def packet(mode='capture'):
    value=dict(mode=mode,profile_id=IDENT,core=PUBLIC)
    if mode=='capture':value['recipient']='age1'+'a'*40
    else:value['archive_bytes']=4
    return value


@pytest.mark.parametrize('change',['root_signing_key','recovery_key','mode','core','identity','oversize','boolean_length'])
def test_bad_or_privileged_owner_packets_stop_before_any_child(change,monkeypatch):
    value=packet('restore')
    if change=='root_signing_key':value['ENHANCED_BACKUP_SIGNING_KEY']='invented-root-key'
    elif change=='recovery_key':value['identity']='invented-private-age-key'
    elif change=='mode':value['mode']='command'
    elif change=='core':value['core']='unreviewed public code'
    elif change=='identity':value['profile_id']='root'
    elif change=='oversize':value['archive_bytes']=MODULE['ARCHIVE_LIMIT']+1
    elif change=='boolean_length':value['archive_bytes']=True
    monkeypatch.setattr(MODULE['subprocess'],'run',lambda *a,**kw:pytest.fail('invalid packet crossed owner boundary'))
    with pytest.raises(ValueError):MODULE['owner']({},None,b'public',value,b'data')


def capture_receipt():
    return dict(files=2,source_bytes=1024,sqlite_databases=1,sidecars_rebuilt=0,database_versions_stable=True,
        plain_files_stable=True,plaintext_archive_written=False,omitted_entries=3,source_profiles_preserved=True,
        source_logical_writes_performed=False,sqlite_read_bookkeeping_may_change=True,
        full_profile_recovery_qualified=False,executable_rebuild_qualified=False,
        database_snapshots_consistent=True,database_snapshot_mode='read_transaction_per_database',
        live_database_changes_observed=0,global_atomic_snapshot_qualified=False)


def restore_receipt():
    return dict(complete=True,archived_files_verified=True,private_restore_verified=True,sqlite_databases_verified=1,
        restored_profile_executed=False,operational_restore_qualified=True,full_profile_recovery_qualified=False,
        executable_rebuild_qualified=False,database_snapshot_mode='read_transaction_per_database',
        global_atomic_snapshot_qualified=False)


def test_binary_owner_frame_never_uses_arguments_environment_or_plaintext_disk(monkeypatch):
    ciphertext=b'age-encryption.org/v1\ninvented-encrypted-data'
    header=dict(complete=True,receipt=capture_receipt(),ciphertext_bytes=len(ciphertext))
    def run(args,**kw):
        assert kw['user']==1234 and kw['group']==1234 and kw['extra_groups']==()
        assert kw['stderr'] is MODULE['subprocess'].DEVNULL
        assert kw['input'].splitlines()[0]==b'public-source'
        request=json.loads(kw['input'].splitlines()[1])
        assert set(request)=={'mode','core','profile_id','recipient'}
        assert 'recipient' not in repr(args) and request['recipient'] not in repr(kw['env'])
        return SimpleNamespace(returncode=0,stdout=json.dumps(header).encode()+b'\n'+ciphertext)
    monkeypatch.setattr(MODULE['subprocess'],'run',run)
    value,body=MODULE['owner']({'owner_program':lambda source:('public',b'public-source\n'),'EXECUTABLE':'/protected/python'},
        SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/fixed/home'),b'public',packet())
    assert body==ciphertext and value['receipt']['full_profile_recovery_qualified'] is False


@pytest.mark.parametrize('change',['coverage','executed','other_home','private_extra','unbounded_count','global_atomic','snapshot_mode'])
def test_restore_cannot_inflate_coverage_execute_data_or_change_owner(change):
    account=SimpleNamespace(pw_dir='/fixed/home')
    value=dict(complete=True,destination='/fixed/home/ec-main-operational-restore-invented',receipt=restore_receipt())
    if change=='coverage':value['receipt']['full_profile_recovery_qualified']=True
    elif change=='executed':value['receipt']['restored_profile_executed']=True
    elif change=='other_home':value['destination']='/other/home/ec-main-operational-restore-invented'
    elif change=='private_extra':value['private_detail']='invented-must-not-return'
    elif change=='unbounded_count':value['receipt']['sqlite_databases_verified']=20001
    elif change=='global_atomic':value['receipt']['global_atomic_snapshot_qualified']=True
    elif change=='snapshot_mode':value['receipt']['database_snapshot_mode']='unverified'
    with pytest.raises(ValueError):MODULE['validate_owner_result'](value,b'','restore',account)


def test_actual_core_receipts_fit_operator_contract_and_keep_coverage_open(tmp_path):
    profile=tmp_path/'source';profile.mkdir(mode=0o700)
    (profile/'.env').write_bytes(b'INVENTED_NOT_A_REAL_KEY=test-only')
    with sqlite3.connect(profile/'state.db') as db:db.execute('CREATE TABLE invented(value TEXT)')
    archive,receipt=CORE['capture'](profile,online_databases=True)
    ciphertext=b'age-encryption.org/v1\ninvented-ciphertext'
    MODULE['validate_owner_result'](dict(complete=True,receipt=receipt,ciphertext_bytes=len(ciphertext)),ciphertext,'capture',None)
    destination,recovered=CORE['restore'](archive)
    MODULE['validate_owner_result'](dict(complete=True,receipt=recovered,destination=destination),b'','restore',SimpleNamespace(pw_dir='/tmp'))
    assert recovered['sqlite_databases_verified']==1 and recovered['restored_profile_executed'] is False


def test_root_crypto_key_stays_out_of_owner_packets_and_published_evidence(tmp_path,monkeypatch):
    function=MODULE['worker'];state=function.__globals__
    artifact=tmp_path/'operator-main-operational-recovery-v2';artifact.mkdir()
    (artifact/'capture_main_operational_profile_v3.py').write_text(PUBLIC)
    executable=artifact/'continue_launch_main_operational.py';executable.write_bytes(b'public-wrapper-source')
    evidence=tmp_path/'operator-evidence/main-operational-recovery-invented';evidence.mkdir(parents=True)
    source=SimpleNamespace(pw_name='vincentspereira',pw_uid=1000,pw_gid=1000,pw_dir='/fixed/source')
    target=SimpleNamespace(pw_name='ecbot_'+IDENT,pw_uid=1234,pw_gid=1234,pw_dir='/fixed/target')
    row={'profile_id':IDENT}
    key='invented-root-backup-signing-key-kept-private'
    archive=b'invented-main-operational-plaintext'
    ciphertext=b'age-encryption.org/v1\ninvented-ciphertext'
    events=[];writes={}
    def owner(helper,account,code,request,payload=b''):
        events.append(request['mode'])
        assert key not in repr(request) and key.encode() not in payload
        assert all('KEY' not in name for name in request)
        if request['mode']=='capture':
            assert account is source and payload==b''
            return {'complete':True,'receipt':capture_receipt()},ciphertext
        assert account is target and payload==archive
        return {'complete':True,'receipt':restore_receipt(),'destination':'/fixed/target/ec-main-operational-restore-invented'},b''
    def read(path,uid,*limits):
        if path.name=='context.json':return json.dumps({'evidence':str(evidence)}).encode()
        if path.name in {'fleet-credentials.json','candidate-policy.json'}:return b'{"profiles":[{"enabled":false}]}'
        if path.name=='backup.json':return json.dumps(dict(ENHANCED_BACKUP_SIGNING_KEY=key,
            ENHANCED_BACKUP_SIGNING_KEY_ID='invented-signing-id',ENHANCED_BACKUP_RECIPIENT='age1'+'a'*40)).encode()
        return writes[path]
    def age(args,**kwargs):
        assert args[0]==str(MODULE['AGE']) and kwargs['input']==ciphertext
        assert key not in repr(args) and key not in repr(kwargs['env'])
        return SimpleNamespace(stdout=archive)
    monkeypatch.setattr(MODULE['os'],'geteuid',lambda:0)
    monkeypatch.setattr(MODULE['subprocess'],'run',age)
    for name,value in dict(BASE=tmp_path,ARTIFACT=artifact,__file__=str(executable),selected=lambda read:(row,source,target),
        definitions=lambda *a:{},owner=owner,sync=lambda *a:None,retained_failure=lambda *a:None).items():monkeypatch.setitem(state,name,value)
    assert function(read,lambda path,raw:writes.setdefault(path,raw))==0
    result=json.loads(writes[evidence/'summary.json'])
    assert events==['capture','restore']
    assert result['main_operational_snapshot_restore_qualified'] is True
    assert result['main_profile_backup_qualified'] is result['full_profile_recovery_qualified'] is False
    assert result['executable_rebuild_qualified'] is result['fleet_launch_approved'] is False
    assert all(key.encode() not in raw and archive not in raw for raw in writes.values())


def test_repeat_attaches_without_creating_another_main_generation(monkeypatch):
    launch=MODULE['launch'];state=launch.__globals__
    monkeypatch.setattr(MODULE['os'],'geteuid',lambda:0)
    monkeypatch.setattr(MODULE['os'].path,'lexists',lambda path:True)
    monkeypatch.setitem(state,'definitions',lambda *a:{'read_file':None,'private_write':None})
    monkeypatch.setitem(state,'selected',lambda *a:pytest.fail('must not capture again'))
    monkeypatch.setitem(state,'watch',lambda *a:42)
    assert launch()==42


@pytest.mark.parametrize('checkpoint',['payload_read','invented-private-detail'])
def test_owner_failure_forwards_only_fixed_diagnostics(monkeypatch,checkpoint):
    body=dict(complete=False,phase='capture',error_kind='CaptureError',capture_checkpoint=checkpoint,
              capture_reason='durable_file_changed_before_read')
    monkeypatch.setattr(MODULE['subprocess'],'run',lambda *a,**kw:SimpleNamespace(returncode=1,stdout=json.dumps(body).encode()+b'\n'))
    with pytest.raises(ValueError) as error:
        MODULE['owner']({'owner_program':lambda source:('public',b'public\n'),'EXECUTABLE':'/protected/python'},
            SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/fixed/home'),b'public',packet())
    assert getattr(error.value,'capture_checkpoint',None)==('payload_read' if checkpoint=='payload_read' else None)
    assert error.value.capture_reason=='durable_file_changed_before_read'
    assert 'invented-private-detail' not in str(error.value)


def test_continuation_refuses_any_attempt_that_already_created_a_generation():
    previous=dict(complete=False,failure_phase='capture',owner_error_kind='CaptureError',owner_phase='capture',
        encrypted_generations_created=1,disposable_restores_qualified=0,generation_write_started=True,
        restored_candidate_may_exist=False,all_admission_policies_preserved_disabled=True)
    with pytest.raises(ValueError):MODULE['retained_failure'](lambda *a:json.dumps(previous).encode())


def test_public_sources_are_pinned_and_fit_owner_pipe():
    for name,digest in MODULE['PINS'].items():assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest
    helper=runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'),run_name='main_owner_protocol_check')
    helper['owner_program']((DIRECTORY/'continue_launch_main_operational.py').read_bytes())
    control=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='main_recovery_dispatch_test')
    assert hashlib.sha256((DIRECTORY/'backup_launch_main_operational.py').read_bytes()).hexdigest()==control['MAIN_BACKUP_SHA']
    assert hashlib.sha256((DIRECTORY/'continue_launch_main_operational.py').read_bytes()).hexdigest()==control['MAIN_CONTINUE_SHA']
