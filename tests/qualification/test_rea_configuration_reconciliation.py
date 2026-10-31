"""Require authenticated semantic equality before any new REA launch effects."""
import ast
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile
from types import SimpleNamespace

import pytest
import yaml

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'rea_candidate_owner_v3.py'))
ROOT=runpy.run_path(str(FOLDER/'reconcile_rea_configuration.py'))
CORE=runpy.run_path(str(FOLDER/'main_live_reconciliation_owner.py'))
TRANSFORM=runpy.run_path(str(FOLDER/'current_main_configuration.py'))


def fixture_config():
    return dict(model=dict(provider='zai',default='GLM-5.3-Flash',base_url='https://open.bigmodel.cn/api/coding/paas/v4',key_env='GLM_API_KEY'),
        memory={},gateway={'multiplex_profiles':True,'profile_routes':{}},mcp_servers={
            'filesystem':dict(command='npx',args=['@modelcontextprotocol/server-filesystem',TRANSFORM['SOURCE_WORKSPACE']]),
            'rea':dict(command='npx',args=['-y','rea-agents@6.7.0','mcp'],env={
                'GHIDRA_INSTALL_DIR':OWNER['PROGRAMS']['ghidra']['source'],'JAVA_HOME':OWNER['PROGRAMS']['java']['source'],
                'REA_GHIDRA_STARTUP_TIMEOUT_MS':'invented-preserved'})})


def encoded_archive(config, damage=None):
    raw=yaml.safe_dump(config).encode()
    manifest=dict(schema=2,format='hermes-main-operational-profile-sqlite-v2',entries=[dict(
        path='config.yaml',kind='file',mode=0o600,size=len(raw),sha256='0'*64 if damage=='digest' else hashlib.sha256(raw).hexdigest())])
    result=io.BytesIO()
    with tarfile.open(fileobj=result,mode='w',format=tarfile.GNU_FORMAT) as target:
        rows=[('profile-manifest.json',json.dumps(manifest).encode()),('config.yaml',raw)]
        if damage=='duplicate':rows.append(('config.yaml',raw))
        for name,data in rows:
            item=tarfile.TarInfo(name);item.mode=0o600;item.size=len(data)
            if damage=='symlink' and name=='config.yaml':item.type=tarfile.SYMTYPE;item.linkname='/invented/private';item.size=0
            target.addfile(item,io.BytesIO(data) if item.isfile() else None)
    return result.getvalue()


