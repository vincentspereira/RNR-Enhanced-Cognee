"""Consolidated native candidate conversation/access qualification.

The operator stages public pinned provider code without changing the existing
pilot. Two separate restricted processes use a new invented-data profile and
new fixed scopes. A real terminal answer separates the model's question from
the later correction/retraction. This is not whole-fleet launch permission.
Execute only via the reviewed, hash-verified public source bundle.
"""
from __future__ import annotations

import contextlib
import hashlib
from http.client import HTTPConnection
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import time
import uuid

BASE = "integrations/hermes/"
HOME = Path("/var/lib/hermes-runtime")
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
PROGRESS = {"failure_stage": "operator_preflight", "candidate_staged": False,
            "native_question_passed": False, "reviewed_sharing_passed": False,
            "human_answer_received": False, "native_followup_passed": False}
CHILD_PHASES = {"restricted_preflight", "pilot_snapshot", "original_provider_verification",
                "secondary_model_credential", "candidate_profile", "native_imports",
                "candidate_discovery", "candidate_initialization", "authenticated_status",
                "empty_scope", "synthetic_fixture", "native_clarification", "question_preservation",
                "question_reinitialization", "question_pending_gate", "question_record_preservation",
                "question_history_preservation", "answer_reinitialization",
                "resume_pending_fixture",
                "attempt_state_observation",
                "restart_pending_gate", "native_followup", "final_history", "pilot_preservation"}
CHILD_PROGRESS = {"native_substage": "restricted_preflight"}
FOLLOWUP_STATE = None
COMPLETION_DIAGNOSTIC = None
FINISHED_RUNS = {"5d0e9a49bdf544359ae6deff", "e8d9362220ad4a78b3806974", "1fbbc4a6b40b48ed91f3b44b"}
MEMORY_TOOL_NAMES = {"enhanced_recall", "enhanced_get", "enhanced_status", "enhanced_correct", "enhanced_retract", "enhanced_clarify"}


def completion_diagnostic(result, maximum, tools=()):
    value = result if isinstance(result, dict) else {}
    reason = value.get("turn_exit_reason")
    category = "other"
    if isinstance(reason, str):
        if reason.startswith("max_iterations_reached("):
            category = "iteration_limit"
        elif reason.startswith("text_response("):
            category = "text_response"
        elif reason == "budget_exhausted":
            category = "budget_exhausted"
    calls = value.get("api_calls")
    return {"exit_category": category, "api_calls": calls if type(calls) is int and 0 <= calls <= 6 else None,
            "max_iterations": maximum, "final_response_present": value.get("final_response") is not None,
            "failed": value.get("failed") is True, "interrupted": value.get("interrupted") is True,
            "memory_tool_calls": [x for x in tools if x in MEMORY_TOOL_NAMES][:16], "tool_trace_truncated": len(tools) > 16}


def validate_completion_diagnostic(value):
    require(isinstance(value, dict) and set(value) == {"exit_category", "api_calls", "max_iterations",
        "final_response_present", "failed", "interrupted", "memory_tool_calls", "tool_trace_truncated"}
        and value["exit_category"] in {"other", "iteration_limit", "text_response", "budget_exhausted"}
        and (value["api_calls"] is None or type(value["api_calls"]) is int and 0 <= value["api_calls"] <= 6)
        and type(value["max_iterations"]) is int and value["max_iterations"] == 6
        and all(type(value[k]) is bool for k in ("final_response_present", "failed", "interrupted", "tool_trace_truncated"))
        and isinstance(value["memory_tool_calls"], list) and len(value["memory_tool_calls"]) <= 16
        and all(isinstance(x, str) and x in MEMORY_TOOL_NAMES for x in value["memory_tool_calls"]))
    return dict(value)


def validate_followup_state(value):
    flags = {"correction_tool_called", "retraction_tool_called", "correction_committed",
             "peer_withdrawal_verified", "retraction_committed", "native_completed",
             "native_error_present", "rate_limited"}
    require(isinstance(value, dict) and set(value) == flags | {"model_requests", "checkpoint", "last_model_http_status"}
            and all(type(value[k]) is bool for k in flags)
            and (value["model_requests"] is None or type(value["model_requests"]) is int
                 and 0 <= value["model_requests"] <= 6)
            and (value["last_model_http_status"] is None or type(value["last_model_http_status"]) is int
                 and 100 <= value["last_model_http_status"] <= 599)
            and value["checkpoint"] in {"manager_initialization", "agent_initialization", "request_admission",
                "native_conversation", "target_correction", "correction_response", "peer_withdrawal",
                "target_retraction", "retraction_response", "completion_validation"})
    return dict(value)


def validate_status(status, project):
    require(isinstance(status, dict) and status.get("ready") is True
            and type(status.get("schema_version")) is int and status["schema_version"] == 3
            and status.get("tenant_id") == "qualification" and status.get("project_id") == project
            and status.get("encryption") == "AES-256-GCM")


def child_failure(error):
    # Never serialize exception text, paths, model output or arbitrary attributes.
    status = getattr(error, "status_code", None)
    category = ("dependency_missing" if isinstance(error, ModuleNotFoundError) else
                "timeout" if isinstance(error, TimeoutError) else
                "http_error" if type(status) is int and 400 <= status <= 599 else
                "condition_or_native_error")
    result = dict(complete=False, native_substage=CHILD_PROGRESS["native_substage"],
                native_failure_category=category,
                native_http_status=status if type(status) is int and 400 <= status <= 599 else None)
    if FOLLOWUP_STATE is not None:
        result["followup_observation"] = validate_followup_state(FOLLOWUP_STATE)
    if COMPLETION_DIAGNOSTIC is not None:
        result["completion_diagnostic"] = validate_completion_diagnostic(COMPLETION_DIAGNOSTIC)
    return result


