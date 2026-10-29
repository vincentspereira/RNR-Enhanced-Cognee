"""Synthetic admission and restricted local qualification; no host/model calls."""
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import tarfile
from types import SimpleNamespace as NS

import httpx
import jwt
import pytest


@pytest.fixture
def privacy():
    path = Path("integrations/hermes/deployment/check_pilot_privacy.py").resolve()
    spec = importlib.util.spec_from_file_location("pilot_privacy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Refused(RuntimeError):
    def __init__(self, status, clarify=False):
        self.status_code, self.clarification_required = status, clarify
        super().__init__("PRIVATE_ERROR_SENTINEL")


class CheckError(RuntimeError):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize("case_index", range(11))
async def test_actual_api_admission_rejects_every_case_before_canonical_database_access(privacy, monkeypatch, case_index):
    from src.memory_api import create_app
    from src.memory_service import MemoryService
    signing = "synthetic-privacy-test-signing-key-not-a-real-service-key"
    monkeypatch.setenv("ENHANCED_JWT_SECRET", signing)
    now = int(time.time())
    token = jwt.encode({"sub": "hermes_pilot_runtime", "tenant": "qualification", "project_id": "hermes_pilot",
        "agent_id": "hermes_pilot", "roles": ["api_client"], "capture_policy": "selected",
        # This lane tests content admission, not exact issue-time boundaries.
        # A small host clock correction must not turn it into a 401 test.
        "iat": now - 30, "exp": now + 300}, signing, algorithm="HS256")
    pool = NS(acquire=lambda: pytest.fail("Rejected input must not reach a database write/read transaction"))
    service = MemoryService(pool, NS(_enabled=True))
    # Request-budget accounting uses PostgreSQL before content admission. Keep
    # that separate existing subsystem out of this no-database semantic test.
    async def admit_budget(principal, budget):
        assert principal.subject == "hermes_pilot_runtime"
    service.admit_request = admit_budget
    name, method, path, body, status, clarify = privacy.cases("synthetic-cedar")[case_index]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(service)), base_url="http://test") as client:
        result = await client.request(method, path, json=body, headers={"Authorization": "Bearer " + token})
    assert result.status_code == status
    assert (result.json().get("clarification_required") is True) == clarify
    assert "ghp_" + "Q" * 40 not in result.text and "synthetic-person@example.invalid" not in result.text


def test_probe_requires_all_expected_statuses_and_clarification_flags(privacy):
    plan = privacy.cases("synthetic-cedar")
    calls, results = [], []
    def request(method, path, body):
        calls.append((method, path))
        _, _, _, _, status, clarify = plan[len(calls) - 1]
        raise Refused(status, clarify)
    assert privacy.probe(request, Refused, "synthetic-cedar", results)
    assert len(calls) == len(results) == 11 and all(row["expected_refusal"] for row in results)
    assert "PRIVATE_" not in json.dumps(results) and "ghp_" not in json.dumps(results)


@pytest.mark.parametrize("outcome", ["accepted", "401", "403", "409", "422-clarify", "timeout"])
def test_unexpected_response_stops_immediately_and_retains_case_evidence(privacy, outcome):
    results = []
    def request(*a):
        if outcome == "accepted": return {"id": "PRIVATE_RECORD"}
        if outcome == "timeout": raise Refused(None)
        if outcome == "422-clarify": raise Refused(422, True)
        raise Refused(int(outcome))
    assert not privacy.probe(request, Refused, "synthetic-cedar", results)
    assert len(results) == 1 and not results[0]["expected_refusal"]
    assert "PRIVATE_" not in json.dumps(results)


