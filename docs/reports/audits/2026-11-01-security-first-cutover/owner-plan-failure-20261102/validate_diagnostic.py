"""Validate only syntax, redaction and ordinary-user refusal; never sudo."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DOC = OUT / "OWNER-READONLY-REFUSAL-DIAGNOSTIC.md"
text = DOC.read_text("ascii")
fence = chr(96) * 3
blocks = re.findall(fence + r"bash\n(.*?)" + fence, text, re.S)
assert len(blocks) == 1
shell = subprocess.run(["/bin/bash", "-n"], input=blocks[0], text=True, capture_output=True)
assert shell.returncode == 0
code = blocks[0].split("-c '\n", 1)[1].rsplit("'", 1)[0]
tree = ast.parse(code)
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "unit_structure")
scope: dict[str, object] = {"shlex": shlex}
# Execute only our local formatter definition against invented string fixtures.
# This is not external XML/code input, protected helper execution or root code.
exec(compile(ast.Module(body=[function], type_ignores=[]), str(DOC), "exec"), scope)
p = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
spec = importlib.util.spec_from_file_location("formatter_test_helper", p)
assert spec is not None and spec.loader is not None
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
h = vars(helper)
formatter = scope["unit_structure"]
assert callable(formatter)
canary = "INVENTED_PRIVATE_VALUE_MUST_NOT_APPEAR"
examples = [
    ("missing_identity", b"[Service]\nWorkingDirectory=" + h["OLD"].encode() + b"\nExecStart=\n"),
    ("secret_environment", ("[Service]\nEnvironment=ENHANCED_LLM_API_KEY=" + canary + "\n").encode()),
    ("inline_credential", ("[Service]\nSetCredential=llm.json:" + canary + "\n").encode()),
    ("comment", ("# " + canary + "\n[Service]\nUser=enhanced-cognee-api\n").encode()),
    ("malformed_quote", ("[Service]\nEnvironment=\"" + canary + "\n").encode()),
    ("unknown_directive_and_section", ("[" + canary + "]\n" + canary + "=" + canary + "\n").encode()),
    ("non_ascii", b"[Service]\nEnvironment=\xff\n"),
    ("known_environment", b"[Service]\nEnvironment=ENHANCED_LOAD_DOTENV=0\n"),
]
rows = []
for name, raw in examples:
    value = formatter(raw, h)
    assert isinstance(value, dict)
    assert canary not in json.dumps(value)
    assert value["raw_values_printed"] is False
    if name == "missing_identity":
        assert value["missing_required_launch_directives"] == ["User", "Group"]
    if name == "known_environment":
        assert value["rows"][1]["matches_approved_literal_allowlist"] is True
    rows.append({"case": name, "passed": True})
negative = subprocess.run(["/usr/bin/python3", "-I", "-S", "-B", "-c", code],
                          capture_output=True, text=True, cwd="/", timeout=15)
assert negative.returncode == 1 and negative.stderr == ""
result = json.loads(negative.stdout)
assert result["complete"] is False and result["failed_stage"] == "protected_helper_identity"
receipt = {"bash_syntax_exit": 0, "python_ast_valid": True, "formatter_cases": rows,
           "ordinary_uid_negative_exit": negative.returncode, "root_commands_executed": False,
           "real_root_diagnostic": "OWNER_PENDING", "scope": "Syntax and formatter-only probes, not root-plan acceptance"}
path = OUT / "parent-diagnostic-validation.json"
with path.open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps(receipt, indent=2))
