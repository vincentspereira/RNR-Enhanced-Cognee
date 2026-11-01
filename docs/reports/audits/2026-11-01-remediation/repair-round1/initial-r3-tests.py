"""Round-1 review regressions; sandbox files, invented tokens, no launches.

R1/R2/R3 and inventory cases derive from the preserved independent v2 review.
REPO is located from this file; no protected tree, profiles or live API is read.
"""
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
DEPLOY = REPO / "integrations/hermes/deployment"
REAL_LSTAT = Path.lstat


def load(path):
    spec = importlib.util.spec_from_file_location("round1_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def root_tree(monkeypatch):
    # Keep real symlinks, resolution and file types. Only owner/mode metadata
    # is synthetic; preserve explicit unsafe directories. Never chown anything.
    unsafe = set()

    def synthetic_root_lstat(path):
        values = list(REAL_LSTAT(path))
        values[4] = 0
        if path not in unsafe:
            values[0] &= ~0o022
        return os.stat_result(values)

    monkeypatch.setattr(Path, "lstat", synthetic_root_lstat)
    return unsafe


def setup_renewal_tree(tmp_path):
    runtime = tmp_path / "runtime"
    binary_dir = runtime / "bin"
    binary_dir.mkdir(parents=True, mode=0o755)
    alias = binary_dir / "python"
    alias.symlink_to(Path("/usr/bin/python3").resolve())
    (runtime / "pyvenv.cfg").write_text("home = /usr/bin\n")
    provisioner = tmp_path / "provision_gateway_profile_access.py"
    provisioner.write_bytes((DEPLOY / provisioner.name).read_bytes())
    inventory = tmp_path / "roles.json"
    inventory.write_bytes((DEPLOY / "roles.json").read_bytes())
    return alias, provisioner, inventory


def renewal_fixture(tmp_path, monkeypatch):
    renewal = load(DEPLOY / "renew_fleet_memory_tokens.py")
    alias, provisioner, inventory = setup_renewal_tree(tmp_path)
    monkeypatch.setattr(renewal, "PROVISIONER_PYTHON", alias)
    monkeypatch.setattr(renewal, "PROVISIONER", provisioner)
    monkeypatch.setattr(renewal, "INVENTORY", inventory)
    return renewal, alias


def installer_fixture(tmp_path, monkeypatch):
    installer = load(DEPLOY / "install_fleet_token_renewal.py")
    stage = tmp_path / "stage"
    stage.mkdir()
    for name in ("roles.json", "provision_gateway_profile_access.py",
                 "renew_fleet_memory_tokens.py", "install_fleet_token_renewal.py"):
        (stage / name).write_bytes((DEPLOY / name).read_bytes())
    alias, _, _ = setup_renewal_tree(tmp_path / "runtime-fixture")
    target = tmp_path / "installed"
    target.mkdir()
    for name in ("provision_gateway_profile_access.py", "renew_fleet_memory_tokens.py"):
        (target / name).write_bytes((DEPLOY / name).read_bytes())
    service = tmp_path / "renewal.service"
    monkeypatch.setattr(installer, "DEPLOY", stage)
    monkeypatch.setattr(installer, "__file__", str(stage / "install_fleet_token_renewal.py"))
    monkeypatch.setattr(installer, "RENEWAL_ROOT", target)
    monkeypatch.setattr(installer, "SERVICE", service)
    monkeypatch.setattr(installer, "PROVISIONER_PYTHON", alias)
    service.write_text(installer.unit_text())
    monkeypatch.setattr(installer.os, "geteuid", lambda: 0)
    monkeypatch.setattr(installer.os, "uname", lambda: SimpleNamespace(nodename="Ubuntu-Hermes"))
    monkeypatch.setattr(installer.sys, "argv", ["installer", "--upgrade"])
    calls = []

    def systemctl(*args):
        calls.append(args)
        if args[0] == "is-active":
            return 3, "inactive"
        if args[0] == "show":
            return 0, "/usr/bin/python3 -I -B /opt/enhanced-cognee-memory/fleet-renewal/renew_fleet_memory_tokens.py"
        return 0, ""

    monkeypatch.setattr(installer, "systemctl", systemctl)
    return installer, alias, target, calls


def test_root_runtime_positive_control(tmp_path, monkeypatch, root_tree):
    renewal, _ = renewal_fixture(tmp_path, monkeypatch)
    renewal.validate_runtime()


@pytest.mark.parametrize("unsafe_part", ["bin", "runtime"])
def test_root_runtime_rejects_replaceable_interpreter_alias(
        tmp_path, monkeypatch, root_tree, unsafe_part):
    renewal, alias = renewal_fixture(tmp_path, monkeypatch)
    unsafe = alias.parent if unsafe_part == "bin" else alias.parent.parent
    unsafe.chmod(0o777)
    root_tree.add(unsafe)
    with pytest.raises(ValueError, match="untrusted_runtime_path"):
        renewal.validate_runtime()


def test_runtime_validates_os_interpreter_lexical_parent(tmp_path, monkeypatch, root_tree):
    renewal, _ = renewal_fixture(tmp_path, monkeypatch)
    checked = []
    trusted = renewal.trusted_path

    def record(path):
        checked.append(path)
        trusted(path)

    monkeypatch.setattr(renewal, "trusted_path", record)
    renewal.validate_runtime()
    assert Path("/usr/bin/python3").parent in checked


def test_installer_rejects_replaceable_interpreter_before_launch(
        tmp_path, monkeypatch, root_tree):
    installer, alias, _, calls = installer_fixture(tmp_path, monkeypatch)
    alias.parent.chmod(0o777)
    root_tree.add(alias.parent)
    launches = []

    def no_launch(command, **kwargs):
        launches.append(command)
        return subprocess.CompletedProcess(command, 1, b"", b"")

    monkeypatch.setattr(installer.subprocess, "run", no_launch)
    with pytest.raises(ValueError):
        installer.main()
    assert launches == [], "replaceable exec path reached subprocess"
    assert calls == [], "replaceable exec path reached systemctl"


def mcp_rpc(body, monkeypatch):
    mcp = load(REPO / "integrations/hermes/enhanced_cognee_mcp/server.py")

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda size: body)

        def close(self):
            pass

    monkeypatch.setattr(mcp, "HTTPConnection", Connection)
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "get_stats", "arguments": {}}}
    output = io.StringIO()
    with patch("sys.stdin", io.StringIO(json.dumps(message) + "\n")), patch("sys.stdout", output):
        mcp.serve(mcp.handlers("invented-review-placeholder"))
    return json.loads(output.getvalue())["result"]


