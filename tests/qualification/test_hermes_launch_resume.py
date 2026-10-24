"""Explicit invented-scope continuation admission; no installed host actions."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def native():
    spec = importlib.util.spec_from_file_location("launch_resume_test", "integrations/hermes/deployment/qualify_launch_candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("damage", [None, "subject", "count", "no-pending", "extra-pending",
    "row-project", "row-content", "row-version", "row-state", "history-content", "history-version",
    "history-extra", "history-state", "history-page", "history-limited"])
def test_resume_admits_only_exact_unmodified_pending_invented_fixture(native, damage):
    run_id = "a" * 24
    status = dict(subject="launch_" + run_id, active_records=1)
    pending = {"fixture"}
    prefix = "Fictional Cedar launch " + run_id + " uses "
    row = dict(id="fixture", version=2, project_id="launch_" + run_id, state="active", content=prefix + "ten-day reviews.")
    history = dict(record_state="active", next_before_version=None, response_limit_reached=False,
        versions=[dict(id="fixture", version=1, content=prefix + "eleven-day reviews."),
                  dict(id="fixture", version=2, content=prefix + "ten-day reviews.")])
    if damage == "subject": status["subject"] = "other"
    if damage == "count": status["active_records"] = True
    if damage == "no-pending": pending.clear()
    if damage == "extra-pending": pending.add("other")
    if damage == "row-project": row["project_id"] = "private"
    if damage == "row-content": row["content"] = "PRIVATE_FIXTURE_DO_NOT_CHANGE"
    if damage == "row-version": row["version"] = 2.0
    if damage == "row-state": row["state"] = "retracted"
    if damage == "history-content": history["versions"][0]["content"] = "OTHER_FIXTURE"
    if damage == "history-version": history["versions"][0]["version"] = 1.0
    if damage == "history-extra": history["versions"].append(dict(version=3))
    if damage == "history-state": history["record_state"] = "retracted"
    if damage == "history-page": history["next_before_version"] = 1
    if damage == "history-limited": history["response_limit_reached"] = True
    before = copy.deepcopy((row, history, pending))
    requests = []
    def request(method, path):
        requests.append((method, path))
        assert method == "GET"
        return history if "/history?" in path else row
    provider = NS(_pending_clarifications=pending, _client=NS(request=request))
    if damage:
        with pytest.raises(ValueError): native.verify_pending_fixture(provider, status, run_id)
    else:
        assert native.verify_pending_fixture(provider, status, run_id) == "fixture"
        assert len(requests) == 2
    assert (row, history, pending) == before


@pytest.mark.parametrize("run_id", [None, "", "../private", "a" * 23, "a" * 25, "A" * 24])
def test_invalid_resume_id_refused_before_terminal_issuer_or_profile(native, monkeypatch, run_id):
    monkeypatch.setattr(native.os, "geteuid", lambda: 0)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Hermes")
    monkeypatch.setenv("SUDO_USER", "vincentspereira")
    monkeypatch.setattr(native, "terminal_preflight", lambda: pytest.fail("Invalid scope reached terminal"))
    monkeypatch.setattr(native, "definitions", lambda *args: pytest.fail("Invalid scope reached issuer"))
    with pytest.raises(ValueError): native.main({}, "resume-answer", run_id)


@pytest.mark.parametrize("stop", [None, "pending", "peer", "human", "followup", "withdrawal"])
def test_resume_never_replays_question_or_grants_access_and_requires_live_answer(native, monkeypatch, capsys, stop):
    run_id = "a" * 24
    issued = []
    stages = []
    def sign(claims, key):
        issued.append(dict(claims))
        return "synthetic-ordinary-token"
    issuer = dict(load_signing_key=lambda: b"synthetic-issuer", sign_claims=sign)
    def child(account, sources, bundle, stage, artifact):
        stages.append(stage)
        assert bundle["run_id"] == run_id and bundle["project"] == "launch_" + run_id
        if stage == "resume-check":
            if stop == "pending": raise ValueError("synthetic pending refusal")
            return dict(record_id="fixture", pending_original_fixture_verified=True)
        assert stage == "answer" and native.PROGRESS["human_answer_received"] is True
        assert bundle["human_answer"] == "SYNTHETIC_ACTUAL_TERMINAL_INPUT"
        if stop == "followup": raise ValueError("synthetic followup refusal")
        return dict(complete=True, model_requests=1, later_human_answer_passed=True,
            restart_pending_gate_passed=True, versioned_correction_and_retraction_passed=True,
            history_preserved=True, correction_withdrawn_from_peer=True,
            original_pilot_settings_and_credentials_preserved=True)
    def api(token, method, path, body=None):
        assert method == "GET" and path == "/v1/memories/fixture" and body is None
        if stages == ["resume-check"]:
            return (404 if stop == "peer" else 200), dict(id="fixture", version=2,
                project_id="launch_" + run_id, content="Fictional Cedar launch " + run_id + " uses ten-day reviews.")
        return (500 if stop == "withdrawal" else 404), {}
    def answer(ident, *, resumed):
        assert ident == run_id and resumed is True and stages == ["resume-check"]
        if stop == "human": raise ValueError("synthetic human refusal")
        return "SYNTHETIC_ACTUAL_TERMINAL_INPUT"
    monkeypatch.setattr(native, "run_child", child)
    monkeypatch.setattr(native, "api", api)
    monkeypatch.setattr(native, "read_human_answer", answer)
    if stop:
        with pytest.raises(ValueError): native.resume_answer(NS(), {}, Path("/public-candidate"), issuer, run_id)
        assert capsys.readouterr().out == ""
        if stop in {"pending", "peer", "human"}:
            assert stages == ["resume-check"] and native.PROGRESS["human_answer_received"] is False
    else:
        native.resume_answer(NS(), {}, Path("/public-candidate"), issuer, run_id)
        report = json.loads(capsys.readouterr().out)
        assert report["complete"] is True and report["resumed_run_id"] == run_id
        assert report["prior_question_and_sharing_replayed"] is report["prior_machine_receipt_verified"] is False
        assert report["model_requests"] == 1 and report["request_count_scope"] == "resumed_followup_only"
        assert report["fleet_launch_approved"] is False
    assert stages[0] == "resume-check" and "question" not in stages
    assert len(issued) == 2 and all(c["roles"] == ["api_client"] and c["tenant"] == "qualification" for c in issued)
    assert {c["project_id"] for c in issued} == {"launch_" + run_id, "peer_" + run_id}


@pytest.mark.parametrize("bad", ["private-field", "model-called", "bad-id"])
def test_resume_readonly_receipt_is_strict(native, monkeypatch, bad):
    report = dict(complete=True, pending_original_fixture_verified=True,
        original_pilot_settings_and_credentials_preserved=True, model_called=False,
        memory_records_written=False, oauth_store_read=False, record_id="fixture")
    if bad == "private-field": report["PRIVATE"] = "PRIVATE_VALUE"
    if bad == "model-called": report["model_called"] = True
    if bad == "bad-id": report["record_id"] = "../private"
    monkeypatch.setattr(native.subprocess, "run", lambda *args, **kw: NS(returncode=0, stdout=json.dumps(report).encode()))
    with pytest.raises(ValueError): native.run_child(NS(pw_uid=995, pw_gid=996), {}, {}, "resume-check", Path("/public"))
