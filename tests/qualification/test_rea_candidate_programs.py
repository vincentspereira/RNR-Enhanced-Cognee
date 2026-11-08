"""REA candidate changes and protected job gates; unit operations are doubles."""
import copy
import hashlib
import hmac
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
OWNER=runpy.run_path(str(FOLDER/'rea_candidate_owner.py'))
ROOT=runpy.run_path(str(FOLDER/'stage_rea_main_programs.py'))
TRANSFORM=runpy.run_path(str(FOLDER/'current_main_configuration.py'))


def configuration():
    original=Path('/var/lib/enhanced-cognee-profiles/'+'a'*16+'/ec-main-operational-restore-original')
    value=dict(memory={'provider':'enhanced_cognee','invented_preference':'preserved'},
        gateway={'multiplex_profiles':True,'profile_routes':{}},model={'invented_route':'unchanged'},
        mcp_servers={'filesystem':dict(command='npx',args=['@modelcontextprotocol/server-filesystem',str(original/'workspace')]),
            'rea':dict(command='npx',args=['invented-existing-rea-package','mcp','stdio'],env={
                'GHIDRA_INSTALL_DIR':OWNER['PROGRAMS']['ghidra']['source'],
                'JAVA_HOME':OWNER['PROGRAMS']['java']['source'],'REA_GHIDRA_STARTUP_TIMEOUT_MS':'invented-retained'}),
            'invented_remote':dict(url='https://invented.invalid',headers={'Authorization':'invented-test-only'})})
    paths={k:'/opt/hermes-runtime/programs/rea-'+k+'-'+v['sha256'][:16] for k,v in OWNER['PROGRAMS'].items()}
    destination=original.with_name('ec-main-operational-restore-invented')
    return value,original,destination,paths


def test_only_the_existing_rea_dependency_values_and_workspace_are_rebound():
    cfg,old,new,paths=configuration();saved=copy.deepcopy(cfg)
    value=OWNER['rewrite'](cfg,old,new,paths,TRANSFORM)
    assert cfg==saved
    rea=value['mcp_servers']['rea']
    assert rea['command']==cfg['mcp_servers']['rea']['command']
    assert rea['args']==cfg['mcp_servers']['rea']['args']
    assert rea['env']['REA_GHIDRA_STARTUP_TIMEOUT_MS']=='invented-retained'
    assert rea['env']['GHIDRA_INSTALL_DIR']==paths['ghidra'] and rea['env']['JAVA_HOME']==paths['java']
    assert value['mcp_servers']['invented_remote']==cfg['mcp_servers']['invented_remote']
    assert value['model']==cfg['model'] and value['memory']==cfg['memory']


@pytest.mark.parametrize('damage',['missing','duplicate','other_source','caller_path','wrong_command'])
def test_dependency_rebinding_refuses_ambiguous_or_unreviewed_definitions(damage):
    cfg,old,new,paths=configuration()
    if damage=='missing':cfg['mcp_servers'].pop('rea')
    if damage=='duplicate':cfg['mcp_servers']['duplicate']=copy.deepcopy(cfg['mcp_servers']['rea'])
    if damage=='other_source':cfg['mcp_servers']['rea']['env']['JAVA_HOME']='/invented/unreviewed'
    if damage=='caller_path':paths['ghidra']='/invented/caller-choice'
    if damage=='wrong_command':cfg['mcp_servers']['rea']['command']='invented-wrapper'
    with pytest.raises(ValueError):OWNER['rewrite'](cfg,old,new,paths,TRANSFORM)


@pytest.mark.parametrize('damage',[None,'failed','old_source','not_stopped','promoted','old_state','enabled'])
def test_live_state_pass_is_required_before_program_staging(monkeypatch,damage):
    base=Path('/invented/base');live=base/'live';evidence=base/'operator-evidence/main-live-invented'
    monkeypatch.setitem(ROOT['retained_live'].__globals__,'BASE',base);monkeypatch.setitem(ROOT['retained_live'].__globals__,'LIVE',live)
    context={'source_sha256':ROOT['LIVE_SHA'],'evidence':str(evidence)}
    value=dict(operator_helper_sha256=ROOT['LIVE_SHA'],source_revision=base.name,complete=True,operator_job_stopped=True,
        current_source_operational_refresh_qualified=True,configured_candidate_restore_qualified=True,
        current_settings_and_oauth_preserved=True,all_admission_policies_preserved_disabled=True,
        candidate_promoted=False,daily_backup_registry_changed=False,fleet_launch_approved=False,
        source_profiles_changed=False,production_renewal_timer_enabled=False,previous_operational_state_reused=False)
    if damage=='failed':value['complete']=False
    if damage=='old_source':context['source_sha256']='wrong'
    if damage=='not_stopped':value['operator_job_stopped']=False
    if damage=='promoted':value['candidate_promoted']=True
    if damage=='old_state':value['previous_operational_state_reused']=True
    if damage=='enabled':value['all_admission_policies_preserved_disabled']=False
    read=lambda path,*args:json.dumps(context if path.name=='context.private.json' else value).encode()
    if damage:
        with pytest.raises(ValueError):ROOT['retained_live'](read)
    else:assert ROOT['retained_live'](read)==value


