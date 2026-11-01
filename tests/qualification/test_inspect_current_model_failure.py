"""Retained diagnosis prints no prompt, credential, response text or payload."""
import asyncio
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest

DIRECTORY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
MODULE=runpy.run_path(str(DIRECTORY/'inspect_launch_current_model_failure.py'),run_name='retained_model_inspection_tests')


def test_private_extra_fields_are_never_printed():
    private='invented-sensitive-field-must-not-escape'
    value=dict(complete=False,phase='native_turn',error_kind='GuardError',prompt=private,
        observation=dict(stage='capture',requests=dict(count=1,http_statuses=[400],failed_response=True,
            rate_limited=False,prefetched_evidence_delivered=False,returned_model_verified_requests=0,
            api_key=private,body=private),network=dict(memory_operations=2,model_dns=1,model_connections=1,
            metadata_denied=1,unexpected_denied=0,controls_denied=3,private_trace=private),
            files_equal={'.env':True,'config.yaml':True,'auth.json':False,'enhanced_cognee.json':True,'private_file':private}))
    result=MODULE['project'](value)
    assert private not in json.dumps(result)
    assert result['requests']['http_statuses']==[400] and result['network']['unexpected_denied']==0
    assert set(result['files_equal'])=={'.env','config.yaml','auth.json','enhanced_cognee.json'}


@pytest.mark.parametrize('bad',[True,-1,100001,'private-value',None,3.5])
def test_only_bounded_integer_counts_are_projected(bad):
    value=dict(complete=False,phase='agent',error_kind='ValueError',observation={'network':{'model_connections':bad}})
    assert MODULE['project'](value)['network']=={}


def test_unknown_phase_exception_and_invalid_http_status_are_hidden():
    value=dict(complete=False,phase='private-exception-text',error_kind='private-type',
        observation={'requests':{'http_statuses':[200,'private-value']}})
    result=MODULE['project'](value)
    assert result['phase']==result['error_kind']=='other' and result['requests']=={}


def test_canonical_metadata_query_is_fixed_scope_and_readonly(monkeypatch):
    closed=[];scope='zai_'+MODULE['IDENT']
    class Transaction:
        async def __aenter__(self):return self
        async def __aexit__(self,*unused):pass
    class Connection:
        def transaction(self,**kw):
            assert kw=={'readonly':True};return Transaction()
        async def fetch(self,sql,*args):
            assert args==('qualification',scope) and 'payload' not in sql and 'LIMIT 3' in sql
            assert sql.startswith('SELECT id,version,state,owner_subject,writer_agent')
            return [dict(id='not-printed',version=1,state='active',owner_subject=scope,writer_agent=scope)]
        async def fetchval(self,sql,*args):
            assert args==('qualification',scope) and sql.startswith('SELECT count(*)') and 'payload' not in sql
            return 1
        async def close(self):closed.append(True)
    async def connect(url,**kw):
        assert url=='invented-operator-dsn' and kw['server_settings']['default_transaction_read_only']=='on'
        return Connection()
    monkeypatch.setitem(sys.modules,'asyncpg',SimpleNamespace(connect=connect))
    result=asyncio.run(MODULE['canonical_metadata'](lambda *a:json.dumps({'ENHANCED_MEMORY_DATABASE_URL':'invented-operator-dsn'}).encode()))
    assert result['records_observed']==result['canonical_version_count']==1
    assert result['fixed_subjects_match'] is True and result['payloads_read'] is False
    assert 'not-printed' not in str(result) and 'invented-operator-dsn' not in str(result) and closed==[True]
