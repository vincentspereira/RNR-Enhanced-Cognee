"""Fresh-scope public bundle guards; no model, database or private profile calls."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment"


def module(name):
    spec = importlib.util.spec_from_file_location(name,BASE / (name+".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_public_native_bundle_hashes_match_reviewed_files():
    helper = module("run_launch_native_qualification")
    sources = helper.source_bundle()
    assert len(sources) == 7
    assert "integrations/hermes/deployment/qualify_launch_candidate.py" in sources


def test_ordinary_user_cannot_read_runtime_receipt_or_private_profile(monkeypatch):
    helper = module("run_launch_native_qualification")
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    monkeypatch.setattr(helper,"installed_switch",lambda:pytest.fail("must not inspect protected state"))
    with pytest.raises(ValueError,match="fixed_fresh_operator_action_required"):
        helper.main()


def test_wrapper_does_not_accept_resume_arguments(monkeypatch):
    helper = module("run_launch_native_qualification")
    monkeypatch.setattr(helper.os,"geteuid",lambda:0)
    monkeypatch.setattr(sys,"argv",["helper","resume-answer","5d0e9a49bdf544359ae6deff"])
    with pytest.raises(ValueError,match="fixed_fresh_operator_action_required"):
        helper.main()


@pytest.mark.parametrize("finished",["5d0e9a49bdf544359ae6deff","e8d9362220ad4a78b3806974","1fbbc4a6b40b48ed91f3b44b"])
def test_completed_historical_run_is_refused_before_credential_issuance(monkeypatch, finished):
    helper = module("qualify_launch_candidate")
    monkeypatch.setattr(helper.uuid,"uuid4",lambda:SimpleNamespace(hex=finished+"0"*8))
    with pytest.raises(ValueError,match="qualification_condition_not_met"):
        helper.qualify_candidate(None,{},None,{})


def test_completion_diagnostic_retains_numeric_exit_evidence_without_model_text():
    helper = module("qualify_launch_candidate")
    value = helper.completion_diagnostic({"turn_exit_reason":"max_iterations_reached(6/6)",
        "api_calls":6,"final_response":"invented-private-model-text","failed":False,"interrupted":False},6)
    assert helper.validate_completion_diagnostic(value) == value
    assert value["exit_category"] == "iteration_limit"
    assert "invented-private-model-text" not in str(value)
    unknown = helper.completion_diagnostic({"turn_exit_reason":"invented-private-reason"},6)
    assert unknown["exit_category"] == "other"
    assert "invented-private-reason" not in str(unknown)


def test_completion_diagnostic_refuses_expanded_request_budget_or_extra_fields():
    helper = module("qualify_launch_candidate")
    value = helper.completion_diagnostic({},7)
    with pytest.raises(ValueError):
        helper.validate_completion_diagnostic(value)


def test_tool_trace_keeps_only_bounded_fixed_names_without_arguments():
    helper = module("qualify_launch_candidate")
    value = helper.completion_diagnostic({},6,["enhanced_get"]*17+["invented-private-arguments"])
    assert len(value["memory_tool_calls"]) == 16
    assert value["tool_trace_truncated"] is True
    assert "invented-private-arguments" not in str(value)
    assert helper.validate_completion_diagnostic(value) == value
    value = helper.completion_diagnostic({},6)
    value["model_text"] = "invented-private-marker"
    with pytest.raises(ValueError):
        helper.validate_completion_diagnostic(value)
