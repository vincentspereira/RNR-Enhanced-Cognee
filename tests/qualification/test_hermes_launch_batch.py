"""Consolidated-run admission and native launcher boundaries; no host actions."""
import ast
import importlib.util
import json
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace as NS

import pytest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def native():
    return load("integrations/hermes/deployment/qualify_launch_candidate.py", "native_launch_test")


@pytest.mark.asyncio
async def test_launch_accepts_status_from_actual_memory_service(native):
    from src.memory_service import MemoryService, MemoryScope
    class Connection:
        async def fetchval(self, *args): return 0
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    service = MemoryService(NS(acquire=Connection), NS(_enabled=True))
    scope = MemoryScope("qualification", "launch_fixture", "fixture", "fixture")
    status = await service.status(scope)
    native.validate_status(status, scope.project)
    assert status["encryption"] == "AES-256-GCM"


@pytest.mark.parametrize("key,value", [("encryption", "enabled"), ("encryption", "disabled"),
    ("tenant_id", "private"), ("project_id", "other"), ("schema_version", 3.0), ("ready", 1)])
def test_launch_status_rejects_wrong_contract(native, key, value):
    status = dict(ready=True, schema_version=3, tenant_id="qualification",
                  project_id="launch_fixture", encryption="AES-256-GCM")
    status[key] = value
    with pytest.raises(ValueError): native.validate_status(status, "launch_fixture")


@pytest.mark.parametrize("phase", sorted({"secondary_model_credential", "authenticated_status", "native_clarification"}))
def test_child_failure_reports_stage_without_exception_content(native, phase):
    native.CHILD_PROGRESS["native_substage"] = phase
    report = native.child_failure(ValueError("PRIVATE_TOKEN_AND_MODEL_OUTPUT"))
    assert report == dict(complete=False, native_substage=phase,
                          native_failure_category="condition_or_native_error", native_http_status=None)
    assert "PRIVATE" not in json.dumps(report)


@pytest.mark.parametrize("mutation", [None, "private-field", "private-phase", "private-category", "bad-status"])
def test_parent_only_accepts_fixed_child_failure_fields(native, monkeypatch, mutation):
    report = dict(complete=False, native_substage="authenticated_status",
                  native_failure_category="http_error", native_http_status=401)
    if mutation == "private-field": report["PRIVATE"] = "secret"
    if mutation == "private-phase": report["native_substage"] = "PRIVATE"
    if mutation == "private-category": report["native_failure_category"] = "PRIVATE"
    if mutation == "bad-status": report["native_http_status"] = "PRIVATE"
    monkeypatch.setattr(native.subprocess, "run", lambda *a, **kw: NS(returncode=1, stdout=json.dumps(report).encode()))
    with pytest.raises(ValueError):
        native.run_child(NS(pw_uid=995, pw_gid=996), {}, {}, "question", Path("/opt/public-candidate"))
    if mutation is None:
        assert native.PROGRESS["native_substage"] == "authenticated_status"
        assert native.PROGRESS["native_failure_category"] == "http_error"
    else:
        assert "native_substage" not in native.PROGRESS


