"""Actual filesystem/SQLite fixtures; no host inspection, credentials or models."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def inspector():
    path = Path("integrations/hermes/deployment/inspect_pilot_recovery.py").resolve()
    spec = importlib.util.spec_from_file_location("recovery_inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(inspector, root, **kwargs):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try: return inspector.inventory(fd, os.geteuid(), **kwargs)
    finally: os.close(fd)


def populate(inspector, root):
    for name in (*inspector.PRIVATE, *inspector.RECEIPTS):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"PRIVATE_CREDENTIAL_OR_RECEIPT_CONTENT_NEVER_RETURNED")
        path.chmod(0o600)
    plugin = root / inspector.PLUGIN_RELATIVE
    plugin.parent.mkdir(parents=True, exist_ok=True)
    plugin.symlink_to(inspector.ARTIFACT)


def test_full_home_inventory_counts_receipts_workspace_and_prior_generations_without_content(inspector, tmp_path):
    populate(inspector, tmp_path)
    (tmp_path / "PRIVATE_WORKSPACE_NAME").mkdir()
    (tmp_path / "PRIVATE_WORKSPACE_NAME/PRIVATE_FILENAME").write_bytes(b"PRIVATE_ORIGINAL_WORK")
    (tmp_path / ".env-before-cognee-renew-retained").write_bytes(b"PRIVATE_PREVIOUS_TOKEN")
    result = inspect(inspector, tmp_path)
    assert result["regular_files"] == 9 and all(result["required_private_files"].values())
    assert all(result["required_receipts"].values()) and result["expected_provider_link"]
    assert result["unknown_symlinks"] == result["unreadable_entries"] == result["changed_entries"] == 0
    assert result["logical_bytes"] > 0 and result["allocated_bytes"] > 0
    assert "PRIVATE_" not in json.dumps(result)


def test_unknown_and_outside_links_are_never_followed(inspector, tmp_path):
    root, outside = tmp_path / "home", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret").write_bytes(b"SQLite format 3\x00PRIVATE")
    (root / "outside-link").symlink_to(outside, target_is_directory=True)
    (root / "missing-link").symlink_to(tmp_path / "missing")
    result = inspect(inspector, root)
    assert result["unknown_symlinks"] == 2 and result["regular_files"] == 0 and result["sqlite_databases"] == 0


def test_live_wal_sqlite_is_identified_without_opening_connection_or_changing_files(inspector, tmp_path, monkeypatch):
    db = tmp_path / "private-state.db"
    connection = sqlite3.connect(db)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE private_items(value TEXT)")
        connection.execute("INSERT INTO private_items VALUES ('PRIVATE_SQLITE_CONTENT')")
        connection.commit()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
        monkeypatch.setattr(sqlite3, "connect", lambda *a, **kw: pytest.fail("Inventory must not open SQLite"))
        result = inspect(inspector, tmp_path)
        assert result["sqlite_databases"] == result["sqlite_wal_files"] == result["sqlite_shm_files"] == 1
        assert result["largest_sqlite_bytes"] == db.stat().st_size
        assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()} == before
        assert "PRIVATE_" not in json.dumps(result)
    finally: connection.close()


def test_special_files_are_counted_without_opening_or_blocking(inspector, tmp_path):
    os.mkfifo(tmp_path / "private-pipe")
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.bind(str(tmp_path / "private-socket"))
        result = inspect(inspector, tmp_path)
        assert result["sockets"] == result["other_special_files"] == 1 and result["regular_files"] == 0
    finally: sock.close()


@pytest.mark.parametrize("mutation", ["mode", "missing", "hardlink", "symlink"])
def test_required_private_file_flags_never_accept_unsafe_or_missing_entries(inspector, tmp_path, mutation):
    populate(inspector, tmp_path)
    target = tmp_path / next(iter(inspector.PRIVATE))
    if mutation == "mode": target.chmod(0o644)
    elif mutation == "missing": target.rename(target.with_name("retained-original"))
    elif mutation == "hardlink": os.link(target, target.with_name("retained-link"))
    else:
        retained = target.with_name("retained-original")
        target.rename(retained)
        target.symlink_to(retained)
    result = inspect(inspector, tmp_path)
    assert not result["required_private_files"][".env"]
    if mutation == "hardlink": assert result["hardlinked_files"] == 2


@pytest.mark.parametrize("kind", ["entries", "time", "depth"])
def test_inventory_limits_refuse_unbounded_traversal(inspector, tmp_path, monkeypatch, kind):
    (tmp_path / "private").write_bytes(b"PRIVATE")
    kwargs = {}
    if kind == "entries": kwargs["max_entries"] = 0
    if kind == "time": kwargs["seconds"] = -1
    if kind == "depth":
        path = tmp_path
        for _ in range(65):
            path = path / "x"
            path.mkdir()
    with pytest.raises(inspector.InspectionError): inspect(inspector, tmp_path, **kwargs)


@pytest.mark.parametrize("mutation", ["denied", "changed", "mount"])
def test_unreadable_racing_or_nested_mount_entries_are_reported_as_incomplete(inspector, tmp_path, monkeypatch, mutation):
    path = tmp_path / "PRIVATE_FILENAME"
    path.write_bytes(b"PRIVATE")
    original_open, original_read, original_stat = os.open, os.read, os.stat
    if mutation == "denied":
        def open_file(name, flags, *a, **kw):
            if name == path.name: raise PermissionError("PRIVATE_ERROR")
            return original_open(name, flags, *a, **kw)
        monkeypatch.setattr(inspector.os, "open", open_file)
    elif mutation == "changed":
        def read(fd, size):
            result = original_read(fd, size)
            path.write_bytes(b"PRIVATE_CHANGED")
            return result
        monkeypatch.setattr(inspector.os, "read", read)
    else:
        def info(name, *a, **kw):
            actual = original_stat(name, *a, **kw)
            return NS(st_dev=actual.st_dev + 1) if name == path.name else actual
        monkeypatch.setattr(inspector.os, "stat", info)
    result = inspect(inspector, tmp_path)
    assert result[{"denied": "unreadable_entries", "changed": "changed_entries", "mount": "nested_mounts"}[mutation]] == 1
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("mutation", [None, "writable", "hash", "link", "not-executable"])
def test_public_artifact_and_age_file_protection(inspector, tmp_path, monkeypatch, mutation):
    path = tmp_path / "tool"
    path.write_bytes(b"PUBLIC_PROGRAM")
    path.chmod(0o644 if mutation == "not-executable" else 0o755)
    if mutation == "writable": path.chmod(0o777)
    if mutation == "link":
        original = tmp_path / "retained"
        path.rename(original)
        path.symlink_to(original)
    monkeypatch.setattr(inspector, "directory", lambda parent, owners: os.open(parent, os.O_RDONLY | os.O_DIRECTORY))
    fstat = os.fstat
    def root_info(fd):
        info = fstat(fd)
        return NS(**{name: (0 if name == "st_uid" else getattr(info, name)) for name in (
            "st_dev", "st_ino", "st_uid", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")})
    monkeypatch.setattr(inspector.os, "fstat", root_info)
    if mutation == "link":
        with pytest.raises(OSError): inspector.protected_file(path)
    else:
        expected = "bad" if mutation == "hash" else hashlib.sha256(b"PUBLIC_PROGRAM").hexdigest()
        assert inspector.protected_file(path, expected=expected, executable=True) == (mutation is None)


@pytest.mark.parametrize("mutation", [None, "incomplete", "identity-error"])
def test_public_report_is_sanitized_and_never_claims_recovery(inspector, tmp_path, monkeypatch, capsys, mutation):
    populate(inspector, tmp_path)
    uid = os.geteuid()
    def preflight(approved):
        if mutation == "identity-error": raise OSError("PRIVATE_OPERATOR_ERROR")
        assert approved is True
        return uid
    monkeypatch.setattr(inspector, "HOME", tmp_path)
    monkeypatch.setattr(inspector, "preflight", preflight)
    monkeypatch.setattr(inspector, "directory", lambda path, owners: os.open(path, os.O_RDONLY | os.O_DIRECTORY))
    monkeypatch.setattr(inspector, "protected_file", lambda *a, **kw: True)
    if mutation == "incomplete":
        original = inspector.inventory
        def inventory(*a):
            result = original(*a)
            result["changed_entries"] += 1
            return result
        monkeypatch.setattr(inspector, "inventory", inventory)
    if mutation:
        with pytest.raises(SystemExit): inspector.main(approved_test=True)
    else: inspector.main(approved_test=True)
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["complete"] == (mutation is None)
    assert "PRIVATE_" not in output and not result["files_written"] and not result["model_called"]
    assert not result["profile_recovery_qualified"] and not result["runtime_qualified"]


@pytest.mark.parametrize("mutation", ["approval", "account", "home", "groups", "python", "capabilities", "privileges", "ambient-setuid", "effective-setuid"])
def test_identity_protection_before_any_home_inspection(inspector, monkeypatch, tmp_path, mutation):
    uid, gid = os.geteuid(), os.getegid()
    release = Path(inspector.sys.executable).resolve().parent
    monkeypatch.setattr(inspector, "RELEASE", tmp_path if mutation == "python" else release)
    monkeypatch.setattr(inspector.pwd, "getpwuid", lambda value: NS(pw_name="other" if mutation == "account" else "hermes-runtime",
        pw_uid=uid, pw_gid=gid, pw_dir=str(inspector.HOME)))
    monkeypatch.setenv("HOME", "/wrong" if mutation == "home" else str(inspector.HOME))
    monkeypatch.setenv("HERMES_HOME", str(inspector.HOME / inspector.PROFILE_RELATIVE))
    monkeypatch.setattr(inspector.os, "getgroups", lambda: [gid, gid + 1] if mutation == "groups" else [gid])
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw: "NoNewPrivs: " + ("0" if mutation == "privileges" else "1")
        + "\nCapAmb: " + ("0000000000000080" if mutation == "ambient-setuid" else "0000000000000000")
        + "\nCapEff: " + ("0000000000000080" if mutation == "effective-setuid" else
            "0000000000000001" if mutation == "capabilities" else "0000000000000000"))
    with pytest.raises(inspector.InspectionError): inspector.preflight(mutation != "approval")
