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
import tempfile
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
    monkeypatch.setattr(backup, "open_recovery_directory", directory)
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
    recovery.chmod(0o700)
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


@pytest.mark.parametrize("mode", ["snapshot", "restore", "inspect"])
@pytest.mark.parametrize("mutation", [None, "failed", "extra", "flag", "count", "empty", "oversize"])
def test_child_drop_identity_clean_environment_and_private_output_validation(home, monkeypatch, mode, mutation):
    core, inspector, backup, _, recovery, _, _, _ = home
    report = {"complete": True, "files": 60, "source_bytes": 205571, "entries": 104}
    if mode in {"restore", "inspect"}: report.update(restored_files_verified=True, restored_provider_binding_verified=True,
        restored_scope_status_passed=True, live_source_preserved=True)
    if mode == "inspect": report.update(files_written=False,
        checks=dict.fromkeys(backup.CHECK_FLAGS, True) | {"api_http_status": 200})
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


@pytest.mark.parametrize("mutation", [None, "encrypt", "authenticate", "decrypt", "restore", "restore-count", "existing-parent-mode", "daily", "scheduled"])
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
        if mutation in {"daily", "scheduled"} and name == key_path.name:
            pytest.fail('Daily backup must not read the recovery identity')
        return read(fd, name, uid)
    monkeypatch.setitem(core, "read_private_at", private)
    calls = []
    receipt = {"complete": True, "files": 60, "entries": 104, "source_bytes": 205571}
    def child(core, inspector, sources, account, mode, data=b"", destination=None, **options):
        assert options == ({'external_identity': True} if mutation == 'scheduled' else {})
        calls.append(mode)
        if mode == "snapshot": return b"PRIVATE_SYNTHETIC_ARCHIVE_CANARY", dict(receipt)
        if mutation == "restore": raise backup.BackupError("restricted_snapshot_or_restore_incomplete_preserve_evidence")
        assert data == b"PRIVATE_SYNTHETIC_ARCHIVE_CANARY"
        return b"", dict(receipt, source_bytes=1 if mutation == "restore-count" else receipt["source_bytes"],
            restored_files_verified=True, restored_provider_binding_verified=True, restored_scope_status_passed=True, live_source_preserved=True)
    monkeypatch.setattr(backup, "run_child", child)
    age = backup.age
    def crypto(args, **kwargs):
        if mutation in {"daily", "scheduled"}: assert args[0] == '--encrypt'
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
        if mutation == 'scheduled': monkeypatch.delenv('SUDO_USER')
        if mutation in {'daily', 'scheduled'}:
            backup.main(core=core, inspector=inspector, sources={}, backup_only=True, scheduled_backup=mutation == 'scheduled')
        elif mutation:
            with pytest.raises(SystemExit): backup.main(core=core, inspector=inspector, sources={})
        else: backup.main(core=core, inspector=inspector, sources={})
    finally: os.umask(old_mask)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert "PRIVATE_" not in output and report["complete"] == (mutation in {None, 'daily', 'scheduled'})
    assert not report["model_called"] and not report["runtime_qualified"]
    assert calls == (["snapshot", "restore"] if mutation in {None, "restore", "restore-count"} else ["snapshot"])
    if mutation is None:
        assert stat.S_IMODE(recovery.stat().st_mode) == 0o711
        assert report["signed_ciphertext_verified"] and report["decryption_roundtrip_verified"]
        assert not report["plaintext_archive_written"] and not report["recurring_profile_backup_installed"]
        assert Path(report["encrypted_backup"]).read_bytes().startswith(b"age-encryption.org/v1\n")
    elif mutation in {'daily', 'scheduled'}:
        assert report['stage'] == 'profile_backup_only'
        assert report['recovery_identity_read'] is False and report['decryption_tested'] is False
        assert report['disposable_restore_created'] is False and not recovery.exists()
        assert report['signed_ciphertext_verified'] is True
        assert len(list(destination.glob('*.tar.age'))) == 1
    else:
        assert report["encrypted_backup_created"] == (mutation != "encrypt")
        if mutation == "existing-parent-mode": assert stat.S_IMODE(recovery.stat().st_mode) == 0o700


