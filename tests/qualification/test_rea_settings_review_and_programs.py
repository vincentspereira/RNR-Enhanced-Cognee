"""Safe settings metadata does not authorize settings or block offline proof."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'review_rea_configuration_owner.py'))
ROOT=runpy.run_path(str(FOLDER/'review_rea_settings_and_programs.py'))
SCHEMA={'_config_version':{},'agent':{'max_turns':{}},'display':{'interface':{},'personality':{},'compact':{}},'providers':{}}


def review():
    value=OWNER['delta']({'agent':{'max_turns':4}},{'agent':{'max_turns':8}},SCHEMA)
    value.update(complete=True,critical_sections_equal=True,source_capsule_verified=True,
        configuration_semantically_equivalent=False,settings_accepted=False)
    return value


def test_private_names_values_and_hashes_never_enter_delta():
    before={'private-field-DO-NOT-OUTPUT':'invented-before-DO-NOT-OUTPUT','display':{'personality':'invented-private-old-DO-NOT-OUTPUT'},
        'providers':{'private-provider-DO-NOT-OUTPUT':{'api_key':'invented-old-key-DO-NOT-OUTPUT'}},'agent':{'max_turns':4}}
    after=copy.deepcopy(before);after['private-field-DO-NOT-OUTPUT']='invented-new-DO-NOT-OUTPUT'
    after['display']['personality']='invented-private-new-DO-NOT-OUTPUT';after['providers']['private-provider-DO-NOT-OUTPUT']['api_key']='invented-new-key-DO-NOT-OUTPUT'
    after['agent']['max_turns']=8
    result=OWNER['delta'](before,after,SCHEMA)
    assert result['redacted_changed_fields']==2
    assert result['changed_public_fields']==[
        {'path':['agent','max_turns'],'previous':{'kind':'integer','value':4},'current':{'kind':'integer','value':8}},
        {'path':['display','personality'],'previous':{'kind':'string'},'current':{'kind':'string'}}]
    assert 'DO-NOT-OUTPUT' not in json.dumps(result)
    assert before['agent']['max_turns']==4 and after['agent']['max_turns']==8


@pytest.mark.parametrize('path,value,allowed',[
    (('agent','max_turns'),None,True),(('agent','max_turns'),8,True),(('agent','max_turns'),True,False),
    (('agent','max_turns'),10**10,False),(('display','interface'),'tui',True),
    (('display','interface'),'invented-private-string',False),(('display','personality'),'invented-private-string',False)])
def test_only_closed_nonsecret_values_are_projected(path,value,allowed):
    assert bool(OWNER['safe_value'](path,value,True)) is allowed


@pytest.mark.parametrize('damage',[None,'private_path','secret_value','wrong_kind','accepted','private_top','excessive_rows'])
def test_root_rechecks_every_projected_field_before_publication(damage):
    value=review()
    if damage=='private_path':value['changed_public_fields'][0]['path']=['invented-private-field']
    if damage=='secret_value':value['changed_public_fields'][0].update(path=['display','personality'],current={'kind':'string','value':'invented-private-value'})
    if damage=='wrong_kind':value['changed_public_fields'][0]['current']['kind']='string'
    if damage=='accepted':value['settings_accepted']=True
    if damage=='private_top':value['private']=dict(value='invented-secret')
    if damage=='excessive_rows':value['changed_public_fields']*=129
    owner=dict(public_schema=lambda:SCHEMA,safe_value=OWNER['safe_value'],setting_kind=OWNER['setting_kind'])
    if damage:
        with pytest.raises(ValueError):ROOT['validate_review'](value,owner)
    else:ROOT['validate_review'](value,owner)


@pytest.mark.parametrize('damage',[None,'credentials','generation','changed_model','running','later_phase'])
def test_only_exact_stopped_configuration_refusal_is_admitted(monkeypatch,tmp_path,damage):
    scope=ROOT['retained'].__globals__;base=tmp_path/'base';frozen=base/'frozen';frozen.mkdir(parents=True)
    expected=base/'operator-evidence/rea-main-programs-invented';expected.mkdir(parents=True)
    value=dict(source_revision=base.name,operator_helper_sha256=ROOT['SOURCE_SHA'],evidence=str(expected),complete=False,
        operator_job_stopped=True,credentials_issued=0,encrypted_generations_created=0,previous_configuration_bytes_equal=False,
        category='rea_configuration_changed_requires_review_no_effectful_retry',checkpoint='configuration_equivalence',failure_phase='configuration_equivalence',
        configuration_comparison=dict(complete=True,source_capsule_verified=True,configuration_semantically_equivalent=False,changed_sections=['other_settings']),
        all_admission_policies_preserved_disabled=True)
    value.update({k:False for k in ('source_profiles_changed','source_programs_changed','previous_candidates_changed','candidate_promoted',
        'daily_backup_registry_changed','canonical_memory_edits','chat_model_called','rea_server_started','fleet_launch_approved','production_renewal_timer_enabled')})
    if damage=='credentials':value['credentials_issued']=1
    if damage=='generation':value['encrypted_generations_created']=1
    if damage=='changed_model':value['configuration_comparison']['changed_sections']=['model']
    files={frozen/'context.private.json':json.dumps(dict(source_sha256=ROOT['SOURCE_SHA'],evidence=str(expected))).encode(),expected/'finish.summary.json':json.dumps(value).encode()}
    phases=('model_binding','current_settings_capture','configuration_equivalence','public_programs')
    for phase in phases[:3]:files[expected/(phase+'.started.json')]=json.dumps(dict(phase=phase)).encode()
    if damage=='later_phase':(expected/'public_programs.started.json').write_text('{"phase":"public_programs"}')
    for name,var in dict(BASE=base,FROZEN=frozen,EXPECTED=expected).items():monkeypatch.setitem(scope,name,var)
    old=dict(metadata=lambda unit:{},stopped=lambda state:damage!='running',UNIT='invented',PHASES=phases)
    if damage:
        with pytest.raises(ValueError):ROOT['retained'](old,lambda path,*a:files[path])
    else:assert ROOT['retained'](old,lambda path,*a:files[path])==value


@pytest.mark.parametrize('existing',[False,True])
def test_program_proof_reuses_verified_existing_copy_and_never_writes_old_artifact(monkeypatch,tmp_path,existing):
    scope=ROOT['qualify_programs'].__globals__;artifact=tmp_path/'new-artifact';frozen=tmp_path/'old-artifact';programs=tmp_path/'programs'
    programs.mkdir();evidence=tmp_path/'evidence';evidence.mkdir()
    pin={'size':1,'sha256':hashlib.sha256(b'x').hexdigest()};events=[];files={}
    if existing:(programs/('rea-java-'+pin['sha256'][:16])).mkdir()
    parent=dict(PROGRAMS={'java':pin},_verified_source_bytes=b'invented-public-code')
    def restore(body,name,path):events.append(('restore',path));assert path!=frozen
    snapshot=dict(MAX_ARCHIVE=1024,restore=restore,validate=lambda body,name:dict(invented=True),verify=lambda path,manifest:events.append(('verify',path)))
    monkeypatch.setitem(scope,'ARTIFACT',artifact);monkeypatch.setitem(scope,'FROZEN',frozen)
    monkeypatch.setitem(scope,'definitions',lambda path,*a:parent if path.name=='rea_candidate_owner_v3.py' else snapshot)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name))
    def probe(context,account,paths,read,write):
        assert old['ARTIFACT']==artifact;events.append(('probe',paths));return dict(complete=True,qualification_unit_stopped=True)
    old=dict(OWNER_SHA='invented',SNAPSHOT_SHA='invented',PROGRAM_ROOT=programs,ARTIFACT=frozen,program_probe=probe)
    def owner(*args,**kw):return dict(complete=True,program='java',archive_bytes=1,archive_sha256=pin['sha256']),b'x'
    c=dict(owner=owner,packet=lambda account,mode,**kw:dict(mode=mode,**kw))
    result,proof=ROOT['qualify_programs'](old,c,lambda *a:None,lambda path,raw:files.update({path:raw}),dict(id='a'*32,evidence=str(evidence)),SimpleNamespace())
    assert result['java']['existing_copy_reused'] is existing and proof['complete']
    assert [event[0] for event in events]==(['verify','restore','probe'] if existing else ['restore','restore','probe'])
    assert set(files)=={evidence/'programs.json'} and not frozen.exists()


@pytest.mark.parametrize('drift',[False,True])
def test_group_finishes_independent_proof_while_settings_remain_unaccepted(monkeypatch,tmp_path,drift):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    expected=base/'operator-evidence/rea-main-programs-failed';expected.mkdir(parents=True)
    evidence=base/'operator-evidence/rea-settings-programs-invented';evidence.mkdir()
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='b'*32);policy=Path('/invented/policy')
    files={artifact/'context.private.json':json.dumps(context).encode(),expected/'summary.json':b'invented-old',expected/'finish.summary.json':b'invented-finished',
        policy:b'disabled',Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    entry=dict(user='invented-restricted');events=[]
    def owner(account,source,packet,**kw):
        mode=packet['mode'];events.append(mode)
        if mode=='capture_source':return dict(fingerprints={'invented':'bound'}),b'invented-cipher'
        if mode=='review_configuration':return review(),b''
        assert mode=='verify_source'
        if drift:raise ValueError('invented-current-source-drift')
        return dict(complete=True,current_source_settings_preserved=True),b''
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:(entry,{}))
    c=dict(legacy=lambda:driver,owner=owner,packet=lambda account,mode,**kw:dict(mode=mode,**kw),decrypt=lambda *a,**kw:b'invented-capsule',KINDS={'ValueError'})
    old=dict(OWNER_SHA='invented',validate_current=lambda *a:None,retained_live=lambda read:{'new_inactive_candidate':'/invented/profile'},authenticated_profile_archive=lambda *a:b'invented-archive')
    child=dict(_verified_source_bytes=b'invented-source',public_schema=lambda:SCHEMA,safe_value=OWNER['safe_value'],setting_kind=OWNER['setting_kind'])
    proof=dict(complete=True,qualification_unit_stopped=True,java_version_verified=True,ghidra_headless_import_passed=True)
    def programs(*args,**kwargs):
        kwargs['checkpoint']('isolated_program_execution')
        events.append('offline_program_proof');return {'invented':'public-pins'},proof
    for name,value in dict(BASE=base,ARTIFACT=artifact,EXPECTED=expected,__file__=str(artifact/'review_rea_settings_and_programs.py'),helpers=lambda:(old,c,read,write),retained=lambda *a:{},definitions=lambda *a:child,qualify_programs=programs).items():monkeypatch.setitem(scope,name,value)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','c'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name))
    assert ROOT['worker']()==(1 if drift else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['rea_dependency_execution_qualified'] is True and result['complete'] is (not drift)
    assert result['settings_accepted'] is result['source_profiles_changed'] is result['candidate_promoted'] is result['fleet_launch_approved'] is False
    assert result['credentials_issued']==result['encrypted_generations_created']==0
    assert result['prior_failure_preserved'] is result['configuration_review_required'] is True
    assert result['settings_review_source_current'] is (not drift)
    assert events==['capture_source','review_configuration','offline_program_proof','verify_source']
    assert files[expected/'summary.json']==b'invented-old' and files[expected/'finish.summary.json']==b'invented-finished'


def test_frozen_helpers_and_owner_protocol_are_exact():
    assert ROOT['SOURCE_SHA']==hashlib.sha256((FOLDER/'reconcile_rea_configuration.py').read_bytes()).hexdigest()
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'review_rea_configuration_owner.py').read_bytes()).hexdigest()
    assert OWNER['FROZEN_SHA']==hashlib.sha256((FOLDER/'rea_candidate_owner_v3.py').read_bytes()).hexdigest()
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'review_rea_configuration_owner.py').read_bytes())


@pytest.mark.parametrize('complete',[False,True])
def test_finished_job_is_returned_without_restarting_or_repeating_proof(monkeypatch,tmp_path,capsys,complete):
    scope=ROOT['watch'].__globals__;artifact=tmp_path/'artifact';artifact.mkdir()
    evidence=tmp_path/'operator-evidence/rea-settings-programs-invented';evidence.mkdir(parents=True)
    (artifact/'context.private.json').write_text(json.dumps(dict(source_sha256='a'*64,evidence=str(evidence))))
    result=dict(complete=complete,operator_job_stopped=True,operator_helper_sha256='a'*64,credentials_issued=0,settings_accepted=False)
    (evidence/'finish.summary.json').write_text(json.dumps(result))
    monkeypatch.setitem(scope,'BASE',tmp_path);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    assert ROOT['watch']({},lambda path,*a:path.read_bytes(),lambda *a:pytest.fail('retained result rewritten'))==(0 if complete else 1)
    assert json.loads(capsys.readouterr().out)==result


def test_program_failure_projects_only_fixed_receipt_fields(monkeypatch,tmp_path):
    scope=ROOT['qualify_programs'].__globals__;artifact=tmp_path/'new';frozen=tmp_path/'old'
    monkeypatch.setitem(scope,'ARTIFACT',artifact);monkeypatch.setitem(scope,'FROZEN',frozen)
    parent=dict(PROGRAMS={},_verified_source_bytes=b'invented')
    monkeypatch.setitem(scope,'definitions',lambda path,*a:parent if path.name=='rea_candidate_owner_v3.py' else {})
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name))
    def failed(*args):raise ValueError('invented-private-error-DO-NOT-OUTPUT')
    old=dict(OWNER_SHA='invented',SNAPSHOT_SHA='invented',program_probe=failed)
    receipt=dict(complete=False,java_version_verified=True,ghidra_headless_import_passed=False,
        real_profiles_read=False,rea_server_started=False,model_called=False,error_kind='invented-private-kind-DO-NOT-OUTPUT',
        private_value='invented-secret-DO-NOT-OUTPUT')
    def read(path,uid,limit):
        assert path==Path('/run/ec-rea-program-proof-'+'a'*32+'/receipt.json') and uid==3001 and limit==65536
        return json.dumps(receipt).encode()
    with pytest.raises(ValueError) as failure:
        ROOT['qualify_programs'](old,{},read,lambda *a:None,dict(id='a'*32,evidence=str(tmp_path)),SimpleNamespace(pw_uid=3001))
    projected=failure.value.program_diagnostic
    assert projected['receipt_available'] is projected['java_version_verified'] is True
    assert projected['ghidra_headless_import_passed'] is False and projected['error_kind']=='other'
    assert 'DO-NOT-OUTPUT' not in json.dumps(projected)