def child_inspect(sources):
    """Read authenticated pilot status without loading a provider or a model."""
    core = definitions(sources[BASE + "deployment/check_pilot_codex.py"], "launch_inspection_core")
    uid, snapshots = core["preflight"](True, include_auth=False)
    CHILD_PROGRESS["native_substage"] = "pilot_snapshot"
    snapshots[".env"] = core["read_private"](".env", uid)
    require(json.loads(snapshots["enhanced_cognee.json"]) == {
        "base_url": "http://127.0.0.1:28080", "timeout": 10,
        "include_shared": True, "capture_policy": "selected"})
    CHILD_PROGRESS["native_substage"] = "original_provider_verification"
    core["verify_provider"]()
    CHILD_PROGRESS["native_substage"] = "native_imports"
    sys.path.insert(0, str(RELEASE / "repo"))
    import agent.secret_scope as secrets
    require(Path(secrets.__file__).resolve().is_relative_to(RELEASE / "repo"))
    token = secrets.load_env_file(core["PROFILE"] / ".env").get("ENHANCED_COGNEE_ACCESS_TOKEN")
    require(isinstance(token, str) and bool(token))
    client = definitions(sources[BASE + "enhanced_cognee/client.py"], "launch_inspection_client")
    CHILD_PROGRESS["native_substage"] = "authenticated_status"
    status = client["MemoryClient"]("http://127.0.0.1:28080", token, timeout=10).request("GET", "/v1/memories/status")
    validate_status(status, "hermes_pilot")
    require(status.get("subject") == "hermes_pilot_runtime")
    CHILD_PROGRESS["native_substage"] = "pilot_preservation"
    require(original_profile_unchanged(core, snapshots, uid))
    return dict(complete=True, authenticated_status_contract_passed=True,
                original_pilot_settings_and_credentials_preserved=True,
                model_called=False, memory_records_written=False, oauth_store_read=False)


def require(condition):
    if not condition:
        raise ValueError("qualification_condition_not_met")


def terminal_preflight():
    """A piped source bundle still needs a real terminal for the human answer."""
    try:
        # Buffered text r+ requires seeking; Linux terminals cannot seek.
        with open("/dev/tty", "r", encoding="ascii") as reader, \
                open("/dev/tty", "w", encoding="ascii", buffering=1) as writer:
            require(reader.isatty() and writer.isatty())
    except (OSError, ValueError):
        PROGRESS["human_answer_failure"] = "terminal_unavailable"
        raise ValueError("qualification_terminal_unavailable") from None


def read_human_answer(run_id, *, resumed=False):
    require(isinstance(run_id, str) and re.fullmatch(r"[a-f0-9]{24}", run_id) is not None)
    expected = ("For fictional Cedar launch " + run_id
        + ", use five-day reviews, then retract this invented test record while preserving history.")
    try:
        with open("/dev/tty", "r", encoding="ascii") as reader, \
                open("/dev/tty", "w", encoding="ascii", buffering=1) as writer:
            require(reader.isatty() and writer.isatty())
            lead = ("Existing invented record, history and peer access verified.\n" if resumed else
                    "Native question, unchanged record and scoped sharing checks passed.\n")
            writer.write(lead +
                         "For this invented test only, type the following answer to continue:\n" + expected + "\n> ")
            writer.flush()
            raw = reader.readline(1024)
    except (OSError, ValueError):
        PROGRESS["human_answer_failure"] = "terminal_unavailable_or_encoding"
        raise ValueError("qualification_terminal_input_unavailable") from None
    if not raw:
        PROGRESS["human_answer_failure"] = "terminal_end_of_input"
        raise ValueError("qualification_human_answer_missing")
    if not raw.endswith("\n") or raw.strip() != expected:
        PROGRESS["human_answer_failure"] = "answer_mismatch_or_truncated"
        raise ValueError("qualification_human_answer_not_confirmed")
    return raw.strip()


def verify_pending_fixture(provider, status, run_id):
    """Bind continuation to the explicit invented scope, not a guessed profile."""
    require(type(status.get("active_records")) is int and status["active_records"] == 1
            and status.get("subject") == "launch_" + run_id
            and len(provider._pending_clarifications) == 1)
    ident = next(iter(provider._pending_clarifications))
    require(isinstance(ident, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ident) is not None)
    row = provider._client.request("GET", "/v1/memories/" + ident)
    prefix = "Fictional Cedar launch " + run_id + " uses "
    require(isinstance(row, dict) and row.get("id") == ident and type(row.get("version")) is int
            and row["version"] == 2 and row.get("state") == "active"
            and row.get("project_id") == "launch_" + run_id
            and row.get("content") == prefix + "ten-day reviews.")
    history = provider._client.request("GET", "/v1/memories/" + ident + "/history?limit=10")
    require(isinstance(history, dict) and history.get("record_state") == "active"
            and history.get("next_before_version") is None and not history.get("response_limit_reached"))
    versions = history.get("versions")
    require(isinstance(versions, list) and len(versions) == 2
            and all(isinstance(v, dict) and type(v.get("version")) is int for v in versions)
            and {v["version"] for v in versions} == {1, 2})
    require(all(v.get("id") == ident and v.get("content") == prefix +
                ("eleven-day reviews." if v["version"] == 1 else "ten-day reviews.") for v in versions))
    return ident