@pytest.mark.parametrize('change',[None,'formatting','model','mcp_servers','other_settings','scalar_type'])
def test_only_equal_parsed_settings_pass_with_no_private_diff_output(monkeypatch,change):
    original=Path('/var/lib/enhanced-cognee-profiles/'+'a'*16+'/ec-main-operational-restore-retained')
    previous=fixture_config();current=copy.deepcopy(previous)
    if change=='model':current['model']['default']='glm-5.3-flash'
    if change=='mcp_servers':current['mcp_servers']['rea']['env']['REA_GHIDRA_STARTUP_TIMEOUT_MS']='invented-new-timeout'
    if change=='other_settings':current['invented-private-setting-DO-NOT-OUTPUT']='invented-private-value-DO-NOT-OUTPUT'
    if change=='scalar_type':previous['invented_setting']=True;current['invented_setting']=1
    raw=yaml.safe_dump(current,sort_keys=change!='formatting').encode()
    if change=='formatting':raw=b'# invented new comment only\n'+raw
    files={'config.yaml':raw,'.env':b'INVENTED_SETTING=current\n','auth.json':b'{"invented_oauth":"current-DO-NOT-OUTPUT"}'}
    capsule=json.dumps(dict(schema=1,files={k:base64.b64encode(v).decode() for k,v in files.items()})).encode()
    helpers={'current_main_configuration.py':TRANSFORM,
        'capture_main_operational_profile_v4.py':dict(MAX_ARCHIVE=600*1024**2,MAX_ENTRIES=12000,MAX_MANIFEST=8*1024**2),
        'inspect_launch_main_references.py':runpy.run_path(str(FOLDER/'inspect_launch_main_references.py'))}
    source_scope=CORE['inspect_source'].__globals__;monkeypatch.setitem(source_scope,'public',lambda name:helpers[name])
    c=dict(public=lambda name:helpers[name],capsule=CORE['capsule'],fingerprints=CORE['fingerprints'],inspect_source=CORE['inspect_source'])
    packet=dict(capsule_bytes=len(capsule),fingerprints=CORE['fingerprints'](files),original=str(original))
    archive=encoded_archive(TRANSFORM['transform'](previous,original))
    result,body=OWNER['compare_configuration'](c,packet,capsule+archive,SimpleNamespace(pw_dir=str(original.parent)))
    assert result['complete'] is result['source_capsule_verified'] is True and body==b''
    assert result['configuration_semantically_equivalent'] is (change in {None,'formatting'})
    assert result['changed_sections']==([] if change in {None,'formatting'} else ['other_settings'] if change=='scalar_type' else [change])
    assert 'DO-NOT-OUTPUT' not in json.dumps(result) and set(result)=={'complete','source_capsule_verified','configuration_semantically_equivalent','changed_sections'}
    if change=='formatting':
        old=runpy.run_path(str(FOLDER/'continue_rea_main_programs.py'))
        cipher=b'age-encryption.org/v1\ninvented'
        value=dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},fingerprints=packet['fingerprints'],mcp_definitions=2,source_configuration_preserved=True,ciphertext_bytes=len(cipher))
        with pytest.raises(ValueError):old['validate_current'](value,cipher,{'config.yaml':hashlib.sha256(yaml.safe_dump(previous).encode()).hexdigest()})


@pytest.mark.parametrize('damage',['digest','duplicate','symlink'])
def test_untrusted_archive_configuration_is_refused_without_extraction(damage):
    c=dict(public=lambda name:dict(MAX_ARCHIVE=600*1024**2,MAX_ENTRIES=12000,MAX_MANIFEST=8*1024**2))
    with pytest.raises(ValueError):OWNER['archived_config'](c,encoded_archive(fixture_config(),damage))


@pytest.mark.parametrize('damage',[None,'wrong_checkpoint','inspection_effects','old_effects'])
def test_admission_requires_both_preserved_failures_and_latest_inspection(monkeypatch,damage):
    scope=ROOT['retained_admission'].__globals__;context={'evidence':'/invented/stopped-v2'}
    markers={name:name in {'model_binding','current_settings_capture'} for name in ROOT['PHASES'] if name!='configuration_equivalence'}
    report=dict(complete=True,source_revision=ROOT['BASE'].name,previous_evidence=context['evidence'],checkpoint_markers=markers,
        prior_failure_preserved=True,credentials_issued=0,readonly_model_binding=dict(inspection_complete=False,not_reexecuted=True))
    report.update({name:False for name in ('effectful_retry','profiles_changed','programs_staged','services_started','model_called','memory_api_called','fleet_launch_approved')})
    if damage=='wrong_checkpoint':markers['public_programs']=True
    if damage=='inspection_effects':report['services_started']=True
    def retained(*args):
        if damage=='old_effects':raise ValueError('invented-effects')
        return context,markers
    inspector=dict(FAILED_SHA='invented',PHASES=tuple(markers),retained=retained)
    monkeypatch.setitem(scope,'retained_v1_admission',lambda read:Path('/invented/stopped-v1'))
    monkeypatch.setitem(scope,'definitions',lambda path,*a:inspector if path.name=='inspect_rea_continuation_failure.py' else {})
    if damage:
        with pytest.raises(ValueError):ROOT['retained_admission'](lambda *a:json.dumps(report).encode())
    else:assert ROOT['retained_admission'](lambda *a:json.dumps(report).encode())==Path(context['evidence'])


