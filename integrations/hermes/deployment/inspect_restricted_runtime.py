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
CHILD_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"}


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
        ["/usr/bin/git", "-c", "core.fsmonitor=false", "-C", str(SOURCE), *args],
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


def inspect() -> dict:
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
    parser.parse_args()
    try:
        result = inspect()
    except InspectionError as error:
        parser.exit(1, "STOP: " + str(error) + "\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        parser.exit(1, "STOP: runtime inspection did not complete; no changes were made.\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
