"""Pinned native agent + provider + actual SDK, invented in-memory HTTP only.

Run with the pinned native Python and setpriv --no-new-privs. Identity/profile
selection is adapted ONLY in this offline test. It proves no installed-host or
real-model behavior. All actual socket/DNS operations fail before any I/O.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import pwd
import runpy
import socket
import sys
import tempfile
from types import SimpleNamespace

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
MODULE=runpy.run_path(str(DIRECTORY/'qualify_launch_model_recall_child.py'),run_name='offline_current_model_smoke')
sys.path.insert(0,str(MODULE['RELEASE']/'repo'))
PHASE='imports'


def main():
    global PHASE
    def deny(*args,**kwargs):raise AssertionError('offline_smoke_socket_refused')
    socket.socket.connect=socket.socket.connect_ex=socket.getaddrinfo=deny
    import httpx
    import openai
    from agent import process_bootstrap
    from plugins import memory as loader
    rows={};counter={'capture':0,'recall':0};active={'stage':'recall'};loaded={}
    ident='b'*32
    contract=runpy.run_path(str(DIRECTORY.parents[2]/'src/multi_tenant.py'),run_name='offline_backend_partition_contract')
    for peer in (False,True):contract['validate_tenant_id'](MODULE['identity'](ident,peer)['project_id'])
    content='Fictional Rowan '+ident+' uses a thirteen-day review cycle.'
    def memory(method,path,body=None):
        if path=='/v1/memories/status':
            return dict(ready=True,schema_version=3,encryption='AES-256-GCM',tenant_id='qualification',
                project_id=MODULE['identity'](ident)['project_id'],subject='zai_'+ident,active_records=len(rows),pending_change_events=0,worker_available=True)
        if path=='/v1/memories/recall':return {'results':list(rows.values())}
        if path=='/v1/memories':
            rows['new-invented-record']=dict(id='new-invented-record',version=1,content=body['content'],state='active')
            return rows['new-invented-record']
        if path.endswith('/retract'):
            rows['new-invented-record'].update(version=2,state='retracted');return rows['new-invented-record']
        if path.endswith('/history'):return {'versions':[{'version':2},{'version':1}]}
        return rows['new-invented-record']
    rows['new-invented-record']=dict(id='new-invented-record',version=1,content=content,state='active')
    original_load=loader.load_memory_provider
    def load(*args,**kwargs):
        provider=original_load(*args,**kwargs);initialize=provider.initialize
        loaded['module']=sys.modules[type(provider).__module__]
        original_type=loaded['module'].MemoryClient
        class Peer(original_type):
            def request(self,*a,**kw):
                error=RuntimeError('invented_peer_denied');error.status_code=404;raise error
        loaded['module'].MemoryClient=Peer
        def init(*a,**kw):
            initialize(*a,**kw);provider._client.request=memory
        provider.initialize=init
        return provider
    loader.load_memory_provider=load
    def response(request):
        data=json.loads(request.content);stage=active['stage'];counter[stage]+=1
        step=counter[stage]
        assert str(request.url)=='https://open.bigmodel.cn/api/coding/paas/v4/chat/completions'
        if stage=='capture' and step==1:
            tool=('enhanced_recall',{'query':'Rowan '+ident})
        elif stage=='capture' and step==2:
            tool=('enhanced_remember',{'content':content,'idempotency_key':'invented-capture-retry-key'})
        else:tool=None
        message={'role':'assistant','content':None if tool else content}
        if tool:
            message['tool_calls']=[{'id':'call_invented_'+str(step),'type':'function',
                'function':{'name':tool[0],'arguments':json.dumps(tool[1])}}]
        if data.get('stream'):
            event=dict(id='chatcmpl-invented',object='chat.completion.chunk',created=1,model='glm-5.3-flash',
                choices=[dict(index=0,delta=message,finish_reason=None)])
            if tool:event['choices'][0]['delta']['tool_calls'][0]['index']=0
            end=dict(id='chatcmpl-invented',object='chat.completion.chunk',created=1,model='glm-5.3-flash',
                choices=[dict(index=0,delta={},finish_reason='tool_calls' if tool else 'stop')])
            raw='data: '+json.dumps(event)+'\n\ndata: '+json.dumps(end)+'\n\ndata: [DONE]\n\n'
            return httpx.Response(200,text=raw,headers={'Content-Type':'text/event-stream'})
        return httpx.Response(200,json=dict(id='chatcmpl-invented',object='chat.completion',created=1,model='glm-5.3-flash',
            choices=[dict(index=0,message=message,finish_reason='tool_calls' if tool else 'stop')]))
    def client(**kwargs):
        kwargs['http_client']=httpx.Client(transport=httpx.MockTransport(response),trust_env=False)
        return openai.OpenAI(**kwargs)
    process_bootstrap.OpenAI=client
    parent=Path(tempfile.mkdtemp(prefix='ec-offline-model-smoke-',dir='/tmp'));(parent/('zai_recall_'+ident)).mkdir(mode=0o700)
    operation=MODULE['child_operation'];scope=operation.__globals__;scope['FIXTURES']=parent
    account=pwd.getpwuid(os.geteuid())
    # Offline fixture selection, not a kernel identity assertion or host pass.
    original_getuid=pwd.getpwuid;original_groups=os.getgroups
    pwd.getpwuid=lambda uid:SimpleNamespace(pw_name='hermes-runtime',pw_uid=uid,pw_dir=account.pw_dir)
    os.getgroups=lambda:()
    packet=dict(stage='recall',run_id=ident,key='invented-unused-model-key',token='invented-api-token',peer='invented-peer-token',
        guard=(DIRECTORY/'zai_native_qualification_guard_v2.py').read_text(),
        observer=(DIRECTORY/'observe_launch_native_runtime.py').read_text(),record_id='new-invented-record')
    try:
        PHASE='native_recall'
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):recall=operation(packet)
        assert recall['complete'] and counter['recall']==1 and counter['capture']==0
        assert recall['network']['unexpected_denied']==0
        assert rows['new-invented-record']['state']=='retracted' and rows['new-invented-record']['version']==2
        print(json.dumps(dict(complete=True,synthetic_only=True,real_network_operations=0,
            native_agent_provider_sdk_exercised=True,capture_model_requests=0,recall_model_requests=1,
            fresh_recall_fixture=True,canonical_evidence_delivered=recall['canonical_evidence_delivered'],
            real_model_qualified=False,installed_identity_qualified=False,fixture_preserved=str(parent))))
    finally:
        pwd.getpwuid=original_getuid;os.getgroups=original_groups


if __name__=='__main__':
    try:main()
    except Exception as error:
        import traceback
        print(json.dumps(dict(complete=False,synthetic_only=True,phase=PHASE,error_kind=type(error).__name__,
            helper_phase=MODULE['child_operation'].__globals__.get('PHASE'),
            helper_observation=MODULE['child_operation'].__globals__.get('OBSERVATION'),
            public_frames=[dict(file=Path(frame.filename).name,line=frame.lineno) for frame in traceback.extract_tb(error.__traceback__)[-8:]])))
        raise SystemExit(1)
