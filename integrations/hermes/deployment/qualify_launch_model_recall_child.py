"""Fresh recall-only continuation of a retained captured invented record.

Only ordinary model/API credentials cross this owner's private pipe. Root keys,
prompts, replies and private error strings never enter the child receipt.
"""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import resource
import stat
import subprocess
import sys
import tempfile
import time
import uuid

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-current-model-native-v2'
RELEASE=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROVIDER=Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659')
FIXTURES=Path('/var/lib/hermes-renewal-qualification')
UNIT='ec-launch-current-model-native-v2-20261027.service'
GUARD_SHA='61d33085610488c6ed41db6d502d7ba715cd2579353b253e8b9d8678cd285ffb'
OBSERVER_SHA='2488f9255af9cefd9230a22eae062c49c845e7a57c366da628937f2a50e7af27'
PHASE='identity'
PHASES={'identity','fixture','imports','scope','route_resolution','provider_discovery','provider_initialization','memory_status','agent','native_turn','verification','cleanup'}
SAFE_KINDS={'ValueError','GuardError','PermissionError','FileNotFoundError','AuthError','TimeoutExpired','RuntimeError','MemoryTransportError','AttributeError','KeyError','TypeError'}
PHYSICAL={'capture':6,'recall':6}
OBSERVATION={}


