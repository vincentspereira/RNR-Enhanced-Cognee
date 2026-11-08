"""Publish only the accepted ordinary-user V2 artifacts; no protected actions."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parent
OUT = BASE / "v2-publication"
BRANCH = "codex/enhanced-cognee-security-first-cutover-20261101"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def checked_file(base, relative):
    rel = Path(relative)
    assert not rel.is_absolute() and ".." not in rel.parts
    target = base / rel
    assert all(not p.is_symlink() for p in [target, *target.parents])
    assert stat.S_ISREG(target.lstat().st_mode)
    return target


def main():
    assert os.geteuid() != 0
    assert ROOT.joinpath("AGENTS.md").is_file(), str(ROOT)
    assert git("branch", "--show-current").decode().strip() == BRANCH
    assert git("rev-parse", "HEAD").decode().strip() == "72d2d90c3383cc9a83b7dfed7e3060c6ab27a8cf"
    assert git("diff", "--name-only") == b""
    assert git("diff", "--cached", "--name-only") == b""
    OUT.mkdir()
    review = BASE / "review-v2"
    repair = BASE / "repair-v2"
    verdict_bytes = (review / "independent-verdict.json").read_bytes()
    assert sha(verdict_bytes) == "cc3dc12c68fd87fc84168418d3f34d088bad9f3fa500177f9c57a09c81f8bf98"
    verdict = json.loads(verdict_bytes)
    assert verdict["passed"] is True and not verdict["security_concerns"] and not verdict["logic_errors"]
    for relative, expected in verdict["source_hashes"].items():
        assert sha(checked_file(ROOT, relative).read_bytes()) == expected
    named = json.loads((review / "named-case-inventory.json").read_bytes())
    assert len(named["canonical"]) == 202 and len(named["fresh_final"]) == 40
    executions = 0
    failures = 0
    for run in verdict["receipts"]["runs"]:
        receipt_path = review / run["receipt"]
        receipt = json.loads(receipt_path.read_bytes())
        assert receipt["exit_code"] == run["exit_code"]
        # Fixed local reviewer JUnit only; bound bytes and reject XML DTD/entities.
        xml_bytes = (receipt_path.parent / "junit.xml").read_bytes()
        assert len(xml_bytes) <= 2000000
        assert b"<!DOCTYPE" not in xml_bytes.upper() and b"<!ENTITY" not in xml_bytes.upper()
        suites = ET.fromstring(xml_bytes).findall("testsuite")
        for key in ("tests", "failures", "errors", "skipped"):
            assert sum(int(s.get(key, "0")) for s in suites) == run[key]
        executions += run["tests"]
        failures += run["failures"]
    assert executions == 247 and failures == 2
    selected = [ROOT / p for p in (
        "integrations/hermes/deployment/prepare_security_first_cutover_v2.py",
        "tests/unit/test_security_first_cutover_v2.py",
        "tests/unit/test_security_first_cutover_v2_review_regressions.py",
    )]
    for base, index_name, nested in ((repair, "evidence-index.json", True), (review, "evidence-index.json", False)):
        index = json.loads((base / index_name).read_bytes())
        entries = index["files"] if nested else index
        for relative, expected in entries.items():
            p = checked_file(base, relative)
            expected_sha = expected["sha256"] if nested else expected
            assert sha(p.read_bytes()) == expected_sha
            if nested:
                assert p.stat().st_size == expected["bytes"]
            selected.append(p)
        selected.append(base / index_name)
    parent = BASE / "parent-verification-v2-6f019fba148245e58a14b8e0641e13ed"
    selected += [parent / p for p in ("receipt.json", "stdout.log", "stderr.log", "tests.xml")]
    selected += [BASE / "cause-confirmation/OWNER-DIAGNOSTIC-AND-CONFIRMED-CAUSE.json", BASE / "V2-SOURCE-ACCEPTANCE.md", Path(__file__).resolve()]
    paths = sorted({str(p.relative_to(ROOT)) for p in selected})
    bindings = {p: sha(checked_file(ROOT, p).read_bytes()) for p in paths}
    (OUT / "selected-bindings.json").write_text(json.dumps(bindings, indent=2) + "\n")
    # Force only explicit named files, because generic *.log exclusions apply.
    subprocess.run(["git", "add", "-f", "--", *paths], cwd=ROOT, check=True, capture_output=True)
    assert set(git("diff", "--cached", "--name-only").decode().splitlines()) == set(paths)
    assert all(sha(git("show", ":" + p)) == h for p, h in bindings.items())
    maintained = [p for p in paths if p.endswith((".py", ".md"))]
    scoped = subprocess.run(["git", "diff", "--cached", "--check", "--", *maintained], cwd=ROOT, capture_output=True)
    (OUT / "maintained-whitespace.txt").write_bytes(scoped.stdout + scoped.stderr)
    assert scoped.returncode == 0
    full = subprocess.run(["git", "diff", "--cached", "--check"], cwd=ROOT, capture_output=True)
    (OUT / "full-whitespace.txt").write_bytes(full.stdout + full.stderr)
    assert full.returncode in (0, 2)
    committed = subprocess.run(["git", "commit", "-m", "[verified] Add versioned DynamicUser-safe cutover helper and owner plan"], cwd=ROOT, capture_output=True)
    (OUT / "commit-output.txt").write_bytes(committed.stdout + committed.stderr)
    assert committed.returncode == 0
    head = git("rev-parse", "HEAD").decode().strip()
    pushed = subprocess.run(["git", "push", "origin", "HEAD:refs/heads/" + BRANCH], cwd=ROOT, capture_output=True, timeout=120)
    assert pushed.returncode == 0, "Push failed; preserve local commit and inspect separately"
    remote = git("ls-remote", "--heads", "origin", "refs/heads/" + BRANCH).decode().split()[0]
    assert remote == head
    assert all(sha(git("show", "HEAD:" + p)) == h for p, h in bindings.items())
    assert git("diff", "--name-only") == b"" and git("diff", "--cached", "--name-only") == b""
    result = {"commit": head, "remote_matches": True, "branch": BRANCH,
              "selected_files": len(paths), "selected_blob_bindings_verified": True,
              "maintained_whitespace_exit": scoped.returncode,
              "full_evidence_whitespace_exit": full.returncode,
              "independent_canonical": 202, "independent_fresh": 40,
              "independent_raw_executions": executions, "retained_instrumentation_failures": failures,
              "installed_v2": False, "owner_root_plan_accepted": False,
              "services_restarted": False, "ledger_created": False, "hosted_ci_verified": False}
    (OUT / "readback.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
