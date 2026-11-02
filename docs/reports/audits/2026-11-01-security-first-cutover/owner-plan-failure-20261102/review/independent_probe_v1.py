"""Bounded independent diagnostic review; all root metadata is in-memory.
No root execution, private reads, helper CLI, systemctl or service actions.
"""
import ast
import builtins
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import stat
import subprocess
import sys
import types
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
DOC = HERE.parent / "OWNER-READONLY-REFUSAL-DIAGNOSTIC.md"
HELPER = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
EXPECTED_DOC = "1bcf3e2bb780a8baa59a8f68e75354e78bed9e767a631821a0314037e18b5256"
EXPECTED_HELPER = "d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"
sha = lambda b: hashlib.sha256(b).hexdigest()
doc_bytes, helper_bytes = DOC.read_bytes(), HELPER.read_bytes()
assert sha(doc_bytes) == EXPECTED_DOC
assert sha(helper_bytes) == EXPECTED_HELPER
assert os.geteuid() != 0 and os.getegid() != 0
text = doc_bytes.decode("ascii")
blocks = re.findall(r"```bash\n(.*?)```", text, re.S)
assert len(blocks) == 1
argv = shlex.split(blocks[0])
assert argv[:6] == ["sudo", "/usr/bin/python3", "-I", "-S", "-B", "-c"] and len(argv) == 7
code = argv[-1]
tree = ast.parse(code)
compiled = compile(tree, str(DOC), "exec")
# Ordinary-user, definition-only load of the exact accepted checkout helper.
real = runpy.run_path(str(HELPER), run_name="__independent_review__")
Refusal = real["Refusal"]
canary = "INVENTED_PRIVATE_CANARY_9b4f"
unknown_name = "INVENTED_UNKNOWN_KEY_7c2a"
results = []

def record(name, category, action):
    try:
        details = action() or {}
        results.append({"case": name, "category": category, "passed": True, **details})
    except Exception as exc:
        # Review exceptions only: never dump synthetic/real input values.
        results.append({"case": name, "category": category, "passed": False,
                        "error_kind": type(exc).__name__})


def syntax():
    p = subprocess.run(["/bin/bash", "-n"], input=blocks[0], capture_output=True,
                       text=True, timeout=10)
    assert p.returncode == 0 and p.stderr == ""
    return {"bash_exit": p.returncode, "python_ast_valid": True}
record("one_literal_command_and_syntax", "syntax", syntax)


def negative():
    p = subprocess.run(argv[1:], capture_output=True, text=True, timeout=15, cwd="/")
    value = json.loads(p.stdout)
    assert p.returncode == 1 and not p.stderr
    assert value == {"read_only": True, "checks": [], "services_restarted": False,
                     "ledger_created": False, "complete": False,
                     "failed_stage": "protected_helper_identity", "error_kind": "RuntimeError"}
    return {"exit_code": p.returncode, "output": value,
            "scope": "Real ordinary UID, rejects before any protected helper access"}
record("real_ordinary_uid_negative", "ordinary_uid", negative)

