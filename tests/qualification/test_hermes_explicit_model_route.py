"""Explicit endpoint binding avoids native ZAI probes without replacing a key."""
import hashlib
import io
import json
from pathlib import Path
import runpy

import pytest
from dotenv.parser import parse_stream

DIRECTORY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
ROUTE = runpy.run_path(str(DIRECTORY/'bind_launch_model_route.py'), run_name='explicit_model_route_tests')
BATCH = runpy.run_path(str(DIRECTORY/'complete_launch_named_runtime.py'), run_name='explicit_route_batch_tests')
KEY = 'invented-not-a-real-model-key'
URL = 'https://open.bigmodel.cn/api/paas/v4'


@pytest.mark.parametrize('environment,expected,reused', [
    ({}, {'ZAI_API_KEY':KEY,'GLM_BASE_URL':URL}, False),
    ({'ZAI_API_KEY':KEY}, {'GLM_BASE_URL':URL}, True),
    ({'GLM_BASE_URL':URL}, {'ZAI_API_KEY':KEY}, False),
    ({'ZAI_API_KEY':'','OTHER':'preserved'}, {'ZAI_API_KEY':KEY,'GLM_BASE_URL':URL}, False),
])
def test_only_missing_key_or_route_is_published(environment,expected,reused):
    assert ROUTE['environment_update'](environment,'ZAI_API_KEY',KEY,'/api/paas/v4') == (expected,reused)


@pytest.mark.parametrize('environment', [
    {'ZAI_API_KEY':'invented-independent-key'},
    {'GLM_BASE_URL':'https://invalid.example/api/paas/v4'},
    {'GLM_BASE_URL':'http://open.bigmodel.cn/api/paas/v4'},
    {'GLM_BASE_URL':'https://open.bigmodel.cn/api/coding/paas/v4'},
    {'GLM_BASE_URL':URL+'?changed=1'},
    {'ZAI_API_KEY':KEY,'GLM_BASE_URL':URL},
])
def test_conflicting_credentials_routes_and_already_completed_publication_refuse(environment):
    with pytest.raises(ValueError):
        ROUTE['environment_update'](environment,'ZAI_API_KEY',KEY,'/api/paas/v4')


@pytest.mark.parametrize('credential', [KEY, 'invented-backslash-\\-and-quote-"-value', 'invented-dollar-$-value'])
def test_environment_keeps_original_bytes_and_quotes_new_values(credential):
    original = b'# preserve comments\nOTHER="invented-oauth-is-preserved"'
    updated = ROUTE['append_environment'](original, {'ZAI_API_KEY':credential,'GLM_BASE_URL':URL})
    parsed = {r.key:r.value for r in parse_stream(io.StringIO(updated.decode())) if r.key}
    assert updated.startswith(original+b'\n')
    assert parsed == dict(OTHER='invented-oauth-is-preserved',ZAI_API_KEY=credential,GLM_BASE_URL=URL)


def test_new_source_pins_preserve_both_failed_attempts_and_owner_protocol():
    for name,digest in BATCH['PINS'].items():
        assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest() == digest
    for name,digest in [('finish_launch_named_runtime.py','6310e49d7d8b4128e3b24d73fcf1093e93433ab702e853a05a0513edbfd8003e'),
                        ('bind_launch_model_credential.py','bf24f095bc8ccfb037a4278e3f5efd72c33de14195367d1bb727fc809b454b01')]:
        assert hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest() == digest
    helper = runpy.run_path(str(DIRECTORY/'qualify_launch_isolated_accounts.py'),run_name='explicit_route_owner_protocol')
    helper['owner_program']((DIRECTORY/'bind_launch_model_route.py').read_bytes())
    assert BATCH['ARTIFACT'].name == 'operator-named-runtime-explicit-route-v4'
    control=runpy.run_path(str(DIRECTORY/'launch_control.py'),run_name='explicit_route_dispatch_test')
    assert hashlib.sha256((DIRECTORY/'complete_launch_named_runtime.py').read_bytes()).hexdigest() == control['ROUTES_SHA']


def test_successful_profile_cannot_be_admitted_to_failure_continuation():
    value = dict(complete=False,selected_profiles=40,qualified_profiles=1,failed_profiles=1,
        existing_model_bindings_localized=1,refreshed_candidate_restores_qualified=1,
        unattempted_profiles=38,credentials_issued=0,all_admission_policies_preserved_disabled=True)
    with pytest.raises(ValueError):
        BATCH['retained_failure'](lambda *args:json.dumps(value).encode())


def test_batch_preserves_first_key_and_recovery_then_backs_up_each_changed_route(tmp_path,monkeypatch):
    worker=BATCH['worker']; state=worker.__globals__
    artifact=tmp_path/'operator-named-runtime-explicit-route-v4';artifact.mkdir()
    for name in ('observe_launch_native_runtime.py','bind_launch_model_route.py'):
        (artifact/name).write_bytes(b'public-test-source')
    evidence=tmp_path/'operator-evidence/named-runtime-routes-invented';evidence.mkdir(parents=True)
    rows=[dict(profile_id=f'{n:016x}',user='ecbot_'+f'{n:016x}',home='/var/lib/enhanced-cognee-profiles/'+f'{n:016x}') for n in range(40)]
    events=[];writes={}
    def publish(row,*args):
        events.append(('route_and_fresh_restore',row['profile_id']))
        return {'existing_model_key_reused':row['profile_id']==rows[0]['profile_id']}
    def compare(*args):
        events.append(('check_prior_generation',rows[0]['profile_id']))
        return {'preserved':True}
    def definitions(path,digest):
        if path.name == 'observe_launch_native_runtime.py':return {'compare_generation':compare}
        if path.name == 'bind_launch_model_route.py':return dict(prepare=lambda *a:({}, {}, {}),PHASES={'identity'},bind_and_backup=publish)
        return {}
    def read(path,owner):
        if path.name == 'context.json':return json.dumps({'evidence':str(evidence)}).encode()
        if path.name == 'binding.private.json':return json.dumps(rows[0]).encode()
        return b'{"profiles":[{"enabled":false}]}'
    def native(row,*args):
        events.append(('native',row['profile_id']))
        return {'observation':{'blocked_context_discovery_attempts':1}}
    monkeypatch.setattr(BATCH['os'],'geteuid',lambda:0)
    for key,value in dict(BASE=tmp_path,ARTIFACT=artifact,__file__=str(artifact/'complete_launch_named_runtime.py'),
        definitions=definitions,selected=lambda *a:rows,
        retained_failure=lambda *a:(rows[0]['profile_id'],tmp_path/'original-generation'),
        sync_directory=lambda *a:None,native_probe=native).items():monkeypatch.setitem(state,key,value)
    assert worker(read,lambda path,raw:writes.setdefault(path,raw)) == 0
    result=json.loads(writes[evidence/'summary.json'])
    assert events[0] == ('check_prior_generation',rows[0]['profile_id'])
    assert [kind for kind,ident in events[1:]] == ['route_and_fresh_restore','native']*40
    assert result['existing_model_keys_preserved'] == result['reused_model_bindings'] == 1
    assert result['reused_profile_restores'] == 1 and result['new_model_keys_localized'] == 39
    assert result['explicit_model_routes_bound'] == result['new_candidate_generations'] == 40
    assert result['qualified_profiles'] == 40 and result['credentials_issued'] == 0
    assert result['all_admission_policies_preserved_disabled'] is True and result['fleet_launch_approved'] is False
