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
                "restart_pending_gate", "native_followup", "final_history", "pilot_preservation"}
CHILD_PROGRESS = {"native_substage": "restricted_preflight"}


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
    return dict(complete=False, native_substage=CHILD_PROGRESS["native_substage"],
                native_failure_category=category,
                native_http_status=status if type(status) is int and 400 <= status <= 599 else None)


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


def read_human_answer(run_id):
    require(isinstance(run_id, str) and re.fullmatch(r"[a-f0-9]{24}", run_id) is not None)
    expected = ("For fictional Cedar launch " + run_id
        + ", use five-day reviews, then retract this invented test record while preserving history.")
    try:
        with open("/dev/tty", "r", encoding="ascii") as reader, \
                open("/dev/tty", "w", encoding="ascii", buffering=1) as writer:
            require(reader.isatty() and writer.isatty())
            writer.write("Native question, unchanged record and scoped sharing checks passed.\n"
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
            require(method == "PATCH" and path == endpoint and type(body.get("expected_version")) is int
                    and body["expected_version"] == 2)
            content = body.get("content", "")
            require(isinstance(content, str) and target["run_id"] in content
                    and re.search(r"\b(?:five|5)[ -]+day", content.casefold()))
            result = original(method, path, body)
            require(result.get("version") == 3)
            require(api(target["peer_token"], "GET", endpoint)[0] == 404)
            changes.append("correct")
            return result
        require(changes == ["correct"] and method == "POST" and path == endpoint + "/retract"
                and type(body.get("expected_version")) is int and body == {"expected_version": 3})
        result = original(method, path, body)
        require(result.get("version") == 4 and result.get("state") == "retracted")
        changes.append("retract")
        return result
    provider._client.request = guarded
    agent = run_agent.AIAgent(model=core["MODEL"], provider="openai-codex", api_mode="codex_responses",
        api_key=oauth, base_url=core["BASE_URL"], enabled_toolsets=["memory"], max_iterations=5,
        run_budget_seconds=100, fallback_model={}, credential_pool=None,
        reasoning_config={"enabled": True, "effort": "low"}, save_trajectories=False,
        quiet_mode=True, skip_background_review=True, session_id="launch-answer-" + target["run_id"],
        memory_manager=manager, cwd=str(HOME))
    try:
        requests = core["restrict_agent"](agent, {"enhanced_recall", "enhanced_get", "enhanced_status",
                                                "enhanced_correct", "enhanced_retract", "enhanced_clarify"})
        result = agent.run_conversation(prompt, conversation_history=[])
        require(isinstance(result, dict) and result.get("completed") is True
                and not result.get("failed") and not result.get("error")
                and not requests.get("rate_limited") and 0 < requests["count"] <= 6
                and changes == ["correct", "retract"])
        return requests["count"]
    finally:
        agent.close()


def child(sources, bundle, stage, artifact):
    if stage == "inspect":
        return child_inspect(sources)
    core = definitions(sources[BASE + "deployment/check_pilot_codex.py"], "launch_native_core")
    uid, snapshots = core["preflight"](True)
    CHILD_PROGRESS["native_substage"] = "pilot_snapshot"
    snapshots[".env"] = core["read_private"](".env", uid)
    original_home = core["PROFILE"]
    CHILD_PROGRESS["native_substage"] = "original_provider_verification"
    core["verify_provider"]()  # Preserve the previous pilot's exact admission.
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
        require(set(report) == {"complete", "native_substage", "native_failure_category", "native_http_status"}
                and report["native_substage"] in CHILD_PHASES
                and report["native_failure_category"] in {
                    "dependency_missing", "timeout", "http_error", "condition_or_native_error"}
                and (report["native_http_status"] is None or type(report["native_http_status"]) is int
                     and 400 <= report["native_http_status"] <= 599))
        PROGRESS.update(native_substage=report["native_substage"],
                        native_failure_category=report["native_failure_category"],
                        native_http_status=report["native_http_status"])
        raise ValueError("native_candidate_incomplete_preserve_evidence")
    require(result.returncode == 0)
    require(isinstance(report, dict) and report.get("complete") is True)
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


def main(sources, mode="qualify"):
    require(os.geteuid() == 0 and os.environ.get("WSL_DISTRO_NAME") == "Ubuntu-Hermes"
            and os.environ.get("SUDO_USER") == "vincentspereira")
    require(mode in {"qualify", "inspect"})
    if mode == "qualify":
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
    if mode == "inspect":
        PROGRESS["failure_stage"] = "protected_candidate_verification"
        directory = installer["open_directory"](installer["ARTIFACT"])
        try:
            installer["protected_directory"](directory)
            installer["verify_artifact"](directory)
        finally:
            os.close(directory)
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


def qualify_candidate(account, sources, artifact, issuer):
    run_id = uuid.uuid4().hex[:24]
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
