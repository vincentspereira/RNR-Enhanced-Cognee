"""Current limits are preserved without admitting unrelated configuration drift."""
import copy
import base64
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest
import yaml

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'assess_rea_candidate_settings_owner.py'))
ROOT=runpy.run_path(str(FOLDER/'prepare_main_after_rea.py'))


@pytest.mark.parametrize('change',['unchanged','timeout','offered_registry','approval_mode','selected_tools','disabled_tools','other_setting','version','wrong_timeout','wrong_scalar','new_platform','implicit_selection'])
def test_only_reviewed_limit_and_bounded_bookkeeping_can_be_preserved(change):
    old=dict(approvals=dict(mode='smart',timeout=900,unattended_mode='deny'),agent=dict(disabled_toolsets=[]),
        platform_toolsets=dict(cli=['hermes-cli']),known_builtin_toolsets=dict(cli=['terminal']),version=1)
    new=copy.deepcopy(old)
    if change=='timeout':new['approvals']['timeout']=600
    if change=='offered_registry':new['known_builtin_toolsets']['cli'].append('invented-offered-tool')
    if change=='approval_mode':new['approvals']['mode']='off'
    if change=='selected_tools':new['platform_toolsets']['cli'].append('invented-tool')
    if change=='disabled_tools':new['agent']['disabled_toolsets'].append('invented-tool')
    if change=='other_setting':new['invented-private-setting']='invented-value'
    if change=='version':new['version']=2
    if change=='wrong_timeout':new['approvals']['timeout']=601
    if change=='wrong_scalar':new['version']=True
    if change=='new_platform':new['known_builtin_toolsets']['invented-platform']=[]
    if change=='implicit_selection':old.pop('platform_toolsets');new.pop('platform_toolsets');new['known_builtin_toolsets']['cli'].append('invented-offered-tool')
    before=copy.deepcopy((old,new));result=OWNER['preservation_policy'](old,new,{'cli','whatsapp'})
    assert result['inactive_preparation_allowed'] is (change in {'unchanged','timeout','offered_registry'})
    assert result['fleet_settings_accepted'] is False and (old,new)==before
    assert result['allowed_preserved_changes']==(['approvals.timeout'] if change=='timeout' else ['known_builtin_toolsets'] if change=='offered_registry' else [])


@pytest.mark.parametrize('damage',[None,'not_complete','receipt_changed','replayed','accepted','bad_archive'])
def test_completed_dependency_pass_is_required_without_replaying_it(monkeypatch,damage):
    proof=dict(verified=True,invocation_id='e88c25dbc8bc44728c107fcd307f47f9',predicates={key:True for key in ('unique_start_completion_and_stop','same_invocation','ordered_monotonic_events','same_current_boot','no_conflicting_start_failure')})
    value=dict(source_revision=ROOT['BASE'].name,operator_helper_sha256=ROOT['FINISH_SHA'],evidence=str(ROOT['PASSED'].parent),
        credentials_issued=0,encrypted_generations_created=0,journal_execution_proof=proof,
        program_snapshots=dict(java=dict(archive_sha256='a'*64,archive_bytes=100,protected_copy_verified=True,disposable_program_restore_verified=True)))
    for key in ('complete','owner_read_verified','receipt_unchanged_since_completion','rea_dependency_execution_qualified','java_version_verified','ghidra_headless_import_passed',
        'retained_staging_and_readback_reused','retained_program_execution_reused','all_admission_policies_preserved_disabled'):value[key]=True
    for key in ('programs_replayed','services_started','settings_accepted','source_profiles_changed','previous_candidates_changed','candidate_promoted','canonical_memory_edits','memory_api_called','chat_model_called','fleet_launch_approved'):value[key]=False
    if damage=='not_complete':value['complete']=False
    if damage=='receipt_changed':value['receipt_unchanged_since_completion']=False
    if damage=='replayed':value['programs_replayed']=True
    if damage=='accepted':value['settings_accepted']=True
    if damage=='bad_archive':value['program_snapshots']['java']['archive_sha256']='b'*64
    parent=dict(PROGRAMS=dict(java=dict(sha256='a'*64,size=100)))
    if damage:
        with pytest.raises(ValueError):ROOT['retained_pass'](lambda *a:json.dumps(value).encode(),parent)
    else:assert ROOT['retained_pass'](lambda *a:json.dumps(value).encode(),parent)==value


