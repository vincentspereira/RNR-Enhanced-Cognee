"""Ordinary credential scope, preservation, denial and privilege regressions."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest


@pytest.fixture
def access():
    path = Path("integrations/hermes/deployment/provision_pilot_access.py").resolve()
    spec = importlib.util.spec_from_file_location("pilot_access", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bundle(access):
    return access.make_bundle(b"synthetic-signing-key-used-only-by-tests-123456", 1700000000)


def test_generated_token_matches_existing_pyjwt_contract(access, bundle):
    key = b"synthetic-signing-key-used-only-by-tests-123456"
    claims = jwt.decode(bundle["token"], key, algorithms=["HS256"], options={"verify_exp": False})
    assert claims == dict(access.IDENTITY, iat=1700000000, exp=1700086400)
    assert claims["roles"] == ["api_client"] and claims["capture_policy"] == "selected"
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(bundle["expired"], key, algorithms=["HS256"])
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(bundle["altered"], key, algorithms=["HS256"])
    assert b"synthetic-signing-key" not in json.dumps(bundle).encode()


@pytest.mark.parametrize("mutation", ["match", "different", "short", "not-string"])
def test_only_matching_protected_operator_api_signing_keys_are_used(access, monkeypatch, mutation):
    key = "synthetic-private-key-12345678901234567890"
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    monkeypatch.setattr(access, "open_directory", lambda path, owners: fd)
    names = []
    def read(directory, name, uid):
        assert directory == fd and uid == 0
        names.append(name)
        value = key
        if mutation == "different" and name == "api.json": value = key + "other"
        elif mutation == "short": value = "tiny"
        elif mutation == "not-string": value = 123
        return json.dumps({"ENHANCED_JWT_SECRET": value}).encode(), None
    monkeypatch.setattr(access, "read_private_at", read)
    if mutation == "match":
        assert access.load_signing_key() == key.encode()
        assert names == ["operator.json", "api.json"]
    else:
        with pytest.raises(access.ProvisionError) as error:
            access.load_signing_key()
        assert key not in str(error.value)


@pytest.mark.parametrize("raw", [b"", b"# original comment", b"OTHER=original\r\n", b"MULTILINE=\"one\ntwo\"\n", b"DUP=one\nDUP=two\n"])
def test_environment_preserves_original_bytes_and_values(access, bundle, raw):
    updated = access.prepare_environment(raw, bundle["token"])
    assert updated.startswith(raw + b"\n# Scoped")
    assert updated.count(access.TOKEN_NAME.encode() + b"=") == 1


@pytest.mark.parametrize("raw", [
    b"ENHANCED_COGNEE_ACCESS_TOKEN=existing-private-token\n",
    b" export ENHANCED_COGNEE_ACCESS_TOKEN = old\n",
    b"ENHANCED_COGNEE_ACCESS_TOKEN=\n", b"BROKEN=\"unterminated\n",
    b"A=one\x00two", b"\xff", b"#" * 65537])
def test_existing_credentials_or_bad_environment_are_refused_without_echo(access, bundle, raw):
    with pytest.raises((access.ProvisionError, UnicodeError)) as error:
        access.prepare_environment(raw, bundle["token"])
    assert "existing-private-token" not in str(error.value)


def test_credential_newline_injection_is_refused(access):
    with pytest.raises(access.ProvisionError):
        access.prepare_environment(b"OTHER=keep\n", "token\nEVIL=value")


def good_status(access):
    return {"ready": True, "tenant_id": access.IDENTITY["tenant"],
            "project_id": access.IDENTITY["project_id"], "subject": access.IDENTITY["sub"],
            "schema_version": 3, "encryption": "AES-256-GCM", "active_records": 0,
            "pending_change_events": 0}


def test_api_negative_controls_and_fresh_scope_checked_before_writes(access, bundle):
    calls = []
    def request(token):
        calls.append(token)
        return (200, good_status(access)) if token == bundle["token"] else (401, {})
    access.qualify_access(bundle, request=request)
    assert calls == [None, bundle["expired"], bundle["altered"], bundle["token"]]


@pytest.mark.parametrize("status", [200, 302, 401])
def test_status_transport_is_fixed_loopback_without_redirect_or_proxy(access, monkeypatch, status):
    import http.client
    calls = []
    class Response:
        def read(self, limit):
            assert limit == 131073
            return b'{"ready":true}'
    reply = Response()
    reply.status = status
    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("127.0.0.1", 28080, 5)
        def request(self, method, path, headers):
            assert (method, path) == ("GET", "/v1/memories/status")
            assert headers == {"Authorization": "Bearer ordinary-synthetic-token"}
            calls.append("request")
        def getresponse(self): return reply
        def close(self): calls.append("closed")
    monkeypatch.setattr(http.client, "HTTPConnection", Connection)
    code, data = access.api_status("ordinary-synthetic-token")
    assert code == status and data == ({"ready": True} if status == 200 else {})
    assert calls == ["request", "closed"]


@pytest.mark.parametrize("mutation", ["unauth", "expired", "altered", "redirect", "project", "tenant", "subject", "ready", "schema", "encryption", "records", "pending", "boolean-count"])
def test_api_scope_or_denial_failures_stop_provisioning(access, bundle, mutation):
    data = good_status(access)
    changes = {"project": ("project_id", "other"), "tenant": ("tenant_id", "other"),
               "subject": ("subject", "other"), "ready": ("ready", False),
               "schema": ("schema_version", 2), "encryption": ("encryption", "none"),
               "records": ("active_records", 1), "pending": ("pending_change_events", 1),
               "boolean-count": ("active_records", False)}
    if mutation in changes:
        field, value = changes[mutation]
        data[field] = value
    def request(token):
        if token == bundle["token"]:
            return (302 if mutation == "redirect" else 200), data
        if ((mutation == "unauth" and token is None)
                or (mutation in {"expired", "altered"} and token == bundle[mutation])):
            return 200, {}
        return 401, {}
    with pytest.raises(access.ProvisionError):
        access.qualify_access(bundle, request=request)


def open_profile(access, tmp_path):
    path = tmp_path / "profile"
    path.mkdir(mode=0o700)
    env = path / ".env"
    env.write_bytes(b"OTHER=ORIGINAL_PRIVATE_VALUE\n")
    env.chmod(0o600)
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    original_fd = os.open(env, os.O_RDONLY)
    return path, directory, original_fd


def test_install_keeps_private_exact_backup_and_original_values(access, bundle, tmp_path):
    path, directory, original_fd = open_profile(access, tmp_path)
    try:
        raw = (path / ".env").read_bytes()
        phases = []
        backup = access.install_environment(directory, original_fd, raw, bundle["token"], os.getuid(), phases.append)
        assert (path / backup).read_bytes() == raw
        assert (path / ".env").read_bytes().startswith(raw)
        assert (path / ".env").stat().st_mode & 0o777 == 0o600
        assert (path / backup).stat().st_mode & 0o777 == 0o600
        assert phases == ["environment_backup", "environment_publication", "environment_readback"]
        assert {p.name for p in path.iterdir()} == {".env", backup}
        installed = (path / ".env").read_bytes()
        with pytest.raises(access.ProvisionError):
            access.install_environment(directory, original_fd, installed, bundle["token"], os.getuid(), phases.append)
        assert (path / ".env").read_bytes() == installed
    finally:
        os.close(original_fd)
        os.close(directory)


@pytest.mark.parametrize("mutation", ["content", "replacement", "symlink"])
def test_concurrent_changes_are_preserved_before_publication(access, bundle, tmp_path, mutation):
    path, directory, original_fd = open_profile(access, tmp_path)
    try:
        raw = (path / ".env").read_bytes()
        def phase(value):
            if value != "environment_publication": return
            if mutation == "content":
                (path / ".env").write_bytes(b"CONCURRENT=KEEP_THIS\n")
            else:
                (path / ".env").rename(path / "original-retained")
                if mutation == "replacement":
                    (path / ".env").write_bytes(b"CONCURRENT=KEEP_THIS\n")
                    (path / ".env").chmod(0o600)
                else:
                    (path / "untouched-target").write_bytes(b"CONCURRENT=KEEP_THIS\n")
                    (path / ".env").symlink_to("untouched-target")
        with pytest.raises(access.ProvisionError):
            access.install_environment(directory, original_fd, raw, bundle["token"], os.getuid(), phase)
        assert (path / ".env").read_bytes() == b"CONCURRENT=KEEP_THIS\n"
        assert list(path.glob(".env-before-cognee-pilot-*"))[0].read_bytes() == raw
    finally:
        os.close(original_fd)
        os.close(directory)


@pytest.mark.parametrize("mutation", ["public", "hardlink", "symlink", "large"])
def test_private_file_protection_failures_preserve_contents(access, tmp_path, mutation):
    path, directory, original_fd = open_profile(access, tmp_path)
    try:
        if mutation == "public": (path / ".env").chmod(0o644)
        elif mutation == "hardlink": os.link(path / ".env", path / "alias")
        elif mutation == "symlink":
            (path / ".env").rename(path / "retained")
            (path / ".env").symlink_to("retained")
        else: (path / ".env").write_bytes(b"x" * 65537)
        before = (path / ".env").read_bytes()
        with pytest.raises((access.ProvisionError, OSError)):
            access.read_private_at(directory, ".env", os.getuid())
        assert (path / ".env").read_bytes() == before
    finally:
        os.close(original_fd)
        os.close(directory)


def receipt(access, bundle):
    return {"complete": True, "effective_user": "hermes-runtime", "credential_installed": True,
            "environment_backup": ".env-before-cognee-pilot-" + "a" * 32,
            "tenant": access.IDENTITY["tenant"], "project": access.IDENTITY["project_id"],
            "subject": access.IDENTITY["sub"], "role": "api_client", "capture_policy": "selected",
            "expires_utc": access.datetime.fromtimestamp(bundle["claims"]["exp"], access.timezone.utc).isoformat(),
            "authenticated_api_status_passed": True, "unauthenticated_expired_altered_denied": True,
            "provider_selected": False, "model_called": False, "memory_records_written": False,
            "runtime_qualified": False}


def test_process_receives_only_ordinary_tokens_after_uid_drop(access, bundle, monkeypatch):
    source = Path(access.__file__).read_bytes()
    def run(command, **options):
        assert command[:4] == ["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env"]
        assert "-i" in command and "-I" in command and "-B" in command
        assert options["user"] == 993 and options["group"] == 985 and options["extra_groups"] == ()
        assert options["cwd"] == access.HOME
        assert json.loads(options["input"]) == bundle
        assert b"synthetic-signing-key" not in options["input"]
        assert all(bundle["token"] not in value for value in command)
        assert not any("KEY" in key or "TOKEN" in key for key in options["env"])
        compile(command[-1], "restricted-child-command", "exec")
        assert len(command[-1].encode()) < 131072
        return SimpleNamespace(returncode=0, stdout=json.dumps(receipt(access, bundle)).encode(), stderr=b"")
    monkeypatch.setattr(access.subprocess, "run", run)
    assert access.run_child(SimpleNamespace(pw_uid=993, pw_gid=985), source, bundle)["credential_installed"]


@pytest.mark.parametrize("mutation", ["extra", "identity", "role", "backup", "integer-flag", "failure", "private-failure"])
def test_unexpected_child_outputs_never_echo_private_values(access, bundle, monkeypatch, mutation):
    data = receipt(access, bundle)
    code = 0
    if mutation == "extra": data["private"] = "PRIVATE_TEST_SENTINEL"
    elif mutation == "identity": data["effective_user"] = "root"
    elif mutation == "role": data["role"] = "admin"
    elif mutation == "backup": data["environment_backup"] = "../../PRIVATE_TEST_SENTINEL"
    elif mutation == "integer-flag": data["complete"] = 1
    else:
        code = 1
        data = {"complete": False, "failure_stage": "api_checks" if mutation == "failure" else "PRIVATE_TEST_SENTINEL"}
    monkeypatch.setattr(access.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=code, stdout=json.dumps(data).encode(), stderr=b"PRIVATE_TEST_SENTINEL"))
    with pytest.raises(access.ProvisionError) as error:
        access.run_child(SimpleNamespace(pw_uid=993, pw_gid=985), b"# reviewed", bundle)
    assert "PRIVATE_TEST_SENTINEL" not in str(error.value)


def test_wrong_operator_stops_before_keys_are_read(access, monkeypatch):
    monkeypatch.setattr(access.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(access, "load_signing_key", lambda: pytest.fail("No key read permitted"))
    with pytest.raises(SystemExit, match="approved human"):
        access.main(b"# reviewed")
