"""Recover proof with owner-only reads and trusted manager metadata, never replay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import time
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'finish_rea_review_owner.py'))
ROOT=runpy.run_path(str(FOLDER/'finish_rea_dependency_review.py'))
PRIOR=runpy.run_path(str(FOLDER/'review_rea_settings_and_programs.py'))


def proof_receipt():
    return dict(complete=True,java_version_verified=True,ghidra_headless_import_passed=True,
        real_profiles_read=False,rea_server_started=False,model_called=False,external_sends=0)


@pytest.mark.parametrize('damage',[None,'mode','late_change','hardlink','symlink','private_field','duplicate','boolean_counter'])
def test_receipt_is_read_as_actual_owner_without_changing_bookkeeping(tmp_path,damage):
    path=tmp_path/'receipt.json';value=proof_receipt()
    if damage=='private_field':value['private']='invented-DO-NOT-OUTPUT'
    if damage=='boolean_counter':value['external_sends']=False
    raw=json.dumps(value).encode()
    if damage=='duplicate':raw=b'{"complete":false,'+raw[1:]
    path.write_bytes(raw);path.chmod(0o644 if damage=='mode' else 0o600)
    if damage=='hardlink':os.link(path,tmp_path/'other')
    if damage=='symlink':path.rename(tmp_path/'other');path.symlink_to(tmp_path/'other')
    before=path.lstat();cutoff=before.st_ctime_ns-1 if damage=='late_change' else time.time_ns()+10**9
    descriptor=os.open(tmp_path,os.O_PATH|os.O_DIRECTORY)
    try:
        if damage:
            with pytest.raises((ValueError,OSError)):OWNER['receipt_at'](descriptor,os.geteuid(),cutoff)
        else:
            assert OWNER['receipt_at'](descriptor,os.geteuid(),cutoff)==value
            after=path.lstat()
            assert (before.st_atime_ns,before.st_mtime_ns,before.st_ctime_ns)==(after.st_atime_ns,after.st_mtime_ns,after.st_ctime_ns)
    finally:os.close(descriptor)


def test_root_cannot_use_receipt_reader_as_a_privileged_shortcut(monkeypatch):
    monkeypatch.setattr(OWNER['os'],'geteuid',lambda:0)
    with pytest.raises(ValueError):OWNER['receipt_at'](-1,0,1)
    with pytest.raises(ValueError):OWNER['retained_receipt'](1000,'invented-other-id',1)


@pytest.mark.parametrize('damage',[None,'forged_pid','failed_start','duplicate','invocation','boot','missing_stop','reverse','bad_wall'])
def test_journal_proof_uses_only_unique_ordered_pid1_events(damage):
    unit='invented.service';boot='a'*32;invocation='b'*32
    base=dict(_PID='1',_UID='0',_COMM='systemd',UNIT=unit,_BOOT_ID=boot,INVOCATION_ID=invocation)
    rows=[dict(base,JOB_TYPE='start',MESSAGE_ID='7d4958e842da4a758f6c1cdc7b36dcc5',__MONOTONIC_TIMESTAMP='100',__REALTIME_TIMESTAMP='1000'),
        dict(base,JOB_TYPE='start',JOB_RESULT='done',MESSAGE_ID='39f53479d3a045ac8e11786248231fbf',__MONOTONIC_TIMESTAMP='200',__REALTIME_TIMESTAMP='2000'),
        dict(base,JOB_TYPE='stop',JOB_RESULT='done',MESSAGE_ID='9d1aaa27d60140bd96365438aad20286',__MONOTONIC_TIMESTAMP='300',__REALTIME_TIMESTAMP='3000')]
    if damage=='forged_pid':rows[1]['_PID']='123'
    if damage=='failed_start':rows.append(dict(rows[1],JOB_RESULT='failed',__MONOTONIC_TIMESTAMP='150'))
    if damage=='duplicate':rows.append(dict(rows[1],__MONOTONIC_TIMESTAMP='201'))
    if damage=='invocation':rows[1]['INVOCATION_ID']='c'*32
    if damage=='boot':rows[1]['_BOOT_ID']='c'*32
    if damage=='missing_stop':rows.pop()
    if damage=='reverse':rows[0]['__MONOTONIC_TIMESTAMP']='400'
    if damage=='bad_wall':rows[1]['__REALTIME_TIMESTAMP']='not-a-time'
    proof,deadline=ROOT['journal_proof'](rows,unit,boot)
    assert proof['verified'] is (damage is None)
    if not damage:assert deadline==2000999 and proof['invocation_id']==invocation


def test_known_legacy_maps_are_opaque_and_timeout_is_bounded_nonsecret_metadata():
    schema={'approvals':{'timeout':{}},'known_plugin_toolsets':{'cli':{}}}
    old={'approvals':{'timeout':300},'known_plugin_toolsets':{'cli':{'invented-private-name-DO-NOT-OUTPUT':['invented-private-tool']}}}
    new={'approvals':{'timeout':600},'known_plugin_toolsets':{'cli':{'invented-private-name-DO-NOT-OUTPUT':['invented-other-tool']}}}
    value=OWNER['delta'](old,new,schema)
    assert value['redacted_changed_fields']==0 and 'DO-NOT-OUTPUT' not in json.dumps(value)
    assert value['changed_public_fields']==[
        dict(path=['approvals','timeout'],previous=dict(kind='integer',value=300),current=dict(kind='integer',value=600)),
        dict(path=['known_plugin_toolsets','cli'],previous=dict(kind='mapping'),current=dict(kind='mapping'))]
    assert OWNER['safe_value'](('approvals','timeout'),True,True)=={}
    assert OWNER['safe_value'](('approvals','timeout'),100000,True)=={}
    value.update(complete=True,critical_sections_equal=True,source_capsule_verified=True,configuration_semantically_equivalent=False,settings_accepted=False)
    PRIOR['validate_review'](value,dict(public_schema=lambda:schema,safe_value=OWNER['safe_value'],setting_kind=OWNER['setting_kind']))


@pytest.mark.parametrize('review_failure',[False,True])
def test_finish_reuses_completed_execution_and_preserves_failure(monkeypatch,tmp_path,capsys,review_failure):
    scope=ROOT['main'].__globals__;base=tmp_path/'base';expected=base/'operator-evidence/rea-settings-programs-invented';expected.mkdir(parents=True)
    frozen=base/'frozen';context=dict(evidence=str(expected),source_sha256=ROOT['SOURCE_SHA'],id=ROOT['PROOF_ID'])
    pins={'java':dict(sha256='1'*64,size=100),'ghidra':dict(sha256='2'*64,size=200)}
    programs={name:dict(archive_sha256=pin['sha256'],archive_bytes=pin['size'],protected_copy_verified=True,existing_copy_reused=False,disposable_program_restore_verified=True) for name,pin in pins.items()}
    files={expected/'summary.json':b'invented-old',expected/'finish.summary.json':b'invented-old-finish',expected/'programs.json':json.dumps(programs).encode(),expected/'settings-review.json':b'invented-prior-review',
        frozen/'context.private.json':json.dumps(context).encode(),Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    def read(path,*args):return files[path]
    def write(path,raw):
        assert path not in files;files[path]=raw;path.write_bytes(raw)
    calls=[];entry=dict(user='invented-restricted');policy=Path('/invented/policy');files[policy]=b'disabled'
    def owner(account,source,packet,**kwargs):
        mode=packet['mode'];calls.append(mode)
        if mode=='read_retained_receipt':return dict(complete=True,receipt=proof_receipt(),owner_read_verified=True,receipt_unchanged_since_completion=True),b''
        if mode=='capture_source':return dict(fingerprints={'invented':'bound'}),b'invented-cipher'
        if mode=='review_configuration':
            if review_failure:raise ValueError('invented-readonly-review-failure')
            return dict(complete=True,configuration_semantically_equivalent=False,settings_accepted=False),b''
        assert mode=='verify_source';return dict(complete=True,current_source_settings_preserved=True),b''
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:(entry,{}))
    c=dict(legacy=lambda:driver,owner=owner,packet=lambda account,mode,**kw:dict(mode=mode,**kw),decrypt=lambda *a,**kw:b'invented-capsule',KINDS={'ValueError'})
    old=dict(OWNER_SHA='invented',validate_current=lambda *a:None,retained_live=lambda read:{'new_inactive_candidate':'invented'},authenticated_profile_archive=lambda *a:b'invented-archive')
    prior=dict(FROZEN=base/'prior-artifact',helpers=lambda:(old,c,read,write),retained=lambda *a:None,definitions=lambda *a:dict(PROGRAMS=pins,_verified_source_bytes=b'invented-old-code'),
        validate_review=lambda *a:None,pwd=SimpleNamespace(getpwnam=lambda name:SimpleNamespace(pw_name=name)))
    owner_module=dict(_verified_source_bytes=b'invented-owner-source')
    script=tmp_path/'operator.py';script.write_bytes(b'invented-operator-source')
    for name,value in dict(BASE=base,FROZEN=frozen,EXPECTED=expected,__file__=str(script),definitions=lambda path,*a:prior if path.name=='review_rea_settings_and_programs.py' else owner_module,
        retained=lambda *a:None,proof_from_journal=lambda *a:(dict(verified=True),1000000)).items():monkeypatch.setitem(scope,name,value)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setattr(ROOT['sys'],'argv',['operator.py'])
    assert ROOT['main']()==(1 if review_failure else 0)
    result=json.loads(capsys.readouterr().out)
    assert result['rea_dependency_execution_qualified'] is True and result['retained_program_execution_reused'] is True
    assert result['programs_replayed'] is result['services_started'] is result['settings_accepted'] is result['candidate_promoted'] is result['fleet_launch_approved'] is False
    assert result['credentials_issued']==result['encrypted_generations_created']==0
    assert result['complete'] is (not review_failure)
    assert calls==['read_retained_receipt','capture_source','review_configuration']+([] if review_failure else ['verify_source'])
    assert files[expected/'finish.summary.json']==b'invented-old-finish'
    if not review_failure:
        before=list(calls);assert ROOT['main']()==0;assert calls==before
        assert json.loads(capsys.readouterr().out)==result
    else:
        component=[path for path in files if path.name=='dependency-component.summary.json']
        assert len(component)==1 and json.loads(files[component[0]])['rea_dependency_execution_qualified'] is True


def test_pins_and_owner_protocol_preserve_old_attempt():
    assert ROOT['SOURCE_SHA']==hashlib.sha256((FOLDER/'review_rea_settings_and_programs.py').read_bytes()).hexdigest()
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'finish_rea_review_owner.py').read_bytes()).hexdigest()
    assert OWNER['FROZEN_SHA']==hashlib.sha256((FOLDER/'rea_candidate_owner_v3.py').read_bytes()).hexdigest()
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'finish_rea_review_owner.py').read_bytes())
