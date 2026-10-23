"""Manual encrypted restricted-HOME backup and non-executing disposable restore.

Only reviewed stdlib code runs as root. Source/archive traversal runs as the
restricted account. No plaintext archive file, upload, cleanup or timer change.
"""
from __future__ import annotations

import contextlib
import ctypes
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import stat
import subprocess
import sys
import tarfile
import uuid

BASE = "integrations/hermes/deployment/"
NAMES = {BASE + name for name in ("provision_pilot_access.py", "inspect_pilot_recovery.py", "backup_pilot_profile.py")}
DESTINATION = Path("/var/backups/enhanced-cognee")
RECOVERY = Path("/var/lib/hermes-runtime-recovery")
AGE = Path("/usr/local/bin/age")
IDENTITY = Path("/etc/enhanced-cognee/age-recovery-identity.txt")
MAX_DATA = 16 * 1024 * 1024
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_ENTRIES = 2048
FORMAT = "hermes-home-tar+age"


class BackupError(RuntimeError):
    """Fixed public category; no private filenames, response bodies or values."""


def verified_sources(raw, expected):
    if set(expected) != NAMES or not isinstance(raw, bytes) or len(raw) > 262144:
        raise BackupError("unapproved_backup_bundle")
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for index, member in enumerate(archive):
            if index >= 8: raise BackupError("backup_bundle_entry_budget")
            if member.isdir() and member.name.rstrip("/") in {"integrations", "integrations/hermes", "integrations/hermes/deployment"}: continue
            if member.name not in NAMES or member.name in result or not member.isfile() or not 0 < member.size <= 65536:
                raise BackupError("unexpected_backup_bundle_member")
            source = archive.extractfile(member).read(65537)
            if len(source) != member.size or digest(source) != expected[member.name]:
                raise BackupError("backup_source_hash_mismatch")
            result[member.name] = source
    if set(result) != NAMES: raise BackupError("incomplete_backup_bundle")
    return result


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def source_snapshot(inspector, uid):
    root = inspector["directory"](inspector["HOME"], {0, uid})
    if os.fstat(root).st_uid != uid or stat.S_IMODE(os.fstat(root).st_mode) != 0o700:
        os.close(root)
        raise BackupError("source_home_protection")
    entries, blobs, stamps = [], {}, {}
    used = 0
    root_stamp = inspector["stamp"](os.fstat(root))
    device = os.fstat(root).st_dev
    def names_at(fd):
        names = []
        with os.scandir(fd) as listing:
            for entry in listing:
                if len(names) >= MAX_ENTRIES: raise BackupError("source_entry_budget")
                names.append(entry.name)
        return sorted(names)
    def walk(fd, relative="", depth=0):
        nonlocal used
        if depth > 32: raise BackupError("source_depth_budget")
        before_dir = os.fstat(fd)
        names = names_at(fd)
        for name in names:
            if len(entries) >= MAX_ENTRIES: raise BackupError("source_entry_budget")
            path = relative + "/" + name if relative else name
            if len(path.encode()) > 512 or any(ord(c) < 32 for c in path):
                raise BackupError("source_name_needs_review")
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if info.st_dev != device: raise BackupError("source_mount_needs_review")
            if info.st_mode & 0o7000: raise BackupError("source_special_mode_needs_review")
            stamps[path] = inspector["stamp"](info)
            row = {"path": path, "mode": stat.S_IMODE(info.st_mode)}
            if stat.S_ISDIR(info.st_mode):
                row["kind"] = "directory"
                entries.append(row)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    if inspector["stamp"](os.fstat(child)) != stamps[path]: raise BackupError("source_changed")
                    walk(child, path, depth + 1)
                finally: os.close(child)
            elif stat.S_ISLNK(info.st_mode):
                target = os.readlink(name, dir_fd=fd)
                if path != inspector["PLUGIN_RELATIVE"] or target != str(inspector["ARTIFACT"]):
                    raise BackupError("source_link_needs_review")
                row.update(kind="provider_link", target=target)
                entries.append(row)
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1 or info.st_size > MAX_DATA - used:
                    raise BackupError("source_size_or_hardlink_needs_review")
                opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    if inspector["stamp"](os.fstat(opened)) != stamps[path]: raise BackupError("source_changed")
                    with os.fdopen(opened, "rb", closefd=False) as handle: raw = handle.read(info.st_size + 1)
                    if len(raw) != info.st_size or inspector["stamp"](os.fstat(opened)) != stamps[path]:
                        raise BackupError("source_changed")
                finally: os.close(opened)
                if raw.startswith(b"SQLite format 3\x00") or name.endswith(("-wal", "-shm")):
                    raise BackupError("database_requires_consistent_backup_method")
                used += len(raw)
                row.update(kind="file", size=len(raw), sha256=digest(raw))
                entries.append(row)
                blobs[path] = raw
            else: raise BackupError("source_special_file_needs_review")
            if inspector["stamp"](os.stat(name, dir_fd=fd, follow_symlinks=False)) != stamps[path]:
                raise BackupError("source_changed")
        if names != names_at(fd) or inspector["stamp"](os.fstat(fd)) != inspector["stamp"](before_dir):
            raise BackupError("source_changed")
    try:
        walk(root)
        # A second complete observation catches an earlier file changing after
        # its individual read. Nothing is copied silently from a live database.
        observed = set()
        def recheck(fd, relative=""):
            for name in names_at(fd):
                path = relative + "/" + name if relative else name
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if path not in stamps or inspector["stamp"](info) != stamps[path]: raise BackupError("source_changed")
                observed.add(path)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if inspector["stamp"](os.fstat(child)) != stamps[path]: raise BackupError("source_changed")
                        recheck(child, path)
                    finally: os.close(child)
        recheck(root)
        if observed != set(stamps) or inspector["stamp"](os.fstat(root)) != root_stamp: raise BackupError("source_changed")
    finally: os.close(root)
    manifest = {"version": 1, "scope": "restricted-hermes-home", "profile": inspector["PROFILE_RELATIVE"],
                "artifact": str(inspector["ARTIFACT"]), "release": str(inspector["RELEASE"]), "entries": entries}
    return manifest, blobs