def test_inspection_uses_only_status_and_never_reads_oauth_or_creates_profile(native, monkeypatch):
    import types
    calls = []
    settings = json.dumps(dict(base_url="http://127.0.0.1:28080", timeout=10,
                               include_shared=True, capture_policy="selected")).encode()
    snapshots = {"enhanced_cognee.json": settings, "config.yaml": b"original"}
    files = dict(snapshots, **{".env": b"private-test-env"})
    core = dict(PROFILE=Path("/private-pilot"),
                preflight=lambda approved, include_auth: (calls.append(("preflight", include_auth)) or (995, dict(snapshots))),
                read_private=lambda name, uid: (calls.append(("read", name)) or files[name]),
                verify_provider=lambda: calls.append(("verify_provider",)))
    class Client:
        def __init__(self, origin, token, timeout):
            assert origin == "http://127.0.0.1:28080" and token == "fixture-only" and timeout == 10
        def request(self, method, path):
            calls.append((method, path))
            return dict(ready=True, schema_version=3, tenant_id="qualification", project_id="hermes_pilot",
                        subject="hermes_pilot_runtime", encryption="AES-256-GCM")
    monkeypatch.setattr(native, "definitions", lambda source, name: core if source == "core" else {"MemoryClient": Client})
    package = types.ModuleType("agent")
    secrets = types.ModuleType("agent.secret_scope")
    secrets.__file__ = str(native.RELEASE / "repo/agent/secret_scope.py")
    secrets.load_env_file = lambda path: {"ENHANCED_COGNEE_ACCESS_TOKEN": "fixture-only"}
    package.secret_scope = secrets
    monkeypatch.setitem(sys.modules, "agent", package)
    monkeypatch.setitem(sys.modules, "agent.secret_scope", secrets)
    sources = {native.BASE + "deployment/check_pilot_codex.py": "core",
               native.BASE + "enhanced_cognee/client.py": "client"}
    report = native.child(sources, {}, "inspect", Path("/unused"))
    assert report["complete"] is True and report["authenticated_status_contract_passed"] is True
    assert report["model_called"] is report["memory_records_written"] is report["oauth_store_read"] is False
    assert ("preflight", False) in calls and ("read", "auth.json") not in calls
    assert [c for c in calls if c[0] in {"GET", "POST", "PATCH", "DELETE"}] == [("GET", "/v1/memories/status")]


def test_read_only_receipt_rejects_any_claim_that_it_called_model(native, monkeypatch):
    report = dict(complete=True, authenticated_status_contract_passed=True,
                  original_pilot_settings_and_credentials_preserved=True,
                  model_called=True, memory_records_written=False, oauth_store_read=False)
    monkeypatch.setattr(native.subprocess, "run", lambda *a, **kw: NS(returncode=0, stdout=json.dumps(report).encode()))
    with pytest.raises(ValueError):
        native.run_child(NS(pw_uid=995, pw_gid=996), {}, {}, "inspect", Path("/opt/public-candidate"))


def test_pinned_launcher_matches_every_public_source_and_never_extracts_a_bundle():
    import hashlib
    script = Path("scripts/qualification/run_hermes_launch_native.sh").read_text()
    bootstrap = shlex.split(script.split("/usr/bin/python3 -I -B -c ", 1)[1])[0]
    tree = ast.parse(bootstrap)
    table = next(n.value for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "expected")
    expected = ast.literal_eval(table)
    assert len(expected) == 7
    assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest for name, digest in expected.items())
    assert "extractall" not in bootstrap and "extract(" not in bootstrap
    assert 'member.name in sources' in bootstrap and 'member.isfile()' in bootstrap
    assert 'set(sources)!=set(expected)' in bootstrap
    assert 'namespace["PROGRESS"]' in bootstrap


@pytest.mark.parametrize("counts", ["", '<testsuites/>', '<testsuite tests="0"/>',
    '<testsuite tests="1" failures="2"/>', '<testsuite tests="-1"/>', '<testsuite tests="PRIVATE"/>'])
def test_empty_or_malformed_reports_never_pass(counts, tmp_path):
    module = load("scripts/qualification/run_launch_batches.py", "launch_batches_test")
    path = tmp_path / "report.xml"
    path.write_text(counts)
    with pytest.raises(Exception):
        module.counts(path)


def test_skip_failure_and_error_counts_remain_separate(tmp_path):
    module = load("scripts/qualification/run_launch_batches.py", "launch_batches_counts")
    path = tmp_path / "report.xml"
    path.write_text('<testsuites><testsuite tests="5" failures="1" errors="1" skipped="1"/></testsuites>')
    assert module.counts(path) == dict(tests=5, failures=1, errors=1, skipped=1, passed=2)


@pytest.mark.parametrize("environment", [{}, {"WSL_DISTRO_NAME": "Ubuntu-Workspace"},
    {"WSL_DISTRO_NAME": "Ubuntu-Hermes", "SUDO_USER": "other"}])
