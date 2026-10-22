"""No-content access probes must fail closed and never modify existing files."""
import importlib.util
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest


@pytest.fixture
def probe():
    path = Path("integrations/hermes/deployment/check_restricted_access.py").resolve()
    spec = importlib.util.spec_from_file_location("restricted_access_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_permission_open_cannot_truncate_create_or_change_data(probe, monkeypatch, tmp_path):
    program = tmp_path / "program"
    original = b"SYNTHETIC_PROGRAM_MUST_STAY_INTACT"
    program.write_bytes(original)
    real_open, flags_seen = os.open, []
    def capture(path, flags, *args, **kwargs):
        flags_seen.append(flags)
        return real_open(path, flags, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("Access probes must not read or write file data")
    with monkeypatch.context() as patch:
        patch.setattr(os, "open", capture)
        patch.setattr(os, "read", forbidden)
        patch.setattr(os, "write", forbidden)
        assert probe.open_permission(program, write=True) == "ALLOWED"
        assert probe.open_permission(program) == "ALLOWED"
        assert probe.open_permission(tmp_path / "missing", write=True) == "MISSING"
    assert program.read_bytes() == original and not (tmp_path / "missing").exists()
    assert all(not flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND) for flags in flags_seen)
    assert flags_seen[0] & os.O_WRONLY


def test_links_and_nonregular_files_are_not_treated_as_denial_evidence(probe, tmp_path):
    original = tmp_path / "original"
    original.write_bytes(b"PRIVATE_SYNTHETIC_DATA")
    linked = tmp_path / "link"
    linked.symlink_to(original)
    assert probe.open_permission(linked) == "INCONCLUSIVE"
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    assert probe.open_permission(fifo) == "UNEXPECTED_TYPE"
    assert original.read_bytes() == b"PRIVATE_SYNTHETIC_DATA"


@pytest.mark.parametrize("error,expected", [
    (PermissionError, "DENIED"), (FileNotFoundError, "MISSING"), (OSError, "INCONCLUSIVE")])
def test_only_permission_errors_prove_denial(probe, monkeypatch, error, expected):
    def reject(*args, **kwargs):
        raise error()
    monkeypatch.setattr(os, "open", reject)
    assert probe.open_permission(Path("/synthetic")) == expected


def test_acl_write_access_invalidates_root_mode_only_protection(probe, monkeypatch, tmp_path):
    original_lstat = Path.lstat
    def info(path):
        if path == tmp_path:
            return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0)
        return original_lstat(path)
    monkeypatch.setattr(Path, "lstat", info)
    monkeypatch.setattr(os, "access", lambda *args, **kwargs: True)
    assert probe.directory_protected(tmp_path) is False
    monkeypatch.setattr(os, "access", lambda *args, **kwargs: False)
    assert probe.directory_protected(tmp_path) is True


@pytest.mark.parametrize("secret_result,secret_write_result,program_result,passed", [
    ("DENIED", "DENIED", "DENIED", True), ("ALLOWED", "DENIED", "DENIED", False),
    ("MISSING", "DENIED", "DENIED", False), ("DENIED", "DENIED", "ALLOWED", False),
    ("DENIED", "DENIED", "MISSING", False), ("INCONCLUSIVE", "DENIED", "DENIED", False),
    ("DENIED", "ALLOWED", "DENIED", False)])
def test_access_summary_does_not_claim_full_qualification(probe, monkeypatch, tmp_path, secret_result, secret_write_result, program_result, passed):
    tmp_path.chmod(0o700)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(probe, "ACCOUNT_HOME", tmp_path)
    identity = SimpleNamespace(pw_name="hermes-runtime", pw_uid=os.geteuid(), pw_gid=os.getegid(), pw_dir=str(tmp_path))
    monkeypatch.setattr(probe.pwd, "getpwuid", lambda uid: identity)
    monkeypatch.setattr(os, "getgroups", lambda: [identity.pw_gid])
    secret = tmp_path / "secret"
    monkeypatch.setattr(probe, "SECRETS", (secret,))
    monkeypatch.setattr(probe, "PROGRAM_FILES", (probe.RELEASE / "bin/hermes",))
    monkeypatch.setattr(probe, "PROGRAM_DIRECTORIES", (probe.RELEASE,))
    monkeypatch.setattr(probe, "process_confined", lambda: True)
    monkeypatch.setattr(probe, "directory_protected", lambda path: True)
    def access(path, **kwargs):
        if path == secret:
            return secret_write_result if kwargs.get("write") else secret_result
        return program_result
    monkeypatch.setattr(probe, "open_permission", access)
    result = probe.check()
    assert result["selected_access_checks_passed"] is passed
    assert result["runtime_qualified"] is False and result["memory_connection_tested"] is False
    assert result["secret_or_program_data_read_or_written"] is False


def test_wrong_account_is_refused_before_any_file_probe(probe, monkeypatch):
    monkeypatch.setattr(probe.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="human"))
    def forbidden(*args, **kwargs):
        raise AssertionError("Wrong user must not attempt secret/program probes")
    monkeypatch.setattr(probe, "open_permission", forbidden)
    with pytest.raises(RuntimeError, match="restricted account"):
        probe.check()
