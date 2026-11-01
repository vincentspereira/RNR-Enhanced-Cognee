"""Reuse capture; validate the real nested status contract before recall only."""
import asyncio
import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import uuid

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
FINISH=runpy.run_path(str(DIRECTORY/'finish_launch_model_scope.py'),run_name='finish_model_unit_tests')
DELIVERY=runpy.run_path(str(DIRECTORY/'model_delivery_readiness.py'),run_name='delivery_contract_tests')
CHILD=runpy.run_path(str(DIRECTORY/'qualify_launch_model_recall_child.py'),run_name='recall_only_child_tests')
IDENT=FINISH['IDENT']


async def real_status():
    from src.memory_service import MemoryScope,MemoryService
    from src.recall_service import DerivedRecall
    class Connection:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def fetchval(self,sql,*args):return 1 if "state='active'" in sql else 0
        async def fetchrow(self,sql,*args):
            return dict(state='running',fresh=True,model='synthetic-embedding',dimensions=3) if 'index_workers' in sql else {'pending':0,'seconds':0}
    pool=SimpleNamespace(acquire=lambda:Connection())
    derived=DerivedRecall(SimpleNamespace(identity=SimpleNamespace(pipeline='synthetic_pipeline'),model='synthetic-embedding',dimensions=3))
    service=MemoryService(pool,SimpleNamespace(active='invented-key-id',_enabled=True),derived=derived)
    identity=CHILD['identity'](IDENT)
    scope=MemoryScope(identity['tenant'],identity['project_id'],identity['sub'],identity['agent_id'])
    return await service.status(scope)


def test_real_service_status_exposes_nested_worker_and_old_gate_cannot_pass():
    status=asyncio.run(real_status())
    assert status.get('worker_available') is None and status['index']['worker_available'] is True
    assert not (status.get('pending_change_events')==0 and status.get('worker_available') is True)
    proof=DELIVERY['observation'](status)
    assert proof['ready'] is True and proof['pending_change_events']==proof['index_pending_change_events']==0


@pytest.mark.parametrize('damage',['missing_index','worker_false','worker_stale','pending','mismatch','bool_count','vector','graph','top_only'])
def test_readiness_does_not_mask_unready_or_malformed_derived_state(damage):
    status=asyncio.run(real_status())
    if damage=='missing_index':status.pop('index')
    elif damage=='worker_false':status['index']['worker_available']=False
    elif damage=='worker_stale':status['index']['worker_state']='unavailable'
    elif damage=='pending':status['pending_change_events']=status['index']['pending_change_events']=1
    elif damage=='mismatch':status['index']['pending_change_events']=1
    elif damage=='bool_count':status['index']['pending_change_events']=False
    elif damage=='vector':status['index']['vector_index']='degraded'
    elif damage=='graph':status['index']['graph']='unavailable'
    else:status.pop('index');status['worker_available']=True
    assert DELIVERY['observation'](status)['ready'] is False


def test_wait_only_reads_and_bounds_unready_polling():
    status=asyncio.run(real_status());scope=CHILD['identity'](IDENT);clock=[0];reads=[]
    status['index']['worker_available']=False
    def fetch():reads.append(True);return status
    with pytest.raises(ValueError) as stopped:
        DELIVERY['wait'](fetch,scope,seconds=2,monotonic=lambda:clock[0],sleep=lambda n:clock.__setitem__(0,clock[0]+n))
    assert len(reads)==3 and stopped.value.readiness['worker_available'] is False
    assert DELIVERY['wait'](lambda:asyncio.run(real_status()),scope)['ready'] is True


def retained():
    observation=dict(complete=False,error_kind='ValueError',phase='verification',receipt_is_object=True,
        helper_lines=[271,237,40],files_equal=dict.fromkeys(('.env','auth.json','config.yaml','enhanced_cognee.json'),True),
        requests=dict(count=3,returned_model_verified_requests=3,http_statuses=[200]*3,failed_response=False,rate_limited=False,prefetched_evidence_delivered=False),
        network=dict(controls_denied=3,unexpected_denied=0,model_dns=3,model_connections=3,memory_operations=72,metadata_denied=3))
    summary=dict(complete=False,failure_phase='capture',new_invented_scope=IDENT,operator_helper_sha256=FINISH['DRIVER_SHA'],
        all_admission_policies_preserved_disabled=True,credentials_issued=2,child_observation=observation)
    capture=dict(complete=False,phase='verification',error_kind='ValueError',helper_lines=[271,237,40],http_status=None,errno=None,
        observation=dict(stage='capture',files_equal=observation['files_equal'],requests=observation['requests'],network=observation['network']))
    return summary,capture


