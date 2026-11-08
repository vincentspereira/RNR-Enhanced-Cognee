"""Generate sanitized ordinary-user receipts. No root or application imports."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
HELPER = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
TEST = ROOT / "tests/unit/test_security_first_cutover.py"


def save(name, value):
    path = OUT / name
    with path.open("x", encoding="ascii") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


spec = importlib.util.spec_from_file_location("stage_only_helper_evidence", HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
receipts = []
for path in sorted(OUT.glob("*.json")):
    data = json.loads(path.read_bytes())
    if "command" not in data or "returncode" not in data:
        continue
    xml = path.with_suffix(".xml")
    # Only our own locally generated pytest XML is parsed, not external XML.
    suites = ET.parse(xml).getroot() if xml.exists() else None
    cases = list(suites.iter("testcase")) if suites is not None else []
    receipts.append({"receipt": str(path), "returncode": data["returncode"], "case_count": len(cases),
                     "failures": sum(case.find("failure") is not None for case in cases),
                     "errors": sum(case.find("error") is not None for case in cases),
                     "skips": sum(case.find("skipped") is not None for case in cases),
                     "identities": [case.get("classname", "") + "::" + case.get("name", "") for case in cases]})
save("test_receipts.json", receipts)
loaded = {"checked_as_uid": os.geteuid(), "protected_root_plan_executed": False}
try:
    loaded["selected_loaded_properties"] = h.read_loaded()
except Exception:
    loaded["selected_loaded_properties_check"] = "refused_or_unavailable"
static = []
for path, expected in h.SOURCE_HASHES.items():
    raw = Path(path).read_bytes()
    info = os.lstat(path)
    supported = True
    try:
        h.parse_unit(raw)
    except Exception:
        supported = False
    static.append({"path": path, "sha256": h.digest(raw), "expected_sha256": expected,
                   "matches": h.digest(raw) == expected, "supported_syntax": supported,
                   "uid": info.st_uid, "gid": info.st_gid, "mode": format(stat.S_IMODE(info.st_mode), "04o"),
                   "nlink": info.st_nlink})
loaded["readable_static_units"] = static
loaded["unreadable_source"] = h.SOURCES[2]
loaded["unreadable_source_hashed"] = False
loaded["candidate_qualification_rerun"] = False
save("readable_live_metadata.json", loaded)
hashes = {str(p): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size,
                  "lines": len(p.read_bytes().splitlines())} for p in (HELPER, TEST, OUT / "run_tdd.py", Path(__file__))}
save("artifact_hashes.json", hashes)
assert os.geteuid() != 0
result = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True)
save("scope_verification.json", {"tracked_diff_check_returncode": result.returncode,
     "tracked_changed_paths": subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).splitlines(),
     "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
     "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
     "root_execution": False, "activation": False, "credentials_read": False,
     "llm_or_api_calls": False, "qualification_rerun": False})
print(json.dumps({"artifact_hashes": hashes, "runs": [{k: v for k, v in receipt.items() if k != "identities"} for receipt in receipts],
                  "live_readable_static_units": static}, indent=2))
