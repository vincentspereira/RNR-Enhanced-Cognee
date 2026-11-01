"""Prepare, but do not launch, the approved protected Hermes program snapshot.

No service/recovery configuration is read. Git runs as the human operator;
only stdlib runs as root. Existing installations and profiles are not changed.
Requires the separately inspected source, dependency selection and startup hashes.
"""
from __future__ import annotations

import argparse
import ast
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import tarfile
import tempfile


HOME = Path("/home/vincentspereira")
SOURCE = HOME / "agent-workspace/hermes-agent"
PYTHON = HOME / ".hermes/tools/python-3.14.7+20260901-linux-x64"
STATE = HOME / ".hermes/installs/cec419d56f3c6da1"
ENVIRONMENT = STATE / "environments/1729494fe7834770ba4afd450a636baa/venv"
REVISION = "4d04303818b61bf3aa09278af48356315515965b"
ACCOUNT = "hermes-runtime"
ACCOUNT_HOME = Path("/var/lib/hermes-runtime")
PARENT = Path("/opt/hermes-runtime")
RELEASE = PARENT / "releases/4d04303818b6-1729494fe783"
TOOL_STORE = HOME / ".hermes/tools"
MANAGED_TOOLS = {
    "ffmpeg": ("9.0.1", "bin/ffmpeg"),
    "node": ("26.7.0", "bin/node"),
    "npm": ("12.0.2", "bin/npm"),
    "ripgrep": ("15.2.0", "rg"),
}
PTH_HASHES = {
    "__editable__.hermes_agent-0.0.0.pth": "a58e1404c760ee958735df264804a620ef9ad7362443d1fb2437731d205a9c5c",
    "_virtualenv.pth": "69ac3d8f27e679c81b94ab30b3b56e9cd138219b1ba94a1fa3606d5a76a1433d",
    "distutils-precedence.pth": "2638ce9e2500e572a5e0de7faed6661eb569d1b696fcba07b0dd223da5f5d224",
}


