"""Exact configured ZAI request budget and network boundaries for invented tests."""
from __future__ import annotations
import functools
import json
from pathlib import Path
import socket
import sys
import threading

RELEASE=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
MODEL='glm-5.3-flash'
BASE_URL='https://open.bigmodel.cn/api/coding/paas/v4'
REQUEST_URL=BASE_URL+'/chat/completions'
MAX_CALLS=6
MAX_TOKENS=2048
METADATA={'agent.'+name:str(RELEASE/'repo/agent'/(name+'.py')) for name in ('model_metadata','model_metadata_http','models_dev')}


class GuardError(RuntimeError):
    pass


def require(value):
    if not value:raise GuardError('zai_qualification_guard_refused')


def trusted_frame(names):
    frame=sys._getframe(1)
    for _ in range(120):
        if frame is None:return False
        name=frame.f_globals.get('__name__')
        module=sys.modules.get(name) if name in names else None
        if module is not None and module.__dict__ is frame.f_globals:
            path=getattr(module,'__file__','')
            expected=names[name]
            if expected is None and isinstance(path,str) and path.startswith(str(RELEASE)+'/'):
                return True
            if path==expected:return True
        frame=frame.f_back
    return False


class NetworkBoundary:
    def __init__(self):
        self.local=threading.local();self.lock=threading.RLock();self.addresses=set();self.failed=False
        self.counts=dict(memory_operations=0,model_dns=0,model_connections=0,
            metadata_denied=0,unexpected_denied=0,controls_denied=0)

    def admit(self,value):self.local.admitted=value

    def model_allowed(self):
        return not self.failed and getattr(self.local,'admitted',False) and trusted_frame({'openai._base_client':None})

    def denied(self,host=None,port=None):
        with self.lock:
            if getattr(self.local,'control',False):key='controls_denied'
            elif host in {'models.dev','openrouter.ai','open.bigmodel.cn','api.z.ai'} and port in {443,'443'} and trusted_frame(METADATA):key='metadata_denied'
            else:key='unexpected_denied'
            self.counts[key]+=1
            if key=='unexpected_denied':self.failed=True
        raise GuardError('zai_qualification_network_denied')

    def install(self):
        original_connect,original_ex,original_resolve=socket.socket.connect,socket.socket.connect_ex,socket.getaddrinfo
        def address(value):
            if isinstance(value,tuple) and len(value)>=2:
                if value[:2]==('127.0.0.1',28080):
                    with self.lock:self.counts['memory_operations']+=1
                    return
                if self.model_allowed() and value[:2] in self.addresses:
                    with self.lock:self.counts['model_connections']+=1
                    return
            self.denied()
        def connect(sock,value):address(value);return original_connect(sock,value)
        def connect_ex(sock,value):address(value);return original_ex(sock,value)
        def resolve(host,port,*args,**kwargs):
            if (host,port)==('127.0.0.1',28080):
                with self.lock:self.counts['memory_operations']+=1
                return original_resolve(host,port,*args,**kwargs)
            if host=='open.bigmodel.cn' and port in {443,'443'} and self.model_allowed():
                rows=original_resolve(host,port,*args,**kwargs)
                with self.lock:
                    self.counts['model_dns']+=1
                    self.addresses.update(row[4][:2] for row in rows)
                return rows
            return self.denied(host,port)
        socket.socket.connect,socket.socket.connect_ex,socket.getaddrinfo=connect,connect_ex,resolve
        self.local.control=True
        try:
            with socket.socket() as probe:
                for call in (lambda:probe.connect(('192.0.2.1',443)),lambda:probe.connect_ex(('192.0.2.1',443)),lambda:socket.getaddrinfo('invalid.example',443)):
                    try:call()
                    except GuardError:continue
                    raise GuardError('network_control_failed')
        finally:self.local.control=False
        require(self.counts['controls_denied']==3)
        return self