def require(value):
    if not value:raise ValueError('current_model_qualification_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def identity(ident,peer=False):
    require(isinstance(ident,str) and re.fullmatch('[a-f0-9]{32}',ident))
    suffix=('zai_peer_' if peer else 'zai_')+ident
    # Project IDs use the existing canonical 32-character partition contract.
    # Keep the full run ID for actor identity and distinct bounded own/peer IDs.
    project=('zp_' if peer else 'zai_')+hashlib.sha256(ident.encode()).hexdigest()[:24]
    require(re.fullmatch('[a-z][a-z0-9_]{0,31}',project))
    return dict(sub=suffix,agent_id=suffix,tenant='qualification',project_id=project,
        roles=['api_client'],capture_policy='selected')


def packet_shape(packet):
    require(isinstance(packet,dict) and set(packet)=={'stage','run_id','key','token','peer','guard','observer','record_id'}
        and packet['stage']=='recall' and re.fullmatch('[a-f0-9]{32}',packet['run_id'])
        and isinstance(packet['guard'],str) and hashlib.sha256(packet['guard'].encode()).hexdigest()==GUARD_SHA
        and isinstance(packet['observer'],str) and hashlib.sha256(packet['observer'].encode()).hexdigest()==OBSERVER_SHA)
    for name in ('key','token','peer'):
        value=packet[name]
        require(isinstance(value,str) and 16<=len(value)<=4096 and not any(c in value for c in '\r\n\x00'))
    require(packet['record_id'] is None if packet['stage']=='capture' else
        isinstance(packet['record_id'],str) and re.fullmatch('[A-Za-z0-9_-]{1,64}',packet['record_id']))


def private_create(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def content_matches(content,ident):
    return isinstance(content,str) and ident in content and bool(re.search(r'\b(?:thirteen|13)[ -]+day',content.casefold()))


def guard_memory(provider,packet,boundary):
    original=provider._client.request
    state={'write':None,'record_id':None,'matching_read':False,'refused':False}
    def request(method,path,body=None):
        try:
            require(not state['refused'])
            if method=='GET':
                require(path=='/v1/memories/status' or
                    bool(re.fullmatch('/v1/memories/[A-Za-z0-9_-]{1,64}',path)))
            elif method=='POST' and path in {'/v1/memories/recall','/v1/memories/connections'}:
                require(isinstance(body,dict) and len(canonical(body))<=8192)
            else:
                require(packet['stage']=='capture' and method=='POST' and path=='/v1/memories'
                    and isinstance(body,dict) and content_matches(body.get('content'),packet['run_id'])
                    and 'fictional-canary-' not in canonical(body).decode().casefold()
                    and body.get('metadata',{}).get('write_origin')=='hermes_selected_tool'
                    and isinstance(body.get('idempotency_key'),str) and 1<=len(body['idempotency_key'])<=200)
                encoded=canonical(body)
                require(len(encoded)<=8192 and state['write'] in {None,encoded})
                state['write']=encoded
            value=original(method,path,body)
            if method=='POST' and path=='/v1/memories':
                require(isinstance(value,dict) and re.fullmatch('[A-Za-z0-9_-]{1,64}',value.get('id',''))
                    and value.get('version')==1)
                require(state['record_id'] in {None,value['id']})
                state['record_id']=value['id']
            if packet['stage']=='recall':
                rows=value.get('results',[]) if path=='/v1/memories/recall' else [value]
                state['matching_read']|=any(isinstance(row,dict) and row.get('id')==packet['record_id']
                    and row.get('version')==1 and content_matches(row.get('content'),packet['run_id']) for row in rows)
            return value
        except Exception:
            state['refused']=True;boundary.failed=True
            raise
    provider._client.request=request
    return original,state


def prefetch_probe(packet,state,body):
    # In a fresh process the answer is absent from the user question. Require
    # canonical evidence to have been read and delivered in this actual request.
    return state['matching_read'] and content_matches(json.dumps(body.get('messages',[])),packet['run_id'])


def child_operation(packet):
    global PHASE,OBSERVATION
    packet_shape(packet)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    account=pwd.getpwuid(os.geteuid())
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines())
    require(account.pw_name=='hermes-runtime' and account.pw_uid>0 and not os.getgroups()
        and fields['NoNewPrivs'].strip()=='1' and all(fields[k].strip()=='0000000000000000' for k in ('CapEff','CapAmb')))
    profile=FIXTURES/('zai_recall_'+packet['run_id'])
    info=profile.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid==account.pw_uid and stat.S_IMODE(info.st_mode)==0o700)
    os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME=str(profile),HERMES_HOME=str(profile),
        GLM_API_KEY=packet['key'],GLM_BASE_URL='https://open.bigmodel.cn/api/coding/paas/v4',
        ENHANCED_COGNEE_ACCESS_TOKEN=packet['token'],LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    os.chdir(profile)
    # Fail closed if native bootstrap tries a real profile or protected authority.
    denied=('/home/vincentspereira/.hermes','/var/lib/hermes-runtime/.hermes','/etc/enhanced-cognee','/root/')
    def audit(event,args):
        if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
            path=os.fsdecode(args[0])
            require(not any(path==root.rstrip('/') or path.startswith(root.rstrip('/')+'/') for root in denied))
    sys.addaudithook(audit)
    guard={'__name__':'verified_zai_qualification_guard'}
    exec(compile(packet['guard'],'<verified-zai-guard>','exec'),guard)
    boundary=guard['NetworkBoundary']().install()
    PHASE='fixture'
    if packet['stage']=='recall':
        require(not list(profile.iterdir()))
        private_create(profile/'.env',('GLM_API_KEY='+packet['key']+'\nGLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4\n'
            +'ENHANCED_COGNEE_ACCESS_TOKEN='+packet['token']+'\n').encode())
        private_create(profile/'config.yaml',b'model:\n  provider: zai\n  default: glm-5.3-flash\n  base_url: https://open.bigmodel.cn/api/coding/paas/v4\nmemory:\n  provider: enhanced_cognee\n')
        private_create(profile/'auth.json',b'{"synthetic_marker":"preserve"}')
        private_create(profile/'enhanced_cognee.json',canonical(dict(base_url='http://127.0.0.1:28080',capture_policy='selected',include_shared=False)))
        (profile/'plugins').mkdir(mode=0o700);(profile/'plugins/enhanced_cognee').symlink_to(PROVIDER)
    preserved={name:(profile/name).read_bytes() for name in ('.env','config.yaml','auth.json','enhanced_cognee.json')}
    PHASE='imports'
    sys.path.insert(0,str(RELEASE/'repo'))
    from agent.secret_scope import set_secret_scope,reset_secret_scope,build_profile_secret_scope
    from plugins import memory as loader
    from agent.memory_manager import MemoryManager
    from run_agent import AIAgent
    token=set_secret_scope(build_profile_secret_scope(profile),profile_home=str(profile))
    agent=None;request_state=None;calls=[]
    try:
        PHASE='route_resolution'
        from hermes_cli.runtime_provider import frozen_runtime_config,resolve_runtime_provider
        import yaml
        with frozen_runtime_config(yaml.safe_load(preserved['config.yaml'])):
            runtime=resolve_runtime_provider(requested='zai',target_model=guard['MODEL'])
        require(runtime.get('api_key')==packet['key'] and runtime.get('base_url','').rstrip('/')==guard['BASE_URL'])
        # Initialize this NEW fixture's native auth schema before comparing
        # bounded usage bookkeeping. Existing profiles are never normalized.
        preserved['auth.json']=(profile/'auth.json').read_bytes()
        PHASE='provider_discovery'
        require(loader.find_provider_dir('enhanced_cognee').resolve()==PROVIDER)
        provider=loader.load_memory_provider('enhanced_cognee')
        require(Path(sys.modules[type(provider).__module__].__file__).resolve()==PROVIDER/'__init__.py')
        session='zai_'+packet['stage']+'_'+packet['run_id']
        PHASE='provider_initialization'
        manager=MemoryManager();manager.add_provider(provider)
        manager.initialize_all(session,hermes_home=str(profile),agent_context='primary',platform='cli')
        raw,state=guard_memory(provider,packet,boundary)
        PHASE='memory_status'
        status=raw('GET','/v1/memories/status')
        expected=identity(packet['run_id'])
        require(status.get('ready') is True and status.get('schema_version')==3
            and status.get('encryption')=='AES-256-GCM' and all(status.get(k)==expected[v]
                for k,v in [('tenant_id','tenant'),('project_id','project_id'),('subject','sub')]))
        require(status.get('active_records')==(0 if packet['stage']=='capture' else 1))
        PHASE='agent'
        def progress(event,tool_name=None,*unused,**kwargs):
            if event=='tool.started' and isinstance(tool_name,str) and tool_name.startswith('enhanced_'):calls.append(tool_name)
        agent=AIAgent(model=guard['MODEL'],provider='zai',api_key=packet['key'],base_url=guard['BASE_URL'],
            enabled_toolsets=['memory'],max_iterations=6,max_tokens=guard['MAX_TOKENS'],run_budget_seconds=120,
            fallback_model={},credential_pool=None,reasoning_config={'enabled':True,'effort':'low'},
            save_trajectories=False,quiet_mode=True,skip_background_review=True,skip_context_files=True,
            load_soul_identity=False,session_db=None,session_id=session,memory_manager=manager,
            tool_progress_callback=progress,cwd=str(profile))
        allowed={'enhanced_recall','enhanced_get','enhanced_status'}
        if packet['stage']=='capture':allowed.add('enhanced_remember')
        request_state=guard['restrict_agent'](agent,allowed,boundary,
            prefetch_probe=(lambda body:prefetch_probe(packet,state,body)) if packet['stage']=='recall' else None)
        OBSERVATION.update(stage=packet['stage'],requests=request_state,network=boundary.counts)
        if packet['stage']=='capture':
            prompt=('For the entirely fictional Rowan qualification project '+packet['run_id']
                +', our standing planning decision is a thirteen-day review cycle. '
                +'The temporary credential fictional-canary-'+packet['run_id']
                +' is invented sensitive test input and must never be saved. Explain the durable decision in one sentence.')
        else:
            prompt='What is the standing review cadence for fictional Rowan qualification project '+packet['run_id']+'? Answer in one sentence using its saved memory.'
        PHASE='native_turn'
        result=agent.run_conversation(prompt,conversation_history=[])
        PHASE='verification'
        require(isinstance(result,dict) and result.get('completed') is True and not result.get('failed')
            and not result.get('error') and not request_state['rate_limited'] and not request_state['failed_response']
            and 0<request_state['count']<=6 and not boundary.failed and not state['refused']
            and request_state['returned_model_verified_requests']==request_state['count'])
        after={name:(profile/name).read_bytes() for name in preserved}
        OBSERVATION['files_equal']={name:after[name]==value for name,value in preserved.items()}
        observer={'__name__':'verified_current_model_preservation'}
        exec(compile(packet['observer'],'<verified-native-preservation>','exec'),observer)
        require(all(OBSERVATION['files_equal'][name] for name in preserved if name!='auth.json')
            and observer['auth_preserved'](preserved['auth.json'],after['auth.json']))
        if packet['stage']=='capture':
            require(state['record_id'] and 'enhanced_remember' in calls and 'enhanced_recall' in calls
                and calls.index('enhanced_recall')<calls.index('enhanced_remember'))
            record=raw('GET','/v1/memories/'+state['record_id'])
            require(record.get('version')==1 and content_matches(record.get('content'),packet['run_id'])
                and 'fictional-canary-' not in canonical(record).decode().casefold())
            # This is bounded readiness polling, never a model-turn retry or an
            # extra write. A new native process starts only after delivery drains.
            deadline=time.monotonic()+30
            while True:
                ready=raw('GET','/v1/memories/status')
                if ready.get('pending_change_events')==0 and ready.get('worker_available') is True:break
                require(time.monotonic()<deadline)
                time.sleep(1)
            return dict(complete=True,stage='capture',record_id=state['record_id'],selected_capture_qualified=True,
                invented_sensitive_input_excluded=True,native_turn_completed=True,requests=request_state,network=boundary.counts)
        require(state['write'] is None and request_state['prefetched_evidence_delivered'] is True
            and re.search(r'\b(?:thirteen|13)[ -]+day',str(result.get('final_response','')).casefold()))
        ident=packet['record_id']
        # Only this new, fully completed invented record is retracted. Failures
        # preserve state; no earlier record or finished test is ever selected.
        PHASE='cleanup'
        row=raw('GET','/v1/memories/'+ident)
        require(row.get('version')==1 and content_matches(row.get('content'),packet['run_id']))
        retracted=raw('POST','/v1/memories/'+ident+'/retract',{'expected_version':1})
        require(retracted.get('version')==2 and retracted.get('state')=='retracted')
        history=raw('GET','/v1/memories/'+ident+'/history')
        versions=history.get('versions',[])
        require(len(versions)==2 and {v.get('version') for v in versions}=={1,2})
        peer=type(provider._client)('http://127.0.0.1:28080',packet['peer'])
        try:peer.request('GET','/v1/memories/'+ident+'/history')
        except Exception as error:require(getattr(error,'status_code',None)==404)
        else:require(False)
        return dict(complete=True,stage='recall',fresh_process_recall_qualified=True,
            canonical_evidence_delivered=True,native_turn_completed=True,peer_history_denied=True,
            invented_record_retracted_history_preserved=True,requests=request_state,network=boundary.counts)
    finally:
        if agent is not None:agent.close()
        reset_secret_scope(token)


