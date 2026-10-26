"""Strict untouched-only resume and detached operator-job boundaries."""
from pathlib import Path
import hashlib
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'integrations/hermes/deployment'
MODULE = runpy.run_path(str(DIRECTORY / 'resume_launch_named_providers.py'),run_name='resume_test')


def fixture():
    selected,snapshot = [],[]
    for index in range(39):
        ident=f'{index:016x}'
        scope={'project_id':'profile_'+ident}
        selected.append(({'profile_id':ident},scope))
        complete=index<30
        snapshot.append(dict(profile_id=ident,scope=scope,
            classification='completed_preserve' if complete else 'not_started_or_no_effects',
            completed_summary=complete,owner_receipt_complete=complete,
            record={'state':'retracted','version':2} if complete else None,
            owner=dict(layout='configured_or_partial' if complete else 'staged',original_candidate_exists=not complete,nonce=None)))
    return selected,snapshot


def test_only_nine_untouched_profiles_selected():
    pending,preserved=MODULE['resume_selection'](*fixture())
    assert len(pending)==9 and len(preserved)==30
    assert not {row['profile_id'] for row,_ in pending}&set(preserved)


@pytest.mark.parametrize('change',['already_started','missing_receipt','wrong_scope','changed_record','ambiguous_layout'])
def test_ambiguous_or_finished_work_never_replayed(change):
    selected,snapshot=fixture()
    if change=='already_started': snapshot[-1]['classification']='unfinished_invented_probe'
    elif change=='missing_receipt': snapshot[0]['owner_receipt_complete']=False
    elif change=='wrong_scope': snapshot[-1]['scope']={'project_id':'other'}
    elif change=='changed_record': snapshot[0]['record']['version']=3
    else: snapshot[-1]['owner']['layout']='partial_layout'
    with pytest.raises(ValueError): MODULE['resume_selection'](selected,snapshot)


def test_operator_job_permissions_are_scoped_and_preserve_restores():
    homes=['/var/lib/enhanced-cognee-profiles/'+f'{i:016x}' for i in range(9)]
    properties=MODULE['service_properties'](homes)
    assert properties['NoNewPrivileges']=='yes' and properties['ProtectHome']=='yes'
    assert properties['ProtectSystem']=='strict' and properties['KillMode']=='control-group'
    assert properties['Restart']=='no' and properties['PrivateTmp']=='no'
    assert 'CAP_KILL' in properties['CapabilityBoundingSet']
    assert '/tmp' in properties['ReadWritePaths'].split()
    assert all(home in properties['ReadWritePaths'].split() for home in homes)
    with pytest.raises(ValueError): MODULE['service_properties'](['/unrelated']*9)


@pytest.mark.parametrize('state,sub,start,summary,finished',[
    ('inactive','dead','0',None,False),('activating','start','1',None,False),
    ('active','exited','1',{},True),('failed','failed','1',None,True),
    ('inactive','dead','0',{'complete':True},True)])
def test_reattach_does_not_restart_job_or_wait_forever_after_collection(state,sub,start,summary,finished):
    assert MODULE['job_finished'](dict(ActiveState=state,SubState=sub,ExecMainStartTimestampMonotonic=start),summary) is finished


def test_dispatcher_pins_resume_source_and_owner_program_still_fits():
    control=runpy.run_path(str(DIRECTORY / 'launch_control.py'),run_name='dispatcher_test')
    raw=(DIRECTORY / 'resume_launch_named_providers.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==control['RESUME_SHA']
    module=control['definitions'](DIRECTORY / 'resume_launch_named_providers.py',control['RESUME_SHA'])
    assert module['_verified_source_bytes']==raw
    account=runpy.run_path(str(DIRECTORY / 'qualify_launch_isolated_accounts.py'),run_name='owner_frame_test')
    account['owner_program']((DIRECTORY / 'launch_control.py').read_bytes())


def test_main_summary_reports_buckets_without_private_names():
    result=MODULE['main_buckets'](dict(top_levels=[
        dict(name='workspace',kind='directory',metadata=dict(entries=5,bytes=100,links=1,hardlinks=2,observation_complete=False)),
        dict(name='invented-private-project-name',kind='link_not_followed'),
        dict(name='auth.json',kind='file',bytes=42)]))
    assert 'invented-private-project-name' not in str(result)
    assert result['workspace']['observation_complete'] is False
    assert result['other']['links']==1 and result['auth.json']['bytes_observed']==42


def test_ctrl_c_detaches_view_without_stopping_job(tmp_path,monkeypatch,capsys):
    import json
    evidence=tmp_path/'operator-evidence/provider-resume-invented'
    evidence.mkdir(parents=True)
    watch=MODULE['watch']
    monkeypatch.setitem(watch.__globals__,'BASE',tmp_path)
    def interrupt(): raise KeyboardInterrupt()
    monkeypatch.setitem(watch.__globals__,'service_metadata',interrupt)
    def forbidden(*args,**kwargs): raise AssertionError('view must not stop the job')
    monkeypatch.setattr(MODULE['subprocess'],'run',forbidden)
    assert watch(lambda *args:json.dumps(dict(evidence=str(evidence),unit=MODULE['UNIT'])).encode())==0
    result=json.loads(capsys.readouterr().out)
    assert result['detached'] is True and result['job_continues'] is True
