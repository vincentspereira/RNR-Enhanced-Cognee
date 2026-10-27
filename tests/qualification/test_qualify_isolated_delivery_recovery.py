"""Exact native admission, phase exit codes and immutable recovery evidence."""
import hashlib
import io
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
QUAL=runpy.run_path(str(DIRECTORY/'qualify_isolated_delivery_recovery.py'))


@pytest.mark.parametrize('phase',list(QUAL['PHASES']))
def test_each_owner_phase_requires_its_exact_forced_or_clean_exit(phase):
    status,flags=QUAL['PHASES'][phase]
    value=dict(dict.fromkeys(flags,True),complete=True,phase=phase)
    assert QUAL['receipt'](value,phase,status)==value
    with pytest.raises(ValueError):QUAL['receipt'](value,phase,1)
    with pytest.raises(ValueError):QUAL['receipt'](dict(value,private='invented-private'),phase,status)
    for flag in flags:
        altered=dict(value);altered[flag]=False
        with pytest.raises(ValueError):QUAL['receipt'](altered,phase,status)


@pytest.mark.parametrize('damage',[None,'failed','scope_drift','wrong_native','different_bindings','enabled'])
def test_crash_qualification_requires_completed_native_and_same_fixed_uids(monkeypatch,damage):
    scope=QUAL['prior_native_pass'].__globals__
    base=Path('/invented/base');artifact=base/'native';evidence=base/'operator-evidence/isolated-native-text-invented'
    rows=[{'user':'invented-one'},{'user':'invented-two'}]
    canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    native=dict(ARTIFACT=artifact,PUBLIC={'invented':'sha'},NATIVE={'invented-native':'sha'})
    binding=hashlib.sha256(canonical(rows)).hexdigest()
    context=dict(source_sha256=QUAL['NATIVE_QUAL_SHA'],component_hashes=native['PUBLIC'],native_source_hashes=native['NATIVE'],
        evidence=str(evidence),bindings_sha256=binding)
    result=dict(complete=True,operator_helper_sha256=QUAL['NATIVE_QUAL_SHA'],source_revision=base.name,
        component_hashes=native['PUBLIC'],binding_manifest_sha256=binding,distinct_restricted_uids=2,
        native_dm_text_ingress_component_qualified=True,native_authorization_and_pending_clarification_preserved=True,
        all_admission_policies_preserved_disabled=True,fleet_launch_approved=False)
    if damage=='failed':result['complete']=False
    if damage=='scope_drift':result['binding_manifest_sha256']='changed'
    if damage=='wrong_native':context['native_source_hashes']={}
    if damage=='different_bindings':context['bindings_sha256']='changed'
    if damage=='enabled':result['all_admission_policies_preserved_disabled']=False
    files={artifact/'context.private.json':canonical(context),artifact/'selected-bindings.private.json':canonical(rows),
        evidence/'summary.json':canonical(result)}
    monkeypatch.setitem(scope,'BASE',base)
    action=lambda:QUAL['prior_native_pass'](lambda path,*a:files[path],native,dict(canonical=canonical),rows)
    if damage:
        with pytest.raises(ValueError):action()
    else:assert action()==str(evidence)


