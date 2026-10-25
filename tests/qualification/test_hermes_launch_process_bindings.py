"""Launch classification and bounded privacy checks; no real process reads."""
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/inspect_launch_process_bindings.py'
spec = importlib.util.spec_from_file_location('launch_observer', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
HOME = '/home/invented'
PROFILE = HOME + '/.hermes/profiles/bot'


def test_only_explicit_profile_binding_and_no_raw_values():
    row = helper.observe(['hermes', '--profile', 'bot', 'gateway', 'run', '--token', 'invented-secret'],
                         ['UNRELATED_SECRET=invented-secret', 'HERMES_HOME=' + PROFILE], HOME, True)
    assert row['profile_home'] == PROFILE and row['kind'] == 'gateway'
    assert row['launch_binding_qualified'] is False
    assert 'invented-secret' not in json.dumps(row)


def test_missing_profile_is_not_assumed_from_default_or_active_profile():
    row = helper.observe(['hermes', 'gateway', 'run'], [], HOME, True)
    assert row['profile_home'] is None


def test_conflicting_and_duplicate_selectors_are_unresolved():
    for args, env in [(['--profile', 'other'], ['HERMES_HOME=' + PROFILE]),
                      (['--profile=bot', '--profile=bot'], []),
                      (['--profile=bot'], ['HERMES_HOME=/outside']),
                      (['--profile=bot'], ['HERMES_HOME=' + PROFILE] * 2)]:
        row = helper.observe(['hermes', *args, 'gateway', 'run'], env, HOME, True)
        assert row['profile_home'] is None and row['profile_selector_conflict'] is True


@pytest.mark.parametrize('path', ['/etc/secrets', HOME + '/.hermes/../secret',
    HOME + '/.hermes//bot', HOME + '/.hermes/profiles/lswa',
    HOME + '/.hermes/profiles/legal-social-frameworks', HOME + '/.hermes-other'])
def test_outside_paths_and_excluded_projects_not_admitted(path):
    assert helper.profile_path(path, HOME) is None


def test_arbitrary_process_not_classified():
    assert helper.observe(['python', 'unrelated.py'], ['SECRET=invented'], HOME, False) is None


def test_manager_is_only_a_candidate_not_a_profile_admission():
    row = helper.observe(['node', '/opt/pm2/bin/pm2'], [], HOME, False)
    assert row['kind'] == 'manager' and row['profile_home'] is None


@pytest.mark.parametrize('mutation', [dict(raw_argv=['invented-secret']), dict(pid=True),
    dict(launch_binding_qualified=True), dict(profile_home='/etc/secrets'), dict(pinned_executable=1)])
def test_child_receipt_cannot_widen_claim_or_return_raw_fields(mutation):
    row = helper.observe(['hermes', '--profile=bot', 'gateway', 'run'], [], HOME, True)
    row.update(pid=123)
    row.update(mutation)
    with pytest.raises(ValueError):
        helper.validate_child(dict(rows=[row], refused=0, races=0), HOME)


def test_unprivileged_parent_refused_before_protected_reads(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()
