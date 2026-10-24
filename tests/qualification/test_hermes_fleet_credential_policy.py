"""Reject widened signing authority and incomplete real profile admission."""
import copy
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/fleet_credential_policy.py"
spec = importlib.util.spec_from_file_location("fleet_credential_policy", SOURCE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def candidate():
    return {"schema": 1, "profiles": [{"name": "invented", "enabled": False, "user": "hermes-runtime",
        "uid": 993, "home": "/var/lib/hermes-runtime", "profile": "/var/lib/hermes-runtime/.hermes/profiles/invented",
        "tenant": "qualification", "project_id": "invented", "subject": "invented", "agent_id": "invented",
        "roles": ["api_client"], "lifetime_seconds": 86400, "origin": policy.ORIGIN, "executable": policy.EXECUTABLE,
        "reload_qualified": False, "launch_binding_qualified": False, "backup_qualified": False,
        "os_boundary_qualified": False}]}


@pytest.mark.parametrize("field,value", [
    ("roles", ["memory_admin"]), ("roles", ["api_client", "reviewer"]),
    ("origin", "https://example.invalid"), ("executable", "/home/invented/python"),
    ("lifetime_seconds", 86401), ("lifetime_seconds", True), ("uid", 0), ("uid", True),
    ("profile", "/var/lib/hermes-runtime/.hermes/../../peer"),
    ("profile", "/var/lib/peer/.hermes"), ("enabled", True), ("enabled", 1),
    ("project_id", "caller/selected"),
])
def test_unapproved_authority_or_admission_refused(field, value):
    document = candidate()
    document["profiles"][0][field] = value
    with pytest.raises(ValueError):
        policy.validate(document)


def test_caller_signing_choices_not_in_schema():
    document = candidate()
    document["profiles"][0]["signing_key"] = "invented-never-used"
    with pytest.raises(ValueError, match="invalid_policy_fields"):
        policy.validate(document)


def test_distinct_subjects_cannot_accidentally_share_private_scope():
    document = candidate()
    peer = copy.deepcopy(document["profiles"][0])
    peer.update(name="peer", subject="peer", agent_id="peer", profile="/var/lib/hermes-runtime/.hermes/profiles/peer")
    document["profiles"].append(peer)
    with pytest.raises(ValueError, match="duplicate_policy_binding"):
        policy.validate(document)


def test_disabled_candidate_stays_independent_and_unadmitted():
    document = candidate()
    plan = policy.validate(document)
    document["profiles"][0]["roles"].append("reviewer")
    assert plan["profiles"][0]["roles"] == ["api_client"]
    assert plan["profiles"][0]["enabled"] is False


def test_each_installed_gate_required_before_enable():
    for missing in ("reload_qualified", "launch_binding_qualified", "backup_qualified", "os_boundary_qualified"):
        document = candidate()
        row = document["profiles"][0]
        for key in ("enabled", "reload_qualified", "launch_binding_qualified", "backup_qualified", "os_boundary_qualified"):
            row[key] = True
        row[missing] = False
        with pytest.raises(ValueError, match="profile_gates_incomplete"):
            policy.validate(document)
