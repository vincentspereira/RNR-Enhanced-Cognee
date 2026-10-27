"""Guard physical requests and invented-only memory effects without networking."""
import hashlib
import json
from pathlib import Path
import runpy
import socket
from types import SimpleNamespace

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
GUARD=runpy.run_path(str(DIRECTORY/'zai_native_qualification_guard_v2.py'),run_name='zai_guard_unit_tests')
MODULE=runpy.run_path(str(DIRECTORY/'qualify_launch_current_model_v2.py'),run_name='current_model_unit_tests')
ERROR=GUARD['GuardError']
IDENT='a'*32


def packet(stage='capture'):
    return dict(stage=stage,run_id=IDENT,key='invented-unused-model-key',token='invented-api-token',peer='invented-peer-token',
        guard=(DIRECTORY/'zai_native_qualification_guard_v2.py').read_text(),
        observer=(DIRECTORY/'observe_launch_native_runtime.py').read_text(),record_id=None if stage=='capture' else 'new-invented-record')


def client():
    transport=SimpleNamespace(event_hooks={},follow_redirects=True)
    def create(body,status=200,exception=None,url=GUARD['REQUEST_URL'],model='glm-5.3-flash'):
        request=SimpleNamespace(method='POST',url=url,content=json.dumps(body).encode(),headers={})
        for hook in transport.event_hooks['request']:hook(request)
        if exception:raise exception
        response=SimpleNamespace(status_code=status,request=request,model=model)
        for hook in transport.event_hooks['response']:hook(response)
        return response
    return SimpleNamespace(max_retries=2,_client=transport,chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def agent():
    main=client()
    return SimpleNamespace(tools=[{'function':{'name':name}} for name in ('enhanced_recall','enhanced_remember','terminal')],
        _fallback_chain=[],_fallback_activated=False,_memory_manager=object(),client=main,
        _create_openai_client=lambda *a,**kw:client(),_request_client_cache={'client':client()})


def body():return dict(model=GUARD['MODEL'],max_tokens=2048,messages=[],tools=[{'type':'function','function':{'name':'enhanced_recall'}}])


def test_cloned_and_cached_clients_share_budget_and_evidence():
    instance=agent();boundary=GUARD['NetworkBoundary']()
    state=GUARD['restrict_agent'](instance,{'enhanced_recall'},boundary,prefetch_probe=lambda body:True)
    clients=[instance.client,instance._request_client_cache['client'],instance._create_openai_client()]
    for i in range(6):
        current=clients[i%3]
        assert current.max_retries==0 and current._client.follow_redirects is False
        current.chat.completions.create(body())
        assert boundary.model_allowed() is False
    assert state['count']==6 and state['prefetched_evidence_delivered'] is True
    assert state['returned_model_verified_requests']==6
    with pytest.raises(ERROR):clients[2].chat.completions.create(body())
    assert state['count']==6
    assert instance.valid_tool_names=={'enhanced_recall'}


@pytest.mark.parametrize('damage',['route','model','tokens','oversize','tools','service_tier'])
def test_unapproved_requests_fail_before_budget_or_network_admission(damage):
    instance=agent();boundary=GUARD['NetworkBoundary']();value=body()
    state=GUARD['restrict_agent'](instance,{'enhanced_recall'},boundary)
    url=GUARD['REQUEST_URL']
    if damage=='route':url='https://api.z.ai/api/coding/paas/v4/chat/completions'
    elif damage=='model':value['model']='unapproved-model'
    elif damage=='tokens':value['max_tokens']=2049
    elif damage=='oversize':value['messages']=['x'*65537]
    elif damage=='tools':value['tools'][0]['function']['name']='terminal'
    else:value['service_tier']='priority'
    with pytest.raises(ERROR):instance.client.chat.completions.create(value,url=url)
    assert state['count']==0 and state['failed_response'] is True
    assert boundary.model_allowed() is False
    with pytest.raises(ERROR):instance._create_openai_client().chat.completions.create(body())


@pytest.mark.parametrize('status',[301,401,403,429,500])
def test_error_status_stops_later_physical_requests(status):
    instance=agent();boundary=GUARD['NetworkBoundary']()
    state=GUARD['restrict_agent'](instance,{'enhanced_recall'},boundary)
    instance.client.chat.completions.create(body(),status=status)
    with pytest.raises(ERROR):instance._create_openai_client().chat.completions.create(body())
    assert state['count']==1 and state['rate_limited'] is (status==429)


def test_transport_exception_latches_stop_across_clients():
    instance=agent();boundary=GUARD['NetworkBoundary']()
    state=GUARD['restrict_agent'](instance,{'enhanced_recall'},boundary)
    with pytest.raises(TimeoutError):instance.client.chat.completions.create(body(),exception=TimeoutError())
    with pytest.raises(ERROR):instance._create_openai_client().chat.completions.create(body())
    assert state['count']==1 and state['failed_response'] is True


def test_unexpected_returned_model_stops_before_native_effects():
    instance=agent();boundary=GUARD['NetworkBoundary']()
    state=GUARD['restrict_agent'](instance,{'enhanced_recall'},boundary)
    with pytest.raises(ERROR):instance.client.chat.completions.create(body(),model='unexpected-served-model')
    with pytest.raises(ERROR):instance._create_openai_client().chat.completions.create(body())
    assert state['count']==1 and state['returned_model_verified_requests']==0


@pytest.mark.parametrize('damage',['no_wire_requests','not_served_model','no_connection','no_dns','failed_status','private_extra'])
def test_owner_receipt_cannot_claim_mock_or_wrong_model_as_host_success(damage):
    value=dict(complete=True,stage='capture',record_id='new-invented-record',selected_capture_qualified=True,
        invented_sensitive_input_excluded=True,native_turn_completed=True,
        requests=dict(count=1,http_statuses=[200],rate_limited=False,failed_response=False,
            prefetched_evidence_delivered=False,returned_model_verified_requests=1),
        network=dict(memory_operations=4,model_dns=1,model_connections=1,metadata_denied=1,unexpected_denied=0,controls_denied=3))
    MODULE['validate_result'](value,'capture')
    if damage=='no_wire_requests':value['requests'].update(count=0,http_statuses=[],returned_model_verified_requests=0)
    elif damage=='not_served_model':value['requests']['returned_model_verified_requests']=0
    elif damage=='no_connection':value['network']['model_connections']=0
    elif damage=='no_dns':value['network']['model_dns']=0
    elif damage=='failed_status':value['requests']['http_statuses']=[500]
    else:value['private_packet']='must-not-return'
    with pytest.raises(ValueError):MODULE['validate_result'](value,'capture')


def test_model_admission_is_per_thread_and_requires_native_sdk_frame(monkeypatch):
    boundary=GUARD['NetworkBoundary']();boundary.admit(True)
    assert boundary.model_allowed() is False
    monkeypatch.setitem(boundary.model_allowed.__globals__,'trusted_frame',lambda names:True)
    assert boundary.model_allowed() is True
    import threading
    values=[]
    thread=threading.Thread(target=lambda:values.append(boundary.model_allowed()))
    thread.start();thread.join()
    assert values==[False]
    boundary.failed=True
    assert boundary.model_allowed() is False


def test_unhooked_connections_to_configured_host_still_refuse(monkeypatch):
    for target in ('connect','connect_ex'):
        monkeypatch.setattr(socket.socket,target,lambda *a:pytest.fail('escaped network guard'))
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:pytest.fail('escaped DNS guard'))
    boundary=GUARD['NetworkBoundary']().install()
    with pytest.raises(ERROR):socket.getaddrinfo('open.bigmodel.cn',443)
    assert boundary.counts['controls_denied']==3 and boundary.counts['unexpected_denied']==1
    assert boundary.failed is True


