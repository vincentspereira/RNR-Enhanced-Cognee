"""Bounded, redacted inspection of one retained model-binding failure."""
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/inspect_launch_model_binding_failure.py'),
                        run_name='failure_inspection_tests')
GLOBALS = MODULE['main'].__globals__


def fixture(tmp_path):
    evidence = tmp_path / 'operator-evidence/named-runtime-models-grkvr08r'
    profile = evidence / ('a' * 16)
    profile.mkdir(parents=True)
    for name in ('child.failure.json', 'unit.started.json', 'model-binding.receipt.json',
                 'model-profile-recovery.json'):
        (profile / name).touch()
    values = {
        evidence / 'summary.json': dict(phase='repair_model_bindings', complete=False,
            selected_profiles=40, failed_profiles=1, unattempted_profiles=39),
        profile / 'child.failure.json': dict(phase='configured_route_resolution', error_kind='AuthError'),
        profile / 'unit.started.json': dict(unit='ec-named-runtime-' + 'b' * 32 + '.service'),
        profile / 'model-binding.receipt.json': dict(complete=True, existing_model_credential_bound=True,
            configured_primary_route_resolved=True, unrelated_environment_and_oauth_preserved=True,
            candidate_model_auth_metadata_may_change=True, source_profile_changed=False,
            model_called=False, credentials_generated=0),
        profile / 'model-profile-recovery.json': dict(complete=True,
            generation='/var/backups/enhanced-cognee/hermes_candidate_renewed_' + 'c' * 32 + '.tar.age'),
    }
    return evidence, values


def test_inspection_prints_only_fixed_diagnostics_and_never_candidate_values(tmp_path, monkeypatch, capsys):
    evidence, values = fixture(tmp_path)
    monkeypatch.setitem(GLOBALS, 'EVIDENCE', evidence)
    monkeypatch.setattr(GLOBALS['sys'], 'argv', ['inspect_launch_model_binding_failure.py'])
    monkeypatch.setattr(GLOBALS['os'], 'geteuid', lambda: 0)
    monkeypatch.setitem(GLOBALS, 'read_support', lambda: lambda path, owner: json.dumps(values[Path(path)]).encode())
    monkeypatch.setattr(GLOBALS['subprocess'], 'run', lambda *args, **kwargs: SimpleNamespace(stdout=(
        b'LoadState=loaded\nActiveState=failed\nSubState=failed\nResult=exit-code\n'
        b'ExecMainStatus=1\nMainPID=0\nControlPID=0\n')))
    assert MODULE['main']() == 0
    output = json.loads(capsys.readouterr().out)
    assert output['failure_phase'] == 'configured_route_resolution'
    assert output['failure_kind'] == 'AuthError'
    assert output['encrypted_restore_qualified'] is True
    assert output['source_profile_preserved'] is True
    assert output['fleet_launch_approved'] is False
    assert set(output) == {'complete', 'stage', 'source_revision', 'failed_count', 'untouched_count',
        'failure_phase', 'failure_kind', 'http_status', 'model_binding_receipt_complete',
        'configured_primary_route_resolved', 'source_profile_preserved', 'model_called',
        'encrypted_restore_qualified', 'service_state', 'candidate_generation_recorded',
        'credentials_printed', 'fleet_launch_approved'}


def test_inspection_rejects_unknown_failure_phase_without_printing_it(tmp_path, monkeypatch, capsys):
    evidence, values = fixture(tmp_path)
    profile = next(path for path in evidence.iterdir() if path.is_dir())
    values[profile / 'child.failure.json']['phase'] = 'secret-bearing-invented-detail'
    monkeypatch.setitem(GLOBALS, 'EVIDENCE', evidence)
    monkeypatch.setattr(GLOBALS['sys'], 'argv', ['inspect_launch_model_binding_failure.py'])
    monkeypatch.setattr(GLOBALS['os'], 'geteuid', lambda: 0)
    monkeypatch.setitem(GLOBALS, 'read_support', lambda: lambda path, owner: json.dumps(values[Path(path)]).encode())
    # Refusal remains generic; unknown journal or child text is never forwarded.
    monkeypatch.setattr(GLOBALS['subprocess'], 'run', lambda *args, **kwargs: pytest.fail('must reject before systemctl'))
    with pytest.raises(ValueError):
        MODULE['main']()
    assert capsys.readouterr().out == ''