# Execute exactly the formatter definition, never supplied fixture text.
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unit_structure")
scope = {"shlex": shlex}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(DOC), "exec"), scope)
formatter = scope["unit_structure"]
fixtures = {
    "credential_directives": "[Service]\nSetCredential=x:" + canary + "\nLoadCredential=x:/" + canary + "\nEnvironmentFile=/" + canary + "\n",
    "unknown_key_section_comment": "[" + unknown_name + "]\n" + unknown_name + "=" + canary + "\n# " + canary + "\n",
    "known_variable_secret_values": "[Service]\nEnvironment=HOME=" + canary + " ENHANCED_LOAD_DOTENV=" + canary + " " + unknown_name + "=" + canary + "\n",
    "malformed_quotes": "[Service]\nEnvironment=\"" + canary + "\n",
    "malformed_no_equals": "[Service]\n" + canary + "\n",
    "launch_values": "[Service]\nUser=" + canary + "\nGroup=" + canary + "\nWorkingDirectory=/" + canary + "\nExecStart=/" + canary + "\n",
    "continuation_controls": "[Service]\nEnvironment=HOME=" + canary + "\\\n" + canary + "\n\t" + unknown_name + "=" + canary + "\r\n",
    "non_ascii": b"[Service]\nEnvironment=HOME=\xff\n",
    "safe_environment": "[Service]\nEnvironment=ENHANCED_LOAD_DOTENV=0\n",
    "missing_identity": "[Service]\nWorkingDirectory=" + real["OLD"] + "\nExecStart=\n",
}
for name, raw in fixtures.items():
    def check_formatter(name=name, raw=raw):
        raw = raw.encode("ascii") if isinstance(raw, str) else raw
        value = formatter(raw, real)
        rendered = json.dumps(value, sort_keys=True)
        assert canary not in rendered and unknown_name not in rendered
        assert value["raw_values_printed"] is False
        if name == "known_variable_secret_values":
            row = value["rows"][1]
            assert row["known_variable_names"] == ["HOME", "ENHANCED_LOAD_DOTENV"]
            assert row["other_variable_count"] == 1
            assert row["matches_approved_literal_allowlist"] is False
        if name == "malformed_quotes":
            assert value["rows"][1]["environment_syntax_valid"] is False
        if name == "non_ascii":
            assert value == {"ascii": False, "raw_values_printed": False}
        if name == "safe_environment":
            assert value["rows"][1]["matches_approved_literal_allowlist"] is True
        if name == "missing_identity":
            assert value["missing_required_launch_directives"] == ["User", "Group"]
        return {"fixture_sha256": sha(raw), "sanitized_output": value}
    record("formatter_" + name, "redaction", check_formatter)

# All methods below are no-I/O test doubles. Fake root ownership never changes
# the actual process identity. Exact diagnostic code is executed unmodified.
installed = real["INSTALLED_HELPER"]
order = ["runtime_guard", "output_guard", "unit_inventory", "loaded_unit_state",
         "protected_runtime_unit_read", "protected_runtime_unit_parse",
         "snapshot_collection", "plan_validation"]
fixture_raw = ("[Service]\nUser=enhanced-cognee-api\nGroup=enhanced-cognee-api\nWorkingDirectory="
               + real["OLD"] + "\nExecStart=\nExecStart=" + real["OLD"]
               + "/runtime/bin/python -m src.memory_daemon api\n").encode("ascii")