@pytest.mark.parametrize("body", [
    b"", b"null", b"[]", b"true", b"false", b"17", b"1.5",
    b'"invented-private-response"', b'["invented-private-response"]',
    b"not-json-invented-private-response", b"\xffinvented-private-response",
])
def test_mcp_rejects_http_200_invalid_response_shapes(body, monkeypatch):
    result = mcp_rpc(body, monkeypatch)
    assert result.get("isError") is True
    payload = json.loads(result["content"][0]["text"])
    assert payload["error"] in {"memory response was not a JSON object",
                                "memory response was not JSON"}
    assert "invented-private-response" not in json.dumps(result)


@pytest.mark.parametrize("body", [b"{}", b'{"ready":true,"project_id":"invented"}'])
def test_mcp_object_reply_positive_control(body, monkeypatch):
    result = mcp_rpc(body, monkeypatch)
    assert not result.get("isError", False)
    assert json.loads(result["content"][0]["text"]) == json.loads(body)


def invented_token(exp):
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).rstrip(b"=").decode()
    return "a" * 16 + "." + payload + "." + "a" * 16


@pytest.mark.parametrize("exp", [10**100, 253402300800, 0, -1, True, 1.5])
def test_r3_decoder_rejects_unsupported_expiry(exp):
    renewal = load(DEPLOY / "renew_fleet_memory_tokens.py")
    with pytest.raises(ValueError):
        renewal.decode_exp(invented_token(exp))


@pytest.mark.parametrize("exp", [1, 253402300799])
def test_r3_decoder_supported_expiry_positive_control(exp):
    renewal = load(DEPLOY / "renew_fleet_memory_tokens.py")
    assert renewal.decode_exp(invented_token(exp)) == exp


@pytest.mark.parametrize("error", [OverflowError, OSError, ValueError])
def test_r3_decoder_rejects_platform_unrepresentable_expiry(monkeypatch, error):
    renewal = load(DEPLOY / "renew_fleet_memory_tokens.py")

    def unavailable(exp):
        raise error("invented-private-timestamp")

    monkeypatch.setattr(renewal.time, "gmtime", unavailable)
    with pytest.raises(ValueError) as caught:
        renewal.decode_exp(invented_token(1800000000))
    assert "invented-private-timestamp" not in str(caught.value)


