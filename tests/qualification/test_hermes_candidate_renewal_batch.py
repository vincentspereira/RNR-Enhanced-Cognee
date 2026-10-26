"""Scheduling proof, component pins and bounded gateway protocol."""
from pathlib import Path
import hashlib
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / 'integrations/hermes/deployment'
BATCH = runpy.run_path(str(DEPLOYMENT / 'qualify_launch_candidate_renewal.py'),run_name='batch_test')


def evidence():
    service = dict(LoadState='loaded',ActiveState='active',SubState='exited',Result='success',ExecMainStatus='0',
        User='root',InvocationID='b'*32,NoNewPrivileges='yes',ProtectSystem='strict',ProtectHome='yes',
        ExecMainStartTimestampMonotonic='16000000')
    timer = dict(LoadState='loaded',Result='success',LastTriggerUSecMonotonic='15999000')
    job = dict(complete=True,credential_published=True,invocation_id='b'*32)
    return service,timer,job


def test_bound_scheduled_publication_passes():
    BATCH['scheduling_proof'](*evidence())


@pytest.mark.parametrize('state,substate,start,finished', [
    ('inactive','dead','0',False),('activating','start','100',False),
    ('active','exited','100',True),('failed','failed','100',True),('inactive','dead','100',True)])
def test_scheduled_poll_waits_for_real_execution(state,substate,start,finished):
    assert BATCH['service_finished'](dict(ActiveState=state,SubState=substate,ExecMainStartTimestampMonotonic=start)) is finished


@pytest.mark.parametrize('field,value', [('LoadState','not-found'),('ActiveState','inactive'),('SubState','running'),
    ('Result','exit-code'),('ExecMainStatus','1'),('User','nobody'),('InvocationID','c'*32),
    ('NoNewPrivileges','no'),('ProtectSystem','no'),('ProtectHome','no'),('ExecMainStartTimestampMonotonic','0')])
def test_missing_or_unbound_service_proof_refused(field,value):
    service,timer,job = evidence()
    with pytest.raises(ValueError):
        BATCH['scheduling_proof'](dict(service,**{field:value}),timer,job)


@pytest.mark.parametrize('field,value',[('LastTriggerUSecMonotonic','0'),('LastTriggerUSecMonotonic','17000000'),
    ('LoadState','not-found'),('Result','failure')])
def test_timer_without_matching_trigger_refused(field,value):
    service,timer,job = evidence()
    with pytest.raises(ValueError):
        BATCH['scheduling_proof'](service,dict(timer,**{field:value}),job)


def test_publication_required_not_just_successful_process():
    service,timer,job = evidence()
    with pytest.raises(ValueError):
        BATCH['scheduling_proof'](service,timer,dict(job,credential_published=False))


