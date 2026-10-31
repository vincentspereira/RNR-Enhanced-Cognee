"""Run one fresh native question/human-answer qualification; never resume.

Root verifies the public bundle; existing reviewed helper drops identity before
profile/OAuth access. No fleet admission, OAuth enrollment or automatic retry.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import stat
import sys
import tempfile

REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
BASE = Path("/opt/enhanced-cognee-memory/candidates") / REVISION
FILES = {
    "deployment/qualify_launch_candidate.py":"913bd50a69963ccc74656cce037c9b4fc0b066a7a8fe8ac6be46e29773d4caeb",
    "deployment/check_pilot_codex.py":"8aad07b7a40770eb89d687bc2b7c9c004f88b1b79b94304e179058e568b38695",
    "deployment/install_pilot_provider.py":"410cfc4145848f5bf868c0ff1f8e7a0245057c0b53f662b8cb45a41f5d450368",
    "deployment/provision_pilot_access.py":"f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "enhanced_cognee/__init__.py":"fcc7be3d7659671f14006f685c8e5419554075a1e35ca4dde687d7ae46400061",
    "enhanced_cognee/client.py":"8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "enhanced_cognee/plugin.yaml":"c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48",
}


def source_bundle():
    sources = {}
    root = Path(__file__).absolute().parents[1]
    for name, expected in FILES.items():
        fd = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd,"rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                raise ValueError("public_source_size_required")
            raw = stream.read(65537)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("reviewed_source_hash_required")
        sources["integrations/hermes/"+name] = raw
    return sources


def installed_switch():
    path = BASE / "operator-evidence/controlled-runtime-switch/summary.json"
    for item in [*reversed(path.parents),path]:
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError("protected_runtime_receipt_required")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 16384:
        raise ValueError("protected_runtime_receipt_required")
    value = json.loads(path.read_bytes())
    if (value.get("complete") is not True or value.get("source_revision") != REVISION
            or value.get("api_candidate_bound") is not True or value.get("worker_candidate_bound") is not True):
        raise ValueError("installed_candidate_required")


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise ValueError("fixed_fresh_operator_action_required")
    os.umask(0o077)
    installed_switch()
    sources = source_bundle()
    # Existing helper verifies Ubuntu-Hermes/SUDO_USER and a real terminal.
    namespace = {"__name__":"reviewed_fresh_native_qualification"}
    helper = "integrations/hermes/deployment/qualify_launch_candidate.py"
    exec(compile(sources[helper],"<verified-fresh-native>","exec"),namespace)
    evidence = Path(tempfile.mkdtemp(prefix="native-qualification-",dir=BASE / "operator-evidence"))
    for name, raw in sources.items():
        path = evidence / "public-sources" / name
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    logging.disable(logging.CRITICAL)
    captured = io.StringIO()
    result = {"complete":False,"evidence":str(evidence),"source_revision":REVISION,
              "fleet_launch_approved":False,"automatic_retry":False,"existing_test_resumed":False}
    try:
        with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
            namespace["main"](sources)  # Default qualify mode only, no resume_id.
        text = captured.getvalue()
        if len(text) > 16384:
            raise ValueError("bounded_native_receipt_required")
        receipt = json.loads(text)
        if not isinstance(receipt,dict) or receipt.get("complete") is not True or receipt.get("fleet_launch_approved") is not False:
            raise ValueError("native_receipt_required")
        result.update(complete=True,native_qualification=receipt,
                      new_test_run_id=namespace["PROGRESS"].get("new_test_run_id"))
    except BaseException:
        result["category"] = "fresh_native_qualification_incomplete_preserve_evidence"
        result["progress"] = namespace["PROGRESS"]
    with (evidence / "summary.json").open("x",encoding="ascii") as stream:
        json.dump(result,stream,ensure_ascii=True,indent=2)
        stream.write("\n")
    print(json.dumps(result,ensure_ascii=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError):
        print('{"complete":false,"category":"fresh_native_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