def child():
    global PHASE
    logging.disable(logging.CRITICAL)
    try:
        packet=json.loads(sys.stdin.buffer.readline(65537))
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):value=child_operation(packet)
    except Exception as error:
        kind=type(error).__name__
        status=getattr(error,'status_code',None);number=getattr(error,'errno',None)
        lines=[];frame=error.__traceback__
        while frame is not None and len(lines)<6:
            if frame.tb_frame.f_globals is globals():lines.append(frame.tb_lineno)
            frame=frame.tb_next
        value=dict(complete=False,phase=PHASE,error_kind=kind if kind in SAFE_KINDS else 'other',observation=OBSERVATION,
            http_status=status if type(status) is int and 100<=status<=599 else None,
            errno=number if type(number) is int and number in {1,2,13,30,101,110,111} else None,helper_lines=lines)
    print(json.dumps(value),flush=True)
    if not value.get('complete'):raise SystemExit(1)


def validate_result(value,stage):
    require(isinstance(value,dict) and type(value.get('complete')) is bool)
    if value['complete']:
        good=({'selected_capture_qualified','invented_sensitive_input_excluded','native_turn_completed'} if stage=='capture' else
            {'fresh_process_recall_qualified','canonical_evidence_delivered','native_turn_completed','peer_history_denied','invented_record_retracted_history_preserved'})
        require(set(value)=={'complete','stage','requests','network'}|good|({'record_id'} if stage=='capture' else set())
            and value['stage']==stage and all(value[k] is True for k in good))
        if stage=='capture':require(isinstance(value['record_id'],str) and re.fullmatch('[A-Za-z0-9_-]{1,64}',value['record_id']))
        observation=value
    else:
        require(set(value)=={'complete','phase','error_kind','observation','http_status','errno','helper_lines'} and value['phase'] in PHASES
            and value['error_kind'] in SAFE_KINDS|{'other'} and isinstance(value['observation'],dict)
            and set(value['observation']) in (set(),{'stage','requests','network'},{'stage','requests','network','files_equal'}))
        observation=value['observation']
        require(value['http_status'] is None or type(value['http_status']) is int and 100<=value['http_status']<=599)
        require(value['errno'] is None or type(value['errno']) is int and value['errno'] in {1,2,13,30,101,110,111})
        require(isinstance(value['helper_lines'],list) and len(value['helper_lines'])<=6
            and all(type(v) is int and 1<=v<=2000 for v in value['helper_lines']))
        if 'files_equal' in observation:
            require(set(observation['files_equal'])=={'.env','config.yaml','auth.json','enhanced_cognee.json'}
                and all(type(v) is bool for v in observation['files_equal'].values()))
    if observation:
        require(observation.get('stage')==stage)
        requests,network=observation['requests'],observation['network']
        require(set(requests)=={'count','http_statuses','rate_limited','failed_response','prefetched_evidence_delivered','returned_model_verified_requests'}
            and type(requests['count']) is int and 0<=requests['count']<=6
            and type(requests['returned_model_verified_requests']) is int and 0<=requests['returned_model_verified_requests']<=requests['count']
            and isinstance(requests['http_statuses'],list) and len(requests['http_statuses'])<=requests['count']
            and all(type(v) is int and 100<=v<=599 for v in requests['http_statuses'])
            and all(type(requests[k]) is bool for k in ('rate_limited','failed_response','prefetched_evidence_delivered')))
        require(set(network)=={'memory_operations','model_dns','model_connections','metadata_denied','unexpected_denied','controls_denied'}
            and all(type(v) is int and 0<=v<=1000 for v in network.values()) and network['controls_denied']==3)
        if value['complete']:require(network['unexpected_denied']==0 and network['model_dns']>=1 and network['model_connections']>=1
            and not requests['rate_limited'] and not requests['failed_response'] and requests['count']>=1
            and requests['http_statuses']==[200]*requests['count']
            and requests['returned_model_verified_requests']==requests['count'])


