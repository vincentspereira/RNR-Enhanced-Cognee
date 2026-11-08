"""Parent verification of repaired offline inputs and owner-command syntax only."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "docs/reports/audits/2026-11-01-security-first-cutover"
OUT = BASE / "parent"
REPAIR = BASE / "repair-round1"
PYTHON = "/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python"


def save_new(path, data):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(data)


hashes = json.loads((REPAIR / "final-source-test-hashes.json").read_text())
for name, expected in hashes.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name

# Correct only the replay-output location and the fixed copied-body input path.
wrappers = []
for kind in ("original", "review"):
    source = REPAIR / ("test_current_" + kind + "_cases.py")
    text = source.read_text("ascii")
    old = '_copy = _Path(__file__).resolve().parent / "copied-' + kind + '-cases.py"'
    assert text.count(old) == 1
    text = text.replace(old, "_copy = _Path(" + repr(str(REPAIR / ("copied-" + kind + "-cases.py"))) + ")")
    destination = OUT / ("test_parent_current_" + kind + "_cases.py")
    save_new(destination, text)
    wrappers.append(destination)

owner_path = BASE / "OWNER-NEXT-PLAN.md"
text = owner_path.read_text("ascii")
fence = chr(96) * 3
blocks = re.findall(fence + r"bash\n(.*?)" + fence, text, re.S)
assert len(blocks) == 2
for block in blocks:
    syntax = subprocess.run(["/bin/bash", "-n"], input=block, text=True, capture_output=True, timeout=10)
    assert syntax.returncode == 0, syntax.stderr
embedded = re.findall(r"-c '\n(.*?)'", blocks[0], re.S)
assert len(embedded) == 3
for code in embedded:
    ast.parse(code)
helper = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
helper_hash = hashlib.sha256(helper.read_bytes()).hexdigest()
assert helper_hash == "d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"
assert blocks[0].count('expected="' + helper_hash + '"') == 1
assert "--prepare" not in "\n".join(blocks)
negative = subprocess.run(["/usr/bin/python3", "-I", "-S", "-B", str(helper), "--plan"],
                          cwd="/", capture_output=True, text=True, timeout=10)
assert negative.returncode == 1 and negative.stdout == "" and negative.stderr == "ERR stage_only_refused\n"
syntax_receipt = {
    "bash_blocks_valid": 2, "python_blocks_parsed": 3,
    "bootstrap_source_hash_matches": True,
    "ordinary_uid_plan_refused": True,
    "actual_root_plan": "OWNER_PENDING",
    "commands_executed_as_root": False,
    "owner_instructions_sha256": hashlib.sha256(owner_path.read_bytes()).hexdigest(),
}
save_new(OUT / "round2-owner-command-validation.json", json.dumps(syntax_receipt, indent=2) + "\n")

command = [PYTHON, "-B", "-m", "pytest", "--confcutdir=tests/unit", "-p", "no:cacheprovider",
           "--basetemp=" + str(OUT / "round2-parent-sandbox"),
           "--junitxml=" + str(OUT / "round2-parent-regressions.xml"), "-q"]
command.extend(str(path) for path in wrappers)
command.append("tests/unit/test_security_first_cutover_review_regressions.py")
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=180)
save_new(OUT / "round2-parent-regressions.log", result.stdout)
# Parse only the JUnit file emitted by our just-completed local pytest child;
# this verification runner has no externally supplied XML input interface.
tree = ET.parse(OUT / "round2-parent-regressions.xml")
suites = list(tree.getroot().iter("testsuite"))
counts = {key: sum(int(node.get(key, "0")) for node in suites)
          for key in ("tests", "failures", "errors", "skipped")}
cases = [(case.get("classname"), case.get("name")) for case in tree.getroot().iter("testcase")]
assert len(cases) == len(set(cases))
receipt = {"command": command, "returncode": result.returncode, "counts": counts,
           "distinct_historical_logical_cases": 173, "additional_replay_implementations": 3,
           "helper_sha256": helper_hash, "cases": cases,
           "wrapper_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in wrappers}}
save_new(OUT / "round2-parent-regressions.json", json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"returncode": result.returncode, "counts": counts, "owner_command_validation": syntax_receipt}, indent=2))
assert result.returncode == 0 and counts == {"tests": 176, "failures": 0, "errors": 0, "skipped": 0}
manifest = dict(hashes)
manifest[str(owner_path.relative_to(ROOT))] = hashlib.sha256(owner_path.read_bytes()).hexdigest()
save_new(OUT / "round2-review-manifest.json", json.dumps({"base": "41e4de7a5db99970a7629ef3f274138eef3031e8", "files": manifest}, indent=2) + "\n")
