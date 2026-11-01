"""Invented-fixture tests for the gateway token provisioner cores."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prov = load('provision_gateway_profile_access')

ENV = b"MODEL=default\nAPI_TIMEOUT=30\n"


def test_prepare_environment_appends_when_absent():
    updated = prov.prepare_environment(ENV, "tok-123_ABC.")
    assert b"ENHANCED_COGNEE_ACCESS_TOKEN=tok-123_ABC." in updated
    assert b"MODEL=default" in updated and b"API_TIMEOUT=30" in updated
    assert updated.startswith(ENV)


def test_prepare_environment_replaces_existing_in_place():
    existing = b"MODEL=default\nENHANCED_COGNEE_ACCESS_TOKEN=old-token\nAPI_TIMEOUT=30\n"
    updated = prov.prepare_environment(existing, "new-token")
    assert b"old-token" not in updated
    assert b"ENHANCED_COGNEE_ACCESS_TOKEN=new-token" in updated
    assert b"MODEL=default" in updated and b"API_TIMEOUT=30" in updated
    assert updated.count(b"ENHANCED_COGNEE_ACCESS_TOKEN=") == 1


def test_prepare_environment_replaces_only_one_line_when_duplicated():
    duplicated = (b"MODEL=default\nENHANCED_COGNEE_ACCESS_TOKEN=one\n"
                  b"API_TIMEOUT=30\nENHANCED_COGNEE_ACCESS_TOKEN=two\n")
    updated = prov.prepare_environment(duplicated, "fresh")
    assert updated.count(b"ENHANCED_COGNEE_ACCESS_TOKEN=") == 1
    assert b"one" not in updated and b"two" not in updated and b"fresh" in updated
    assert b"API_TIMEOUT=30" in updated


def test_prepare_environment_preserves_comments_and_order():
    existing = b"# memory credentials follow\nFOO=1\n# ENHANCED_COGNEE_ACCESS_TOKEN=commented\nENHANCED_COGNEE_ACCESS_TOKEN=old\nBAR=2\n"
    updated = prov.prepare_environment(existing, "new")
    assert b"# memory credentials follow" in updated
    assert b"# ENHANCED_COGNEE_ACCESS_TOKEN=commented" in updated
    assert b"FOO=1" in updated and b"BAR=2" in updated
    assert b"old" not in updated and b"new" in updated


def test_prepare_environment_refuses_bad_inputs():
    with pytest.raises(ValueError):
        prov.prepare_environment(b"", "token")
    with pytest.raises(ValueError):
        prov.prepare_environment(b"key=\x00nul\n", "token")
    with pytest.raises(ValueError):
        prov.prepare_environment(ENV, "bad token with spaces")
    with pytest.raises(ValueError):
        prov.prepare_environment(b"x" * 70000, "token")


def test_identity_scopes_default_and_roles_separately():
    default = prov.identity_for("default")
    role = prov.identity_for("code-implementer")
    assert default["project_id"] == "default" and default["sub"].endswith("_default")
    assert role["project_id"] == "code_implementer"
    assert role["sub"] == "hermes_gateway_code_implementer"
    assert default["sub"] != role["sub"]
    for identity in (default, role):
        assert identity["tenant"] == "hermes_gateway"
        assert identity["roles"] == ["api_client"]
        assert identity["capture_policy"] == "selected"


def test_identity_maps_hyphenated_roles_to_canonical_space_ids():
    for role in ("ai-safety-guardrails", "customer-feedback-analyst",
                 "deep-research-specialist", "ecommerce-kdp-publisher"):
        identity = prov.identity_for(role)
        assert "-" not in identity["project_id"]
        assert len(identity["project_id"]) <= 32
        import re
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", identity["project_id"])


def test_denial_checks_cover_unauthenticated_expired_and_altered():
    import base64
    import hashlib
    import hmac
    import json
    key = b"invented-signing-key-material-0123456789"
    identity = prov.identity_for("default")
    now = 1_800_000_000

    def sign(claims):
        head = base64.urlsafe_b64encode(json.dumps(
            {"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps(
            claims, separators=(",", ":"), ensure_ascii=True).encode()).rstrip(b"=")
        signature = base64.urlsafe_b64encode(hmac.new(
            key, head + b"." + payload, hashlib.sha256).digest()).rstrip(b"=")
        return (head + b"." + payload + b"." + signature).decode("ascii")

    status = {}

    def fake_api(token=None):
        if token is None:
            return 401, {}
        try:
            head, payload, signature = token.split(".")
            expected = base64.urlsafe_b64encode(hmac.new(
                key, (head + "." + payload).encode(), hashlib.sha256).digest()).rstrip(b"=")
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            authentic = hmac.compare_digest(signature.encode(), expected)
            unexpired = claims["exp"] > now
            recognized = claims.get("project_id") == "default"
            if authentic and unexpired and recognized:
                return 200, {"ready": True, "tenant_id": claims["tenant"],
                             "project_id": claims["project_id"], "subject": claims["sub"],
                             "schema_version": 3, "encryption": "AES-256-GCM",
                             "active_records": 0, "pending_change_events": 0}
            return 401, {}
        except Exception:
            return 401, {}

    original = prov.api_status
    prov.api_status = fake_api
    try:
        checks = prov.qualify_access(sign(dict(identity, iat=now, exp=now + 3600)),
                                     identity, expect_fresh=True)
        assert checks["ready"] is True
        expired = sign(dict(identity, iat=now - 7200, exp=now - 3600))
        assert prov.api_status(expired)[0] == 401
        head, payload, signature = sign(dict(identity, iat=now, exp=now + 3600)).split(".")
        tampered_claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        tampered_claims["project_id"] = "hermes_gateway_other"
        tampered_payload = base64.urlsafe_b64encode(json.dumps(
            tampered_claims, separators=(",", ":")).encode()).rstrip(b"=")
        altered = head + "." + tampered_payload.decode("ascii") + "." + signature
        assert prov.api_status(altered)[0] == 401
    finally:
        prov.api_status = original
