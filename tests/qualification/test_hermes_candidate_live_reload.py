"""Strict retained-proof admission, live reload receipt and process cleanup."""
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/qualify_launch_candidate_reload.py'),run_name='live_reload_test')


def finish():
    return dict(complete=True,publication_replayed=False,credentials_issued=0,qualification_units_stopped=True,
        candidate_scheduled_publication_component_qualified=True,current_credential_authenticated=True,
        renewed_profile_recovery_qualified=True,all_admission_policies_preserved_disabled=True,
        candidate_headless_gateway_reload_qualified=False,journal_scheduling_proof={'verified':True})


def test_complete_retained_proof_admitted():
    HELPER['accepted_finish'](finish())


@pytest.mark.parametrize('field,value',[('complete',False),('publication_replayed',True),('credentials_issued',1),
    ('qualification_units_stopped',False),('candidate_scheduled_publication_component_qualified',False),
    ('current_credential_authenticated',False),('renewed_profile_recovery_qualified',False),
    ('all_admission_policies_preserved_disabled',False),('candidate_headless_gateway_reload_qualified',True),
    ('journal_scheduling_proof',{'verified':False})])
def test_no_unproved_or_already_completed_reload_admitted(field,value):
    with pytest.raises(ValueError):
        HELPER['accepted_finish'](dict(finish(),**{field:value}))


def reload():
    return dict(complete=True,id='a'*32,retained_native_gateway=True,unchanged_agent_reused=True,
        renewed_agent_rebuilt=True,candidate_token_bound=True,replacement_authenticated=True,
        settings_and_oauth_preserved=True,non_memory_network_attempts=0,chat_model_called=False,platform_adapters_started=0)


def test_live_reload_bound_to_run_and_actual_changed_agent():
    HELPER['accepted_reload'](reload(),'a'*32)
    for field,value in [('id','b'*32),('renewed_agent_rebuilt',False),('candidate_token_bound',False),
        ('settings_and_oauth_preserved',False),('non_memory_network_attempts',True),
        ('non_memory_network_attempts',1),('chat_model_called',True),('platform_adapters_started',True)]:
        with pytest.raises(ValueError):
            HELPER['accepted_reload'](dict(reload(),**{field:value}),'a'*32)


def test_retained_process_killed_and_waited_when_controller_fails():
    process = subprocess.Popen([sys.executable,'-I','-B','-c','import sys;sys.stdin.readline()'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    assert HELPER['terminate'](process) is True
    assert process.poll() is not None
    assert process.stdin.closed and process.stdout.closed


def test_completed_process_and_no_process_cleanup_pass():
    assert HELPER['terminate'](None) is True
    process = subprocess.Popen([sys.executable,'-I','-B','-c','pass'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    process.wait(timeout=5)
    assert HELPER['terminate'](process) is True
