"""Bounded offline pytest evidence recorder; never runs the privileged CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
label = sys.argv[1]
if not label.replace("-", "").isalnum():
    raise SystemExit("invalid evidence label")
command = ["/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python",
           "-B", "-m", "pytest", "--confcutdir=tests/unit", "-p", "no:cacheprovider",
           "tests/unit/test_security_first_cutover.py", "-vv", "--tb=short",
           "--junitxml=" + str(OUT / (label + ".xml")),
           "--basetemp=" + str(OUT / (label + "-sandbox"))] + sys.argv[2:]
for suffix in (".log", ".json", ".xml", "-sandbox"):
    if (OUT / (label + suffix)).exists():
        raise SystemExit("evidence already exists")
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(OUT / (label + ".log")).write_bytes(result.stdout)
(OUT / (label + ".json")).write_text(json.dumps({"command": command, "cwd": str(ROOT), "returncode": result.returncode}, indent=2) + "\n")
print("\n".join(result.stdout.decode("utf-8", "replace").splitlines()[-4:]))
print("EVIDENCE", OUT / (label + ".json"))
raise SystemExit(result.returncode)
