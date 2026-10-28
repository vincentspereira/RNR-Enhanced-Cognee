"""Diagnostic stages must distinguish real identity refusal from source drift."""
import hashlib
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

FOLDER=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
CHILD=runpy.run_path(str(FOLDER/'diagnose_rea_owner_preflight.py'))
ROOT=runpy.run_path(str(FOLDER/'inspect_rea_program_failure.py'))


@pytest.mark.parametrize('failure',[None,'core','identity','file','comparison'])
def test_source_comparison_failure_is_not_mislabeled_as_identity(failure):
    expected={name:'a'*64 for name in CHILD['NAMES']}
    actual=dict(expected)
    if failure=='comparison':actual['.env']='b'*64
    def fail():raise ValueError('invented-sensitive-value-must-not-be-reported')
    def guard(packet):
        assert packet==dict(mode='verify_source',uid=os.geteuid(),gid=os.getegid())
        if failure=='identity':fail()
        return SimpleNamespace(pw_dir='/invented/source-owner')
    def files(path):
        assert path==Path('/invented/source-owner/.hermes')
        if failure=='file':raise PermissionError('invented-private-path-must-not-be-reported')
        return {'invented':'fixture-not-a-private-profile'}
    core=dict(guard=guard,files=files,fingerprints=lambda values:actual)
    result=CHILD['observe'](dict(uid=os.geteuid(),gid=os.getegid(),fingerprints=expected),fail if failure=='core' else lambda:core)
    assert result['complete'] is True and result['preflight_passed'] is (failure is None)
    assert result['profiles_changed'] is False and result['credentials_issued']==0
    assert 'invented-sensitive' not in json.dumps(result) and 'invented-private-path' not in json.dumps(result)
    assert 'a'*64 not in json.dumps(result) and 'b'*64 not in json.dumps(result)
    if failure=='core':assert result['phase']=='core_loading' and not result['core_loaded']
    if failure=='identity':assert result['phase']=='identity_verification' and not result['identity_verified']
    if failure=='file':assert result['phase']=='source_file_read' and result['identity_verified']
    if failure=='comparison':
        assert result['phase']=='complete' and result['identity_verified'] and result['source_files_read']
        assert result['source_files_equal']=={n:n!='.env' for n in sorted(CHILD['NAMES'])}
        assert 'error_kind' not in result


@pytest.mark.parametrize('damage',[None,'credentials','source','completed','running','program_checkpoint','program_archive'])
def test_only_the_exact_stopped_zero_effect_failure_is_inspected(monkeypatch,tmp_path,damage):
    base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence/rea-main-programs-invented';evidence.mkdir(parents=True)
    scope=ROOT['retained'].__globals__;monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    context=dict(source_sha256=ROOT['FAILED_SHA'],evidence=str(evidence))
    value=dict(operator_helper_sha256=ROOT['FAILED_SHA'],source_revision=base.name,complete=False,
        operator_job_stopped=True,credentials_issued=0,all_admission_policies_preserved_disabled=True,
        owner_diagnostic=dict(error_kind='ValueError',phase='identity'),source_profiles_changed=False,
        source_programs_changed=False,previous_candidates_changed=False,candidate_promoted=False,
        daily_backup_registry_changed=False,canonical_memory_edits=False,chat_model_called=False,
        rea_server_started=False,fleet_launch_approved=False,production_renewal_timer_enabled=False)
    if damage=='credentials':value['credentials_issued']=1
    if damage=='source':value['source_profiles_changed']=True
    if damage=='completed':value['complete']=True
    if damage=='running':value['operator_job_stopped']=False
    if damage=='program_checkpoint':(evidence/'public_programs.started.json').write_text('{}')
    if damage=='program_archive':(artifact/'ghidra.tar').write_bytes(b'invented')
    read=lambda path,*args:json.dumps(context if path.name=='context.private.json' else value).encode()
    if damage:
        with pytest.raises(ValueError):ROOT['retained'](read)
    else:assert ROOT['retained'](read)==evidence


def test_exact_public_pins_and_original_frozen_guard_are_preserved():
    assert ROOT['CHILD_SHA']==hashlib.sha256((FOLDER/'diagnose_rea_owner_preflight.py').read_bytes()).hexdigest()
    assert CHILD['FROZEN_SHA']==hashlib.sha256((FOLDER/'rea_candidate_owner.py').read_bytes()).hexdigest()
    assert ROOT['FAILED_SHA']==hashlib.sha256((FOLDER/'stage_rea_main_programs.py').read_bytes()).hexdigest()
    controller=runpy.run_path(str(FOLDER/'launch_control.py'))
    assert controller['REA_FAILURE_INSPECTION_SHA']==hashlib.sha256((FOLDER/'inspect_rea_program_failure.py').read_bytes()).hexdigest()
    protocol=runpy.run_path(str(FOLDER/'qualify_launch_isolated_accounts.py'))
    protocol['owner_program']((FOLDER/'diagnose_rea_owner_preflight.py').read_bytes())


def test_inspection_does_not_restart_units_or_stage_programs(monkeypatch,tmp_path,capsys):
    base=tmp_path/'base';artifact=base/'artifact';artifact.mkdir(parents=True)
    evidence=base/'operator-evidence';evidence.mkdir();live=base/'live';live_evidence=evidence/'main-live-invented'
    diagnostic=(FOLDER/'diagnose_rea_owner_preflight.py').read_bytes()
    files={live/'context.private.json':json.dumps({'source_sha256':'a'*64,'evidence':str(live_evidence)}).encode(),
        live_evidence/'source-configuration.private.json':json.dumps({'fingerprints':{'invented':'private-hash'}}).encode()}
    def read(path,*args):return files[path]
    writes=[]
    def write(path,raw):writes.append(path);assert path.parent.parent==evidence;files[path]=raw
    child_result=dict(complete=True,preflight_passed=False,identity_verified=True,source_fingerprints_match=False,
        profiles_changed=False,credentials_issued=0,model_called=False,memory_api_called=False)
    calls=[]
    def owner(account,source,packet,**kwargs):
        calls.append(packet);assert source==diagnostic and packet['mode']=='inspect'
        return child_result,b''
    c=dict(owner=owner,packet=lambda account,mode,**args:dict(mode=mode,**args))
    original=dict(common=lambda:c,support=lambda c:(read,write),metadata=lambda unit:{'MainPID':'0','ControlPID':'0','ActiveState':'inactive'},
        stopped=lambda state:state['MainPID']==state['ControlPID']=='0',UNIT='invented-existing-unit',LIVE=live,LIVE_SHA='a'*64)
    scope=ROOT['main'].__globals__;monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'definitions',lambda *args:original);monkeypatch.setitem(scope,'retained',lambda read:evidence/'rea-main-programs-invented')
    monkeypatch.setattr(ROOT['os'],'geteuid',lambda:0)
    monkeypatch.setattr(ROOT['pwd'],'getpwnam',lambda name:SimpleNamespace(pw_uid=1000,pw_gid=1000))
    assert ROOT['main']()==0
    result=json.loads(capsys.readouterr().out)
    assert result['complete'] and not result['preflight']['preflight_passed']
    assert result['services_started'] is result['programs_staged'] is result['effectful_retry'] is False
    assert result['credentials_issued']==0 and len(calls)==len(writes)==1
    assert 'private-hash' not in json.dumps(result)
