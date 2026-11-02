"""Offline verification only: never execute any sudo/bootstrap root portion."""
import ast
from collections import Counter
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
V1 = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
V2 = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover_v2.py"
T1 = ROOT / "tests/unit/test_security_first_cutover.py"
T2 = ROOT / "tests/unit/test_security_first_cutover_v2.py"
TR1 = ROOT / "tests/unit/test_security_first_cutover_review_regressions.py"
TR2 = ROOT / "tests/unit/test_security_first_cutover_v2_review_regressions.py"
OWNER = OUT / "OWNER-V2-PLAN.md"
assert os.geteuid() != 0

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    with (OUT / name).open("x", encoding="ascii") as f:
        json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")

def functions(path):
    text = path.read_text(encoding="ascii")
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

manifest = json.loads((OUT / "baseline-manifest.json").read_text())
assert all(sha(ROOT / p) == pin for p, pin in manifest.items())
f1, f2 = functions(V1), functions(V2)
changed = [k for k in f1 if f1[k] != f2[k]]
assert changed == ["parse_unit", "plan_from_snapshot"]
assert set(f1) == set(f2)
t1, t2 = functions(T1), functions(T2)
assert all(t1[k] == t2[k] for k in t1 if k.startswith("test_"))
assert all(t1[k] == t2[k] for k in t1 if k != "snapshot")
assert t2["snapshot"] == t1["snapshot"].replace("[Service]\\nLoadCredential=api.json", "[Service]\\nDynamicUser=yes\\nLoadCredential=api.json")
# The mapped wrapper must change its imported challenge HELPER, not only its PIN.
reg = TR2.read_text(encoding="ascii")
assert "text = text.replace(old_helper," in reg
assert "prepare_security_first_cutover_v2.py" in reg
assert functions(TR1)["test_L01_exact_installed_module_mapping_is_readable"] == functions(TR2)["test_L01_exact_installed_module_mapping_is_readable"]
for k, v in functions(TR1).items():
    if k.startswith("test_"): assert functions(TR2)[k] == v
spec = importlib.util.spec_from_file_location("verified_v2_binding", V2)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
assert Path(h.__file__) == V2
# Compare pins and loaded policy by importing ONLY the standalone stdlib V1 helper.
spec1 = importlib.util.spec_from_file_location("verified_v1_binding", V1)
old = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(old)
for key in ("SOURCE_HASHES", "MODULE_HASHES", "EXPECTED_LOADED", "SAFE_ENV", "LAUNCH_KEYS", "SOURCES"):
    assert getattr(h, key) == getattr(old, key)
assert h.proposed_dropin() == old.proposed_dropin()
assert h.BUNDLE == old.BUNDLE + "-v2"
assert h.INSTALLED_HELPER == "/opt/enhanced-cognee-memory/security-first-helper-v2/prepare_security_first_cutover_v2.py"
assert "63764" not in V2.read_text()
newtext = V2.read_text()
assert "prepare_security_first_cutover.py" not in newtext
imports = [n for n in ast.walk(ast.parse(newtext)) if isinstance(n, (ast.Import, ast.ImportFrom))]
assert {alias.name for n in imports if isinstance(n, ast.Import) for alias in n.names} <= {"hashlib", "json", "re", "shlex", "os", "stat", "subprocess", "sys"}
assert [n.module for n in imports if isinstance(n, ast.ImportFrom)] == ["pathlib"]
with (OUT / "minimal-v1-to-v2.diff").open("x", encoding="ascii") as f:
    f.writelines(difflib.unified_diff(V1.read_text().splitlines(True), newtext.splitlines(True),
                                   fromfile=str(V1.relative_to(ROOT)), tofile=str(V2.relative_to(ROOT))))