def observe_attempt(provider, status, run_id):
    """Read only the explicit invented scope; report shape, never stored text."""
    require(status.get("subject") == "launch_" + run_id
            and type(status.get("active_records")) is int and status["active_records"] in {0, 1})
    with provider._clarification_journal(create=False) as fd:
        require(fd is not None)
        before = os.fstat(fd)
        raw = os.pread(fd, 1048577, 0)
        after = os.fstat(fd)
        require(len(raw) == before.st_size <= 1048576
                and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_size, after.st_mtime_ns, after.st_ctime_ns))
        # initialize() and the journal context already validate every entry.
        ids = {json.loads(line)["record_id"] for line in raw.splitlines()}
        require(len(ids) == 1)
        ident = next(iter(ids))
        require(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ident) is not None)
        pending = provider._pending_clarifications == {ident}
        require(provider._pending_clarifications in (set(), {ident}))
        history = provider._client.request("GET", "/v1/memories/" + ident + "/history?limit=10")
        require(isinstance(history, dict) and history.get("next_before_version") is None
                and not history.get("response_limit_reached"))
        versions = history.get("versions")
        require(isinstance(versions, list) and 2 <= len(versions) <= 4
                and all(isinstance(v, dict) and v.get("id") == ident and type(v.get("version")) is int
                        for v in versions)
                and {v["version"] for v in versions} == set(range(1, len(versions) + 1)))
        rows = {v["version"]: v for v in versions}
        prefix = "Fictional Cedar launch " + run_id + " uses "
        require(rows[1].get("content") == prefix + "eleven-day reviews."
                and rows[2].get("content") == prefix + "ten-day reviews.")
        if len(versions) >= 3:
            content = rows[3].get("content")
            require(isinstance(content, str) and run_id in content
                    and re.search(r"\b(?:five|5)[ -]+day", content.casefold()))
        latest = len(versions)
        retracted = latest == 4
        require(history.get("record_state") == ("retracted" if retracted else "active")
                and status["active_records"] == (0 if retracted else 1))
        if retracted:
            require(rows[4].get("content") == rows[3]["content"])
        else:
            row = provider._client.request("GET", "/v1/memories/" + ident)
            require(isinstance(row, dict) and row.get("id") == ident
                    and row.get("project_id") == "launch_" + run_id
                    and type(row.get("version")) is int and row["version"] == latest
                    and row.get("state") == "active" and row.get("content") == rows[latest]["content"])
    return dict(record_id=ident, canonical_version=latest, record_retracted=retracted,
                pending_clarification_present=pending, history_versions_verified=latest,
                model_called=False, memory_records_written=False, oauth_store_read=False)


def api(token, method, path, body=None):
    require(path.startswith("/v1/memories"))
    connection = HTTPConnection("127.0.0.1", 28080, timeout=10)
    try:
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        response = connection.getresponse()
        raw = response.read(262145)
        require(len(raw) <= 262144)
        return response.status, json.loads(raw)
    finally:
        connection.close()


def definitions(source, name):
    namespace = {"__name__": name}
    exec(compile(source, "<reviewed-" + name + ">", "exec"), namespace)
    return namespace


def candidate_payload(sources):
    return {name: sources[BASE + "enhanced_cognee/" + name] for name in ("__init__.py", "client.py", "plugin.yaml")}


def original_profile_unchanged(core, snapshots, uid):
    return all(core["read_private"](name, uid) == raw for name, raw in snapshots.items())


