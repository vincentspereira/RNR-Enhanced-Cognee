"""Current settings refresh is explicit, recoverable and never weakens guards.

Service, restore and issuer operations are invented doubles. Actual installed
settings preparation and protected host qualification are separate evidence.
"""
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest
import yaml

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'rea_candidate_owner_v2.py'))
ROOT=runpy.run_path(str(FOLDER/'continue_rea_main_programs.py'))
CORE=runpy.run_path(str(FOLDER/'main_live_reconciliation_owner.py'))
TRANSFORM=runpy.run_path(str(FOLDER/'current_main_configuration.py'))


@pytest.mark.parametrize('damage',[None,'identity','config','old_failed_effects','inspection_effects','wrong_previous','running'])
def test_only_verified_source_drift_can_admit_the_explicit_continuation(monkeypatch,damage):
    previous=Path('/invented/previous');base=Path('/invented/base')
    report=dict(complete=True,source_revision=base.name,previous_evidence=str(previous),credentials_issued=0,
        prior_failure_preserved=True,effectful_retry=False,profiles_changed=False,programs_staged=False,
        services_started=False,fleet_launch_approved=False,
        preflight=dict(complete=True,core_loaded=True,identity_verified=True,source_files_read=True,preflight_passed=False,
            source_fingerprints_match=False,source_files_equal={'.env':False,'auth.json':False,'config.yaml':True},
            phase='complete',profiles_changed=False,credentials_issued=0,memory_api_called=False,model_called=False,
            identity_predicates={str(i):True for i in range(8)}))
    if damage=='identity':report['preflight']['identity_predicates']['0']=False
    if damage=='config':report['preflight']['source_files_equal']['config.yaml']=False
    if damage=='inspection_effects':report['effectful_retry']=True
    if damage=='wrong_previous':report['previous_evidence']='/invented/unrelated'
    def retained(read):
        if damage=='old_failed_effects':raise ValueError('invented-old-effects')
        return previous
    inspected=dict(retained=retained,FAILED_SHA='invented-old-sha')
    original=dict(metadata=lambda unit:{},UNIT='invented-unit',stopped=lambda state:damage!='running')
    scope=ROOT['retained_admission'].__globals__;monkeypatch.setitem(scope,'BASE',base)
    monkeypatch.setitem(scope,'definitions',lambda path,*args:inspected if path.name=='inspect_rea_program_failure.py' else original)
    if damage:
        with pytest.raises(ValueError):ROOT['retained_admission'](lambda *args:json.dumps(report).encode())
    else:assert ROOT['retained_admission'](lambda *args:json.dumps(report).encode())==previous


@pytest.mark.parametrize('damage',[None,'config_changed','bad_hash','wrong_keys','plaintext','missing_preservation'])
def test_fresh_capsule_admission_preserves_config_match_and_integrity(damage):
    body=b'age-encryption.org/v1\ninvented-encrypted-current-settings'
    value=dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},
        fingerprints={'config.yaml':'a'*64,'.env':'b'*64,'auth.json':'c'*64},mcp_definitions=6,
        source_configuration_preserved=True,ciphertext_bytes=len(body))
    if damage=='config_changed':value['fingerprints']['config.yaml']='d'*64
    if damage=='bad_hash':value['fingerprints']['auth.json']='invalid'
    if damage=='wrong_keys':value['fingerprints']['unreviewed']='e'*64
    if damage=='plaintext':body=b'invented-unencrypted';value['ciphertext_bytes']=len(body)
    if damage=='missing_preservation':value['source_configuration_preserved']=False
    if damage:
        with pytest.raises(ValueError):ROOT['validate_current'](value,body,{'config.yaml':'a'*64})
    else:ROOT['validate_current'](value,body,{'config.yaml':'a'*64})


