"""Telegram home data can be copied without authorizing any platform execution."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'assess_telegram_candidate_owner.py'))
ROOT=runpy.run_path(str(FOLDER/'prepare_main_with_telegram.py'))
OLD=runpy.run_path(str(FOLDER/'assess_rea_candidate_settings_owner.py'))
FIELDS={'platform','chat_id','name','thread_id','user_id','scope_id'}


def telegram():
    return dict(enabled=True,home_channel=dict(platform='telegram',chat_id='invented-id-DO-NOT-OUTPUT',name='invented-name-DO-NOT-OUTPUT',user_id='invented-user-DO-NOT-OUTPUT'))


@pytest.fixture
def policy(monkeypatch):
    scope=OWNER['preservation_policy'].__globals__
    monkeypatch.setitem(scope,'_base',{'_original_policy':OLD['preservation_policy']})
    monkeypatch.setitem(scope,'home_fields',lambda:FIELDS)
    return OWNER['preservation_policy']


@pytest.mark.parametrize('damage',[None,'token','custom_option','wrong_platform','empty_id','unknown_home_key','invalid_enable','existing_telegram','other_platform','approval_mode','private_change'])
def test_only_new_bounded_home_record_is_admitted_for_inactive_copy(policy,damage):
    old={'approvals':{'mode':'smart','timeout':900},'platforms':{'whatsapp':{'enabled':True}}}
    current=copy.deepcopy(old);current['approvals']['timeout']=600;current['platforms']['telegram']=telegram()
    block=current['platforms']['telegram']
    if damage=='token':block['token']='invented-secret-DO-NOT-OUTPUT'
    if damage=='custom_option':block['extra']={'listener':'invented'}
    if damage=='wrong_platform':block['home_channel']['platform']='discord'
    if damage=='empty_id':block['home_channel']['chat_id']=''
    if damage=='unknown_home_key':block['home_channel']['private_key']='invented-secret-DO-NOT-OUTPUT'
    if damage=='invalid_enable':block['enabled']='true'
    if damage=='existing_telegram':old['platforms']['telegram']=dict(enabled=False,home_channel=copy.deepcopy(block['home_channel']))
    if damage=='other_platform':current['platforms']['whatsapp']['enabled']=False
    if damage=='approval_mode':current['approvals']['mode']='off'
    if damage=='private_change':current['invented-private-field']='invented-secret-DO-NOT-OUTPUT'
    before=copy.deepcopy((old,current));result=policy(old,current,{'cli','whatsapp','telegram'})
    assert result['inactive_preparation_allowed'] is (damage is None)
    assert result['fleet_settings_accepted'] is False and (old,current)==before
    assert 'DO-NOT-OUTPUT' not in json.dumps(result)
    if not damage:assert result['allowed_preserved_changes']==['approvals.timeout','platforms.telegram.inactive_copy']


@pytest.mark.parametrize('old_platforms',[None,{}])
def test_absent_platform_mapping_is_handled_without_mutating_source(policy,old_platforms):
    old={'approvals':{'timeout':900}}
    if old_platforms is not None:old['platforms']=old_platforms
    current=copy.deepcopy(old);current['approvals']['timeout']=600;current['platforms']={'telegram':telegram()}
    assert policy(old,current,{'telegram'})['inactive_preparation_allowed'] is True


@pytest.mark.parametrize('damage',[None,'issued','later_phase','other_change','running'])
def test_only_the_specific_zero_effect_stopped_refusal_can_continue(monkeypatch,tmp_path,damage):
    scope=ROOT['retained_refusal'].__globals__;base=tmp_path/'base';previous=base/'previous';refusal=base/'operator-evidence/main-rea-reviewed-invented';refusal.mkdir(parents=True)
    value=dict(source_revision=base.name,operator_helper_sha256=ROOT['PREVIOUS_SHA'],complete=False,operator_job_stopped=True,checkpoint='settings_assessment',failure_phase='settings_assessment',
        category='unreviewed_setting_change_requires_review_no_credentials_issued',credentials_issued=0,encrypted_generations_created=0,all_admission_policies_preserved_disabled=True,
        settings_assessment=dict(complete=True,inactive_preparation_allowed=False,allowed_preserved_changes=['approvals.timeout'],review=dict(critical_sections_equal=True,source_capsule_verified=True,redacted_changed_fields=0,additional_public_changes=0,
            changed_public_fields=[dict(path=['approvals','timeout'],previous=dict(kind='integer',value=900),current=dict(kind='integer',value=600)),dict(path=['platforms','telegram'],previous=dict(kind='absent'),current=dict(kind='mapping'))])))
    value.update({key:False for key in ('source_profiles_changed','previous_candidates_changed','candidate_promoted','canonical_memory_edits','chat_model_called','programs_replayed','fleet_settings_accepted','fleet_launch_approved')})
    if damage=='issued':value['credentials_issued']=2
    if damage=='later_phase':(refusal/'new_candidate.started.json').write_text('{}')
    if damage=='other_change':value['settings_assessment']['review']['changed_public_fields'][1]['path']=['api_server']
    files={previous/'context.private.json':json.dumps(dict(source_sha256=ROOT['PREVIOUS_SHA'],evidence=str(refusal))).encode(),refusal/'finish.summary.json':json.dumps(value).encode()}
    for name,var in dict(BASE=base,PREVIOUS=previous,REFUSAL=refusal).items():monkeypatch.setitem(scope,name,var)
    old=dict(metadata=lambda unit:{},stopped=lambda state:damage!='running')
    if damage:
        with pytest.raises(ValueError):ROOT['retained_refusal'](old,lambda path,*a:files[path])
    else:assert ROOT['retained_refusal'](old,lambda path,*a:files[path])==value


@pytest.mark.parametrize('accepted',[False,True])
def test_group_remains_inactive_and_reuses_dependency_pass(monkeypatch,tmp_path,accepted):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-rea-reviewed-invented';evidence.mkdir(parents=True);passed=base/'pass.json';refusal=base/'refusal';policy_path=Path('/invented/policy')
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='b'*32,restore_id='c'*32)
    files={artifact/'context.private.json':json.dumps(context).encode(),passed:b'invented-pass',refusal/'finish.summary.json':b'invented-refusal',policy_path:b'disabled',Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    entry=dict(user='ecbot_'+'d'*16,home='/var/lib/enhanced-cognee-profiles/'+'d'*16);destination=entry['home']+'/ec-main-operational-restore-invented'
    modes=[];issued=[];generations=[];fingerprints={'config.yaml':'1'*64,'.env':'2'*64,'auth.json':'3'*64};cipher=b'age-encryption.org/v1\ninvented'
    def owner(account,source,packet,**kw):
        mode=packet['mode'];modes.append(mode)
        if mode=='capture_source':return dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},fingerprints=fingerprints,mcp_definitions=6,source_configuration_preserved=True,ciphertext_bytes=len(cipher)),cipher
        if mode=='assess_configuration':
            assert not issued and not generations
            return dict(complete=True,review={'critical_sections_equal':True},inactive_preparation_allowed=accepted,allowed_preserved_changes=['approvals.timeout','platforms.telegram.inactive_copy'],fleet_settings_accepted=False),b''
        if mode=='verify_source':return dict(complete=True,current_source_settings_preserved=True),b''
        if mode=='prepare':
            assert kw['body']==b'invented-capsuleinvented-archive'
            return dict(complete=True,remaining_reference_count=0,rea_definition_preserved=True,settings_and_oauth_preserved=True,scoped_status_authenticated=True,current_auth_snapshot_preserved=True,current_source_settings_refreshed=True,destination=destination,mcp_definitions=6),b''
        if mode=='capture_candidate':return dict(complete=True,receipt={'sqlite_databases':9}),cipher
        assert mode=='restore_candidate'
        return dict(mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,oauth_and_environment_preserved=True,current_auth_snapshot_preserved=True,receipt={'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':9}),b''
    def fresh(entry):issued.append(entry);return {'token':'invented-token'}
    def generation(kind,*args):generations.append(kind);return Path('/invented/'+kind+'.age'),kind.encode()
    driver=dict(policies=lambda read:{policy_path:b'disabled'},fixed_entry=lambda read:(entry,{}),fresh_bundle=fresh,PINS={'continue_launch_main_operational.py':'invented'},definitions=lambda *a:{'validate_owner_result':lambda *a:None})
    common=dict(legacy=lambda:driver,owner=owner,packet=lambda account,mode,**kw:dict(mode=mode,**kw),runtime_model=lambda *a:'invented-qualified-key',PACKAGE=Path('/invented/package'),generation=generation,decrypt=lambda data,**kw:b'invented-capsule' if kw.get('configuration') else b'invented-restored-archive',KINDS={'ValueError'})
    old=dict(OWNER_SHA='invented',PROGRAM_ROOT=Path('/opt/hermes-runtime/programs'),validate_current=lambda *a:None,retained_live=lambda read:{'new_inactive_candidate':destination},authenticated_profile_archive=lambda *a:b'invented-archive')
    parent=dict(_verified_source_bytes=b'invented-parent',PROGRAMS={'java':{'sha256':'e'*64}})
    def definitions(path,*args):
        if path.name=='rea_candidate_owner_v3.py':return parent
        if path.name=='assess_telegram_candidate_owner.py':return {'_verified_source_bytes':b'invented-assessor'}
        assert path.name=='review_rea_settings_and_programs.py';return {'validate_review':lambda *a:None}
    for name,var in dict(BASE=base,ARTIFACT=artifact,PASSED=passed,REFUSAL=refusal,__file__=str(artifact/'prepare_main_with_telegram.py'),helpers=lambda:(old,common,read,write),definitions=definitions,retained_pass=lambda *a:{},retained_refusal=lambda *a:{}).items():monkeypatch.setitem(scope,name,var)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','f'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert ROOT['worker']()==(0 if accepted else 1)
    result=json.loads(files[evidence/'summary.json'])
    assert result['telegram_activation_qualified'] is result['fleet_settings_accepted'] is result['fleet_launch_approved'] is result['candidate_promoted'] is result['source_profiles_changed'] is False
    assert result['external_platform_connections']==result['external_platform_sends']==result['platform_adapters_started']==0
    assert result['programs_replayed'] is False and files[refusal/'finish.summary.json']==b'invented-refusal'
    if accepted:
        assert result['telegram_configuration_preserved_inactive_only'] is True and result['configured_candidate_restore_qualified'] is True
        assert len(issued)==1 and generations==['configuration','configured'] and result['credentials_issued']==2
        assert modes==['capture_source','assess_configuration','verify_source','prepare','capture_candidate','restore_candidate','verify_source']
    else:assert not issued and not generations and result['credentials_issued']==0


def test_frozen_source_pins_and_owner_frame_preserve_previous_attempt():
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'assess_telegram_candidate_owner.py').read_bytes()).hexdigest()
    assert ROOT['PREVIOUS_SHA']==hashlib.sha256((FOLDER/'prepare_main_after_rea.py').read_bytes()).hexdigest()
    assert OWNER['PARENT_SHA']==hashlib.sha256((FOLDER/'assess_rea_candidate_settings_owner.py').read_bytes()).hexdigest()
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'assess_telegram_candidate_owner.py').read_bytes())
