"""Offline source-fragment probes. No application/server/dependency imports."""
import ast
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types
from urllib.parse import urlsplit

ROOT = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101')
OUT = Path(__file__).resolve().parent
os.environ.clear()
results = []


def case(name, check):
    check()
    results.append({"case": name, "passed": True})


def load_stdlib_source(relative, source=None):
    source = source if source is not None else (ROOT / relative).read_text()
    namespace = {"__name__": "offline_fragment", "__file__": str(ROOT / relative)}
    exec(compile(source, relative, "exec"), namespace)
    return namespace


def require(condition):
    if not condition:
        raise AssertionError("Offline assertion failed")


def refused(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("Expected refusal")


# Only this pure-stdlib launcher is executed as a whole; its __main__ is inactive.
daemon = load_stdlib_source("src/memory_daemon.py")
credentials = OUT / "invented_credentials"
credentials.mkdir(mode=0o700, exist_ok=False)
api_path = credentials / "api.json"
api_settings = {
    "ENHANCED_MEMORY_DATABASE_URL": "postgresql://offline.invalid/invented",
    "ENCRYPTION_MASTER_KEY": "invented-not-a-real-encryption-key",
    "ENHANCED_EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
    "ENHANCED_MODEL_CACHE": "/invented/model-cache",
    "ENHANCED_INDEX_CONFIG": "/invented/index.json",
    "ENHANCED_INDEX_KEY": "invented-not-a-real-index-key",
}
api_path.write_text(json.dumps(api_settings))
api_path.chmod(0o600)
os.environ.update({
    "ENHANCED_LLM_BASE_URL": "https://inherited.invalid/v1",
    "ENHANCED_LLM_API_KEY": "invented-not-a-real-provider-key",
    "ENHANCED_LLM_MODEL": "invented-inherited-model",
    "ENHANCED_LLM_BUDGET_DB": "/invented/ledger.sqlite3",
    "OPENAI_API_KEY": "invented-not-a-real-provider-key",
    "LLM_PROVIDER": "invented-provider", "LLM_MODEL": "invented-model",
    "CREDENTIALS_DIRECTORY": str(credentials), "ENHANCED_LOAD_DOTENV": "1",
    "PYTHONPATH": "/invented/untrusted", "ENHANCED_ENV": "development",
})
clean = daemon["credential_environment"]("api", str(credentials))
case("daemon_strips_inherited_model_routes_and_credential_directory", lambda: require(
    not any(k in clean for k in os.environ if k not in {"ENHANCED_LOAD_DOTENV", "ENHANCED_ENV"})))
case("daemon_preserves_core_settings_and_forces_production_offline_dotenv_off", lambda: require(
    all(clean[k] == v for k, v in api_settings.items())
    and clean["ENHANCED_LOAD_DOTENV"] == "0" and clean["ENHANCED_ENV"] == "production"
    and clean["HF_HUB_OFFLINE"] == "1" and clean["COGNEE_TELEMETRY_ENABLED"] == "0"))


def rejects_api_fallback_fields():
    for field in ("ENHANCED_LLM_BASE_URL", "CREDENTIALS_DIRECTORY", "ENHANCED_LOAD_DOTENV", "OPENAI_API_KEY"):
        api_path.write_text(json.dumps(dict(api_settings, **{field: "invented"})))
        refused(lambda: daemon["credential_environment"]("api", str(credentials)))
    api_path.write_text(json.dumps(api_settings))


case("api_json_rejects_four_model_or_fallback_injection_fields", rejects_api_fallback_fields)

# Compile only route selectors and the exception class, with explicit stdlib globals.
llm_tree = ast.parse((ROOT / "src/llm_summarize.py").read_text())
names = {"LlmUnavailable", "load_route_env", "load_route", "detect_language"}
selected = ast.Module(body=[n for n in llm_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names], type_ignores=[])
route_ns = {"os": os, "Path": Path, "json": json, "urlsplit": urlsplit, "DEFAULT_DAILY_TOKEN_CAP": 50000}
# detect_language has a table constant; extract the actual literal without any imports.
for node in llm_tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_SCRIPTS" for t in node.targets):
        route_ns["_SCRIPTS"] = ast.literal_eval(node.value)
exec(compile(selected, "src/llm_summarize.py", "exec"), route_ns)
os.environ.clear()
os.environ.update(clean)
case("child_route_composition_is_none_without_llm_json", lambda: require(
    (route_ns["load_route_env"]() or route_ns["load_route"](os.environ.get("CREDENTIALS_DIRECTORY"))) is None))
llm_path = credentials / "llm.json"
llm_path.write_text(json.dumps({"base_url": "https://offline.invalid/v1", "api_key": "invented-not-a-real-provider-key", "model": "invented-offline-model"}))
llm_path.chmod(0o600)
case("direct_api_fallback_is_real_when_given_a_credential_directory", lambda: require(
    route_ns["load_route"](str(credentials))["model"] == "invented-offline-model"))
with_llm = daemon["credential_environment"]("api", str(credentials))
case("llm_credential_positive_control_enables_route_and_ledger_setting", lambda: require(
    with_llm["ENHANCED_LLM_MODEL"] == "invented-offline-model"
    and with_llm["ENHANCED_LLM_BUDGET_DB"] == "/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3"))
# Keep the positive-control fixture; subsequent child environment remains the no-LLM environment.
case("language_detection_is_script_only", lambda: require(
    route_ns["detect_language"]("Invented plain text")["method"] == "script_heuristic"))

api_tree = ast.parse((ROOT / "src/memory_api.py").read_text())
create_app = next(n for n in api_tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_app")
inner = {n.name: n for n in create_app.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


class JSONResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


class StoreDouble:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        async def invoke(*args, **kwargs):
            self.calls.append(name)
            return {"offline_delegated": name}
        return invoke


store_double = StoreDouble()
app_double = types.SimpleNamespace(state=types.SimpleNamespace(llm_route=None, llm_budget=None))
llm_double = types.ModuleType("src.llm_summarize")
llm_double.LlmUnavailable = route_ns["LlmUnavailable"]
package_double = types.ModuleType("src")
package_double.llm_summarize = llm_double
budget_double = types.ModuleType("src.llm_budget")
budget_double.BudgetUnavailable = type("BudgetUnavailable", (ValueError,), {})
sys.modules["src"] = package_double
sys.modules["src.llm_summarize"] = llm_double
sys.modules["src.llm_budget"] = budget_double
selected_names = {"_llm", "_project", "summarize", "consolidation", "translate", "summarization_status", "invalid", "remember", "recall", "get", "correct", "retract", "connections"}
# Decorators and annotations are framework wiring, intentionally not executed.
nodes = []
for name in sorted(selected_names):
    node = inner[name]
    node.decorator_list = []
    node.returns = None
    for arg in node.args.args + node.args.kwonlyargs:
        arg.annotation = None
    nodes.append(node)
ns = {"app": app_double, "store": lambda: store_double, "scope": lambda request: types.SimpleNamespace(tenant="invented", project="invented", subject="invented"), "JSONResponse": JSONResponse}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "src/memory_api.py", "exec"), ns)


def endpoint_guards():
    for name in ("summarize", "consolidation", "translate"):
        try:
            asyncio.run(ns[name](object(), object()))
        except route_ns["LlmUnavailable"] as exc:
            response = asyncio.run(ns["invalid"](None, exc))
            require(response.status_code == 422)
            require(response.content == {"detail": "The model route is not configured for this service"})
        else:
            raise AssertionError("Model endpoint did not refuse")
    require(store_double.calls == [])


case("three_model_endpoint_bodies_refuse_before_store_access_with_422_handler", endpoint_guards)
case("analysis_status_returns_unconfigured_nulls_without_budget", lambda: require(
    asyncio.run(ns["summarization_status"](object())) == {"configured": False, "model": None, "daily_token_cap": None, "used_today": None, "project_id": "invented"}))


def core_delegation():
    body = types.SimpleNamespace(model_dump=lambda: {})
    for name in ("remember", "recall", "connections"):
        asyncio.run(ns[name](body, object()))
    asyncio.run(ns["get"]("invented-id", object()))
    asyncio.run(ns["correct"]("invented-id", body, object()))
    asyncio.run(ns["retract"]("invented-id", body, object()))
    require(store_double.calls == ["remember", "recall", "connections", "get", "correct", "correct"])


case("six_core_endpoint_bodies_delegate_without_optional_route", core_delegation)

mcp_file = "integrations/hermes/enhanced_cognee_mcp/server.py"
mcp = load_stdlib_source(mcp_file)
old_ref = subprocess.run(["git", "rev-parse", "c14f595c^"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
old_text = subprocess.run(["git", "show", old_ref + ":" + mcp_file], cwd=ROOT, capture_output=True, text=True, check=True).stdout
old_mcp = load_stdlib_source(mcp_file, old_text)


def wire_capture(module):
    calls = []
    def api(method, path, token, body=None):
        calls.append({"method": method, "path": path, "body": body})
        return 422, {"detail": "The model route is not configured for this service"}
    module["api"] = api
    return module["handlers"]("invented-offline-token"), calls


new_table, new_calls = wire_capture(mcp)
old_table, old_calls = wire_capture(old_mcp)


def contract_capture():
    for table in (new_table, old_table):
        table["get_related"][1]({"query": "invented entity"})
        args = {"record_ids": ["invented-1"]} if table is new_table else {}
        table["summarize_memories"][1](args)
        args = {"record_ids": ["invented-1", "invented-2"]} if table is new_table else {}
        table["find_consolidation_candidates"][1](args)
    require(new_calls[0]["body"] == {"entity": "invented entity"})
    require(old_calls[0]["body"] == {"query": "invented entity"})
    require(new_calls[1]["body"] == {"record_ids": ["invented-1"]})
    require(old_calls[1]["body"] == {"limit": 20})
    require(new_calls[2]["body"] == {"record_ids": ["invented-1", "invented-2"]})
    require(old_calls[2]["body"] == {"limit": 20})


case("current_vs_pre_hardening_mcp_wire_contracts_differ_as_expected", contract_capture)


def rpc(module, table):
    stdin, stdout = sys.stdin, sys.stdout
    try:
        sys.stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "translate_text", "arguments": {"text": "invented text", "target_language": "en"}}}) + "\n")
        sys.stdout = io.StringIO()
        module["serve"](table)
        return json.loads(sys.stdout.getvalue())
    finally:
        sys.stdin, sys.stdout = stdin, stdout


