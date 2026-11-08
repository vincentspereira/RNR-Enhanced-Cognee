"""Offline pytest receipt runner. Each label/output/base directory is exclusive."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PYTHON = "/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python"
SOURCE = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
ORIGINAL = ROOT / "tests/unit/test_security_first_cutover.py"
REGRESSIONS = ROOT / "tests/unit/test_security_first_cutover_review_regressions.py"
REVIEW = OUT.parent / "review-round1/test_independent_challenges.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.geteuid() != 0, "ordinary user required"
    label, *selection = sys.argv[1:]
    assert label and all(c.isalnum() or c == "-" for c in label)
    assert selection
    run = OUT / label
    assert not run.exists()
    run.mkdir(mode=0o700)
    base = run / "sandbox"
    assert not base.exists()
    junit = run / "junit.xml"
    argv = [PYTHON, "-B", "-m", "pytest", "--confcutdir=tests/unit", "-p", "no:cacheprovider",
            "--basetemp=" + str(base), "--junitxml=" + str(junit), "-vv", "--tb=long", *selection]
    dependencies = [SOURCE, ORIGINAL, REGRESSIONS, REVIEW, Path(__file__)]
    dependencies += [p for name in ("copied-original-cases.py", "copied-review-cases.py")
                     if (p := OUT / name).exists()]
    bindings = {str(p.relative_to(ROOT)): sha(p) for p in dependencies}
    for arg in selection:
        p = ROOT / arg.split("::", 1)[0]
        if p.is_file():
            bindings[str(p.relative_to(ROOT))] = sha(p)
    started = time.time()
    with (run / "process.log").open("xb") as log:
        result = subprocess.run(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, check=False, timeout=180)
    receipt = {"argv": argv, "cwd": str(ROOT), "euid": os.geteuid(), "exit_code": result.returncode,
               "started_unix": started, "finished_unix": time.time(), "bindings_sha256": bindings,
               "obsolete_fixture_binding": os.environ.get("CUTOVER_REPAIR_OBSOLETE_FIXTURE") == "1",
               "log_sha256": sha(run / "process.log"), "junit_path": str(junit),
               "scope": "offline synthetic tests only; no qualification or live service calls"}
    if junit.exists():
        # Parse only this local pytest subprocess's newly created JUnit output.
        tree = ET.parse(junit)
        cases = []
        for case in tree.iter("testcase"):
            state = next((s for s in ["failure", "error", "skipped"] if case.find(s) is not None), "passed")
            cases.append({"classname": case.get("classname"), "name": case.get("name"), "state": state})
        receipt["cases"] = cases
        receipt["counts"] = {state: sum(c["state"] == state for c in cases)
                             for state in ["passed", "failure", "error", "skipped"]}
        receipt["total"] = len(cases)
        receipt["junit_sha256"] = sha(junit)
    with (run / "process-receipt.json").open("x", encoding="ascii") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    print(json.dumps({"receipt": str(run / "process-receipt.json"), "exit_code": result.returncode,
                      "counts": receipt.get("counts"), "total": receipt.get("total")}, ensure_ascii=True))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
