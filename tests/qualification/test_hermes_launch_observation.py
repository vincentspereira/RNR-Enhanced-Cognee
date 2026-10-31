"""Read-only explicit-attempt evidence, with actual journal and fake transport."""
import copy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from test_hermes_provider_contract import provider_module


@pytest.fixture
def native():
    spec = importlib.util.spec_from_file_location("launch_observation_test", "integrations/hermes/deployment/qualify_launch_candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("version,pending", [(2, True), (2, False), (3, True), (3, False), (4, False), (4, True)])
def test_observer_reads_real_protected_journal_and_complete_canonical_shape(native, provider_module, version, pending):
    module, home = provider_module
    provider = module.EnhancedCogneeProvider()
    provider.initialize("observer-fixture", hermes_home=str(home), agent_context="primary")
    provider.on_turn_start(1, "Invented interval remains uncertain.")
    assert json.loads(provider.handle_tool_call("enhanced_clarify", {"record_id": "fixture", "reason": "conflict"}))["clarification_required"]
    if not pending:
        with provider._clarification_journal(create=True) as fd:
            provider._record_clarification(fd, "fixture", False)
    run_id = "a" * 24
    prefix = "Fictional Cedar launch " + run_id + " uses "
    contents = [prefix + "eleven-day reviews.", prefix + "ten-day reviews.", prefix + "five-day reviews.", prefix + "five-day reviews."]
    history = dict(record_state="retracted" if version == 4 else "active", next_before_version=None,
                   response_limit_reached=False, versions=[dict(id="fixture", version=i, content=contents[i - 1]) for i in range(1, version + 1)])
    row = dict(history["versions"][-1], project_id="launch_" + run_id, state="active")
    status = dict(subject="launch_" + run_id, active_records=0 if version == 4 else 1)
    calls = []
    def request(method, path):
        calls.append((method, path))
        assert method == "GET"
        if "/history?" in path: return history
        assert version != 4  # Retracted current rows are unavailable by contract.
        return row
    provider._client.request = request
    journal = home / ".enhanced-cognee-clarifications.jsonl"
    before = (journal.read_bytes(), copy.deepcopy(history), copy.deepcopy(row))
    report = native.observe_attempt(provider, status, run_id)
    assert report["canonical_version"] == report["history_versions_verified"] == version
    assert report["pending_clarification_present"] is pending
    assert report["record_retracted"] is (version == 4)
    assert report["model_called"] is report["memory_records_written"] is report["oauth_store_read"] is False
    assert before == (journal.read_bytes(), history, row)
    assert len(calls) == (1 if version == 4 else 2)


@pytest.mark.parametrize("violation", ["extra-field", "bool-version", "wrong-history", "wrong-state", "private-id", "model-call"])
def test_observation_receipt_refuses_unexpected_fields_or_types(native, monkeypatch, violation):
    report = dict(complete=True, original_pilot_settings_and_credentials_preserved=True,
        record_id="fixture", canonical_version=2, history_versions_verified=2,
        record_retracted=False, pending_clarification_present=True,
        model_called=False, memory_records_written=False, oauth_store_read=False)
    if violation == "extra-field": report["PRIVATE"] = "PRIVATE_FIXTURE"
    if violation == "bool-version": report["canonical_version"] = True
    if violation == "wrong-history": report["history_versions_verified"] = 3
    if violation == "wrong-state": report["record_retracted"] = True
    if violation == "private-id": report["record_id"] = "../private"
    if violation == "model-call": report["model_called"] = True
    monkeypatch.setattr(native.subprocess, "run", lambda *args, **kw: NS(returncode=0, stdout=json.dumps(report).encode()))
    with pytest.raises(ValueError):
        native.run_child(NS(pw_uid=995, pw_gid=996), {}, {}, "attempt-state", Path("/public"))


@pytest.mark.parametrize("damage", ["v3-content", "v4-content", "history-page", "history-limited",
    "history-state", "active-count", "current-drift", "duplicate-version", "float-version", "other-id"])
def test_inconsistent_canonical_observation_refuses_without_changing_any_state(native, provider_module, damage):
    module, home = provider_module
    provider = module.EnhancedCogneeProvider()
    provider.initialize("observer-refusal", hermes_home=str(home), agent_context="primary")
    provider.on_turn_start(1, "Invented fixture remains uncertain.")
    provider.handle_tool_call("enhanced_clarify", {"record_id": "fixture", "reason": "conflict"})
    run_id = "a" * 24
    prefix = "Fictional Cedar launch " + run_id + " uses "
    version = 3 if damage == "current-drift" else 4
    contents = [prefix + "eleven-day reviews.", prefix + "ten-day reviews.", prefix + "five-day reviews.", prefix + "five-day reviews."]
    history = dict(record_state="active" if version == 3 else "retracted", next_before_version=None,
        response_limit_reached=False, versions=[dict(id="fixture", version=i, content=contents[i - 1]) for i in range(1, version + 1)])
    row = dict(history["versions"][-1], project_id="launch_" + run_id, state="active")
    status = dict(subject="launch_" + run_id, active_records=1 if version == 3 else 0)
    if damage == "v3-content": history["versions"][2]["content"] = "PRIVATE_WRONG_CONTENT"
    if damage == "v4-content": history["versions"][3]["content"] = "PRIVATE_WRONG_CONTENT"
    if damage == "history-page": history["next_before_version"] = 1
    if damage == "history-limited": history["response_limit_reached"] = True
    if damage == "history-state": history["record_state"] = "active"
    if damage == "active-count": status["active_records"] = 1
    if damage == "current-drift": row["content"] = "PRIVATE_WRONG_CURRENT"
    if damage == "duplicate-version": history["versions"][3]["version"] = 3
    if damage == "float-version": history["versions"][3]["version"] = 4.0
    if damage == "other-id": history["versions"][0]["id"] = "other"
    def request(method, path):
        assert method == "GET"
        return history if "/history?" in path else row
    provider._client.request = request
    journal = home / ".enhanced-cognee-clarifications.jsonl"
    before = (journal.read_bytes(), copy.deepcopy(history), copy.deepcopy(row))
    with pytest.raises(ValueError) as failure:
        native.observe_attempt(provider, status, run_id)
    assert "PRIVATE" not in str(failure.value)
    assert before == (journal.read_bytes(), history, row)


@pytest.mark.parametrize("version", [2, 3, 4])
def test_parent_observation_only_issues_ordinary_credentials_and_reads_peer(native, monkeypatch, capsys, version):
    run_id = "a" * 24
    issued = []
    issuer = dict(load_signing_key=lambda: b"synthetic-issuer",
                  sign_claims=lambda claims, key: (issued.append(dict(claims)) or "synthetic-token"))
    def child(account, sources, bundle, stage, artifact):
        assert stage == "attempt-state" and bundle["run_id"] == run_id
        return dict(complete=True, original_pilot_settings_and_credentials_preserved=True,
            record_id="fixture", canonical_version=version, history_versions_verified=version,
            record_retracted=version == 4, pending_clarification_present=version == 2,
            model_called=False, memory_records_written=False, oauth_store_read=False)
    def api(token, method, path):
        assert method == "GET" and path == "/v1/memories/fixture"
        return (200 if version == 2 else 404), {}
    monkeypatch.setattr(native, "run_child", child)
    monkeypatch.setattr(native, "api", api)
    monkeypatch.setattr(native, "read_human_answer", lambda *a, **k: pytest.fail("Read-only probe asked for input"))
    native.inspect_attempt(NS(), {}, Path("/public-candidate"), issuer, run_id)
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] is True and report["model_failure_cause_established"] is False
    assert report["native_followup_qualified"] is report["automatic_retry"] is report["fleet_launch_approved"] is False
    assert report["observed_phase"] == {2: "unchanged_pending", 3: "corrected_not_retracted", 4: "retracted_with_history"}[version]
    assert "record_id" not in report and len(issued) == 2
    assert all(c["roles"] == ["api_client"] and c["tenant"] == "qualification" for c in issued)


@pytest.mark.parametrize("violation", [None, "private-field", "private-checkpoint", "bad-count", "bad-flag"])
def test_followup_diagnostics_are_bounded_and_never_serialize_error_text(native, violation):
    state = dict(correction_tool_called=True, retraction_tool_called=False, correction_committed=False,
        peer_withdrawal_verified=False, retraction_committed=False, native_completed=False,
        native_error_present=False, rate_limited=False, last_model_http_status=200,
        model_requests=1, checkpoint="native_conversation")
    if violation == "private-field": state["PRIVATE"] = "PRIVATE_FIXTURE"
    if violation == "private-checkpoint": state["checkpoint"] = "PRIVATE_CHECKPOINT"
    if violation == "bad-count": state["model_requests"] = True
    if violation == "bad-flag": state["native_completed"] = "PRIVATE"
    native.FOLLOWUP_STATE = state
    if violation:
        with pytest.raises(ValueError): native.child_failure(ValueError("PRIVATE_EXCEPTION_TEXT"))
    else:
        report = native.child_failure(ValueError("PRIVATE_EXCEPTION_TEXT"))
        assert report["followup_observation"] == state
        assert "PRIVATE" not in json.dumps(report)
