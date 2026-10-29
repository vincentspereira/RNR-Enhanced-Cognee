"""Read-only readiness using the canonical status API's nested index contract."""
from __future__ import annotations
import time


def observation(status):
    if not isinstance(status,dict):return {'status_is_object':False,'ready':False}
    index=status.get('index');index=index if isinstance(index,dict) else {}
    def count(value):return value if type(value) is int and 0<=value<=1000000 else None
    outer=count(status.get('pending_change_events'));inner=count(index.get('pending_change_events'))
    available=index.get('worker_available') is True
    state=index.get('worker_state');state=state if isinstance(state,str) and state in {'running','degraded','unavailable'} else 'other'
    vector=index.get('vector_index');vector=vector if isinstance(vector,str) and vector in {'available','degraded'} else 'other'
    graph=index.get('graph')=='source_linked_graph'
    ready=(status.get('ready') is True and available and state=='running' and vector=='available'
        and graph and outer==inner==0)
    return dict(status_is_object=True,ready=ready,worker_available=available,worker_state=state,
        pending_change_events=outer,index_pending_change_events=inner,vector_index=vector,source_linked_graph=graph)


def wait(fetch,scope,*,seconds=30,monotonic=time.monotonic,sleep=time.sleep):
    deadline=monotonic()+seconds
    while True:
        value=fetch()
        expected={'tenant_id':scope['tenant'],'project_id':scope['project_id'],'subject':scope['sub']}
        if not isinstance(value,dict) or not all(value.get(k)==v for k,v in expected.items()) or value.get('schema_version')!=3 or value.get('encryption')!='AES-256-GCM':
            raise ValueError('fixed_scope_status_required')
        result=observation(value)
        if result['ready']:return result
        if monotonic()>=deadline:
            error=ValueError('retained_model_delivery_not_ready');error.readiness=result;raise error
        sleep(1)