# Direct copy of independent v2 lines 174-194. The sole semantic change is
# line 178's old-bug precondition: the repaired decoder must now reject it.
def test_renewal_unrepresentable_expiry_does_not_abort_remaining_profiles(tmp_path, monkeypatch):
    renewal = load(DEPLOY / 'renew_fleet_memory_tokens.py')
    payload = base64.urlsafe_b64encode(json.dumps({'exp':10**100}).encode()).rstrip(b'=').decode()
    token = 'a' * 16 + '.' + payload + '.' + 'a' * 16
    with pytest.raises(ValueError):
        renewal.decode_exp(token)
    monkeypatch.setattr(renewal.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(renewal.os, 'uname', lambda: SimpleNamespace(nodename='Ubuntu-Hermes'))
    monkeypatch.setattr(renewal, 'validate_runtime', lambda: None)
    monkeypatch.setattr(renewal, 'PROVISIONER', tmp_path / 'provisioner.py')
    renewal.PROVISIONER.write_text('# no executable content\n')
    monkeypatch.setattr(renewal, 'profiles', lambda: ['default', 'web-researcher'])
    monkeypatch.setattr(renewal, 'load_profile_token', lambda path: token)
    monkeypatch.setattr(renewal, 'STATE', tmp_path / 'state.json')
    attempted = []
    def fake_renew(profile):
        attempted.append(profile)
        return {'profile':profile,'complete':False,'expires_utc':None,'error':'invented-refusal'}
    monkeypatch.setattr(renewal, 'renew', fake_renew)
    # No exception should escape a single malformed profile and abort the fleet.
    assert renewal.main() == 1
    assert 'web-researcher' in attempted


@pytest.mark.parametrize("problem", ["huge", "unicode", "load", "format", "malformed"])
def test_r3_main_continues_and_publishes_state(tmp_path, monkeypatch, capsys, problem):
    renewal = load(DEPLOY / "renew_fleet_memory_tokens.py")
    monkeypatch.setattr(renewal.os, "geteuid", lambda: 0)
    monkeypatch.setattr(renewal.os, "uname", lambda: SimpleNamespace(nodename="Ubuntu-Hermes"))
    monkeypatch.setattr(renewal, "validate_runtime", lambda: None)
    monkeypatch.setattr(renewal, "HOME", tmp_path)
    monkeypatch.setattr(renewal, "PROVISIONER", tmp_path / "provisioner.py")
    renewal.PROVISIONER.write_text("# no executable content\n")
    monkeypatch.setattr(renewal, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(renewal, "profiles", lambda: ["default", "web-researcher", "writer"])
    now, later = 1800000000, 1801000000
    monkeypatch.setattr(renewal.time, "time", lambda: now)
    env = tmp_path / ".env"
    bad_token = invented_token(10**100)
    raw = renewal.TOKEN_NAME + "=" + (invented_token(later) if problem == "format" else bad_token)
    env.write_bytes(b"\xffinvented-private-profile" if problem == "unicode" else raw.encode())
    good_env = tmp_path / "profiles/writer/.env"
    good_env.parent.mkdir(parents=True)
    good_env.write_text(renewal.TOKEN_NAME + "=" + invented_token(later + 1))
    original_load = renewal.load_profile_token

    def load_token(path):
        if path == env and problem == "load":
            raise OSError("invented-private-profile")
        if path == env and problem == "malformed":
            return "invented-private-profile-not-a-token"
        return original_load(path)

    monkeypatch.setattr(renewal, "load_profile_token", load_token)
    strftime = renewal.time.strftime

    def format_utc(fmt, value):
        if problem == "format" and value == renewal.time.gmtime(later):
            raise OverflowError("invented-private-profile")
        return strftime(fmt, value)

    monkeypatch.setattr(renewal.time, "strftime", format_utc)
    attempted = []

    def fake_renew(profile):
        attempted.append(profile)
        return {"profile": profile, "complete": profile == "web-researcher",
                "expires_utc": "2027-02-14T08:00:00Z" if profile == "web-researcher" else None,
                "error": None if profile == "web-researcher" else "invalid_receipt"}

    monkeypatch.setattr(renewal, "renew", fake_renew)
    assert renewal.main() == 1
    state_raw = renewal.STATE.read_text()
    state = json.loads(state_raw)
    assert attempted == ["default", "web-researcher"]
    assert state["renewed"] == ["web-researcher"]
    assert state["skipped"] == ["writer"]
    assert state["failed"] == [{"profile": "default", "complete": False,
                                "expires_utc": None, "error": "invalid_receipt"}]
    assert state["expires_utc"]["web-researcher"] == "2027-02-14T08:00:00Z"
    assert "writer" in state["expires_utc"] and state["token_values_emitted"] is False
    assert not list(tmp_path.glob(".state.json-stage-*"))
    output = capsys.readouterr()
    assert json.loads(output.out)["complete"] is False
    for private in [bad_token, invented_token(later), "invented-private-profile"]:
        assert private not in output.out + output.err + state_raw
