"""One finite native ZAI capture/recall test in a NEW invented scope.

Repeating launch attaches to the retained job; it never repeats model turns.
Only ordinary model/API credentials cross owner pipes. No root keys, private
profile contents, prompts or model replies enter output or evidence. Existing
profiles, launchers, records, admission policies and completed tests are retained.
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
ARTIFACT=BASE/'operator-current-model-native-v1'
RELEASE=Path('/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1')
PROVIDER=Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659')
FIXTURES=Path('/var/lib/hermes-renewal-qualification')
UNIT='ec-launch-current-model-native-20261027.service'
GUARD_SHA='1f579b3cbf88b5b922f3e0ff2cda345e496c639fdec79600bb3b92e3e90f5cde'
OBSERVER_SHA='2488f9255af9cefd9230a22eae062c49c845e7a57c366da628937f2a50e7af27'
PINS={
    'zai_native_qualification_guard.py':GUARD_SHA,
    'observe_launch_native_runtime.py':OBSERVER_SHA,
    'bind_launch_model_route.py':'edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52',
    'qualify_launch_isolated_accounts.py':'d0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94',
    'recover_launch_graph_operator.py':'d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef',
    'qualify_launch_gateway_renewal_v2.py':'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2',
}
PHASE='identity'
PHASES={'identity','fixture','imports','scope','agent','native_turn','verification','cleanup'}
SAFE_KINDS={'ValueError','GuardError','PermissionError','FileNotFoundError','AuthError','TimeoutExpired','RuntimeError'}
PHYSICAL={'capture':6,'recall':6}
OBSERVATION={}


def require(value):
    if not value:raise ValueError('current_model_qualification_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes()
    require(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    namespace={'__name__':'verified_current_model_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-public-current-model-support>','exec'),namespace)
    return namespace


def identity(ident,peer=False):
    require(isinstance(ident,str) and re.fullmatch('[a-f0-9]{32}',ident))
    suffix=('zai_peer_' if peer else 'zai_')+ident
    return dict(sub=suffix,agent_id=suffix,tenant='qualification',project_id=suffix,
        roles=['api_client'],capture_policy='selected')


def packet_shape(packet):
    require(isinstance(packet,dict) and set(packet)=={'stage','run_id','key','token','peer','guard','observer','record_id'}
        and packet['stage'] in {'capture','recall'} and re.fullmatch('[a-f0-9]{32}',packet['run_id'])
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
    profile=FIXTURES/('zai_model_'+packet['run_id'])
    info=profile.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid==account.pw_uid and stat.S_IMODE(info.st_mode)==0o700)
    os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME=str(profile),HERMES_HOME=str(profile),
        GLM_API_KEY=packet['key'],GLM_BASE_URL='https://open.bigmodel.cn/api/paas/v4',
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
    if packet['stage']=='capture':
        require(not list(profile.iterdir()))
        private_create(profile/'.env',('GLM_API_KEY='+packet['key']+'\nGLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4\n'
            +'ENHANCED_COGNEE_ACCESS_TOKEN='+packet['token']+'\n').encode())
        private_create(profile/'config.yaml',b'model:\n  provider: zai\n  default: glm-5.3-flash\n  base_url: https://open.bigmodel.cn/api/paas/v4\nmemory:\n  provider: enhanced_cognee\n')
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
        PHASE='scope'
        from hermes_cli.runtime_provider import frozen_runtime_config,resolve_runtime_provider
        import yaml
        with frozen_runtime_config(yaml.safe_load(preserved['config.yaml'])):
            runtime=resolve_runtime_provider(requested='zai',target_model=guard['MODEL'])
        require(runtime.get('api_key')==packet['key'] and runtime.get('base_url','').rstrip('/')==guard['BASE_URL'])
        # Initialize this NEW fixture's native auth schema before comparing
        # bounded usage bookkeeping. Existing profiles are never normalized.
        if packet['stage']=='capture':preserved['auth.json']=(profile/'auth.json').read_bytes()
        require(loader.find_provider_dir('enhanced_cognee').resolve()==PROVIDER)
        provider=loader.load_memory_provider('enhanced_cognee')
        require(Path(sys.modules[type(provider).__module__].__file__).resolve()==PROVIDER/'__init__.py')
        session='zai_'+packet['stage']+'_'+packet['run_id']
        manager=MemoryManager();manager.add_provider(provider)
        manager.initialize_all(session,hermes_home=str(profile),agent_context='primary',platform='cli')
        raw,state=guard_memory(provider,packet,boundary)
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
        value=dict(complete=False,phase=PHASE,error_kind=kind if kind in SAFE_KINDS else 'other',observation=OBSERVATION)
    print(json.dumps(value),flush=True)
    if not value.get('complete'):raise SystemExit(1)


def owner(helper,source,account,packet):
    packet_shape(packet)
    code,line=helper['owner_program'](source)
    frame=canonical(packet);require(len(frame)<=65536)
    process=subprocess.run(['/usr/bin/setpriv','--no-new-privs','--',helper['EXECUTABLE'],'-I','-B','-c',code],
        input=line+frame+b'\n',stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=180,cwd='/',
        user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={'PATH':'/usr/bin:/bin','HOME':account.pw_dir,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    require(0<len(process.stdout)<=8192)
    value=json.loads(process.stdout)
    validate_result(value,packet['stage'])
    return value


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
        require(set(value)=={'complete','phase','error_kind','observation'} and value['phase'] in PHASES
            and value['error_kind'] in SAFE_KINDS|{'other'} and isinstance(value['observation'],dict)
            and set(value['observation']) in (set(),{'stage','requests','network'},{'stage','requests','network','files_equal'}))
        observation=value['observation']
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


def properties():
    result=subprocess.run(['/usr/bin/systemctl','show',UNIT,'--property=LoadState,ActiveState,SubState,MainPID,ControlPID'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True)
    require(len(result.stdout)<=8192)
    return dict(line.split('=',1) for line in result.stdout.decode().splitlines() if '=' in line)


def quiescent(value):
    return value.get('ActiveState') in {'inactive','failed'} and value.get('MainPID')==value.get('ControlPID')=='0'


def worker(read,write):
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    context=json.loads(read(ARTIFACT/'context.json',0));ident=context['run_id'];identity(ident)
    evidence=Path(context['evidence'])
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('current-model-native-[A-Za-z0-9_-]{6,64}',evidence.name))
    helper=definitions(ARTIFACT/'qualify_launch_isolated_accounts.py',PINS['qualify_launch_isolated_accounts.py'])
    route=definitions(ARTIFACT/'bind_launch_model_route.py',PINS['bind_launch_model_route.py'])
    native=definitions(ARTIFACT/'qualify_launch_gateway_renewal_v2.py',PINS['qualify_launch_gateway_renewal_v2.py'])
    for name,digest in native['NATIVE'].items():require(hashlib.sha256((RELEASE/'repo'/name).read_bytes()).hexdigest()==digest)
    for name,digest in native['PROVIDER_FILES'].items():require(hashlib.sha256((PROVIDER/name).read_bytes()).hexdigest()==digest)
    policies=[Path('/etc/enhanced-cognee/fleet-credentials.json'),BASE/'operator-isolated-issuer-candidate-v3/candidate-policy.json']
    before={path:read(path,0) for path in policies}
    require(all(row['enabled'] is False for raw in before.values() for row in json.loads(raw)['profiles']))
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,new_invented_scope=ident,
        source_profiles_changed=False,existing_launchers_changed=False,private_keys_sent_to_owner=False,
        credentials_issued=0,production_renewal_timer_enabled=False,actual_profile_admission_qualified=False,
        maximum_context_verified=False,fleet_launch_approved=False,automatic_model_retry=False,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(evidence/'started.json',canonical(result));phase='preflight'
    try:
        _,_,authority=route['prepare']((ARTIFACT/'bind_launch_model_route.py').read_bytes(),definitions)
        require(authority['endpoint_path']=='/api/paas/v4')
        issuer=definitions(BASE/'operator-issuer-candidate-v2/provision_pilot_access.py',
            'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6')
        key=issuer['load_signing_key']();now=int(time.time())
        ordinary=[issuer['sign_claims'](dict(identity(ident,peer),iat=now,exp=now+1200),key) for peer in (False,True)]
        del key;result['credentials_issued']=2
        guard=(ARTIFACT/'zai_native_qualification_guard.py').read_bytes()
        require(hashlib.sha256(guard).hexdigest()==GUARD_SHA)
        observer=(ARTIFACT/'observe_launch_native_runtime.py').read_bytes()
        require(hashlib.sha256(observer).hexdigest()==OBSERVER_SHA)
        packet=dict(stage='capture',run_id=ident,key=authority['key'],token=ordinary[0],peer=ordinary[1],
            guard=guard.decode(),observer=observer.decode(),record_id=None)
        account=pwd.getpwnam('hermes-runtime');source=Path(__file__).read_bytes()
        for stage in ('capture','recall'):
            phase=stage;packet['stage']=stage
            write(evidence/(stage+'.started.json'),canonical(dict(stage=stage,automatic_retry=False)))
            value=owner(helper,source,account,packet)
            write(evidence/(stage+'.summary.json'),canonical(value))
            require(value.get('complete') is True)
            if stage=='capture':packet['record_id']=value['record_id']
        result.update(complete=True,current_configured_model_native_capture_qualified=True,
            current_configured_model_fresh_process_recall_qualified=True,invented_sensitive_input_excluded=True,
            invented_record_retracted_history_preserved=True,model_route='zai/glm-5.3-flash',
            physical_model_request_limit=12,separate_native_processes=2)
    except Exception as error:
        result.update(category='current_model_native_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase,
            error_kind=type(error).__name__ if type(error).__name__ in SAFE_KINDS else 'other')
    require(all(read(path,0)==raw for path,raw in before.items()))
    result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result));sync(evidence)
    return 0 if result['complete'] else 1


def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def watch(read):
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence']);last=0
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('current-model-native-[A-Za-z0-9_-]{6,64}',evidence.name))
    try:
        while True:
            value=properties()
            try:result=json.loads(read(evidence/'summary.json',0))
            except FileNotFoundError:result=None
            if result is not None or value.get('ActiveState')=='failed' or value.get('SubState')=='exited':
                result=result or dict(complete=False,evidence=str(evidence),category='current_model_worker_exited_preserve_evidence')
                if not quiescent(value):
                    subprocess.run(['/usr/bin/systemctl','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=True)
                result['operator_job_stopped']=quiescent(properties())
                result['complete']=result.get('complete') is True and result['operator_job_stopped']
                print(json.dumps(result),flush=True);return 0 if result['complete'] else 1
            if quiescent(value):
                print(json.dumps(dict(complete=False,evidence=str(evidence),category='current_model_job_not_running_preserve_evidence')),flush=True);return 1
            if time.monotonic()-last>=15:
                print('{"event":"current_model_native_running","note":"Ctrl+C detaches; repeat qualify-current-model to reattach without repeating model turns."}',flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True,job_continues=True,evidence=str(evidence))),flush=True);return 0


def launch():
    require(os.geteuid()==0)
    directory=Path(__file__).parent
    shared=definitions(directory/'recover_launch_graph_operator.py',PINS['recover_launch_graph_operator.py'])
    read,write=shared['read_file'],shared['private_write']
    if os.path.lexists(ARTIFACT):return watch(read)
    require(properties().get('LoadState')=='not-found' and quiescent(properties()))
    # Retain both completed batches as preconditions; never call their workers.
    main=json.loads(read(BASE/'operator-evidence/main-operational-recovery-0xjyrv2b/summary.json',0))
    named=json.loads(read(BASE/'operator-evidence/named-runtime-routes-ivk3f5hw/summary.json',0))
    require(main.get('complete') is True and main.get('main_operational_snapshot_restore_qualified') is True
        and named.get('complete') is True and named.get('qualified_profiles')==40 and named.get('failed_profiles')==0)
    driver=definitions(BASE/'operator-issuer-candidate-v2/renew_fleet_credentials.py',
        'a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    driver['protected'](FIXTURES)
    native=definitions(directory/'qualify_launch_gateway_renewal_v2.py',PINS['qualify_launch_gateway_renewal_v2.py'])
    for name in native['NATIVE']:driver['protected'](RELEASE/'repo'/name)
    for name in native['PROVIDER_FILES']:driver['protected'](PROVIDER/name)
    account=pwd.getpwnam('hermes-runtime');require(account.pw_uid>0)
    ident=uuid.uuid4().hex;profile=FIXTURES/('zai_model_'+ident)
    profile.mkdir(mode=0o700);os.chown(profile,account.pw_uid,account.pw_gid)
    sources={Path(__file__).name:globals()['_verified_source_bytes']}
    for name,digest in PINS.items():sources[name]=definitions(directory/name,digest)['_verified_source_bytes']
    evidence=Path(tempfile.mkdtemp(prefix='current-model-native-',dir=BASE/'operator-evidence'))
    ARTIFACT.mkdir(mode=0o700)
    for name,raw in sources.items():write(ARTIFACT/name,raw)
    write(ARTIFACT/'sources.json',canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}))
    write(ARTIFACT/'context.json',canonical(dict(evidence=str(evidence),run_id=ident)));sync(ARTIFACT)
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='',ProtectHome='no',ProtectSystem='strict',
        PrivateTmp='no',ReadWritePaths=str(BASE/'operator-evidence')+' '+str(profile),
        Restart='no',TimeoutStartSec='480',MemoryMax='2G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+k+'='+v for k,v in settings.items()]
    args += [str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/Path(__file__).name),'--worker']
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=True)
    return watch(read)


if __name__=='__main__':
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        require(sys.argv[1:]==['--worker'])
        shared=definitions(ARTIFACT/'recover_launch_graph_operator.py',PINS['recover_launch_graph_operator.py'])
        raise SystemExit(worker(shared['read_file'],shared['private_write']))
    except Exception:
        print('{"complete":false,"category":"current_model_native_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