@pytest.mark.parametrize('extra',['ENHANCED_JWT_SECRET','ENHANCED_BACKUP_SIGNING_KEY','private_key','command'])
def test_root_keys_and_commands_cannot_cross_owner_packet(extra):
    value=packet();value[extra]='invented-root-secret'
    with pytest.raises(ValueError):MODULE['packet_shape'](value)


def memory(packet,boundary):
    calls=[]
    def request(method,path,body=None):
        calls.append((method,path,body))
        if path=='/v1/memories':return {'id':'new-invented-record','version':1}
        return {'id':'new-invented-record','version':1,'content':'Rowan '+IDENT+' has thirteen-day reviews.'}
    provider=SimpleNamespace(_client=SimpleNamespace(request=request))
    original,state=MODULE['guard_memory'](provider,packet,boundary)
    return provider._client.request,state,calls


def selected():
    return dict(content='Rowan '+IDENT+' uses thirteen-day reviews.',idempotency_key='new-invented-retry-key',
        metadata={'write_origin':'hermes_selected_tool'})


def test_one_selected_record_allows_only_identical_retry():
    boundary=GUARD['NetworkBoundary']();request,state,calls=memory(packet(),boundary)
    request('POST','/v1/memories',selected());request('POST','/v1/memories',selected())
    value=selected();value['idempotency_key']='different-key'
    with pytest.raises(ValueError):request('POST','/v1/memories',value)
    assert len(calls)==2 and state['record_id']=='new-invented-record' and boundary.failed is True


