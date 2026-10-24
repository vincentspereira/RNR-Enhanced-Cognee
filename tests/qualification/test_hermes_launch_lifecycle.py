"""Run both launch child stages with real provider/core and simulated host/model.

Actual provider shutdown, journal I/O, reinitialization and tool guards run here.
The memory transport and native host/model are fixtures, not installed evidence.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest

from test_hermes_provider_contract import provider_module


@pytest.fixture
def private_umask():
    # The production child is a separate process; this in-process simulation
    # must restore its process-wide file-mode mask for unrelated fixtures.
    original = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(original)


@pytest.mark.parametrize("damage", [None, "question", "record", "history", "pending", "answer-history"])
def test_both_native_child_stages_reopen_closed_provider_and_preserve_gates(provider_module, monkeypatch, damage, private_umask):
    module, root = provider_module
    spec = importlib.util.spec_from_file_location("launch_lifecycle", "integrations/hermes/deployment/qualify_launch_candidate.py")
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    core = native.definitions(Path("integrations/hermes/deployment/check_pilot_codex.py").read_text(), "launch_core_fixture")
    run_id = "a" * 24
    project = "launch_" + run_id
    profile = root / ("hermes-launch-" + run_id)
    release = root / "release"
    repo = release / "repo"
    (repo / "agent").mkdir(parents=True)
    (repo / "plugins").mkdir()
    (repo / "run_agent.py").write_text("# Native host fixture\n")
    core.update(RELEASE=release, PROFILE=root / "original-pilot")
    monkeypatch.setattr(native, "RELEASE", release)
    monkeypatch.setattr(native, "Path", lambda value: root if str(value) == "/var/tmp" else Path(value))
    monkeypatch.setattr(module, "get_hermes_home", lambda: profile)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("HERMES_HOME", str(core["PROFILE"]))
    files = {"config.yaml": b"original config", "auth.json": b"private synthetic auth",
             "enhanced_cognee.json": b"original settings", ".env": b"private synthetic env"}
    auth_selections = []
    core.update(preflight=lambda approved, include_auth=True: (os.geteuid(), {
                    k: v for k, v in files.items() if k != ".env" and (include_auth or k != "auth.json")}),
                read_private=lambda name, uid: files[name], verify_provider=lambda: None,
                select_credential=lambda raw, credential_label: (auth_selections.append(True) or "synthetic-oauth"))
    snapshots = copy.deepcopy(files)
    state = {"row": None, "versions": []}
    api_calls = []
    closes = []
    providers = []

    class Client:
        def __init__(self, *args): pass
        def request(self, method, path, body=None):
            api_calls.append((method, path))
            if path == "/v1/memories/status":
                return dict(ready=True, schema_version=3, tenant_id="qualification", project_id=project,
                            subject="launch_" + run_id,
                            encryption="AES-256-GCM", active_records=int(bool(state["row"] and state["row"]["state"] == "active")))
            if path.endswith("/history?limit=10"):
                return copy.deepcopy(dict(record_state=state["row"]["state"], versions=state["versions"]))
            if method == "GET": return copy.deepcopy(state["row"])
            if method == "POST" and path == "/v1/memories":
                assert state["row"] is None
                row = dict(id="fixture", version=1, content=body["content"], state="active", project_id=project)
            else:
                assert body["expected_version"] == state["row"]["version"]
                row = dict(state["row"], version=state["row"]["version"] + 1)
                if method == "PATCH": row["content"] = body["content"]
                else:
                    assert method == "POST" and path.endswith("/retract")
                    row["state"] = "retracted"
            state["row"] = row
            state["versions"].append(copy.deepcopy(row))
            return copy.deepcopy(row)
    monkeypatch.setattr(module, "MemoryClient", Client)
    secrets = sys.modules["agent.secret_scope"]
    secrets.__file__ = str(repo / "agent/secret_scope.py")
    secrets.set_secret_scope = lambda *args, **kw: "fixture-binding"
    secrets.reset_secret_scope = lambda binding: None
    loader = ModuleType("plugins.memory")
    loader.__file__ = str(repo / "plugins/memory.py")
    artifact = root / "public-artifact"
    loader.find_provider_dir = lambda name: artifact
    def load_provider(name):
        provider = module.EnhancedCogneeProvider()
        providers.append(provider)
        return provider
    loader.load_memory_provider = load_provider
    package = ModuleType("plugins")
    package.memory = loader
    monkeypatch.setitem(sys.modules, "plugins", package)
    monkeypatch.setitem(sys.modules, "plugins.memory", loader)
    class Manager:
        def add_provider(self, provider): self.provider = provider
        def initialize_all(self, session, **kwargs): self.provider.initialize(session, **kwargs)
    class Agent:
        def __init__(self, **kwargs):
            self.options = kwargs
            self.max_iterations = kwargs["max_iterations"]
        def run_conversation(self, prompt, conversation_history):
            provider = self.options["memory_manager"].provider
            provider.on_turn_start(1, prompt)
            def call(name, **args):
                callback = self.options.get("tool_progress_callback")
                if callback: callback("tool.started", "enhanced_" + name)
                result = json.loads(provider.handle_tool_call("enhanced_" + name, args))
                assert "error" not in result
                return result
            if "not decided" in prompt:
                call("get", record_id="fixture")
                call("clarify", record_id="fixture", reason="conflict")
                answer = "Would you like five-day reviews?" if damage != "question" else "Please confirm your preference."
            else:
                call("correct", record_id="fixture", expected_version=2,
                     content="Fictional Cedar launch " + run_id + " uses five-day reviews.",
                     user_confirmation_quote=prompt)
                call("retract", record_id="fixture", expected_version=3)
                answer = "The invented record was corrected and retracted."
            return dict(completed=True, final_response=answer)
        def close(self):
            provider = self.options["memory_manager"].provider
            provider.shutdown()
            assert provider._client is None and provider._pending_clarifications == set()
            closes.append(True)
            if len(closes) == 1 and damage == "record": state["row"]["content"] = "unexpected record change"
            if len(closes) == 1 and damage == "history": state["versions"][0]["content"] = "unexpected history change"
            if len(closes) == 1 and damage == "pending":
                with provider._clarification_journal(create=True) as journal:
                    provider._record_clarification(journal, "fixture", False)
            if len(closes) == 2 and damage == "answer-history": state["versions"][0]["version"] = 99
    monkeypatch.setitem(sys.modules, "run_agent", NS(__file__=str(repo / "run_agent.py"), AIAgent=Agent))
    monkeypatch.setitem(sys.modules, "agent.memory_manager", NS(MemoryManager=Manager))
    core["restrict_agent"] = lambda agent, allowed, **kwargs: {"count": 1}
    monkeypatch.setattr(native, "definitions", lambda *args: core)
    monkeypatch.setattr(native, "api", lambda *args: (404, {}))
    bundle = dict(run_id=run_id, project=project, token="synthetic-api", peer_token="synthetic-peer")
    sources = {native.BASE + "deployment/check_pilot_codex.py": "reviewed-core"}
    if damage in {"question", "record", "history", "pending"}:
        with pytest.raises(ValueError): native.child(sources, bundle, "question", artifact)
        assert native.CHILD_PROGRESS["native_substage"] == {
            "question": "question_preservation", "record": "question_record_preservation",
            "history": "question_history_preservation", "pending": "question_pending_gate"}[damage]
        assert state["row"]["version"] == 2 and len(state["versions"]) == 2
        assert closes == [True]
    else:
        question = native.child(sources, bundle, "question", artifact)
        assert question["question_and_preservation_passed"] is True
        assert state["row"]["version"] == 2
        assert question["record_id"] == "fixture"
        assert all(p._client is None for p in providers)
        journal_before = (profile / ".enhanced-cognee-clarifications.jsonl").read_bytes()
        canonical_before = copy.deepcopy(state)
        prepared = native.child(sources, bundle, "resume-check", artifact)
        assert prepared["pending_original_fixture_verified"] is True and prepared["record_id"] == "fixture"
        assert prepared["model_called"] is prepared["memory_records_written"] is prepared["oauth_store_read"] is False
        assert len(auth_selections) == 1 and closes == [True]
        assert (profile / ".enhanced-cognee-clarifications.jsonl").read_bytes() == journal_before
        assert state == canonical_before
        bundle.update(record_id="fixture", human_answer="Use five-day reviews, then retract the invented record.")
        if damage == "answer-history":
            with pytest.raises(ValueError): native.child(sources, bundle, "answer", artifact)
            assert native.CHILD_PROGRESS["native_substage"] == "final_history"
        else:
            answer = native.child(sources, bundle, "answer", artifact)
            assert answer["complete"] is answer["restart_pending_gate_passed"] is answer["history_preserved"] is True
            assert answer["versioned_correction_and_retraction_passed"] is True
            assert [row["version"] for row in state["versions"]] == [1, 2, 3, 4]
        assert closes == [True, True] and len(providers) == 3
        assert state["row"]["version"] == 4 and state["row"]["state"] == "retracted"
    assert files == snapshots
    assert Path(os.environ["HERMES_HOME"]) == core["PROFILE"] == root / "original-pilot"
    assert (profile / ".enhanced-cognee-clarifications.jsonl").is_file()
