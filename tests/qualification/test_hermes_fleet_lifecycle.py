"""Source-only synthetic renewal boundaries; HTTP acceptance is a test double."""
import importlib.util
import json
import os
from pathlib import Path
import time

import pytest


BASE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment"


def definitions(name):
    spec = importlib.util.spec_from_file_location("fixture_" + name, BASE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__dict__


@pytest.fixture
def transaction(tmp_path):
    core = definitions("provision_pilot_access")
    renewal = definitions("renew_pilot_access")
    lifecycle = definitions("fleet_credential_lifecycle")
    core["IDENTITY"] = {"sub": "invented_subject", "agent_id": "invented_agent", "tenant": "qualification",
                        "project_id": "invented_project", "roles": ["api_client"], "capture_policy": "selected"}
    key = b"invented-only-signing-fixture-not-a-live-key"
    now = int(time.time())
    old = core["sign_claims"](dict(core["IDENTITY"], iat=now-60, exp=now+86340), key)
    bundle = core["make_bundle"](key, now)
    original = ("UNRELATED_SYNTHETIC_SETTING=preserved\nENHANCED_COGNEE_ACCESS_TOKEN=" + old + "\n").encode()
    for name, raw in {".env": original, "config.yaml": b"memory:\n  provider: enhanced_cognee\nmodel: unchanged\n",
                      "auth.json": b'{"invented_oauth_marker":"preserve"}',
                      "enhanced_cognee.json": b'{"base_url":"http://127.0.0.1:28080","capture_policy":"selected","include_shared":true}'}.items():
        path = tmp_path / name
        path.write_bytes(raw)
        path.chmod(0o600)
    accepted = {old, bundle["token"]}
    def status(token):
        if token not in accepted:
            return 401, {}
        return 200, {"ready": True, "schema_version": 3, "encryption": "AES-256-GCM",
                     "tenant_id": "qualification", "project_id": "invented_project", "subject": "invented_subject",
                     "active_records": 7, "pending_change_events": 0}
    core["api_status"] = status
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield core, renewal, lifecycle, fd, bundle, original, tmp_path
    finally:
        os.close(fd)


def test_preserves_arbitrary_existing_settings_and_auth(transaction):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    preserved = {name: (path / name).read_bytes() for name in ("config.yaml", "auth.json", "enhanced_cognee.json")}
    result = lifecycle["publish"](core, renewal, fd, bundle, os.geteuid())
    assert result["complete"] is True
    assert result["native_reload_qualified"] is False
    assert result["timer_activation_approved"] is False
    assert renewal["environment"](core, (path / ".env").read_bytes()) == bundle["token"]
    assert b"UNRELATED_SYNTHETIC_SETTING=preserved" in (path / ".env").read_bytes()
    assert all((path / name).read_bytes() == raw for name, raw in preserved.items())
    assert [p.read_bytes() for p in path.glob(".env-before-*")] == [original]


@pytest.mark.parametrize("phase,outcome", [("prepared", "not_published"), ("published", "published")])
def test_interrupted_attempts_reconcile_without_deleting_evidence(transaction, phase, outcome):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    class Interruption(Exception):
        pass
    def checkpoint(current):
        if current == phase:
            raise Interruption
    with pytest.raises(Interruption):
        lifecycle["publish"](core, renewal, fd, bundle, os.geteuid(), checkpoint=checkpoint)
    before_names = {p.name for p in path.iterdir()}
    active = (path / ".env").read_bytes()
    assert renewal["reconcile"](core, fd, os.geteuid(), active) == 1
    assert before_names <= {p.name for p in path.iterdir()}
    assert (path / ".env").read_bytes() == active
    assert json.loads(next(path.glob(".cognee-renewal-*.done.json")).read_text())["outcome"] == outcome
    assert [p.read_bytes() for p in path.glob(".env-before-*")] == [original]


def test_concurrent_profile_change_is_preserved(transaction):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    changed = b"UNRELATED_SYNTHETIC_SETTING=concurrent\n"
    def checkpoint(phase):
        if phase == "prepared":
            (path / "config.yaml").write_bytes(changed)
    with pytest.raises(ValueError, match="renewal_profile_changed"):
        lifecycle["publish"](core, renewal, fd, bundle, os.geteuid(), checkpoint=checkpoint)
    assert (path / ".env").read_bytes() == original
    assert (path / "config.yaml").read_bytes() == changed


def test_wrong_api_scope_never_published(transaction):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    request = core["api_status"]
    def wrong_scope(token):
        code, data = request(token)
        return code, dict(data, project_id="other_project")
    core["api_status"] = wrong_scope
    with pytest.raises(ValueError, match="renewal_scope_or_api_refused"):
        lifecycle["publish"](core, renewal, fd, bundle, os.geteuid())
    assert (path / ".env").read_bytes() == original
    assert not list(path.glob(".env-before-*"))


def test_missing_refusal_control_never_published(transaction):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    request = core["api_status"]
    core["api_status"] = lambda token: (200, {}) if token is None else request(token)
    with pytest.raises(ValueError, match="renewal_refusal_control_failed"):
        lifecycle["publish"](core, renewal, fd, bundle, os.geteuid())
    assert (path / ".env").read_bytes() == original


def test_expired_profile_requires_operator_recovery(transaction):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    now = int(time.time())
    expired = core["sign_claims"](dict(core["IDENTITY"], iat=now-90000, exp=now-3600), b"invented-fixture-key")
    raw = ("ENHANCED_COGNEE_ACCESS_TOKEN=" + expired + "\n").encode()
    (path / ".env").write_bytes(raw)
    with pytest.raises(ValueError, match="expired_profile_requires_operator_recovery"):
        lifecycle["publish"](core, renewal, fd, bundle, os.geteuid())
    assert (path / ".env").read_bytes() == raw


def test_published_credential_is_not_replayed(transaction):
    core, renewal, lifecycle, fd, bundle, original, path = transaction
    lifecycle["publish"](core, renewal, fd, bundle, os.geteuid())
    names = {p.name for p in path.iterdir()}
    with pytest.raises(ValueError, match="credential_already_current"):
        lifecycle["publish"](core, renewal, fd, bundle, os.geteuid())
    assert {p.name for p in path.iterdir()} == names
