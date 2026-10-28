"""Observe the original model guards without relaxing them or exposing values."""
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

FOLDER = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
INSPECTION = runpy.run_path(str(FOLDER / 'inspect_rea_continuation_failure.py'))


@pytest.mark.parametrize('damage', [None, 'key_changed', 'fixture_changed', 'endpoint_changed',
                                  'source_exception', 'runtime_changed', 'fixture_shape', 'source_body'])
def test_actual_frozen_model_checks_are_observed_without_receipt_or_key_output(monkeypatch, tmp_path, damage):
    # Use the exact production function, not an imitation of its comparisons.
    loaded = runpy.run_path(str(FOLDER / 'refresh_live_main_candidate.py'))
    c = loaded['runtime_model'].__globals__
    package = tmp_path / 'package'
    package.mkdir()
    for name in ('bind_launch_model_route.py', 'inspect_qualified_model_key.py'):
        (package / name).write_bytes((FOLDER / name).read_bytes())
    completed = tmp_path / 'operator-evidence/model-recall-finish-fdu97vca/summary.json'
    completed.parent.mkdir(parents=True)
    completed.write_text(json.dumps(dict(complete=True,
        operator_helper_sha256='ddf3b82e294b7b723463a82a66098fb6d52edd370f9fd1344696368b500a0123',
        current_configured_model_fresh_process_recall_qualified=True)))
    events = []
    key = 'invented-source-key-DO-NOT-OUTPUT'
    fixture_key = 'invented-different-key-DO-NOT-OUTPUT' if damage == 'key_changed' else key

    def owner(account, source, packet, **kwargs):
        events.append(dict(packet=packet, user=account.pw_name))
        if packet == {'mode': 'read_source'}:
            if damage == 'source_exception':
                error = ValueError('invented-private-error-DO-NOT-OUTPUT')
                error.owner_diagnostic = dict(error_kind='PermissionError', phase='source_configuration')
                raise error
            return dict(complete=True, key=key, endpoint_path='/invented-other' if damage == 'endpoint_changed' else '/api/coding/paas/v4'), (b'invented-extra-body' if damage == 'source_body' else b'')
        assert set(packet) == {'completed_ns'} and account.pw_name == 'hermes-runtime'
        value = dict(complete=True, model_key_sha256=hashlib.sha256(fixture_key.encode()).hexdigest(),
                     fixture_unchanged_since_receipt=damage != 'fixture_changed')
        if damage == 'fixture_shape':
            value['unexpected_private_field'] = 'invented-DO-NOT-OUTPUT'
        return value, b''

    def verify_runtime():
        if damage == 'runtime_changed':
            raise ValueError('invented-public-runtime-change')

    for name, value in dict(BASE=tmp_path, PACKAGE=package, owner=owner).items():
        monkeypatch.setitem(c, name, value)
    monkeypatch.setattr(c['pwd'], 'getpwnam', lambda name: SimpleNamespace(pw_name=name))
    evidence = tmp_path / 'new-inspection'
    result = INSPECTION['observe_binding'](c, {'verify_runtime': verify_runtime}, lambda path, *a: path.read_bytes(), evidence)
    assert result['inspection_complete'] is True and result['model_binding_verified'] is (damage is None)
    assert c['owner'] is owner and not evidence.exists()
    output = json.dumps(result)
    for forbidden in (key, fixture_key, hashlib.sha256(key.encode()).hexdigest(),
                      hashlib.sha256(fixture_key.encode()).hexdigest(), 'invented-private-error', 'invented-DO-NOT-OUTPUT'):
        assert forbidden not in output
    if damage == 'key_changed':
        assert result['qualified_key_matches_current_source'] is False
        assert result['fixture_unchanged_since_receipt'] is True
    if damage == 'source_exception':
        assert result['owner_error_kind'] == 'PermissionError' and result['owner_phase'] == 'source_configuration'
    if not damage:
        assert result['qualified_key_matches_current_source'] is result['private_receipt_verified'] is True
    assert [event['packet'].get('mode', 'fixture_digest') for event in events] == (
        [] if damage == 'runtime_changed' else ['read_source'] if damage in {'endpoint_changed', 'source_exception', 'source_body'}
        else ['read_source', 'fixture_digest'])


@pytest.mark.parametrize('damage', [None, 'credentials', 'generation', 'profile_changed', 'running', 'staging_started', 'archive_present'])
def test_inspection_admission_requires_stopped_zero_effect_attempt(monkeypatch, tmp_path, damage):
    scope = INSPECTION['retained'].__globals__
    base = tmp_path / 'base'; artifact = base / 'artifact'; artifact.mkdir(parents=True)
    evidence = base / 'operator-evidence/rea-main-programs-invented'; evidence.mkdir(parents=True)
    result = dict(evidence=str(evidence), source_revision=base.name, operator_helper_sha256=INSPECTION['FAILED_SHA'],
        complete=False, operator_job_stopped=True, credentials_issued=0, encrypted_generations_created=0,
        prior_failure_preserved=True, all_admission_policies_preserved_disabled=True,
        category='rea_main_programs_incomplete_preserve_evidence_no_automatic_retry', error_kind='ValueError', invocation_id='a'*32)
    result.update({key: False for key in ('source_profiles_changed', 'source_programs_changed', 'previous_candidates_changed',
        'candidate_promoted', 'daily_backup_registry_changed', 'canonical_memory_edits', 'chat_model_called',
        'rea_server_started', 'fleet_launch_approved', 'production_renewal_timer_enabled')})
    if damage == 'credentials': result['credentials_issued'] = 1
    if damage == 'generation': result['encrypted_generations_created'] = 1
    if damage == 'profile_changed': result['source_profiles_changed'] = True
    if damage == 'staging_started': (evidence / 'public_programs.started.json').write_text('{"phase":"public_programs"}')
    if damage == 'archive_present': (artifact / 'ghidra.tar').write_bytes(b'invented')
    (evidence / 'model_binding.started.json').write_text('{"phase":"model_binding"}')
    files = {artifact / 'context.private.json': json.dumps(dict(source_sha256=INSPECTION['FAILED_SHA'], evidence=str(evidence))).encode(),
             evidence / 'finish.summary.json': json.dumps(result).encode()}
    for name, value in dict(BASE=base, ARTIFACT=artifact, EXPECTED=evidence).items(): monkeypatch.setitem(scope, name, value)
    original = dict(metadata=lambda unit: {}, stopped=lambda state: damage != 'running', UNIT='invented-service')
    def read(path, *args):
        return files[path] if path in files else path.read_bytes()
    if damage:
        with pytest.raises(ValueError): INSPECTION['retained'](original, read)
    else:
        context, markers = INSPECTION['retained'](original, read)
        assert context['evidence'] == str(evidence) and markers['model_binding'] is True
        assert sum(markers.values()) == 1


def test_preserved_failed_helper_is_exact_and_controller_pins_inspection():
    assert hashlib.sha256((FOLDER / 'continue_rea_main_programs.py').read_bytes()).hexdigest() == INSPECTION['FAILED_SHA']
    controller = runpy.run_path(str(FOLDER / 'launch_control.py'))
    assert controller['REA_CONTINUATION_INSPECTION_SHA'] == hashlib.sha256((FOLDER / 'inspect_rea_continuation_failure.py').read_bytes()).hexdigest()
