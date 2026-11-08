"""Offline renewal regression tests; never touch installed credentials or systemd."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment"


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def renewal():
    return load("renew_fleet_memory_tokens")


@pytest.mark.parametrize("outcome", [
    subprocess.TimeoutExpired("synthetic", 180, output=b"SECRET"),
    OSError("SECRET"),
    subprocess.CompletedProcess([], 7, b'{"complete":true,"profile":"default","expires_utc":"2099-01-01T00:00:00Z"}'),
    subprocess.CompletedProcess([], 0, b'[]'),
    subprocess.CompletedProcess([], 0, b'null'),
    subprocess.CompletedProcess([], 0, b'not-json-SECRET'),
    subprocess.CompletedProcess([], 0, b'{"complete":"true"}'),
    subprocess.CompletedProcess([], 0, b'{"complete":1}'),
    subprocess.CompletedProcess([], 0, b'{"complete":true,"profile":"other","expires_utc":"2099-01-01T00:00:00Z"}'),
    subprocess.CompletedProcess([], 0, b'{"complete":true,"profile":"default","expires_utc":"2099-01-01T00:00:00Z"}'),
])
def test_renew_rejects_untrusted_results_without_leaking(renewal, monkeypatch, outcome):
    def run(*args, **kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(renewal.subprocess, "run", run)
    result = renewal.renew("default")
    assert result["complete"] is False
    assert result["profile"] == "default"
    assert "SECRET" not in json.dumps(result)


def test_renew_validates_receipt_and_uses_system_isolated_python(renewal, monkeypatch):
    expiry = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + renewal.TTL_HOURS * 3600))
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps({"complete": True, "profile": "default", "expires_utc": expiry}).encode())
    monkeypatch.setattr(renewal.subprocess, "run", run)
    assert renewal.renew("default")["complete"] is True
    # The provisioner needs python-dotenv, absent from the OS Python. Use the
    # existing protected runtime, whose resolved chain is checked before use.
    assert commands[0][:3] == [str(renewal.PROVISIONER_PYTHON), "-I", "-B"]
    assert str(renewal.PROVISIONER_PYTHON).startswith("/opt/")


def test_main_continues_after_timeout_and_atomically_publishes_state(renewal, monkeypatch, tmp_path):
    monkeypatch.setattr(renewal.os, "geteuid", lambda: 0)
    monkeypatch.setattr(renewal, "profiles", lambda: ["default", "web-researcher"])
    monkeypatch.setattr(renewal, "HOME", tmp_path)
    monkeypatch.setattr(renewal, "PROVISIONER", tmp_path / "provisioner.py")
    renewal.PROVISIONER.touch()
    monkeypatch.setattr(renewal, "STATE", tmp_path / "state.json")
    renewal.STATE.write_text('{"original":true}')
    now = int(time.time())
    expiry = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + renewal.TTL_HOURS * 3600))
    attempts = []
    def run(command, **kwargs):
        attempts.append(command)
        if len(attempts) == 1:
            raise subprocess.TimeoutExpired("synthetic", 180)
        return subprocess.CompletedProcess(command, 0, json.dumps({"complete": True, "profile": "web-researcher", "expires_utc": expiry}).encode())
    monkeypatch.setattr(renewal.subprocess, "run", run)
    # Runtime path checks are covered separately; no production root tree used.
    monkeypatch.setattr(renewal, "validate_runtime", lambda: None, raising=False)
    replacements, syncs = [], []
    real_replace, real_fsync = renewal.os.replace, renewal.os.fsync
    def replace(src, dst, **kwargs):
        replacements.append((src, dst))
        return real_replace(src, dst, **kwargs)
    def fsync(fd):
        syncs.append(fd)
        return real_fsync(fd)
    monkeypatch.setattr(renewal.os, "replace", replace)
    monkeypatch.setattr(renewal.os, "fsync", fsync)
    assert renewal.main() == 1
    state = json.loads(renewal.STATE.read_text())
    assert len(attempts) == 2
    assert state["renewed"] == ["web-researcher"]
    assert state["failed"][0]["profile"] == "default"
    assert replacements and len(syncs) >= 2


def test_inventory_is_complete_data_only_and_does_not_read_user_receipts(renewal, monkeypatch, tmp_path):
    inventory = tmp_path / "roles.json"
    monkeypatch.setattr(renewal, "INVENTORY", inventory, raising=False)
    monkeypatch.setattr(renewal, "trusted_path", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(renewal, "RECEIPTS", tmp_path / "missing.json")
    # AST inspection is data-only; never execute the enablement module.
    import ast
    tree = ast.parse((DEPLOY / "enable_fleet_memory_mcp.py").read_text())
    roles = next(ast.literal_eval(n.value.keys[0]) for n in [] ) if False else None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ROLE_GROUPS" for t in node.targets):
            roles = sorted(["default"] + [ast.literal_eval(k) for k in node.value.keys])
    inventory.write_text(json.dumps({"schema": 1, "profiles": roles}))
    assert len(roles) == 45
    assert renewal.profiles() == roles
    for invalid in [roles + [roles[0]], roles[:-1], roles[:-1] + ["../evil"], roles[:-1] + ["enhanced-cognee-test"]]:
        inventory.write_text(json.dumps({"schema": 1, "profiles": invalid}))
        with pytest.raises(ValueError):
            renewal.profiles()


def test_trusted_path_checks_ancestors_owner_mode_and_symlinks(renewal, tmp_path):
    import os
    root = tmp_path / "trusted"
    root.mkdir(mode=0o700)
    file = root / "job.py"
    file.write_text("safe")
    file.chmod(0o600)
    # trust_root narrows only sandbox tests; production always walks from '/'.
    renewal.trusted_path(file, uid=os.getuid(), trust_root=tmp_path)
    with pytest.raises(ValueError):
        renewal.trusted_path(file)  # real ordinary-user tree is NOT root trusted
    file.chmod(0o622)
    with pytest.raises(ValueError):
        renewal.trusted_path(file, uid=os.getuid(), trust_root=tmp_path)
    file.chmod(0o600)
    root.chmod(0o722)
    with pytest.raises(ValueError):
        renewal.trusted_path(file, uid=os.getuid(), trust_root=tmp_path)
    root.chmod(0o700)
    link = root / "link"
    link.symlink_to(file)
    with pytest.raises(ValueError):
        renewal.trusted_path(link, uid=os.getuid(), trust_root=tmp_path)


def test_runtime_preflight_is_before_any_profile_access(renewal, monkeypatch):
    monkeypatch.setattr(renewal.os, "geteuid", lambda: 0)
    checked = []
    def refuse():
        checked.append("preflight")
        raise ValueError("unsafe_runtime")
    monkeypatch.setattr(renewal, "validate_runtime", refuse, raising=False)
    monkeypatch.setattr(renewal, "profiles", lambda: pytest.fail("profile accessed before trust check"))
    with pytest.raises(ValueError, match="unsafe_runtime"):
        renewal.main()
    assert checked == ["preflight"]
