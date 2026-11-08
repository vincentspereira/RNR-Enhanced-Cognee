"""Content-free restricted-HOME inventory before encrypted recovery work.

No writes, SQLite connections, credential decoding, HTTP, model or subprocess.
Only regular-file headers (16 bytes) and protected public program files are read.
Unknown symlinks are counted, never followed or printed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import sys
import time


HOME = Path("/var/lib/hermes-runtime")
PROFILE_RELATIVE = ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
ARTIFACT = Path("/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-29cb9fa3400a")
PLUGIN_RELATIVE = PROFILE_RELATIVE + "/plugins/enhanced_cognee"
HASHES = {
    "__init__.py": "b221c38baab2c2915f42683e0b8e764be0a42bc3d160f9ab786fd8ea64da6a0a",
    "client.py": "8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "plugin.yaml": "c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48",
}
PRIVATE = {PROFILE_RELATIVE + "/" + name: name for name in
           (".env", "auth.json", "config.yaml", "enhanced_cognee.json")}
RECEIPTS = {"cognee-pilot-model-test.json": "original_capture",
            "cognee-pilot-capture-followup.json": "followup_capture",
            "cognee-pilot-correction.json": "correction"}


class InspectionError(RuntimeError):
    """Fixed public category; never include a private filename or contents."""


def directory(path, owners):
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in (None, *path.parts[1:]):
            if name is not None:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            info = os.fstat(descriptor)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in owners or info.st_mode & 0o022:
                raise InspectionError("recovery_directory_protection")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def preflight(approved_test):
    account = pwd.getpwuid(os.geteuid())
    if (approved_test is not True or account.pw_name != "hermes-runtime" or account.pw_uid == 0
            or Path(account.pw_dir) != HOME or os.environ.get("HOME") != str(HOME)
            or os.environ.get("HERMES_HOME") != str(HOME / PROFILE_RELATIVE)
            or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
            or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)):
        raise InspectionError("restricted_identity")
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    if (fields.get("NoNewPrivs", "").strip() != "1"
            or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))):
        raise InspectionError("restricted_process_protection")
    return account.pw_uid


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def inventory(root_fd, uid, *, max_entries=100000, seconds=45):
    """Walk pinned directory descriptors; inspect headers without SQLite side effects."""
    result = {name: 0 for name in ("entries", "directories", "regular_files", "logical_bytes", "allocated_bytes",
        "largest_file_bytes", "sqlite_databases", "largest_sqlite_bytes", "sqlite_wal_files", "sqlite_shm_files",
        "symlinks", "unknown_symlinks", "sockets", "other_special_files", "hardlinked_files",
        "nested_mounts", "unreadable_entries", "changed_entries")}
    private = {name: False for name in PRIVATE.values()}
    receipts = {name: False for name in RECEIPTS.values()}
    result.update(required_private_files=private, required_receipts=receipts, expected_provider_link=False)
    start = time.monotonic()
    device = os.fstat(root_fd).st_dev
    def walk(fd, relative="", depth=0):
        if depth > 64: raise InspectionError("recovery_depth_budget")
        before_dir = os.fstat(fd)
        try: names = os.listdir(fd)
        except OSError:
            result["unreadable_entries"] += 1
            return
        for name in names:
            result["entries"] += 1
            if result["entries"] > max_entries or time.monotonic() - start > seconds:
                raise InspectionError("recovery_inventory_budget")
            path = relative + "/" + name if relative else name
            try:
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if info.st_dev != device:
                    result["nested_mounts"] += 1
                    continue
                if stat.S_ISLNK(info.st_mode):
                    result["symlinks"] += 1
                    known = path == PLUGIN_RELATIVE and os.readlink(name, dir_fd=fd) == str(ARTIFACT)
                    result["expected_provider_link"] |= known
                    if not known: result["unknown_symlinks"] += 1
                    if stamp(info) != stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)):
                        result["changed_entries"] += 1
                elif stat.S_ISDIR(info.st_mode):
                    result["directories"] += 1
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if stamp(os.fstat(child)) != stamp(info):
                            result["changed_entries"] += 1
                            continue
                        walk(child, path, depth + 1)
                    finally: os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    result["regular_files"] += 1
                    result["logical_bytes"] += info.st_size
                    result["allocated_bytes"] += info.st_blocks * 512
                    result["largest_file_bytes"] = max(result["largest_file_bytes"], info.st_size)
                    if info.st_nlink != 1: result["hardlinked_files"] += 1
                    safe = info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
                    if path in PRIVATE: private[PRIVATE[path]] = safe
                    if path in RECEIPTS: receipts[RECEIPTS[path]] = safe
                    opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    try:
                        before = os.fstat(opened)
                        if not stat.S_ISREG(before.st_mode) or stamp(before) != stamp(info):
                            result["changed_entries"] += 1
                            continue
                        header = os.read(opened, 16)
                        if header == b"SQLite format 3\x00":
                            result["sqlite_databases"] += 1
                            result["largest_sqlite_bytes"] = max(result["largest_sqlite_bytes"], info.st_size)
                        if stamp(os.fstat(opened)) != stamp(before): result["changed_entries"] += 1
                    finally: os.close(opened)
                    if name.endswith("-wal"): result["sqlite_wal_files"] += 1
                    if name.endswith("-shm"): result["sqlite_shm_files"] += 1
                elif stat.S_ISSOCK(info.st_mode): result["sockets"] += 1
                else: result["other_special_files"] += 1
            except OSError: result["unreadable_entries"] += 1
        if stamp(before_dir) != stamp(os.fstat(fd)): result["changed_entries"] += 1
    walk(root_fd)
    return result


def protected_file(path, *, expected=None, executable=False):
    fd = directory(path.parent, {0})
    try:
        opened = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            info = os.fstat(opened)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                    or info.st_mode & 0o6022 or executable and not info.st_mode & 0o111): return False
            if expected is None: return True
            if info.st_size > 65536: return False
            raw = os.read(opened, 65537)
            return stamp(info) == stamp(os.fstat(opened)) and len(raw) == info.st_size and hashlib.sha256(raw).hexdigest() == expected
        finally: os.close(opened)
    finally: os.close(fd)


def main(*, approved_test=False):
    try:
        uid = preflight(approved_test)
        fd = directory(HOME, {0, uid})
        try:
            info = os.fstat(fd)
            if info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
                raise InspectionError("recovery_home_protection")
            data = inventory(fd, uid)
        finally: os.close(fd)
        artifact = all(protected_file(ARTIFACT / name, expected=value) for name, value in HASHES.items())
        age = {}
        for name in ("age", "age-keygen"):
            try: age[name] = protected_file(Path("/usr/local/bin") / name, executable=True)
            except OSError: age[name] = False
        complete = not any(data[k] for k in ("unreadable_entries", "changed_entries", "nested_mounts"))
        print(json.dumps({"complete": complete, "stage": "recovery_inventory", "effective_user": "hermes-runtime",
            "profile": "enhanced-cognee-pilot", "inventory": data, "protected_provider_payload_verified": artifact,
            "protected_age_tools_present": age, "private_file_reads_limited_to_headers": True, "credentials_decoded": False,
            "sqlite_connections_opened": False, "files_written": False, "model_called": False,
            "encrypted_profile_backup_created": False, "profile_recovery_qualified": False,
            "runtime_qualified": False}, indent=2))
        if not complete: raise SystemExit(1)
    except Exception as error:
        category = str(error) if isinstance(error, InspectionError) else "recovery_inventory_incomplete_review_required"
        print(json.dumps({"complete": False, "stage": "recovery_inventory", "category": category,
            "files_written": False, "model_called": False, "profile_recovery_qualified": False,
            "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None


if __name__ == "__main__":
    raise SystemExit("Use the published hash-verified restricted inspection command.")