@pytest.mark.parametrize('damage',['secret','raw_transcript','unrelated','wrong_origin','correction','old_record'])
def test_unrelated_secret_or_history_edits_refuse_before_api(damage):
    boundary=GUARD['NetworkBoundary']();request,state,calls=memory(packet(),boundary)
    value=selected();method,path='POST','/v1/memories'
    if damage=='secret':value['content']+=' fictional-canary-'+IDENT
    elif damage=='raw_transcript':value['metadata']['raw']='fictional-canary-'+IDENT
    elif damage=='unrelated':value['content']='An unrelated decision.'
    elif damage=='wrong_origin':value['metadata']['write_origin']='raw_transcript'
    elif damage=='correction':method='PATCH';path='/v1/memories/new-invented-record'
    else:path='/v1/memories/5d0e9a49bdf544359ae6deff/retract'
    with pytest.raises(ValueError):request(method,path,value)
    assert not calls and state['refused'] and boundary.failed


def test_recall_turn_has_no_writes_and_evidence_must_reach_model_request():
    value=packet('recall');boundary=GUARD['NetworkBoundary']();request,state,calls=memory(value,boundary)
    wire={'messages':[{'role':'tool','content':'Rowan '+IDENT+' thirteen-day reviews.'}]}
    assert MODULE['prefetch_probe'](value,state,wire) is False
    request('GET','/v1/memories/new-invented-record')
    assert MODULE['prefetch_probe'](value,state,wire) is True
    assert MODULE['prefetch_probe'](value,state,{'messages':[{'content':'no saved evidence'}]}) is False
    with pytest.raises(ValueError):request('POST','/v1/memories',selected())
    assert len(calls)==1


def test_owner_packet_uses_only_private_stdin(monkeypatch):
    value=packet();events=[]
    def run(args,**kw):
        events.append(kw)
        assert value['key'] not in repr(args) and value['token'] not in repr(args)
        assert value['key'] not in repr(kw['env']) and value['token'] not in repr(kw['env'])
        assert kw['input'].splitlines()[0]==b'public-source'
        assert json.loads(kw['input'].splitlines()[1])==value
        assert kw['extra_groups']==() and kw['user']==1234 and kw['stderr'] is MODULE['subprocess'].DEVNULL
        return SimpleNamespace(stdout=b'{"complete":false,"phase":"identity","error_kind":"ValueError","observation":{}}',returncode=1)
    monkeypatch.setattr(MODULE['subprocess'],'run',run)
    result=MODULE['owner']({'owner_program':lambda source:('public',b'public-source\n'),'EXECUTABLE':'/fixed/python'},
        b'public',SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/fixed/home'),value)
    assert result['complete'] is False and len(events)==1


def test_frozen_pins_and_bounded_owner_program():
    for name,digest in MODULE['PINS'].items():
        assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest
    helper=runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'),run_name='current_model_owner_protocol')
    helper['owner_program']((DIRECTORY/'qualify_launch_current_model_v2.py').read_bytes())
    assert MODULE['identity'](IDENT)['roles']==['api_client']
    assert MODULE['identity'](IDENT)['project_id']!=MODULE['identity'](IDENT,True)['project_id']
    control=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='current_model_dispatch_contract')
    assert hashlib.sha256((DIRECTORY/'qualify_launch_current_model_v2.py').read_bytes()).hexdigest()==control['CURRENT_MODEL_V2_SHA']