@pytest.mark.parametrize('damage',[None,'unreviewed','early_drift','late_drift'])
def test_whole_group_reuses_dependency_pass_and_requires_policy_before_issuance(monkeypatch,tmp_path,damage):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-rea-reviewed-invented';evidence.mkdir(parents=True)
    passed=base/'operator-evidence/retained-pass.json';policy=Path('/invented/policy')
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='b'*32,restore_id='c'*32)
    files={artifact/'context.private.json':json.dumps(context).encode(),passed:b'invented-retained-pass',policy:b'disabled',Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    entry=dict(user='ecbot_'+'d'*16,home='/var/lib/enhanced-cognee-profiles/'+'d'*16)
    destination=entry['home']+'/ec-main-operational-restore-invented';modes=[];issued=[];generations=[];verifications=[]
    cipher=b'age-encryption.org/v1\ninvented';fingerprints={'config.yaml':'1'*64,'.env':'2'*64,'auth.json':'3'*64}
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    def owner(account,source,packet,**kwargs):
        mode=packet['mode'];modes.append(mode)
        if mode=='capture_source':return dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},fingerprints=fingerprints,mcp_definitions=6,source_configuration_preserved=True,ciphertext_bytes=len(cipher)),cipher
        if mode=='assess_configuration':
            assert not issued and not generations and kwargs['body']==b'invented-capsuleinvented-original-archive'
            return dict(complete=True,review={'critical_sections_equal':True},inactive_preparation_allowed=damage!='unreviewed',allowed_preserved_changes=['approvals.timeout'],fleet_settings_accepted=False),b''
        if mode=='verify_source':
            assert packet['fingerprints']==fingerprints;verifications.append(mode)
            if damage=='early_drift' or (damage=='late_drift' and len(verifications)==2):raise ValueError('invented-source-change')
            return dict(complete=True,current_source_settings_preserved=True),b''
        if mode=='prepare':
            assert packet['model_key']=='invented-qualified-key' and kwargs['body']==b'invented-capsuleinvented-original-archive'
            return dict(complete=True,remaining_reference_count=0,rea_definition_preserved=True,settings_and_oauth_preserved=True,scoped_status_authenticated=True,
                current_auth_snapshot_preserved=True,current_source_settings_refreshed=True,destination=destination,mcp_definitions=6),b''
        if mode=='capture_candidate':return dict(complete=True,receipt={'sqlite_databases':9}),cipher
        assert mode=='restore_candidate' and packet['fingerprints']==fingerprints and packet['id']=='c'*32
        return dict(mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,oauth_and_environment_preserved=True,current_auth_snapshot_preserved=True,
            receipt={'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':9}),b''
    def fresh_bundle(entry):issued.append(entry);return {'token':'invented-ordinary-token'}
    def generation(kind,*args):generations.append(kind);return Path('/invented/'+kind+'.age'),kind.encode()
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:(entry,{}),fresh_bundle=fresh_bundle,
        PINS={'continue_launch_main_operational.py':'invented'},definitions=lambda *a:{'validate_owner_result':lambda *a:None})
    c=dict(legacy=lambda:driver,owner=owner,packet=lambda account,mode,**kw:dict(mode=mode,**kw),runtime_model=lambda *a:'invented-qualified-key',PACKAGE=Path('/invented/package'),
        generation=generation,decrypt=lambda cipher,**kw:b'invented-capsule' if kw.get('configuration') else b'invented-restored-archive',KINDS={'ValueError'})
    old=dict(OWNER_SHA='invented',PROGRAM_ROOT=Path('/opt/hermes-runtime/programs'),validate_current=lambda *a:None,
        retained_live=lambda read:{'new_inactive_candidate':destination},authenticated_profile_archive=lambda *a:b'invented-original-archive')
    parent=dict(_verified_source_bytes=b'invented-frozen-parent',PROGRAMS={'java':{'sha256':'e'*64}})
    def definitions(path,*args):
        if path.name=='rea_candidate_owner_v3.py':return parent
        if path.name=='assess_rea_candidate_settings_owner.py':return {'_verified_source_bytes':b'invented-assessor'}
        assert path.name=='review_rea_settings_and_programs.py';return {'validate_review':lambda *a:None}
    for name,value in dict(BASE=base,ARTIFACT=artifact,PASSED=passed,__file__=str(artifact/'prepare_main_after_rea.py'),helpers=lambda:(old,c,read,write),retained_pass=lambda *a:{},definitions=definitions).items():monkeypatch.setitem(scope,name,value)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','f'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert ROOT['worker']()==(1 if damage else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['complete'] is (damage is None) and result['rea_dependency_execution_qualified'] is True
    assert result['programs_replayed'] is result['candidate_promoted'] is result['source_profiles_changed'] is result['fleet_settings_accepted'] is result['fleet_launch_approved'] is False
    assert result['prior_dependency_pass_preserved'] is result['all_admission_policies_preserved_disabled'] is True
    assert files[passed]==b'invented-retained-pass'
    if damage in {'unreviewed','early_drift'}:assert not issued and not generations and result['credentials_issued']==0
    else:assert len(issued)==1 and generations==['configuration','configured'] and result['credentials_issued']==2
    if damage=='unreviewed':assert result['category']=='unreviewed_setting_change_requires_review_no_credentials_issued'
    if damage=='late_drift':assert result['failure_phase']=='source_freshness'
    if not damage:
        assert result['sqlite_databases_recovered']==9 and result['inactive_current_settings_preservation_qualified'] is True
        assert modes==['capture_source','assess_configuration','verify_source','prepare','capture_candidate','restore_candidate','verify_source']


