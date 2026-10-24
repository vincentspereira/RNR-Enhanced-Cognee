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


def require(condition):
    if not condition:
        raise ValueError("qualification_condition_not_met")


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
    core = definitions(sources[BASE + "deployment/check_pilot_codex.py"], "launch_native_core")
    uid, snapshots = core["preflight"](True)
    snapshots[".env"] = core["read_private"](".env", uid)
    original_home = core["PROFILE"]
    core["verify_provider"]()  # Preserve the previous pilot's exact admission.
    oauth = core["select_credential"](snapshots["auth.json"], credential_label="cognee-pilot-codex-secondary")
    run_id = bundle["run_id"]
    require(re.fullmatch(r"[a-f0-9]{24}", run_id) is not None)
    # The qualified whole-home backup refuses unknown provider links. Keep
    # this disposable candidate profile outside that home so qualification
    # cannot break the already-qualified unattended backup's source policy.
    # Retain this private test directory; it is not admitted everyday state.
    profile = Path("/var/tmp") / ("hermes-launch-" + run_id)
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
    sys.path.insert(0, str(RELEASE / "repo"))
    import agent.secret_scope as secrets
    from plugins import memory as loader
    require(all(Path(m.__file__).resolve().is_relative_to(RELEASE / "repo") for m in (secrets, loader)))
    binding = secrets.set_secret_scope({"ENHANCED_COGNEE_ACCESS_TOKEN": bundle["token"]}, profile_home=str(profile))
    provider = None
    try:
        require(loader.find_provider_dir("enhanced_cognee").resolve() == Path(artifact))
        provider = loader.load_memory_provider("enhanced_cognee")
        provider.initialize("launch-" + stage + "-" + run_id, hermes_home=str(profile), agent_context="primary")
        core["PROFILE"] = profile
        status = provider._client.request("GET", "/v1/memories/status")
        require(status.get("ready") is True and status.get("schema_version") == 3
                and status.get("project_id") == bundle["project"] and status.get("encryption") == "enabled")
        def call(name, args):
            return json.loads(provider.handle_tool_call("enhanced_" + name, args))
        if stage == "question":
            require(status.get("active_records") == 0 and provider._pending_clarifications == set())
            provider.on_turn_start(1, "Create an entirely invented qualification decision.")
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
            answer, _, requests = core["native_memory_turn"]("clarify", oauth, provider,
                "launch-question-" + run_id, prompt, clarification_target=ident,
                clarification_record=previous, clarification_observation=observation)
            require(isinstance(answer, str) and "?" in answer)
            require(provider._client.request("GET", "/v1/memories/" + ident) == previous)
            require(provider._client.request("GET", "/v1/memories/" + ident + "/history?limit=10") == before)
            result = {"record_id": ident, "question_and_preservation_passed": True, "model_requests": requests}
        else:
            ident = bundle["record_id"]
            require(provider._pending_clarifications == {ident})
            # A fresh native provider process must still deny an unconfirmed edit.
            require("error" in call("correct", {"record_id": ident, "expected_version": 2,
                                                 "content": "Fictional Cedar launch " + run_id + " uses five-day reviews."}))
            requests = native_turn(core, provider, oauth, bundle["human_answer"], bundle)
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
            "except Exception:\n print(json.dumps({'complete':False,'category':'native_candidate_incomplete_preserve_evidence'}));sys.exit(1)\n")
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
    require(result.returncode == 0 and 0 < len(result.stdout) <= 16384)
    report = json.loads(result.stdout)
    require(isinstance(report, dict) and report.get("complete") is True)
    common = {"complete", "model_requests", "original_pilot_settings_and_credentials_preserved"}
    fields = ({"record_id", "question_and_preservation_passed"} if stage == "question" else {
        "later_human_answer_passed", "restart_pending_gate_passed", "versioned_correction_and_retraction_passed",
        "history_preserved", "correction_withdrawn_from_peer"})
    require(set(report) == common | fields and type(report["model_requests"]) is int
            and 0 < report["model_requests"] <= 6)
    require(all(report[name] is True for name in common | fields if name not in {"record_id", "model_requests"}))
    return report


def main(sources):
    require(os.geteuid() == 0 and os.environ.get("WSL_DISTRO_NAME") == "Ubuntu-Hermes"
            and os.environ.get("SUDO_USER") == "vincentspereira")
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
    PROGRESS["failure_stage"] = "public_candidate_staging"
    installer["stage_artifact"](candidate_payload(sources))
    PROGRESS["candidate_staged"] = True
    artifact = installer["ARTIFACT"]
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
    PROGRESS["reviewed_sharing_passed"] = True
    require(api(peer, "GET", endpoint)[0] == 200)
    require(api(reviewer, "POST", endpoint + "/share", dict(share, revoke=True))[0] == 200)
    require(api(peer, "GET", endpoint)[0] == 404)
    require(api(reviewer, "POST", endpoint + "/share", share)[0] == 200)
    expected_answer = ("For fictional Cedar launch " + run_id
        + ", use five-day reviews, then retract this invented test record while preserving history.")
    PROGRESS["failure_stage"] = "human_answer"
    with open("/dev/tty", "r+", encoding="ascii", buffering=1) as terminal:
        terminal.write("Native question, unchanged record and scoped sharing checks passed.\n"
                       "For this invented test only, type the following answer to continue:\n" + expected_answer + "\n> ")
        answer = terminal.readline(1024).strip()
    require(answer == expected_answer)
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