@pytest.mark.parametrize('damage',[None,'early_predicate','files','429','model_identity','complete','source','observation_mismatch'])
def test_only_exact_late_timeout_can_reuse_the_capture(monkeypatch,damage):
    summary,capture=retained()
    if damage=='early_predicate':summary['child_observation']['helper_lines']=[271,215,40]
    elif damage=='files':summary['child_observation']['files_equal']['auth.json']=False
    elif damage=='429':summary['child_observation']['requests']['http_statuses']=[200,429,200]
    elif damage=='model_identity':summary['child_observation']['requests']['returned_model_verified_requests']=2
    elif damage=='complete':summary['complete']=True
    elif damage=='source':summary['operator_helper_sha256']='0'*64
    elif damage=='observation_mismatch':capture['observation']['network']=dict(capture['observation']['network'],memory_operations=999)
    def read(path,*args):
        if path.name=='summary.json':return json.dumps(summary).encode()
        if path.name=='capture.summary.json':return json.dumps(capture).encode()
        if path.name=='context.json':return json.dumps(dict(run_id=IDENT,evidence=str(FINISH['PREVIOUS']))).encode()
        return (DIRECTORY/path.name).read_bytes()
    namespace=FINISH['retained_capture'].__globals__
    monkeypatch.setitem(namespace,'properties',lambda *a:dict(ActiveState='inactive',MainPID='0',ControlPID='0'))
    original=namespace['definitions']
    monkeypatch.setitem(namespace,'definitions',lambda path,digest:original(DIRECTORY/path.name,digest))
    if damage is not None:
        with pytest.raises(ValueError):FINISH['retained_capture'](read)
    else:
        proof=FINISH['retained_capture'](read)
        assert proof['capture_replayed'] is False and proof['reused_model_requests']==3
        assert proof['prior_overall_failure_preserved'] is True


def test_recall_component_refuses_capture_before_any_model_or_write():
    packet=dict(stage='capture',run_id=IDENT,key='invented-unused-key',token='invented-api-token',peer='invented-peer-token',record_id=None,
        guard=(DIRECTORY/'zai_native_qualification_guard_v2.py').read_text(),observer=(DIRECTORY/'observe_launch_native_runtime.py').read_text())
    with pytest.raises(ValueError):CHILD['packet_shape'](packet)
    packet.update(stage='recall',record_id='invented-owned-record')
    CHILD['packet_shape'](packet)


def test_recall_memory_guard_refuses_remember_before_transport():
    calls=[];boundary=SimpleNamespace(failed=False)
    provider=SimpleNamespace(_client=SimpleNamespace(request=lambda *args:calls.append(args)))
    packet={'stage':'recall','run_id':IDENT,'record_id':'invented-record'}
    CHILD['guard_memory'](provider,packet,boundary)
    with pytest.raises(ValueError):
        provider._client.request('POST','/v1/memories',{'content':'must not be written'})
    assert calls==[] and boundary.failed is True


def test_controller_pins_the_exact_finish_source():
    controller=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='recall_finish_controller_pin')
    assert controller['CURRENT_MODEL_FINISH_SHA']==hashlib.sha256((DIRECTORY/'finish_launch_model_scope.py').read_bytes()).hexdigest()


def test_selected_record_reads_only_fixed_scope_metadata_and_rejects_finished_rows(monkeypatch):
    scope=CHILD['identity'](IDENT);record=uuid.uuid4();finished=[False];closed=[]
    class Transaction:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    class Connection:
        def transaction(self,**kw):assert kw=={'readonly':True};return Transaction()
        async def fetch(self,sql,*args):
            assert args==(scope['tenant'],scope['project_id']) and 'payload' not in sql
            return [dict(id=record,version=2 if finished[0] else 1,state='retracted' if finished[0] else 'active',
                live=True,owner_subject=scope['sub'],writer_agent=scope['agent_id'])]
        async def fetchval(self,sql,*args):assert args==(scope['tenant'],scope['project_id'],record);return 1
        async def close(self):closed.append(True)
    async def connect(url,**kw):assert kw['server_settings']['default_transaction_read_only']=='on';return Connection()
    monkeypatch.setitem(sys.modules,'asyncpg',SimpleNamespace(connect=connect))
    read=lambda *args:b'{"ENHANCED_MEMORY_DATABASE_URL":"invented-operator-url"}'
    assert asyncio.run(FINISH['selected_record'](read,scope))==str(record)
    finished[0]=True
    with pytest.raises(ValueError):asyncio.run(FINISH['selected_record'](read,scope))
    assert closed==[True,True]


def test_repeating_finish_only_attaches_and_all_sources_are_pinned(monkeypatch):
    for name,digest in FINISH['PINS'].items():assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest
    launch=FINISH['launch'];namespace=launch.__globals__;events=[]
    monkeypatch.setattr(FINISH['os'],'geteuid',lambda:0)
    monkeypatch.setattr(FINISH['os'].path,'lexists',lambda *a:True)
    monkeypatch.setitem(namespace,'definitions',lambda *a:dict(read_file=object(),private_write=object()))
    monkeypatch.setitem(namespace,'watch',lambda *a:events.append('reattach') or 0)
    assert launch()==0 and events==['reattach']