@pytest.mark.parametrize('damage',[None,'failed','network_unprotected','timeout'])
def test_native_program_probe_is_isolated_and_always_stopped(monkeypatch,tmp_path,damage):
    scope=ROOT['program_probe'].__globals__;artifact=tmp_path/'artifact';artifact.mkdir();programs=tmp_path/'programs';programs.mkdir()
    raw=(FOLDER/'probe_rea_public_programs.py').read_bytes();(artifact/'probe_rea_public_programs.py').write_bytes(raw)
    monkeypatch.setitem(scope,'ARTIFACT',artifact);monkeypatch.setitem(scope,'PROGRAM_ROOT',programs)
    context=dict(id='a'*32);account=SimpleNamespace(pw_name='invented-ec-identity',pw_uid=3001,pw_gid=3001)
    active=dict(Result='success',ExecMainStatus='0',User=account.pw_name,PrivateNetwork='yes',ProtectHome='yes',
        NoNewPrivileges='yes',SubState='exited',ActiveState='active',MainPID='0',ControlPID='0')
    if damage=='failed':active['Result']='exit-code'
    if damage=='network_unprotected':active['PrivateNetwork']='no'
    if damage=='timeout':active.update(SubState='running',MainPID='10')
    stopped=dict(ActiveState='inactive',MainPID='0',ControlPID='0')
    states=iter([{'LoadState':'not-found'},active,stopped]);monkeypatch.setitem(scope,'metadata',lambda unit:next(states))
    calls=[]
    monkeypatch.setattr(ROOT['subprocess'],'run',lambda args,**kwargs:calls.append((args,kwargs)) or SimpleNamespace(returncode=0))
    if damage=='timeout':
        ticks=iter([0,300]);monkeypatch.setattr(ROOT['time'],'monotonic',lambda:next(ticks))
    receipt=dict(complete=True,java_version_verified=True,ghidra_headless_import_passed=True,
        real_profiles_read=False,rea_server_started=False,model_called=False,external_sends=0)
    read=lambda path,uid:json.dumps(receipt).encode()
    def write(path,body):path.write_bytes(body)
    if damage:
        with pytest.raises(ValueError):ROOT['program_probe'](context,account,{'ghidra':'invented-ghidra','java':'invented-java'},read,write)
    else:
        result=ROOT['program_probe'](context,account,{'ghidra':'invented-ghidra','java':'invented-java'},read,write)
        assert result['complete'] and result['network_isolated'] and result['qualification_unit_stopped']
    args=calls[0][0]
    assert '--property=User='+account.pw_name in args
    assert '--property=PrivateNetwork=yes' in args and '--property=IPAddressDeny=any' in args
    assert '--property=CapabilityBoundingSet=' in args and '--property=NoNewPrivileges=yes' in args
    assert '--property=ProtectHome=yes' in args
    assert any('/var/lib/enhanced-cognee-profiles' in x for x in args if x.startswith('--property=InaccessiblePaths='))
    assert calls[-1][0][:2]==['/usr/bin/systemctl','stop']


def test_public_sources_and_native_handoff_are_exact():
    assert ROOT['OWNER_SHA']==hashlib.sha256((FOLDER/'rea_candidate_owner.py').read_bytes()).hexdigest()
    assert ROOT['SNAPSHOT_SHA']==hashlib.sha256((FOLDER/'public_program_snapshot.py').read_bytes()).hexdigest()
    assert ROOT['PROBE_SHA']==hashlib.sha256((FOLDER/'probe_rea_public_programs.py').read_bytes()).hexdigest()
    assert OWNER['OWNER_SHA']==hashlib.sha256((FOLDER/'main_live_reconciliation_owner.py').read_bytes()).hexdigest()
    controller=runpy.run_path(str(FOLDER/'launch_control.py'))
    assert controller['REA_PROGRAMS_SHA']==hashlib.sha256((FOLDER/'stage_rea_main_programs.py').read_bytes()).hexdigest()
    protocol=runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))
    protocol['owner_program']((FOLDER/'rea_candidate_owner.py').read_bytes())