def native_turn(core, provider, oauth, prompt, target):
    """Permit only the human-confirmed target's exact correction/retraction.

    Keep both editing choices visible. Transport guards prevent unrelated
    writes and verify withdrawal from the peer scope after correction.
    """
    global FOLLOWUP_STATE, COMPLETION_DIAGNOSTIC
    FOLLOWUP_STATE = dict(correction_tool_called=False, retraction_tool_called=False,
        correction_committed=False, peer_withdrawal_verified=False, retraction_committed=False,
        native_completed=False, native_error_present=False, rate_limited=False,
        last_model_http_status=None, model_requests=None, checkpoint="manager_initialization")
    import run_agent
    from agent.memory_manager import MemoryManager
    require(Path(run_agent.__file__).resolve().is_relative_to(RELEASE / "repo"))
    manager = MemoryManager()
    manager.add_provider(provider)
    manager.initialize_all("launch-answer-" + target["run_id"], hermes_home=str(core["PROFILE"]),
                           agent_context="primary", platform="cli")
    original = provider._client.request
    changes = []
    def guarded(method, path, body=None):
        if method == "GET" or method == "POST" and path == "/v1/memories/recall":
            return original(method, path, body)
        endpoint = "/v1/memories/" + target["record_id"]
        require(isinstance(body, dict))
        if not changes:
            FOLLOWUP_STATE["checkpoint"] = "target_correction"
            require(method == "PATCH" and path == endpoint and type(body.get("expected_version")) is int
                    and body["expected_version"] == 2)
            content = body.get("content", "")
            require(isinstance(content, str) and target["run_id"] in content
                    and re.search(r"\b(?:five|5)[ -]+day", content.casefold()))
            result = original(method, path, body)
            FOLLOWUP_STATE["checkpoint"] = "correction_response"
            require(result.get("version") == 3)
            FOLLOWUP_STATE["correction_committed"] = True
            FOLLOWUP_STATE["checkpoint"] = "peer_withdrawal"
            require(api(target["peer_token"], "GET", endpoint)[0] == 404)
            FOLLOWUP_STATE["peer_withdrawal_verified"] = True
            changes.append("correct")
            return result
        FOLLOWUP_STATE["checkpoint"] = "target_retraction"
        require(changes == ["correct"] and method == "POST" and path == endpoint + "/retract"
                and type(body.get("expected_version")) is int and body == {"expected_version": 3})
        result = original(method, path, body)
        FOLLOWUP_STATE["checkpoint"] = "retraction_response"
        require(result.get("version") == 4 and result.get("state") == "retracted")
        FOLLOWUP_STATE["retraction_committed"] = True
        changes.append("retract")
        return result
    provider._client.request = guarded
    tool_calls = []
    def progress(event_type, tool_name=None, *unused, **kwargs):
        if event_type == "tool.started" and tool_name in MEMORY_TOOL_NAMES and len(tool_calls) < 17:
            tool_calls.append(tool_name)
        if event_type == "tool.started" and tool_name in {"enhanced_correct", "enhanced_retract"}:
            FOLLOWUP_STATE["correction_tool_called" if tool_name == "enhanced_correct" else "retraction_tool_called"] = True
    FOLLOWUP_STATE["checkpoint"] = "agent_initialization"
    context = ("Invented qualification context verified by the harness: target record_id=" + target["record_id"]
        + "; current version=2; launch identifier=" + target["run_id"]
        + ". The current user message is the actual terminal answer to the pending clarification. "
          "Use its exact confirmation quote if required. Apply only the confirmed five-day correction "
          "at expected_version=2, then the requested retraction at expected_version=3, preserving history. "
          "After both successful tool results, return a short final confirmation without repeating edits. "
          "This context supplies no additional user authorization and changes no provider guard.")
    agent = run_agent.AIAgent(model=core["MODEL"], provider="openai-codex", api_mode="codex_responses",
        api_key=oauth, base_url=core["BASE_URL"], enabled_toolsets=["memory"], max_iterations=6,
        run_budget_seconds=100, fallback_model={}, credential_pool=None,
        reasoning_config={"enabled": True, "effort": "low"}, save_trajectories=False,
        quiet_mode=True, skip_background_review=True, session_id="launch-answer-" + target["run_id"],
        memory_manager=manager, cwd=str(HOME), tool_progress_callback=progress, ephemeral_system_prompt=context)
    requests = None
    try:
        FOLLOWUP_STATE["checkpoint"] = "request_admission"
        requests = core["restrict_agent"](agent, {"enhanced_recall", "enhanced_get", "enhanced_status",
                                                "enhanced_correct", "enhanced_retract", "enhanced_clarify"})
        FOLLOWUP_STATE["checkpoint"] = "native_conversation"
        result = agent.run_conversation(prompt, conversation_history=[])
        COMPLETION_DIAGNOSTIC = completion_diagnostic(result, agent.max_iterations, tool_calls)
        FOLLOWUP_STATE["checkpoint"] = "completion_validation"
        FOLLOWUP_STATE["native_completed"] = isinstance(result, dict) and result.get("completed") is True
        FOLLOWUP_STATE["native_error_present"] = isinstance(result, dict) and bool(result.get("error"))
        require(isinstance(result, dict) and result.get("completed") is True
                and not result.get("failed") and not result.get("error")
                and not requests.get("rate_limited") and 0 < requests["count"] <= 6
                and changes == ["correct", "retract"])
        return requests["count"]
    finally:
        if isinstance(requests, dict):
            count = requests.get("count")
            FOLLOWUP_STATE["model_requests"] = count if type(count) is int and 0 <= count <= 6 else None
            FOLLOWUP_STATE["rate_limited"] = requests.get("rate_limited") is True
            statuses = requests.get("http_statuses")
            if isinstance(statuses, list) and statuses:
                code = statuses[-1]
                FOLLOWUP_STATE["last_model_http_status"] = code if type(code) is int and 100 <= code <= 599 else None
        agent.close()


