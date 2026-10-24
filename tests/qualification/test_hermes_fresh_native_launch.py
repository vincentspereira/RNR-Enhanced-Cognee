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


def test_completed_historical_run_is_refused_before_credential_issuance(monkeypatch):
    helper = module("qualify_launch_candidate")
    monkeypatch.setattr(helper.uuid,"uuid4",lambda:SimpleNamespace(hex="5d0e9a49bdf544359ae6deff"+"0"*8))
    with pytest.raises(ValueError,match="qualification_condition_not_met"):
        helper.qualify_candidate(None,{},None,{})