def restrict_agent(agent,allowed,boundary,*,prefetch_probe=None):
    names={tool.get('function',{}).get('name') for tool in agent.tools}
    require(allowed <= names and not agent._fallback_chain and not agent._fallback_activated and agent._memory_manager is not None)
    agent.tools=[tool for tool in agent.tools if tool.get('function',{}).get('name') in allowed]
    agent.valid_tool_names=set(allowed)
    state=dict(count=0,http_statuses=[],rate_limited=False,failed_response=False,prefetched_evidence_delivered=False,
        returned_model_verified_requests=0)
    lock=threading.RLock();evidence=set()
    def validate_request(request):
        with lock:
            require(not boundary.failed and not state['failed_response'] and state['count']<MAX_CALLS
                and request.method=='POST' and str(request.url)==REQUEST_URL
                and len(request.content)<=65536 and request.headers.get('content-encoding') in {None,'identity'})
            body=json.loads(request.content)
            require(isinstance(body,dict) and body.get('model')==MODEL and not body.get('service_tier'))
            tokens=body.get('max_tokens',body.get('max_completion_tokens'))
            require(type(tokens) is int and 0<tokens<=MAX_TOKENS)
            tools=body.get('tools',[])
            require(isinstance(tools,list) and all(isinstance(t,dict) and t.get('type')=='function'
                and t.get('function',{}).get('name') in allowed for t in tools))
            state['count']+=1
            if prefetch_probe is not None and prefetch_probe(body) is True:evidence.add(id(request))
            boundary.admit(True)
    def request_hook(request):
        try:validate_request(request)
        except Exception:
            state['failed_response']=True
            boundary.admit(False)
            raise
    def response_hook(response):
        boundary.admit(False)
        code=response.status_code
        with lock:
            require(type(code) is int and 100<=code<=599 and len(state['http_statuses'])<MAX_CALLS)
            state['http_statuses'].append(code)
            state['rate_limited']|=code==429
            state['failed_response']|=code!=200
            if code==200 and id(getattr(response,'request',None)) in evidence:state['prefetched_evidence_delivered']=True
    def install(client):
        if getattr(client,'_ec_zai_qualification_guard',None) is state:return client
        client.max_retries=0
        transport=client._client;transport.follow_redirects=False
        for kind,hook in [('request',request_hook),('response',response_hook)]:
            hooks=transport.event_hooks.setdefault(kind,[])
            if hook not in hooks:hooks.append(hook)
        original=client.chat.completions.create
        @functools.wraps(original)
        def create(*args,**kwargs):
            seen=False
            def observe(value):
                nonlocal seen
                model=getattr(value,'model',None)
                if model is not None:
                    if not isinstance(model,str) or model.casefold()!=MODEL:
                        state['failed_response']=True
                        raise GuardError('returned_model_mismatch')
                    if not seen:
                        seen=True
                        with lock:state['returned_model_verified_requests']+=1
                return value
            class ObservedStream:
                def __init__(self,stream):self.stream=stream
                def __getattr__(self,name):return getattr(self.stream,name)
                def __iter__(self):
                    try:
                        for chunk in self.stream:yield observe(chunk)
                    except Exception:
                        state['failed_response']=True
                        raise
                def __enter__(self):return self
                def __exit__(self,*unused):self.stream.close()
            try:
                result=original(*args,**kwargs)
                return ObservedStream(result) if kwargs.get('stream') else observe(result)
            except Exception:
                state['failed_response']=True
                raise
            finally:boundary.admit(False)
        client.chat.completions.create=create
        client._ec_zai_qualification_guard=state
        return client
    factory=agent._create_openai_client
    def guarded_factory(*args,**kwargs):return install(factory(*args,**kwargs))
    agent._create_openai_client=guarded_factory
    install(agent.client)
    cache=getattr(agent,'_request_client_cache',None)
    if isinstance(cache,dict) and cache.get('client') is not None:install(cache['client'])
    return state
