"""Record read-only dashboard-source findings and hashes, without importing it."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[2]
OWNED = ["src/hermes_memory/library.py", "bin/enhanced_cognee_library.py",
         "docs/hermes-knowledge-library.md", "tests/hermes_library/test_library.py",
         "tests/hermes_library/exercise_library.py", "tests/hermes_library/verify_sources.py"]
SOURCES = {
    "dashboard/dashboard_api.py": [(326, 343), (754, 810), (813, 850), (859, 911), (1081, 1125)],
    "dashboard/nextjs-dashboard/src/app/memories/page.tsx": [(9, 13), (79, 98)],
    "dashboard/nextjs-dashboard/src/app/memories/[id]/page.tsx": [(22, 22), (98, 103), (185, 192)],
    "dashboard/nextjs-dashboard/src/components/organisms/AddMemoryModal.tsx": [(82, 98)],
    "dashboard/nextjs-dashboard/src/components/organisms/EditMemoryModal.tsx": [(118, 139)],
    "dashboard/nextjs-dashboard/package.json": [(20, 71)],
    "dashboard/docker-compose-dashboard.yml": [(123, 128), (147, 165), (167, 187)],
    "dashboard/nextjs-dashboard/tsconfig.json": [(21, 23)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    baseline = "e25bd6356e38970c525e0258bdac983cd4079d29"
    records = []
    for relative, ranges in SOURCES.items():
        path = REPO / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        original = subprocess.run(["git", "show", baseline + ":" + relative], cwd=REPO,
                                  capture_output=True, check=True).stdout
        lines = data.decode("utf-8").splitlines()
        records.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                        "matches_baseline": data == original,
                        "excerpts": [{"start_line": start, "end_line": end,
                                      "lines": lines[start - 1:end]} for start, end in ranges]})
    tree = ast.parse((REPO / "dashboard/dashboard_api.py").read_text(encoding="utf-8"))
    routes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                        and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "app"
                        and decorator.args and isinstance(decorator.args[0], ast.Constant)):
                    routes.append({"method": decorator.func.attr, "path": decorator.args[0].value,
                                   "function": node.name, "line": node.lineno})
    missing = ["dashboard/nextjs-dashboard/src/lib/api/memories.ts",
               "dashboard/nextjs-dashboard/src/lib/utils/export.ts",
               "dashboard/nextjs-dashboard/src/lib/stores/index.ts",
               "dashboard/nextjs-dashboard/src/app/memories/[id]/edit/page.tsx"]
    tracked = subprocess.run(["git", "ls-files", "dashboard/nextjs-dashboard/src/lib",
                              "dashboard/nextjs-dashboard/src/app/memories"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout.splitlines()
    result = {"baseline": baseline, "source_only": True, "dashboard_build_attempted": False,
              "browser_ui_acceptance": False, "source_records": records, "routes": routes,
              "missing_referenced_files": {p: not (REPO / p).exists() for p in missing},
              "tracked_lib_and_memory_pages": tracked}
    assert all(r["matches_baseline"] for r in records)
    assert all(result["missing_referenced_files"].values())
    assert not any("export" in r["path"] or "revision" in r["path"] for r in routes)
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / "dashboard-source-verification.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="ascii")
    hashes = {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in OWNED}
    for relative in OWNED:
        if relative.endswith(".py"):
            compile((REPO / relative).read_text(encoding="utf-8"), str(REPO / relative), "exec")
        assert (REPO / relative).read_bytes().isascii(), "Keep owned code/docs ASCII"
    (args.evidence / "owned-files-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="ascii")
    print(json.dumps({"owned_sha256": hashes, "source_records": len(records), "routes": len(routes),
                      "baseline_sources_unchanged": True, "missing_referenced_files_confirmed": True,
                      "syntax_and_ascii_verified": True}, indent=2))


if __name__ == "__main__":
    main()
