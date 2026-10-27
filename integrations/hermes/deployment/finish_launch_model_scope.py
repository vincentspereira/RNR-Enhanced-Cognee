"""Finish retained native capture after the corrected read-only delivery gate.

No capture replay, new remember call or completed-record replay is admitted.
Only fresh-process recall and exact invented-record retraction can run.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import subprocess
import sys
import tempfile
import time

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-model-recall-finish-v1'
PREVIOUS=BASE/'operator-evidence/current-model-native-ydgaddnq'
PREVIOUS_ARTIFACT=BASE/'operator-current-model-native-v3'
IDENT='b5ceda49da6343159db0687cd0529045'
UNIT='ec-launch-model-recall-finish-20261027.service'
FIXTURES=Path('/var/lib/hermes-renewal-qualification')
CHILD_NAME='qualify_launch_model_recall_child.py'
CHILD_SHA='29903d0cc30b937c9e76ac6aa90ffee8f329d351167142b1ebdf6c3f53b8abb1'
DRIVER_SHA='3d8c9d76fe19067289cf53d9587308b315cb23987a41b3db966f2f08a13b1c63'
CAPTURE_SHA='68e4cee48692fd5759a705153045f489b1d13f87cb41b0699cac1daf99bf7bf4'
SUPPORT_SHA='d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
PINS={CHILD_NAME:CHILD_SHA,
    'model_delivery_readiness.py':'1352ab6d2148b169bfdf9c72f3fca4e19ce878d292e0d889d4fffd86ed850eed',
    'bind_launch_model_route.py':'edf8349fd53f88b7570c608e28533adef707f5ff8d8b4e4d7a0c03433670dd52',
    'qualify_launch_current_model_v3.py':DRIVER_SHA,
    'recover_launch_graph_operator.py':SUPPORT_SHA,
    'qualify_launch_gateway_renewal_v2.py':'a2ce8eb144aaf4fd3e040b6a7436d2561c4bb12f9e6d7eda41aec8b59d9bdfe2',
    'zai_native_qualification_guard_v2.py':'61d33085610488c6ed41db6d502d7ba715cd2579353b253e8b9d8678cd285ffb',
    'observe_launch_native_runtime.py':'2488f9255af9cefd9230a22eae062c49c845e7a57c366da628937f2a50e7af27'}


def require(value):
    if not value:raise ValueError('current_model_qualification_refused')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()


def definitions(path,digest):
    raw=path.read_bytes()
    require(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==digest)
    namespace={'__name__':'verified_current_model_support','__file__':str(path),'_verified_source_bytes':raw}
    exec(compile(raw,'<verified-public-current-model-support>','exec'),namespace)
    return namespace


def properties(unit=None):
    result=subprocess.run(['/usr/bin/systemctl','show',unit or UNIT,'--property=LoadState,ActiveState,SubState,MainPID,ControlPID'],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True)
    require(len(result.stdout)<=8192)
    return dict(line.split('=',1) for line in result.stdout.decode().splitlines() if '=' in line)


def quiescent(value):
    return value.get('ActiveState') in {'inactive','failed'} and value.get('MainPID')==value.get('ControlPID')=='0'


def sync(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def watch(read):
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence']);last=0
    require(evidence.parent==BASE/'operator-evidence' and re.fullmatch('model-recall-finish-[A-Za-z0-9_-]{6,64}',evidence.name))
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
                print('{"event":"current_model_native_running","note":"Ctrl+C detaches; repeat finish-model-scope to reattach without repeating model turns."}',flush=True);last=time.monotonic()
            time.sleep(2)
    except KeyboardInterrupt:
        print(json.dumps(dict(detached=True,job_continues=True,evidence=str(evidence))),flush=True);return 0


def retained_capture(read):
    """Pinned checkpoint is AFTER completed turn, selection and privacy checks."""
    value=json.loads(read(PREVIOUS/'summary.json',0))
    require(value.get('complete') is False and value.get('failure_phase')=='capture'
        and value.get('new_invented_scope')==IDENT and value.get('operator_helper_sha256')==DRIVER_SHA
        and value.get('all_admission_policies_preserved_disabled') is True and value.get('credentials_issued')==2)
    context=json.loads(read(PREVIOUS_ARTIFACT/'context.json',0))
    require(context.get('evidence')==str(PREVIOUS) and context.get('run_id')==IDENT)
    require(hashlib.sha256(read(PREVIOUS_ARTIFACT/'qualify_launch_current_model_v3.py',0)).hexdigest()==DRIVER_SHA
        and hashlib.sha256(read(PREVIOUS_ARTIFACT/'qualify_launch_model_child.py',0)).hexdigest()==CAPTURE_SHA
        and quiescent(properties('ec-launch-current-model-native-v3-20261027.service')))
    observation=value.get('child_observation',{})
    require(observation.get('complete') is False and observation.get('phase')=='verification'
        and observation.get('error_kind')=='ValueError' and observation.get('helper_lines')==[271,237,40]
        and observation.get('files_equal')==dict.fromkeys(('.env','auth.json','config.yaml','enhanced_cognee.json'),True))
    requests=observation.get('requests',{});network=observation.get('network',{})
    require(requests.get('count')==requests.get('returned_model_verified_requests')==3
        and requests.get('http_statuses')==[200,200,200] and requests.get('failed_response') is False
        and requests.get('rate_limited') is False and network.get('unexpected_denied')==0
        and network.get('controls_denied')==3 and network.get('model_dns',0)>=1 and network.get('model_connections',0)>=1)
    capture=json.loads(read(PREVIOUS/'capture.summary.json',0))
    require(capture.get('complete') is False and capture.get('phase')=='verification'
        and capture.get('helper_lines')==[271,237,40] and capture.get('error_kind')=='ValueError')
    template=definitions(PREVIOUS_ARTIFACT/'qualify_launch_model_child.py',CAPTURE_SHA)
    template['validate_result'](capture,'capture')
    require(template['safe_report'](capture)==observation)
    return dict(complete=True,previous_evidence=str(PREVIOUS),native_capture_turn_predicates_verified=True,
        selected_capture_and_privacy_predicates_verified=True,preservation_predicates_verified=True,
        prior_overall_failure_preserved=True,capture_replayed=False,reused_model_requests=3)


async def selected_record(read,identity):
    import asyncpg
    config=json.loads(read(Path('/etc/enhanced-cognee/operator.json'),0))
    connection=await asyncpg.connect(config['ENHANCED_MEMORY_DATABASE_URL'],timeout=10,command_timeout=10,
        server_settings={'default_transaction_read_only':'on','application_name':'ec_finish_captured_model_readonly'})
    del config
    try:
        async with connection.transaction(readonly=True):
            rows=await connection.fetch("SELECT id,version,state,owner_subject,writer_agent,(expires_at IS NULL OR expires_at>now()) AS live FROM shared_memory.records WHERE tenant=$1 AND project=$2 LIMIT 2",
                identity['tenant'],identity['project_id'])
            require(len(rows)==1)
            row=rows[0]
            require(row['version']==1 and row['state']=='active' and row['live'] is True
                and row['owner_subject']==identity['sub'] and row['writer_agent']==identity['agent_id'])
            ident=str(row['id']);require(re.fullmatch('[a-f0-9-]{36}',ident))
            versions=await connection.fetchval('SELECT count(*) FROM shared_memory.record_versions WHERE tenant=$1 AND project=$2 AND record_id=$3',
                identity['tenant'],identity['project_id'],row['id'])
            require(versions==1)
            return ident
    finally:await connection.close()


def worker(read,write):
    require(os.geteuid()==0 and Path(__file__).parent==ARTIFACT)
    context=json.loads(read(ARTIFACT/'context.json',0));evidence=Path(context['evidence'])
    require(context.get('run_id')==IDENT and evidence.parent==BASE/'operator-evidence'
        and re.fullmatch('model-recall-finish-[A-Za-z0-9_-]{6,64}',evidence.name))
    child=definitions(ARTIFACT/CHILD_NAME,CHILD_SHA)
    native=definitions(ARTIFACT/'qualify_launch_gateway_renewal_v2.py',PINS['qualify_launch_gateway_renewal_v2.py'])
    for name,digest in native['NATIVE'].items():require(hashlib.sha256((native['RELEASE']/'repo'/name).read_bytes()).hexdigest()==digest)
    for name,digest in native['PROVIDER_FILES'].items():require(hashlib.sha256((native['PROVIDER']/name).read_bytes()).hexdigest()==digest)
    legacy=definitions(PREVIOUS_ARTIFACT/'qualify_launch_current_model_v3.py',DRIVER_SHA)
    legacy['install_child'](PREVIOUS_ARTIFACT)
    scope=child['identity'](IDENT)
    policies=[Path('/etc/enhanced-cognee/fleet-credentials.json'),BASE/'operator-isolated-issuer-candidate-v3/candidate-policy.json']
    before={path:read(path,0) for path in policies}
    require(all(row['enabled'] is False for raw in before.values() for row in json.loads(raw)['profiles']))
    result=dict(complete=False,evidence=str(evidence),source_revision=BASE.name,continued_from=str(PREVIOUS),
        capture_replayed=False,reused_capture_model_requests=3,new_model_request_limit=6,
        original_failed_fixture_changed=False,source_profiles_changed=False,existing_launchers_changed=False,
        private_keys_sent_to_owner=False,production_renewal_timer_enabled=False,actual_profile_admission_qualified=False,
        maximum_context_verified=False,fleet_launch_approved=False,automatic_model_retry=False,credentials_issued=0,
        operator_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(evidence/'started.json',canonical(result));phase='retained_capture_validation'
    try:
        proof=retained_capture(read);write(evidence/'retained-capture-proof.json',canonical(proof))
        phase='canonical_metadata_selection';record=asyncio.run(selected_record(read,scope))
        require(record==context['record_id'])
        issuer=definitions(BASE/'operator-issuer-candidate-v2/provision_pilot_access.py',
            'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6')
        key=issuer['load_signing_key']();now=int(time.time())
        tokens=[issuer['sign_claims'](dict(child['identity'](IDENT,peer),iat=now,exp=now+1200),key) for peer in (False,True)]
        del key;result['credentials_issued']=2
        phase='delivery_readiness'
        transport=definitions(Path('/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-launch-fcc7be3d7659/client.py'),
            '8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64')
        client=transport['MemoryClient']('http://127.0.0.1:28080',tokens[0])
        delivery=definitions(ARTIFACT/'model_delivery_readiness.py',PINS['model_delivery_readiness.py'])
        readiness=delivery['wait'](lambda:client.request('GET','/v1/memories/status'),scope)
        write(evidence/'delivery-readiness.json',canonical(readiness));result['delivery_readiness']=readiness
        phase='ordinary_model_route'
        route=definitions(ARTIFACT/'bind_launch_model_route.py',PINS['bind_launch_model_route.py'])
        helper,_,authority=route['prepare']((ARTIFACT/'bind_launch_model_route.py').read_bytes(),definitions)
        require(authority['endpoint_path']=='/api/coding/paas/v4')
        packet=dict(stage='recall',run_id=IDENT,key=authority['key'],token=tokens[0],peer=tokens[1],record_id=record,
            guard=(ARTIFACT/'zai_native_qualification_guard_v2.py').read_text(),observer=(ARTIFACT/'observe_launch_native_runtime.py').read_text())
        def observe(stage,value):
            report=child['safe_report'](value);write(evidence/(stage+'.observation.json'),canonical(report));result['child_observation']=report
        legacy['owner'].__globals__['OWNER_OBSERVER']=observe
        phase='fresh_process_recall'
        write(evidence/'recall.started.json',canonical(dict(capture_replayed=False,record_id=record,expected_version=1)))
        value=legacy['owner'](helper,(ARTIFACT/CHILD_NAME).read_bytes(),pwd.getpwnam('hermes-runtime'),packet)
        write(evidence/'recall.summary.json',canonical(value));require(value.get('complete') is True)
        phase='post_retraction_delivery'
        after=delivery['wait'](lambda:client.request('GET','/v1/memories/status'),scope)
        withdrawn=client.request('POST','/v1/memories/recall',dict(query='Rowan '+IDENT,limit=5,include_shared=False))
        require(withdrawn.get('results')==[])
        write(evidence/'withdrawal-readiness.json',canonical(after))
        result.update(complete=True,retained_capture_reused=True,current_configured_model_native_capture_qualified=True,
            current_configured_model_fresh_process_recall_qualified=True,canonical_evidence_delivered=True,
            invented_sensitive_input_excluded=True,invented_record_retracted_history_preserved=True,
            peer_history_denied=True,post_retraction_delivery_ready=True,canonical_recall_withdrawn=True,
            model_route='zai/glm-5.3-flash',record_id=record)
    except Exception as error:
        result.update(category='model_recall_finish_incomplete_preserve_evidence_no_automatic_retry',failure_phase=phase,
            error_kind=type(error).__name__ if type(error).__name__ in {'ValueError','MemoryTransportError','TimeoutExpired','PermissionError','FileNotFoundError'} else 'other')
        if isinstance(getattr(error,'readiness',None),dict):result['delivery_readiness']=error.readiness
        code=getattr(error,'status_code',None)
        if type(code) is int and 100<=code<=599:result['http_status']=code
    require(all(read(path,0)==raw for path,raw in before.items()))
    result['all_admission_policies_preserved_disabled']=True
    write(evidence/'summary.json',canonical(result));sync(evidence)
    return 0 if result['complete'] else 1


def launch():
    require(os.geteuid()==0)
    directory=Path(__file__).parent
    shared=definitions(directory/'recover_launch_graph_operator.py',SUPPORT_SHA);read,write=shared['read_file'],shared['private_write']
    if os.path.lexists(ARTIFACT):return watch(read)
    retained_capture(read)
    require(properties().get('LoadState')=='not-found' and quiescent(properties()))
    child=definitions(directory/CHILD_NAME,CHILD_SHA)
    record=asyncio.run(selected_record(read,child['identity'](IDENT)))
    driver=definitions(BASE/'operator-issuer-candidate-v2/renew_fleet_credentials.py','a7432a8a6c258b2f81466f51b782dd9b53c2211a5a52fcb863f3a1567ad858bf')
    driver['protected'](FIXTURES)
    account=pwd.getpwnam('hermes-runtime');profile=FIXTURES/('zai_recall_'+IDENT)
    profile.mkdir(mode=0o700);os.chown(profile,account.pw_uid,account.pw_gid)
    sources={Path(__file__).name:globals()['_verified_source_bytes']}
    for name,digest in PINS.items():sources[name]=definitions(directory/name,digest)['_verified_source_bytes']
    evidence=Path(tempfile.mkdtemp(prefix='model-recall-finish-',dir=BASE/'operator-evidence'));ARTIFACT.mkdir(mode=0o700)
    for name,raw in sources.items():write(ARTIFACT/name,raw)
    write(ARTIFACT/'sources.json',canonical({k:hashlib.sha256(v).hexdigest() for k,v in sources.items()}))
    write(ARTIFACT/'context.json',canonical(dict(evidence=str(evidence),run_id=IDENT,record_id=record)));sync(ARTIFACT)
    settings=dict(Type='oneshot',RemainAfterExit='yes',User='root',Group='root',UMask='0077',NoNewPrivileges='yes',
        CapabilityBoundingSet='CAP_SETUID CAP_SETGID',AmbientCapabilities='',ProtectHome='no',ProtectSystem='strict',
        PrivateTmp='no',ReadWritePaths=str(BASE/'operator-evidence')+' '+str(profile),
        Restart='no',TimeoutStartSec='480',MemoryMax='2G',LimitCORE='0')
    args=['/usr/bin/systemd-run','--quiet','--no-block','--unit='+UNIT]+['--property='+k+'='+v for k,v in settings.items()]
    args+=[str(BASE/'runtime/bin/python'),'-I','-B',str(ARTIFACT/Path(__file__).name),'--worker']
    subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=True)
    return watch(read)


if __name__=='__main__':
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        require(sys.argv[1:]==['--worker'])
        shared=definitions(ARTIFACT/'recover_launch_graph_operator.py',SUPPORT_SHA)
        raise SystemExit(worker(shared['read_file'],shared['private_write']))
    except Exception:
        print('{"complete":false,"category":"model_recall_finish_preflight_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