class PreparationError(RuntimeError):
    """Only fixed, non-secret diagnostics leave the operator process."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_startup(site: Path):
    found = {p.name: digest(small_file(p, 65536)) for p in site.glob("*.pth")}
    if found != PTH_HASHES:
        raise PreparationError("The startup files differ from the inspected set.")


def small_file(path: Path, limit=1048576) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise PreparationError("Unexpected metadata file type or size.")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise PreparationError("Metadata exceeded its size limit.")
    return raw


def write_new(path: Path, raw: bytes, mode=0o644):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fsync(stream.fileno())


def private_parent(path: Path):
    """Do not traverse writable ancestors, even on an initial installation."""
    for part in reversed((path, *path.parents)):
        if not part.exists() and not part.is_symlink():
            part.mkdir(mode=0o755)
        info = part.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
                or info.st_mode & 0o022):
            raise PreparationError("A destination ancestor is not protected and root-owned.")


def translated(path: Path, mappings: list[tuple[Path, Path]]) -> Path:
    lexical = Path(os.path.normpath(path))
    for old, new in sorted(mappings, key=lambda pair: len(str(pair[0])), reverse=True):
        if lexical.is_relative_to(old):
            return new / lexical.relative_to(old)
    raise PreparationError("A program link references files outside the selected runtime.")


def make_link(original: Path, target: str, destination: Path, mappings):
    source_target = Path(target) if os.path.isabs(target) else original.parent / target
    mapped = translated(source_target, mappings)
    os.symlink(os.path.relpath(mapped, destination.parent), destination)


def copy_regular(source: Path, destination: Path, *, directory_fd=None):
    fd = os.open(source if directory_fd is None else source.name,
                 os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as incoming:
        before = os.fstat(incoming.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o6000:
            raise PreparationError("A program file has an unexpected type or privilege bit.")
        mode = 0o755 if before.st_mode & 0o111 else 0o644
        output = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(output, "wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            outgoing.flush()
            os.fchmod(outgoing.fileno(), mode)
        after = os.fstat(incoming.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise PreparationError("A source program file changed while being copied.")


def ignored(name: str) -> bool:
    return (name == "__pycache__" or name.endswith((".pyc", ".pyo"))
            or name in {"direct_url.json", "pyvenv.cfg", ".env"}
            or (name.startswith(".env.") and not name.endswith((".example", ".template"))))


def open_directory(path: Path) -> int:
    """Pin every ancestor without following a swapped directory symlink."""
    if not path.is_absolute():
        raise PreparationError("A copy source is not an absolute path.")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def tool_metadata(path: Path) -> bytes:
    """Read public package metadata through pinned, non-symlink ancestors."""
    parent = open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
                raise PreparationError("Managed tool metadata has an unsupported type or size.")
            raw = stream.read(1048577)
            if len(raw) > 1048576:
                raise PreparationError("Managed tool metadata exceeded its size limit.")
            return raw
    finally:
        os.close(parent)


def tool_digest(root: Path, *, mappings=None, destination=None) -> str:
    """PM-compatible Linux payload hash, without following source links.

    Match the selected pm/store.py relpath/NUL/content format. Recalculate link
    text only when predicting the relocated copy. Never execute PM code as root.
    """
    paths = []

    def collect(fd, prefix=Path(".")):
        try:
            for name in sorted(os.listdir(fd)):
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                relative = prefix / name
                if stat.S_ISDIR(info.st_mode):
                    if name != "__pycache__":
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                        collect(child, relative)
                elif stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    paths.append(relative)
                else:
                    raise PreparationError("A managed tool contains a special file.")
        finally:
            os.close(fd)

    collect(open_directory(root))
    hasher = hashlib.sha256()
    for relative in sorted(paths, key=lambda path: path.as_posix()):
        parent = open_directory(root / relative.parent)
        try:
            info = os.stat(relative.name, dir_fd=parent, follow_symlinks=False)
            hasher.update(relative.as_posix().encode("utf-8") + b"\0")
            if stat.S_ISLNK(info.st_mode):
                value = os.readlink(relative.name, dir_fd=parent)
                if mappings is not None:
                    original = root / relative
                    target = Path(value) if os.path.isabs(value) else original.parent / value
                    value = os.path.relpath(translated(target, mappings),
                                           (destination / relative).parent)
                hasher.update(value.encode("utf-8"))
            else:
                fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o6000:
                        raise PreparationError("A managed tool file has an unsupported type or privilege bit.")
                    for chunk in iter(lambda: stream.read(1048576), b""):
                        hasher.update(chunk)
                    after = os.fstat(stream.fileno())
                    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                        raise PreparationError("A managed tool changed during fingerprinting.")
        finally:
            os.close(parent)
    return hasher.hexdigest()


def selected_tools(lock_raw: bytes, facts_raw: bytes) -> dict:
    """Admit only the four inspected pins with complete recorded identities."""
    lock, facts = json.loads(lock_raw), json.loads(facts_raw)
    if lock.get("schema") != 1 or facts.get("schema") != 1:
        raise PreparationError("Managed tool metadata needs a schema review.")
    selected = {}
    for name, (version, binary) in MANAGED_TOOLS.items():
        pin = lock["packages"][name]
        record = facts["packages"][name]
        entry = name + "-" + version + "-linux-x64"
        artifacts = pin["artifacts"].get("linux-x64", pin["artifacts"].get("any"))
        artifacts = artifacts if isinstance(artifacts, list) else [artifacts]
        hashes = [item["sha256"] for item in artifacts]
        if (pin["version"] != version or record.get("version") != version
                or record.get("entry") != entry or record.get("target") != "linux-x64"
                or record.get("artifacts") != hashes or not hashes
                or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                       for value in [*hashes, record.get("digest")])):
            raise PreparationError("A managed tool identity or payload fingerprint differs from the inspected lock.")
        # Construct only the reviewed program PATH. Do not import arbitrary
        # environment keys/values from the human account's package facts.
        bindir = str(PurePosixPath(entry) / PurePosixPath(binary).parent)
        selected[name] = {"entry": entry, "version": version, "target": "linux-x64",
                          "artifacts": hashes, "digest": record["digest"],
                          "env": {"PATH": ["{{store}}/" + bindir]}}
    return selected


def copy_managed_tools(stage: Path, selected: dict) -> list[dict]:
    reports = []
    tool_mappings = [(TOOL_STORE / row["entry"], stage / "python" / row["entry"])
                     for row in selected.values()]
    for name, record in selected.items():
        source = TOOL_STORE / record["entry"]
        target = stage / "python" / record["entry"]
        if tool_digest(source) != record["digest"]:
            raise PreparationError("A managed tool's original payload fingerprint does not match its record.")
        expected = tool_digest(source, mappings=tool_mappings, destination=target)
        copy_tree(source, target, tool_mappings)
        actual = tool_digest(target)
        if actual != expected or tool_digest(source) != record["digest"]:
            raise PreparationError("A managed tool changed during protected copying.")
        binary = target / MANAGED_TOOLS[name][1]
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise PreparationError("A protected tool binary is missing or not executable.")
        record["digest"] = actual
        reports.append({"name": name, "version": record["version"],
                        "source_payload_verified": True, "copy_payload_verified": True,
                        "tool_version_verified_by_execution": False})
    return reports


def copy_tree(source: Path, destination: Path, mappings, *, directory_fd=None):
    fd = open_directory(source) if directory_fd is None else directory_fd
    try:
        destination.mkdir(mode=0o755)
        for name in sorted(os.listdir(fd)):
            if ignored(name) or (source == ENVIRONMENT / "bin" and name.startswith("activate")):
                continue
            item, out = source / name, destination / name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                make_link(item, os.readlink(name, dir_fd=fd), out, mappings)
            elif stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                copy_tree(item, out, mappings, directory_fd=child)
            elif stat.S_ISREG(info.st_mode):
                copy_regular(item, out, directory_fd=fd)
            else:
                raise PreparationError("A source program tree contains a special file.")
    finally:
        os.close(fd)


def unpack_source(archive: Path, destination: Path, mappings):
    destination.mkdir(mode=0o755)
    links = []
    with tarfile.open(archive, "r:") as stream:
        for member in stream:
            relative = PurePosixPath(member.name)
            if (relative.is_absolute() or ".." in relative.parts or "\\" in member.name
                    or not relative.parts or relative.parts[0] in {".git", ".hermes"}):
                raise PreparationError("An archive member has an unsafe destination.")
            if any(ignored(part) for part in relative.parts):
                continue
            out = destination.joinpath(*relative.parts)
            out.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            if member.isdir():
                out.mkdir(mode=0o755, exist_ok=True)
            elif member.issym():
                links.append((SOURCE.joinpath(*relative.parts), member.linkname, out))
            elif member.isfile() and not member.mode & 0o6000:
                incoming = stream.extractfile(member)
                if incoming is None:
                    raise PreparationError("A source archive member could not be read.")
                with incoming:
                    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o755 if member.mode & 0o111 else 0o644)
                    with os.fdopen(fd, "wb") as outgoing:
                        shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                        os.fchmod(outgoing.fileno(), 0o755 if member.mode & 0o111 else 0o644)
            else:
                raise PreparationError("The source archive has an unsupported member type.")
    for original, target, out in links:
        make_link(original, target, out, mappings)


def verified_import_bindings(tree, source_tree: Path | None, mappings, *, catalog=None,
                             report=None) -> dict[int, str]:
    """Reconstruct generated imports from committed files, never old build trees.

    Setuptools finders can refer to a build-source mirror outside SOURCE.
    Missing derived namespace entries are omitted from the NEW import map, never
    from the original installation. Module bindings must always exist. Every
    path, including omitted namespace paths, must describe the same source root.
    """
    replacements, roots, tables = {}, set(), set()
    final_source = translated(SOURCE, mappings)
    module_name = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
    namespace_name = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")
    counts = {"module_bindings": 0, "namespace_paths_retained": 0,
              "namespace_paths_omitted": 0, "namespace_entries_omitted": 0}

    def source_types(relative):
        expected = None
        if catalog is not None:
            files, directories = catalog
            expected = relative.as_posix() in directories, relative.as_posix() in files
            if source_tree is None:
                return expected
        candidate = source_tree / relative
        if not candidate.resolve().is_relative_to(source_tree.resolve()):
            raise PreparationError("An editable import escapes the committed source copy.")
        actual = candidate.is_dir(), candidate.is_file()
        return tuple(left and right for left, right in zip(actual, expected)) if expected is not None else actual

    for statement in tree.body:
        if isinstance(statement, ast.AnnAssign):
            targets, value = [statement.target], statement.value
        elif isinstance(statement, ast.Assign):
            targets, value = statement.targets, statement.value
        else:
            continue
        named = [target.id for target in targets if isinstance(target, ast.Name)
                 and target.id in {"MAPPING", "NAMESPACES"}]
        if not named:
            continue
        if len(targets) != 1 or len(named) != 1 or named[0] in tables or not isinstance(value, ast.Dict):
            raise PreparationError("An editable import table has an unsupported structure.")
        table = named[0]
        tables.add(table)
        seen = set()
        retained_keys, retained_values = [], []
        for key, entry in zip(value.keys, value.values):
            name_rule = namespace_name if table == "NAMESPACES" else module_name
            if (not isinstance(key, ast.Constant) or not isinstance(key.value, str)
                    or len(key.value) > 256 or not name_rule.fullmatch(key.value)
                    or key.value in seen):
                raise PreparationError("An editable import table has an unsupported module name.")
            seen.add(key.value)
            relative = Path(*key.value.split("."))
            if table == "NAMESPACES":
                if not isinstance(entry, ast.List):
                    raise PreparationError("An editable namespace has an unsupported path list.")
                entries = entry.elts
            else:
                entries = [entry]
            retained_nodes = []
            for node in entries:
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    raise PreparationError("An editable import path is not a literal string.")
                old = Path(node.value)
                if not old.is_absolute() or str(old) != os.path.normpath(node.value):
                    raise PreparationError("An editable import path is not a normalized absolute path.")
                # A module's generated finder target can omit its .py suffix.
                suffix = relative.with_suffix(".py") if old.suffix == ".py" else relative
                if old.parts[-len(suffix.parts):] != suffix.parts:
                    raise PreparationError("An editable import does not match its declared module path.")
                root = old
                for _ in suffix.parts:
                    root = root.parent
                roots.add(root)
                is_directory, is_file = source_types(suffix)
                if table == "NAMESPACES":
                    if not is_directory:
                        counts["namespace_paths_omitted"] += 1
                        continue
                    counts["namespace_paths_retained"] += 1
                else:
                    _unused, has_python_file = source_types(suffix.with_suffix(".py"))
                    if not (is_directory or (is_file if suffix.suffix == ".py" else has_python_file)):
                        raise PreparationError("An editable module is missing from the committed source copy.")
                    counts["module_bindings"] += 1
                replacements[id(node)] = str(final_source / suffix)
                retained_nodes.append(node)
            if table == "NAMESPACES":
                if entries and not retained_nodes:
                    counts["namespace_entries_omitted"] += 1
                    continue
                entry.elts = retained_nodes
            retained_keys.append(key)
            retained_values.append(entry)
        value.keys, value.values = retained_keys, retained_values
    if "MAPPING" not in tables or not replacements or len(roots) != 1:
        raise PreparationError("Editable imports do not describe one supported committed source layout.")
    if report is not None:
        report.update(counts)
    return replacements


def rebase_finder(raw: bytes, mappings, *, source_tree: Path | None = None,
                  catalog=None, report=None) -> bytes:
    tree = ast.parse(raw.decode("utf-8"))
    replacements = (verified_import_bindings(tree, source_tree, mappings, catalog=catalog, report=report)
                    if source_tree is not None or catalog is not None else {})
    class Rebase(ast.NodeTransformer):
        def visit_Constant(self, node):
            if id(node) in replacements:
                node.value = replacements[id(node)]
            elif isinstance(node.value, str) and node.value.startswith(str(HOME) + "/"):
                node.value = str(translated(Path(node.value), mappings))
            return node
    tree = ast.fix_missing_locations(Rebase().visit(tree))
    result = (ast.unparse(tree) + "\n").encode()
    if str(HOME).encode() in result:
        raise PreparationError("An editable import still refers to the administrator home.")
    compile(result, "protected-editable-install", "exec")
    return result


def rewrite_generated(path: Path, raw: bytes, audit: Path):
    """Original user files are never modified; keep copied originals privately."""
    original = small_file(path, 4194304)
    write_new(audit / (path.name + ".original"), original, 0o600)
    fd = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def git_as_operator(operator, *args, stdout=subprocess.PIPE):
    credentials = {}
    if os.geteuid() == 0:
        credentials = {"user": operator.pw_uid, "group": operator.pw_gid, "extra_groups": ()}
    elif os.geteuid() != operator.pw_uid:
        raise PreparationError("Git inspection must run as the human operator.")
    result = subprocess.run(
        ["/usr/bin/git", "--no-replace-objects", "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=/dev/null", "-C", str(SOURCE), *args],
        **credentials, cwd="/tmp",
        env={"PATH": "/usr/bin:/bin", "HOME": str(HOME), "LC_ALL": "C",
             "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_GLOBAL": "/dev/null",
             "GIT_CONFIG_SYSTEM": "/dev/null"},
        stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.PIPE, timeout=120,
    )
    if result.returncode:
        raise PreparationError("The unprivileged source export failed; originals were retained.")
    return result.stdout


def committed_catalog(operator):
    """The same public source layout drives no-copy and copied-source checks."""
    files, directories = set(), set()
    for item in git_as_operator(operator, "ls-tree", "-r", "-z", REVISION).split(b"\0"):
        if not item:
            continue
        header, raw_name = item.split(b"\t", 1)
        mode, kind, _oid = header.split()
        relative = PurePosixPath(raw_name.decode("utf-8"))
        if (relative.is_absolute() or ".." in relative.parts or "\\" in str(relative)
                or relative.parts[0] in {".git", ".hermes"}):
            raise PreparationError("Committed source metadata has an unsafe path.")
        if mode == b"160000" or mode == b"120000":
            raise PreparationError("Source links/submodules need a separate native preflight review.")
        if kind != b"blob" or any(ignored(part) for part in relative.parts):
            continue
        files.add(relative.as_posix())
        directories.update(parent.as_posix() for parent in relative.parents if parent != PurePosixPath("."))
    return files, directories


def preflight() -> dict:
    """Validate import relocation from committed tree metadata, with no copies."""
    if (os.geteuid() == 0 or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes"
            or pwd.getpwuid(os.geteuid()).pw_name != "vincentspereira"):
        raise PreparationError("Run preflight as the normal Ubuntu-Hermes human operator without sudo.")
    operator = pwd.getpwuid(os.geteuid())
    revision = git_as_operator(operator, "rev-parse", "HEAD").decode().strip()
    if revision != REVISION:
        raise PreparationError("The Hermes source revision changed; inspect it before preflight.")
    facts = small_file(STATE / "facts.json")
    if json.loads(facts)["packages"]["venv"]["environment"] != str(ENVIRONMENT):
        raise PreparationError("The selected dependency generation changed.")
    site = ENVIRONMENT / "lib/python3.14/site-packages"
    check_startup(site)
    files, directories = committed_catalog(operator)
    finders = []
    mappings = [(SOURCE, RELEASE / "repo"), (PYTHON, RELEASE / "python"),
                (ENVIRONMENT, RELEASE / "venv")]
    originals = {}
    for path in sorted(site.glob("__editable__*_finder.py")):
        raw = small_file(path, 4194304)
        counts = {}
        rebase_finder(raw, mappings, catalog=(files, directories), report=counts)
        originals[path] = raw
        finders.append({"file": path.name, **counts})
    if not finders:
        raise PreparationError("The inspected editable import finder is missing.")
    if (small_file(STATE / "facts.json") != facts
            or git_as_operator(operator, "rev-parse", "HEAD").decode().strip() != REVISION
            or any(small_file(path, 4194304) != raw for path, raw in originals.items())
            or {path.name for path in site.glob("__editable__*_finder.py")} != {path.name for path in originals}):
        raise PreparationError("Source, selection or editable imports changed during preflight.")
    check_startup(site)
    return {"complete": True, "read_only": True, "import_preflight_passed": True,
            "source_revision": REVISION, "finders": finders, "files_copied": 0,
            "snapshot_prepared": False, "hermes_launched": False, "runtime_qualified": False}


def snapshot_manifest(root: Path) -> dict:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("operator-evidence/") or relative == "snapshot-files.json":
            continue
        info = path.lstat()
        if info.st_uid != os.geteuid() or (not path.is_symlink() and info.st_mode & 0o022):
            raise PreparationError("A copied program file has unsafe ownership or permissions.")
        if path.is_symlink():
            if not path.resolve(strict=True).is_relative_to(root):
                raise PreparationError("A copied symlink escapes the protected snapshot.")
            result[relative] = {"link": os.readlink(path)}
        elif path.is_file():
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1048576), b""):
                    hasher.update(chunk)
            result[relative] = {"sha256": hasher.hexdigest(), "bytes": info.st_size}
    return result


def publish(source: Path, destination: Path):
    """Atomic Linux publication that never replaces an existing destination."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                       ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
        raise PreparationError("Snapshot publication refused; the destination was not replaced.")


