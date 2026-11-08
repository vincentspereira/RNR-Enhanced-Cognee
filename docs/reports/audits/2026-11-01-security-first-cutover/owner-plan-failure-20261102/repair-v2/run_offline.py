"""Bounded offline runner: preserve each output and refuse reused basetemp."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
PYTHON = "/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python"
label, *targets = sys.argv[1:]
if not label or "/" in label or not targets or os.geteuid() == 0:
    raise SystemExit("runner scope refused")
run = OUT / label
run.mkdir()
sandbox = run / "sandbox"
assert not os.path.lexists(sandbox)
env = dict(os.environ)
env["PYTHONDONTWRITEBYTECODE"] = "1"
assert not env.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
cmd = [PYTHON, "-B", "-m", "pytest", "--confcutdir=tests/unit", "-p", "no:cacheprovider",
       "--basetemp=" + str(sandbox), "--junitxml=" + str(run / "junit.xml"), "-vv", *targets]
bound = set(p.split("::", 1)[0] for p in targets)
bound.update(["integrations/hermes/deployment/prepare_security_first_cutover.py",
              "integrations/hermes/deployment/prepare_security_first_cutover_v2.py"])
files = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(bound) if (ROOT / p).is_file()}
receipt = {"argv": cmd, "cwd": str(ROOT), "uid": os.geteuid(), "bound_sha256": files,
           "baseline_v1": env.get("ENHANCED_CUTOVER_BASELINE_V1") == "1", "plugin_autoload": True,
           "started_ns": time.time_ns()}
(run / "started.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="ascii")
with (run / "stdout.log").open("xb") as stdout, (run / "stderr.log").open("xb") as stderr:
    result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
receipt.update(returncode=result.returncode, finished_ns=time.time_ns())
receipt["output_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in run.iterdir() if p.is_file()}
(run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="ascii")
print(json.dumps(receipt, indent=2))
print((run / "stdout.log").read_text())
print((run / "stderr.log").read_text())
sys.exit(result.returncode)