def child(sources, bundle, stage, artifact):
    require(stage in {"inspect", "question", "answer", "resume-check", "attempt-state"})
    if stage == "inspect":
        return child_inspect(sources)
    core = definitions(sources[BASE + "deployment/check_pilot_codex.py"], "launch_native_core")
    uid, snapshots = (core["preflight"](True, include_auth=False) if stage in {"resume-check", "attempt-state"}
                      else core["preflight"](True))
    CHILD_PROGRESS["native_substage"] = "pilot_snapshot"
    snapshots[".env"] = core["read_private"](".env", uid)
    original_home = core["PROFILE"]
    CHILD_PROGRESS["native_substage"] = "original_provider_verification"
    core["verify_provider"]()  # Preserve the previous pilot's exact admission.
    oauth = None
    if stage not in {"resume-check", "attempt-state"}:
        CHILD_PROGRESS["native_substage"] = "secondary_model_credential"
        oauth = core["select_credential"](snapshots["auth.json"], credential_label="cognee-pilot-codex-secondary")
    run_id = bundle["run_id"]
    require(re.fullmatch(r"[a-f0-9]{24}", run_id) is not None)
    # The qualified whole-home backup refuses unknown provider links. Keep
    # this disposable candidate profile outside that home so qualification
    # cannot break the already-qualified unattended backup's source policy.
    # Retain this private test directory; it is not admitted everyday state.
    profile = Path("/var/tmp") / ("hermes-launch-" + run_id)
    CHILD_PROGRESS["native_substage"] = "candidate_profile"
    os.umask(0o077)
    if stage == "question":
        profile.mkdir(mode=0o700, exist_ok=False)
        (profile / "plugins").mkdir(mode=0o700)
        (profile / "plugins/enhanced_cognee").symlink_to(artifact, target_is_directory=True)
        fd = os.open(profile / "enhanced_cognee.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as output:
            json.dump({"base_url": "http://127.0.0.1:28080", "timeout": 10,
                       "include_shared": True, "capture_policy": "selected"}, output)
    info = profile.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700)
    os.environ["HERMES_HOME"] = str(profile)
    CHILD_PROGRESS["native_substage"] = "native_imports"
    sys.path.insert(0, str(RELEASE / "repo"))
    import agent.secret_scope as secrets
    from plugins import memory as loader
    require(all(Path(m.__file__).resolve().is_relative_to(RELEASE / "repo") for m in (secrets, loader)))
    binding = secrets.set_secret_scope({"ENHANCED_COGNEE_ACCESS_TOKEN": bundle["token"]}, profile_home=str(profile))
    provider = None
    try:
        CHILD_PROGRESS["native_substage"] = "candidate_discovery"
        require(loader.find_provider_dir("enhanced_cognee").resolve() == Path(artifact))
        provider = loader.load_memory_provider("enhanced_cognee")
        CHILD_PROGRESS["native_substage"] = "candidate_initialization"
        provider.initialize("launch-" + stage + "-" + run_id, hermes_home=str(profile), agent_context="primary")
        core["PROFILE"] = profile
        CHILD_PROGRESS["native_substage"] = "authenticated_status"
        status = provider._client.request("GET", "/v1/memories/status")
        validate_status(status, bundle["project"])
        def call(name, args):
            return json.loads(provider.handle_tool_call("enhanced_" + name, args))
        if stage == "question":
            CHILD_PROGRESS["native_substage"] = "empty_scope"
            require(status.get("active_records") == 0 and provider._pending_clarifications == set())
            provider.on_turn_start(1, "Create an entirely invented qualification decision.")
            CHILD_PROGRESS["native_substage"] = "synthetic_fixture"
            first = call("remember", {"content": "Fictional Cedar launch " + run_id + " uses eleven-day reviews.",
                                       "idempotency_key": "launch-" + run_id})
            ident = first["id"]
            changed = call("correct", {"record_id": ident, "expected_version": 1,
                                       "content": "Fictional Cedar launch " + run_id + " uses ten-day reviews."})
            require(changed.get("version") == 2)
            previous = provider._client.request("GET", "/v1/memories/" + ident)
            before = provider._client.request("GET", "/v1/memories/" + ident + "/history?limit=10")
            prompt = ("For fictional Cedar launch " + run_id + ", I may prefer five-day reviews instead, "
                      "but I have not decided. What should we clarify before changing the standing decision?")
            observation = {}
            CHILD_PROGRESS["native_substage"] = "native_clarification"
            answer, _, requests = core["native_memory_turn"]("clarify", oauth, provider,
                "launch-question-" + run_id, prompt, clarification_target=ident,
                clarification_record=previous, clarification_observation=observation)
            CHILD_PROGRESS["native_substage"] = "question_preservation"
            require(isinstance(answer, str) and "?" in answer)
            # Native agent.close() shuts down its memory manager/provider.
            # Reopen under the same scoped binding for authoritative reads,
            # as the original pilot verification already does.
            CHILD_PROGRESS["native_substage"] = "question_reinitialization"
            provider.initialize("launch-question-verification-" + run_id,
                                hermes_home=str(profile), agent_context="primary")
            CHILD_PROGRESS["native_substage"] = "question_pending_gate"
            require(provider._pending_clarifications == {ident})
            CHILD_PROGRESS["native_substage"] = "question_record_preservation"
            require(provider._client.request("GET", "/v1/memories/" + ident) == previous)
            CHILD_PROGRESS["native_substage"] = "question_history_preservation"
            require(provider._client.request("GET", "/v1/memories/" + ident + "/history?limit=10") == before)
            result = {"record_id": ident, "question_and_preservation_passed": True, "model_requests": requests}
        elif stage == "resume-check":
            CHILD_PROGRESS["native_substage"] = "resume_pending_fixture"
            ident = verify_pending_fixture(provider, status, run_id)
            result = dict(record_id=ident, pending_original_fixture_verified=True,
                          model_called=False, memory_records_written=False, oauth_store_read=False)
        elif stage == "attempt-state":
            CHILD_PROGRESS["native_substage"] = "attempt_state_observation"
            result = observe_attempt(provider, status, run_id)
        else:
            CHILD_PROGRESS["native_substage"] = "restart_pending_gate"
            ident = bundle["record_id"]
            require(provider._pending_clarifications == {ident})
            # A fresh native provider process must still deny an unconfirmed edit.
            require("error" in call("correct", {"record_id": ident, "expected_version": 2,
                                                 "content": "Fictional Cedar launch " + run_id + " uses five-day reviews."}))
            CHILD_PROGRESS["native_substage"] = "native_followup"
            requests = native_turn(core, provider, oauth, bundle["human_answer"], bundle)
            CHILD_PROGRESS["native_substage"] = "answer_reinitialization"
            provider.initialize("launch-answer-verification-" + run_id,
                                hermes_home=str(profile), agent_context="primary")
            CHILD_PROGRESS["native_substage"] = "final_history"
            history = provider._client.request("GET", "/v1/memories/" + ident + "/history?limit=10")
            require(history.get("record_state") == "retracted")
            versions = history.get("versions")
            require(isinstance(versions, list) and {v.get("version") for v in versions} == {1, 2, 3, 4})
            require(provider._pending_clarifications == set())
            require(provider._client.request("GET", "/v1/memories/status").get("active_records") == 0)
            result = {"later_human_answer_passed": True, "restart_pending_gate_passed": True,
                      "versioned_correction_and_retraction_passed": True,
                      "history_preserved": True, "correction_withdrawn_from_peer": True, "model_requests": requests}
    finally:
        if provider is not None:
            provider.shutdown()
        secrets.reset_secret_scope(binding)
        os.environ["HERMES_HOME"] = str(original_home)
        core["PROFILE"] = original_home
    CHILD_PROGRESS["native_substage"] = "pilot_preservation"
    require(original_profile_unchanged(core, snapshots, uid))
    return dict(result, complete=True, original_pilot_settings_and_credentials_preserved=True)


