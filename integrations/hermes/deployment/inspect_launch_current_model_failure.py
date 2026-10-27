"""Read the retained V2 receipt and fixed invented-scope canonical metadata.

No model call, credential issuance, profile walk, decryption, service change or
record edit. Only allowlisted phase/count/status/boolean fields leave root.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE=Path('/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529')
ARTIFACT=BASE/'operator-current-model-native-v2'
EVIDENCE=BASE/'operator-evidence/current-model-native-spnm6ro6'
IDENT='e04a048d26af4631b2126bcd27a9174a'
HELPER_SHA='e21579372b94a1a881908e543342fbfcd7582d593ac579d7f2b23a1d805dbda1'
SUPPORT_SHA='d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef'
PHASES={'identity','fixture','imports','scope','agent','native_turn','verification','cleanup'}
KINDS={'ValueError','GuardError','PermissionError','FileNotFoundError','AuthError','TimeoutExpired','RuntimeError','other'}
NETWORK={'memory_operations','model_dns','model_connections','metadata_denied','unexpected_denied','controls_denied'}
REQUEST_COUNTS={'count','returned_model_verified_requests'}
REQUEST_FLAGS={'rate_limited','failed_response','prefetched_evidence_delivered'}


def require(value):
    if not value:raise ValueError('retained_model_inspection_refused')


def project(value):
    """A malformed/private extra field can never become terminal output."""
    require(isinstance(value,dict))
    result=dict(complete=value.get('complete') is True,
        phase=value.get('phase') if value.get('phase') in PHASES else 'other',
        error_kind=value.get('error_kind') if value.get('error_kind') in KINDS else 'other')
    observation=value.get('observation',value)
    if not isinstance(observation,dict):return result
    if observation.get('stage') in {'capture','recall'}:result['stage']=observation['stage']
    for group in ('requests','network'):
        data=observation.get(group)
        if not isinstance(data,dict):continue
        projected={}
        for name in (NETWORK if group=='network' else REQUEST_COUNTS):
            item=data.get(name)
            if type(item) is int and 0<=item<=100000:projected[name]=item
        if group=='requests':
            for name in REQUEST_FLAGS:
                if type(data.get(name)) is bool:projected[name]=data[name]
            codes=data.get('http_statuses')
            if isinstance(codes,list) and len(codes)<=6 and all(type(c) is int and 100<=c<=599 for c in codes):
                projected['http_statuses']=codes
        result[group]=projected
    files=observation.get('files_equal')
    if isinstance(files,dict):
        result['files_equal']={name:files[name] for name in ('.env','config.yaml','auth.json','enhanced_cognee.json') if type(files.get(name)) is bool}
    return result


async def canonical_metadata(read):
    import asyncpg
    config=json.loads(read(Path('/etc/enhanced-cognee/operator.json'),0))
    connection=await asyncpg.connect(config['ENHANCED_MEMORY_DATABASE_URL'],timeout=10,command_timeout=10,
        server_settings={'default_transaction_read_only':'on','application_name':'ec_model_retained_readonly'})
    del config
    try:
        async with connection.transaction(readonly=True):
            scope='zai_'+IDENT
            rows=await connection.fetch('SELECT id,version,state,owner_subject,writer_agent FROM shared_memory.records WHERE tenant=$1 AND project=$2 LIMIT 3',
                'qualification',scope)
            versions=await connection.fetchval('SELECT count(*) FROM shared_memory.record_versions WHERE tenant=$1 AND project=$2',
                'qualification',scope)
            require(type(versions) is int and 0<=versions<=1000)
            return dict(inspection_complete=True,records_observed=len(rows),record_limit_reached=len(rows)==3,
                canonical_version_count=versions,
                states=[row['state'] if row['state'] in {'active','retracted'} else 'other' for row in rows],
                versions=[row['version'] if type(row['version']) is int and 1<=row['version']<=1000 else None for row in rows],
                fixed_subjects_match=all(row['owner_subject']==row['writer_agent']==scope for row in rows),
                payloads_read=False,records_changed=False)
    finally:await connection.close()


def main():
    require(os.geteuid()==0 and not sys.argv[1:])
    raw=(Path(__file__).parent/'recover_launch_graph_operator.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==SUPPORT_SHA)
    support={'__name__':'verified_retained_model_files'}
    exec(compile(raw,'<verified-public-file-helper>','exec'),support)
    read=support['read_file']
    result=json.loads(read(EVIDENCE/'summary.json',0))
    require(result.get('complete') is False and result.get('failure_phase')=='capture'
        and result.get('credentials_issued')==2 and result.get('new_invented_scope')==IDENT
        and result.get('operator_helper_sha256')==HELPER_SHA
        and hashlib.sha256(read(ARTIFACT/'qualify_launch_current_model_v2.py',0)).hexdigest()==HELPER_SHA)
    context=json.loads(read(ARTIFACT/'context.json',0))
    require(context.get('evidence')==str(EVIDENCE) and context.get('run_id')==IDENT)
    process=subprocess.run(['/usr/bin/systemctl','show','ec-launch-current-model-native-v2-20261027.service',
        '--property=ActiveState,SubState,MainPID,ControlPID'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True)
    require(len(process.stdout)<=4096)
    properties=dict(line.split('=',1) for line in process.stdout.decode().splitlines() if '=' in line)
    require(properties.get('ActiveState') in {'inactive','failed'} and properties.get('MainPID')==properties.get('ControlPID')=='0')
    output=dict(complete=True,stage='retained_current_model_capture_inspection',source_revision=BASE.name,
        model_called_by_inspection=False,credentials_issued=0,profiles_read=False,records_changed=False,
        services_changed=False,prior_job_stopped=True,fleet_launch_approved=False)
    try:
        output['capture_receipt']=project(json.loads(read(EVIDENCE/'capture.summary.json',0)))
        output['capture_receipt_present']=True
    except FileNotFoundError:
        output['capture_receipt_present']=False
        output['capture_receipt_lost_before_validation']=True
    try:output['canonical_metadata']=asyncio.run(canonical_metadata(read))
    except Exception as error:
        output['canonical_metadata']=dict(inspection_complete=False,error_kind=type(error).__name__ if type(error).__name__ in {'ValueError','PermissionError','TimeoutError','PostgresError'} else 'other')
    print(json.dumps(output,sort_keys=True),flush=True)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"retained_current_model_inspection_refused_no_secret_output"}',flush=True)
        raise SystemExit(1)
