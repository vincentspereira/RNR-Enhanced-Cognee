"""Admission, descriptor-only owner launch and immutable transport receipts."""
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
QUAL=runpy.run_path(str(DIRECTORY/'qualify_isolated_gateway_transport.py'),run_name='transport_qualification_tests')


def rows():
    return [dict(user='ecbot_'+format(i,'016x'),uid=3000+i,home='/var/lib/enhanced-cognee-profiles/'+format(i,'016x'),
        profile='/var/lib/enhanced-cognee-profiles/'+format(i,'016x')+'/.hermes',enabled=False) for i in range(1,41)]


@pytest.mark.parametrize('damage',[None,'backup_failed','unscheduled','member_drift','uid_duplicate','enabled','wrong_account'])
def test_only_backed_up_disabled_existing_identities_are_selected(monkeypatch,damage):
    selected=rows()
    members=[dict(kind='named',entry=dict(row)) for row in selected]+[dict(kind='main',entry={'uid':4001})]
    passed=dict(complete=True,operator_helper_sha256=QUAL['BACKUP_SHA'],source_revision=QUAL['BASE'].name,
        completed_profiles=41,selected_profiles=41,signed_encrypted_generations_created=41,
        scheduled_fleet_profile_backup_qualified=True,installed_daily_timer_enabled=True,
        journal_scheduling_proof={'verified':True},all_admission_policies_preserved_disabled=True,
        model_called=False,memory_api_called=False,keys_changed=False,private_keys_sent_to_owner=False,
        source_profiles_changed=False,fleet_launch_approved=False)
    if damage=='backup_failed':passed['complete']=False
    if damage=='unscheduled':passed['journal_scheduling_proof']['verified']=False
    if damage=='member_drift':members[0]['entry']['home']+='/changed'
    if damage=='uid_duplicate':selected[1]['uid']=selected[0]['uid']
    if damage=='enabled':selected[0]['enabled']=True
    accounts={row['user']:SimpleNamespace(pw_uid=row['uid'],pw_gid=row['uid'],pw_name=row['user'],
        pw_dir=row['home'],pw_shell='/usr/sbin/nologin') for row in selected}
    if damage=='wrong_account':accounts[selected[0]['user']].pw_uid+=500
    monkeypatch.setattr(QUAL['pwd'],'getpwnam',accounts.__getitem__)
    monkeypatch.setattr(QUAL['os'],'getgrouplist',lambda name,gid:[gid])
    read=lambda path,*a:json.dumps(members if path.name=='members.private.json' else passed).encode()
    policy={'load':lambda path:{'profiles':selected}}
    if damage:
        with pytest.raises(ValueError):QUAL['admission'](read,policy)
    else:assert QUAL['admission'](read,policy)==selected[:2]


@pytest.mark.parametrize('role,case',[('sender','roundtrip'),('receiver','roundtrip'),('sender','wrong_sender'),
    ('receiver','wrong_sender'),('sender','wrong_profile'),('receiver','wrong_profile')])
def test_receipt_requires_exact_expected_acceptance_or_kernel_denial(role,case):
    value=dict(complete=True,role=role,case=case,identity_restricted=True,accepted=case=='roundtrip',
        denied=role=='receiver' and case!='roundtrip',profile_contents_read=False,model_called=False)
    assert QUAL['receipt'](value,role,case)==value
    value['profile_contents_read']=True
    with pytest.raises(ValueError):QUAL['receipt'](value,role,case)


def test_child_diagnostics_never_echo_private_or_unexpected_fields():
    value=dict(phase='socket_identity',error_kind='TransportError',errno=13,category='connection_identity_denied',private='invented-private-data')
    projected=QUAL['failure_projection'](value,'receiver',1)
    assert projected==dict(role='receiver',phase='socket_identity',error_kind='TransportError',errno=13,exit_code=1,category='connection_identity_denied')
    assert 'invented-private-data' not in json.dumps(projected)
    assert QUAL['failure_projection']({'phase':[],'error_kind':{},'category':'invented-private-data'},'sender',2)==dict(role='sender',phase='startup',error_kind='other',exit_code=2)


def test_spawn_drops_groups_caps_and_passes_only_one_ipc_descriptor(monkeypatch):
    class Input(io.BytesIO):
        def close(self):self.closed_by_owner=True
    seen=[];stream=Input()
    def popen(args,**kwargs):seen.append((args,kwargs));return SimpleNamespace(stdin=stream)
    monkeypatch.setattr(QUAL['subprocess'],'Popen',popen)
    helper=runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'),run_name='transport_frame_helper')
    account=SimpleNamespace(pw_uid=3001,pw_gid=3001,pw_dir='/var/lib/enhanced-cognee-profiles/'+'a'*16)
    packet={'fd':17,'uid':3001}
    QUAL['spawn'](account,packet,helper,b'def child(): pass\n')
    args,kwargs=seen[0]
    assert args[:6]==['/usr/bin/setpriv','--no-new-privs','--inh-caps=-all','--ambient-caps=-all','--',QUAL['EXECUTABLE']]
    assert kwargs['user']==kwargs['group']==3001 and kwargs['extra_groups']==() and kwargs['pass_fds']==(17,)
    assert set(kwargs['env'])=={'PATH','HOME','LANG','PYTHONDONTWRITEBYTECODE'}
    assert stream.getvalue().endswith(QUAL['canonical'](packet)+b'\n') and stream.closed_by_owner


