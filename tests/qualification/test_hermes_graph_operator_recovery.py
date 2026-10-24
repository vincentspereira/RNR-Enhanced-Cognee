"""Hash/schema preservation contracts; installed stop/start remains operator work."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/recover_launch_graph_operator.py"
spec = importlib.util.spec_from_file_location("graph_operator_recovery", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_hash_uses_base64_salt_text_as_documented_for_installed_format():
    salt = base64.b64encode(bytes(range(32))).decode("ascii")
    encoded = helper.password_hash("invented-only-password", salt)
    expected = hashlib.pbkdf2_hmac("sha256", b"invented-only-password", salt.encode(), 65536, 32)
    assert encoded.split("$")[-1] == base64.b64encode(expected).decode()
    assert helper.matches("invented-only-password", encoded)
    assert not helper.matches("different-invented-password", encoded)
    assert not helper.matches("invented-only-password", "unsupported$format")


def test_only_builtin_root_hash_changes_and_service_lines_are_byte_preserved():
    worker = b'{ "name": "worker", "password": "preserve-hash", "databases": {"memory":["writer"]}}\n'
    root = {"name": "root", "password": "old-hash", "databases": {"*": ["admin"]}, "extra": "preserve"}
    original = worker + json.dumps(root).encode()+b"\n"
    updated, rows = helper.replace_root(original, "invented-replacement")
    assert updated.startswith(worker)
    result = json.loads(updated.splitlines()[1])
    assert result == dict(root, password=result["password"])
    assert helper.matches("invented-replacement", result["password"])
    assert rows[1] == root


@pytest.mark.parametrize("rows", [[], [{"name":"worker","password":"hash","databases":{}}],
    [{"name":"root","password":"hash","databases":{}}]*2, [{"name":"root"}]])
def test_ambiguous_or_unsupported_user_file_refused(rows):
    raw = b"\n".join(json.dumps(row).encode() for row in rows)
    with pytest.raises(ValueError, match="unique_builtin_root_schema_required"):
        helper.replace_root(raw, "invented-only-password")


def test_ordinary_user_cannot_read_stage_or_stop_service(monkeypatch):
    monkeypatch.setattr(helper.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(helper, "read_file", lambda *a: pytest.fail("must not read secret"))
    monkeypatch.setattr(helper, "control", lambda *a: pytest.fail("must not control service"))
    with pytest.raises(ValueError, match="local_root_operator_required"):
        helper.main()


def test_failed_new_authentication_restores_original_users_and_restarts(monkeypatch, tmp_path, capsys):
    original = b'{"name":"root","password":"old","databases":{"*":["admin"]}}\n'
    original += json.dumps({"name":"worker","password":helper.password_hash("invented-worker"),
                           "databases":{"memory":["writer"]}}).encode()+b"\n"
    users = tmp_path / "users"
    state = {users: original}
    worker = {"INDEX_ARCADEDB_USER":"worker", "INDEX_ARCADEDB_PASSWORD":"invented-worker"}
    candidates = {"arcadedb":{"operator":{"password":"invented-"+"x"*40}}}
    calls = []
    monkeypatch.setattr(helper, "STAGE", tmp_path)
    monkeypatch.setattr(helper, "USERS", users)
    monkeypatch.setattr(helper, "AUTHORITY", tmp_path / "no-existing-authority")
    monkeypatch.setattr(helper.os, "geteuid", lambda: 0)
    monkeypatch.setattr(helper.pwd, "getpwnam", lambda name: SimpleNamespace(pw_uid=995))
    def read(path, owner):
        if path in state:
            return state[path]
        if path.name == "replacement-logins.private.json":
            return json.dumps(candidates).encode()
        if path.name in {"api.json", "worker.json"}:
            return json.dumps(worker).encode()
        return b"{}"
    monkeypatch.setattr(helper, "read_file", read)
    monkeypatch.setattr(helper, "private_write", lambda path, raw: path.write_bytes(raw))
    monkeypatch.setattr(helper, "replace_file", lambda path, raw, owner: state.update({path:raw}))
    monkeypatch.setattr(helper, "control", lambda action: calls.append(action))
    monkeypatch.setattr(helper, "graph_status", lambda name, password: 200 if password == "invented-worker" else 403)
    monkeypatch.setattr(helper, "await_status", lambda name, password: name == "worker")
    monkeypatch.setattr(helper.signal, "signal", lambda *args: None)
    assert helper.main() == 1
    assert state[users] == original
    assert calls == ["stop", "start", "stop", "start"]
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["rollback_worker_authenticated"] is True
    assert receipt["complete"] is False
