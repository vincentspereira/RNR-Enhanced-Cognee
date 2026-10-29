"""Existing-key localization, private pipes, snapshots and failure preservation."""
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
BIND = runpy.run_path(str(DIRECTORY/'bind_launch_model_credential.py'), run_name='binding_tests')
REPAIR = runpy.run_path(str(DIRECTORY/'repair_launch_named_runtime.py'), run_name='repair_tests')


def config():
    return {'model':dict(provider='zai', default='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/paas/v4/',
                         key_env='HERMES_CUSTOM_ZAI_API_KEY')}


def test_only_the_declared_zai_credential_pointer_is_accepted():
    assert BIND['pointer'](config()) == ('HERMES_CUSTOM_ZAI_API_KEY','/api/paas/v4')


@pytest.mark.parametrize('change',['root_key','model','provider','host','userinfo','query','port','managed_secret'])
def test_key_source_cannot_be_rebound_to_operator_or_another_service(change):
    c = config()
    if change=='root_key':c['model']['key_env']='ENCRYPTION_MASTER_KEY'
    elif change=='model':c['model']['default']='other'
    elif change=='provider':c['model']['provider']='other'
    elif change=='host':c['model']['base_url']='https://invented.example/api/paas/v4'
    elif change=='userinfo':c['model']['base_url']='https://user:invented@open.bigmodel.cn/api/paas/v4'
    elif change=='query':c['model']['base_url']+='?key=invented'
    elif change=='port':c['model']['base_url']='https://open.bigmodel.cn:8443/api/paas/v4'
    else:c['secrets']={'external':{'enabled':True}}
    with pytest.raises(ValueError):BIND['pointer'](c)


def test_oauth_and_other_provider_changes_cannot_hide_in_pool_normalization():
    before={'providers':{'nous':{'invented_oauth':'preserved'}}, 'credential_pool':{'zai':[{'source':'env'}], 'other':[{'id':'stable'}]}, 'updated_at':1}
    after=json.loads(json.dumps(before))
    after['credential_pool']['zai']=[{'source':'env','priority':1}];after['updated_at']=2
    assert BIND['auth_without_zai_metadata'](before)==BIND['auth_without_zai_metadata'](after)
    after['providers']['nous']['invented_oauth']='changed'
    assert BIND['auth_without_zai_metadata'](before)!=BIND['auth_without_zai_metadata'](after)


def test_model_key_travels_only_in_private_stdin_not_arguments_environment_or_evidence(monkeypatch):
    credential='invented-not-a-real-model-key'
    packet=dict(mode='bind',key=credential,endpoint_path='/api/paas/v4',nonce='a'*32)
    def run(args,**kw):
        assert credential not in repr(args) and credential not in repr(kw['env'])
        assert credential.encode() in kw['input']
        assert kw['user']==1234 and kw['extra_groups']==() and kw['stderr'] is BIND['subprocess'].DEVNULL
        return SimpleNamespace(returncode=0,stdout=b'{"complete":true}')
    monkeypatch.setattr(BIND['subprocess'],'run',run)
    helper={'owner_program':lambda source:('public-launcher',b'public-source\n')}
    assert BIND['owner'](helper,SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/invented'),b'public',packet)=={'complete':True}


@pytest.mark.parametrize('packet',[{'mode':'read_source','private_key':'invented'}, {'mode':'bind','private_key':'invented'}, {'mode':'other'}])
def test_operator_keys_and_unknown_packets_never_cross_owner_pipe(packet,monkeypatch):
    monkeypatch.setattr(BIND['subprocess'],'run',lambda *a,**kw:pytest.fail('invalid packet crossed owner boundary'))
    with pytest.raises(ValueError):BIND['owner']({},SimpleNamespace(pw_uid=1234),b'public',packet)


def test_binding_is_backed_up_before_any_native_construction_and_never_logged(tmp_path,monkeypatch):
    function=BIND['bind_and_backup']; events=[];writes=[]
    key='invented-not-a-real-model-key'
    receipt=dict(complete=True,existing_model_credential_bound=True,configured_primary_route_resolved=True,
                 unrelated_environment_and_oauth_preserved=True,candidate_model_auth_metadata_may_change=True,
                 source_profile_changed=False,model_called=False,credentials_generated=0)
    monkeypatch.setitem(function.__globals__,'owner',lambda *a:events.append('bind') or receipt)
    monkeypatch.setitem(function.__globals__,'sync_directory',lambda p:None)
    monkeypatch.setattr(BIND['pwd'],'getpwnam',lambda p:object())
    batch={'fresh_backup':lambda *a:events.append('backup_restore') or '/invented/generation.tar.age'}
    function(dict(user='ecbot_'+'a'*16,home='/var/lib/enhanced-cognee-profiles/'+'a'*16),tmp_path,b'public',
             ({},batch,{'key':key,'endpoint_path':'/api/paas/v4'}),lambda *a:b'',lambda p,v:writes.append(v))
    assert events==['bind','backup_restore'] and all(key.encode() not in raw for raw in writes)
    assert any(b'model-profile' not in raw and b'generation.tar.age' in raw for raw in writes)


@pytest.mark.parametrize('state,sub,pid,control,expected',[
    ('failed','failed','0','0',True), ('inactive','dead','0','0',True),
    ('active','running','1','0',False),('failed','failed','1','0',False),
    ('inactive','dead','0','2',False),('inactive','dead',None,None,False)])
def test_quiescent_failure_is_preserved_and_never_mistaken_for_a_running_or_passing_test(state,sub,pid,control,expected):
    assert REPAIR['quiescent'](dict(ActiveState=state,SubState=sub,MainPID=pid,ControlPID=control)) is expected


def test_controller_source_access_is_readonly_and_agent_units_remain_separate():
    rows=[{'home':'/var/lib/enhanced-cognee-profiles/'+f'{n:016x}'} for n in range(40)]
    value=REPAIR['operator_properties'](rows)
    assert value['CapabilityBoundingSet']=='CAP_SETUID CAP_SETGID' and value['NoNewPrivileges']=='yes'
    assert value['ReadOnlyPaths']=='/home/vincentspereira/.hermes' and value['ProtectSystem']=='strict'
    assert '/home/vincentspereira/.hermes' not in value['ReadWritePaths'].split()
    assert value['Restart']=='no' and value['PrivateTmp']=='no'
    with pytest.raises(ValueError):REPAIR['operator_properties']([{'home':'/unrelated'}]*40)


def test_repair_source_pins_and_original_failed_probe_are_preserved():
    for name,digest in REPAIR['PINS'].items():
        assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((DIRECTORY/'qualify_launch_named_runtime.py').read_bytes()).hexdigest()=='d7494b5d7507322b5a0dd731211d3ef00c66122f90a7544961f06d9f75b6933f'
    control=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='repair_dispatch_tests')
    assert hashlib.sha256((DIRECTORY/'repair_launch_named_runtime.py').read_bytes()).hexdigest()==control['REPAIR_SHA']


def test_native_failure_receipts_cannot_authorize_replay_of_a_successful_profile(tmp_path,monkeypatch):
    function=REPAIR['retained_failure']
    monkeypatch.setitem(function.__globals__,'BASE',tmp_path)
    value=dict(complete=False,selected_profiles=40,qualified_profiles=1,failed_profiles=3,unattempted_profiles=36,
               credentials_issued=0,all_admission_policies_preserved_disabled=True)
    with pytest.raises(ValueError):function(lambda *args:json.dumps(value).encode())
