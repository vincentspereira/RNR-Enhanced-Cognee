"""Read-only inventory before preparing the approved restricted Hermes runtime.

Run as the human Ubuntu-Hermes operator. Does not import Hermes, execute .pth
files, launch an interpreter from the inspected tree, or read profile settings.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess


HOME = Path("/home/vincentspereira")
SOURCE = HOME / "agent-workspace/hermes-agent"
PYTHON = HOME / ".hermes/tools/python-3.14.7+20260901-linux-x64"
EXPECTED_REVISION = "4d04303818b61bf3aa09278af48356315515965b"
MODULE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
CHILD_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0",
             "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}


class InspectionError(RuntimeError):
    """Fixed, non-secret operator diagnostics."""


def bounded(path: Path, limit: int = 1048576) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise InspectionError("Installation metadata exceeded its size limit.")
    return raw


def git(*args: str) -> bytes:
    result = subprocess.run(
        ["/usr/bin/git", "--no-replace-objects", "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=/dev/null", "-C", str(SOURCE), *args],
        env=CHILD_ENV, capture_output=True, timeout=30,
    )
    if result.returncode:
        raise InspectionError("Source metadata could not be inspected; no changes made.")
    return result.stdout


def location(path: Path, environment: Path) -> dict:
    resolved = path.resolve()
    for kind, base in (("hermes_source", SOURCE.resolve()),
                       ("selected_environment", environment),
                       ("managed_python", PYTHON.resolve())):
        if resolved.is_relative_to(base):
            return {"kind": kind, "relative_path": resolved.relative_to(base).as_posix()}
    return {"kind": "outside_selected_runtime", "requires_review": True}


def pth_details(path: Path, site: Path, environment: Path) -> dict:
    if path.is_symlink() or not path.resolve().is_relative_to(site.resolve()):
        raise InspectionError("A startup file is a symlink or outside the selected environment.")
    raw = bounded(path, 65536)
    imports, references, unknown = set(), [], []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        if line.startswith(("import ", "import\t")):
            try:
                tree = ast.parse(line)
            except SyntaxError:
                unknown.append(number)
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names if MODULE.fullmatch(alias.name))
                elif isinstance(node, ast.ImportFrom) and node.module and MODULE.fullmatch(node.module):
                    imports.add(node.module)
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id == "__import__" and node.args
                      and isinstance(node.args[0], ast.Constant)
                      and isinstance(node.args[0].value, str)
                      and MODULE.fullmatch(node.args[0].value)):
                    imports.add(node.args[0].value)
            if any(not isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body):
                unknown.append(number)
        else:
            candidate = site / line
            if candidate.exists():
                references.append(location(candidate, environment))
            else:
                references.append({"kind": "nonexistent_entry"})
    return {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "imports": sorted(imports), "path_entries": references,
            "non_import_statement_or_unparsed_lines": unknown}


def allocated_bytes(path: Path) -> int:
    result = subprocess.run(
        ["/usr/bin/du", "-sx", "--block-size=1", "--", str(path)],
        env=CHILD_ENV, capture_output=True, timeout=120,
    )
    if result.returncode:
        raise InspectionError("Runtime size could not be measured; no files copied.")
    return int(result.stdout.split(None, 1)[0])


def selected_environment() -> tuple[Path, Path, bytes]:
    if os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes":
        raise InspectionError("Run this inside Ubuntu-Hermes, not Workspace or Windows.")
    if os.geteuid() == 0 or pwd.getpwuid(os.geteuid()).pw_name != "vincentspereira":
        raise InspectionError("Run as the human vincentspereira account without sudo.")
    if git("rev-parse", "HEAD").decode().strip() != EXPECTED_REVISION:
        raise InspectionError("Hermes source changed since the last checkpoint; inspect its new revision first.")
    key = hashlib.sha256(str(SOURCE.resolve()).encode()).hexdigest()[:16]
    state = HOME / ".hermes/installs" / key
    facts = bounded(state / "facts.json")
    selected = json.loads(facts.decode("utf-8-sig"))["packages"]["venv"]["environment"]
    if not isinstance(selected, str) or not Path(selected).is_absolute():
        raise InspectionError("The selected environment path is invalid.")
    environment = Path(selected).resolve(strict=True)
    if not environment.is_relative_to((state / "environments").resolve()):
        raise InspectionError("The selected environment escaped its installation.")
    site = environment / "lib/python3.14/site-packages"
    if not (environment / "pyvenv.cfg").is_file() or not site.is_dir():
        raise InspectionError("The selected Python 3.14 environment is incomplete.")
    return environment, state, facts


def lexical_location(path: Path, environment: Path) -> dict:
    """Match the preparer's lexical guard without following external targets."""
    normalized = Path(os.path.normpath(path))
    for kind, base in (("hermes_source", SOURCE), ("selected_environment", environment),
                       ("managed_python", PYTHON)):
        if normalized.is_relative_to(base):
            return {"kind": kind, "relative_path": normalized.relative_to(base).as_posix()}
    # Do not publish arbitrary outside paths or read their contents.
    for kind, base in (("other_operator_home", HOME), ("system_usr", Path("/usr")),
                       ("system_lib", Path("/lib")), ("system_lib64", Path("/lib64")),
                       ("system_bin", Path("/bin")), ("system_etc", Path("/etc")),
                       ("temporary", Path("/tmp"))):
        if normalized.is_relative_to(base):
            return {"kind": "outside_selected_runtime", "area": kind}
    if normalized == Path("/dev/null"):
        return {"kind": "outside_selected_runtime", "area": "dev_null"}
    return {"kind": "outside_selected_runtime", "area": "other_redacted"}