@pytest.mark.parametrize('damage',[None,'semantic_change','early_drift','late_drift'])
def test_grouped_reconciliation_checks_equivalence_before_staging_or_issuance(monkeypatch,tmp_path,damage):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/rea-main-programs-invented';evidence.mkdir(parents=True)
    live=base/'live';live_evidence=base/'operator-evidence/main-live-invented'
    owner=b'invented-public-owner';(artifact/'rea_candidate_owner_v3.py').write_bytes(owner)
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='b'*32,restore_id='c'*32)
    entry=dict(user='ecbot_'+'d'*16,home='/var/lib/enhanced-cognee-profiles/'+'d'*16)
    destination=entry['home']+'/ec-main-operational-restore-invented';policy=Path('/invented/policy')
    previous={'config.yaml':'1'*64,'.env':'2'*64,'auth.json':'3'*64};current={'config.yaml':'4'*64,'.env':'5'*64,'auth.json':'6'*64}
    files={artifact/'context.private.json':json.dumps(context).encode(),policy:b'disabled',
        live/'context.private.json':json.dumps({'evidence':str(live_evidence)}).encode(),
        live_evidence/'source-configuration.private.json':json.dumps({'fingerprints':previous}).encode(),
        Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    stages=[];issued=[];generations=[];modes=[];verifications=[]
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    cipher=b'age-encryption.org/v1\ninvented';pin=dict(size=1,sha256=hashlib.sha256(b'x').hexdigest())
    def owner_call(account,source,packet,**kwargs):
        mode=packet['mode'];modes.append(mode)
        if mode=='capture_source':
            assert account.pw_uid==1000
            return dict(complete=True,receipt={'files':3,'plaintext_archive_written':False},fingerprints=current,mcp_definitions=6,source_configuration_preserved=True,ciphertext_bytes=len(cipher)),cipher
        if mode=='compare_configuration':
            assert not issued and not stages and not generations and account.pw_uid==3001
            assert packet['fingerprints']==current and kwargs['body']==b'invented-capsuleinvented-original-archive'
            return dict(complete=True,source_capsule_verified=True,configuration_semantically_equivalent=damage!='semantic_change',changed_sections=['mcp_servers'] if damage=='semantic_change' else []),b''
        if mode=='verify_source':
            assert packet['fingerprints']==current;verifications.append(mode)
            if damage=='early_drift' or (damage=='late_drift' and len(verifications)==2):raise ValueError('invented-drift')
            return dict(complete=True,current_source_settings_preserved=True),b''
        if mode=='program_archive':return dict(complete=True,program=packet['program'],archive_bytes=1,archive_sha256=pin['sha256']),b'x'
        if mode=='prepare':
            assert kwargs['body']==b'invented-capsuleinvented-original-archive' and packet['fingerprints']==current
            return dict(complete=True,remaining_reference_count=0,rea_definition_preserved=True,settings_and_oauth_preserved=True,scoped_status_authenticated=True,destination=destination,mcp_definitions=6,current_auth_snapshot_preserved=True,current_source_settings_refreshed=True),b''
        if mode=='capture_candidate':return dict(complete=True,receipt={'sqlite_databases':9}),cipher
        assert mode=='restore_candidate' and packet['fingerprints']==current
        return dict(mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,oauth_and_environment_preserved=True,current_auth_snapshot_preserved=True,receipt={'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':9}),b''
    def fresh_bundle(entry):issued.append(entry);return {'token':'invented-token'}
    def generation(kind,*args):generations.append(kind);return Path('/invented/'+kind+'.age'),kind.encode()
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:(entry,{}),fresh_bundle=fresh_bundle,
        PINS={'continue_launch_main_operational.py':'invented'},definitions=lambda *args:{'validate_owner_result':lambda *args:None})
    common=dict(legacy=lambda:driver,owner=owner_call,packet=lambda account,mode,**kw:dict(mode=mode,**kw),runtime_model=lambda *a:'invented-qualified-key',PACKAGE=Path('/invented/package'),generation=generation,
        decrypt=lambda cipher,**kw:b'invented-capsule' if kw.get('configuration') else b'invented-restored-archive',KINDS={'ValueError'})
    owned=dict(PROGRAMS={'ghidra':pin,'java':pin});snapshot=dict(MAX_ARCHIVE=1024,restore=lambda body,name,path:stages.append(path))
    for name,value in dict(BASE=base,ARTIFACT=artifact,LIVE=live,PROGRAM_ROOT=tmp_path/'programs',__file__=str(artifact/'reconcile_rea_configuration.py'),OWNER_SHA=hashlib.sha256(owner).hexdigest(),
        common=lambda:common,support=lambda c:(read,write),definitions=lambda path,*a:owned if path.name=='rea_candidate_owner_v3.py' else snapshot,
        retained_admission=lambda read:Path('/invented/stopped-v2'),retained_live=lambda read:{'new_inactive_candidate':destination},authenticated_profile_archive=lambda *a:b'invented-original-archive',program_probe=lambda *a:dict(complete=True)).items():monkeypatch.setitem(scope,name,value)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','e'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_uid=1000 if name=='vincentspereira' else 3001,pw_gid=1000 if name=='vincentspereira' else 3001,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert ROOT['worker']()==(1 if damage else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['complete'] is (damage is None) and result['previous_configuration_bytes_equal'] is False
    assert result['all_admission_policies_preserved_disabled'] is result['prior_failure_preserved'] is True
    assert result['source_profiles_changed'] is result['previous_candidates_changed'] is result['candidate_promoted'] is result['fleet_launch_approved'] is False
    if damage in {'semantic_change','early_drift'}:assert not issued and not stages and result['credentials_issued']==0
    else:assert len(issued)==1 and len(stages)==4 and result['credentials_issued']==2 and generations==['configuration','configured']
    if damage=='semantic_change':
        assert not generations and result['category']=='rea_configuration_changed_requires_review_no_effectful_retry'
        assert result['failure_phase']=='configuration_equivalence' and modes==['capture_source','compare_configuration']
    if damage=='late_drift':assert result['failure_phase']=='source_freshness'
    if not damage:assert result['configuration_equivalence_qualified'] is True and result['sqlite_databases_recovered']==9