def test_source_pins_and_protocol_are_exact():
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'assess_rea_candidate_settings_owner.py').read_bytes()).hexdigest()
    assert ROOT['LIB_SHA']==OWNER['LIB_SHA']==hashlib.sha256((FOLDER/'finish_rea_review_owner.py').read_bytes()).hexdigest()
    assert ROOT['V3_SHA']==hashlib.sha256((FOLDER/'reconcile_rea_configuration.py').read_bytes()).hexdigest()
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'assess_rea_candidate_settings_owner.py').read_bytes())


@pytest.mark.parametrize('private_api_change',[False,True])
def test_assessment_checks_actual_capsule_archive_and_transform_without_private_output(monkeypatch,private_api_change):
    fixtures=runpy.run_path(str(Path(__file__).with_name('test_rea_configuration_reconciliation.py')))
    transform=fixtures['TRANSFORM'];core=fixtures['CORE'];parent=fixtures['OWNER']
    old=fixtures['fixture_config']();old['approvals']={'mode':'smart','timeout':900}
    old['api_server']={'private':'invented-private-old-DO-NOT-OUTPUT'}
    new=copy.deepcopy(old);new['approvals']['timeout']=600
    if private_api_change:new['api_server']['private']='invented-private-new-DO-NOT-OUTPUT'
    original=Path('/var/lib/enhanced-cognee-profiles/'+'a'*16+'/ec-main-operational-restore-retained')
    values={'config.yaml':yaml.safe_dump(new).encode(),'.env':b'INVENTED=current\n','auth.json':b'{"invented":"private-DO-NOT-OUTPUT"}'}
    capsule=json.dumps(dict(schema=1,files={k:base64.b64encode(v).decode() for k,v in values.items()})).encode()
    archive=fixtures['encoded_archive'](transform['transform'](old,original))
    helpers={'current_main_configuration.py':transform,'capture_main_operational_profile_v4.py':dict(MAX_ARCHIVE=600*1024**2,MAX_MANIFEST=8*1024**2,MAX_ENTRIES=12000),
        'inspect_launch_main_references.py':runpy.run_path(str(FOLDER/'inspect_launch_main_references.py'))}
    monkeypatch.setitem(core['inspect_source'].__globals__,'public',lambda name:helpers[name])
    c=dict(public=lambda name:helpers[name],capsule=core['capsule'],fingerprints=core['fingerprints'],inspect_source=core['inspect_source'])
    scope=OWNER['assess'].__globals__
    monkeypatch.setitem(scope,'_library',runpy.run_path(str(FOLDER/'finish_rea_review_owner.py')))
    monkeypatch.setitem(scope,'public_schema',lambda:{'approvals':{'timeout':{},'mode':{}},'api_server':{}})
    monkeypatch.setitem(scope,'platform_names',lambda:{'cli','api_server'})
    packet=dict(capsule_bytes=len(capsule),fingerprints=core['fingerprints'](values),original=str(original))
    result=OWNER['assess'](c,parent,packet,capsule+archive,SimpleNamespace(pw_dir=str(original.parent)))
    assert result['inactive_preparation_allowed'] is (not private_api_change)
    assert result['review']['critical_sections_equal'] is True and result['fleet_settings_accepted'] is False
    assert 'DO-NOT-OUTPUT' not in json.dumps(result)
    assert result['allowed_preserved_changes']==['approvals.timeout']


@pytest.mark.parametrize('complete',[False,True])
def test_repeating_finished_group_returns_immutable_result_without_reissuing(monkeypatch,tmp_path,capsys,complete):
    scope=ROOT['watch'].__globals__;artifact=tmp_path/'artifact';artifact.mkdir()
    evidence=tmp_path/'operator-evidence/main-rea-reviewed-invented';evidence.mkdir(parents=True)
    (artifact/'context.private.json').write_text(json.dumps(dict(source_sha256='a'*64,evidence=str(evidence))))
    result=dict(complete=complete,operator_job_stopped=True,operator_helper_sha256='a'*64,credentials_issued=2,programs_replayed=False)
    (evidence/'finish.summary.json').write_text(json.dumps(result))
    monkeypatch.setitem(scope,'BASE',tmp_path);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    assert ROOT['watch']({},lambda path,*a:path.read_bytes(),lambda *a:pytest.fail('immutable result rewritten'))==(0 if complete else 1)
    assert json.loads(capsys.readouterr().out)==result