def launcher_bytes(uid: int) -> bytes:
    code = ("import os,runpy,sys; "
            f"os.environ['HOME']={str(ACCOUNT_HOME)!r}; "
            f"os.environ['HERMES_HOME']={str(ACCOUNT_HOME / '.hermes')!r}; "
            f"sys.path.insert(0,{str(RELEASE / 'repo')!r}); "
            "import hermes_bootstrap; runpy.run_module('hermes_cli.main',run_name='__main__')")
    launcher = ("#!/bin/sh\n"
                f"if [ \"$(/usr/bin/id -u)\" != {shlex.quote(str(uid))} ]; then\n"
                "  printf 'Run this launcher as hermes-runtime.\\n' >&2; exit 1\nfi\n"
                f"cd {shlex.quote(str(ACCOUNT_HOME))} || exit 1\n"
                "exec /usr/bin/setpriv --no-new-privs -- /usr/bin/env -i "
                f"HOME={shlex.quote(str(ACCOUNT_HOME))} USER=hermes-runtime LOGNAME=hermes-runtime "
                "PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 "
                'TERM="${TERM:-xterm-256color}" '
                f"{shlex.quote(str(RELEASE / 'venv/bin/python'))} -I -B -c "
                + shlex.quote(code) + ' "$@"\n')
    return launcher.encode()