@pytest.mark.parametrize('complete,tamper',[(True,False),(False,False),(True,True)])
def test_completed_or_failed_crash_probe_never_replays(monkeypatch,tmp_path,capsys,complete,tamper):
    scope=QUAL['main'].__globals__;base=tmp_path/'base';artifact=base/'artifact'
    artifact.mkdir(parents=True);evidence=base/'operator-evidence/isolated-delivery-invented';evidence.mkdir(parents=True)
    source=b'invented public source';source_sha=hashlib.sha256(source).hexdigest()
    (artifact/'qualify_isolated_delivery_recovery.py').write_bytes(source)
    for name in QUAL['PUBLIC']:(artifact/name).write_bytes((DIRECTORY/name).read_bytes())
    bindings=b'invented private bindings'
    (artifact/'selected-bindings.private.json').write_bytes(bindings if not tamper else b'changed')
    context=dict(source_sha256=source_sha,component_hashes=QUAL['PUBLIC'],bindings_sha256=hashlib.sha256(bindings).hexdigest(),evidence=str(evidence))
    (artifact/'context.private.json').write_text(json.dumps(context))
    result=dict(complete=complete,operator_helper_sha256=source_sha,source_revision=base.name,binding_manifest_sha256=context['bindings_sha256'])
    (evidence/'summary.json').write_text(json.dumps(result))
    native=runpy.run_path(str(DIRECTORY/'qualify_isolated_native_text_ingress.py'))
    transport=runpy.run_path(str(DIRECTORY/'qualify_isolated_gateway_transport.py'))
    def definitions(path,digest):
        if path.name=='qualify_isolated_native_text_ingress.py':return native
        if path.name=='qualify_isolated_gateway_transport.py':return transport
        assert path.name=='recover_launch_graph_operator.py'
        return dict(read_file=lambda path,*a:path.read_bytes(),private_write=lambda *a:pytest.fail('evidence changed'))
    monkeypatch.setitem(scope,'definitions',definitions);monkeypatch.setitem(scope,'BASE',base);monkeypatch.setitem(scope,'ARTIFACT',artifact)
    monkeypatch.setitem(scope,'_verified_source_bytes',source)
    monkeypatch.setattr(QUAL['os'],'geteuid',lambda:0);monkeypatch.setattr(QUAL['os'],'umask',lambda mask:None)
    monkeypatch.setattr(QUAL['resource'],'setrlimit',lambda *a:None)
    monkeypatch.setitem(scope,'run_phase',lambda *a:pytest.fail('owner process replayed'))
    if tamper:
        with pytest.raises(ValueError):QUAL['main']()
    else:
        assert QUAL['main']()==(0 if complete else 1)
        assert json.loads(capsys.readouterr().out)==result


def test_reviewed_components_and_controller_pin_exact_public_source():
    assert len(QUAL['PUBLIC'])==5
    for name,digest in QUAL['PUBLIC'].items():assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest
    controller=runpy.run_path(str(DIRECTORY/'launch_control.py'))
    assert controller['DELIVERY_RECOVERY_SHA']==hashlib.sha256((DIRECTORY/'qualify_isolated_delivery_recovery.py').read_bytes()).hexdigest()


@pytest.mark.parametrize('phase',['initial','finish','peer'])
def test_supervisor_drops_authority_and_returns_only_the_exact_phase_receipt(monkeypatch,phase):
    status,flags=QUAL['PHASES'][phase]
    value=dict(dict.fromkeys(flags,True),complete=True,phase=phase)
    accounts={name:SimpleNamespace(pw_uid=uid,pw_gid=uid,pw_dir='/invented/owner')
        for name,uid in [('ecbot_'+'1'*16,3001),('ecbot_'+'2'*16,3002)]}
    rows=[dict(user=name,uid=account.pw_uid) for name,account in accounts.items()]
    class Input(io.BytesIO):
        def close(self):pass
    process=SimpleNamespace(stdin=Input(),stdout=io.BytesIO(json.dumps(value).encode()),returncode=status,
        wait=lambda **kw:status,poll=lambda:status)
    captured={}
    def spawn(args,**kwargs):captured.update(args=args,**kwargs);return process
    monkeypatch.setattr(QUAL['pwd'],'getpwnam',accounts.__getitem__)
    monkeypatch.setattr(QUAL['subprocess'],'Popen',spawn)
    transport=dict(EXECUTABLE='/invented/native/python',canonical=lambda value:json.dumps(value).encode())
    helper=dict(owner_program=lambda raw:('invented-bootstrap',b'invented-public-source\n'))
    assert QUAL['run_phase'](phase,rows,'a'*32,transport,helper)==value
    assert captured['user']==(3001 if phase=='peer' else 3002)
    assert captured['group']==captured['user'] and captured['extra_groups']==()
    assert captured['args'][:5]==['/usr/bin/setpriv','--no-new-privs','--inh-caps=-all','--ambient-caps=-all','--']
    assert set(captured['env'])=={'PATH','HOME','LANG','PYTHONDONTWRITEBYTECODE'}
    assert 'pass_fds' not in captured and 'shell' not in captured
    supplied=json.loads(process.stdin.getvalue().splitlines()[1])
    assert set(supplied)=={'uid','gid','worker_uid','profile_id','run_id','phase'}
