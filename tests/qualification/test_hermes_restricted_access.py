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


def test_tools_generation_selects_only_fixed_paths_without_inspection(probe, monkeypatch):
    original = probe.RELEASE
    def forbidden(*args, **kwargs):
        raise AssertionError("Selecting a fixed generation must not inspect or open files")
    monkeypatch.setattr(probe, "open_permission", forbidden)
    probe.use_tools_generation()
    assert probe.RELEASE == original.with_name(original.name + "-tools1")
    assert probe.TOOLS_SELECTED is True
    assert all(path.is_relative_to(probe.RELEASE) for path in probe.PROGRAM_FILES)
    assert all(not path.is_relative_to(original) for path in probe.PROGRAM_DIRECTORIES)
    probe.use_tools_generation()
    assert probe.RELEASE == probe.TOOLS_RELEASE


@pytest.fixture
def tool_paths(probe, monkeypatch, tmp_path):
    release = tmp_path / "protected"
    monkeypatch.setattr(probe, "RELEASE", release)
    for relative in probe.TOOL_BINARIES:
        path = release / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"SYNTHETIC_PUBLIC_PROGRAM")
    (release / "python/facts.json").write_text('{"schema":1}')
    npm = release / probe.TOOL_BINARIES[2]
    npm.rename(npm.parent / "npm-cli.js")
    npm.symlink_to("npm-cli.js")
    return release


def test_selected_tool_paths_include_link_target_facts_and_ancestors(probe, tool_paths):
    files, directories = probe.selected_tool_paths()
    assert len(files) == 5
    assert tool_paths / "python/facts.json" in files
    npm = tool_paths / probe.TOOL_BINARIES[2]
    assert npm not in files and npm.resolve() in files
    for binary in (tool_paths / relative for relative in probe.TOOL_BINARIES):
        assert set(binary.parents) <= set(directories)
    assert Path("/") in directories


@pytest.mark.parametrize("mutation", ["outside-link", "broken-link", "missing"])
def test_unconfined_or_missing_tool_is_refused_before_any_permission_open(probe, tool_paths, monkeypatch, mutation):
    npm = tool_paths / probe.TOOL_BINARIES[2]
    if mutation == "outside-link":
        outside = tool_paths.parent / "PRIVATE_TARGET_DO_NOT_OPEN"
        outside.write_bytes(b"SYNTHETIC_PRIVATE_DATA")
        npm.unlink()  # Disposable fixture only.
        npm.symlink_to(outside)
    elif mutation == "broken-link":
        npm.unlink()
        npm.symlink_to("not-present")
    else:
        npm.rename(npm.parent / "original-preserved")
    monkeypatch.setattr(probe, "open_permission", lambda *a, **kw: pytest.fail("No permission opening allowed yet"))
    with pytest.raises((RuntimeError, OSError)) as error:
        probe.selected_tool_paths()
    assert "PRIVATE_TARGET" not in str(error.value)


@pytest.mark.parametrize("mode,owner,links,writable,expected", [
    (stat.S_IFREG | 0o755, 0, 1, False, True),
    (stat.S_IFREG | 0o755, 1000, 1, False, False),
    (stat.S_IFREG | 0o775, 0, 1, False, False),
    (stat.S_IFREG | 0o4755, 0, 1, False, False),
    (stat.S_IFREG | 0o755, 0, 2, False, False),
    (stat.S_IFREG | 0o755, 0, 1, True, False),
    (stat.S_IFLNK | 0o777, 0, 1, False, False),
])
def test_file_metadata_and_effective_acl_must_both_protect_program(probe, monkeypatch, mode, owner, links, writable, expected):
    monkeypatch.setattr(Path, "lstat", lambda self: SimpleNamespace(st_mode=mode, st_uid=owner, st_nlink=links))
    monkeypatch.setattr(os, "access", lambda *args, **kwargs: writable)
    assert probe.file_protected(Path("/selected-public-program")) is expected


def test_bad_tool_metadata_cannot_pass_an_otherwise_denied_summary(probe, tool_paths, monkeypatch, tmp_path):
    home = tmp_path / "runtime-home"
    home.mkdir(mode=0o700)
    monkeypatch.chdir(home)
    monkeypatch.setattr(probe, "ACCOUNT_HOME", home)
    monkeypatch.setattr(probe, "TOOLS_SELECTED", True)
    identity = SimpleNamespace(pw_name="hermes-runtime", pw_uid=os.geteuid(), pw_gid=os.getegid(), pw_dir=str(home))
    monkeypatch.setattr(probe.pwd, "getpwuid", lambda uid: identity)
    monkeypatch.setattr(os, "getgroups", lambda: [identity.pw_gid])
    monkeypatch.setattr(probe, "PROGRAM_FILES", (tool_paths / "python/facts.json",))
    monkeypatch.setattr(probe, "PROGRAM_DIRECTORIES", (tool_paths,))
    monkeypatch.setattr(probe, "SECRETS", (tmp_path / "secret",))
    monkeypatch.setattr(probe, "process_confined", lambda: True)
    monkeypatch.setattr(probe, "open_permission", lambda *a, **kw: "DENIED")
    monkeypatch.setattr(probe, "directory_protected", lambda path: True)
    monkeypatch.setattr(probe, "file_protected", lambda path: False)
    result = probe.check()
    assert result["tools_generation_selected"] is True
    assert result["selected_access_checks_passed"] is False
    assert result["runtime_qualified"] is False and result["memory_connection_tested"] is False
    monkeypatch.setattr(probe, "file_protected", lambda path: True)
    assert probe.check()["selected_access_checks_passed"] is True


@pytest.mark.parametrize("argument", ["--release=/etc", "--tools-generation-extra", "--tools-generation --apply"])
def test_cli_refuses_arbitrary_generation_or_extra_flags(probe, monkeypatch, argument):
    monkeypatch.setattr(probe.sys, "argv", ["probe", *argument.split()])
    monkeypatch.setattr(probe, "check", lambda: pytest.fail("Invalid arguments must not probe files"))
    with pytest.raises(SystemExit, match="only --tools-generation"):
        probe.main()
