"""Real pseudo-terminal I/O plus simulated native operator orchestration.

Typed input/model/store boundaries here are fixtures, not owner confirmation
or installed-host evidence. No operator keys or installed profiles are read.
"""
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def native():
    spec = importlib.util.spec_from_file_location("launch_terminal_test", "integrations/hermes/deployment/qualify_launch_candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("response", ["accepted", "accepted-resume", "mismatch", "eof", "non-ascii"])
def test_real_controlling_terminal_with_piped_bundle_input(response):
    code = '''import fcntl,importlib.util,json,os,sys,termios
os.setsid()
fd=os.open(sys.argv[1],os.O_RDWR|os.O_NOCTTY)
fcntl.ioctl(fd,termios.TIOCSCTTY,0)
os.close(fd)
assert sys.stdin.read()=="PUBLIC-BUNDLE-FIXTURE"
spec=importlib.util.spec_from_file_location("terminal_fixture",sys.argv[2])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
try:
 module.terminal_preflight()
 module.PROGRESS["failure_stage"]="human_answer"
 answer=module.read_human_answer("a"*24,resumed=sys.argv[3]=="resume")
 print(json.dumps({"complete":True,"human_answer_received":bool(answer)}))
except Exception:
 print(json.dumps({"complete":False,**module.PROGRESS}));sys.exit(1)
'''
    master, slave = pty.openpty()
    process = None
    try:
        process = subprocess.Popen([sys.executable, "-I", "-B", "-c", code, os.ttyname(slave),
            str(Path("integrations/hermes/deployment/qualify_launch_candidate.py").resolve()),
            "resume" if response == "accepted-resume" else "new"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.stdin.write(b"PUBLIC-BUNDLE-FIXTURE")
        process.stdin.close()
        process.stdin = None
        prompt = b""
        deadline = time.monotonic() + 5
        while b"\n> " not in prompt and time.monotonic() < deadline and process.poll() is None:
            if select.select([master], [], [], 0.1)[0]: prompt += os.read(master, 4096)
        assert b"type the following answer" in prompt and b"> " in prompt
        answer = ("For fictional Cedar launch " + "a" * 24
                  + ", use five-day reviews, then retract this invented test record while preserving history.\n").encode()
        sent = {"accepted": answer, "accepted-resume": answer, "mismatch": b"PRIVATE_MISMATCH_FIXTURE\n",
                "eof": b"\x04", "non-ascii": b"\xc3\xa9\n"}[response]
        os.write(master, sent)
        stdout, stderr = process.communicate(timeout=5)
        assert stderr == b"" and b"PRIVATE_" not in stdout
        report = json.loads(stdout)
        if response in {"accepted", "accepted-resume"}:
            assert process.returncode == 0 and report == dict(complete=True, human_answer_received=True)
        else:
            assert process.returncode == 1 and report["complete"] is False
            assert report["human_answer_received"] is report["native_followup_passed"] is False
            assert report["human_answer_failure"] == {
                "mismatch": "answer_mismatch_or_truncated", "eof": "terminal_end_of_input",
                "non-ascii": "terminal_unavailable_or_encoding"}[response]
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        os.close(slave)
        os.close(master)


def test_missing_terminal_stops_before_loading_issuer_or_staging_candidate():
    code = '''import importlib.util,json,os,sys
os.setsid()
spec=importlib.util.spec_from_file_location("no_terminal_fixture",sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.os.geteuid=lambda:0
module.os.environ.update(WSL_DISTRO_NAME="Ubuntu-Hermes",SUDO_USER="vincentspereira")
module.definitions=lambda *args:sys.exit("PRIVATE_ISSUER_MUST_NOT_LOAD")
try:
 module.main({})
except ValueError:
 print(json.dumps(module.PROGRESS));sys.exit(1)
'''
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code,
        str(Path("integrations/hermes/deployment/qualify_launch_candidate.py").resolve())],
        input=b"public-bundle", capture_output=True, timeout=5)
    assert result.returncode == 1 and result.stderr == b""
    report = json.loads(result.stdout)
    assert report["failure_stage"] == "terminal_preflight"
    assert report["human_answer_failure"] == "terminal_unavailable"
    assert report["candidate_staged"] is report["native_question_passed"] is False


@pytest.mark.parametrize("stop", [None, "question", "sharing", "human", "followup"])
def test_operator_flow_preserves_real_answer_boundary_and_reports_stage(native, monkeypatch, capsys, stop):
    calls = []
    shared = {"allowed": False}
    issued = []
    def sign(claims, key):
        assert key == b"synthetic-signing-fixture"
        issued.append(dict(claims))
        return "fixture." + claims["sub"] + "." + claims["roles"][0]
    issuer = dict(load_signing_key=lambda: b"synthetic-signing-fixture", sign_claims=sign,
                  encode_segment=lambda value: b"altered-claims-fixture")
    def api(token, method, path, body=None):
        if path.endswith("/status"): return 401, {}
        if method == "GET": return (200 if shared["allowed"] else 404), {}
        if method == "PATCH": return 403, {}
        assert method == "POST" and path.endswith("/share")
        if not token.endswith("memory_reviewer"): return 403, {}
        if stop == "sharing" and body.get("revoke"): return 500, {}
        shared["allowed"] = not body.get("revoke", False)
        return 200, {}
    def child(account, sources, bundle, stage, artifact):
        calls.append(stage)
        if stage == "question":
            if stop == "question": raise ValueError("synthetic question refusal")
            return dict(complete=True, record_id="fixture", model_requests=1,
                        question_and_preservation_passed=True,
                        original_pilot_settings_and_credentials_preserved=True)
        assert calls == ["question", "human", "answer"]
        assert bundle["human_answer"] == "SYNTHETIC_TYPED_ANSWER_FIXTURE" and bundle["record_id"] == "fixture"
        assert native.PROGRESS["human_answer_received"] is True
        if stop == "followup": raise ValueError("synthetic followup refusal")
        shared["allowed"] = False
        return dict(complete=True, model_requests=1, original_pilot_settings_and_credentials_preserved=True,
                    later_human_answer_passed=True, restart_pending_gate_passed=True,
                    versioned_correction_and_retraction_passed=True,
                    history_preserved=True, correction_withdrawn_from_peer=True)
    def answer(run_id):
        calls.append("human")
        assert len(run_id) == 24 and native.PROGRESS["reviewed_sharing_passed"] is True
        if stop == "human": raise ValueError("synthetic unanswered prompt")
        return "SYNTHETIC_TYPED_ANSWER_FIXTURE"
    monkeypatch.setattr(native, "api", api)
    monkeypatch.setattr(native, "run_child", child)
    monkeypatch.setattr(native, "read_human_answer", answer)
    if stop:
        with pytest.raises(ValueError): native.qualify_candidate(NS(), {}, Path("/public-candidate"), issuer)
        assert not capsys.readouterr().out
        assert native.PROGRESS["failure_stage"] == {"question": "native_question",
            "sharing": "scoped_access_and_reviewed_sharing", "human": "human_answer",
            "followup": "native_followup_after_process_restart"}[stop]
        if stop in {"question", "sharing"}: assert "human" not in calls
        if stop != "followup": assert native.PROGRESS["human_answer_received"] is False
        if stop == "sharing": assert native.PROGRESS["reviewed_sharing_passed"] is False
        assert native.PROGRESS["native_followup_passed"] is False
    else:
        native.qualify_candidate(NS(), {}, Path("/public-candidate"), issuer)
        result = json.loads(capsys.readouterr().out)
        assert result["complete"] is True and result["model_requests"] == 2
        assert result["reviewed_sharing_and_revocation_passed"] is result["history_preserved"] is True
        assert result["fleet_launch_approved"] is result["unattended_renewal_qualified"] is False
        assert result["current_database_restore_qualified"] is result["actual_fleet_boundaries_qualified"] is False
    assert len(issued) == 4 and all(c["tenant"] == "qualification" for c in issued)