@pytest.mark.parametrize('recall_complete',[True,False])
def test_worker_runs_only_remaining_recall_and_keeps_root_authority_out_of_owner_packet(tmp_path,monkeypatch,recall_complete):
    worker=FINISH['worker'];namespace=worker.__globals__;artifact=tmp_path/'operator-model-recall-finish-v1';artifact.mkdir()
    base=tmp_path/'base';evidence=base/'operator-evidence/model-recall-finish-invented';evidence.mkdir(parents=True)
    (artifact/'finish_launch_model_scope.py').write_bytes((DIRECTORY/'finish_launch_model_scope.py').read_bytes())
    (artifact/FINISH['CHILD_NAME']).write_bytes((DIRECTORY/FINISH['CHILD_NAME']).read_bytes())
    for name in ('bind_launch_model_route.py','zai_native_qualification_guard_v2.py','observe_launch_native_runtime.py'):
        (artifact/name).write_text('reviewed-public-source')
    record='12345678-1234-4234-8234-123456789abc';scope=CHILD['identity'](IDENT);events=[];writes={}
    root_key=b'invented-root-key-never-sent-to-owner';api_status=asyncio.run(real_status())
    def read(path,*args):
        if path.name=='context.json':return json.dumps(dict(evidence=str(evidence),run_id=IDENT,record_id=record)).encode()
        return b'{"profiles":[{"enabled":false}]}'
    def owner(helper,source,account,packet):
        events.append(packet['stage'])
        assert packet['stage']=='recall' and packet['record_id']==record and packet['run_id']==IDENT
        assert root_key.decode() not in json.dumps(packet) and account.pw_uid==1234
        return {'complete':recall_complete}
    class Client:
        def __init__(self,base,token):pass
        def request(self,method,path,body=None):
            if path.endswith('/status'):return api_status
            assert method=='POST' and path.endswith('/recall');events.append('withdrawal_readonly');return {'results':[]}
    async def selected(*args):return record
    def definitions(path,digest):
        if path.name==FINISH['CHILD_NAME']:return CHILD
        if path.name=='qualify_launch_gateway_renewal_v2.py':return {'NATIVE':{},'PROVIDER_FILES':{}}
        if path.name=='qualify_launch_current_model_v3.py':return dict(install_child=lambda *a:None,owner=owner)
        if path.name=='provision_pilot_access.py':return dict(load_signing_key=lambda:root_key,
            sign_claims=lambda claims,key:'invented-ordinary-'+claims['sub'])
        if path.name=='client.py':return {'MemoryClient':Client}
        if path.name=='model_delivery_readiness.py':return DELIVERY
        if path.name=='bind_launch_model_route.py':return {'prepare':lambda *a:({}, {}, {'key':'invented-model-key','endpoint_path':'/api/coding/paas/v4'})}
        raise AssertionError('unexpected public source dependency')
    monkeypatch.setattr(FINISH['os'],'geteuid',lambda:0)
    monkeypatch.setattr(FINISH['pwd'],'getpwnam',lambda *a:SimpleNamespace(pw_uid=1234))
    for name,value in dict(BASE=base,ARTIFACT=artifact,__file__=str(artifact/'finish_launch_model_scope.py'),
        definitions=definitions,retained_capture=lambda *a:{'capture_replayed':False},selected_record=selected,sync=lambda *a:None).items():
        monkeypatch.setitem(namespace,name,value)
    code=worker(read,lambda path,raw:writes.setdefault(path,raw))
    result=json.loads(writes[evidence/'summary.json'])
    assert code==(0 if recall_complete else 1)
    assert events==(['recall','withdrawal_readonly'] if recall_complete else ['recall'])
    assert result['capture_replayed'] is False and result['reused_capture_model_requests']==3
    assert result['fleet_launch_approved'] is False and result['credentials_issued']==2
    assert root_key.decode() not in str(writes)


def test_watch_accepts_only_continuation_evidence_and_returns_without_replaying(monkeypatch,capsys):
    watch=FINISH['watch'];namespace=watch.__globals__;events=[]
    evidence=FINISH['BASE']/'operator-evidence/model-recall-finish-invented'
    def read(path,*args):
        if path.name=='context.json':return json.dumps({'evidence':str(evidence)}).encode()
        assert path==evidence/'summary.json'
        return b'{"complete":true,"capture_replayed":false,"fleet_launch_approved":false}'
    monkeypatch.setitem(namespace,'properties',lambda *a:dict(ActiveState='inactive',MainPID='0',ControlPID='0'))
    monkeypatch.setattr(FINISH['subprocess'],'run',lambda *a,**kw:events.append('unexpected service action'))
    assert watch(read)==0 and events==[]
    assert json.loads(capsys.readouterr().out)['operator_job_stopped'] is True