def main_fixture(privacy, monkeypatch, *, mutation=None):
    files = {"config.yaml": b"memory:\n  provider: enhanced_cognee\n", ".env": b"PRIVATE_MEMORY_TOKEN",
        "enhanced_cognee.json": json.dumps({"base_url": "http://127.0.0.1:28080", "timeout": 10,
            "include_shared": True, "capture_policy": "selected"}).encode()}
    reads, resets, calls, snapshots = [], [], [], []
    plan = privacy.cases("synthetic-cedar")
    def request(*args):
        calls.append(args)
        if mutation == "exception": raise RuntimeError("PRIVATE_NATIVE_ERROR")
        if mutation == "accepted": return {"id": "PRIVATE_UNEXPECTED_RECORD"}
        *_, status, clarify = plan[len(calls) - 1]
        raise Refused(status, clarify)
    def read(name, uid):
        assert name in files and name != "auth.json"
        reads.append(name)
        if mutation == "profile-drift" and calls and name == "config.yaml": return b"PRIVATE_CHANGED_CONFIG"
        return files[name]
    def preflight(approved, **kwargs):
        if approved is not True: raise CheckError("restricted_identity")
        assert kwargs == {"include_auth": False}
        return os.geteuid(), {k: v for k, v in files.items() if k != ".env"}
    core = {"preflight": preflight, "read_private": read, "verify_provider": lambda: None,
        "HOME": Path("/synthetic/home"), "CheckError": CheckError,
        "failure": lambda error: {"category": str(error) if isinstance(error, CheckError) else "unclassified"}}
    monkeypatch.setattr(privacy.os, "chdir", lambda p: None)
    monkeypatch.setattr(privacy.logging, "disable", lambda p: None)
    provider = NS(_client=NS(request=request), shutdown=lambda: resets.append("shutdown"))
    monkeypatch.setattr(privacy, "open_provider", lambda core: (
        provider, NS(reset_secret_scope=lambda value: resets.append(value)), "binding", Refused))
    def snapshot(*a):
        snapshots.append(True)
        return {"current": {"id": "synthetic-cedar"}, "value": 2 if mutation == "canonical-drift" and calls else 1}
    monkeypatch.setattr(privacy, "snapshot", snapshot)
    return core, reads, resets, calls, snapshots


def test_main_qualifies_local_api_only_and_preserves_profile_without_oauth_access(privacy, monkeypatch, capsys):
    core, reads, resets, calls, snapshots = main_fixture(privacy, monkeypatch)
    privacy.main(core=core, approved_test=True)
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] and report["cases_passed"] == 11
    assert report["existing_canonical_and_history_preserved"] and report["receipts_and_checked_profile_files_preserved"]
    assert not any(report[k] for k in ("model_called", "oauth_store_read", "native_model_privacy_qualified",
        "memory_records_written", "runtime_qualified"))
    assert "auth.json" not in reads and len(calls) == 11 and len(snapshots) == 2
    assert resets == ["shutdown", "binding"]


@pytest.mark.parametrize("mutation", ["accepted", "exception", "canonical-drift", "profile-drift"])
def test_main_preserves_unexpected_state_and_sanitizes_every_failure(privacy, monkeypatch, capsys, mutation):
    core, reads, resets, calls, snapshots = main_fixture(privacy, monkeypatch, mutation=mutation)
    with pytest.raises(SystemExit): privacy.main(core=core, approved_test=True)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert not report["complete"] and "PRIVATE_" not in output
    assert report["existing_state_preservation_verified"] == (mutation in {"accepted", "exception"})
    assert len(snapshots) == 2 and resets == ["shutdown", "binding"]
    assert len(calls) == (1 if mutation in {"accepted", "exception"} else 11)


def test_no_profile_read_or_api_attempt_without_explicit_approval(privacy, monkeypatch, capsys):
    core, reads, resets, calls, snapshots = main_fixture(privacy, monkeypatch)
    with pytest.raises(SystemExit): privacy.main(core=core, approved_test=False)
    assert not reads and not calls and not snapshots and not resets
    assert json.loads(capsys.readouterr().out)["failure_stage"] == "restricted_preflight"


@pytest.mark.parametrize("mutation", [None, "scope", "history"])
def test_snapshot_validates_existing_fixtures_versions_history_and_receipts(privacy, mutation):
    core = {"CheckError": CheckError,
        "memory_status": lambda p: {"active_records": 3 if mutation == "scope" else 2},
        "read_state": lambda uid, followup=False: {"fixture": "second" if followup else "first"},
        "read_correction_receipt": lambda *a: ({"record_id": "cedar"}, (1, 2, 3, 4)),
        "verify_saved": lambda *a: {"id": "larch", "version": 1},
        "prior_correction_version": lambda *a: {"id": "cedar", "version": 1},
        "verify_correction": lambda *a: {"id": "cedar", "version": 2},
        "state_stamp": lambda followup=False: (int(followup), 2, 3, 4)}
    def request(method, path):
        assert method == "GET" and path.endswith("/history?limit=3")
        return {"versions": [] if mutation == "history" else [1] if "larch" in path else [1, 2]}
    provider = NS(_client=NS(request=request))
    if mutation:
        with pytest.raises(CheckError): privacy.snapshot(core, provider, 1000)
    else:
        result = privacy.snapshot(core, provider, 1000)
        assert result["current"]["version"] == 2 and len(result["histories"]) == 2 and len(result["receipts"]) == 3


