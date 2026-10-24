"""Issuer receipt and administrative-runtime refusal before any child launch."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/renew_fleet_credentials.py"
spec = importlib.util.spec_from_file_location("fleet_issuer", SOURCE)
issuer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(issuer)


def good():
    return {"complete": True, "credential_published": True, "preserved_settings_and_oauth": True,
            "preserved_previous_environment": True, "interrupted_attempts_reconciled": 0,
            "native_reload_qualified": False, "timer_activation_approved": False}


@pytest.mark.parametrize("field,value", [("complete", "true"), ("complete", False),
    ("interrupted_attempts_reconciled", True), ("interrupted_attempts_reconciled", 129),
    ("native_reload_qualified", True), ("timer_activation_approved", True),
    ("preserved_settings_and_oauth", False), ("unexpected_private_field", "invented-only")])
def test_unbounded_or_widened_receipt_refused(field, value):
    document = good()
    document[field] = value
    with pytest.raises(ValueError):
        issuer.receipt(json.dumps(document).encode())


def test_duplicate_receipt_keys_refused():
    with pytest.raises(ValueError, match="duplicate_child_receipt_field"):
        issuer.receipt(b'{"complete":true,"complete":false}')


def test_receipt_size_bound():
    with pytest.raises(ValueError, match="child_receipt_budget"):
        issuer.receipt(b" "*16385)


def test_valid_receipt_never_establishes_native_or_timer_acceptance():
    result = issuer.receipt(json.dumps(good()).encode())
    assert result["native_reload_qualified"] is False
    assert result["timer_activation_approved"] is False


def test_administrative_launch_account_is_refused_before_child(monkeypatch):
    account = SimpleNamespace(pw_name="invented", pw_uid=1000, pw_gid=1000, pw_dir="/home/invented")
    monkeypatch.setattr(issuer.pwd, "getpwnam", lambda name: account)
    monkeypatch.setattr(issuer.os, "getgrouplist", lambda name, gid: [1000, 27])
    monkeypatch.setattr(issuer.grp, "getgrgid", lambda gid: SimpleNamespace(gr_name="sudo" if gid == 27 else "invented"))
    monkeypatch.setattr(issuer.subprocess, "Popen", lambda *a, **kw: pytest.fail("Administrative runtime launched"))
    with pytest.raises(ValueError, match="administrative_runtime_identity_refused"):
        issuer.run_child({"user": "invented", "uid": 1000, "home": "/home/invented"}, {}, {})


def test_exact_reviewed_helpers_verified():
    assert set(issuer.sources()) == set(issuer.SOURCES)


def test_operator_refuses_issuer_from_agent_writable_checkout(monkeypatch):
    monkeypatch.setattr(issuer.os, "geteuid", lambda: 0)
    with pytest.raises(ValueError, match="operator_path_protection"):
        issuer.main()
