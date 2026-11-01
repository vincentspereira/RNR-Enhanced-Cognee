"""Private-scope admission, existing-binding deferral and typed owner proofs."""
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'integrations/hermes/deployment'
BATCH = runpy.run_path(str(DIRECTORY / 'qualify_launch_named_providers.py'),run_name='provider_batch_test')
PROVIDER = runpy.run_path(str(DIRECTORY / 'prepare_launch_candidate_provider_v2.py'),run_name='pinned_provider_test')


def fixture(existing_count=1):
    plans,records = [],[]
    for index in range(41):
        ident = f'{index:016x}'
        home = '/var/lib/enhanced-cognee-profiles/'+ident
        plans.append(dict(profile_id=ident,source_user='vincentspereira',source_profile='/home/vincentspereira/.hermes/profiles/invented_'+ident,
            enabled=False,existing_binding={'roles':['readonly']} if index < existing_count else None,
            proposed_user='ecbot_'+ident,proposed_home=home,proposed_binding=dict(sub='subject_'+ident,agent_id='agent_'+ident,
                tenant='hermes_private',project_id='profile_'+ident,roles=['api_client'],capture_policy='selected')))
        records.append(dict(profile_id=ident,user='ecbot_'+ident,home=home,complete=True,profile_started=False,paired_os_boundary_qualified=True))
    return plans,records


@pytest.mark.parametrize('existing_count',[0,1,2,3])
def test_every_profile_accounted_and_existing_binding_never_replaced(existing_count):
    plans,records = fixture(existing_count)
    selected,deferred = BATCH['selection'](plans,records,PROVIDER)
    assert len(selected) == 41-existing_count and len(deferred) == existing_count
    assert {row['profile_id'] for row,_ in selected}.isdisjoint({row['profile_id'] for row in deferred})
    assert all(scope['roles'] == ['api_client'] for _,scope in selected)
    assert all(item['reason'] == 'existing_binding_non_widening_admission_pending' for item in deferred)


@pytest.mark.parametrize('field,value',[('user','root'),('home','/unrelated'),('profile_started',True),
    ('paired_os_boundary_qualified',False),('complete',False)])
def test_wrong_identity_or_unqualified_staging_refused(field,value):
    plans,records = fixture()
    records[1][field] = value
    with pytest.raises(ValueError):
        BATCH['selection'](plans,records,PROVIDER)


def test_scope_widening_and_duplicate_scope_refused():
    plans,records = fixture(0)
    plans[0]['proposed_binding']['roles'] = ['operator']
    with pytest.raises(ValueError):
        BATCH['selection'](plans,records,PROVIDER)
    plans,records = fixture(0)
    plans[1]['proposed_binding']['project_id'] = plans[0]['proposed_binding']['project_id']
    with pytest.raises(ValueError):
        BATCH['selection'](plans,records,PROVIDER)


def owner():
    return dict(complete=True,candidate_modified=True,ordinary_credential_published=True,native_profile_file_scope_bound=True,
        own_scoped_api_verified=True,semantic_graph_verified=True,invented_probe_retracted_history_preserved=True,
        unrelated_settings_and_oauth_preserved=True,forbidden_network_attempts=0,chat_model_called=False,gateways_started=0)


def test_only_complete_scoped_owner_proof_accepted():
    BATCH['verified_owner'](owner())
    for field,value in [('semantic_graph_verified',False),('invented_probe_retracted_history_preserved',False),
        ('ordinary_credential_published',False),('forbidden_network_attempts',True),('chat_model_called',True),('gateways_started',True)]:
        with pytest.raises(ValueError):
            BATCH['verified_owner'](dict(owner(),**{field:value}))


def test_owner_payload_and_all_reused_sources_remain_exact():
    import hashlib
    assert hashlib.sha256((DIRECTORY / 'prepare_launch_candidate_provider_v2.py').read_bytes()).hexdigest() == BATCH['PROVIDER_SHA']
    assert hashlib.sha256((DIRECTORY / 'qualify_launch_candidate_renewal.py').read_bytes()).hexdigest() == BATCH['BATCH_SHA']
    helper = runpy.run_path(str(DIRECTORY / 'qualify_launch_isolated_accounts.py'),run_name='frame_test')
    helper['owner_program']((DIRECTORY / 'prepare_launch_candidate_provider_v2.py').read_bytes())
