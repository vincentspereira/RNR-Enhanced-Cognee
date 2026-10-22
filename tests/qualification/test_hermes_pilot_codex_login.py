"""Fresh restricted OAuth selection/preservation with no live auth or model calls."""
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def login():
    spec = importlib.util.spec_from_file_location("pilot_codex_login",
        Path("integrations/hermes/deployment/login_pilot_codex.py").resolve())
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_explicit_owner_selection_required_before_auth_reads(login, monkeypatch):
    monkeypatch.setattr(login.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="hermes-runtime"))
    monkeypatch.setattr(login, "read_private", lambda *a: pytest.fail("No read before explicit selection"))
    with pytest.raises(login.LoginError):
        login.preflight(False)


def test_terminal_filter_shows_only_fixed_url_and_device_code(login):
    destination = io.StringIO()
    output = login.LoginOutput(destination)
    for part in ("PRIVATE_TOKEN_SENTINEL\n", "     \x1b[94m" + login.URL + "\x1b[0m\n",
                 "  2. Enter this ", "code:\n", "     \x1b[94mABCD-EFGH\x1b[0m\n",
                 "Added PRIVATE_EMAIL_SENTINEL\n"):
        output.write(part)
    public = destination.getvalue()
    assert login.URL in public and "ABCD-EFGH" in public and output.code_shown
    assert "PRIVATE_" not in public


@pytest.mark.parametrize("code", ["PRIVATE TOKEN SENTINEL", "https://other.example", "secret.with.dots",
                                  "A" * 200, "abCD-EFGH", "123"])
def test_invalid_device_output_is_not_echoed(login, code):
    destination = io.StringIO()
    output = login.LoginOutput(destination)
    output.write("2. Enter this code:\n")
    with pytest.raises(login.LoginError) as error:
        output.write(code + "\n")
    assert code not in destination.getvalue() and code not in str(error.value)


def auth_record(login):
    return {"credential_pool": {"openai-codex": [{"label": login.LABEL, "auth_type": "oauth",
        "source": "manual:device_code", "access_token": "PRIVATE_ACCESS_SENTINEL",
        "refresh_token": "PRIVATE_REFRESH_SENTINEL"}]}}


def test_new_native_pool_shape_verified_without_printing_values(login, monkeypatch, capsys):
    monkeypatch.setattr(login, "read_private", lambda *a: json.dumps(auth_record(login)).encode())
    login.verify_auth(1000)
    assert not capsys.readouterr().out


@pytest.mark.parametrize("change", ["label", "type", "source", "missing-refresh", "duplicate", "absent"])
def test_ambiguous_or_unexpected_auth_state_preserved_and_refused(login, monkeypatch, change):
    auth = auth_record(login)
    row = auth["credential_pool"]["openai-codex"][0]
    if change == "label": row["label"] = "PRIVATE_OTHER_SENTINEL"
    elif change == "type": row["auth_type"] = "api_key"
    elif change == "source": row["source"] = "device_code"
    elif change == "missing-refresh": row.pop("refresh_token")
    elif change == "duplicate": auth["credential_pool"]["openai-codex"].append(dict(row))
    else: auth = {}
    monkeypatch.setattr(login, "read_private", lambda *a: json.dumps(auth).encode())
    with pytest.raises(login.LoginError) as error:
        login.verify_auth(1000)
    assert "PRIVATE_" not in str(error.value)


def mock_native(login, tmp_path, monkeypatch, execute):
    release = tmp_path / "release"
    (release / "repo/hermes_cli").mkdir(parents=True)
    constants = release / "repo/hermes_constants.py"
    commands = release / "repo/hermes_cli/auth_commands.py"
    constants.touch()
    commands.touch()
    monkeypatch.setattr(login, "RELEASE", release)
    module = SimpleNamespace(__file__=str(commands), auth_add_command=execute)
    monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(auth_commands=module))
    monkeypatch.setitem(sys.modules, "hermes_constants", SimpleNamespace(
        __file__=str(constants), get_hermes_home=lambda: login.PROFILE))
    monkeypatch.setattr(sys, "path", list(sys.path))


def test_native_auth_add_uses_new_oauth_not_key_import_or_model_command(login, tmp_path, monkeypatch, capsys):
    calls = []
    def execute(args):
        calls.append(vars(args))
        print(login.URL)
        print("2. Enter this code:\nABCD-EFGH")
        print("PRIVATE_NATIVE_OUTPUT_SENTINEL")
    mock_native(login, tmp_path, monkeypatch, execute)
    login.native_login()
    assert calls == [{"provider": "openai-codex", "auth_type": "oauth", "label": login.LABEL,
                      "no_browser": True, "browser": False, "timeout": 20.0, "priority": None}]
    assert "PRIVATE_" not in capsys.readouterr().out


def test_native_shortcut_without_fresh_device_flow_is_not_qualified(login, tmp_path, monkeypatch):
    mock_native(login, tmp_path, monkeypatch, lambda args: None)
    with pytest.raises(login.LoginError):
        login.native_login()


def setup_main(login, monkeypatch, *, dns_status=0):
    snapshots = {"config.yaml": login.EXPECTED_CONFIG, ".env": b"PRIVATE_MEMORY_KEY_SENTINEL"}
    monkeypatch.setattr(login, "preflight", lambda approved: (1000, snapshots))
    monkeypatch.setattr(login.os, "chdir", lambda path: None)
    monkeypatch.setattr(login.os, "umask", lambda mask: None)
    monkeypatch.setattr(login.logging, "disable", lambda value: None)
    monkeypatch.setattr(login.subprocess, "run", lambda command, **kw: SimpleNamespace(returncode=dns_status))
    monkeypatch.setattr(login, "read_private", lambda name, uid: snapshots[name])
    monkeypatch.setattr(login, "verify_auth", lambda uid: None)
    return snapshots