def test_repeating_completed_job_only_watches(monkeypatch):
    launch=MODULE['launch'];scope=launch.__globals__;events=[]
    monkeypatch.setattr(MODULE['os'],'geteuid',lambda:0)
    monkeypatch.setattr(MODULE['os'].path,'lexists',lambda path:True)
    monkeypatch.setitem(scope,'definitions',lambda *a:{'read_file':object(),'private_write':object()})
    monkeypatch.setitem(scope,'watch',lambda read:events.append('reattach') or 0)
    assert launch()==0 and events==['reattach']


@pytest.mark.parametrize('damage',['successful','credentials','phase','source','scope','active_job'])
def test_continuation_refuses_any_prior_success_effect_or_live_job(monkeypatch,damage):
    prior=MODULE['BASE']/'operator-evidence/current-model-native-z_rt7ame'
    value=dict(complete=False,failure_phase='preflight',credentials_issued=0,error_kind='ValueError',
        operator_helper_sha256='4a9ba1890c56fcf3806e834ee28c6c28686e6137a4f16c33e08cfa70eb535402',
        new_invented_scope='404b12912a5b4abdbd4172ff46422f8b',all_admission_policies_preserved_disabled=True)
    if damage=='successful':value['complete']=True
    elif damage=='credentials':value['credentials_issued']=2
    elif damage=='phase':value['failure_phase']='capture'
    elif damage=='source':value['operator_helper_sha256']='0'*64
    elif damage=='scope':value['new_invented_scope']='0'*32
    def read(path,*unused):
        if path.name=='summary.json':return json.dumps(value).encode()
        if path.name=='context.json':return json.dumps(dict(evidence=str(prior),run_id=value['new_invented_scope'])).encode()
        return (DIRECTORY/'qualify_launch_current_model.py').read_bytes()
    state=MODULE['retained_zero_call_refusal'].__globals__
    monkeypatch.setitem(state,'properties',lambda *a:dict(ActiveState='active' if damage=='active_job' else 'inactive',MainPID='0',ControlPID='0'))
    with pytest.raises(ValueError):MODULE['retained_zero_call_refusal'](read)


def test_exact_zero_call_refusal_can_continue_without_replaying_it(monkeypatch):
    prior=MODULE['BASE']/'operator-evidence/current-model-native-z_rt7ame'
    value=dict(complete=False,failure_phase='preflight',credentials_issued=0,error_kind='ValueError',
        operator_helper_sha256='4a9ba1890c56fcf3806e834ee28c6c28686e6137a4f16c33e08cfa70eb535402',
        new_invented_scope='404b12912a5b4abdbd4172ff46422f8b',all_admission_policies_preserved_disabled=True)
    def read(path,*unused):
        if path.name=='summary.json':return json.dumps(value).encode()
        if path.name=='context.json':return json.dumps(dict(evidence=str(prior),run_id=value['new_invented_scope'])).encode()
        return (DIRECTORY/'qualify_launch_current_model.py').read_bytes()
    state=MODULE['retained_zero_call_refusal'].__globals__
    monkeypatch.setitem(state,'properties',lambda *a:dict(ActiveState='inactive',MainPID='0',ControlPID='0'))
    assert MODULE['retained_zero_call_refusal'](read)==str(prior)
    assert hashlib.sha256((DIRECTORY/'zai_native_qualification_guard.py').read_bytes()).hexdigest()=='1f579b3cbf88b5b922f3e0ff2cda345e496c639fdec79600bb3b92e3e90f5cde'