def test_exact_pins_preserved_failures_and_controller_dispatch(monkeypatch):
    controller=runpy.run_path(str(FOLDER/'launch_control.py'))
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'rea_candidate_owner_v3.py').read_bytes()).hexdigest()
    assert ROOT['V2_INSPECTION_SHA']==hashlib.sha256((FOLDER/'inspect_rea_continuation_failure.py').read_bytes()).hexdigest()
    assert hashlib.sha256((FOLDER/'continue_rea_main_programs.py').read_bytes()).hexdigest()=='bce3399d071eb69f9d1a4a95dd52a6aab255d67f6dd96a1a71d739fcf85e3a41'
    assert controller['REA_CONFIGURATION_RECONCILIATION_SHA']==hashlib.sha256((FOLDER/'reconcile_rea_configuration.py').read_bytes()).hexdigest()
    runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))['owner_program']((FOLDER/'rea_candidate_owner_v3.py').read_bytes())
    events=[]
    def definitions(path,digest):
        assert path==FOLDER/'reconcile_rea_configuration.py' and digest==controller['REA_CONFIGURATION_RECONCILIATION_SHA']
        events.append('verified_dispatch');return {'launch':lambda:0}
    controller.update(__name__='__main__',definitions=definitions)
    monkeypatch.setattr(controller['sys'],'argv',['launch_control.py','reconcile-rea-capture'])
    block=ast.parse((FOLDER/'launch_control.py').read_text()).body[-1]
    with pytest.raises(SystemExit) as outcome:exec(compile(ast.Module(body=[block],type_ignores=[]),'<reconciliation-dispatch>','exec'),controller)
    assert outcome.value.code==0 and events==['verified_dispatch']