@pytest.mark.parametrize('complete',[True,False])
@pytest.mark.parametrize('tamper',[True,False])
def test_repeat_returns_retained_receipt_without_process_or_policy_replay(tmp_path,monkeypatch,capsys,complete,tamper):
    scope=QUAL['main'].__globals__;artifact=tmp_path/'artifact';artifact.mkdir();base=tmp_path/'backend'
    evidence=base/'operator-evidence/isolated-transport-invented';evidence.mkdir(parents=True)
    source=(DIRECTORY/'qualify_isolated_gateway_transport.py').read_bytes();digest=hashlib.sha256(source).hexdigest()
    (artifact/'qualify_isolated_gateway_transport.py').write_bytes(source)
    (artifact/'isolated_gateway_transport.py').write_bytes((DIRECTORY/'isolated_gateway_transport.py').read_bytes())
    bindings=QUAL['canonical'](rows()[:2]);binding_digest=hashlib.sha256(bindings).hexdigest()
    (artifact/'selected-bindings.private.json').write_bytes(bindings if not tamper else b'changed-bindings')
    context=dict(source_sha256=digest,transport_sha256=QUAL['TRANSPORT_SHA'],bindings_sha256=binding_digest,evidence=str(evidence))
    (artifact/'context.private.json').write_text(json.dumps(context))
    result=dict(complete=complete,operator_helper_sha256=digest,transport_component_sha256=QUAL['TRANSPORT_SHA'],source_revision=base.name,
        binding_manifest_sha256=binding_digest)
    (evidence/'summary.json').write_text(json.dumps(result))
    monkeypatch.setitem(scope,'ARTIFACT',artifact);monkeypatch.setitem(scope,'BASE',base)
    monkeypatch.setitem(scope,'_verified_source_bytes',source);monkeypatch.setattr(QUAL['os'],'geteuid',lambda:0)
    monkeypatch.setitem(scope,'definitions',lambda *a:{'read_file':lambda path,*a:path.read_bytes(),
        'private_write':lambda *a:pytest.fail('existing receipt rewritten')})
    monkeypatch.setitem(scope,'admission',lambda *a:pytest.fail('completed qualification replayed'))
    if tamper:
        with pytest.raises(ValueError):QUAL['main']()
    else:
        assert QUAL['main']()==(0 if complete else 1)
        assert json.loads(capsys.readouterr().out)==result


def test_source_pins_and_public_owner_frame_fit_native_protocol():
    transport=(DIRECTORY/'isolated_gateway_transport.py').read_bytes()
    assert hashlib.sha256(transport).hexdigest()==QUAL['TRANSPORT_SHA']
    code=QUAL['owner_program_source'](transport);compile(code,'<transport-child-test>','exec')
    helper=runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'),run_name='transport_frame_budget')
    helper['owner_program'](code)
    controller=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='transport_controller_pin')
    assert controller['ISOLATED_TRANSPORT_SHA']==hashlib.sha256((DIRECTORY/'qualify_isolated_gateway_transport.py').read_bytes()).hexdigest()


@pytest.mark.parametrize('case',['roundtrip','wrong_sender','wrong_profile'])
def test_native_child_protocol_runs_with_same_uid_fixture_only(monkeypatch,case):
    # Adapt ONLY fixture listener ownership/groups and launching the current
    # identity. Product admission still requires two distinct restricted UIDs.
    uid,gid=os.getuid(),os.getgid()
    # This is a same-user protocol fixture, not a test of the installed
    # Hermes interpreter. The production pin and installed-host gate remain.
    import sys
    monkeypatch.setitem(QUAL['spawn'].__globals__, 'EXECUTABLE', sys.executable)
    front_uid=uid+1 if case=='wrong_sender' else uid
    accounts={'ecbot_'+'1'*16:SimpleNamespace(pw_uid=front_uid,pw_gid=gid,pw_dir='/tmp'),
              'ecbot_'+'2'*16:SimpleNamespace(pw_uid=uid,pw_gid=gid,pw_dir='/tmp')}
    members=[{'user':name} for name in accounts]
    monkeypatch.setattr(QUAL['pwd'],'getpwnam',accounts.__getitem__)
    real_popen=QUAL['subprocess'].Popen
    def fixture_popen(args,**kwargs):
        assert kwargs.pop('user')==uid and kwargs.pop('group')==gid and kwargs.pop('extra_groups')==()
        return real_popen(args,**kwargs)
    monkeypatch.setattr(QUAL['subprocess'],'Popen',fixture_popen)
    source=QUAL['owner_program_source']((DIRECTORY/'isolated_gateway_transport.py').read_bytes())
    assert source.count(b'listener_uid=0,timeout=5')==source.count(b'and not os.getgroups()')==1
    source=source.replace(b'listener_uid=0,timeout=5',b'listener_uid=os.getuid(),timeout=5').replace(b'and not os.getgroups()',b'and True')
    helper=runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'),run_name='native_transport_fixture_frame')
    result=QUAL['run_case'](case,members,helper,source)
    assert result['complete'] and result['case']==case and not result['profile_contents_read'] and not result['native_turn_started']