def run_child(account, sources, bundle, stage, artifact):
    code = ("import contextlib,io,json,logging,sys\n"
            "data=json.load(sys.stdin)\nns={'__name__':'reviewed_launch_candidate'}\n"
            "exec(compile(data['sources'][data['helper']],'<reviewed-launch>','exec'),ns)\n"
            "logging.disable(logging.CRITICAL)\n"
            "try:\n"
            " with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):\n"
            "  report=ns['child'](data['sources'],data['bundle'],data['stage'],data['artifact'])\n"
            " print(json.dumps(report))\n"
            "except Exception as error:\n print(json.dumps(ns['child_failure'](error)));sys.exit(1)\n")
    data = dict(sources={name: raw.decode("utf-8") for name, raw in sources.items()}, bundle=bundle,
                stage=stage, artifact=str(artifact), helper=BASE + "deployment/qualify_launch_candidate.py")
    result = subprocess.run(["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env", "-i",
        "HOME=" + str(HOME), "USER=hermes-runtime", "LOGNAME=hermes-runtime",
        "HERMES_HOME=" + str(HOME / ".hermes/profiles/enhanced-cognee-pilot"),
        "PATH=/usr/bin:/bin", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1",
        str(RELEASE / "venv/bin/python"), "-I", "-B", "-c", code],
        input=json.dumps(data).encode(), user=account.pw_uid, group=account.pw_gid, extra_groups=(),
        cwd=HOME, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=150)
    require(0 < len(result.stdout) <= 16384)
    report = json.loads(result.stdout)
    if result.returncode == 1 and isinstance(report, dict) and report.get("complete") is False:
        fixed = {"complete", "native_substage", "native_failure_category", "native_http_status"}
        require(fixed <= set(report) <= fixed | {"followup_observation", "completion_diagnostic"}
                and report["native_substage"] in CHILD_PHASES
                and report["native_failure_category"] in {
                    "dependency_missing", "timeout", "http_error", "condition_or_native_error"}
                and (report["native_http_status"] is None or type(report["native_http_status"]) is int
                     and 400 <= report["native_http_status"] <= 599))
        PROGRESS.update(native_substage=report["native_substage"],
                        native_failure_category=report["native_failure_category"],
                        native_http_status=report["native_http_status"])
        if "followup_observation" in report:
            PROGRESS["followup_observation"] = validate_followup_state(report["followup_observation"])
        if "completion_diagnostic" in report:
            PROGRESS["completion_diagnostic"] = validate_completion_diagnostic(report["completion_diagnostic"])
        raise ValueError("native_candidate_incomplete_preserve_evidence")
    require(result.returncode == 0)
    require(isinstance(report, dict) and report.get("complete") is True)
    if stage == "attempt-state":
        fixed = dict(complete=True, original_pilot_settings_and_credentials_preserved=True,
                     model_called=False, memory_records_written=False, oauth_store_read=False)
        fields = {"record_id", "canonical_version", "record_retracted",
                  "pending_clarification_present", "history_versions_verified"}
        require(set(report) == set(fixed) | fields and all(report[k] is v for k, v in fixed.items())
                and isinstance(report["record_id"], str)
                and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", report["record_id"]) is not None
                and type(report["canonical_version"]) is int and report["canonical_version"] in {2, 3, 4}
                and type(report["history_versions_verified"]) is int
                and report["history_versions_verified"] == report["canonical_version"]
                and type(report["record_retracted"]) is bool
                and report["record_retracted"] is (report["canonical_version"] == 4)
                and type(report["pending_clarification_present"]) is bool)
        return report
    if stage == "resume-check":
        expected = dict(complete=True, pending_original_fixture_verified=True,
                        original_pilot_settings_and_credentials_preserved=True,
                        model_called=False, memory_records_written=False, oauth_store_read=False)
        require(set(report) == set(expected) | {"record_id"}
                and all(report[k] is v for k, v in expected.items())
                and isinstance(report["record_id"], str)
                and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", report["record_id"]) is not None)
        return report
    if stage == "inspect":
        expected = dict(complete=True, authenticated_status_contract_passed=True,
                        original_pilot_settings_and_credentials_preserved=True,
                        model_called=False, memory_records_written=False, oauth_store_read=False)
        require(set(report) == set(expected) and all(report[k] is v for k, v in expected.items()))
        return report
    common = {"complete", "model_requests", "original_pilot_settings_and_credentials_preserved"}
    fields = ({"record_id", "question_and_preservation_passed"} if stage == "question" else {
        "later_human_answer_passed", "restart_pending_gate_passed", "versioned_correction_and_retraction_passed",
        "history_preserved", "correction_withdrawn_from_peer"})
    require(set(report) == common | fields and type(report["model_requests"]) is int
            and 0 < report["model_requests"] <= 6)
    require(all(report[name] is True for name in common | fields if name not in {"record_id", "model_requests"}))
    return report


def main(sources, mode="qualify", resume_id=None):
    require(os.geteuid() == 0 and os.environ.get("WSL_DISTRO_NAME") == "Ubuntu-Hermes"
            and os.environ.get("SUDO_USER") == "vincentspereira")
    require(mode in {"qualify", "inspect", "resume-answer", "inspect-attempt"})
    require((mode in {"resume-answer", "inspect-attempt"} and isinstance(resume_id, str)
             and re.fullmatch(r"[a-f0-9]{24}", resume_id) is not None)
            or mode not in {"resume-answer", "inspect-attempt"} and resume_id is None)
    require(mode != "resume-answer" or resume_id not in FINISHED_RUNS)
    if mode in {"qualify", "resume-answer"}:
        PROGRESS["failure_stage"] = "terminal_preflight"
        terminal_preflight()
        PROGRESS["failure_stage"] = "operator_preflight"
    issuer = definitions(sources[BASE + "deployment/provision_pilot_access.py"], "launch_issuer")
    installer = definitions(sources[BASE + "deployment/install_pilot_provider.py"], "launch_installer")
    account = pwd.getpwnam("hermes-runtime")
    require(account.pw_uid != 0 and Path(account.pw_dir) == HOME
            and set(os.getgrouplist(account.pw_name, account.pw_gid)) == {account.pw_gid})
    for path in (Path("/usr/bin/setpriv"), RELEASE / "venv/bin/python"):
        resolved = path.resolve(strict=True)
        info = resolved.stat()
        require(info.st_uid == 0 and stat.S_ISREG(info.st_mode) and not info.st_mode & 0o6022)
        require(path == Path("/usr/bin/setpriv") or resolved.is_relative_to(RELEASE))
        directory = issuer["open_directory"](resolved.parent, {0})
        os.close(directory)
    if mode in {"inspect", "resume-answer", "inspect-attempt"}:
        PROGRESS["failure_stage"] = "protected_candidate_verification"
        directory = installer["open_directory"](installer["ARTIFACT"])
        try:
            installer["protected_directory"](directory)
            installer["verify_artifact"](directory)
        finally:
            os.close(directory)
        if mode == "resume-answer":
            return resume_answer(account, sources, installer["ARTIFACT"], issuer, resume_id)
        if mode == "inspect-attempt":
            return inspect_attempt(account, sources, installer["ARTIFACT"], issuer, resume_id)
        PROGRESS["failure_stage"] = "read_only_native_inspection"
        report = run_child(account, sources, {}, "inspect", installer["ARTIFACT"])
        print(json.dumps(dict(report, stage="read_only_launch_diagnostic",
                              candidate_artifact_verified=True, fleet_launch_approved=False)))
        return
    PROGRESS["failure_stage"] = "public_candidate_staging"
    installer["stage_artifact"](candidate_payload(sources))
    PROGRESS["candidate_staged"] = True
    artifact = installer["ARTIFACT"]
    return qualify_candidate(account, sources, artifact, issuer)


def resume_answer(account, sources, artifact, issuer, run_id):
    require(isinstance(run_id, str) and re.fullmatch(r"[a-f0-9]{24}", run_id) is not None)
    PROGRESS["resuming_explicit_test_scope"] = True
    PROGRESS["failure_stage"] = "resume_scoped_credentials"
    now = int(time.time())
    claims = dict(sub="launch_" + run_id, agent_id="launch_test", tenant="qualification",
                  project_id="launch_" + run_id, roles=["api_client"], capture_policy="selected",
                  iat=now, exp=now + 3600)
    key = issuer["load_signing_key"]()
    token = issuer["sign_claims"](claims, key)
    peer = issuer["sign_claims"](dict(claims, sub="peer_" + run_id, project_id="peer_" + run_id), key)
    del key
    bundle = dict(run_id=run_id, project=claims["project_id"], token=token, peer_token=peer)
    PROGRESS["failure_stage"] = "resume_pending_fixture"
    prior = run_child(account, sources, bundle, "resume-check", artifact)
    ident = prior["record_id"]
    PROGRESS["pending_original_fixture_verified"] = True
    PROGRESS["failure_stage"] = "resume_existing_peer_access"
    code, row = api(peer, "GET", "/v1/memories/" + ident)
    require(code == 200 and isinstance(row, dict) and row.get("id") == ident
            and type(row.get("version")) is int and row["version"] == 2
            and row.get("project_id") == claims["project_id"]
            and row.get("content") == "Fictional Cedar launch " + run_id + " uses ten-day reviews.")
    PROGRESS["existing_peer_access_verified"] = True
    PROGRESS["failure_stage"] = "human_answer"
    answer = read_human_answer(run_id, resumed=True)
    PROGRESS["human_answer_received"] = True
    bundle.update(record_id=ident, human_answer=answer)
    PROGRESS["failure_stage"] = "native_followup_after_process_restart"
    second = run_child(account, sources, bundle, "answer", artifact)
    PROGRESS["native_followup_passed"] = True
    require(api(peer, "GET", "/v1/memories/" + ident)[0] == 404)
    print(json.dumps(dict(complete=True, stage="native_candidate_resumed_human_followup",
        resumed_run_id=run_id, candidate_artifact=artifact.name,
        pending_original_fixture_verified=True, existing_peer_access_verified=True,
        prior_question_and_sharing_replayed=False, prior_machine_receipt_verified=False,
        prior_question_evidence_source="owner_report_separate_from_this_followup",
        model_requests=second["model_requests"], request_count_scope="resumed_followup_only",
        **{k: v for k, v in second.items() if k not in {"complete", "model_requests"}},
        unattended_renewal_qualified=False, current_database_restore_qualified=False,
        actual_fleet_boundaries_qualified=False, fleet_launch_approved=False), indent=2))


def inspect_attempt(account, sources, artifact, issuer, run_id):
    require(isinstance(run_id, str) and re.fullmatch(r"[a-f0-9]{24}", run_id) is not None)
    PROGRESS["failure_stage"] = "observation_scoped_credentials"
    now = int(time.time())
    claims = dict(sub="launch_" + run_id, agent_id="launch_test", tenant="qualification",
                  project_id="launch_" + run_id, roles=["api_client"], capture_policy="selected",
                  iat=now, exp=now + 3600)
    key = issuer["load_signing_key"]()
    token = issuer["sign_claims"](claims, key)
    peer = issuer["sign_claims"](dict(claims, sub="peer_" + run_id, project_id="peer_" + run_id), key)
    del key
    bundle = dict(run_id=run_id, project=claims["project_id"], token=token)
    PROGRESS["failure_stage"] = "read_only_attempt_observation"
    result = run_child(account, sources, bundle, "attempt-state", artifact)
    code, _ = api(peer, "GET", "/v1/memories/" + result["record_id"])
    require(type(code) is int and code in {200, 404})
    phase = ("unchanged_pending" if result["canonical_version"] == 2 and result["pending_clarification_present"]
             else "corrected_not_retracted" if result["canonical_version"] == 3
             else "retracted_with_history" if result["canonical_version"] == 4
             else "state_needs_review")
    print(json.dumps(dict({k: v for k, v in result.items() if k != "record_id"},
        stage="read_only_existing_attempt", observed_run_id=run_id, observed_phase=phase,
        peer_http_status=code, ordinary_credentials_issued=2, credentials_persisted=False,
        model_failure_cause_established=False, native_followup_qualified=False,
        automatic_retry=False, fleet_launch_approved=False), indent=2))


def qualify_candidate(account, sources, artifact, issuer):
    run_id = uuid.uuid4().hex[:24]
    require(run_id not in FINISHED_RUNS)
    PROGRESS["new_test_run_id"] = run_id
    now = int(time.time())
    key = issuer["load_signing_key"]()
    claims = {"sub": "launch_" + run_id, "agent_id": "launch_test", "tenant": "qualification",
              "project_id": "launch_" + run_id, "roles": ["api_client"], "capture_policy": "selected",
              "iat": now, "exp": now + 3600}
    token = issuer["sign_claims"](claims, key)
    peer_project = "peer_" + run_id
    peer = issuer["sign_claims"](dict(claims, sub="peer_" + run_id, project_id=peer_project), key)
    reviewer = issuer["sign_claims"](dict(claims, sub="reviewer_" + run_id, roles=["memory_reviewer"]), key)
    expired = issuer["sign_claims"](dict(claims, iat=now - 7200, exp=now - 3600), key)
    del key
    parts = token.split(".")
    altered = parts[0] + "." + issuer["encode_segment"](dict(claims, project_id=peer_project)).decode() + "." + parts[2]
    PROGRESS["failure_stage"] = "credential_negative_controls"
    require(all(api(value, "GET", "/v1/memories/status")[0] == 401 for value in (None, expired, altered)))
    bundle = dict(run_id=run_id, token=token, peer_token=peer, project=claims["project_id"])
    PROGRESS["failure_stage"] = "native_question"
    first = run_child(account, sources, bundle, "question", artifact)
    PROGRESS["native_question_passed"] = True
    ident = first.get("record_id")
    require(isinstance(ident, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ident) is not None)
    endpoint = "/v1/memories/" + ident
    PROGRESS["failure_stage"] = "scoped_access_and_reviewed_sharing"
    require(api(peer, "GET", endpoint)[0] == 404)
    share = {"target_project": peer_project, "expected_version": 2}
    require(api(token, "POST", endpoint + "/share", share)[0] == 403)
    require(api(reviewer, "PATCH", endpoint, {"expected_version": 2, "content": "Unapproved reviewer edit"})[0] == 403)
    require(api(reviewer, "POST", endpoint + "/share", share)[0] == 200)
    require(api(peer, "GET", endpoint)[0] == 200)
    require(api(reviewer, "POST", endpoint + "/share", dict(share, revoke=True))[0] == 200)
    require(api(peer, "GET", endpoint)[0] == 404)
    require(api(reviewer, "POST", endpoint + "/share", share)[0] == 200)
    PROGRESS["reviewed_sharing_passed"] = True
    PROGRESS["failure_stage"] = "human_answer"
    answer = read_human_answer(run_id)
    PROGRESS["human_answer_received"] = True
    bundle.update(record_id=ident, human_answer=answer)
    PROGRESS["failure_stage"] = "native_followup_after_process_restart"
    second = run_child(account, sources, bundle, "answer", artifact)
    PROGRESS["native_followup_passed"] = True
    require(api(peer, "GET", endpoint)[0] == 404)
    print(json.dumps(dict(complete=True, stage="native_candidate_conversations_and_sharing",
        candidate_artifact=artifact.name, private_cross_scope_denied=True, reviewer_cannot_edit=True,
        unreviewed_sharing_denied=True, reviewed_sharing_and_revocation_passed=True,
        expired_missing_altered_credentials_denied=True, separate_native_processes=2,
        model_requests=first["model_requests"] + second["model_requests"],
        **{k: v for k, v in second.items() if k not in {"complete", "model_requests"}},
        original_pilot_provider_unchanged=True, signing_key_available_to_runtime=False,
        synthetic_profile_outside_runtime_home=True, synthetic_profile_backup_qualified=False,
        unattended_renewal_qualified=False, current_database_restore_qualified=False,
        actual_fleet_boundaries_qualified=False, fleet_launch_approved=False), indent=2))


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified operator bundle.")
