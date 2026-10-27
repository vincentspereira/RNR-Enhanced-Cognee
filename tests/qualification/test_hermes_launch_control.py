"""Read-only reconciliation classification and private metadata boundaries."""
from pathlib import Path
import os
import runpy
import sqlite3
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/launch_control.py'),run_name='control_test')


@pytest.mark.parametrize('owner,completed,receipt,record,expected',[
    ({'complete':False},False,False,None,'needs_review'),
    ({'complete':True},True,True,{'state':'retracted','version':2},'completed_preserve'),
    ({'complete':True},True,True,{'state':'active','version':3},'completed_changed_requires_review'),
    ({'complete':True,'layout':'staged'},False,False,None,'not_started_or_no_effects'),
    ({'complete':True,'layout':'partial_layout'},False,False,None,'partial_layout_needs_reconciliation'),
    ({'complete':True,'layout':'configured_or_partial'},False,False,{'state':'active','version':1},'unfinished_invented_probe'),
    ({'complete':True,'layout':'configured_or_partial'},False,True,{'state':'retracted','version':2},'finish_evidence_only'),
    ({'complete':True,'layout':'configured_or_partial'},False,False,{'state':'retracted','version':2},'finished_record_preserve_missing_proof'),
    ({'complete':True,'layout':'configured_or_partial'},False,False,{'state':'active','version':3},'unexpected_record_state_needs_review'),
])
def test_completed_work_never_becomes_a_write_retry(owner,completed,receipt,record,expected):
    assert HELPER['classification'](owner,completed,receipt,record) == expected


def test_nonce_requires_matching_unique_backup_pair():
    nonce = 'a'*16
    names = ['.env-before-provider-'+nonce,'.config-before-provider-'+nonce+'.yaml']
    assert HELPER['nonce_from_names'](names) == nonce
    assert HELPER['nonce_from_names'](names[:1]) is None
    with pytest.raises(ValueError):
        HELPER['nonce_from_names'](names+['.env-before-provider-'+'b'*16])


def test_main_metadata_never_follows_links_or_reads_excluded_project(tmp_path):
    profile = tmp_path / 'profile'
    profile.mkdir(mode=0o700)
    workspace = profile / 'workspace'
    workspace.mkdir()
    outside = tmp_path / 'excluded-target'
    outside.mkdir()
    (outside / 'private').write_bytes(b'not-read')
    (workspace / 'redirect').symlink_to(outside,target_is_directory=True)
    (workspace / 'legal-social-frameworks').mkdir()
    (workspace / 'legal-social-frameworks/private').write_bytes(b'not-read')
    (profile / 'profiles').mkdir()
    (profile / 'profiles/separate').write_bytes(b'not-read')
    (profile / '.env').write_text('ENHANCED_JWT_SECRET=invented-not-a-real-key\n')
    (profile / '.env').chmod(0o600)
    with sqlite3.connect(workspace / 'state.db') as connection:
        connection.execute('CREATE TABLE invented(value integer)')
    fd = os.open(profile,os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = HELPER['inspect_main_descriptor'](SimpleNamespace(pw_uid=os.geteuid()),fd)
    finally:
        os.close(fd)
    assert result['source_profiles_changed'] is False
    assert not any(row['name'] == 'profiles' for row in result['top_levels'])
    counts = next(row['metadata'] for row in result['top_levels'] if row['name'] == 'workspace')
    assert counts['links'] == counts['excluded'] == counts['sqlite_headers'] == 1
    assert result['privileged_environment_field_names'] == ['ENHANCED_JWT_SECRET']
    assert 'invented-not-a-real-key' not in str(result)


def test_private_read_refuses_redirects_and_unprotected_files(tmp_path):
    private = tmp_path / 'private'
    private.write_bytes(b'invented')
    private.chmod(0o600)
    assert HELPER['private_read'](private,os.geteuid()) == b'invented'
    private.chmod(0o644)
    with pytest.raises(ValueError):
        HELPER['private_read'](private,os.geteuid())
    link = tmp_path / 'link'
    link.symlink_to(private)
    with pytest.raises(OSError):
        HELPER['private_read'](link,os.geteuid())


def test_controller_fits_existing_restricted_owner_protocol():
    source = ROOT / 'integrations/hermes/deployment/launch_control.py'
    helper = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/qualify_launch_isolated_accounts.py'),run_name='owner_frame_test')
    helper['owner_program'](source.read_bytes())


def test_canonical_inspection_is_parameterized_metadata_only_and_readonly(monkeypatch):
    import asyncio
    import json
    import sys
    events = []
    class Transaction:
        async def __aenter__(self):
            return self
        async def __aexit__(self,*args):
            return False
    class Connection:
        def transaction(self,**kwargs):
            assert kwargs == {'readonly':True}
            return Transaction()
        async def fetch(self,sql,*args):
            assert sql.startswith('SELECT id,version,state,owner_subject,writer_agent')
            assert 'payload' not in sql and 'FOR UPDATE' not in sql
            assert args == ('qualification','invented_project','candidate-'+'a'*16)
            return [dict(id='invented',version=2,state='retracted',owner_subject='invented_subject',writer_agent='invented_agent')]
        async def close(self):
            events.append('closed')
    async def connect(url,**kwargs):
        assert kwargs['server_settings']['default_transaction_read_only'] == 'on'
        return Connection()
    monkeypatch.setitem(sys.modules,'asyncpg',SimpleNamespace(connect=connect))
    profiles = [dict(owner={'nonce':'a'*16},scope=dict(tenant='qualification',project_id='invented_project',
        sub='invented_subject',agent_id='invented_agent'))]
    asyncio.run(HELPER['read_record_metadata'](lambda *args:json.dumps({'ENHANCED_MEMORY_DATABASE_URL':'invented'}).encode(),profiles))
    assert profiles[0]['record'] == dict(id='invented',version=2,state='retracted')
    assert events == ['closed']


@pytest.mark.parametrize('model_outcome',[0,1,'preflight_failure'])
def test_prerequisite_batch_continues_independent_recovery_and_reports_both_results(monkeypatch,capsys,model_outcome):
    import json
    scope=HELPER['qualify_prerequisites'].__globals__;events=[]
    base=HELPER['BASE']
    def read(path,*args):
        if path.name=='context.json':return json.dumps({'evidence':str(base/'operator-evidence'/path.parent.name)}).encode()
        return b'{"complete":true,"fleet_launch_approved":false}'
    def module(path,digest):
        if path.name=='recover_launch_graph_operator.py':return {'read_file':read}
        def launch():
            events.append(path.name)
            if path.name=='finish_launch_model_scope.py':
                if model_outcome=='preflight_failure':raise ValueError('invented fixed refusal')
                return model_outcome
            return 0
        return dict(launch=launch,ARTIFACT=base/path.stem)
    monkeypatch.setattr(HELPER['os'],'geteuid',lambda:0)
    monkeypatch.setitem(scope,'definitions',module)
    result=HELPER['qualify_prerequisites']()
    value=json.loads(capsys.readouterr().out)
    assert events==['finish_launch_model_scope.py','qualify_launch_program_recovery.py']
    assert value['complete'] is (model_outcome==0) and result==(0 if model_outcome==0 else 1)
    assert value['components']['program_recovery']['complete'] is True
    assert value['components']['current_model']['complete'] is (model_outcome==0)
    assert value['fleet_launch_approved'] is False and value['actual_profile_admission_qualified'] is False