@pytest.mark.parametrize('damaged_fingerprint',[False,True])
def test_new_copy_uses_current_environment_and_oauth_not_old_scoped_token(damaged_fingerprint):
    home=Path('/var/lib/enhanced-cognee-profiles/'+'a'*16)
    profile=home/'ec-main-operational-restore-newcandidate';original=home/'ec-main-operational-restore-oldcandidate'
    config=dict(memory={},gateway={'multiplex_profiles':True,'profile_routes':{}},mcp_servers={
        'filesystem':dict(command='npx',args=['@modelcontextprotocol/server-filesystem',TRANSFORM['SOURCE_WORKSPACE']]),
        'rea':dict(command='npx',args=['-y','rea-agents@6.7.0','mcp'],env={
            'GHIDRA_INSTALL_DIR':OWNER['PROGRAMS']['ghidra']['source'],'JAVA_HOME':OWNER['PROGRAMS']['java']['source'],
            'REA_GHIDRA_STARTUP_TIMEOUT_MS':'invented-preserved'})})
    current={'config.yaml':yaml.safe_dump(config).encode(),'.env':b'INVENTED_SETTING=current\n',
        'auth.json':b'{"invented_account":"current"}'};unchanged=copy.deepcopy(current)
    capsule=json.dumps(dict(schema=1,files={name:base64.b64encode(raw).decode() for name,raw in current.items()})).encode()
    saved={'config.yaml':b'invented-old-config','.env':b'ENHANCED_COGNEE_ACCESS_TOKEN=invented-old-token\n',
        'auth.json':b'{"invented_account":"old"}'};before=dict(saved);effects=[]
    def prepare_files(values,bundle,key,destination,entry):
        assert values==current and key=='invented-qualified-model-key'
        assert b'invented-old-token' not in values['.env']
        cfg=TRANSFORM['transform'](yaml.safe_load(values['config.yaml']),destination)
        return yaml.safe_dump(cfg).encode(),values['.env']+b'ENHANCED_COGNEE_ACCESS_TOKEN=invented-new-token\n',len(cfg['mcp_servers'])
    def public(name):
        if name=='current_main_configuration.py':return TRANSFORM
        if name=='main_memory_profile_recovery.py':
            def restore(core,raw):effects.append('restore');assert raw==b'invented-archive';return str(profile),{'invented':'receipt'}
            return dict(restore=restore)
        if name=='capture_main_operational_profile_v4.py':return {}
        assert name=='inspect_launch_main_references.py'
        return runpy.run_path(str(FOLDER/name))
    def publish(path,name,raw,ident):assert path==profile;effects.append(name);saved[name]=raw
    def forbidden(*args):pytest.fail('old candidate environment passed to first-publication preparation')
    c=dict(public=public,capsule=CORE['capsule'],fingerprints=CORE['fingerprints'],inspect_source=lambda values:None,
        files=lambda path:dict(saved),prepare_files=prepare_files,publish=publish,
        bind=lambda entry:dict(qualify_access=lambda bundle:effects.append('scope_status'),prepare_environment=forbidden))
    programs={name:'/opt/hermes-runtime/programs/rea-'+name+'-'+pin['sha256'][:16] for name,pin in OWNER['PROGRAMS'].items()}
    fingerprints=CORE['fingerprints'](current)
    if damaged_fingerprint:fingerprints['auth.json']='0'*64
    packet=dict(original=str(original),capsule_bytes=len(capsule),fingerprints=fingerprints,programs=programs,
        entry={},bundle={'token':'invented-new-token'},model_key='invented-qualified-model-key',id='b'*32)
    if damaged_fingerprint:
        with pytest.raises(ValueError):OWNER['prepare'](c,packet,capsule+b'invented-archive',SimpleNamespace(pw_dir=str(home)))
        assert not effects and saved==before
    else:
        result,body=OWNER['prepare'](c,packet,capsule+b'invented-archive',SimpleNamespace(pw_dir=str(home)))
        assert result['complete'] and result['current_auth_snapshot_preserved'] and result['remaining_reference_count']==0
        assert not body and current==unchanged and saved['auth.json']==current['auth.json']
        assert saved['.env'].startswith(current['.env']) and b'invented-old-token' not in saved['.env']
        assert effects==['restore','scope_status','config.yaml','.env','auth.json','scope_status']
        updated=yaml.safe_load(saved['config.yaml'])
        assert updated['mcp_servers']['rea']['args']==config['mcp_servers']['rea']['args']
        assert updated['mcp_servers']['rea']['env']['REA_GHIDRA_STARTUP_TIMEOUT_MS']=='invented-preserved'