def test_real_traversal_only_parent_reproduces_old_failure_and_preserves_protection(modules):
    _, inspector, backup = modules
    # Use a protected ancestor chain, not /tmp (which the guard must refuse).
    with tempfile.TemporaryDirectory(prefix='.cognee-permission-test-', dir=Path.home()) as raw:
        parent = Path(raw)
        leaf = parent / 'private-copy'
        leaf.mkdir(mode=0o700)
        parent.chmod(0o111)  # Same effective access as another user's root:root 0711.
        try:
            with pytest.raises(PermissionError):
                inspector.directory(leaf, {0, os.geteuid()})
            fd = backup.open_recovery_directory(leaf, {0, os.geteuid()})
            try:
                assert os.listdir(fd) == []
                assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o700
            finally: os.close(fd)
            value = b'synthetic recovered settings'
            manifest = {'entries': [{'path': 'config', 'kind': 'file', 'mode': 0o600,
                                     'size': len(value), 'sha256': backup.digest(value)}]}
            backup.restore_files(vars(inspector), leaf, manifest, {'config': value})
            backup.verify_restore(vars(inspector), leaf, manifest, {'config': value})
            assert (leaf / 'home/config').read_bytes() == value
            assert stat.S_IMODE(parent.stat().st_mode) == 0o111
            assert stat.S_IMODE(leaf.stat().st_mode) == 0o700
            with pytest.raises(PermissionError): os.listdir(parent)
        finally: parent.chmod(0o700)


@pytest.mark.parametrize('mutation', ['writable', 'symlink', 'owner', 'relative', 'traversal'])
def test_path_only_traversal_keeps_ancestor_guards(modules, mutation):
    *_, backup = modules
    with tempfile.TemporaryDirectory(prefix='.cognee-permission-test-', dir=Path.home()) as raw:
        parent = Path(raw)
        leaf = parent / 'copy'
        leaf.mkdir(mode=0o700)
        selected = leaf
        owners = {0, os.geteuid()}
        if mutation == 'writable': parent.chmod(0o777)
        if mutation == 'symlink':
            selected = parent / 'redirect'
            selected.symlink_to(leaf, target_is_directory=True)
        if mutation == 'owner': owners = set()
        if mutation == 'relative': selected = Path('relative')
        if mutation == 'traversal': selected = parent / '..' / parent.name / 'copy'
        try:
            with pytest.raises((backup.BackupError, OSError)):
                backup.open_recovery_directory(selected, owners)
        finally: parent.chmod(0o700)


@pytest.mark.parametrize('mutation', [None, 'empty', 'partial', 'extra', 'file-mode', 'expired', 'live-drift', 'private-error'])
def test_retained_inspection_reads_without_reextracting_or_changing_source(home, monkeypatch, capsys, mutation):
    core, inspector, backup, root, recovery, files, calls, status = home
    manifest, blobs = backup.source_snapshot(inspector, os.geteuid())
    archive = backup.make_archive(manifest, blobs)
    destination = recovery / ('check-' + 'c' * 32)
    destination.mkdir(mode=0o700)
    if mutation != 'empty': backup.restore_files(inspector, destination, manifest, blobs)
    recovered = destination / 'home/workspace/original.txt'
    if mutation == 'partial': recovered.unlink()  # Disposable synthetic fixture only.
    if mutation == 'extra': (destination / 'unexpected').write_bytes(b'PRIVATE_EXTRA')
    if mutation == 'file-mode': recovered.chmod(0o644)
    if mutation == 'expired': core['api_status'] = lambda token: (401, {})
    if mutation == 'private-error':
        def private_error(token): raise PermissionError('PRIVATE_RAW_SECRET_AND_FILENAME')
        core['api_status'] = private_error
    if mutation == 'live-drift': (root / 'workspace/original.txt').write_bytes(b'PRIVATE_NEW_LIVE_WORK')
    before = backup.source_snapshot(inspector, os.geteuid())
    def no_restore(*a, **kw): pytest.fail('Inspection must not write or re-extract')
    monkeypatch.setattr(backup, 'restore_files', no_restore)
    monkeypatch.setattr(sys, 'stdin', NS(buffer=io.BytesIO(archive)))
    failure = mutation not in {None, 'live-drift'}
    if failure:
        with pytest.raises(SystemExit): backup.child(core, inspector, 'inspect', destination)
    else: backup.child(core, inspector, 'inspect', destination)
    output = capsys.readouterr()
    assert 'PRIVATE' not in output.out + output.err and 'synthetic-ordinary-token' not in output.out + output.err
    result = json.loads(output.err if failure else output.out)
    assert result['complete'] is not failure
    checks = result['checks']
    assert checks['archive_validated'] is True
    assert checks['archive_matches_live_source'] is (mutation != 'live-drift')
    if mutation in {'empty', 'partial', 'extra'}:
        assert result['phase'] == 'restore_verify' and result['category'] == 'restored_membership_mismatch'
        assert checks['recovered_files_verified'] is False
    if mutation == 'expired':
        assert result['phase'] == 'restored_api_status' and checks['api_http_status'] == 401
        assert checks['recovered_files_verified'] and checks['recovered_settings_verified']
    if mutation == 'private-error':
        assert result['phase'] == 'restored_api_status' and result['category'] == 'permission_denied'
    assert backup.source_snapshot(inspector, os.geteuid()) == before
    if not failure: assert result['files_written'] is False