def test_java_and_ghidra_home_and_environment_are_isolated(monkeypatch):
    monkeypatch.setenv('ENHANCED_JWT_SECRET','invented-test-only-must-not-be-inherited')
    probe=runpy.run_path(str(FOLDER/'probe_rea_public_programs.py'))
    home=Path('/run/ec-rea-program-proof-'+'a'*32);java=Path('/opt/hermes-runtime/programs/proof-java-'+'a'*32)
    env=probe['runtime_environment'](java,home)
    assert env['HOME']==str(home) and env['JAVA_TOOL_OPTIONS']=='-Duser.home='+str(home)
    assert env['JAVA_HOME']==str(java) and env['XDG_CONFIG_HOME']==str(home/'config')
    assert set(env)=={'PATH','HOME','JAVA_HOME','LANG','JAVA_TOOL_OPTIONS','XDG_CONFIG_HOME','XDG_CACHE_HOME','GHIDRA_HEADLESS_MAXMEM'}
    assert 'invented-test-only-must-not-be-inherited' not in repr(env)


@pytest.mark.parametrize('damage',[None,'ciphertext','manifest','format'])
def test_consumed_live_profile_generation_is_authenticated_before_decryption(monkeypatch,damage):
    base=Path('/invented/base');backups=Path('/invented/backups')
    monkeypatch.setitem(ROOT['authenticated_profile_archive'].__globals__,'BASE',base)
    path=backups/('hermes_main_live_configured_'+'a'*32+'.tar.age')
    body=b'age-encryption.org/v1\ninvented-ciphertext'
    key=b'invented-unit-test-signing-material-only'
    manifest=dict(format='hermes-live-main-configured+age-v1',source_revision=base.name,
                  ciphertext_sha256=hashlib.sha256(body).hexdigest())
    if damage=='format':manifest['format']='invented-wrong-format'
    manifest['signature']=hmac.new(key,ROOT['canonical'](manifest),hashlib.sha256).hexdigest()
    if damage=='manifest':manifest['source_revision']='tampered'
    if damage=='ciphertext':body+=b'tampered'
    def read(p,*args):
        if p==Path('/etc/enhanced-cognee/backup.json'):return json.dumps({'ENHANCED_BACKUP_SIGNING_KEY':key.decode()}).encode()
        return body if p==path else json.dumps(manifest).encode()
    calls=[]
    c=dict(BACKUPS=backups,MAX_CIPHER=650*1024**2,decrypt=lambda raw:calls.append(raw) or b'invented-private-archive')
    if damage:
        with pytest.raises(ValueError):ROOT['authenticated_profile_archive'](c,read,{'generation':str(path)})
        assert not calls
    else:
        assert ROOT['authenticated_profile_archive'](c,read,{'generation':str(path)})==b'invented-private-archive'
        assert len(calls)==1


@pytest.mark.parametrize('complete',[True,False])
def test_finished_program_job_is_returned_without_restarting_or_reissuing(monkeypatch,tmp_path,capsys,complete):
    base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/rea-main-programs-invented';evidence.mkdir(parents=True)
    context=dict(source_sha256='a'*64,evidence=str(evidence));(artifact/'context.private.json').write_text(json.dumps(context))
    result=dict(complete=complete,operator_job_stopped=True,operator_helper_sha256='a'*64)
    (evidence/'finish.summary.json').write_text(json.dumps(result))
    scope=ROOT['watch'].__globals__;monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'metadata',lambda unit:pytest.fail('retained unit restarted or inspected'))
    assert ROOT['watch'](lambda path,*args:path.read_bytes(),lambda *args:pytest.fail('retained receipt rewritten'))==(0 if complete else 1)
    assert json.loads(capsys.readouterr().out)==result