def test_success_keeps_original_files_and_does_not_claim_model_qualification(login, monkeypatch, capsys):
    setup_main(login, monkeypatch)
    monkeypatch.setattr(login, "native_login", lambda: None)
    login.main(approved_login=True)
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] and report["pilot_settings_unchanged"]
    assert report["fresh_pilot_oauth_saved"] and not report["human_credentials_copied"]
    assert not any(report[field] for field in ("model_defaults_changed", "model_called",
                                              "memory_records_written", "runtime_qualified"))


def test_auth_host_dns_failure_does_not_start_signin(login, monkeypatch, capsys):
    setup_main(login, monkeypatch, dns_status=1)
    monkeypatch.setattr(login, "native_login", lambda: pytest.fail("No auth before DNS succeeds"))
    with pytest.raises(SystemExit): login.main(approved_login=True)
    report = json.loads(capsys.readouterr().out)
    assert report["failure_stage"] == "openid_dns" and not report["complete"]


@pytest.mark.parametrize("error", [RuntimeError("PRIVATE_ERROR_SENTINEL"), SystemExit("PRIVATE_EXIT_SENTINEL")])
def test_native_errors_and_exit_text_are_suppressed(login, monkeypatch, capsys, error):
    setup_main(login, monkeypatch)
    def fail(): raise error
    monkeypatch.setattr(login, "native_login", fail)
    with pytest.raises(SystemExit): login.main(approved_login=True)
    output = capsys.readouterr().out
    assert "PRIVATE_" not in output
    assert json.loads(output)["failure_stage"] == "device_signin"


def test_concurrent_settings_change_is_reported_without_restoration(login, monkeypatch, capsys):
    snapshots = setup_main(login, monkeypatch)
    reads = dict(snapshots)
    reads["config.yaml"] = b"PRIVATE_CONCURRENT_CHANGE"
    monkeypatch.setattr(login, "read_private", lambda name, uid: reads[name])
    monkeypatch.setattr(login, "native_login", lambda: None)
    with pytest.raises(SystemExit): login.main(approved_login=True)
    report = json.loads(capsys.readouterr().out)
    assert report["pilot_settings_unchanged"] is False
    assert reads["config.yaml"] == b"PRIVATE_CONCURRENT_CHANGE"


@pytest.mark.parametrize("mutation", ["none", "root", "supplementary", "nnp", "capability",
                                     "unsafe-directory", "existing-auth", "human-readable"])
def test_restricted_preflight_boundaries(login, monkeypatch, mutation):
    account = SimpleNamespace(pw_name="hermes-runtime", pw_uid=1000, pw_gid=42, pw_dir=str(login.HOME))
    if mutation == "root": account.pw_uid = 0
    monkeypatch.setattr(login.pwd, "getpwuid", lambda uid: account)
    monkeypatch.setattr(login.os, "getgroups", lambda: [42, 99] if mutation == "supplementary" else [42])
    monkeypatch.setattr(login.os, "getegid", lambda: 42)
    monkeypatch.setenv("HOME", str(login.HOME))
    monkeypatch.setenv("HERMES_HOME", str(login.PROFILE))
    monkeypatch.setattr(login, "RELEASE", Path(sys.executable).resolve().parent)
    nnp = "0" if mutation == "nnp" else "1"
    cap = "0000000000000001" if mutation == "capability" else "0000000000000000"
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw:
        f"NoNewPrivs: {nnp}\nCapEff: {cap}\nCapAmb: 0000000000000000\n")
    directory = SimpleNamespace(st_uid=1000, st_mode=stat.S_IFDIR | (0o777 if mutation == "unsafe-directory" else 0o700))
    monkeypatch.setattr(Path, "lstat", lambda *a: directory)
    monkeypatch.setattr(Path, "stat", lambda *a, **kw: directory)
    monkeypatch.setattr(login.os.path, "lexists", lambda path: mutation == "existing-auth")
    monkeypatch.setattr(login.os, "access", lambda *a: mutation == "human-readable")
    monkeypatch.setattr(login, "read_private", lambda name, uid:
        login.EXPECTED_CONFIG if name == "config.yaml" else b"PRIVATE_SETTINGS_SENTINEL")
    if mutation == "none":
        uid, snapshots = login.preflight(True)
        assert uid == 1000 and snapshots["config.yaml"] == login.EXPECTED_CONFIG
    else:
        with pytest.raises(login.LoginError): login.preflight(True)


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "public-mode"])
def test_private_auth_reader_refuses_unsafe_files_without_changing_them(login, tmp_path, monkeypatch, unsafe):
    monkeypatch.setattr(login, "PROFILE", tmp_path)
    target = tmp_path / "original"
    target.write_bytes(b"PRIVATE_STORED_TOKEN_SENTINEL")
    target.chmod(0o600)
    destination = tmp_path / "auth.json"
    if unsafe == "symlink": destination.symlink_to(target)
    elif unsafe == "hardlink": os.link(target, destination)
    else:
        destination.write_bytes(target.read_bytes())
        destination.chmod(0o644)
    with pytest.raises((login.LoginError, OSError)):
        login.read_private("auth.json", os.geteuid())
    assert target.read_bytes() == b"PRIVATE_STORED_TOKEN_SENTINEL"