def test_bounded_handshake_and_second_receipt_from_retained_process():
    code = 'import sys,time;print(\'{"ready":true}\',flush=True);sys.stdin.readline();print(\'{"complete":true}\',flush=True)'
    child = subprocess.Popen([sys.executable,'-I','-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    try:
        assert BATCH['bounded_line'](child,5) == {'ready':True}
        child.stdin.write(b'check\n')
        child.stdin.flush()
        assert BATCH['bounded_line'](child,5) == {'complete':True}
        assert child.wait(timeout=5) == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        child.stdin.close()
        child.stdout.close()


def test_oversized_child_receipt_refused():
    child = subprocess.Popen([sys.executable,'-I','-B','-c','print("x"*5000,flush=True)'],stdout=subprocess.PIPE)
    try:
        with pytest.raises(ValueError):
            BATCH['bounded_line'](child,5)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
        child.stdout.close()


def test_error_messages_and_private_fields_never_forwarded():
    result = BATCH['failure_diagnostic'](dict(complete=False,phase='native_reload',error_kind='PermissionError',
        message='invented private content',token='invented'))
    assert result == dict(phase='native_reload',error_kind='PermissionError')
    assert BATCH['failure_diagnostic'](dict(complete=False,phase='private contents',error_kind='private')) == {}


def test_component_pins_match_installed_stage_generation():
    stage = runpy.run_path(str(DEPLOYMENT / 'stage_launch_candidate_issuer.py'),run_name='stage_source_test')
    core,driver = stage['build_sources']((DEPLOYMENT / 'provision_pilot_access.py').read_bytes(),
        (DEPLOYMENT / 'renew_fleet_credentials.py').read_bytes(),(DEPLOYMENT / 'prepare_launch_candidate_provider_v2.py').read_bytes())
    assert hashlib.sha256(core).hexdigest() == BATCH['PINS']['provision_pilot_access.py']
    assert hashlib.sha256(driver).hexdigest() == BATCH['PINS']['renew_fleet_credentials.py']
    for name,digest in BATCH['PINS'].items():
        if name not in {'provision_pilot_access.py','renew_fleet_credentials.py'}:
            assert hashlib.sha256((DEPLOYMENT / name).read_bytes()).hexdigest() == digest


def test_owner_publication_preserves_private_files_and_unrelated_environment(monkeypatch):
    import json
    import os
    import tempfile
    import time
    from types import SimpleNamespace
    stage = runpy.run_path(str(DEPLOYMENT / 'stage_launch_candidate_issuer.py'),run_name='publication_core_test')
    core_raw,_ = stage['build_sources']((DEPLOYMENT / 'provision_pilot_access.py').read_bytes(),
        (DEPLOYMENT / 'renew_fleet_credentials.py').read_bytes(),(DEPLOYMENT / 'prepare_launch_candidate_provider_v2.py').read_bytes())
    core = stage['definitions'](core_raw)
    modules = {'provision_pilot_access.py':core}
    for name in ('fleet_credential_policy.py','renew_pilot_access.py','fleet_credential_lifecycle.py'):
        modules[name] = stage['definitions']((DEPLOYMENT / name).read_bytes())
    archive = ROOT / '.archive/candidate-renewal-tests'
    archive.mkdir(parents=True,exist_ok=True,mode=0o700)
    home = Path(tempfile.mkdtemp(dir=archive))
    profile = home / '.hermes'
    profile.mkdir(mode=0o700)
    entry = dict(name='candidate_invented',user='invented_owner',uid=os.geteuid(),home=str(home),profile=str(profile),
        tenant='qualification',project_id='candidate_invented',subject='invented',agent_id='invented',roles=['api_client'],
        lifetime_seconds=86400,origin='http://127.0.0.1:28080',executable=modules['fleet_credential_policy.py']['EXECUTABLE'],
        enabled=False,reload_qualified=False,launch_binding_qualified=False,backup_qualified=True,os_boundary_qualified=True)
    core['IDENTITY'] = dict(sub='invented',agent_id='invented',tenant='qualification',project_id='candidate_invented',roles=['api_client'],capture_policy='selected')
    now = int(time.time())
    key = b'invented-test-only-signing-key-not-a-host-secret'
    old = core['sign_claims'](dict(core['IDENTITY'],iat=now-30,exp=now+86370),key)
    bundle = core['make_bundle'](key,now)
    def api_status(token):
        if token not in {old,bundle['token']}:
            return 401,{}
        return 200,dict(ready=True,schema_version=3,encryption='AES-256-GCM',tenant_id='qualification',
            project_id='candidate_invented',subject='invented',active_records=0,pending_change_events=0)
    core['api_status'] = api_status
    original = b'INVENTED_UNRELATED=preserved\nENHANCED_COGNEE_ACCESS_TOKEN=' + old.encode() + b'\n'
    files = {'.env':original,'config.yaml':b'memory:\n  provider: enhanced_cognee\n',
        'auth.json':b'{"invented_oauth_marker":"preserve"}',
        'enhanced_cognee.json':json.dumps(dict(base_url='http://127.0.0.1:28080',capture_policy='selected',include_shared=True)).encode()}
    for name,raw in files.items():
        (profile / name).write_bytes(raw)
        (profile / name).chmod(0o600)
    function = BATCH['owner_publish']
    monkeypatch.setitem(function.__globals__,'components',lambda:modules)
    monkeypatch.setitem(function.__globals__,'restricted_entry',lambda _:SimpleNamespace(pw_uid=os.geteuid()))
    result = function(dict(entry=entry,bundle=bundle))
    assert result['credential_published'] is True
    assert result['preserved_settings_and_oauth'] is True
    assert (profile / '.env').read_bytes().startswith(b'INVENTED_UNRELATED=preserved\n')
    assert modules['renew_pilot_access.py']['environment'](core,(profile / '.env').read_bytes()) == bundle['token']
    assert all((profile / name).read_bytes() == raw for name,raw in files.items() if name != '.env')
    assert any(path.read_bytes() == original for path in profile.glob('.env-before-cognee-renew-*'))
