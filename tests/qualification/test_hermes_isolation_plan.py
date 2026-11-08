"""Inert launch draft admission; no account, process or profile operations."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/prepare_launch_isolation_plan.py'
spec = importlib.util.spec_from_file_location('isolation_draft', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def row(profile='bot'):
    return dict(uid=1000, user='owner', home='/home/owner', profile_home='/home/owner/.hermes/profiles/' + profile)


def test_distinct_accounts_and_scopes_with_every_gate_closed():
    plans = helper.draft([row('one'), row('two')])
    assert len({plan['proposed_user'] for plan in plans}) == 2
    assert len({plan['proposed_binding']['project_id'] for plan in plans}) == 2
    for plan in plans:
        assert not any(plan['gates'].values())
        assert plan['enabled'] is False and plan['launch_unit_installed'] is False
        assert plan['launch_unit_execution_qualified'] is False
        assert plan['copy_status'] == 'not_started' and plan['proposed_uid'] is None
        assert 'Restart=no' in plan['launch_unit_draft']
        assert '[Install]' not in plan['launch_unit_draft']
        assert plan['requires_explicit_multiplex_configuration'] is True


def test_existing_readonly_identity_preserved_without_widening():
    entry = row()
    binding = dict(sub='existing', agent_id='existing', tenant='qualification', project_id='old',
                   roles=['readonly'], capture_policy='explicit')
    entry.update(token_signature_valid=True, verified_binding=binding)
    plan = helper.draft([entry])[0]
    assert plan['existing_binding'] == binding and plan['proposed_binding'] is None


@pytest.mark.parametrize('profile', ['../../outside', 'lswa', 'legal-social-frameworks', 'bot\nUser=root'])
def test_unsafe_or_excluded_source_profiles_refused(profile):
    with pytest.raises(ValueError):
        helper.draft([row(profile)])


def test_unit_fields_come_only_from_fixed_hash_and_protected_release():
    plan = helper.draft([row('ordinary')])[0]
    unit = plan['launch_unit_draft']
    assert '/home/owner' not in unit and 'ordinary' not in unit
    assert 'CapabilityBoundingSet=\n' in unit and 'NoNewPrivileges=yes' in unit
    assert '-I -B -m gateway.run' in unit


def test_duplicate_profile_refused():
    with pytest.raises(ValueError):
        helper.draft([row(), row()])


def test_unverified_binding_is_not_treated_as_current_authority():
    entry = row()
    entry.update(token_signature_valid=False, verified_binding={'roles': ['admin']})
    assert helper.draft([entry])[0]['existing_binding'] is None


def test_empty_inventory_and_privileged_roles_refused():
    with pytest.raises(ValueError):
        helper.draft([])
    entry = row()
    entry.update(token_signature_valid=True, verified_binding=dict(sub='x', agent_id='x', tenant='x',
        project_id='x', roles=['admin'], capture_policy='selected'))
    with pytest.raises(ValueError):
        helper.draft([entry])


def test_nonroot_parent_refused_before_protected_reads(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()
