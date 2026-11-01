"""REA budget regression and immutable partial-result continuation controls."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
ROOT=runpy.run_path(str(FOLDER/'finish_main_rea_mcp.py'))
PROBE=runpy.run_path(str(FOLDER/'probe_rea_catalogue.py'))
OLD=runpy.run_path(str(FOLDER/'qualify_main_local_mcp.py'))
PROTOCOL=runpy.run_path(str(FOLDER/'probe_main_local_mcp.py'))


def filesystem():
    return dict(complete=True,initialize_passed=True,tools_list_passed=True,tools_count=14,tools_called=4,
        invented_write_read_passed=True,outside_root_denied=True)


def prior_documents():
    context=dict(source_sha256=ROOT['PREVIOUS_SHA'],evidence=str(ROOT['EXPECTED']),id='a'*32)
    receipt=dict(complete=False,invocation_id='b'*32,cases=dict(filesystem=filesystem(),rea=dict(complete=False,error_kind='ValueError')),
        real_profiles_read=False,credentials_read=False,model_called=False,memory_api_called=False,external_sends=0,full_main_tool_coverage_qualified=False)
    programs={name:dict(archive_sha256=digest,archive_bytes=size,version=version,public_copy_readback_verified=True,existing_copy_reused=False)
        for name,(digest,size,version) in ROOT['PINS'].items()}
    value=dict(source_revision=ROOT['BASE'].name,operator_helper_sha256=ROOT['PREVIOUS_SHA'],evidence=str(ROOT['EXPECTED']),
        complete=False,category='local_mcp_component_incomplete_preserve_evidence',checkpoint='component_failure',
        credentials_issued=0,external_platform_sends=0,platform_adapters_started=0,components=receipt['cases'],public_programs=programs)
    value.update({k:True for k in ('operator_job_stopped','qualification_unit_stopped','network_isolated',
        'original_main_candidate_pass_preserved','all_admission_policies_preserved_disabled')})
    value.update({k:False for k in ('keys_read','model_called','memory_api_called','source_profiles_changed','previous_candidates_changed',
        'binary_analysis_requested','completed_tests_replayed','fleet_launch_approved','main_tool_program_coverage_qualified',
        'actual_profile_admission_qualified','production_dispatch_qualified','production_renewal_timer_enabled')})
    return context,value,receipt,programs


@pytest.mark.parametrize('damage',[None,'revision','running','wrong_cause','filesystem_failed','filesystem_count','copy_not_verified','copy_version','changed_profile','model','admitted'])
def test_exact_stopped_partial_attempt_and_passed_filesystem_are_required(damage):
    context,value,receipt,programs=prior_documents()
    if damage=='revision':context['source_sha256']='wrong'
    if damage=='wrong_cause':receipt['cases']['rea']['error_kind']='other'
    if damage=='filesystem_failed':receipt['cases']['filesystem']={'complete':False,'error_kind':'ValueError'};value['components']=receipt['cases']
    if damage=='filesystem_count':receipt['cases']['filesystem']['tools_count']=13
    if damage=='copy_not_verified':programs['rea']['public_copy_readback_verified']=False
    if damage=='copy_version':programs['rea']['version']='wrong'
    if damage=='changed_profile':value['source_profiles_changed']=True
    if damage=='model':value['model_called']=True
    if damage=='admitted':value['fleet_launch_approved']=True
    data={ROOT['PREVIOUS']/'context.private.json':context,ROOT['EXPECTED']/'finish.summary.json':value,
        ROOT['EXPECTED']/'component-receipt.json':receipt,ROOT['EXPECTED']/'public-programs.json':programs}
    old=dict(UNIT='old.service',metadata=lambda unit:dict(ActiveState='active' if damage=='running' else 'inactive',SubState='running' if damage=='running' else 'dead'),
        retained=lambda read:{},validate_probe=OLD['validate_probe'])
    if damage:
        with pytest.raises(ValueError):ROOT['retained'](old,lambda path,*a:json.dumps(data[path]).encode())
    else:assert ROOT['retained'](old,lambda path,*a:json.dumps(data[path]).encode())==(context,receipt)


def rea_receipt():
    return dict(complete=True,invocation_id='c'*32,cases={'rea':dict(complete=True,initialize_passed=True,tools_list_passed=True,
        tools_count=207,tools_called=0,binary_analysis_requested=False,reply_limit_bytes=10*1024**2,catalogue_result_bytes=3158382)},
        real_profiles_read=False,credentials_read=False,model_called=False,memory_api_called=False,external_sends=0,
        full_main_tool_coverage_qualified=False)


@pytest.mark.parametrize('damage',[None,'filesystem_replayed','limit','oversize','boolean_count','tool_call','binary_analysis','model','full_coverage'])
def test_new_receipt_only_accepts_bounded_rea_catalogue_without_operations(damage):
    value=rea_receipt();row=value['cases']['rea']
    if damage=='filesystem_replayed':value['cases']['filesystem']=filesystem()
    if damage=='limit':row['reply_limit_bytes']+=1
    if damage=='oversize':row['catalogue_result_bytes']=ROOT['REPLY_LIMIT']+1
    if damage=='boolean_count':row['tools_count']=True
    if damage=='tool_call':row['tools_called']=1
    if damage=='binary_analysis':row['binary_analysis_requested']=True
    if damage=='model':value['model_called']=True
    if damage=='full_coverage':value['full_main_tool_coverage_qualified']=True
    if damage:
        with pytest.raises(ValueError):ROOT['validate_rea_probe'](value,'c'*32)
    else:assert ROOT['validate_rea_probe'](value,'c'*32)==value


@pytest.mark.parametrize('large',[False,True])
def test_large_full_schema_catalogue_keeps_all_schemas_and_bounded_reader(monkeypatch,tmp_path,large):
    # A real fixture subprocess emits a full >2 MiB JSON schema. No vendor code
    # or model/tool operation executes. Both readers remain strictly bounded.
    payload=3*1024**2 if large else 100
    code='''import json,sys
for line in sys.stdin:
 request=json.loads(line)
 if 'id' not in request:continue
 result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}}} if request['method']=='initialize' else {'tools':[{'name':'invented_catalogue','inputSchema':{'type':'object','description':'x'*int(sys.argv[1])},'outputSchema':{'type':'object'}}]}
 print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)
'''
    monkeypatch.setitem(PROTOCOL['Client'].response.__globals__,'MAX_REPLY',PROBE['REPLY_LIMIT'])
    client=PROTOCOL['Client']([sys.executable,'-I','-B','-c',code,str(payload)],{'PATH':'/usr/bin:/bin'},tmp_path)
    try:
        case=PROBE['catalogue'](PROTOCOL,client)
        assert case['tools_count']==1 and case['tools_called']==0 and case['reply_limit_bytes']==10*1024**2
        assert case['catalogue_result_bytes']>2*1024**2 if large else case['catalogue_result_bytes']<2*1024**2
    finally:client.close()


def test_oversized_catalogue_remains_rejected(monkeypatch):
    monkeypatch.setitem(PROBE['catalogue'].__globals__,'REPLY_LIMIT',128)
    client=SimpleNamespace(rpc=lambda method,params:{'tools':[{'name':'x','inputSchema':{'description':'x'*256}}]})
    module={'handshake':lambda client:(client.rpc('tools/list',{}),{'x'})[1]}
    with pytest.raises(ValueError):PROBE['catalogue'](module,client)


@pytest.mark.parametrize('success',[False,True])
def test_finish_merges_retained_filesystem_without_replay_or_recopy(monkeypatch,tmp_path,success):
    scope=ROOT['worker'].__globals__;base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/main-local-mcp-rea-finish-invented';evidence.mkdir(parents=True)
    expected=base/'previous';passed=base/'main-pass.json';policy=Path('/invented/policy')
    context=dict(evidence=str(evidence),source_sha256='d'*64,id='e'*32)
    files={artifact/'context.private.json':json.dumps(context).encode(),passed:b'main-pass',policy:b'disabled'}
    for name in ('summary.json','finish.summary.json','component-receipt.json','public-programs.json'):files[expected/name]=('unchanged-'+name).encode()
    original=dict(files);seen=[];observed=rea_receipt()
    if not success:observed.update(complete=False,cases={'rea':dict(complete=False,error_kind='ValueError')})
    old=dict(PASSED=passed,PROGRAM_ROOT=Path('/opt/hermes-runtime/programs'),NODE_SHA='invented',pwd=SimpleNamespace(getpwnam=lambda name:SimpleNamespace(pw_name=name)))
    def proof(context,account,programs,write):
        seen.append('rea-only-proof')
        assert programs['filesystem'].endswith('/probe.py') and 'mcp-filesystem-' not in programs['filesystem']
        return observed
    old['proof']=proof
    driver=dict(policies=lambda read:{policy:b'disabled'},fixed_entry=lambda read:({'user':'ecbot_5592956882ea9a13','enabled':False},{}))
    def write(path,raw):assert path not in files;files[path]=raw
    c={'legacy':lambda:driver};receipt={'cases':{'filesystem':filesystem()}}
    for name,value in dict(BASE=base,ARTIFACT=artifact,EXPECTED=expected,__file__=str(artifact/'finish_main_rea_mcp.py'),
        helpers=lambda:(old,c,lambda path,*a:files[path],write),retained=lambda *a:({'id':'f'*32},receipt),public_pin=lambda *a:None).items():monkeypatch.setitem(scope,name,value)
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0);monkeypatch.setenv('INVOCATION_ID','a'*32)
    assert ROOT['worker']()==(0 if success else 1)
    result=json.loads(files[evidence/'summary.json'])
    assert result['components']['filesystem']==filesystem() and seen==['rea-only-proof']
    assert result['filesystem_replayed'] is result['full_public_readback_replayed'] is result['java_ghidra_proof_replayed'] is False
    assert result['new_package_copies']==result['credentials_issued']==result['external_platform_sends']==0
    assert result['fleet_launch_approved'] is result['main_tool_program_coverage_qualified'] is False
    assert all(files[path]==raw for path,raw in original.items())


def test_immutable_finished_result_returns_without_starting_new_probe(monkeypatch,tmp_path,capsys):
    scope=ROOT['launch'].__globals__;artifact=tmp_path/'artifact';artifact.mkdir()
    context=artifact/'context.private.json';context.write_text('present')
    source=FOLDER/'finish_main_rea_mcp.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    files={context:json.dumps({'source_sha256':digest}).encode(),artifact/'sources.json':b'{}'}
    seen=[]
    old={}
    def watch(read,write):seen.append('retained-watch');print('{"complete":true,"replayed":false}');return 0
    old['watch']=watch
    monkeypatch.setitem(scope,'ARTIFACT',artifact);monkeypatch.setitem(scope,'__file__',str(source))
    monkeypatch.setitem(scope,'helpers',lambda:(old,{},lambda path,*a:files[path],None));monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0)
    assert ROOT['launch']()==0 and seen==['retained-watch'] and '"replayed":false' in capsys.readouterr().out


def test_sources_and_prior_failed_helpers_remain_pinned():
    assert hashlib.sha256((FOLDER/'probe_rea_catalogue.py').read_bytes()).hexdigest()==ROOT['PROBE_SHA']
    assert hashlib.sha256((FOLDER/'qualify_main_local_mcp.py').read_bytes()).hexdigest()==ROOT['PREVIOUS_SHA']
    assert hashlib.sha256((FOLDER/'probe_main_local_mcp.py').read_bytes()).hexdigest()==PROBE['PROTOCOL_SHA']