@pytest.mark.parametrize('mutation', [None, 'extra-field', 'private-phase', 'private-category', 'private-check', 'numeric-bool', 'raw-error'])
def test_parent_returns_only_allowlisted_child_failure_details(home, monkeypatch, mutation):
    core, inspector, backup, _, recovery, _, _, _ = home
    checks = dict.fromkeys(backup.CHECK_FLAGS | {'api_http_status'})
    report = dict(complete=False, phase='restore_verify', category='entry_missing', checks=checks)
    if mutation == 'extra-field': report['PRIVATE'] = 'SECRET'
    if mutation == 'private-phase': report['phase'] = 'PRIVATE_PATH'
    if mutation == 'private-category': report['category'] = 'PRIVATE_VALUE'
    if mutation == 'private-check': checks['PRIVATE'] = 'SECRET'
    if mutation == 'numeric-bool': checks['archive_validated'] = 1
    raw = b'PRIVATE_EXCEPTION_AND_KEY' if mutation == 'raw-error' else json.dumps(report).encode()
    monkeypatch.setattr(backup.subprocess, 'run', lambda *a, **kw: NS(returncode=1, stdout=b'', stderr=raw))
    with pytest.raises(backup.BackupError) as failure:
        backup.run_child(core, inspector, {name: Path(name).read_bytes() for name in backup.NAMES},
                         NS(pw_uid=993, pw_gid=985), 'inspect', b'opaque', recovery)
    assert failure.value.diagnostics == (report if mutation is None else None)
    assert 'PRIVATE' not in str(failure.value)