@pytest.mark.parametrize('changed',[False,True])
def test_whole_group_preserves_live_state_and_keeps_all_admission_gates_closed(monkeypatch,tmp_path,changed):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/rea-main-programs-invented';evidence.mkdir(parents=True)
    live=base/'live';live_evidence=base/'operator-evidence/main-live-invented'
    owner=b'invented-public-owner';(artifact/'rea_candidate_owner.py').write_bytes(owner)
    context=dict(source_sha256='a'*64,evidence=str(evidence),id='b'*32,restore_id='c'*32)
    entry=dict(user='ecbot_'+'d'*16,home='/var/lib/enhanced-cognee-profiles/'+'d'*16)
    destination=entry['home']+'/ec-main-operational-restore-invented'
    policy=Path('/invented/policy');files={artifact/'context.private.json':json.dumps(context).encode(),policy:b'disabled',
        live/'context.private.json':json.dumps({'evidence':str(live_evidence)}).encode(),
        live_evidence/'source-configuration.private.json':b'{"fingerprints":{"invented":"bound"}}',
        Path('/etc/enhanced-cognee/backup.json'):b'{"ENHANCED_BACKUP_RECIPIENT":"invented-public-recipient"}'}
    modes=[];stages=[]
    def read(path,*args):return files[path]
    def write(path,raw):assert path not in files;files[path]=raw
    pin=dict(size=1,sha256=hashlib.sha256(b'x').hexdigest())
    owned=dict(PROGRAMS={'ghidra':pin,'java':pin})
    snapshot=dict(MAX_ARCHIVE=1024,restore=lambda body,name,path:stages.append((name,path)))
    def owner_call(account,source,packet,**kwargs):
        modes.append((account.pw_uid,packet['mode'],packet))
        mode=packet['mode']
        if mode=='verify_source':
            if changed:raise ValueError('invented-current-source-changed')
            return dict(complete=True,current_source_settings_preserved=True),b''
        if mode=='program_archive':
            assert account.pw_uid==1000
            return dict(complete=True,program=packet['program'],archive_bytes=1,archive_sha256=pin['sha256']),b'x'
        assert account.pw_uid==3001
        if mode=='prepare':return dict(complete=True,remaining_reference_count=0,rea_definition_preserved=True,
            settings_and_oauth_preserved=True,scoped_status_authenticated=True,destination=destination,mcp_definitions=6),b''
        if mode=='capture_candidate':return dict(complete=True,receipt={'sqlite_databases':9}),b'invented-encrypted'
        assert mode=='restore_candidate' and packet['id']=='c'*32
        return dict(mcp_definitions=6,workspace_rebased=True,restored_scope_authenticated=True,oauth_and_environment_preserved=True,
            receipt={'pinned_provider_binding_reconstructed':True,'sqlite_databases_verified':9}),b''
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:(entry,{}),
        fresh_bundle=lambda entry:{'token':'invented-ordinary-only'},PINS={'continue_launch_main_operational.py':'invented'},
        definitions=lambda *args:{'validate_owner_result':lambda *args:None})
    common=dict(legacy=lambda:driver,owner=owner_call,packet=lambda account,mode,**kw:dict(mode=mode,**kw),
        PACKAGE=Path('/invented/package'),generation=lambda *args:(Path('/invented/configured.tar.age'),b'invented-cipher'),
        decrypt=lambda cipher:b'invented-private-archive',KINDS={'ValueError'})
    monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact);monkeypatch.setitem(scope,'LIVE',live)
    monkeypatch.setitem(scope,'PROGRAM_ROOT',tmp_path/'programs');monkeypatch.setitem(scope,'__file__',str(artifact/'stage_rea_main_programs.py'))
    monkeypatch.setitem(scope,'OWNER_SHA',hashlib.sha256(owner).hexdigest());monkeypatch.setitem(scope,'common',lambda:common)
    monkeypatch.setitem(scope,'support',lambda c:(read,write))
    monkeypatch.setitem(scope,'definitions',lambda path,*args:owned if path.name=='rea_candidate_owner.py' else snapshot)
    monkeypatch.setitem(scope,'retained_live',lambda read:{'new_inactive_candidate':destination})
    monkeypatch.setitem(scope,'authenticated_profile_archive',lambda *args:b'invented-original-archive')
    monkeypatch.setitem(scope,'program_probe',lambda *args:dict(complete=True))
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','e'*32)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_name=name,pw_uid=1000 if name=='vincentspereira' else 3001,
        pw_gid=1000 if name=='vincentspereira' else 3001,pw_dir='/home/vincentspereira' if name=='vincentspereira' else entry['home']))
    assert ROOT['worker']()==(1 if changed else 0)
    result=json.loads(files[evidence/'summary.json'])
    assert result['complete'] is (not changed)
    assert result['source_profiles_changed'] is result['previous_candidates_changed'] is result['candidate_promoted'] is False
    assert result['fleet_launch_approved'] is result['production_dispatch_qualified'] is result['production_renewal_timer_enabled'] is False
    assert result['all_admission_policies_preserved_disabled'] is True
    assert result['credentials_issued']==(0 if changed else 2)
    if changed:assert not stages and len(modes)==1
    else:
        assert len(stages)==4 and result['remaining_reference_count']==0 and result['sqlite_databases_recovered']==9
        assert [x[1] for x in modes]==['verify_source','program_archive','program_archive','prepare','capture_candidate','restore_candidate','verify_source']
        assert 'ENHANCED_BACKUP_SIGNING_KEY' not in repr(modes) and 'age-recovery-identity' not in repr(modes)