@pytest.mark.parametrize("mutation", [None, "missing", "duplicate", "extra", "traversal", "symlink", "hardlink", "hash", "oversize"])
def test_reviewed_bundle_is_hash_verified_in_memory_with_no_filesystem_extraction(privacy, mutation, tmp_path):
    first = "integrations/hermes/deployment/check_pilot_codex.py"
    second = "integrations/hermes/deployment/check_pilot_privacy.py"
    payload = {first: b"core = True\n", second: b"privacy = True\n"}
    expected = {name: hashlib.sha256(value).hexdigest() for name, value in payload.items()}
    members = list(payload)
    if mutation == "missing": members.pop()
    if mutation == "duplicate": members.append(second)
    if mutation == "extra": members.append("unexpected.py")
    if mutation == "traversal": members.append("../../unexpected.py")
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in members:
            value = payload.get(name, b"raise RuntimeError('must not execute')\n")
            info = tarfile.TarInfo(name)
            if mutation in {"symlink", "hardlink"} and name == second:
                info.type = tarfile.SYMTYPE if mutation == "symlink" else tarfile.LNKTYPE
                info.linkname = first
                archive.addfile(info)
                continue
            if mutation == "hash" and name == second: value = b"modified = True\n"
            if mutation == "oversize" and name == second: value = b"x" * 65537
            info.size = len(value)
            archive.addfile(info, io.BytesIO(value))
    if mutation:
        with pytest.raises(ValueError): privacy.verified_sources(stream.getvalue(), expected)
    else:
        assert privacy.verified_sources(stream.getvalue(), expected) == payload
    assert not list(tmp_path.iterdir())


def test_actual_two_file_sources_compose_without_starting_a_host_check(privacy, capsys):
    paths = [Path("integrations/hermes/deployment/check_pilot_codex.py"),
             Path("integrations/hermes/deployment/check_pilot_privacy.py")]
    payload = {path.as_posix(): path.read_bytes() for path in paths}
    expected = {name: hashlib.sha256(value).hexdigest() for name, value in payload.items()}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, source in payload.items():
            info = tarfile.TarInfo(name)
            info.size = len(source)
            archive.addfile(info, io.BytesIO(source))
    sources = privacy.verified_sources(stream.getvalue(), expected)
    for name, source in sources.items():
        scope = {"__name__": "reviewed_source_only"}
        exec(compile(source, name, "exec"), scope)
        assert callable(scope["main"])
    assert not capsys.readouterr().out


@pytest.mark.parametrize("mutation", [None, "native-source", "missing-token", "provider-link", "initialization", "client-source"])
def test_native_provider_scope_and_source_are_checked_and_binding_is_released_on_failure(privacy, monkeypatch, tmp_path, mutation):
    release, artifact = tmp_path / "release", tmp_path / "artifact"
    (release / "repo").mkdir(parents=True)
    artifact.mkdir()
    source = release / "repo/native.py"
    source.touch()
    client_source = artifact / "client.py"
    client_source.touch()
    resets = []
    secrets = NS(__file__=str(client_source if mutation == "native-source" else source),
        load_env_file=lambda path: {} if mutation == "missing-token" else {"ENHANCED_COGNEE_ACCESS_TOKEN": "PRIVATE_TOKEN"},
        set_secret_scope=lambda *a, **kw: "binding", reset_secret_scope=resets.append)
    client_type = type("Client", (), {"__module__": "synthetic_privacy_client"})
    module = NS(__file__=str(source if mutation == "client-source" else client_source), MemoryTransportError=Refused)
    monkeypatch.setitem(sys.modules, "synthetic_privacy_client", module)
    def initialize(*a, **kw):
        if mutation == "initialization": raise RuntimeError("PRIVATE_INITIALIZATION")
    provider = NS(_client=client_type(), initialize=initialize, shutdown=lambda: resets.append("shutdown"))
    loader = NS(__file__=str(source), find_provider_dir=lambda name: release if mutation == "provider-link" else artifact,
        load_memory_provider=lambda name: provider)
    monkeypatch.setitem(sys.modules, "agent", NS(secret_scope=secrets))
    monkeypatch.setitem(sys.modules, "agent.secret_scope", secrets)
    monkeypatch.setitem(sys.modules, "plugins", NS(memory=loader))
    monkeypatch.setattr(sys, "path", list(sys.path))
    core = {"RELEASE": release, "PROFILE": tmp_path / "profile", "ARTIFACT": artifact, "CheckError": CheckError}
    if mutation:
        with pytest.raises((CheckError, RuntimeError)): privacy.open_provider(core)
        assert ("binding" in resets) == (mutation not in {"native-source", "missing-token"})
    else:
        actual, secret_module, binding, refused = privacy.open_provider(core)
        assert actual is provider and secret_module is secrets and binding == "binding" and refused is Refused
        assert not resets