@pytest.mark.parametrize('mutation', [None, 'authentication', 'decrypt', 'child-failure', 'parent-mode'])
@pytest.mark.parametrize('restore_existing', [False, True])
def test_operator_inspects_or_restores_fixed_generation_without_reencrypting(home, monkeypatch, capsys, mutation, restore_existing):
    core, inspector, backup, _, recovery, _, _, _ = home
    real_uid = os.geteuid()
    release = recovery.parent / 'public-test-release'
    (release / 'venv/bin').mkdir(parents=True)
    (release / 'venv/bin/python').write_bytes(b'PUBLIC_TEST_INTERPRETER')
    monkeypatch.setitem(inspector, 'RELEASE', release)
    recovery.chmod(0o711 if mutation != 'parent-mode' else 0o700)
    retained = recovery / backup.FAILED_RESTORE
    retained.mkdir(mode=0o700)
    (retained / 'retained-evidence').write_bytes(b'PRIVATE_FAILED_ATTEMPT')
    original_mkdir = os.mkdir
    original_fchown = os.fchown
    created = []
    monkeypatch.setattr(backup.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes')
    monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    monkeypatch.setattr(backup.pwd, 'getpwnam', lambda name: NS(pw_name='hermes-runtime', pw_uid=real_uid,
        pw_gid=os.getegid(), pw_dir=str(inspector['HOME'])))
    monkeypatch.setattr(backup.os, 'getgrouplist', lambda *a: [os.getegid()])
    config = {'ENHANCED_BACKUP_RECIPIENT': 'age1' + 'x' * 30, 'ENHANCED_BACKUP_SIGNING_KEY': 'x' * 32,
              'ENHANCED_BACKUP_SIGNING_KEY_ID': 'synthetic'}
    monkeypatch.setitem(core, 'read_private_at', lambda fd, name, uid: (json.dumps(config).encode(), None))
    def open_dir(path, owners):
        # These host-root metadata checks are simulated; path traversal is
        # exercised independently by the real permission regression above.
        return os.open(recovery if path == backup.RECOVERY else inspector['HOME'], os.O_RDONLY | os.O_DIRECTORY)
    monkeypatch.setitem(core, 'open_directory', open_dir)
    paths = []
    def verify(core, fd, name, key, kid):
        paths.append(name)
        assert name == backup.FAILED_BACKUP
        if mutation == 'authentication': raise backup.BackupError('profile_manifest_authentication_failed')
        return b'authenticated-ciphertext'
    monkeypatch.setattr(backup, 'verify_completed', verify)
    def crypto(args, *, data, **kwargs):
        assert args == ['--decrypt', '--identity', str(backup.IDENTITY)]
        assert data == b'authenticated-ciphertext'
        if mutation == 'decrypt': raise backup.BackupError('age_operation_failed_private_details_suppressed')
        return b'PRIVATE_ARCHIVE_ONLY_IN_RAM'
    monkeypatch.setattr(backup, 'age', crypto)
    checks = dict.fromkeys(backup.CHECK_FLAGS, True) | {'api_http_status': 200}
    def inspect(core, inspector, sources, account, mode, data, destination):
        if restore_existing:
            assert mode == 'restore' and destination != retained and destination.parent == recovery
            assert destination.is_dir() and not list(destination.iterdir())
            assert stat.S_IMODE(destination.stat().st_mode) == 0o700
        else: assert mode == 'inspect' and destination == retained
        assert data == b'PRIVATE_ARCHIVE_ONLY_IN_RAM'
        if mutation == 'child-failure':
            raise backup.BackupError('restricted_failure', diagnostics=dict(complete=False,
                phase='restore_verify', category='restored_membership_mismatch', checks=checks))
        return b'', dict(checks=checks, files=60, source_bytes=205571)
    monkeypatch.setattr(backup, 'run_child', inspect)
    def mkdir(name, *a, **kw):
        assert restore_existing and name != retained.name
        created.append(name)
        return original_mkdir(name, *a, **kw)
    monkeypatch.setattr(backup.os, 'mkdir', mkdir)
    def chown(fd, uid, gid):
        assert uid == real_uid and gid == os.getegid()
        return original_fchown(fd, uid, gid)
    monkeypatch.setattr(backup.os, 'fchown', chown)
    monkeypatch.setattr(backup, 'restore_files', lambda *a, **kw: pytest.fail('Must not re-extract'))
    monkeypatch.setitem(core, 'create_private_at', lambda *a, **kw: pytest.fail('Must not create archives/manifests'))
    if mutation:
        with pytest.raises(SystemExit): backup.main(core=core, inspector=inspector, sources={},
            inspect_existing=not restore_existing, restore_existing=restore_existing)
    else: backup.main(core=core, inspector=inspector, sources={},
        inspect_existing=not restore_existing, restore_existing=restore_existing)
    output = capsys.readouterr().out
    result = json.loads(output)
    assert 'PRIVATE' not in output
    assert result['complete'] is (mutation is None)
    if not restore_existing: assert result['files_written'] is False
    assert result['memory_records_written'] is False
    assert result.get('encrypted_backup_created', False) is False
    assert paths == [backup.FAILED_BACKUP]
    assert (retained / 'retained-evidence').read_bytes() == b'PRIVATE_FAILED_ATTEMPT'
    assert len(created) == int(restore_existing and mutation in {None, 'child-failure'})
    if restore_existing and mutation is None:
        assert result['reused_existing_encrypted_backup'] is True
        assert result['previous_recovery_destination_reused'] is False
        assert result['restored_scope_status_passed'] is True
    if mutation == 'child-failure': assert result['restricted_diagnostics']['phase'] == 'restore_verify'


@pytest.mark.parametrize('mutation', ['collision', 'parent-mode', 'invalid-generation', 'missing-parent'])
def test_fresh_restore_destination_refuses_reuse_or_unprotected_parent(home, mutation):
    core, _, backup, _, recovery, _, _, _ = home
    generation = 'd' * 32
    recovery.chmod(0o711)
    leaf = recovery / ('check-' + generation)
    if mutation == 'collision':
        leaf.mkdir(mode=0o700)
        (leaf / 'retained').write_bytes(b'PRIVATE_OLD')
    if mutation == 'parent-mode': recovery.chmod(0o700)
    if mutation == 'invalid-generation': generation = '../escape'
    if mutation == 'missing-parent': backup.RECOVERY = recovery / 'missing'
    with pytest.raises((backup.BackupError, OSError)):
        backup.new_recovery_destination(core, NS(pw_uid=os.geteuid(), pw_gid=os.getegid()),
                                        generation, create_parent=False)
    if mutation == 'collision': assert (leaf / 'retained').read_bytes() == b'PRIVATE_OLD'
    else: assert not list(recovery.iterdir())


@pytest.mark.parametrize('inspect,restore', [(True, True), (1, False), (False, 1)])
def test_conflicting_or_non_boolean_operator_modes_refused_before_any_access(modules, monkeypatch, capsys, inspect, restore):
    core, inspector, backup = modules
    monkeypatch.setattr(backup.pwd, 'getpwnam', lambda *a: pytest.fail('No account or credential access'))
    with pytest.raises(SystemExit):
        backup.main(core=vars(core), inspector=vars(inspector), sources={},
                    inspect_existing=inspect, restore_existing=restore)
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'


def test_schedule_program_compiles_and_units_validate_with_native_systemd(modules, tmp_path):
    *_, backup = modules
    sources = {name: Path(name).read_bytes() for name in backup.NAMES}
    runner, code, service, timer = backup.schedule_payloads(sources)
    compile(code, '<protected-scheduled-runner>', 'exec')
    assert len(code) <= 262144 and str(runner).startswith('/opt/enhanced-cognee-profile-backup/')
    assert b'backup_only=True, scheduled_backup=True' in code
    assert b'PrivateNetwork=yes' in service and b'ProtectSystem=strict' in service
    assert b'CapabilityBoundingSet=CAP_SETUID CAP_SETGID\n' in service
    assert b'AmbientCapabilities=CAP_SETUID\n' in service
    assert b'InaccessiblePaths=-/etc/enhanced-cognee/age-recovery-identity.txt' in service
    assert b'OnCalendar=daily' in timer and b'Persistent=true' in timer
    for name, raw in ((backup.SERVICE_NAME, service), (backup.TIMER_NAME, timer)):
        (tmp_path / name).write_bytes(raw)
    result = subprocess.run(['/usr/bin/systemd-analyze', 'verify', str(tmp_path / backup.SERVICE_NAME),
        str(tmp_path / backup.TIMER_NAME)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'SYSTEMD_UNIT_PATH': str(tmp_path) + ':/usr/lib/systemd/system'})
    assert result.returncode == 0, result.stderr.decode()
    assert not result.stderr, 'Unit validation warnings must be reviewed'


@pytest.mark.parametrize('mutation', [None, 'unit-conflict', 'loaded-conflict', 'validate', 'service', 'result', 'enable', 'inactive', 'deadline'])
def test_schedule_install_preserves_conflicts_and_enables_only_after_service_pass(home, monkeypatch, tmp_path, capsys, mutation):
    core, inspector, backup, _, _, _, _, _ = home
    store = tmp_path / 'opt' / 'profile-backup'
    store.parent.mkdir()
    units = tmp_path / 'system-units'
    units.mkdir()
    monkeypatch.setattr(backup, 'SCHEDULE_ROOT', store)
    monkeypatch.setattr(backup, 'UNIT_ROOT', units)
    monkeypatch.setattr(backup.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes')
    monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    original_read = Path.read_text
    def read(path, *args, **kwargs):
        return 'systemd\n' if path == Path('/proc/1/comm') else original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read)
    sentinel = units / backup.SERVICE_NAME
    if mutation == 'unit-conflict': sentinel.write_bytes(b'PRIVATE_EXISTING_OPERATOR_UNIT')
    calls = []
    def command(argv, **kw):
        calls.append(argv)
        if argv[0].endswith('systemd-analyze'):
            if mutation == 'validate': raise backup.BackupError('unit_validation_failed')
            return b''
        action = argv[1]
        if action == 'show' and '--property=LoadState' in argv:
            return b'loaded\n' if mutation == 'loaded-conflict' else b'not-found\n'
        if action == 'show' and '--property=NextElapseUSecRealtime' in argv:
            return b'n/a\n' if mutation == 'deadline' else b'Sat 2026-10-24 00:08:00 BST\n'
        if action == 'show':
            return b'Result=success\nExecMainStatus=0\nActiveState=' + (b'active' if mutation == 'result' else b'inactive') + b'\n'
        if action == 'start' and mutation == 'service': raise backup.BackupError('private_details_suppressed')
        if action == 'enable' and mutation == 'enable': raise backup.BackupError('private_details_suppressed')
        if action == 'is-enabled': return b'enabled\n'
        if action == 'is-active': return b'inactive\n' if mutation == 'inactive' else b'active\n'
        return b''
    monkeypatch.setattr(backup, 'schedule_command', command)
    sources = {name: Path(name).read_bytes() for name in backup.NAMES}
    if mutation:
        with pytest.raises(SystemExit): backup.install_schedule(core=core, inspector=inspector, sources=sources)
    else: backup.install_schedule(core=core, inspector=inspector, sources=sources)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert 'PRIVATE' not in output and report['complete'] is (mutation is None)
    assert report['model_called'] is False and report['existing_database_schedule_changed'] is False
    actions = [a[1] for a in calls if a[0] == '/usr/bin/systemctl']
    enabled = any(action == 'enable' for action in actions)
    assert enabled is (mutation in {None, 'enable', 'inactive', 'deadline'})
    if enabled: assert actions.index('start') < actions.index('enable')
    if mutation == 'unit-conflict': assert sentinel.read_bytes() == b'PRIVATE_EXISTING_OPERATOR_UNIT'
    if mutation is None:
        assert report['daily_profile_timer_active'] and report['daily_profile_timer_enabled']
        runner = Path(report['protected_runner'])
        assert runner.is_file() and stat.S_IMODE(runner.stat().st_mode) == 0o644
        assert stat.S_IMODE(sentinel.stat().st_mode) == 0o644
        assert not report['windows_collection_qualified'] and not report['disposable_restore_created']
    if mutation in {'validate', 'loaded-conflict'}: assert not list(units.iterdir())


def test_schedule_requires_host_systemd_without_changing_or_restarting_it(home, monkeypatch, capsys):
    core, inspector, backup, *_ = home
    monkeypatch.setattr(backup.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('WSL_DISTRO_NAME', 'Ubuntu-Hermes')
    monkeypatch.setenv('SUDO_USER', 'vincentspereira')
    monkeypatch.setattr(Path, 'read_text', lambda *a, **kw: 'sandbox-init\n')
    monkeypatch.setattr(backup, 'schedule_command', lambda *a, **kw: pytest.fail('No changes or restart'))
    with pytest.raises(SystemExit): backup.install_schedule(core=core, inspector=inspector, sources={})
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'


@pytest.mark.parametrize('mutation', [None, 'missing-unit', 'nonzero', 'stdout-budget', 'stderr-budget', 'unit-warning'])
def test_schedule_commands_suppress_private_output_and_enforce_unit_warning_gate(home, monkeypatch, mutation):
    _, _, backup, *_ = home
    kwargs_seen = []
    def run(argv, **kwargs):
        kwargs_seen.append(kwargs)
        assert kwargs['stdin'] is subprocess.DEVNULL and kwargs['close_fds'] is True
        assert kwargs['env']['PATH'] == '/usr/bin:/bin'
        return NS(returncode=4 if mutation == 'missing-unit' else 1 if mutation == 'nonzero' else 0,
            stdout=b'x' * 65537 if mutation == 'stdout-budget' else b'not-found\n',
            stderr=b'x' * 4097 if mutation == 'stderr-budget' else b'PRIVATE_RAW_KEY' if mutation == 'unit-warning' else b'')
    monkeypatch.setattr(backup.subprocess, 'run', run)
    args = dict(allowed_codes=(0, 4)) if mutation == 'missing-unit' else {}
    if mutation == 'unit-warning': args['unit_path'] = Path('/opt/protected-unit-test')
    if mutation in {'nonzero', 'stdout-budget', 'stderr-budget', 'unit-warning'}:
        with pytest.raises(backup.BackupError) as error: backup.schedule_command(['/usr/bin/systemctl', 'show'], **args)
        assert 'PRIVATE' not in str(error.value)
    else: assert backup.schedule_command(['/usr/bin/systemctl', 'show'], **args) == b'not-found\n'
    if mutation == 'unit-warning':
        assert kwargs_seen[0]['env']['SYSTEMD_UNIT_PATH'] == '/opt/protected-unit-test:/usr/lib/systemd/system'


@pytest.mark.parametrize('backup_only,scheduled', [(False, True), (1, False), (True, 1)])
def test_scheduled_mode_cannot_invoke_restore_or_accept_non_boolean_mode(modules, monkeypatch, capsys, backup_only, scheduled):
    core, inspector, backup = modules
    monkeypatch.setattr(backup.pwd, 'getpwnam', lambda *a: pytest.fail('No account or key access'))
    with pytest.raises(SystemExit): backup.main(core=vars(core), inspector=vars(inspector), sources={},
        backup_only=backup_only, scheduled_backup=scheduled)
    assert json.loads(capsys.readouterr().out)['failure_stage'] == 'operator_preflight'


def test_scheduled_identity_launcher_avoids_python_preexec_identity_calls_without_adding_privilege(home, monkeypatch):
    core, inspector, backup, _, _, _, _, _ = home
    receipt = dict(complete=True, files=60, entries=104, source_bytes=205571)
    def run(argv, **kwargs):
        if 'user' in kwargs: raise PermissionError(1, 'synthetic blocked pre-exec transition')
        assert argv[:8] == ['/usr/bin/setpriv', '--reuid=993', '--regid=985', '--clear-groups',
            '--ambient-caps=-all', '--inh-caps=-all', '--no-new-privs', '--']
        assert argv[8:11] == ['/usr/bin/setpriv', '--no-new-privs', '--']
        assert not {'user', 'group', 'extra_groups'}.intersection(kwargs)
        assert kwargs['close_fds'] and kwargs['cwd'] == '/tmp'
        assert kwargs['env'] == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
        assert kwargs['input'] == b''
        compile(argv[-1], '<unchanged-restricted-child-guards>', 'exec')
        return NS(returncode=0, stdout=b'PRIVATE_SYNTHETIC_SNAPSHOT', stderr=json.dumps(receipt).encode())
    monkeypatch.setattr(backup.subprocess, 'run', run)
    sources = {name: Path(name).read_bytes() for name in backup.NAMES}
    account = NS(pw_uid=993, pw_gid=985)
    with pytest.raises(PermissionError): backup.run_child(core, inspector, sources, account, 'snapshot')
    raw, report = backup.run_child(core, inspector, sources, account, 'snapshot', external_identity=True)
    assert raw == b'PRIVATE_SYNTHETIC_SNAPSHOT' and report == receipt


@pytest.mark.parametrize('uid,gid', [(0, 985), (993, 0), (True, 985), (993, '985')])
def test_scheduled_launcher_rejects_root_or_malformed_identity_before_any_launch(home, monkeypatch, uid, gid):
    core, inspector, backup, *_ = home
    monkeypatch.setattr(backup.subprocess, 'run', lambda *a, **kw: pytest.fail('No launch for an invalid restricted identity'))
    with pytest.raises(backup.BackupError): backup.run_child(core, inspector,
        {name: Path(name).read_bytes() for name in backup.NAMES}, NS(pw_uid=uid, pw_gid=gid), 'snapshot', external_identity=True)


def test_schedule_payload_is_stable_across_source_dictionary_insertion_order(modules):
    *_, backup = modules
    sources = {name: Path(name).read_bytes() for name in sorted(backup.NAMES)}
    assert backup.schedule_payloads(sources) == backup.schedule_payloads(dict(reversed(list(sources.items()))))