def test_future_source_drift_is_labeled_as_source_not_identity(monkeypatch):
    scope=OWNER['child'].__globals__
    packet=dict(mode='verify_source',uid=1000,gid=1000,fingerprints={})
    monkeypatch.setattr(OWNER['sys'],'stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(packet).encode()+b'\n')))
    c=dict(guard=lambda packet:SimpleNamespace(pw_dir='/invented/source'),
        public=lambda name:dict(network_guard=lambda:{'forbidden':0}),files=lambda path:{'invented':'private'},
        fingerprints=lambda values:{'changed':'do-not-print'})
    monkeypatch.setitem(scope,'core',lambda:c)
    with pytest.raises(ValueError):OWNER['child']()
    assert scope['PHASE']=='source_configuration'


def test_exact_public_dependencies_protocol_and_prior_versions_are_preserved():
    controller=runpy.run_path(str(FOLDER/'launch_control.py'))
    assert controller['REA_CONTINUATION_SHA']==hashlib.sha256((FOLDER/'continue_rea_main_programs.py').read_bytes()).hexdigest()
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'rea_candidate_owner_v2.py').read_bytes()).hexdigest()
    assert ROOT['INSPECTION_SHA']==hashlib.sha256((FOLDER/'inspect_rea_program_failure.py').read_bytes()).hexdigest()
    assert hashlib.sha256((FOLDER/'stage_rea_main_programs.py').read_bytes()).hexdigest()=='fa213db654f35502ba5bd32b07ae64dea59a6ecb36cd88188eb8805b94d31534'
    assert hashlib.sha256((FOLDER/'rea_candidate_owner.py').read_bytes()).hexdigest()=='25ed007609af9d86b6f0386e340ef7265ef325e3f8d295185bfd809f7468128f'
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'rea_candidate_owner_v2.py').read_bytes())


def test_controller_dispatches_only_the_explicit_pinned_continuation(monkeypatch):
    import ast
    controller=runpy.run_path(str(FOLDER/'launch_control.py'));events=[]
    def definitions(path,digest):
        assert path==FOLDER/'continue_rea_main_programs.py' and digest==controller['REA_CONTINUATION_SHA']
        events.append('verified_dispatch');return {'launch':lambda:0}
    controller.update(__name__='__main__',definitions=definitions)
    monkeypatch.setattr(controller['sys'],'argv',['launch_control.py','continue-rea-programs'])
    block=ast.parse((FOLDER/'launch_control.py').read_text()).body[-1]
    with pytest.raises(SystemExit) as result:exec(compile(ast.Module(body=[block],type_ignores=[]),'<controller-dispatch>','exec'),controller)
    assert result.value.code==0 and events==['verified_dispatch']


