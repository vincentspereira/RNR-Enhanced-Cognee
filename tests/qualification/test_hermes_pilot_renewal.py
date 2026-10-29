"""Real private-file renewal transactions; API and operator boundaries simulated."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import time
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def modules():
    result = []
    for name in ("provision_pilot_access", "renew_pilot_access"):
        path = Path("integrations/hermes/deployment") / (name + ".py")
        spec = importlib.util.spec_from_file_location(name, path.resolve())
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result.append(module)
    return result


KEY = b"synthetic-renewal-signing-key-not-from-any-real-service"


@pytest.fixture
def profile(modules, tmp_path, monkeypatch):
    issuer, renewal = modules
    core = vars(issuer)
    uid = os.geteuid()
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    old = issuer.make_bundle(KEY, int(time.time()) - 3600)
    fresh = issuer.make_bundle(KEY, int(time.time()))
    raw = b'# retained comment\nMULTILINE="one\ntwo"\nOTHER=keep\n' + issuer.TOKEN_NAME.encode() + b'="' + old["token"].encode() + b'" # retained suffix\n'
    files = {".env": raw, "config.yaml": b"memory:\n  provider: enhanced_cognee\n",
        "enhanced_cognee.json": json.dumps({"base_url": "http://127.0.0.1:28080", "timeout": 10,
            "include_shared": True, "capture_policy": "selected"}).encode(), "auth.json": b"PRIVATE_OAUTH_SENTINEL"}
    for name, value in files.items(): issuer.create_private_at(directory, name, value)
    requests = []
    data = {"ready": True, "tenant_id": "qualification", "project_id": "hermes_pilot",
        "subject": "hermes_pilot_runtime", "schema_version": 3, "encryption": "AES-256-GCM",
        "active_records": 2, "pending_change_events": 4}
    def api(token):
        requests.append(token)
        return (200, dict(data)) if token == fresh["token"] else (401, {})
    monkeypatch.setattr(issuer, "api_status", api)
    yield core, renewal, directory, uid, fresh, old, files, requests, data
    os.close(directory)


def test_actual_atomic_renewal_preserves_bytes_and_restricts_all_new_files(profile, tmp_path):
    core, renewal, directory, uid, fresh, old, files, requests, _ = profile
    report = renewal.renew(core, directory, fresh, uid)
    assert report["credential_renewed"] and not report["runtime_qualified"]
    assert report["interrupted_attempts_reconciled"] == 0
    updated = (tmp_path / ".env").read_bytes()
    assert updated == files[".env"].replace(old["token"].encode(), fresh["token"].encode())
    for name, raw in files.items():
        if name != ".env": assert (tmp_path / name).read_bytes() == raw
    assert requests == [None, fresh["expired"], fresh["altered"], fresh["token"], fresh["token"]]
    backups = list(tmp_path.glob(".env-before-cognee-renew-*"))
    assert len(backups) == 1 and backups[0].read_bytes() == files[".env"]
    for path in tmp_path.iterdir(): assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(list(tmp_path.glob("*.done.json"))) == 1
    assert old["token"] not in json.dumps(report) and fresh["token"] not in json.dumps(report)


@pytest.mark.parametrize("phase", ["prepared", "published", "verified"])
def test_interrupted_transaction_is_reconciled_without_reverting_or_deleting(profile, tmp_path, phase):
    core, renewal, directory, uid, fresh, _, files, _, _ = profile
    def interrupt(current):
        if current == phase: raise InterruptedError("PRIVATE_PROCESS_INTERRUPTION")
    with pytest.raises(InterruptedError): renewal.renew(core, directory, fresh, uid, interrupt)
    previous_paths = set(tmp_path.iterdir())
    current = (tmp_path / ".env").read_bytes()
    assert renewal.reconcile(core, directory, uid, current) == 1
    assert set(tmp_path.iterdir()) >= previous_paths and (tmp_path / ".env").read_bytes() == current
    done = json.loads(next(tmp_path.glob("*.done.json")).read_bytes())
    assert done["outcome"] == ("not_published" if phase == "prepared" else "published")
    assert renewal.reconcile(core, directory, uid, current) == 0
    assert next(tmp_path.glob(".env-before-cognee-renew-*")).read_bytes() == files[".env"]
    if phase == "prepared":
        result = renewal.renew(core, directory, fresh, uid)
        assert result["credential_renewed"]


@pytest.mark.parametrize("mutation", ["scope", "role", "lifetime", "future", "malformed", "missing", "duplicate", "syntax", "mode", "symlink", "hardlink", "already-installed"])
def test_invalid_scope_assignment_or_private_file_never_publishes(profile, tmp_path, mutation):
    core, renewal, directory, uid, fresh, old, _, _, _ = profile
    raw = (tmp_path / ".env").read_bytes()
    claims = dict(old["claims"])
    if mutation in {"scope", "role", "lifetime", "future"}:
        if mutation == "scope": claims["project_id"] = "OTHER"
        if mutation == "role": claims["roles"] = ["admin"]
        if mutation == "lifetime": claims["exp"] += 1
        if mutation == "future": claims.update(iat=int(time.time()) + 600, exp=int(time.time()) + 87000)
        raw = raw.replace(old["token"].encode(), core["sign_claims"](claims, KEY).encode())
    if mutation == "malformed": raw = raw.replace(old["token"].encode(), b"PRIVATE_INVALID_TOKEN")
    if mutation == "missing": raw = b"OTHER=keep\n"
    if mutation == "duplicate": raw += core["TOKEN_NAME"].encode() + b"=duplicate\n"
    if mutation == "syntax": raw += b'BROKEN="unterminated\n'
    if mutation == "already-installed": raw = raw.replace(old["token"].encode(), fresh["token"].encode())
    (tmp_path / ".env").write_bytes(raw)
    if mutation == "mode": (tmp_path / ".env").chmod(0o644)
    if mutation in {"symlink", "hardlink"}:
        original = tmp_path / ".env"
        retained = tmp_path / "retained-env"
        original.rename(retained)
        if mutation == "symlink": original.symlink_to(retained)
        else: os.link(retained, original)
    before = {p.name for p in tmp_path.iterdir()}
    with pytest.raises((core["ProvisionError"], OSError, ValueError)):
        renewal.renew(core, directory, fresh, uid)
    assert (tmp_path / ".env").read_bytes() == raw
    assert {p.name for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("mutation", ["unauth", "expired", "altered", "scope", "subject", "records", "bool-records", "schema", "encryption", "ready", "negative-pending"])
def test_api_denial_and_populated_scope_controls_stop_before_profile_write(profile, tmp_path, mutation):
    core, renewal, directory, uid, fresh, _, files, _, data = profile
    field_values = {"scope": ("project_id", "other"), "subject": ("subject", "other"), "records": ("active_records", 3),
        "bool-records": ("active_records", True), "schema": ("schema_version", 2), "encryption": ("encryption", "none"),
        "ready": ("ready", False), "negative-pending": ("pending_change_events", -1)}
    if mutation in field_values:
        key, value = field_values[mutation]
        data[key] = value
    original = core["api_status"]
    core["api_status"] = lambda token: (200, {}) if ((mutation == "unauth" and token is None)
        or (mutation in {"expired", "altered"} and token == fresh[mutation])) else original(token)
    with pytest.raises(core["ProvisionError"]): renewal.renew(core, directory, fresh, uid)
    assert (tmp_path / ".env").read_bytes() == files[".env"]
    assert len(list(tmp_path.iterdir())) == 4


@pytest.mark.parametrize("mutation", ["current", "backup", "candidate", "journal", "done", "profile-during-publication"])
def test_conflicting_or_damaged_evidence_requires_review_without_overwrite(profile, tmp_path, mutation):
    core, renewal, directory, uid, fresh, _, _, _, _ = profile
    def interrupt(phase):
        if phase == "prepared": raise InterruptedError()
    with pytest.raises(InterruptedError): renewal.renew(core, directory, fresh, uid, interrupt)
    if mutation == "current": (tmp_path / ".env").write_bytes(b"PRIVATE_CONCURRENT_EDIT")
    elif mutation in {"backup", "candidate", "journal"}:
        patterns = {"backup": ".env-before-cognee-renew-*", "candidate": ".env-cognee-renew-*", "journal": ".cognee-renewal-*.json"}
        next(tmp_path.glob(patterns[mutation])).write_bytes(b"PRIVATE_CORRUPTION")
    elif mutation == "done":
        name = next(tmp_path.glob(".cognee-renewal-*.json")).name.removesuffix(".json") + ".done.json"
        core["create_private_at"](directory, name, b'{"outcome":"FORGED"}')
    else:
        # A separately tested new transaction detects a config edit after staging.
        renewal.reconcile(core, directory, uid, (tmp_path / ".env").read_bytes())
        def drift(phase):
            if phase == "prepared": (tmp_path / "auth.json").write_bytes(b"PRIVATE_NEW_OAUTH")
        original = (tmp_path / ".env").read_bytes()
        with pytest.raises(core["ProvisionError"]): renewal.renew(core, directory, fresh, uid, drift)
        assert (tmp_path / ".env").read_bytes() == original
        return
    original = (tmp_path / ".env").read_bytes()
    with pytest.raises((core["ProvisionError"], ValueError)):
        renewal.reconcile(core, directory, uid, original)
    assert (tmp_path / ".env").read_bytes() == original


@pytest.mark.parametrize("mutation", [None, "extra", "duplicate", "link", "hash", "missing"])
def test_exact_reviewed_source_bundle_composes_without_root_or_host_calls(modules, mutation, capsys):
    _, renewal = modules
    base = Path("integrations/hermes/deployment")
    payload = {str(base / (name + ".py")): (base / (name + ".py")).read_bytes()
        for name in ("provision_pilot_access", "renew_pilot_access")}
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}
    names = list(payload)
    if mutation == "extra": names += ["unexpected.py"]
    if mutation == "duplicate": names += [names[0]]
    if mutation == "missing": names.pop()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in names:
            raw = payload.get(name, b"extra = True")
            if mutation == "hash": raw += b"\n# changed"
            member = tarfile.TarInfo(name)
            if mutation == "link":
                member.type, member.linkname = tarfile.SYMTYPE, "private-target"
                archive.addfile(member)
            else:
                member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
    if mutation:
        with pytest.raises(ValueError): renewal.verified_sources(stream.getvalue(), hashes)
    else:
        for name, raw in renewal.verified_sources(stream.getvalue(), hashes).items():
            scope = {"__name__": "source_only"}
            exec(compile(raw, name, "exec"), scope)
            assert callable(scope["main"])
        assert not capsys.readouterr().out


@pytest.mark.parametrize("mutation", [None, "failed", "extra", "false-flag", "boolean-count", "secret"])
def test_parent_drops_privileges_sends_no_signing_key_and_validates_receipt(profile, monkeypatch, mutation):
    core, renewal, directory, uid, fresh, _, _, _, _ = profile
    report = renewal.renew(core, directory, fresh, uid)
    if mutation == "extra": report["extra"] = "PRIVATE"
    if mutation == "false-flag": report["settings_and_oauth_preserved"] = False
    if mutation == "boolean-count": report["interrupted_attempts_reconciled"] = True
    if mutation == "secret": report = "PRIVATE_CHILD_OUTPUT"
    def run(argv, **kwargs):
        assert argv[:3] == ["/usr/bin/setpriv", "--no-new-privs", "--"]
        assert kwargs["user"] == 993 and kwargs["group"] == 985 and kwargs["extra_groups"] == ()
        assert KEY not in kwargs["input"] and "PRIVATE" not in str(argv)
        assert kwargs["cwd"] == core["HOME"] and kwargs["timeout"] == 90
        return NS(returncode=int(mutation == "failed"), stdout=json.dumps(report).encode(), stderr=b"PRIVATE_ERROR")
    monkeypatch.setattr(renewal.subprocess, "run", run)
    sources = {"integrations/hermes/deployment/" + name + ".py": b"# reviewed public source"
               for name in ("provision_pilot_access", "renew_pilot_access")}
    if mutation:
        with pytest.raises(core["ProvisionError"]) as error:
            renewal.run_child(core, NS(pw_uid=993, pw_gid=985), sources, fresh)
        assert "PRIVATE" not in str(error.value)
    else:
        assert renewal.run_child(core, NS(pw_uid=993, pw_gid=985), sources, fresh) == report


@pytest.mark.parametrize("mutation", [None, "identity", "groups", "capabilities", "privileges", "lock-held", "lock-link"])
def test_child_protection_and_cross_process_lock_are_required_before_renewal(profile, tmp_path, monkeypatch, capsys, mutation):
    import fcntl
    core, renewal, _, uid, fresh, _, _, _, _ = profile
    monkeypatch.setitem(core, "HOME", tmp_path)
    monkeypatch.setitem(core, "PROFILE", tmp_path)
    monkeypatch.setattr(renewal.pwd, "getpwuid", lambda value: NS(pw_name="wrong" if mutation == "identity" else "hermes-runtime",
        pw_uid=uid, pw_gid=os.getegid(), pw_dir=str(tmp_path)))
    monkeypatch.setattr(renewal.os, "getgroups", lambda: [os.getegid(), os.getegid() + 1] if mutation == "groups" else [os.getegid()])
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    read_text = Path.read_text
    def text(path, *args, **kwargs):
        if str(path) == "/proc/self/status":
            return ("NoNewPrivs: " + ("0" if mutation == "privileges" else "1") + "\nCapAmb: 0000000000000000\nCapEff: "
                + ("0000000000000001" if mutation == "capabilities" else "0000000000000000") + "\n")
        return read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", text)
    monkeypatch.setitem(core, "open_directory", lambda path, owners: os.open(path, os.O_RDONLY | os.O_DIRECTORY))
    operations = []
    def action(*args):
        operations.append(True)
        return {"complete": True}
    monkeypatch.setattr(renewal, "renew", action)
    held = None
    if mutation == "lock-held":
        held = os.open(tmp_path / ".cognee-renewal.lock", os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if mutation == "lock-link": (tmp_path / ".cognee-renewal.lock").symlink_to(tmp_path / ".env")
    try:
        if mutation:
            with pytest.raises(SystemExit): renewal.child_main(core, fresh)
        else: renewal.child_main(core, fresh)
    finally:
        if held is not None: os.close(held)
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] == (mutation is None)
    assert bool(operations) == (mutation is None)


def test_same_human_operator_guard_still_applies_to_composed_renewal(modules, monkeypatch, capsys):
    issuer, renewal = modules
    core = vars(issuer)
    monkeypatch.setattr(issuer.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(issuer, "load_signing_key", lambda: pytest.fail("No privileged key read allowed"))
    sources = {"integrations/hermes/deployment/provision_pilot_access.py": b"# reviewed public core"}
    with pytest.raises(SystemExit, match="approved human"):
        renewal.main(core=core, sources=sources)
    assert not capsys.readouterr().out


def test_failure_after_publication_preserves_both_generations_without_rollback(profile, tmp_path):
    core, renewal, directory, uid, fresh, old, files, _, _ = profile
    def drift(phase):
        if phase == "published": (tmp_path / "auth.json").write_bytes(b"PRIVATE_CONCURRENT_OAUTH_CHANGE")
    with pytest.raises(core["ProvisionError"]): renewal.renew(core, directory, fresh, uid, drift)
    assert renewal.environment(core, (tmp_path / ".env").read_bytes()) == fresh["token"]
    assert next(tmp_path.glob(".env-before-cognee-renew-*")).read_bytes() == files[".env"]
    assert (tmp_path / "auth.json").read_bytes() == b"PRIVATE_CONCURRENT_OAUTH_CHANGE"
    assert not list(tmp_path.glob("*.done.json"))


@pytest.mark.parametrize("phase", ["prepared", "published", "verified"])
def test_next_fresh_renewal_recovers_interruption_and_preserves_every_backup(profile, tmp_path, monkeypatch, phase):
    core, renewal, directory, uid, fresh, _, files, _, data = profile
    def interrupt(current):
        if current == phase: raise InterruptedError()
    with pytest.raises(InterruptedError): renewal.renew(core, directory, fresh, uid, interrupt)
    later = fresh["claims"]["iat"] + 2
    monkeypatch.setattr(renewal.time, "time", lambda: later)
    next_bundle = core["make_bundle"](KEY, later)
    core["api_status"] = lambda token: (200, dict(data)) if token == next_bundle["token"] else (401, {})
    report = renewal.renew(core, directory, next_bundle, uid)
    assert report["interrupted_attempts_reconciled"] == 1
    assert renewal.environment(core, (tmp_path / ".env").read_bytes()) == next_bundle["token"]
    backups = list(tmp_path.glob(".env-before-cognee-renew-*"))
    assert len(backups) == 2 and files[".env"] in [p.read_bytes() for p in backups]
    assert len(list(tmp_path.glob("*.done.json"))) == 2