def make_archive(manifest, blobs):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
        raw = canonical(manifest)
        info = tarfile.TarInfo("snapshot-manifest.json")
        info.size, info.mode = len(raw), 0o600
        archive.addfile(info, io.BytesIO(raw))
        for row in manifest["entries"]:
            info = tarfile.TarInfo("home/" + row["path"])
            if row["kind"] == "directory": info.type, info.mode = tarfile.DIRTYPE, 0o700
            elif row["kind"] == "provider_link": info.type, info.linkname = tarfile.SYMTYPE, row["target"]
            else: info.size, info.mode = row["size"], 0o600
            archive.addfile(info, io.BytesIO(blobs[row["path"]]) if row["kind"] == "file" else None)
    raw = stream.getvalue()
    if len(raw) > MAX_ARCHIVE: raise BackupError("archive_size_budget")
    return raw


def decode_archive(inspector, raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_ARCHIVE: raise BackupError("archive_size_budget")
    rows, blobs = {}, {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for index, member in enumerate(archive):
            if index > MAX_ENTRIES: raise BackupError("archive_entry_budget")
            if member.name in rows: raise BackupError("archive_duplicate_member")
            if member.name == "snapshot-manifest.json":
                if not member.isfile() or not 0 < member.size <= 1024 * 1024: raise BackupError("archive_manifest_shape")
                manifest = json.loads(archive.extractfile(member).read())
                rows[member.name] = None
                continue
            path = PurePosixPath(member.name)
            if (not member.name.startswith("home/") or str(path) != member.name or ".." in path.parts
                    or len(member.name.encode()) > 517 or any(ord(c) < 32 for c in member.name)):
                raise BackupError("archive_path_refused")
            relative = member.name[5:]
            if not relative: raise BackupError("archive_path_refused")
            if member.isdir(): row = {"kind": "directory"}
            elif member.issym() and relative == inspector["PLUGIN_RELATIVE"] and member.linkname == str(inspector["ARTIFACT"]):
                row = {"kind": "provider_link", "target": member.linkname}
            elif member.isfile() and 0 <= member.size <= MAX_DATA:
                blob = archive.extractfile(member).read(member.size + 1)
                if len(blob) != member.size: raise BackupError("archive_file_truncated")
                blobs[relative] = blob
                row = {"kind": "file", "size": len(blob), "sha256": digest(blob)}
            else: raise BackupError("archive_member_type_refused")
            rows[member.name] = row
    expected = {"version": 1, "scope": "restricted-hermes-home", "profile": inspector["PROFILE_RELATIVE"],
                "artifact": str(inspector["ARTIFACT"]), "release": str(inspector["RELEASE"])}
    if ("snapshot-manifest.json" not in rows or not isinstance(manifest, dict)
            or set(manifest) != set(expected) | {"entries"}
            or any(type(manifest.get(k)) is not type(v) or manifest.get(k) != v for k, v in expected.items())
            or not isinstance(manifest["entries"], list) or len(manifest["entries"]) > MAX_ENTRIES):
        raise BackupError("archive_manifest_shape")
    seen = set()
    for row in manifest["entries"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str): raise BackupError("archive_manifest_shape")
        path = row["path"]
        actual = rows.get("home/" + path)
        if (path in seen or actual is None or type(row.get("mode")) is not int or not 0 <= row["mode"] <= 0o777
                or row != dict(actual, path=path, mode=row["mode"])):
            raise BackupError("archive_manifest_mismatch")
        seen.add(path)
    if len(rows) != len(seen) + 1 or sum(map(len, blobs.values())) > MAX_DATA:
        raise BackupError("archive_manifest_mismatch")
    for path in seen:
        for parent in PurePosixPath(path).parents:
            if str(parent) != "." and rows.get("home/" + str(parent), {}).get("kind") != "directory":
                raise BackupError("archive_parent_type_refused")
    return manifest, blobs


def restore_files(inspector, destination, manifest, blobs):
    root = inspector["directory"](destination, {0, os.geteuid()})
    old_mask = os.umask(0o077)
    try:
        if os.listdir(root): raise BackupError("restore_destination_not_empty")
        os.mkdir("home", 0o700, dir_fd=root)
        for row in sorted(manifest["entries"], key=lambda value: (value["path"].count("/"), value["kind"] != "directory", value["path"])):
            parts = PurePosixPath("home/" + row["path"]).parts
            fd = os.dup(root)
            try:
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = child
                if row["kind"] == "directory": os.mkdir(parts[-1], 0o700, dir_fd=fd)
                elif row["kind"] == "provider_link": os.symlink(row["target"], parts[-1], dir_fd=fd)
                else:
                    opened = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                    with os.fdopen(opened, "wb") as handle:
                        os.fchmod(handle.fileno(), 0o600)
                        handle.write(blobs[row["path"]])
                        handle.flush()
                        os.fsync(handle.fileno())
                os.fsync(fd)
            finally: os.close(fd)
        # Re-read every recovered file, without importing or executing it.
        for row in manifest["entries"]:
            parts = PurePosixPath("home/" + row["path"]).parts
            fd = os.dup(root)
            try:
                for part in parts[:-1]:
                    opened = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = opened
                info = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
                if info.st_uid != os.geteuid(): raise BackupError("restored_owner_mismatch")
                if row["kind"] == "file":
                    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
                        raise BackupError("restored_file_mismatch")
                    opened = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    with os.fdopen(opened, "rb") as handle:
                        if handle.read(MAX_DATA + 1) != blobs[row["path"]]: raise BackupError("restored_file_mismatch")
                elif row["kind"] == "directory":
                    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700: raise BackupError("restored_directory_mismatch")
                elif not stat.S_ISLNK(info.st_mode) or os.readlink(parts[-1], dir_fd=fd) != str(inspector["ARTIFACT"]):
                    raise BackupError("restored_provider_link_mismatch")
            finally: os.close(fd)
    finally:
        os.close(root)
        os.umask(old_mask)


def child(core, inspector, mode, destination):
    try:
        uid = inspector["preflight"](True)
        if not all(inspector["protected_file"](inspector["ARTIFACT"] / name, expected=value) for name, value in inspector["HASHES"].items()):
            raise BackupError("protected_provider_mismatch")
        directory = core["open_directory"](core["PROFILE"], {0, uid})
        try:
            lock = os.open(".cognee-renewal.lock", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                core["read_private_fd"](lock, uid)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                manifest, blobs = source_snapshot(inspector, uid)
                if not set(inspector["PRIVATE"] | inspector["RECEIPTS"]).issubset(blobs):
                    raise BackupError("required_source_file_missing")
                for name in inspector["PRIVATE"] | inspector["RECEIPTS"]:
                    if next(row for row in manifest["entries"] if row["path"] == name)["mode"] != 0o600:
                        raise BackupError("required_source_file_permissions")
                if not any(row["path"] == inspector["PLUGIN_RELATIVE"] and row["kind"] == "provider_link" for row in manifest["entries"]):
                    raise BackupError("required_provider_link_missing")
                counts = {"files": len(blobs), "source_bytes": sum(map(len, blobs.values())),
                          "entries": len(manifest["entries"])}
                if mode == "snapshot":
                    raw = make_archive(manifest, blobs)
                    sys.stdout.buffer.write(raw)
                    sys.stdout.buffer.flush()
                    print(json.dumps(dict(complete=True, **counts)), file=sys.stderr)
                elif mode == "restore":
                    if not re.fullmatch(re.escape(str(RECOVERY)) + r"/check-[0-9a-f]{32}", str(destination)):
                        raise BackupError("unapproved_restore_destination")
                    raw = sys.stdin.buffer.read(MAX_ARCHIVE + 1)
                    saved, saved_blobs = decode_archive(inspector, raw)
                    if saved != manifest or saved_blobs != blobs: raise BackupError("live_source_changed_since_snapshot")
                    restore_files(inspector, destination, saved, saved_blobs)
                    profile = destination / "home" / inspector["PROFILE_RELATIVE"]
                    profile_fd = core["open_directory"](profile, {0, uid})
                    try:
                        restored_settings = {name: core["read_private_at"](profile_fd, name, uid)[0]
                                             for name in ("config.yaml", "enhanced_cognee.json", ".env")}
                    finally: os.close(profile_fd)
                    if restored_settings["config.yaml"] != b"memory:\n  provider: enhanced_cognee\n":
                        raise BackupError("restored_provider_settings_mismatch")
                    settings = json.loads(restored_settings["enhanced_cognee.json"])
                    if settings != {"base_url": "http://127.0.0.1:28080", "timeout": 10, "include_shared": True, "capture_policy": "selected"}:
                        raise BackupError("restored_provider_settings_mismatch")
                    from dotenv.parser import parse_stream
                    rows = list(parse_stream(io.StringIO(restored_settings[".env"].decode("utf-8"))))
                    tokens = [row.value for row in rows if row.key == core["TOKEN_NAME"]]
                    if any(row.error for row in rows) or len(tokens) != 1: raise BackupError("restored_credential_assignment")
                    code, status = core["api_status"](tokens[0])
                    if (code != 200 or not isinstance(status, dict) or status.get("ready") is not True
                            or any(status.get(field) != core["IDENTITY"][claim] for field, claim in (
                                ("tenant_id", "tenant"), ("project_id", "project_id"), ("subject", "sub")))
                            or status.get("schema_version") != 3 or status.get("encryption") != "AES-256-GCM"
                            or type(status.get("active_records")) is not int or status["active_records"] != 2):
                        raise BackupError("restored_scoped_access_not_accepted")
                    if source_snapshot(inspector, uid) != (manifest, blobs): raise BackupError("live_source_changed_during_restore")
                    print(json.dumps(dict(complete=True, restored_files_verified=True,
                        restored_provider_binding_verified=True, restored_scope_status_passed=True,
                        live_source_preserved=True, **counts)))
                else: raise BackupError("unapproved_child_mode")
            finally: os.close(lock)
        finally: os.close(directory)
    except Exception:
        print(json.dumps({"complete": False, "category": "restricted_profile_snapshot_or_restore_incomplete"}), file=sys.stderr)
        raise SystemExit(1) from None


def run_child(core, inspector, sources, account, mode, data=b"", destination=None):
    code = "import sys\n"
    for variable, name in (("core", "provision_pilot_access.py"), ("inspector", "inspect_pilot_recovery.py"), ("backup", "backup_pilot_profile.py")):
        code += variable + "={'__name__':'reviewed_definitions'}\nexec(compile(" + repr(sources[BASE + name]) + ",'reviewed-source','exec')," + variable + ")\n"
    code += "backup['child'](core,inspector," + repr(mode) + "," + ("None" if destination is None else "__import__('pathlib').Path(" + repr(str(destination)) + ")") + ")\n"
    if len(code.encode()) > 120000: raise BackupError("child_program_budget")
    result = subprocess.run(["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env", "-i",
        "HOME=" + str(inspector["HOME"]), "USER=hermes-runtime", "LOGNAME=hermes-runtime",
        "HERMES_HOME=" + str(inspector["HOME"] / inspector["PROFILE_RELATIVE"]),
        "PATH=/usr/bin:/bin", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1",
        str(inspector["RELEASE"] / "venv/bin/python"), "-I", "-B", "-c", code],
        input=data, user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd="/tmp",
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, close_fds=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if result.returncode or len(result.stderr) > 4096 or len(result.stdout) > MAX_ARCHIVE:
        raise BackupError("restricted_snapshot_or_restore_incomplete_preserve_evidence")
    report = json.loads(result.stderr if mode == "snapshot" else result.stdout)
    keys = {"complete", "files", "source_bytes", "entries"}
    if mode == "restore": keys |= {"restored_files_verified", "restored_provider_binding_verified", "restored_scope_status_passed", "live_source_preserved"}
    if (not isinstance(report, dict) or set(report) != keys or report.get("complete") is not True
            or any(type(report.get(k)) is not int or not 0 <= report[k] <= limit for k, limit in (
                ("files", MAX_ENTRIES), ("source_bytes", MAX_DATA), ("entries", MAX_ENTRIES)))
            or mode == "restore" and any(report.get(k) is not True for k in keys - {"files", "source_bytes", "entries"})):
        raise BackupError("unexpected_child_receipt_private_output_suppressed")
    if report["files"] < len(inspector["PRIVATE"]) + len(inspector["RECEIPTS"]) or report["entries"] <= report["files"]:
        raise BackupError("unexpected_child_receipt_private_output_suppressed")
    return result.stdout if mode == "snapshot" else b"", report


def signature(manifest, key):
    return hmac.new(key, canonical({k: v for k, v in manifest.items() if k != "signature"}), hashlib.sha256).hexdigest()


def verify_completed(core, directory, name, key, key_id):
    raw, _ = core["read_private_at"](directory, name + ".json", 0)
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get("format") != FORMAT or value.get("complete") is not True
            or value.get("signing_key_id") != key_id or not isinstance(value.get("signature"), str)
            or not hmac.compare_digest(value["signature"], signature(value, key))):
        raise BackupError("profile_manifest_authentication_failed")
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or info.st_size > MAX_ARCHIVE + 1048576:
            raise BackupError("profile_ciphertext_protection_failed")
        with os.fdopen(fd, "rb", closefd=False) as handle: ciphertext = handle.read(MAX_ARCHIVE + 1048577)
        if (len(ciphertext) != info.st_size or not ciphertext.startswith(b"age-encryption.org/v1\n")
                or digest(ciphertext) != value.get("ciphertext_sha256") or core["fingerprint"](info) != core["fingerprint"](os.fstat(fd))):
            raise BackupError("profile_ciphertext_verification_failed")
    finally: os.close(fd)
    return ciphertext


def publish(directory, source, target):
    rename = ctypes.CDLL(None, use_errno=True).renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(directory, os.fsencode(source), directory, os.fsencode(target), 1) != 0:
        raise BackupError("backup_publication_refused_existing_generation_preserved")
    os.fsync(directory)


def age(arguments, *, data, output=subprocess.PIPE):
    result = subprocess.run([str(AGE), *arguments], input=data, stdout=output, stderr=subprocess.PIPE,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, timeout=60)
    if result.returncode: raise BackupError("age_operation_failed_private_details_suppressed")
    if output == subprocess.PIPE and len(result.stdout) > MAX_ARCHIVE: raise BackupError("decrypted_archive_budget")
    return result.stdout


def main(*, core, inspector, sources):
    phase, completed = "operator_preflight", False
    backup_path = recovery_path = None
    try:
        if os.geteuid() != 0 or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes" or os.environ.get("SUDO_USER") != "vincentspereira":
            raise BackupError("approved_human_operator_required")
        account = pwd.getpwnam("hermes-runtime")
        if account.pw_uid == 0 or Path(account.pw_dir) != inspector["HOME"] or set(os.getgrouplist(account.pw_name, account.pw_gid)) != {account.pw_gid}:
            raise BackupError("restricted_account_protection")
        python = (inspector["RELEASE"] / "venv/bin/python").resolve(strict=True)
        if (not python.is_relative_to(inspector["RELEASE"]) or not inspector["protected_file"](python, executable=True)
                or not inspector["protected_file"](AGE, executable=True) or not inspector["protected_file"](IDENTITY)):
            raise BackupError("protected_program_or_recovery_identity")
        config_fd = core["open_directory"](Path("/etc/enhanced-cognee"), {0})
        try:
            config = json.loads(core["read_private_at"](config_fd, "backup.json", 0)[0])
            core["read_private_at"](config_fd, IDENTITY.name, 0)  # Enforce root-only recovery-file mode too.
        finally: os.close(config_fd)
        recipient, key, key_id = (config[k] for k in ("ENHANCED_BACKUP_RECIPIENT", "ENHANCED_BACKUP_SIGNING_KEY", "ENHANCED_BACKUP_SIGNING_KEY_ID"))
        if (not isinstance(recipient, str) or not re.fullmatch(r"age1[0-9a-z]{20,100}", recipient)
                or not isinstance(key, str) or len(key.encode()) < 32 or not isinstance(key_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id)):
            raise BackupError("backup_configuration_needs_review")
        key = key.encode()
        directory = core["open_directory"](DESTINATION, {0})
        try:
            if stat.S_IMODE(os.fstat(directory).st_mode) != 0o700: raise BackupError("backup_directory_protection")
            phase = "restricted_snapshot"
            plaintext, receipt = run_child(core, inspector, sources, account, "snapshot")
            generation = uuid.uuid4().hex
            name = "hermes_profile_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + generation[:8] + ".tar.age"
            partial = "." + name + ".partial"
            phase = "encrypted_snapshot"
            fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(fd, "wb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                age(["--encrypt", "--recipient", recipient], data=plaintext, output=handle)
                handle.flush()
                os.fsync(handle.fileno())
            publish(directory, partial, name)
            # Only ciphertext is persisted by the operator. Source filenames and
            # hashes stay inside the encrypted internal manifest.
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            with os.fdopen(fd, "rb") as handle: ciphertext_hash = hashlib.file_digest(handle, "sha256").hexdigest()
            manifest = {"format": FORMAT, "complete": True, "ciphertext_sha256": ciphertext_hash,
                "created_utc": datetime.now(timezone.utc).isoformat(), "signing_key_id": key_id,
                "plaintext_archive_written": False, "scope": "restricted-hermes-home",
                "source_files": receipt["files"], "source_bytes": receipt["source_bytes"]}
            manifest["signature"] = signature(manifest, key)
            core["create_private_at"](directory, name + ".json", canonical(manifest))
            os.fsync(directory)
            backup_path, completed = str(DESTINATION / name), True
            phase = "authenticated_decryption"
            ciphertext = verify_completed(core, directory, name, key, key_id)
            recovered = age(["--decrypt", "--identity", str(IDENTITY)], data=ciphertext)
            if recovered != plaintext: raise BackupError("encrypted_roundtrip_mismatch")
        finally: os.close(directory)
        phase = "disposable_restore"
        parent = core["open_directory"](RECOVERY.parent, {0})
        created_parent = False
        try:
            try:
                os.mkdir(RECOVERY.name, 0o711, dir_fd=parent)
                created_parent = True
            except FileExistsError: pass
        finally: os.close(parent)
        parent = core["open_directory"](RECOVERY, {0})
        try:
            if created_parent: os.fchmod(parent, 0o711)
            if stat.S_IMODE(os.fstat(parent).st_mode) != 0o711: raise BackupError("recovery_parent_protection")
            leaf = "check-" + generation
            os.mkdir(leaf, 0o700, dir_fd=parent)
            leaf_fd = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                os.fchmod(leaf_fd, 0o700)
                os.fchown(leaf_fd, account.pw_uid, account.pw_gid)
            finally: os.close(leaf_fd)
            os.fsync(parent)
        finally: os.close(parent)
        recovery_path = str(RECOVERY / leaf)
        _, restored = run_child(core, inspector, sources, account, "restore", recovered, Path(recovery_path))
        if any(restored[k] != receipt[k] for k in ("files", "source_bytes", "entries")):
            raise BackupError("restored_inventory_mismatch")
        print(json.dumps({"complete": True, "stage": "profile_backup_restore", "profile": "enhanced-cognee-pilot",
            "encrypted_backup": backup_path, "disposable_restore": recovery_path,
            "files_verified": restored["files"], "source_bytes": restored["source_bytes"],
            "signed_ciphertext_verified": True, "decryption_roundtrip_verified": True,
            "restored_files_and_private_permissions_verified": True, "restored_provider_binding_verified": True,
            "restored_scope_status_passed": True, "live_source_preserved": True,
            "plaintext_archive_written": False, "model_called": False, "memory_records_written": False,
            "native_restored_hermes_launched": False, "recurring_profile_backup_installed": False,
            "windows_collection_qualified": False, "runtime_qualified": False}, indent=2))
    except Exception:
        print(json.dumps({"complete": False, "stage": "profile_backup_restore", "failure_stage": phase,
            "category": "profile_backup_or_restore_incomplete_preserve_evidence", "encrypted_backup_created": completed,
            "encrypted_backup": backup_path, "disposable_restore": recovery_path,
            "model_called": False, "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None


if __name__ == "__main__":
    raise SystemExit("Use the published hash-verified human-operator backup bundle.")