def run_fake(*, fail_stage=None, exception=None, boundary=None, loaded_drift=False, raw=fixture_raw):
    events = []
    failure = exception if exception is not None else Refusal("unit_syntax_or_directive_refused")
    fixture_snapshot = {"fixture_only": "SNAPSHOT"}
    fixture_plan = {"fixture_only": "PLAN_PASSTHROUGH", "activated": False}
    def event(stage, value=None):
        events.append(stage)
        if stage == fail_stage:
            raise failure
        return value
    class FakePath:
        def __init__(self, value):
            self.value = str(value)
            assert self.value == installed or self.value in [str(x) for x in Path(installed).parents]
        @property
        def parents(self):
            return [FakePath(x) for x in Path(self.value).parents]
        def lstat(self):
            leaf = self.value == installed
            mode = stat.S_IFREG | 0o644 if leaf else stat.S_IFDIR | 0o755
            uid, gid, links = 0, 0, 1
            if boundary == "ancestor_symlink" and self.value == str(Path(installed).parent):
                mode = stat.S_IFLNK | 0o777
            if boundary == "ancestor_writable" and self.value == str(Path(installed).parent):
                mode = stat.S_IFDIR | 0o777
            if leaf and boundary == "leaf_symlink": mode = stat.S_IFLNK | 0o644
            if leaf and boundary == "leaf_mode": mode = stat.S_IFREG | 0o666
            if leaf and boundary == "leaf_owner": uid = 1000
            if leaf and boundary == "leaf_multilink": links = 2
            return types.SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid, st_nlink=links)
        def read_bytes(self):
            assert self.value == installed
            events.append("helper_bytes")
            return helper_bytes + b"\n" if boundary == "hash_mismatch" else helper_bytes
        def __str__(self): return self.value
    h = {key: real[key] for key in ["SECTIONS", "SAFE_ENV", "OLD", "EXPECTED_LOADED", "SOURCES", "Refusal", "digest", "canonical"]}
    h["runtime_guard"] = lambda: event("runtime_guard")
    h["check_output"] = lambda: event("output_guard")
    h["inventory_sources"] = lambda: event("unit_inventory", list(real["SOURCES"]))
    h["read_loaded"] = lambda: event("loaded_unit_state", {} if loaded_drift else dict(real["EXPECTED_LOADED"]))
    def read_protected(path):
        assert path == real["SOURCES"][2]
        return event("protected_runtime_unit_read", raw)
    def parse_unit(value, *, launch):
        assert value is raw and launch is True
        event("protected_runtime_unit_parse")
        return real["parse_unit"](value, launch=launch)
    def collect_snapshot(): return event("snapshot_collection", fixture_snapshot)
    def plan_from_snapshot(value):
        assert value is fixture_snapshot
        return event("plan_validation", fixture_plan)
    h.update(read_protected=read_protected, parse_unit=parse_unit,
             collect_snapshot=collect_snapshot, plan_from_snapshot=plan_from_snapshot)
    def fake_run_path(path, *, run_name):
        assert path == installed and run_name == "__readonly_diagnostic__"
        events.append("protected_definition_load")
        return h
    replacements = {
        "os": types.SimpleNamespace(geteuid=lambda: 0, getegid=lambda: 0),
        "pathlib": types.SimpleNamespace(Path=FakePath),
        "runpy": types.SimpleNamespace(run_path=fake_run_path),
    }
    original_import = builtins.__import__
    def controlled_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in replacements: return replacements[name]
        assert name in {"ast", "hashlib", "json", "shlex", "stat", "sys"}
        return original_import(name, globals, locals, fromlist, level)
    b = dict(vars(builtins), __import__=controlled_import)
    stdout, stderr = io.StringIO(), io.StringIO()
    exit_code = None
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            exec(compiled, {"__builtins__": b})
        except SystemExit as exc:
            exit_code = exc.code
    assert not stderr.getvalue()
    output = stdout.getvalue()
    assert canary not in output and unknown_name not in output
    value = json.loads(output)
    assert value["read_only"] is True and value["services_restarted"] is False and value["ledger_created"] is False
    return value, exit_code, events, fixture_plan


def success_route():
    value, status, events, plan = run_fake()
    assert status == 0 and value["complete"] is True
    assert events == ["helper_bytes", "protected_definition_load"] + order
    assert value["plan"] == plan
    assert value["plan_sha256"] == real["digest"](real["canonical"](plan))
    assert [x["stage"] for x in value["checks"]] == order[:4] + order[5:7]
    return {"events": events, "plan_sha256": value["plan_sha256"],
            "scope": "Synthetic plan passthrough and canonical digest only, not real plan acceptance"}
record("full_path_success_passthrough", "routing", success_route)

for stage in order:
    def fail_route(stage=stage):
        value, status, events, _ = run_fake(fail_stage=stage)
        assert status == 1 and value["complete"] is False and value["failed_stage"] == stage
        assert value["fixed_reason_code"] == "unit_syntax_or_directive_refused"
        assert events == ["helper_bytes", "protected_definition_load"] + order[:order.index(stage) + 1]
        return {"events": events, "failed_stage": value["failed_stage"]}
    record("first_failure_" + stage, "routing", fail_route)

for boundary in ["ancestor_symlink", "ancestor_writable", "leaf_symlink", "leaf_mode", "leaf_owner", "leaf_multilink", "hash_mismatch"]:
    def reject_boundary(boundary=boundary):
        value, status, events, _ = run_fake(boundary=boundary)
        assert status == 1 and value["failed_stage"] == "protected_helper_identity"
        assert "protected_definition_load" not in events and "fixed_reason_code" not in value
        return {"events": events}
    record("boundary_" + boundary, "boundary", reject_boundary)

