"""Read-only selected access checks for the approved restricted Hermes account.

No secret/program file data is read or written. Probes omit create/truncate flags.
This is selected access evidence, not full application or fleet qualification.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import stat
import sys


RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783")
TOOLS_RELEASE = RELEASE.with_name(RELEASE.name + "-tools1")
TOOLS_SELECTED = False
TOOL_BINARIES = (
    "python/ffmpeg-9.0.1-linux-x64/bin/ffmpeg",
    "python/node-26.7.0-linux-x64/bin/node",
    "python/npm-12.0.2-linux-x64/bin/npm",
    "python/ripgrep-15.2.0-linux-x64/rg",
)
ACCOUNT_HOME = Path("/var/lib/hermes-runtime")
SECRETS = tuple(Path("/etc/enhanced-cognee") / name for name in (
    "operator.json", "api.json", "worker.json", "backup.json", "age-recovery-identity.txt",
    "api-database.json", "worker-database.json", "pg_hba.conf", "qdrant.yaml",
    "valkey.conf", "valkey-users.acl",
)) + tuple(Path("/home/vincentspereira/.hermes") / name for name in (
    ".env", "profiles/enhanced-cognee-test/.env", "profiles/enhanced-cognee-test-two/.env",
))
PROGRAM_FILES = tuple(RELEASE / name for name in (
    "bin/hermes", "manifest.json", "preparation.json", "snapshot-files.json",
    "repo/hermes_bootstrap.py", "repo/hermes_cli/main.py", "venv/pyvenv.cfg",
    "venv/lib/python3.14/site-packages/__editable__.hermes_agent-0.0.0.pth",
    "venv/lib/python3.14/site-packages/__editable___hermes_agent_0_0_0_finder.py",
))
PROGRAM_DIRECTORIES = (Path("/opt"), Path("/opt/hermes-runtime"), RELEASE.parent,
                       RELEASE, RELEASE / "bin", RELEASE / "repo", RELEASE / "repo/hermes_cli",
                       RELEASE / "python", RELEASE / "python/bin", RELEASE / "venv",
                       RELEASE / "venv/lib/python3.14/site-packages")


def open_permission(path: Path, *, write=False) -> str:
    """Check permission by opening only; never read, write, truncate or create."""
    flags = (os.O_WRONLY if write else os.O_RDONLY) | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        descriptor = os.open(path, flags)
    except PermissionError:
        return "DENIED"
    except FileNotFoundError:
        return "MISSING"
    except OSError:
        return "INCONCLUSIVE"
    try:
        return "ALLOWED" if stat.S_ISREG(os.fstat(descriptor).st_mode) else "UNEXPECTED_TYPE"
    finally:
        os.close(descriptor)


def directory_protected(path: Path) -> bool:
    try:
        info = path.lstat()
        return (stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                and not os.access(path, os.W_OK, effective_ids=True))
    except OSError:
        return False


def file_protected(path: Path) -> bool:
    """Inspect only a selected regular file's metadata and effective write ACL."""
    try:
        info = path.lstat()
        return (stat.S_ISREG(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o6022 and info.st_nlink == 1
                and not os.access(path, os.W_OK, effective_ids=True))
    except OSError:
        return False


def use_tools_generation():
    """Select only the fixed admitted release; accept no caller-supplied path."""
    global RELEASE, PROGRAM_FILES, PROGRAM_DIRECTORIES, TOOLS_SELECTED
    original = RELEASE
    PROGRAM_FILES = tuple(TOOLS_RELEASE / path.relative_to(original) for path in PROGRAM_FILES)
    PROGRAM_DIRECTORIES = tuple(TOOLS_RELEASE / path.relative_to(original)
                                if path.is_relative_to(original) else path
                                for path in PROGRAM_DIRECTORIES)
    RELEASE, TOOLS_SELECTED = TOOLS_RELEASE, True


def selected_tool_paths() -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Resolve npm's program link, confine it and check all selected ancestors.

    Read only link/path metadata. Outside targets are never opened or printed.
    """
    files = [RELEASE / "python/facts.json"]
    directories = set()
    for relative in TOOL_BINARIES:
        binary = RELEASE / relative
        target = binary.resolve(strict=True)
        if target == RELEASE or not target.is_relative_to(RELEASE):
            raise RuntimeError("A selected tool target escapes the protected release.")
        files.append(target)
        for path in (binary, target):
            directories.update(path.parents)
    return tuple(dict.fromkeys(files)), tuple(sorted(directories))


def process_confined() -> bool:
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    return (fields.get("NoNewPrivs", "").strip() == "1"
            and fields.get("CapEff", "").strip() == "0000000000000000"
            and fields.get("CapAmb", "").strip() == "0000000000000000")


def check() -> dict:
    identity = pwd.getpwuid(os.geteuid())
    if (identity.pw_name != "hermes-runtime" or identity.pw_uid == 0
            or Path(identity.pw_dir) != ACCOUNT_HOME or Path.cwd() != ACCOUNT_HOME):
        raise RuntimeError("Use the approved restricted account and home for this check.")
    groups_ok = set(os.getgroups()) | {os.getegid()} == {identity.pw_gid}
    # Only self-process metadata is read; no file contents or environment values.
    confinement = process_confined()
    if not groups_ok or not confinement:
        raise RuntimeError("Restricted groups or no-new-privileges/capability checks failed.")
    files, directories = PROGRAM_FILES, PROGRAM_DIRECTORIES
    file_metadata = {}
    if TOOLS_SELECTED:
        extra_files, extra_directories = selected_tool_paths()
        files = tuple(dict.fromkeys((*files, *extra_files)))
        directories = tuple(dict.fromkeys((*directories, *extra_directories)))
        file_metadata = {path.relative_to(RELEASE).as_posix(): file_protected(path) for path in files}
    secret_access = {str(path): open_permission(path) for path in SECRETS}
    secret_write = {str(path): open_permission(path, write=True) for path in SECRETS}
    write_access = {str(path.relative_to(RELEASE)): open_permission(path, write=True)
                    for path in files}
    parents = {str(path): directory_protected(path) for path in directories}
    home = ACCOUNT_HOME.lstat()
    home_private = (stat.S_ISDIR(home.st_mode) and home.st_uid == identity.pw_uid
                    and home.st_mode & 0o777 == 0o700)
    passed = (all(value == "DENIED" for value in secret_access.values())
              and all(value == "DENIED" for value in secret_write.values())
              and all(value == "DENIED" for value in write_access.values())
              and all(parents.values()) and all(file_metadata.values()) and home_private)
    return {"complete": True, "selected_access_checks_passed": passed,
            "release": str(RELEASE), "tools_generation_selected": TOOLS_SELECTED,
            "effective_user": identity.pw_name, "uid": identity.pw_uid,
            "only_primary_group": groups_ok, "no_new_privileges_and_zero_caps": confinement,
            "home_private": home_private, "secret_read_access": secret_access,
            "secret_write_access": secret_write,
            "selected_program_write_access": write_access, "protected_program_directories": parents,
            "selected_program_metadata_protected": file_metadata,
            "secret_or_program_data_read_or_written": False, "runtime_qualified": False,
            "memory_connection_tested": False}


def main():
    if sys.argv[1:] == ["--tools-generation"]:
        use_tools_generation()
    elif len(sys.argv) != 1:
        raise SystemExit("STOP: use no arguments or only --tools-generation.")
    try:
        result = check()
    except (RuntimeError, OSError, KeyError, ValueError):
        raise SystemExit("STOP: selected access check incomplete; no secret data was read or written.") from None
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["selected_access_checks_passed"] else 1)


if __name__ == "__main__":
    main()
