"""Exact executable bounds and zero-effect continuation without guard changes."""
import hashlib
import json
from pathlib import Path
import runpy
import stat
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
MODULE=runpy.run_path(str(FOLDER/'continue_main_rea_mcp.py'))


@pytest.mark.parametrize('damage',[None,'smaller','larger','owner','writable','symlink','hardlink'])
def test_node_uses_its_exact_known_size_and_original_integrity_guards(damage):
    value=SimpleNamespace(st_mode=stat.S_IFREG|0o755,st_uid=0,st_nlink=1,st_size=MODULE['NODE_BYTES'])
    assert value.st_size>16*1024**2
    if damage=='smaller':value.st_size-=1
    if damage=='larger':value.st_size+=1
    if damage=='owner':value.st_uid=1000
    if damage=='writable':value.st_mode|=0o020
    if damage=='symlink':value.st_mode=stat.S_IFLNK|0o777
    if damage=='hardlink':value.st_nlink=2
    assert bool(MODULE['node_shape'](value)) is (damage is None)


def test_only_node_gets_new_bound_and_scripts_keep_existing_validator(monkeypatch):
    scope=MODULE['prepared'].__globals__;seen=[]
    namespace={'public_pin':lambda path,digest:seen.append(('original',path,digest)),'retained':lambda old,read:seen.append(('original_retained',))}
    monkeypatch.setitem(scope,'source',lambda:namespace)
    monkeypatch.setitem(scope,'verified_node',lambda path,digest:seen.append(('node',path,digest)))
    monkeypatch.setitem(scope,'retained_refusal',lambda *a:seen.append(('refusal_verified',)))
    configured=MODULE['prepared']()
    configured['public_pin'](MODULE['NODE'],MODULE['NODE_SHA'])
    configured['public_pin'](Path('/opt/invented/script.py'),'invented-hash')
    configured['retained']({},None)
    assert seen==[('node',MODULE['NODE'],MODULE['NODE_SHA']),('original',Path('/opt/invented/script.py'),'invented-hash'),('refusal_verified',),('original_retained',)]
    assert configured['ARTIFACT']==MODULE['ARTIFACT']!=MODULE['PREVIOUS'] and configured['UNIT']!=MODULE['PREVIOUS_UNIT']


@pytest.mark.parametrize('damage',[None,'digest','running','phase','issued','boolean_counter','new_copy','key_read','profile_changed','admitted','proof_driver','proof_unit','receipt'])
def test_only_exact_stopped_pin_refusal_with_no_new_probe_can_continue(monkeypatch,tmp_path,damage):
    scope=MODULE['retained_refusal'].__globals__;base=tmp_path/'base';previous=base/'previous';refusal=base/'operator-evidence/refusal';refusal.mkdir(parents=True)
    programs=tmp_path/'programs';programs.mkdir();ident='a'*32
    for name,value in dict(BASE=base,PREVIOUS=previous,REFUSAL=refusal).items():monkeypatch.setitem(scope,name,value)
    context=dict(source_sha256=MODULE['PREVIOUS_SHA'],evidence=str(refusal),id=ident)
    result=dict(source_revision=base.name,operator_helper_sha256=MODULE['PREVIOUS_SHA'],evidence=str(refusal),complete=False,
        checkpoint='public_code_pins',error_kind='ValueError',category='rea_catalogue_finish_incomplete_preserve_evidence',
        credentials_issued=0,new_package_copies=0,external_platform_sends=0,platform_adapters_started=0,protected_public_programs_reused=2)
    result.update({k:True for k in ('operator_job_stopped','original_failure_preserved','original_main_candidate_pass_preserved','all_admission_policies_preserved_disabled')})
    result.update({k:False for k in ('keys_read','model_called','memory_api_called','filesystem_replayed','full_public_readback_replayed',
        'java_ghidra_proof_replayed','source_profiles_changed','previous_candidates_changed','main_tool_program_coverage_qualified',
        'actual_profile_admission_qualified','production_dispatch_qualified','production_renewal_timer_enabled','fleet_launch_approved')})
    if damage=='digest':context['source_sha256']='wrong'
    if damage=='phase':result['checkpoint']='rea_catalogue_only'
    if damage=='issued':result['credentials_issued']=2
    if damage=='boolean_counter':result['credentials_issued']=False
    if damage=='new_copy':result['new_package_copies']=1
    if damage=='key_read':result['keys_read']=True
    if damage=='profile_changed':result['source_profiles_changed']=True
    if damage=='admitted':result['fleet_launch_approved']=True
    if damage=='proof_driver':(programs/('mcp-driver-'+ident)).mkdir()
    if damage=='receipt':(refusal/'rea-component-receipt.json').write_text('{}')
    data={previous/'context.private.json':json.dumps(context).encode(),refusal/'finish.summary.json':json.dumps(result).encode()}
    def metadata(unit):
        if unit==MODULE['PREVIOUS_UNIT']:return {'ActiveState':'active' if damage=='running' else 'inactive','SubState':'running' if damage=='running' else 'dead'}
        return {'LoadState':'loaded' if damage=='proof_unit' else 'not-found'}
    namespace={'stopped':lambda state:state['ActiveState']=='inactive' and state['SubState']=='dead'}
    old={'PROGRAM_ROOT':programs,'metadata':metadata}
    if damage:
        with pytest.raises(ValueError):MODULE['retained_refusal'](namespace,old,lambda path,*a:data[path])
    else:assert MODULE['retained_refusal'](namespace,old,lambda path,*a:data[path])==result


@pytest.mark.parametrize('changed',[False,True])
def test_worker_checks_older_failure_bytes_after_finish(monkeypatch,changed):
    scope=MODULE['main'].__globals__;seen=[]
    paths=[MODULE['PREVIOUS']/'context.private.json',MODULE['PREVIOUS']/'sources.json',MODULE['REFUSAL']/'summary.json',MODULE['REFUSAL']/'finish.summary.json']
    files={path:('unchanged-'+str(index)).encode() for index,path in enumerate(paths)}
    def worker():
        seen.append('finish-worker')
        if changed:files[paths[-1]]=b'changed'
        return 0
    namespace={'helpers':lambda:({},None,lambda path,*a:files[path],None),'worker':worker}
    monkeypatch.setitem(scope,'prepared',lambda:namespace);monkeypatch.setitem(scope,'retained_refusal',lambda *a:seen.append('prior_refusal_verified'))
    monkeypatch.setattr(MODULE['os'],'geteuid',lambda:0);monkeypatch.setattr(MODULE['sys'],'argv',['continue','--worker'])
    if changed:
        with pytest.raises(ValueError):MODULE['main']()
    else:assert MODULE['main']()==0
    assert seen==['prior_refusal_verified','finish-worker']


def test_invalid_node_path_or_digest_refuses_before_opening():
    with pytest.raises(ValueError):MODULE['verified_node'](Path('/tmp/caller-node'),MODULE['NODE_SHA'])
    with pytest.raises(ValueError):MODULE['verified_node'](MODULE['NODE'],'wrong')


def test_original_frozen_helper_pin_is_unchanged():
    assert hashlib.sha256((FOLDER/'finish_main_rea_mcp.py').read_bytes()).hexdigest()==MODULE['PREVIOUS_SHA']
