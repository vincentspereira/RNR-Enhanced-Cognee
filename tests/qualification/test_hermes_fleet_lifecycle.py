"""Source-only synthetic renewal boundaries; HTTP acceptance is a test double."""
import importlib.util
import hashlib
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


@pytest.mark.parametrize("phase,outcome",[("prepared","not_published"),("published","published")])
def test_bound_root_ledger_reconciles_exact_interrupted_child_without_new_issuance(transaction,phase,outcome):
    core,renewal,lifecycle,fd,bundle,original,path = transaction
    driver = definitions("renew_fleet_credentials")
    class Interruption(Exception):pass
    def checkpoint(current):
        if current == phase:raise Interruption
    with pytest.raises(Interruption):lifecycle["publish"](core,renewal,fd,bundle,os.geteuid(),checkpoint=checkpoint)
    ledger = path / "root-ledger-fixture"
    ledger.mkdir(mode=0o700)
    driver["LEDGER"] = ledger
    entry = dict(name="invented",profile=str(path),tenant="qualification",project_id="invented_project")
    ident = "invented-"+"a"*32
    issued = dict(schema=1,profile=entry["name"],entry_sha256=driver["binding_digest"](entry),source_hashes=driver["SOURCES"],
        driver_sha256=hashlib.sha256((BASE / "renew_fleet_credentials.py").read_bytes()).hexdigest(),
        issued_token_sha256=hashlib.sha256(bundle["token"].encode()).hexdigest())
    (ledger / (ident+".started.json")).write_text(json.dumps(dict(profile=entry["name"],state="started",source_hashes=driver["SOURCES"])))
    (ledger / (ident+".issued.json")).write_text(json.dumps(issued))
    active = (path / ".env").read_bytes()
    before_names = {p.name for p in path.iterdir()}
    def run_child(selected,payload,source):
        assert selected == entry and payload == {"reconcile_token_sha256":issued["issued_token_sha256"]}
        result = driver["reconcile_child"](core,renewal,lifecycle,fd,os.geteuid(),active,payload["reconcile_token_sha256"])
        return driver["reconciliation_receipt"](json.dumps(result).encode())
    driver["run_child"] = run_child
    def read(directory,name,uid):return (ledger / name).read_bytes(),None
    root_core = dict(open_directory=lambda *args:os.open(ledger,os.O_RDONLY | os.O_DIRECTORY),read_private_at=read)
    report = driver["reconcile_root"](root_core,entry,ident,{})
    assert report["outcome"] == outcome and report["environment_changed"] is False
    assert driver["attempt_closed"](root_core,entry,ledger / (ident+".started.json"))
    assert (path / ".env").read_bytes() == active
    assert before_names <= {p.name for p in path.iterdir()}
    assert not (ledger / (ident+".done.json")).exists()
    with pytest.raises(ValueError,match="already_closed"):driver["reconcile_root"](root_core,entry,ident,{})
    changed = dict(entry,project_id="different")
    with pytest.raises(ValueError,match="binding"):driver["reconcile_root"](root_core,changed,ident,{})


@pytest.mark.parametrize("failure",["wrong_digest","changed_environment","api_refused","changed_candidate"])
def test_reconciliation_refuses_unbound_conflicting_or_unauthenticated_effects(transaction,failure):
    core,renewal,lifecycle,fd,bundle,original,path = transaction
    driver = definitions("renew_fleet_credentials")
    class Interruption(Exception):pass
    def checkpoint(current):
        if current == "prepared":raise Interruption
    with pytest.raises(Interruption):lifecycle["publish"](core,renewal,fd,bundle,os.geteuid(),checkpoint=checkpoint)
    digest = hashlib.sha256(bundle["token"].encode()).hexdigest()
    if failure == "wrong_digest":digest = "f"*64
    if failure == "changed_environment":(path / ".env").write_bytes(original+b"CONCURRENT=preserve\n")
    if failure == "api_refused":core["api_status"] = lambda token:(401,{})
    if failure == "changed_candidate":next(path.glob(".env-cognee-renew-*")).write_bytes(b"CONCURRENT=preserve\n")
    active = (path / ".env").read_bytes()
    with pytest.raises(ValueError):driver["reconcile_child"](core,renewal,lifecycle,fd,os.geteuid(),active,digest)
    assert (path / ".env").read_bytes() == active
    assert not list(path.glob(".cognee-renewal-*.done.json"))


def test_reconciliation_receipt_refuses_duplicate_keys_and_false_acceptance():
    driver = definitions("renew_fleet_credentials")
    with pytest.raises(ValueError):driver["reconciliation_receipt"](b'{"complete":true,"complete":false}')
    value = dict(complete=True,outcome="published",environment_changed=False,current_credential_authenticated=False,
                 native_reload_qualified=False,timer_activation_approved=False)
    with pytest.raises(ValueError):driver["reconciliation_receipt"](json.dumps(value).encode())


def test_two_matching_issued_journals_remain_ambiguous(transaction):
    core,renewal,lifecycle,fd,bundle,original,path = transaction
    driver = definitions("renew_fleet_credentials")
    class Interruption(Exception):pass
    def checkpoint(phase):
        if phase == "prepared":raise Interruption
    for _ in range(2):
        with pytest.raises(Interruption):lifecycle["publish"](core,renewal,fd,bundle,os.geteuid(),checkpoint=checkpoint)
    digest = hashlib.sha256(bundle["token"].encode()).hexdigest()
    with pytest.raises(ValueError,match="missing_or_ambiguous"):
        driver["reconcile_child"](core,renewal,lifecycle,fd,os.geteuid(),original,digest)
    assert (path / ".env").read_bytes() == original


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