@pytest.mark.parametrize('damage',[None,'model_binding','config_changed','early_drift','late_drift'])
def test_grouped_continuation_binds_fresh_settings_and_stops_on_drift(monkeypatch,tmp_path,damage):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/rea-main-programs-invented';evidence.mkdir(parents=True)
    live=base/'live';live_evidence=base/'operator-evidence/main-live-invented'
    owner=b'invented-public-owner';(artifact/'rea_candidate_owner_v2.py').write_bytes(owner)
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='b'*32,restore_id='c'*32)
    entry=dict(user='ecbot_'+'d'*16,home='/var/lib/enhanced-cognee-profiles/'+'d'*16)
    destination=entry['home']+'/ec-main-operational-restore-invented'
    previous={'config.yaml':'1'*64,'.env':'2'*64,'auth.json':'3'*64}
    current={'config.yaml':('4' if damage=='config_changed' else '1')*64,'.env':'5'*64,'auth.json':'6'*64}
    policy=Path('/invented/policy');files={artifact/'context.private.json':json.dumps(context).encode(),policy:b'disabled',
        live/'context.private.json':json.dumps({'evidence':str(live_evidence)}).encode(),
        live_evidence/'source-configuration.private.json':json.dumps({'fingerprints':previous}).encode(),
        Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    modes=[];stages=[];generations=[];issued=[];verifications=[]
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    pin=dict(size=1,sha256=hashlib.sha256(b'x').hexdigest())
    owned=dict(PROGRAMS={'ghidra':pin,'java':pin})
    snapshot=dict(MAX_ARCHIVE=1024,restore=lambda body,name,path:stages.append((name,path)))
    encrypted=b'age-encryption.org/v1\ninvented-encrypted'
    def owner_call(account,source,packet,**kwargs):
        mode=packet['mode'];modes.append(mode)
        if mode=='capture_source':
            assert account.pw_uid==1000 and set(packet)=={'mode','recipient'}
            return dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},fingerprints=current,
                mcp_definitions=6,source_configuration_preserved=True,ciphertext_bytes=len(encrypted)),encrypted
        if mode=='verify_source':
            assert account.pw_uid==1000 and packet['fingerprints']==current and current!=previous
            verifications.append(mode)
            if damage=='early_drift' or (damage=='late_drift' and len(verifications)==2):raise ValueError('invented-drift')
            return dict(complete=True,current_source_settings_preserved=True),b''
        if mode=='program_archive':
            assert account.pw_uid==1000
            return dict(complete=True,program=packet['program'],archive_bytes=1,archive_sha256=pin['sha256']),b'x'
        assert account.pw_uid==3001
        if mode=='prepare':
            assert packet['fingerprints']==current and packet['capsule_bytes']==len(b'invented-capsule')
            assert kwargs['body']==b'invented-capsuleinvented-original-archive' and packet['model_key']=='invented-qualified-key'
            return dict(complete=True,remaining_reference_count=0,rea_definition_preserved=True,
                settings_and_oauth_preserved=True,scoped_status_authenticated=True,destination=destination,mcp_definitions=6,
                current_auth_snapshot_preserved=True,current_source_settings_refreshed=True),b''
        if mode=='capture_candidate':return dict(complete=True,receipt={'sqlite_databases':9}),encrypted
        assert mode=='restore_candidate' and packet['fingerprints']==current and packet['id']=='c'*32
        return dict(mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,oauth_and_environment_preserved=True,
            current_auth_snapshot_preserved=True,receipt={'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':9}),b''
    def runtime_model(*args):
        if damage=='model_binding':raise ValueError('invented-model-binding-changed')
        return 'invented-qualified-key'
    def fresh_bundle(entry):issued.append(entry);return {'token':'invented-ordinary-token'}
    def generation(kind,*args):
        generations.append(kind);return Path('/invented/'+kind+'.age'),kind.encode()
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:(entry,{}),fresh_bundle=fresh_bundle,
        PINS={'continue_launch_main_operational.py':'invented'},definitions=lambda *args:{'validate_owner_result':lambda *args:None})
    common=dict(legacy=lambda:driver,owner=owner_call,packet=lambda account,mode,**kw:dict(mode=mode,**kw),runtime_model=runtime_model,
        PACKAGE=Path('/invented/package'),generation=generation,
        decrypt=lambda cipher,**kw:b'invented-capsule' if kw.get('configuration') else b'invented-private-archive',KINDS={'ValueError'})
    for name,value in dict(BASE=base,ARTIFACT=artifact,LIVE=live,PROGRAM_ROOT=tmp_path/'programs',
        __file__=str(artifact/'continue_rea_main_programs.py'),OWNER_SHA=hashlib.sha256(owner).hexdigest(),common=lambda:common,
        support=lambda c:(read,write),definitions=lambda path,*args:owned if path.name=='rea_candidate_owner_v2.py' else snapshot,
        retained_admission=lambda read:Path('/invented/retained-failure'),retained_live=lambda read:{'new_inactive_candidate':destination},
        authenticated_profile_archive=lambda *args:b'invented-original-archive',program_probe=lambda *args:dict(complete=True)).items():
        monkeypatch.setitem(scope,name,value)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','e'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_uid=1000 if name=='vincentspereira' else 3001,
        pw_gid=1000 if name=='vincentspereira' else 3001,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert ROOT['worker']()==(1 if damage else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['complete'] is (damage is None)
    assert result['source_profiles_changed'] is result['previous_candidates_changed'] is result['candidate_promoted'] is False
    assert result['fleet_launch_approved'] is result['production_dispatch_qualified'] is result['production_renewal_timer_enabled'] is False
    assert result['all_admission_policies_preserved_disabled'] is result['prior_failure_preserved'] is True
    assert result['prior_live_snapshot_reused'] is True and result['source_operational_state_refreshed'] is False
    if damage in {'model_binding','config_changed','early_drift'}:
        assert not stages and not issued and result['credentials_issued']==0
    else:
        assert len(stages)==4 and len(issued)==1 and result['credentials_issued']==2
        assert generations==['configuration','configured'] and result['encrypted_generations_created']==2
        assert modes==['capture_source','verify_source','program_archive','program_archive','prepare','capture_candidate','restore_candidate','verify_source']
    if not damage:assert result['sqlite_databases_recovered']==9 and result['source_current_at_completion'] is True