def test_operator_boundary_refuses_before_loading_sources_or_keys(native, monkeypatch, environment):
    monkeypatch.setattr(native.os, "geteuid", lambda: 0)
    monkeypatch.setattr(native.os, "environ", environment)
    monkeypatch.setattr(native, "definitions", lambda *a: pytest.fail("Refused operator reached source execution"))
    with pytest.raises(ValueError):
        native.main({})


def test_root_report_parser_rejects_unexpected_private_fields(native, monkeypatch):
    account = NS(pw_uid=995, pw_gid=996)
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return NS(returncode=0, stdout=json.dumps(dict(complete=True, model_requests=1,
            original_pilot_settings_and_credentials_preserved=True, record_id="fixture",
            question_and_preservation_passed=True, PRIVATE_TOKEN="never-publish")).encode())
    monkeypatch.setattr(native.subprocess, "run", run)
    with pytest.raises(ValueError):
        native.run_child(account, {native.BASE + "deployment/qualify_launch_candidate.py": b"# public"},
                         {"token": "ordinary-synthetic-token"}, "question", Path("/opt/public-candidate"))
    command, options = calls[0]
    assert options["user"] == 995 and options["group"] == 996 and options["extra_groups"] == ()
    assert options["timeout"] == 150 and "--no-new-privs" in command
    assert "-I" in command and "-B" in command
    assert "ordinary-synthetic-token" not in " ".join(command)
    assert not any("KEY" in key or "TOKEN" in key for key in options["env"])


@pytest.mark.parametrize("violation", ["exit", "oversized", "missing", "bool-count", "too-many", "false-flag"])
def test_native_receipt_failure_never_becomes_qualification(native, monkeypatch, violation):
    report = dict(complete=True, model_requests=1, original_pilot_settings_and_credentials_preserved=True,
                  record_id="fixture", question_and_preservation_passed=True)
    if violation == "missing": report.pop("question_and_preservation_passed")
    if violation == "bool-count": report["model_requests"] = True
    if violation == "too-many": report["model_requests"] = 7
    if violation == "false-flag": report["question_and_preservation_passed"] = False
    raw = b"x" * 16385 if violation == "oversized" else json.dumps(report).encode()
    monkeypatch.setattr(native.subprocess, "run", lambda *a, **kw: NS(returncode=int(violation == "exit"), stdout=raw))
    with pytest.raises(ValueError):
        native.run_child(NS(pw_uid=995, pw_gid=996), {}, {}, "question", Path("/opt/public-candidate"))


def test_installed_batch_refuses_workspace_without_artifact_or_host_mutation(tmp_path, monkeypatch):
    module = load("scripts/qualification/run_launch_batches.py", "launch_batches_boundary")
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Workspace")
    path = tmp_path / "report"
    with pytest.raises(SystemExit):
        module.main(["installed", "--artifacts", str(path), "--revision", "a" * 40])
    assert not path.exists()


@pytest.mark.parametrize("mutation", ["changed-source", "extra-file", "duplicate", "symlink", "over-budget"])
def test_untrusted_bundle_never_executes_or_extracts(native, tmp_path, mutation):
    import hashlib
    import io
    import subprocess
    import tarfile
    script = Path("scripts/qualification/run_hermes_launch_native.sh").read_text()
    bootstrap = shlex.split(script.split("/usr/bin/python3 -I -B -c ", 1)[1])[0]
    tree = ast.parse(bootstrap)
    expected = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "expected"))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in expected:
            raw = Path(name).read_bytes()
            if mutation == "changed-source" and name.endswith("qualify_launch_candidate.py"):
                raw += b'\nraise RuntimeError("PRIVATE_CONTENT_MUST_NOT_EXECUTE")\n'
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        if mutation in {"extra-file", "duplicate", "symlink"}:
            name = next(iter(expected)) if mutation == "duplicate" else "PRIVATE_UNEXPECTED_FILE"
            member = tarfile.TarInfo(name)
            if mutation == "symlink": member.type, member.linkname = tarfile.SYMTYPE, "/etc/private-not-read"
            archive.addfile(member, io.BytesIO(b""))
    raw = stream.getvalue() if mutation != "over-budget" else b"X" * 1048577
    process = subprocess.run([sys.executable, "-I", "-B", "-c", bootstrap], input=raw,
                             cwd=tmp_path, capture_output=True, check=False)
    assert process.returncode == 1 and process.stderr == b""
    assert json.loads(process.stdout) == dict(complete=False, failure_stage="public_bundle_verification")
    assert b"PRIVATE_" not in process.stdout and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("violation", [None, "other-id", "stale", "float-version", "content", "retract-first",
                                       "create", "missing-retraction", "rate-limit"])
