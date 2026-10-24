"""Disabled policy staging cannot confer profile admission or issue tokens."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment"


def module(name):
    spec = importlib.util.spec_from_file_location(name,BASE / (name+".py"))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def rows():
    return [{"user":"invented_owner","uid":1000,"home":"/home/invented",
             "profile_home":"/home/invented/.hermes","private_mode":True},
            {"user":"invented_owner","uid":1000,"home":"/home/invented",
             "profile_home":"/home/invented/.hermes/profiles/invented","private_mode":True,
             "token_signature_valid":True,"verified_binding":{"tenant":"qualification","project_id":"invented_scope",
                 "sub":"invented_subject","agent_id":"invented_agent","roles":["api_client"],"capture_policy":"selected"}}]


def test_all_profiles_remain_disabled_despite_private_modes_and_verified_claims():
    helper,validator = module("stage_launch_issuer"),module("fleet_credential_policy")
    policy,plans = helper.draft(rows(),validator.EXECUTABLE,validator.ORIGIN,{"invented_owner"})
    assert validator.validate(policy) == policy
    assert all(not entry[flag] for entry in policy["profiles"] for flag in (
        "enabled","reload_qualified","launch_binding_qualified","backup_qualified","os_boundary_qualified"))
    assert all("shared_launch_uid" in row["blockers"] and "administrative_runtime_identity" in row["blockers"] for row in plans)
    assert policy["profiles"][1]["project_id"] == "invented_scope"
    assert policy["profiles"][1]["subject"] == "invented_subject"


def test_existing_readonly_or_explicit_binding_is_not_silently_upgraded():
    helper,validator = module("stage_launch_issuer"),module("fleet_credential_policy")
    values = rows()
    values[1]["verified_binding"]["roles"] = ["readonly"]
    policy,plans = helper.draft(values,validator.EXECUTABLE,validator.ORIGIN,set())
    assert len(policy["profiles"]) == 1
    assert plans[1]["existing_verified_binding"]["roles"] == ["readonly"]
    assert "existing_role_or_capture_requires_manual_reissue_plan" in plans[1]["blockers"]


def test_public_issuer_package_matches_all_reviewed_sources():
    helper = module("stage_launch_issuer")
    for name,digest in helper.SOURCES.items():
        assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == digest


def test_ordinary_user_stops_before_reading_private_inventory(monkeypatch):
    helper = module("stage_launch_issuer")
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="local_root_operator_required"):
        helper.main()