text = OWNER.read_text(encoding="ascii")
blocks = re.findall(r"```bash\n(.*?)```", text, re.S)
assert len(blocks) == 2
assert "--prepare" not in text
assert text.count("expected=\"" + sha(V2) + "\"") == 1
owner_validation = []
for index, block in enumerate(blocks, 1):
    assert (OUT / ("owner-block-" + str(index) + ".sh")).read_text() == block
    result = subprocess.run(["/usr/bin/bash", "-n"], input=block.encode("ascii"), capture_output=True, check=False)
    assert result.returncode == 0
    owner_validation.append({"block": index, "bash_n_exit": result.returncode,
                             "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})
tokens = shlex.split(blocks[0])
scripts = [tokens[i+1] for i, token in enumerate(tokens) if token == "-c"]
assert len(scripts) == 3
for script in scripts:
    compile(ast.parse(script), "<owner-embedded>", "exec")
# Root portions are AST-checked ONLY. No sudo command is ever executed here.
original = ROOT / "docs/reports/audits/2026-11-01-security-first-cutover/OWNER-NEXT-PLAN.md"
oldblocks = re.findall(r"```bash\n(.*?)```", original.read_text(), re.S)
assert blocks[0] == oldblocks[0].replace(sha(V1), sha(V2)).replace("security-first-helper", "security-first-helper-v2").replace("prepare_security_first_cutover.py", "prepare_security_first_cutover_v2.py")
assert blocks[1] == oldblocks[1].replace("sudo /usr/bin/python3", "/usr/bin/sudo /usr/bin/python3").replace("security-first-helper", "security-first-helper-v2").replace("prepare_security_first_cutover.py", "prepare_security_first_cutover_v2.py")
reader = scripts[1]
reader_results = []
for label, prefix, value, expected_rc in [
    ("valid-source", "", sha(V2), 0),
    ("wrong-hash", "", "0" * 64, 1),
    ("short-hash", "", "a" * 63, 1),
    ("long-hash", "", "a" * 65, 1),
    ("uppercase-hash", "", sha(V2).upper(), 1),
    ("mocked-root-reader", "import os; os.geteuid=lambda:0\n", sha(V2), 1)]:
    result = subprocess.run(["/usr/bin/python3", "-I", "-S", "-B", "-c", prefix + reader,
                             str(V2), value], capture_output=True, check=False)
    assert result.returncode == expected_rc
    assert result.stdout == (V2.read_bytes() if expected_rc == 0 else b"")
    reader_results.append({"case": label, "exit": result.returncode,
                           "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                           "stdout_bytes": len(result.stdout), "stderr": result.stderr.decode("ascii")})

# Enumerate actual JUnit case IDs, with exact historical -> V2 mappings.
def cases(run):
    receipt = json.loads((OUT / run / "receipt.json").read_text())
    tree = ET.parse(OUT / run / "junit.xml")
    rows = []
    for tc in tree.findall(".//testcase"):
        status = "passed"
        for tag in ("failure", "error", "skipped"):
            if tc.find(tag) is not None: status = tag
        rows.append({"id": tc.attrib["classname"].replace(".", "/") + ".py::" + tc.attrib["name"], "status": status})
    assert len({r["id"] for r in rows}) == len(rows)
    return receipt, rows
historical_receipt, historical = cases("historical-v1")
new_receipt, new = cases("canonical-v2")
assert historical_receipt["returncode"] == new_receipt["returncode"] == 0
assert len(historical) == 126 and len(new) == 202
assert all(r["status"] == "passed" for r in historical + new)
new_ids = {r["id"] for r in new}
mapping = []
for row in historical:
    old_id = row["id"]
    new_id = old_id.replace("test_security_first_cutover_review_regressions.py", "test_security_first_cutover_v2_review_regressions.py").replace("test_security_first_cutover.py", "test_security_first_cutover_v2.py")
    assert new_id in new_ids
    mapping.append({"historical_v1_node_id": old_id, "canonical_v2_node_id": new_id})
mapped = {r["canonical_v2_node_id"] for r in mapping}
added = [r for r in new if r["id"] not in mapped]
assert len(added) == 76
save("test-inventory-and-mapping.json", {"historical_v1": historical, "canonical_v2": new,
    "replay_mapping": mapping, "new_v2_cases": added, "counts": {"historical_v1":126,
    "canonical_v2":202, "v2_historical_replay":126, "v2_added_cases":76},
    "fixture_change": "Only NEW canonical snapshot base adds DynamicUser=yes. All original test function bodies and parameterizations unchanged; no deletion/deselection/xfail.",
    "mapped_challenge_change": "Only challenge PIN, output, and actual HELPER binding rebound; original challenge bytes and all three assertion bodies unchanged."})
# New executable/authored files only. Never sanitize historical/raw log bytes.
paths = [V2, T2, TR2, OWNER, OUT / "run_offline.py", OUT / "verify_v2_artifacts.py", OUT / "owner-block-1.sh", OUT / "owner-block-2.sh"]
whitespace = {str(p.relative_to(ROOT)): [i for i,line in enumerate(p.read_text(encoding="ascii").splitlines(),1)
                if line.rstrip() != line] for p in paths}
assert not any(whitespace.values())
# Fixed canaries and credential-name policy strings are test data, not credentials.
added_lines = [line[1:] for line in difflib.unified_diff(V1.read_text().splitlines(), newtext.splitlines())
               if line.startswith("+") and not line.startswith("+++")]
scan_patterns = {"shell_true": r"shell\s*=\s*True", "os_system": r"os\.system\(",
                 "pickle": r"pickle\.loads?\(", "eval_exec": r"\b(?:eval|exec)\("}
scan = {k:[line for line in added_lines if re.search(pattern,line)] for k,pattern in scan_patterns.items()}
assert not any(scan.values())
result = {"uid":os.geteuid(), "source_sha256":sha(V2), "owner_sha256":sha(OWNER),
    "v1_sha256":sha(V1), "preserved_originals":manifest, "changed_source_functions":changed,
    "unchanged_source_functions":[k for k in f1 if k not in changed],
    "unchanged_historical_test_functions":len([k for k in t1 if k.startswith("test_")]),
    "actual_imported_v2_path":h.__file__, "source_and_owner_ast":"passed", "owner_bash_n":owner_validation,
    "ordinary_reader_probes":reader_results, "sudo_portions_executed":False,
    "static_added_source_scan":scan, "scoped_whitespace":whitespace,
    "inventory_counts":{"historical_v1":126,"canonical_v2":202,"v2_replays":126,"new_v2_cases":76},
    "fresh_independent_review":"pending_parent", "runtime_acceptance":False}
save("artifact-verification.json",result)
print(json.dumps(result, indent=2, sort_keys=True))