def test_native_followup_transport_is_limited_to_confirmed_target(native, tmp_path, monkeypatch, violation):
    import types
    sent = []
    options = {}
    provider = NS(_client=NS(request=lambda method, path, body=None: sent.append((method, path, body)) or
                            ({"version": 3} if method == "PATCH" else {"version": 4, "state": "retracted"})))
    class Manager:
        def add_provider(self, value): assert value is provider
        def initialize_all(self, *a, **kw): assert kw["hermes_home"] == str(tmp_path)
    class Agent:
        def __init__(self, **kw):
            options.update(kw)
            self.max_iterations = kw["max_iterations"]
        def close(self): options["closed"] = True
        def run_conversation(self, prompt, conversation_history):
            assert prompt == "REAL_TERMINAL_ANSWER_FIXTURE" and conversation_history == []
            body = dict(expected_version=2, content="Fictional Cedar launch fixture uses five-day reviews.")
            method, path = "PATCH", "/v1/memories/target"
            if violation == "other-id": path = "/v1/memories/other"
            if violation == "stale": body["expected_version"] = 1
            if violation == "float-version": body["expected_version"] = 2.0
            if violation == "content": body["content"] = "Unrelated change"
            if violation == "retract-first": method, path, body = "POST", path + "/retract", {"expected_version": 2}
            if violation == "create": method, path = "POST", "/v1/memories"
            provider._client.request(method, path, body)
            if violation != "missing-retraction":
                provider._client.request("POST", "/v1/memories/target/retract", {"expected_version": 3})
            return dict(completed=True)
    monkeypatch.setitem(sys.modules, "run_agent", NS(__file__=str(native.RELEASE / "repo/run_agent.py"), AIAgent=Agent))
    monkeypatch.setitem(sys.modules, "agent", types.ModuleType("agent"))
    monkeypatch.setitem(sys.modules, "agent.memory_manager", NS(MemoryManager=Manager))
    monkeypatch.setattr(native, "api", lambda token, method, path: (404, {}))
    core = dict(PROFILE=tmp_path, MODEL="synthetic-model", BASE_URL="https://example.invalid",
                restrict_agent=lambda agent, allowed: dict(count=1, rate_limited=violation == "rate-limit"))
    target = dict(run_id="fixture", record_id="target", peer_token="synthetic-peer-only")
    if violation is None:
        assert native.native_turn(core, provider, "synthetic-oauth-only", "REAL_TERMINAL_ANSWER_FIXTURE", target) == 1
        assert len(sent) == 2
        assert "record_id=target" in options["ephemeral_system_prompt"]
        assert "current version=2" in options["ephemeral_system_prompt"]
        assert "synthetic-oauth-only" not in options["ephemeral_system_prompt"]
        assert options["max_iterations"] == 6 and options["run_budget_seconds"] == 100
    else:
        with pytest.raises(ValueError):
            native.native_turn(core, provider, "synthetic-oauth-only", "REAL_TERMINAL_ANSWER_FIXTURE", target)
        if violation not in {"missing-retraction", "rate-limit"}: assert sent == []
    assert options["closed"] and options["fallback_model"] == {} and options["credential_pool"] is None
    assert options["run_budget_seconds"] == 100 and options["save_trajectories"] is False