def runtime_links(root: Path):
    """Read link metadata only; never walk a linked directory."""
    def fail(_error):
        raise InspectionError("A selected program directory could not be inspected.")
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        dirs[:] = sorted(name for name in dirs if name != "__pycache__")
        for name in sorted(dirs + files):
            item = Path(directory) / name
            if item.is_symlink():
                yield item.relative_to(root).as_posix(), os.readlink(item)


def link_audit(environment: Path) -> dict:
    """Inspect both failure sources, without copying or executing program code."""
    counts = {"hermes_source": 0, "managed_python": 0, "selected_environment": 0}
    external = []
    def record(kind, root, relative, target):
        counts[kind] += 1
        original = root / relative
        target_path = Path(target) if os.path.isabs(target) else original.parent / target
        classified = lexical_location(target_path, environment)
        if classified["kind"] == "outside_selected_runtime":
            external.append({"tree": kind, "link": relative, "target": classified})

    # Inspect committed link blobs, not potentially modified working-tree links.
    for entry in git("ls-tree", "-r", "-z", EXPECTED_REVISION).split(b"\0"):
        if not entry:
            continue
        header, relative = entry.split(b"\t", 1)
        mode, kind, oid = header.split()
        if mode != b"120000":
            continue
        if kind != b"blob" or not re.fullmatch(b"[0-9a-f]{40,64}", oid):
            raise InspectionError("A committed link has unexpected metadata.")
        target = git("cat-file", "blob", oid.decode("ascii"))
        if len(target) > 4096:
            raise InspectionError("A committed link exceeded its size limit.")
        record("hermes_source", SOURCE, relative.decode("utf-8"), target.decode("utf-8"))
    for kind, root in (("managed_python", PYTHON), ("selected_environment", environment)):
        for relative, target in runtime_links(root):
            record(kind, root, relative, target)

    finders = []
    site = environment / "lib/python3.14/site-packages"
    for path in sorted(site.glob("__editable__*_finder.py")):
        if path.is_symlink():
            raise InspectionError("An editable finder is a link; inspect it separately.")
        tree = ast.parse(bounded(path).decode("utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and node.value.startswith(str(HOME) + "/")):
                finders.append({"file": path.name, "line": node.lineno,
                                "reference": lexical_location(Path(node.value), environment)})
    return {"links_inspected": counts, "external_link_count": len(external),
            "external_links": external[:40], "external_links_truncated": len(external) > 40,
            "editable_path_count": len(finders), "editable_paths": finders[:40],
            "editable_paths_truncated": len(finders) > 40}


def editable_table_audit(environment: Path) -> dict:
    """Explain all binding failures using only names present in the Git commit.

    Never execute a finder or read its mapped source paths. Unknown keys and
    all old source roots remain redacted; public source names come from Git.
    """
    files, directories = set(), set()
    for entry in git("ls-tree", "-r", "-z", EXPECTED_REVISION).split(b"\0"):
        if not entry:
            continue
        header, relative = entry.split(b"\t", 1)
        mode, kind, _oid = header.split()
        if kind != b"blob":
            continue
        name = relative.decode("utf-8")
        files.add(name)
        directories.update(parent.as_posix() for parent in Path(name).parents
                           if parent != Path("."))
    conventional = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
    findings = []
    site = environment / "lib/python3.14/site-packages"
    for finder in sorted(site.glob("__editable__*_finder.py")):
        if finder.is_symlink():
            raise InspectionError("An editable finder is a link; inspect it separately.")
        tree = ast.parse(bounded(finder).decode("utf-8"))
        issues, roots, seen_tables, bound_nodes = [], set(), set(), set()
        entries = paths = empty_namespaces = 0
        for statement in tree.body:
            if isinstance(statement, ast.AnnAssign):
                targets, value = [statement.target], statement.value
            elif isinstance(statement, ast.Assign):
                targets, value = statement.targets, statement.value
            else:
                continue
            names = [target.id for target in targets if isinstance(target, ast.Name)
                     and target.id in {"MAPPING", "NAMESPACES"}]
            if not names:
                continue
            table = names[0]
            if (len(targets) != 1 or len(names) != 1 or table in seen_tables
                    or not isinstance(value, ast.Dict)):
                issues.append({"table": table, "problem": "unsupported_or_duplicate_table"})
                continue
            seen_tables.add(table)
            seen_keys = set()
            for index, (key, entry) in enumerate(zip(value.keys, value.values)):
                entries += 1
                row = {"table": table, "entry": index, "line": getattr(key, "lineno", statement.lineno)}
                problems = []
                literal_key = isinstance(key, ast.Constant) and isinstance(key.value, str)
                name = key.value if literal_key else None
                public_paths = []
                if name is not None:
                    relative = "/".join(name.split("."))
                    for candidate in (name + ".py", relative, relative + ".py"):
                        if candidate in files or candidate in directories:
                            public_paths.append(candidate)
                    if public_paths:
                        row["public_module"] = name
                        row["committed_paths"] = sorted(set(public_paths))
                    else:
                        row["module"] = "redacted_not_in_commit"
                        problems.append("no_corresponding_committed_module")
                    if not conventional.fullmatch(name):
                        problems.append("nonstandard_module_name")
                    if len(name) > 256:
                        problems.append("module_name_too_long")
                    if name in seen_keys:
                        problems.append("duplicate_module_name")
                    seen_keys.add(name)
                else:
                    problems.append("nonliteral_module_name")
                if table == "NAMESPACES":
                    if isinstance(entry, ast.List):
                        nodes = entry.elts
                        empty_namespaces += int(not nodes)
                    else:
                        nodes = []
                        problems.append("unsupported_namespace_paths")
                else:
                    nodes = [entry]
                for node in nodes:
                    paths += 1
                    bound_nodes.add(id(node))
                    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                        problems.append("nonliteral_import_path")
                        continue
                    old = Path(node.value)
                    if not old.is_absolute() or str(old) != os.path.normpath(node.value):
                        problems.append("non_normalized_absolute_import_path")
                    if name is None or not name or "/" in name or "\\" in name:
                        continue
                    suffix = Path(*name.split("."))
                    if not suffix.parts or not suffix.name:
                        problems.append("declared_module_suffix_mismatch")
                        continue
                    if old.suffix == ".py":
                        suffix = suffix.with_suffix(".py")
                    matches = bool(suffix.parts) and old.parts[-len(suffix.parts):] == suffix.parts
                    if matches:
                        root = old
                        for _ in suffix.parts:
                            root = root.parent
                        roots.add(str(root))
                    else:
                        problems.append("declared_module_suffix_mismatch")
                    if name + ".py" in files:
                        row["target_matches_flat_root_module"] = old.name in {name, name + ".py"}
                    # Only output a classification, never the old target/root.
                    row["target_area"] = lexical_location(old, environment)["kind"]
                if problems:
                    row["problems"] = sorted(set(problems))
                    issues.append(row)
        unbound = sum(1 for node in ast.walk(tree)
                      if isinstance(node, ast.Constant) and isinstance(node.value, str)
                      and node.value.startswith(str(HOME) + "/") and id(node) not in bound_nodes)
        findings.append({"file": finder.name, "tables": sorted(seen_tables),
                         "entries_checked": entries, "paths_checked": paths,
                         "empty_namespace_lists": empty_namespaces,
                         "declared_source_root_count": len(roots),
                         "unbound_home_path_count": unbound, "problem_entry_count": len(issues),
                         "problem_entries": issues[:40], "problems_truncated": len(issues) > 40})
    if not findings:
        raise InspectionError("The editable finder is missing; no preparation was attempted.")
    return {"editable_tables": findings}


def managed_tool_audit() -> dict:
    """Read only four tool records/paths; no execution, installation or secrets."""
    root = HOME / ".hermes/tools"
    facts_raw = bounded(root / "facts.json")
    packages = json.loads(facts_raw).get("packages", {})
    lock_raw = git("show", EXPECTED_REVISION + ":pm/lock.json")
    if len(lock_raw) > 1048576 or not isinstance(packages, dict):
        raise InspectionError("Managed tool metadata has an unsupported shape or size.")
    locked = json.loads(lock_raw)["packages"]
    snapshot = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783/python")
    snapshot_packages = json.loads(bounded(snapshot / "facts.json")).get("packages", {})
    if not isinstance(snapshot_packages, dict):
        raise InspectionError("Protected tool metadata has an unsupported shape.")
    binaries = {"ffmpeg": "bin/ffmpeg", "node": "bin/node", "npm": "bin/npm", "ripgrep": "rg"}
    version_pattern = re.compile(r"[A-Za-z0-9_.+\-]{1,120}")
    tools = []
    for name, binary in binaries.items():
        pin = locked[name]["version"]
        if not isinstance(pin, str) or not version_pattern.fullmatch(pin):
            raise InspectionError("A managed tool pin has an unsupported format.")
        record = packages.get(name)
        row = {"name": name, "locked_version": pin,
               "protected_record_present": name in snapshot_packages,
               "original_record_present": record is not None}
        if record is None:
            tools.append(row)
            continue
        if not isinstance(record, dict):
            raise InspectionError("A selected tool record has an unsupported format.")
        version, entry = record.get("version"), record.get("entry")
        if (not isinstance(version, str) or not version_pattern.fullmatch(version)
                or not isinstance(entry, str) or not entry or len(entry) > 512):
            raise InspectionError("A selected tool entry/version needs a format review.")
        row.update(recorded_version=version, recorded_version_matches_lock=version == pin)
        original = root / entry
        lexical = Path(os.path.normpath(original))
        if not lexical.is_relative_to(root) or lexical == root:
            row["entry_state"] = "outside_tool_store_redacted"
            tools.append(row)
            continue
        row["entry"] = lexical.relative_to(root).as_posix()
        if lexical.is_symlink() or not lexical.resolve().is_relative_to(root.resolve()):
            row["entry_state"] = "linked_entry_requires_review"
        elif not lexical.exists():
            row["entry_state"] = "missing"
        elif lexical.is_dir():
            candidate = lexical / binary
            links = list(runtime_links(lexical))
            outside = 0
            for relative, target in links:
                link = lexical / relative
                destination = Path(target) if os.path.isabs(target) else link.parent / target
                outside += int(not Path(os.path.normpath(destination)).is_relative_to(root))
            row.update(entry_state="directory", allocated_bytes=allocated_bytes(lexical),
                       expected_binary=binary, binary_present=candidate.is_file(),
                       binary_executable=os.access(candidate, os.X_OK),
                       binary_resolves_inside_tool_store=candidate.resolve().is_relative_to(root.resolve()),
                       link_count=len(links), links_outside_tool_store=outside)
        else:
            row["entry_state"] = "not_a_directory_requires_review"
        tools.append(row)
    if facts_raw != bounded(root / "facts.json"):
        raise InspectionError("Managed tool selection changed during inspection.")
    return {"managed_tools": tools, "tool_binaries_executed": False,
            "tool_versions_verified_by_execution": False, "runtime_qualified": False}


def inspect(links_only=False, editable_tables=False, managed_tools=False) -> dict:
    environment, state, facts = selected_environment()
    if links_only or editable_tables or managed_tools:
        findings = (managed_tool_audit() if managed_tools else
                    editable_table_audit(environment) if editable_tables else link_audit(environment))
        if facts != bounded(state / "facts.json") or git("rev-parse", "HEAD").decode().strip() != EXPECTED_REVISION:
            raise InspectionError("The source or selection changed during link inspection.")
        return {"complete": True, "read_only": True, "source_revision": EXPECTED_REVISION,
                "files_copied": 0, "hermes_launched": False, **findings}
    site = environment / "lib/python3.14/site-packages"
    startup = [pth_details(path, site, environment) for path in sorted(site.glob("*.pth"))]
    entries = git("ls-tree", "-r", "-l", "-z", "HEAD").split(b"\0")
    source_bytes = submodules = source_files = 0
    for entry in entries:
        if not entry:
            continue
        header, _ = entry.split(b"\t", 1)
        mode, kind, _, size = header.split()
        submodules += int(mode == b"160000")
        if kind == b"blob":
            source_bytes += int(size)
            source_files += 1
    sizes = {"managed_python_allocated_bytes": allocated_bytes(PYTHON),
             "selected_environment_allocated_bytes": allocated_bytes(environment),
             "committed_source_file_bytes": source_bytes,
             "opt_free_bytes": shutil.disk_usage("/opt").free}
    if facts != bounded(state / "facts.json") or git("rev-parse", "HEAD").decode().strip() != EXPECTED_REVISION:
        raise InspectionError("The source or selected dependency environment changed during inspection.")
    return {"complete": True, "read_only": True, "source_revision": EXPECTED_REVISION,
            "selected_environment": str(environment), "pth_files": startup,
            "source_tracked_files": source_files, "source_submodules": submodules,
            "sizes": sizes, "files_copied": 0, "hermes_launched": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--links-only", action="store_true",
                      help="Inspect program link metadata and editable paths without copying.")
    mode.add_argument("--editable-tables", action="store_true",
                      help="Explain generated import-table validation failures without copying.")
    mode.add_argument("--managed-tools", action="store_true",
                      help="Inspect four selected tool records/paths without executing or copying tools.")
    args = parser.parse_args()
    try:
        result = inspect(links_only=args.links_only, editable_tables=args.editable_tables,
                         managed_tools=args.managed_tools)
    except InspectionError as error:
        parser.exit(1, "STOP: " + str(error) + "\n")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError,
            SyntaxError, subprocess.SubprocessError):
        parser.exit(1, "STOP: runtime inspection did not complete; no changes were made.\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