new_rpc = rpc(mcp, new_table)
old_rpc = rpc(old_mcp, old_table)
case("current_mcp_marks_422_as_error_but_pre_hardening_mcp_does_not", lambda: require(
    new_rpc["result"].get("isError") is True and old_rpc["result"].get("isError") is not True))

# Static transitive local import inventory, including imports inside functions.
seen = set()
todo = ["src.memory_api", "src.memory_daemon"]
imports = {}
while todo:
    module = todo.pop()
    if module in seen:
        continue
    path = ROOT / (module.replace(".", "/") + ".py")
    if not path.is_file():
        continue
    seen.add(module)
    tree = ast.parse(path.read_text())
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            deps.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            deps.add(node.module)
            if node.module in {"src", "src.security"}:
                deps.update(node.module + "." + alias.name for alias in node.names)
    imports[module] = sorted(deps)
    todo.extend(d for d in deps if d.startswith("src."))
case("local_import_closure_contains_no_dotenv_or_legacy_model_stack", lambda: require(
    not any(any(word in dep.lower() for word in ("dotenv", "cognee.", "openai", "litellm", "intelligent_summarization", "auto_configuration", "advanced_search_reranking")) for deps in imports.values() for dep in deps)))
manifest = {}
for relative in sorted({m.replace(".", "/") + ".py" for m in seen} | {mcp_file, "integrations/hermes/enhanced_cognee/client.py", "integrations/hermes/deployment/enhanced-cognee-api.service"}):
    raw = (ROOT / relative).read_bytes()
    bound = subprocess.run(["git", "show", "c14f595c:" + relative], cwd=ROOT, capture_output=True)
    manifest[relative] = {"sha256": hashlib.sha256(raw).hexdigest(), "matches_c14f595c": bound.returncode == 0 and bound.stdout == raw}
require(all(v["matches_c14f595c"] for v in manifest.values()))
receipt = {
    "scope": "Offline stdlib-only execution and AST fragments; no server startup, real store, network, production credentials, or installed-state verification",
    "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
    "reviewed_source": subprocess.run(["git", "rev-parse", "c14f595c"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
    "pre_hardening_mcp_ref": old_ref,
    "pre_hardening_mcp_sha256": hashlib.sha256(old_text.encode()).hexdigest(),
    "cases": results, "passed": len(results), "failed": 0,
    "core_double_call_sequence": store_double.calls,
    "new_mcp_wire_calls": new_calls, "pre_hardening_mcp_wire_calls": old_calls,
    "new_mcp_refusal_rpc": new_rpc, "pre_hardening_mcp_refusal_rpc": old_rpc,
    "local_imports": imports, "source_manifest": manifest,
}
(OUT / "offline-route-receipt.json").write_text(json.dumps(receipt, ensure_ascii=True, indent=2) + "\n")
print(json.dumps({"passed": len(results), "failed": 0, "receipt": str(OUT / "offline-route-receipt.json"), "source_files_bound": len(manifest), "local_import_modules": len(imports)}, ensure_ascii=True))