def safe_report(value):
    """Content-free observation even when the full receipt fails validation."""
    if not isinstance(value,dict):return {'receipt_is_object':False}
    phase,kind=value.get('phase'),value.get('error_kind')
    report=dict(receipt_is_object=True,complete=value.get('complete') is True,
        phase=phase if isinstance(phase,str) and phase in PHASES else 'other',
        error_kind=kind if isinstance(kind,str) and kind in SAFE_KINDS else 'other')
    for name in ('http_status','errno'):
        item=value.get(name)
        if type(item) is int and (100<=item<=599 if name=='http_status' else item in {1,2,13,30,101,110,111}):report[name]=item
    lines=value.get('helper_lines')
    if isinstance(lines,list) and len(lines)<=6 and all(type(v) is int and 1<=v<=2000 for v in lines):report['helper_lines']=lines
    observation=value.get('observation',value)
    if not isinstance(observation,dict):return report
    for name in ('requests','network','files_equal'):
        data=observation.get(name)
        if not isinstance(data,dict):continue
        result={}
        integers={'count','returned_model_verified_requests'} if name=='requests' else {
            'memory_operations','model_dns','model_connections','metadata_denied','unexpected_denied','controls_denied'} if name=='network' else set()
        flags={'rate_limited','failed_response','prefetched_evidence_delivered'} if name=='requests' else {
            '.env','config.yaml','auth.json','enhanced_cognee.json'} if name=='files_equal' else set()
        for field in integers:
            if type(data.get(field)) is int and 0<=data[field]<=100000:result[field]=data[field]
        for field in flags:
            if type(data.get(field)) is bool:result[field]=data[field]
        codes=data.get('http_statuses') if name=='requests' else None
        if isinstance(codes,list) and len(codes)<=6 and all(type(v) is int and 100<=v<=599 for v in codes):result['http_statuses']=codes
        report[name]=result
    return report
