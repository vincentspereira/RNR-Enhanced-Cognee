"""No-replay finish admission and collected-unit cleanup semantics."""
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/finish_launch_candidate_publication.py'),run_name='retained_finish_test')


@pytest.mark.parametrize('load,state,sub,pid,accepted',[
    ('not-found','inactive','dead','0',True),('loaded','inactive','dead','0',True),
    ('loaded','active','exited','0',False),('loaded','active','running','123',False),
    ('loaded','inactive','dead','123',False),('loaded','failed','failed','0',False),
    ('error','inactive','dead','0',False)])
def test_cleanup_requires_verified_absence_of_running_unit(load,state,sub,pid,accepted):
    assert MODULE['stopped'](dict(LoadState=load,ActiveState=state,SubState=sub,MainPID=pid)) is accepted


def receipts():
    prior = dict(complete=False,operator_helper_sha256=MODULE['BATCH_SHA'],failure_phase='scheduled_candidate_publication',
        scheduled_publication_observed=True,candidate_ordinary_credential_changed=True)
    context = dict(evidence=str(MODULE['FAILED']))
    job = dict(complete=True,id=MODULE['IDENT'],credential_published=True,bound_root_completion_verified=True,
        settings_and_oauth_preserved=True,invocation_id='a'*32)
    return prior,context,job


def test_matching_published_attempt_can_finish_without_new_publication():
    MODULE['retained_binding'](*receipts())


@pytest.mark.parametrize('field,value',[('complete',False),('id','b'*32),('credential_published',False),
    ('bound_root_completion_verified',False),('settings_and_oauth_preserved',False),('invocation_id','')])
def test_incomplete_or_other_job_cannot_be_salvaged(field,value):
    prior,context,job = receipts()
    with pytest.raises(ValueError):
        MODULE['retained_binding'](prior,context,dict(job,**{field:value}))


def test_other_failure_or_context_refused():
    prior,context,job = receipts()
    with pytest.raises(ValueError):
        MODULE['retained_binding'](dict(prior,failure_phase='retained_native_gateway_reload'),context,job)
    with pytest.raises(ValueError):
        MODULE['retained_binding'](prior,dict(evidence='/unreviewed'),job)
