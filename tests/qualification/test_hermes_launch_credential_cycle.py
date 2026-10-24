"""Source guards only; the real API/native cycle needs the operator run."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import time

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


def test_status_diagnostic_emits_flags_not_response_or_claim_values():
    identity = helper.claims_for("0123456789abcdef")
    body = {"ready": True, "schema_version": 3, "encryption": "AES-256-GCM",
            "tenant_id": identity["tenant"], "project_id": identity["project_id"],
            "subject": identity["sub"], "active_records": 0, "pending_change_events": 0,
            "unexpected_private_field": "invented-sensitive-marker"}
    value = helper.status_diagnostic(identity, 200, body, time.time()+60)
    assert helper.valid_diagnostic(value)
    assert value["project_matches"] is True
    assert value["http_status"] == 200
    assert "invented-sensitive-marker" not in str(value)
    assert identity["project_id"] not in str(value)


def test_expired_authentication_is_distinct_from_scope_mismatch():
    identity = helper.claims_for("0123456789abcdef")
    value = helper.status_diagnostic(identity, 401, {}, time.time()-1)
    assert helper.valid_diagnostic(value)
    assert value["http_status"] == 401 and value["seconds_remaining"] < 0
    assert value["ready"] is False


def test_extra_diagnostic_fields_are_not_forwarded():
    value = helper.status_diagnostic(helper.claims_for("0123456789abcdef"), 0, {}, time.time())
    value["response_body"] = "invented-private-marker"
    assert helper.valid_diagnostic(value) is False


def test_exception_metadata_omits_messages_and_private_attribute_values():
    try:
        try:
            raise PermissionError(13, "invented-private-path-and-token")
        except PermissionError:
            raise RuntimeError("invented-private-response") from None
    except RuntimeError as error:
        value = helper.exception_metadata(error)
    assert [row["kind"] for row in value] == ["RuntimeError", "PermissionError"]
    assert value[1]["errno"] == 13
    assert "invented-private" not in str(value)


def test_exception_metadata_is_bounded_for_chained_errors():
    error = ValueError("invented-private-marker")
    for _ in range(8):
        following = RuntimeError("invented-private-marker")
        following.__cause__ = error
        error = following
    assert len(helper.exception_metadata(error)) == 4


@pytest.mark.skipif(os.geteuid() == 0, reason="Requires ordinary Unix permission enforcement")
def test_readonly_directory_walker_needs_readable_parent_but_private_child(tmp_path):
    parent = tmp_path / "public-identifiers"
    parent.mkdir(mode=0o755)
    child = parent / "private-profile"
    child.mkdir(mode=0o700)
    parent.chmod(0o111)  # Same effective read/traverse rights as other users of 0711.
    try:
        with pytest.raises(PermissionError):
            os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    finally:
        parent.chmod(0o755)
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        private = os.open(child.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            assert os.fstat(private).st_mode & 0o777 == 0o700
        finally:
            os.close(private)
    finally:
        os.close(fd)
