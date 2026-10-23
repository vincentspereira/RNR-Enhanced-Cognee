"""Real file/archive/age round trips; host identities and API replies simulated."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import subprocess
import sys
import tarfile
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def modules():
    result = []
    for name in ("provision_pilot_access", "inspect_pilot_recovery", "backup_pilot_profile"):
        path = Path("integrations/hermes/deployment") / (name + ".py")
        spec = importlib.util.spec_from_file_location(name, path.resolve())
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result.append(module)
    return result


@pytest.fixture
def home(modules, tmp_path, monkeypatch):
    core_module, inspect_module, backup = modules
    core, inspector = vars(core_module), vars(inspect_module)
    root = tmp_path / "live-home"
    root.mkdir(mode=0o700)
    profile = root / inspector["PROFILE_RELATIVE"]
    monkeypatch.setitem(inspector, "HOME", root)
    monkeypatch.setitem(core, "HOME", root)
    monkeypatch.setitem(core, "PROFILE", profile)
    def directory(path, owners):
        return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    monkeypatch.setitem(inspector, "directory", directory)
    monkeypatch.setitem(core, "open_directory", directory)
    monkeypatch.setitem(inspector, "preflight", lambda approved: os.geteuid())
    monkeypatch.setitem(inspector, "protected_file", lambda *a, **kw: True)
    files = {name: b"PRIVATE_RECEIPT_OR_ORIGINAL_WORK" for name in inspector["RECEIPTS"]}
    files.update({inspector["PROFILE_RELATIVE"] + "/" + name: value for name, value in {
        ".env": b"OTHER=retained\nENHANCED_COGNEE_ACCESS_TOKEN=synthetic-ordinary-token\n",
        "auth.json": b'{"PRIVATE_OAUTH":"synthetic"}',
        "config.yaml": b"memory:\n  provider: enhanced_cognee\n",
        "enhanced_cognee.json": json.dumps({"base_url": "http://127.0.0.1:28080", "timeout": 10,
            "include_shared": True, "capture_policy": "selected"}).encode(), ".cognee-renewal.lock": b""}.items()})
    files["workspace/original.txt"] = b"PRIVATE_ORIGINAL_WORK"
    files["workspace/non-ascii-\u00e9.txt"] = b"PRIVATE_UTF8_FILENAME_CONTENT"
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        path.chmod(0o600 if name in inspector["PRIVATE"] or name in inspector["RECEIPTS"] or name.endswith(".lock") else 0o644)
    plugin = root / inspector["PLUGIN_RELATIVE"]
    plugin.parent.mkdir(parents=True, exist_ok=True)
    plugin.symlink_to(inspector["ARTIFACT"])
    api_calls = []
    status = {"ready": True, "tenant_id": "qualification", "project_id": "hermes_pilot",
        "subject": "hermes_pilot_runtime", "schema_version": 3, "encryption": "AES-256-GCM", "active_records": 2}
    def api(token):
        api_calls.append(token)
        return 200, status
    monkeypatch.setitem(core, "api_status", api)
    recovery = tmp_path / "recovery"
    recovery.mkdir()
    monkeypatch.setattr(backup, "RECOVERY", recovery)
    return core, inspector, backup, root, recovery, files, api_calls, status


def test_full_home_roundtrip_retains_all_generations_work_and_private_permissions(home):
    core, inspector, backup, root, recovery, files, _, _ = home
    prior = root / ".env-before-cognee-renew-retained"
    prior.write_bytes(b"PRIVATE_PREVIOUS_TOKEN")
    before = {p: (root / p).read_bytes() for p in files}
    manifest, blobs = backup.source_snapshot(inspector, os.geteuid())
    raw = backup.make_archive(manifest, blobs)
    parsed, recovered = backup.decode_archive(inspector, raw)
    assert parsed == manifest and recovered == blobs and recovered[prior.name] == b"PRIVATE_PREVIOUS_TOKEN"
    destination = recovery / ("check-" + "a" * 32)
    destination.mkdir(mode=0o700)
    backup.restore_files(inspector, destination, parsed, recovered)
    assert {p: (root / p).read_bytes() for p in files} == before
    for path, value in recovered.items():
        actual = destination / "home" / path
        assert actual.read_bytes() == value and stat.S_IMODE(actual.stat().st_mode) == 0o600
    assert (destination / "home" / inspector["PLUGIN_RELATIVE"]).is_symlink()


@pytest.mark.parametrize("mutation", ["sqlite", "wal", "shm", "unknown-link", "hardlink", "fifo", "size", "entries", "mode", "home-mode"])
def test_source_changes_and_unadmitted_file_types_fail_before_any_backup(home, monkeypatch, mutation):
    _, inspector, backup, root, recovery, _, _, _ = home
    path = root / "private-test"
    if mutation == "sqlite":
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE t(x)")
        connection.close()
    elif mutation in {"wal", "shm"}: path.with_name(path.name + "-" + mutation).write_bytes(b"PRIVATE")
    elif mutation == "unknown-link": path.symlink_to(root.parent)
    elif mutation == "hardlink":
        path.write_bytes(b"PRIVATE")
        os.link(path, root / "private-link")
    elif mutation == "fifo": os.mkfifo(path)
    elif mutation == "size": monkeypatch.setattr(backup, "MAX_DATA", 1)
    elif mutation == "entries": monkeypatch.setattr(backup, "MAX_ENTRIES", 1)
    elif mutation == "home-mode": root.chmod(0o755)
    else:
        path.write_bytes(b"PRIVATE")
        path.chmod(0o4755)
    with pytest.raises(backup.BackupError): backup.source_snapshot(inspector, os.geteuid())
    assert not list(recovery.iterdir())


def test_file_modified_during_snapshot_is_rejected(home, monkeypatch):
    _, inspector, backup, root, _, _, _, _ = home
    path = root / "a-first-file"
    path.write_bytes(b"PRIVATE")
    original = os.fdopen
    class Reader:
        def __init__(self, handle): self.handle = handle
        def __enter__(self): return self
        def __exit__(self, *a): self.handle.close()
        def read(self, size):
            value = self.handle.read(size)
            path.write_bytes(b"PRIVATE_CHANGED")
            return value
    monkeypatch.setattr(backup.os, "fdopen", lambda fd, *a, **kw: Reader(original(fd, *a, **kw)))
    with pytest.raises(backup.BackupError, match="source_changed"):
        backup.source_snapshot(inspector, os.geteuid())


def altered_archive(backup, manifest, blobs, mutation):
    source = backup.make_archive(manifest, blobs)
    out = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:") as original, tarfile.open(fileobj=out, mode="w") as changed:
        for member in original:
            raw = original.extractfile(member).read() if member.isfile() else None
            if member.name == "snapshot-manifest.json":
                value = json.loads(raw)
                if mutation == "manifest-hash":
                    next(row for row in value["entries"] if row["kind"] == "file")["sha256"] = "0" * 64
                if mutation == "manifest-scope": value["scope"] = "other"
                if mutation == "manifest-extra": value["unexpected"] = "PRIVATE"
                raw = backup.canonical(value)
                member.size = len(raw)
            if member.isfile() and member.name.startswith("home/"):
                if mutation == "traversal": member.name = "home/../../PRIVATE_OUTSIDE"
                elif mutation == "absolute": member.name = "/PRIVATE_OUTSIDE"
                elif mutation == "hardlink": member.type, member.linkname, member.size = tarfile.LNKTYPE, "outside", 0
                elif mutation == "unknown-symlink": member.type, member.linkname, member.size = tarfile.SYMTYPE, "outside", 0
                elif mutation == "file-bytes": raw = b"CHANGED"; member.size = len(raw)
            changed.addfile(member, io.BytesIO(raw) if member.isfile() else None)
            if mutation == "duplicate" and member.name == "snapshot-manifest.json": changed.addfile(member, io.BytesIO(raw))
    return out.getvalue()


@pytest.mark.parametrize("mutation", ["manifest-hash", "manifest-scope", "manifest-extra", "traversal", "absolute",
    "hardlink", "unknown-symlink", "file-bytes", "duplicate", "budget"])
def test_unsafe_or_inconsistent_tar_is_rejected_without_extracting(home, monkeypatch, mutation):
    _, inspector, backup, _, recovery, _, _, _ = home
    manifest, blobs = backup.source_snapshot(inspector, os.geteuid())
    raw = altered_archive(backup, manifest, blobs, mutation)
    if mutation == "budget": monkeypatch.setattr(backup, "MAX_ARCHIVE", 1)
    with pytest.raises(backup.BackupError): backup.decode_archive(inspector, raw)
    assert not list(recovery.iterdir())


def test_restore_refuses_nonempty_destination_without_touching_it(home):
    _, inspector, backup, _, recovery, _, _, _ = home
    manifest, blobs = backup.source_snapshot(inspector, os.geteuid())
    (recovery / "retained").write_bytes(b"PRIVATE_EXISTING")
    with pytest.raises(backup.BackupError, match="not_empty"): backup.restore_files(inspector, recovery, manifest, blobs)
    assert (recovery / "retained").read_bytes() == b"PRIVATE_EXISTING" and len(list(recovery.iterdir())) == 1


def test_archive_cannot_place_a_file_below_the_only_allowed_provider_symlink(home):
    _, inspector, backup, _, recovery, _, _, _ = home
    manifest, blobs = backup.source_snapshot(inspector, os.geteuid())
    path = inspector["PLUGIN_RELATIVE"] + "/injected"
    raw = b"PRIVATE_INJECTED"
    manifest["entries"].append({"kind": "file", "path": path, "mode": 0o600, "size": len(raw), "sha256": backup.digest(raw)})
    blobs[path] = raw
    with pytest.raises(backup.BackupError, match="parent_type_refused"):
        backup.decode_archive(inspector, backup.make_archive(manifest, blobs))
    assert not list(recovery.iterdir())


@pytest.mark.parametrize("exists", [False, True])
def test_atomic_publication_never_overwrites_an_existing_generation(modules, tmp_path, exists):
    *_, backup = modules
    (tmp_path / "partial").write_bytes(b"NEW_CIPHERTEXT")
    if exists: (tmp_path / "complete").write_bytes(b"PREVIOUS_GENERATION")
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if exists:
            with pytest.raises(backup.BackupError): backup.publish(directory, "partial", "complete")
            assert (tmp_path / "partial").read_bytes() == b"NEW_CIPHERTEXT"
            assert (tmp_path / "complete").read_bytes() == b"PREVIOUS_GENERATION"
        else:
            backup.publish(directory, "partial", "complete")
            assert (tmp_path / "complete").read_bytes() == b"NEW_CIPHERTEXT" and not (tmp_path / "partial").exists()
    finally: os.close(directory)


@pytest.mark.parametrize("mutation", [None, "expired", "scope", "count", "missing-link", "unsafe-required", "live-drift"])
def test_restricted_restore_checks_real_copied_files_and_only_ordinary_api_status(home, monkeypatch, capsys, mutation):
    core, inspector, backup, root, recovery, files, calls, status = home
    if mutation == "missing-link":
        link = root / inspector["PLUGIN_RELATIVE"]
        link.rename(link.with_name("retained-link"))
    if mutation == "unsafe-required": (root / next(iter(inspector["PRIVATE"]))).chmod(0o644)
    # Snapshot through the real child function, capturing its binary channel.
    binary = io.BytesIO()
    output = sys.stdout
    with monkeypatch.context() as context:
        context.setattr(sys, "stdout", NS(buffer=binary))
        if mutation in {"missing-link", "unsafe-required"}:
            with pytest.raises(SystemExit): backup.child(core, inspector, "snapshot", None)
        else: backup.child(core, inspector, "snapshot", None)
    if mutation in {"missing-link", "unsafe-required"}:
        assert not binary.getvalue() and "PRIVATE" not in capsys.readouterr().err
        return
    snapshot_receipt = json.loads(capsys.readouterr().err)
    assert snapshot_receipt["complete"] and not calls
    raw = binary.getvalue()
    destination = recovery / ("check-" + "b" * 32)
    destination.mkdir(mode=0o700)
    if mutation == "expired": core["api_status"] = lambda token: (401, {"PRIVATE": "API_BODY"})
    if mutation == "scope": status["project_id"] = "other"
    if mutation == "count": status["active_records"] = 3
    if mutation == "live-drift": (root / "workspace/original.txt").write_bytes(b"PRIVATE_CHANGED")
    monkeypatch.setattr(sys, "stdin", NS(buffer=io.BytesIO(raw)))
    if mutation:
        with pytest.raises(SystemExit): backup.child(core, inspector, "restore", destination)
    else: backup.child(core, inspector, "restore", destination)
    streams = capsys.readouterr()
    assert "PRIVATE" not in streams.out + streams.err and "synthetic-ordinary-token" not in streams.out + streams.err
    if mutation is None:
        receipt = json.loads(streams.out)
        assert receipt["restored_files_verified"] and receipt["live_source_preserved"] and receipt["restored_scope_status_passed"]
        assert calls == ["synthetic-ordinary-token"] and receipt["files"] == len(files)
    else: assert not streams.out


def test_real_age_encryption_signature_decryption_and_disposable_restore(home, tmp_path, monkeypatch):
    core, inspector, backup, root, recovery, files, _, _ = home
    assert Path("/usr/bin/age").is_file() and Path("/usr/bin/age-keygen").is_file(), "Install the free age test prerequisite"
    monkeypatch.setattr(backup, "AGE", Path("/usr/bin/age"))
    identity = tmp_path / "synthetic-recovery-key"
    subprocess.run(["/usr/bin/age-keygen", "-o", str(identity)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    identity.chmod(0o600)
    recipient = subprocess.check_output(["/usr/bin/age-keygen", "-y", str(identity)], text=True).strip()
    manifest, blobs = backup.source_snapshot(inspector, os.geteuid())
    raw = backup.make_archive(manifest, blobs)
    ciphertext = backup.age(["--encrypt", "--recipient", recipient], data=raw)
    assert ciphertext.startswith(b"age-encryption.org/v1\n") and b"PRIVATE_" not in ciphertext
    recovered = backup.age(["--decrypt", "--identity", str(identity)], data=ciphertext)
    assert recovered == raw
    saved, saved_blobs = backup.decode_archive(inspector, recovered)
    destination = recovery / "actual-age-restore"
    destination.mkdir(mode=0o700)
    backup.restore_files(inspector, destination, saved, saved_blobs)
    assert (destination / "home/workspace/original.txt").read_bytes() == files["workspace/original.txt"]
    signed = {"complete": True, "format": backup.FORMAT, "ciphertext_sha256": backup.digest(ciphertext), "signing_key_id": "synthetic"}
    signed["signature"] = backup.signature(signed, b"synthetic-signing-key-used-only-by-tests")
    assert signed["signature"] != backup.signature(signed | {"complete": False}, b"synthetic-signing-key-used-only-by-tests")
    assert {name: (root / name).read_bytes() for name in files} == files


@pytest.mark.parametrize("mutation", [None, "signature", "ciphertext", "format", "mode", "link"])
def test_authentication_is_required_before_any_decryption(home, tmp_path, monkeypatch, mutation):
    core, _, backup, _, _, _, _, _ = home
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    key = b"synthetic-signing-key-not-a-real-service-key"
    raw = b"age-encryption.org/v1\nSYNTHETIC_CIPHERTEXT"
    name = "synthetic.tar.age"
    (tmp_path / name).write_bytes(raw)
    (tmp_path / name).chmod(0o600)
    value = {"complete": True, "format": backup.FORMAT, "ciphertext_sha256": backup.digest(raw), "signing_key_id": "test"}
    value["signature"] = backup.signature(value, key)
    if mutation == "signature": value["signature"] = "0" * 64
    if mutation == "format": value["format"] = "other"
    if mutation == "ciphertext": (tmp_path / name).write_bytes(raw + b"CHANGED")
    if mutation == "mode": (tmp_path / name).chmod(0o644)
    if mutation == "link":
        (tmp_path / name).rename(tmp_path / "retained")
        (tmp_path / name).symlink_to(tmp_path / "retained")
    monkeypatch.setitem(core, "read_private_at", lambda *a: (backup.canonical(value), None))
    original = os.fstat
    def info(fd):
        actual = original(fd)
        return NS(**{field: 0 if field == "st_uid" else getattr(actual, field) for field in (
            "st_dev", "st_ino", "st_uid", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")})
    monkeypatch.setattr(backup.os, "fstat", info)
    try:
        if mutation:
            with pytest.raises((backup.BackupError, OSError)): backup.verify_completed(core, directory, name, key, "test")
        else: assert backup.verify_completed(core, directory, name, key, "test") == raw
    finally: os.close(directory)


def test_wrong_operator_refuses_before_key_or_profile_access(modules, monkeypatch, capsys):
    core, inspector, backup = modules
    monkeypatch.setattr(backup.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(core, "open_directory", lambda *a: pytest.fail("No protected files may be opened"))
    with pytest.raises(SystemExit): backup.main(core=vars(core), inspector=vars(inspector), sources={})
    result = json.loads(capsys.readouterr().out)
    assert not result["complete"] and result["failure_stage"] == "operator_preflight"


@pytest.mark.parametrize("mutation", [None, "extra", "duplicate", "hash", "link", "missing"])
def test_exact_three_public_sources_are_verified_before_execution(modules, mutation):
    *_, backup = modules
    payload = {name: Path(name).read_bytes() for name in backup.NAMES}
    expected = {name: backup.digest(raw) for name, raw in payload.items()}
    names = sorted(payload)
    if mutation == "extra": names += ["unexpected.py"]
    if mutation == "duplicate": names += [names[0]]
    if mutation == "missing": names.pop()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in names:
            raw = payload.get(name, b"extra = True") + (b"changed" if mutation == "hash" else b"")
            info = tarfile.TarInfo(name)
            if mutation == "link": info.type, info.linkname = tarfile.SYMTYPE, "outside"; archive.addfile(info)
            else:
                info.size = len(raw)
                archive.addfile(info, io.BytesIO(raw))
    if mutation:
        with pytest.raises(backup.BackupError): backup.verified_sources(stream.getvalue(), expected)
    else:
        for name, raw in backup.verified_sources(stream.getvalue(), expected).items():
            scope = {"__name__": "source_only"}
            exec(compile(raw, name, "exec"), scope)
            assert callable(scope["main"])


@pytest.mark.parametrize("mode", ["snapshot", "restore"])
@pytest.mark.parametrize("mutation", [None, "failed", "extra", "flag", "count", "empty", "oversize"])
def test_child_drop_identity_clean_environment_and_private_output_validation(home, monkeypatch, mode, mutation):
    core, inspector, backup, _, recovery, _, _, _ = home
    report = {"complete": True, "files": 60, "source_bytes": 205571, "entries": 104}
    if mode == "restore": report.update(restored_files_verified=True, restored_provider_binding_verified=True,
        restored_scope_status_passed=True, live_source_preserved=True)
    if mutation == "extra": report["PRIVATE"] = "SECRET"
    if mutation == "flag": report["complete"] = 1
    if mutation == "count": report["files"] = True
    if mutation == "empty": report.update(files=0, source_bytes=0, entries=0)
    key = b"UNIQUE_TEST_BACKUP_SIGNING_SECRET_NEVER_TRANSFERRED"
    sources = {name: Path(name).read_bytes() for name in backup.NAMES}
    def run(argv, **kwargs):
        assert argv[:3] == ["/usr/bin/setpriv", "--no-new-privs", "--"]
        assert kwargs["user"] == 993 and kwargs["group"] == 985 and kwargs["extra_groups"] == ()
        assert kwargs["close_fds"] is True
        assert key not in kwargs["input"] and key.decode() not in str(argv)
        assert kwargs["env"] == {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"} and kwargs["cwd"] == "/tmp"
        assert len(argv[-1].encode()) <= 120000
        compile(argv[-1], "actual-child-program", "exec")
        output = b"OPAQUE_SNAPSHOT" if mode == "snapshot" else json.dumps(report).encode()
        if mutation == "oversize": output = b"x" * (backup.MAX_ARCHIVE + 1)
        return NS(returncode=int(mutation == "failed"), stdout=output,
            stderr=json.dumps(report).encode() if mode == "snapshot" else b"")
    monkeypatch.setattr(backup.subprocess, "run", run)
    if mutation:
        with pytest.raises(backup.BackupError) as error:
            backup.run_child(core, inspector, sources, NS(pw_uid=993, pw_gid=985), mode, b"", recovery)
        assert "PRIVATE" not in str(error.value)
    else:
        _, actual = backup.run_child(core, inspector, sources, NS(pw_uid=993, pw_gid=985), mode, b"", recovery)
        assert actual == report


@pytest.mark.parametrize("mutation", [None, "encrypt", "authenticate", "decrypt", "restore", "restore-count", "existing-parent-mode"])
def test_operator_pipeline_uses_real_age_and_ciphertext_files_with_simulated_host_protection(home, tmp_path, monkeypatch, capsys, mutation):
    core, inspector, backup, _, _, _, _, _ = home
    real_uid = os.geteuid()
    key_path = tmp_path / "synthetic-age-identity"
    subprocess.run(["/usr/bin/age-keygen", "-o", str(key_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    key_path.chmod(0o600)
    recipient = subprocess.check_output(["/usr/bin/age-keygen", "-y", str(key_path)], text=True).strip()
    destination = tmp_path / "encrypted-backups"
    destination.mkdir(mode=0o700)
    recovery = tmp_path / "private-recovery"
    if mutation == "existing-parent-mode": recovery.mkdir(mode=0o700)
    release = tmp_path / "release"
    (release / "venv/bin").mkdir(parents=True)
    (release / "venv/bin/python").write_bytes(b"PUBLIC_PROGRAM")
    monkeypatch.setitem(inspector, "RELEASE", release)
    monkeypatch.setattr(backup, "DESTINATION", destination)
    monkeypatch.setattr(backup, "RECOVERY", recovery)
    monkeypatch.setattr(backup, "AGE", Path("/usr/bin/age"))
    monkeypatch.setattr(backup, "IDENTITY", key_path)
    monkeypatch.setattr(backup.os, "geteuid", lambda: 0)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Hermes")
    monkeypatch.setenv("SUDO_USER", "vincentspereira")
    monkeypatch.setattr(backup.pwd, "getpwnam", lambda name: NS(pw_name="hermes-runtime", pw_uid=real_uid, pw_gid=os.getegid(), pw_dir=str(inspector["HOME"])))
    monkeypatch.setattr(backup.os, "getgrouplist", lambda *a: [os.getegid()])
    monkeypatch.setattr(backup.os, "chown", lambda *a, **kw: None)
    fstat = os.fstat
    def root_stat(fd):
        actual = fstat(fd)
        return NS(**{field: 0 if field == "st_uid" else getattr(actual, field) for field in (
            "st_dev", "st_ino", "st_uid", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")})
    monkeypatch.setattr(backup.os, "fstat", root_stat)
    read = core["read_private_at"]
    config = {"ENHANCED_BACKUP_RECIPIENT": recipient, "ENHANCED_BACKUP_SIGNING_KEY": "PRIVATE_TEST_SIGNING_KEY_" + "x" * 32,
        "ENHANCED_BACKUP_SIGNING_KEY_ID": "synthetic-test"}
    def open_dir(path, owners):
        return os.open(tmp_path if path == Path("/etc/enhanced-cognee") else path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    monkeypatch.setitem(core, "open_directory", open_dir)
    def private(fd, name, uid):
        if name == "backup.json": return json.dumps(config).encode(), None
        return read(fd, name, uid)
    monkeypatch.setitem(core, "read_private_at", private)
    calls = []
    receipt = {"complete": True, "files": 60, "entries": 104, "source_bytes": 205571}
    def child(core, inspector, sources, account, mode, data=b"", destination=None):
        calls.append(mode)
        if mode == "snapshot": return b"PRIVATE_SYNTHETIC_ARCHIVE_CANARY", dict(receipt)
        if mutation == "restore": raise backup.BackupError("restricted_snapshot_or_restore_incomplete_preserve_evidence")
        assert data == b"PRIVATE_SYNTHETIC_ARCHIVE_CANARY"
        return b"", dict(receipt, source_bytes=1 if mutation == "restore-count" else receipt["source_bytes"],
            restored_files_verified=True, restored_provider_binding_verified=True, restored_scope_status_passed=True, live_source_preserved=True)
    monkeypatch.setattr(backup, "run_child", child)
    age = backup.age
    def crypto(args, **kwargs):
        if mutation == "encrypt" and args[0] == "--encrypt" or mutation == "decrypt" and args[0] == "--decrypt":
            raise backup.BackupError("age_operation_failed_private_details_suppressed")
        return age(args, **kwargs)
    monkeypatch.setattr(backup, "age", crypto)
    verify = backup.verify_completed
    def verified(*args):
        if mutation == "authenticate": raise backup.BackupError("profile_manifest_authentication_failed")
        return verify(*args)
    monkeypatch.setattr(backup, "verify_completed", verified)
    old_mask = os.umask(0o077)
    try:
        if mutation:
            with pytest.raises(SystemExit): backup.main(core=core, inspector=inspector, sources={})
        else: backup.main(core=core, inspector=inspector, sources={})
    finally: os.umask(old_mask)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert "PRIVATE_" not in output and report["complete"] == (mutation is None)
    assert not report["model_called"] and not report["runtime_qualified"]
    assert calls == (["snapshot", "restore"] if mutation in {None, "restore", "restore-count"} else ["snapshot"])
    if mutation is None:
        assert stat.S_IMODE(recovery.stat().st_mode) == 0o711
        assert report["signed_ciphertext_verified"] and report["decryption_roundtrip_verified"]
        assert not report["plaintext_archive_written"] and not report["recurring_profile_backup_installed"]
        assert Path(report["encrypted_backup"]).read_bytes().startswith(b"age-encryption.org/v1\n")
    else:
        assert report["encrypted_backup_created"] == (mutation != "encrypt")
        if mutation == "existing-parent-mode": assert stat.S_IMODE(recovery.stat().st_mode) == 0o700