def prepare(*, with_managed_tools=False) -> dict:
    if (os.geteuid() != 0 or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes"
            or os.environ.get("SUDO_USER") != "vincentspereira"):
        raise PreparationError("Use the approved Ubuntu-Hermes human operator and sudo launcher.")
    os.umask(0o022)
    privilege_tool = Path("/usr/bin/setpriv").stat()
    if (not stat.S_ISREG(privilege_tool.st_mode) or privilege_tool.st_uid != 0
            or privilege_tool.st_mode & 0o6022 or not privilege_tool.st_mode & 0o111):
        raise PreparationError("The system no-new-privileges launcher needs review.")
    operator = pwd.getpwnam("vincentspereira")
    account = pwd.getpwnam(ACCOUNT)
    if (account.pw_uid == 0 or Path(account.pw_dir) != ACCOUNT_HOME
            or set(os.getgrouplist(ACCOUNT, account.pw_gid)) != {account.pw_gid}):
        raise PreparationError("The restricted account no longer matches the approved setup.")
    if any(path != path.resolve(strict=True) for path in (SOURCE, PYTHON, ENVIRONMENT, ACCOUNT_HOME)):
        raise PreparationError("A selected source or home path changed or contains a symlink.")
    if git_as_operator(operator, "rev-parse", "HEAD").decode().strip() != REVISION:
        raise PreparationError("The Hermes source revision changed; inspect it before copying.")
    facts = small_file(STATE / "facts.json")
    if json.loads(facts)["packages"]["venv"]["environment"] != str(ENVIRONMENT):
        raise PreparationError("The selected dependency generation changed.")
    old_site = ENVIRONMENT / "lib/python3.14/site-packages"
    check_startup(old_site)
    if shutil.disk_usage("/opt").free < 4 * 1024**3:
        raise PreparationError("Insufficient free filesystem space for a protected snapshot.")
    if os.path.lexists(RELEASE):
        raise PreparationError("The proposed snapshot already exists; it will not be overwritten.")
    tool_facts_raw, tool_records = None, {}
    if with_managed_tools:
        tool_facts_raw = tool_metadata(TOOL_STORE / "facts.json")
        tool_records = selected_tools(git_as_operator(operator, "show", REVISION + ":pm/lock.json"),
                                      tool_facts_raw)
        # Fail before the large copy if a cached payload no longer matches.
        for record in tool_records.values():
            if tool_digest(TOOL_STORE / record["entry"]) != record["digest"]:
                raise PreparationError("An original managed tool no longer matches its payload fingerprint.")
    private_parent(RELEASE.parent)
    stage = Path(tempfile.mkdtemp(prefix=".preparing-", dir=RELEASE.parent))
    audit = stage / "operator-evidence"
    audit.mkdir(mode=0o700)
    print("Preparing protected Hermes program files; existing profiles remain unchanged.", flush=True)
    mappings = [(SOURCE, stage / "repo"), (PYTHON, stage / "python"),
                (ENVIRONMENT, stage / "venv")]
    final_mappings = [(SOURCE, RELEASE / "repo"), (PYTHON, RELEASE / "python"),
                      (ENVIRONMENT, RELEASE / "venv")]
    archive = audit / "source.tar"
    with archive.open("xb") as stream:
        os.chmod(archive, 0o600)
        git_as_operator(operator, "archive", "--format=tar", REVISION, stdout=stream)
    unpack_source(archive, stage / "repo", mappings)
    # Validate/reconstruct import maps before the large interpreter/dependency
    # copy. Do not follow the old build-source references or execute the finder.
    finders = {}
    import_reports = []
    catalog = committed_catalog(operator)
    for finder in old_site.glob("__editable__*_finder.py"):
        raw = small_file(finder, 4194304)
        counts = {}
        updated = rebase_finder(raw, final_mappings, source_tree=stage / "repo", catalog=catalog, report=counts)
        finders[finder.name] = (raw, updated)
        import_reports.append({"file": finder.name, **counts})
    if not finders:
        raise PreparationError("The inspected editable import finder is missing.")
    copy_tree(PYTHON, stage / "python", mappings)
    copy_tree(ENVIRONMENT, stage / "venv", mappings)
    site = stage / "venv/lib/python3.14/site-packages"
    check_startup(site)
    if {path.name for path in site.glob("__editable__*_finder.py")} != set(finders):
        raise PreparationError("The editable import finder set changed during the copy.")
    for name, (original, updated) in finders.items():
        finder = site / name
        if small_file(finder, 4194304) != original:
            raise PreparationError("An editable import finder changed during the copy.")
        rewrite_generated(finder, updated, audit)
    for path in (stage / "venv/bin").iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            beginning = stream.read(2)
        if beginning != b"#!":
            continue
        raw = small_file(path, 4194304)
        changed = raw
        for old, new in sorted(final_mappings, key=lambda pair: len(str(pair[0])), reverse=True):
            changed = changed.replace(str(old).encode(), str(new).encode())
        if str(HOME).encode() in changed:
            raise PreparationError("A copied launcher still refers to the administrator home.")
        if changed != raw:
            rewrite_generated(path, changed, audit)
    write_new(stage / "venv/pyvenv.cfg", (
        f"home = {RELEASE}/python/bin\ninclude-system-site-packages = false\n"
        "version_info = 3.14.7\n"
    ).encode())
    manifest = {"repo": "repo", "venv": "venv", "store": "python",
                "runtime": {"commands": {"hermes": "bin/hermes"},
                            "storePython": "python/bin/python3"}}
    write_new(stage / "manifest.json", json.dumps(manifest, indent=2).encode())
    # The optional new generation also admits the four separately inspected tools.
    if (stage / "python/facts.json").exists():
        raise PreparationError("The copied Python contains unexpected installation metadata.")
    tool_reports = copy_managed_tools(stage, tool_records) if with_managed_tools else []
    write_new(stage / "python/facts.json", json.dumps({"schema": 1, "packages": {
        "python": {"entry": "."}, **tool_records}}, sort_keys=True).encode())
    stamp = {"schemaVersion": 2, "commit": REVISION, "commitDate": None,
             "branch": None, "builtAt": datetime.now(timezone.utc).isoformat(),
             "dirty": False, "source": "local", "distribution": "rnr-operator",
             "updateMechanism": "external", "baseVersion": None,
             "displayVersion": "git." + REVISION[:7], "distance": None,
             "payload": "bootstrap", "tag": None}
    write_new(stage / "repo/install-stamp.json", json.dumps(stamp, indent=2).encode())
    bindir = stage / "bin"
    bindir.mkdir(mode=0o755)
    write_new(bindir / "hermes", launcher_bytes(account.pw_uid), 0o755)
    if (small_file(STATE / "facts.json") != facts
            or git_as_operator(operator, "rev-parse", "HEAD").decode().strip() != REVISION
            or (with_managed_tools and tool_metadata(TOOL_STORE / "facts.json") != tool_facts_raw)):
        raise PreparationError("The source or dependency selection changed during preparation.")
    files = snapshot_manifest(stage)
    write_new(stage / "snapshot-files.json", json.dumps(files, sort_keys=True).encode())
    write_new(stage / "preparation.json", json.dumps({
        "source_revision": REVISION, "selected_environment": str(ENVIRONMENT),
        "program_files": len(files), "runtime_qualified": False,
        "generated_install_metadata_rebased": True,
        "source_export_is_committed_revision": True,
        "editable_imports": import_reports,
        "managed_tools": tool_reports,
        "profile_configured": False, "memory_connected": False,
    }, indent=2).encode())
    os.chmod(stage, 0o755)
    os.sync()
    publish(stage, RELEASE)
    return {"complete": True, "snapshot_prepared": True, "snapshot": str(RELEASE),
            "launcher": str(RELEASE / "bin/hermes"), "source_revision": REVISION,
            "program_files": len(files), "runtime_qualified": False,
            "hermes_launched": False, "profile_configured": False,
            "memory_connected": False, "originals_preserved": True,
            "managed_tools": tool_reports,
            "tool_binaries_executed": False,
            "editable_imports": import_reports}


def main():
    global RELEASE
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--preflight", action="store_true",
                      help="Check import relocation without sudo, copies or launches.")
    parser.add_argument("--with-managed-tools", action="store_true",
                        help="Build a separate tools1 release; never replace the earlier release.")
    args = parser.parse_args()
    if args.with_managed_tools:
        if not args.apply:
            parser.error("--with-managed-tools requires --apply")
        RELEASE = RELEASE.with_name(RELEASE.name + "-tools1")
    retained = (" No files copied; originals unchanged.\n" if args.preflight else
                " Partial new snapshots are retained; originals unchanged.\n")
    try:
        report = preflight() if args.preflight else prepare(with_managed_tools=args.with_managed_tools)
    except PreparationError as error:
        parser.exit(1, "STOP: " + str(error) + retained)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, AttributeError,
            SyntaxError, subprocess.SubprocessError):
        parser.exit(1, "STOP: runtime preparation/check did not complete." + retained)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