@pytest.mark.parametrize("mutation", [None, "unapproved", "primary", "model-error", "empty-reply", "echo-password",
    "echo-key", "echo-email", "echo-private", "canonical-drift", "profile-drift", "reopen-error"])
def test_model_privacy_uses_only_selected_oauth_and_compares_state_even_on_failure(privacy, monkeypatch, capsys, mutation):
    core, reads, resets, api_calls, snapshots = main_fixture(privacy, monkeypatch)
    files = {"config.yaml": b"memory:\n  provider: enhanced_cognee\n", "auth.json": b"PRIVATE_OAUTH",
        "enhanced_cognee.json": json.dumps({"base_url": "http://127.0.0.1:28080", "timeout": 10,
            "include_shared": True, "capture_policy": "selected"}).encode(), ".env": b"PRIVATE_MEMORY_TOKEN"}
    turns, selections, reopen = [], [], []
    def preflight(approved, **kwargs):
        assert kwargs == {"include_auth": True}
        if not approved: raise CheckError("restricted_identity")
        return 993, {k: v for k, v in files.items() if k != ".env"}
    def read(name, uid):
        reads.append(name)
        return b"PRIVATE_DRIFT" if mutation == "profile-drift" and turns and name == "auth.json" else files[name]
    def select(raw, **kw):
        assert raw == files["auth.json"] and kw == {"credential_label": "cognee-pilot-codex-secondary"}
        selections.append(True)
        return "PRIVATE_PILOT_ACCESS"
    def initialize(*a, **kw):
        reopen.append(True)
        if mutation == "reopen-error": raise RuntimeError("PRIVATE_REOPEN_ERROR")
    def turn(stage, token, provider, session, prompt):
        assert stage == "privacy" and token == "PRIVATE_PILOT_ACCESS" and session.startswith("pilot_privacy_")
        assert "synthetic integration check" in prompt and "-----BEGIN PRIVATE KEY-----" in prompt
        turns.append(True)
        if mutation == "model-error": raise CheckError("native_agent_turn_incomplete")
        reply = "Private details should be handled in a password vault."
        values = ("invented-canary", "ghp_" + "Q" * 40, "synthetic-person@example.invalid", "NOT-A-KEY-canary")
        if mutation and mutation.startswith("echo-"):
            reply = values[{"echo-password": 0, "echo-key": 1, "echo-email": 2, "echo-private": 3}[mutation]].upper()
        if mutation == "empty-reply": reply = ""
        return reply, [], 1
    provider = NS(initialize=initialize, shutdown=lambda: resets.append("shutdown"))
    monkeypatch.setattr(privacy, "open_provider", lambda core: (
        provider, NS(reset_secret_scope=lambda value: resets.append(value)), "binding", Refused))
    original_case = privacy.model_case
    def case():
        prompt, _ = original_case()
        return prompt, ("invented-canary", "ghp_" + "Q" * 40, "synthetic-person@example.invalid", "NOT-A-KEY-canary")
    monkeypatch.setattr(privacy, "model_case", case)
    def snapshot(*a):
        snapshots.append(True)
        return {"current": {"id": "cedar"}, "value": int(mutation == "canonical-drift" and bool(turns))}
    monkeypatch.setattr(privacy, "snapshot", snapshot)
    monkeypatch.setattr(privacy.os, "umask", lambda value: 0)
    core.update(preflight=preflight, read_private=read, select_credential=select, native_memory_turn=turn,
        MODEL="gpt-6.1-sol", PROFILE=Path("/synthetic/profile"))
    kwargs = {"core": core, "approved_test": mutation != "unapproved"}
    if mutation == "primary": kwargs["credential_label"] = "cognee-pilot-codex"
    if mutation:
        with pytest.raises(SystemExit): privacy.main_model(**kwargs)
    else: privacy.main_model(**kwargs)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["complete"] == (mutation is None)
    assert "PRIVATE_" not in output and "ghp_" not in output and "@example.invalid" not in output
    assert not api_calls
    if mutation in {"unapproved", "primary"}:
        assert not turns and not selections and not snapshots and not resets
    else:
        assert len(turns) == len(selections) == len(reopen) == 1
        assert len(snapshots) == (1 if mutation == "reopen-error" else 2)
        assert resets == ["shutdown", "binding"]
        if mutation:
            assert report["existing_state_preservation_verified"] == (mutation not in {"canonical-drift", "profile-drift", "reopen-error"})
        else:
            assert report["native_selected_privacy_passed"] and report["model_requests"] == 1
            assert not report["memory_records_written"] and not report["runtime_qualified"]