for kind, exception, expected_code, expected_errno in [
    ("known_refusal", Refusal("unsafe_path_mode"), "unsafe_path_mode", None),
    ("unknown_refusal", Refusal(canary), None, None),
    ("ordinary_exception", ValueError(canary), None, None),
    ("os_error", PermissionError(13, canary, canary), None, 13),
]:
    def error_redaction(exception=exception, expected_code=expected_code, expected_errno=expected_errno):
        value, status, events, _ = run_fake(fail_stage="snapshot_collection", exception=exception)
        assert status == 1 and value.get("fixed_reason_code") == expected_code
        assert value.get("errno") == expected_errno and value["error_kind"] == type(exception).__name__
        return {"safe_result": value}
    record("error_redaction_" + kind, "error_redaction", error_redaction)


def drift():
    value, status, events, _ = run_fake(loaded_drift=True)
    assert status == 1 and value["failed_stage"] == "loaded_unit_state"
    assert value["fixed_reason_code"] == "inventory_or_loaded_or_candidate_drift"
    assert "protected_runtime_unit_read" not in events
    return {"events": events}
record("loaded_drift_stops_before_private_unit", "routing", drift)


def malformed_full_path():
    raw = ("[Service]\nEnvironment=\"" + canary + "\n").encode("ascii")
    value, status, events, _ = run_fake(raw=raw)
    assert status == 1 and value["failed_stage"] == "protected_runtime_unit_parse"
    assert value["fixed_reason_code"] == "unit_syntax_or_directive_refused"
    assert value["runtime_unit_structure"]["rows"][1]["environment_syntax_valid"] is False
    assert "snapshot_collection" not in events
    return {"events": events, "safe_result": value}
record("real_parser_malformed_full_path_redacted", "routing", malformed_full_path)


def runpy_semantics():
    # Use real stdlib run_path, but satisfy its only file reader with exact
    # compiled helper bytes in memory. No protected file is opened.
    with mock.patch.object(runpy, "_get_code_from_file", return_value=(compile(helper_bytes, installed, "exec"), installed)):
        h = runpy.run_path(installed, run_name="__readonly_diagnostic__")
    assert h["__file__"] == installed and h["__name__"] == "__readonly_diagnostic__"
    assert h["runtime_guard"].__globals__["__file__"] == installed
    called = []
    h["runtime_guard"](euid=lambda: 0, egid=lambda: 0, guard=lambda *a, **kw: called.append((a, kw)))
    assert called == [((installed,), {}), (("/usr/bin/python3",), {"allow_alias": True})]
    return {"helper_file": h["__file__"], "run_name": h["__name__"],
            "interpreter": sys.executable,
            "flags": {x: bool(getattr(sys.flags, x)) for x in ("isolated", "no_site", "dont_write_bytecode", "safe_path")},
            "scope": "Real runpy and runtime_guard logic, in-memory root identity/path guards only"}
record("protected_runpy_file_runtime_guard_semantics", "runtime", runpy_semantics)

# Bind before final receipt; never overwrite a parent receipt.
assert sha(DOC.read_bytes()) == EXPECTED_DOC and sha(HELPER.read_bytes()) == EXPECTED_HELPER
counts = {"executed": len(results), "passed": sum(x["passed"] for x in results),
          "failed": sum(not x["passed"] for x in results)}
counts["by_category"] = {c: sum(x["category"] == c for x in results) for c in sorted({x["category"] for x in results})}
receipt = {"passed": counts["failed"] == 0, "counts": counts, "cases": results,
           "source_hashes": {"diagnostic_sha256": EXPECTED_DOC, "helper_sha256": EXPECTED_HELPER,
                             "probe_sha256": sha(Path(__file__).read_bytes()), "embedded_python_sha256": sha(code.encode("ascii"))},
           "root_commands_executed": False, "private_file_contents_read": False,
           "service_or_network_calls": False, "production_files_modified": False,
           "owner_root_diagnostic": "PENDING; no live root/protected-unit proof"}
with (HERE / "independent-probe-receipt.json").open("x", encoding="ascii") as f:
    json.dump(receipt, f, indent=2, ensure_ascii=True)
    f.write("\n")
print(json.dumps({k: receipt[k] for k in ("passed", "counts", "source_hashes")}))
sys.exit(0 if receipt["passed"] else 1)
