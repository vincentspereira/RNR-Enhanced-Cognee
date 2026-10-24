"""Source guards only; the real API/native cycle needs the operator run."""
import hashlib
import importlib.util
from pathlib import Path
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_launch_credential_cycle.py"
spec = importlib.util.spec_from_file_location("credential_cycle", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.mark.parametrize("value", ["../pilot", "5d0e9a49bdf544359ae6deff", "A"*16, "0"*15, True])
def test_caller_cannot_select_existing_or_malformed_fixture(value):
    with pytest.raises(ValueError, match="fixture_identifier"):
        helper.claims_for(value)


def test_claims_are_fixed_ordinary_new_scope():
    claims = helper.claims_for("0123456789abcdef")
    assert claims["roles"] == ["api_client"]
    assert claims["project_id"] == "renew_0123456789abcdef"
    assert claims["capture_policy"] == "selected"
    assert "signing_key" not in claims


def test_all_dependency_hashes_match_reviewed_sources():
    for name, expected in helper.FILES.items():
        assert hashlib.sha256((SOURCE.parents[1] / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("mutation", [{"complete": "true"}, {"model_called": True},
    {"memory_records_written": True}, {"scheduled_firing_qualified": True}, {"native_secret_refresh_passed": 1}])
def test_receipt_cannot_widen_or_fake_qualification(mutation):
    value = {"complete": True, "real_api_expiry_denied": True, "new_credential_accepted": True,
        "native_secret_refresh_passed": True, "native_cache_identity_changed": True,
        "prepared_and_published_journals_reconciled": True, "settings_and_synthetic_auth_preserved": True,
        "memory_records_written": False, "model_called": False}
    value.update(mutation)
    with pytest.raises(ValueError, match="child_receipt"):
        helper.cycle_receipt(value)


def test_unprivileged_caller_stops_before_fixture_creation(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(SOURCE)])
    monkeypatch.setattr(helper.os, "geteuid", lambda: 1000)
    with pytest.raises(ValueError, match="protected_operator_python_required"):
        helper.main()
