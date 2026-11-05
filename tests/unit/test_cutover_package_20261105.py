"""Offline unit tests for the 2026-11-05 cutover package helpers.

Invented fixtures only: a stub HTTP memory API, a fake api.json credential,
temporary sqlite ledgers built with the same DDL as src/llm_budget.py, and a
stub `age` executable. No live service, credential, root privilege or network
beyond 127.0.0.1 is used. Never run as root.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import http.server
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE_PATH = ROOT / "integrations/hermes/deployment/cutover_probe_20261105.py"
LEDGER_TOOLS_PATH = ROOT / "integrations/hermes/deployment/ledger_tools_20261105.py"
UNITS_DIR = ROOT / "docs/reports/audits/2026-11-05-cutover-package/units"

# Bind the exact bytes this package ships.
CUTOVER_DROPIN_SHA256 = ("f85e6fc63c58aa6275549fb36e4e1bc6ab31808d0af11f"
                         "5498feac8b31ffd4c7")
# The independently reviewed V3 proposal (owner-v3 plan dropin_sha256,
# 2026-11-03 owner step-2 receipt). Removing exactly the three StateDirectory
# lines from the cutover drop-in must reproduce it.
REVIEWED_V3_DROPIN_SHA256 = "40ee1d8b61322c49676666257531953ee7957db086269bbb25a0373ad4619651"

# Mirrors src/llm_budget.py CREATE TABLE/INDEX statements.
LEDGER_DDL = (
    "CREATE TABLE IF NOT EXISTS reservations ("
    "id TEXT PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL, "
    "day TEXT NOT NULL, tokens INTEGER NOT NULL CHECK(tokens >= 0), "
    "settled INTEGER NOT NULL DEFAULT 0 CHECK(settled IN (0,1)))",
    "CREATE INDEX IF NOT EXISTS budget_scope_day ON reservations(tenant,project,day)",
)

TEST_SECRET = "unit-test-signing-secret-0123456789abcdef"


def load_module(path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load_module(PROBE_PATH)
ledger_tools = load_module(LEDGER_TOOLS_PATH)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_credential(tmp_path):
    path = tmp_path / "api.json"
    path.write_text(json.dumps({"ENHANCED_JWT_SECRET": TEST_SECRET,
                                "ENHANCED_MEMORY_DATABASE_URL":
                                "postgres://user:pass@127.0.0.1:5/db"}), encoding="ascii")
    return str(path)


class StubAPI(http.server.BaseHTTPRequestHandler):
    """Stub of the plugin-facing memory API contract; verifies the bearer."""

    secret = TEST_SECRET
    summarize_status = {"configured": False, "used_today": None}
    ready = True
    seen_bearers = []

    def _verify_bearer(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        token = header[len("Bearer "):]
        StubAPI.seen_bearers.append(token)
        signing_input, _, signature = token.rpartition(".")
        expected = hmac.new(self.secret.encode(), signing_input.encode(),
                            hashlib.sha256).digest()
        pad = lambda data: data + b"=" * (-len(data) % 4)  # noqa: E731
        try:
            decoded = base64.urlsafe_b64decode(pad(signature.encode()))
            return hmac.compare_digest(decoded, expected)
        except Exception:
            return False

    def _send(self, status, body):
        raw = json.dumps(body).encode("ascii")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length)) if length else {}

    def _route(self, method):
        if not self._verify_bearer():
            self._send(401, {"detail": "unauthorized"})
            return
        path = self.path
        if path == "/health/ready":
            self._send(200 if StubAPI.ready else 503,
                       {"ready": StubAPI.ready} if StubAPI.ready else {"ready": False})
        elif path == "/v1/memories" and method == "POST":
            body = self._body()
            self._send(200, {"id": "rec-cutover-1", "version": 1,
                             "idempotency_key": body.get("idempotency_key")})
        elif path == "/v1/memories/recall" and method == "POST":
            self._send(200, {"results": [{"id": "rec-cutover-1"}]})
        elif path == "/v1/memories/summarize" and method == "POST":
            self._send(422, {"detail": probe.ANALYSIS_NOT_CONFIGURED})
        elif path == "/v1/memories/summarization/status":
            self._send(200, dict(StubAPI.summarize_status, project_id="p"))
        else:
            self._send(404, {"detail": "not found"})

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def log_message(self, *args):
        pass


@pytest.fixture()
def stub_server():
    StubAPI.seen_bearers = []
    StubAPI.ready = True
    StubAPI.summarize_status = {"configured": False, "used_today": None}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StubAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d" % server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture()
def ledger(tmp_path):
    path = tmp_path / "tokens.sqlite3"
    connection = sqlite3.connect(str(path))
    for statement in LEDGER_DDL:
        connection.execute(statement)
    connection.execute("INSERT INTO reservations(id,tenant,project,day,tokens) "
                       "VALUES('r1','t','p','2026-11-05',120)")
    connection.commit()
    connection.close()
    os.chmod(path, 0o600)
    return str(path)


@pytest.fixture()
def backup_credential(tmp_path):
    path = tmp_path / "backup.json"
    path.write_text(json.dumps({
        "ENHANCED_BACKUP_RECIPIENT": "age1unit-test-recipient-example-key",
        "ENHANCED_BACKUP_SIGNING_KEY": "unit-test-signing-key-0123456789abcdef",
        "ENHANCED_BACKUP_SIGNING_KEY_ID": "backup_v1"}), encoding="ascii")
    return str(path)


@pytest.fixture()
def age_stub(tmp_path):
    """Stub age CLI: identity 'encryption' and 'decryption' by copy."""
    stub = tmp_path / ("age-stub%s" % ("x" if os.name == "nt" else ""))
    stub.write_text("#!%s\n"
                    "import sys\n"
                    "args = sys.argv[1:]\n"
                    "if '--decrypt' in args:\n"
                    "    source = args[-1]\n"
                    "    sys.stdout.buffer.write(open(source, 'rb').read())\n"
                    "else:\n"
                    "    sys.stdout.buffer.write(sys.stdin.buffer.read())\n"
                    % sys.executable, encoding="ascii")
    stub.chmod(0o755)
    return str(stub)


def run_cli(module, argv):
    result = subprocess.run([sys.executable, str(module.__file__ or PROBE_PATH)] + argv,
                            capture_output=True, text=True, timeout=120)
    assert result.stderr == "", result.stderr
    return result.returncode, result.stdout


def ledger_cli(argv):
    return run_cli(ledger_tools, argv)


def probe_cli(argv):
    return run_cli(probe, argv)


# ---------------------------------------------------------------------------
# cutover_probe: token minting and credential handling
# ---------------------------------------------------------------------------

def test_mint_token_verifies_with_pyjwt_like_verifier():
    token = probe.mint_token(TEST_SECRET, subject="cutover-check", tenant="hermes",
                             project="ubuntu_hermes", ttl=600, now=1_700_000_000)
    assert token.isascii()
    header, payload, signature = token.split(".")
    pad = lambda data: data + b"=" * (-len(data) % 4)  # noqa: E731
    claims = json.loads(base64.urlsafe_b64decode(pad(payload.encode())))
    assert claims["sub"] == "cutover-check"
    assert claims["roles"] == ["user"]
    assert claims["tenant"] == "hermes"
    assert claims["project_id"] == "ubuntu_hermes"
    assert claims["exp"] - claims["iat"] == 600
    expected = hmac.new(TEST_SECRET.encode(), (header + "." + payload).encode(),
                        hashlib.sha256).digest()
    assert hmac.compare_digest(base64.urlsafe_b64decode(pad(signature.encode())), expected)


def test_mint_token_accepted_by_real_pyjwt_verifier():
    jwt = pytest.importorskip("jwt")
    token = probe.mint_token(TEST_SECRET, subject="s", tenant="t", project="p")
    claims = jwt.decode(token, TEST_SECRET, algorithms=["HS256"],
                        options={"verify_aud": False, "require": ["exp", "sub"]})
    assert claims["sub"] == "s" and claims["exp"] > claims["iat"]


def test_mint_token_rejects_empty_or_non_ascii_secret():
    with pytest.raises(ValueError):
        probe.mint_token("", subject="s", tenant="t", project="p")
    with pytest.raises(ValueError):
        probe.mint_token("non-ascii-\xe9", subject="s", tenant="t", project="p")


def test_load_signing_secret_reads_and_refuses_absence(tmp_path):
    path = tmp_path / "api.json"
    path.write_text(json.dumps({"ENHANCED_JWT_SECRET": "s3cret"}), encoding="ascii")
    assert probe.load_signing_secret(str(path)) == "s3cret"
    path.write_text(json.dumps({"ENHANCED_MEMORY_DATABASE_URL": "x"}), encoding="ascii")
    with pytest.raises(ValueError):
        probe.load_signing_secret(str(path))


# ---------------------------------------------------------------------------
# cutover_probe: verify and usage subcommands against the stub API
# ---------------------------------------------------------------------------

def test_verify_passes_against_stub_contract(stub_server, api_credential, capsys):
    code, out = probe_cli(["verify", "--api-credential", api_credential,
                           "--origin", stub_server, "--scope", "hermes/ubuntu_hermes"])
    report = json.loads(out)
    assert code == 0 and report["overall"] == "pass"
    assert [item["check"] for item in report["checks"]] == [
        "health_ready", "remember_roundtrip", "recall_roundtrip",
        "analysis_withheld_422", "analysis_status_configured_false"]
    assert all(item["ok"] for item in report["checks"])
    # The service really received a validly signed bearer token.
    assert StubAPI.seen_bearers and all(StubAPI.seen_bearers)
    # No secret or token material is printed.
    assert TEST_SECRET not in out and "Bearer " not in out


def test_verify_fails_when_health_not_ready(stub_server, api_credential):
    StubAPI.ready = False
    code, out = probe_cli(["verify", "--api-credential", api_credential,
                           "--origin", stub_server, "--scope", "hermes/p"])
    report = json.loads(out)
    assert code == 1 and report["overall"] == "fail"
    assert report["checks"][0]["check"] == "health_ready" and not report["checks"][0]["ok"]


def test_verify_fails_when_analysis_not_withheld(stub_server, api_credential):
    StubAPI.summarize_status = {"configured": True, "used_today": 5}
    code, out = probe_cli(["verify", "--api-credential", api_credential,
                           "--origin", stub_server, "--scope", "hermes/p"])
    assert code == 1


def test_verify_reports_configuration_error_without_secret(tmp_path):
    path = tmp_path / "api.json"
    path.write_text(json.dumps({"ENHANCED_MEMORY_DATABASE_URL": "x"}), encoding="ascii")
    code, out = probe_cli(["verify", "--api-credential", str(path),
                           "--origin", "http://127.0.0.1:1", "--scope", "t/p"])
    assert code == 2 and json.loads(out)["overall"] == "error"


def test_usage_flags_charged_and_unknown_scopes(stub_server, api_credential):
    StubAPI.summarize_status = {"configured": True, "used_today": 4321}
    code, out = probe_cli(["usage", "--api-credential", api_credential,
                           "--origin", stub_server, "--scope", "hermes/p1",
                           "--scope", "hermes/p2"])
    report = json.loads(out)
    assert code == 0
    assert report["any_charged_today"] is True
    assert all(item["charged_today"] for item in report["scopes"])
    assert TEST_SECRET not in out


def test_usage_clean_when_unconfigured(stub_server, api_credential):
    StubAPI.summarize_status = {"configured": False, "used_today": None}
    code, out = probe_cli(["usage", "--api-credential", api_credential,
                           "--origin", stub_server, "--scope", "hermes/p"])
    report = json.loads(out)
    assert code == 0 and report["any_charged_today"] is False


def test_usage_marks_unreachable_scope_unknown(api_credential):
    code, out = probe_cli(["usage", "--api-credential", api_credential,
                           "--origin", "http://127.0.0.1:1", "--scope", "hermes/p"])
    report = json.loads(out)
    assert code == 0 and report["any_unknown_scope"] is True
    assert report["scopes"][0]["error_kind"] in {"URLError", "OSError"}


def test_usage_rejects_malformed_scope(api_credential):
    code, out = probe_cli(["usage", "--api-credential", api_credential,
                           "--origin", "http://127.0.0.1:1", "--scope", "hermes-only"])
    assert code == 2 and json.loads(out)["overall"] == "error"


# ---------------------------------------------------------------------------
# ledger_tools: verify
# ---------------------------------------------------------------------------

def test_ledger_verify_passes_for_wellformed_ledger(ledger):
    code, out = ledger_cli(["verify", "--ledger", ledger,
                            "--expect-uid", str(os.getuid())])
    report = json.loads(out)
    assert code == 0 and report["overall"] == "pass"
    assert report["mode"] == "0600" and report["nlink"] == 1
    assert report["table"] == "reservations" and report["rows"] == 1


def test_ledger_verify_rejects_loose_mode(ledger):
    os.chmod(ledger, 0o644)
    code, out = ledger_cli(["verify", "--ledger", ledger,
                            "--expect-uid", str(os.getuid())])
    assert code == 1 and "0600" in json.loads(out)["reason"]


def test_ledger_verify_rejects_wrong_owner(ledger):
    code, out = ledger_cli(["verify", "--ledger", ledger, "--expect-uid", "4242"])
    assert code == 1


def test_ledger_verify_rejects_missing_schema(tmp_path):
    path = tmp_path / "tokens.sqlite3"
    sqlite3.connect(str(path)).close()
    os.chmod(path, 0o600)
    code, out = ledger_cli(["verify", "--ledger", str(path),
                            "--expect-uid", str(os.getuid())])
    assert code == 1 and "reservations" in json.loads(out)["reason"]


def test_ledger_verify_rejects_symlink(ledger):
    link = ledger + ".link"
    os.symlink(ledger, link)
    code, out = ledger_cli(["verify", "--ledger", link,
                            "--expect-uid", str(os.getuid())])
    assert code == 1


# ---------------------------------------------------------------------------
# ledger_tools: backup + verify-backup with the stub age command
# ---------------------------------------------------------------------------

def test_backup_creates_encrypted_artifact_and_signed_manifest(
        ledger, backup_credential, age_stub, tmp_path):
    out_dir = tmp_path / "backups"
    code, out = ledger_cli(["backup", "--ledger", ledger, "--output-dir", str(out_dir),
                            "--credential", backup_credential, "--age-command", age_stub,
                            "--expect-uid", str(os.getuid())])
    report = json.loads(out)
    assert code == 0 and report["overall"] == "pass" and report["rows"] == 1
    artifact = Path(report["path"])
    assert artifact.parent == out_dir and artifact.suffixes[-1] == ".age"
    manifest = json.loads(Path(report["manifest"]).read_text(encoding="ascii"))
    assert manifest["format"] == "sqlite-snapshot+age" and manifest["complete"] is True
    assert manifest["ciphertext_sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    # Signature validates with the same signing key.
    value = {k: v for k, v in manifest.items() if k != "signature"}
    expected = hmac.new(b"unit-test-signing-key-0123456789abcdef",
                        json.dumps(value, sort_keys=True,
                                   separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(manifest["signature"], expected)
    # No plaintext snapshot remains and no key material is printed.
    assert not list(out_dir.glob("ledger-snapshot-*"))
    assert "signing-key" not in out


def test_verify_backup_round_trips(ledger, backup_credential, age_stub, tmp_path):
    out_dir = tmp_path / "backups"
    code, out = ledger_cli(["backup", "--ledger", ledger, "--output-dir", str(out_dir),
                            "--credential", backup_credential, "--age-command", age_stub,
                            "--expect-uid", str(os.getuid())])
    artifact = json.loads(out)["path"]
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-STUB", encoding="ascii")
    code, out = ledger_cli(["verify-backup", "--backup", artifact,
                            "--identity", str(identity),
                            "--credential", backup_credential, "--age-command", age_stub])
    report = json.loads(out)
    assert code == 0 and report["overall"] == "pass"
    assert report["integrity"] == "ok" and report["rows"] == 1
    assert not list(out_dir.glob("*.verify-*"))


def test_verify_backup_detects_ciphertext_tampering(
        ledger, backup_credential, age_stub, tmp_path):
    out_dir = tmp_path / "backups"
    code, out = ledger_cli(["backup", "--ledger", ledger, "--output-dir", str(out_dir),
                            "--credential", backup_credential, "--age-command", age_stub,
                            "--expect-uid", str(os.getuid())])
    artifact = Path(json.loads(out)["path"])
    raw = bytearray(artifact.read_bytes())
    raw[-1] ^= 0xFF
    artifact.write_bytes(bytes(raw))
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-STUB", encoding="ascii")
    code, out = ledger_cli(["verify-backup", "--backup", str(artifact),
                            "--identity", str(identity),
                            "--credential", backup_credential, "--age-command", age_stub])
    assert code == 1 and "ciphertext" in json.loads(out)["reason"]


def test_verify_backup_rejects_wrong_signing_key(
        ledger, backup_credential, age_stub, tmp_path):
    out_dir = tmp_path / "backups"
    ledger_cli(["backup", "--ledger", ledger, "--output-dir", str(out_dir),
                "--credential", backup_credential, "--age-command", age_stub,
                "--expect-uid", str(os.getuid())])
    artifact = next(out_dir.glob("ledger-*.age"))
    other = tmp_path / "other.json"
    other.write_text(json.dumps({
        "ENHANCED_BACKUP_RECIPIENT": "age1unit-test-recipient-example-key",
        "ENHANCED_BACKUP_SIGNING_KEY":
            "another-unit-test-signing-key-abcdefghij",
        "ENHANCED_BACKUP_SIGNING_KEY_ID": "backup_v1"}), encoding="ascii")
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-STUB", encoding="ascii")
    code, out = ledger_cli(["verify-backup", "--backup", str(artifact),
                            "--identity", str(identity),
                            "--credential", str(other), "--age-command", age_stub])
    assert code == 1 and "signature" in json.loads(out)["reason"]


def test_backup_refuses_short_signing_key(ledger, tmp_path, age_stub):
    weak = tmp_path / "weak.json"
    weak.write_text(json.dumps({
        "ENHANCED_BACKUP_RECIPIENT": "age1example",
        "ENHANCED_BACKUP_SIGNING_KEY": "short"}), encoding="ascii")
    code, out = ledger_cli(["backup", "--ledger", ledger,
                            "--output-dir", str(tmp_path / "b"),
                            "--credential", str(weak), "--age-command", age_stub,
                            "--expect-uid", str(os.getuid())])
    assert code == 1


def test_backup_refuses_dangerous_recipient(ledger, tmp_path, age_stub):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "ENHANCED_BACKUP_RECIPIENT": "--write-out",
        "ENHANCED_BACKUP_SIGNING_KEY": "unit-test-signing-key-0123456789abcdef"}),
        encoding="ascii")
    code, out = ledger_cli(["backup", "--ledger", ledger,
                            "--output-dir", str(tmp_path / "b"),
                            "--credential", str(bad), "--age-command", age_stub,
                            "--expect-uid", str(os.getuid())])
    assert code == 1


def test_backup_requires_credential_source(ledger, tmp_path, age_stub, monkeypatch):
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    code, out = ledger_cli(["backup", "--ledger", ledger,
                            "--output-dir", str(tmp_path / "b"),
                            "--age-command", age_stub,
                            "--expect-uid", str(os.getuid())])
    assert code == 1 and "credential" in json.loads(out)["reason"].lower()


# ---------------------------------------------------------------------------
# Shipped unit-file bytes
# ---------------------------------------------------------------------------

def read_unit(name):
    data = (UNITS_DIR / name).read_bytes()
    text = data.decode("ascii")
    assert text.endswith("\n") and "\r" not in text
    return data, text


def test_cutover_dropin_exact_bytes():
    data, _ = read_unit("40-cutover-candidate.conf")
    assert hashlib.sha256(data).hexdigest() == CUTOVER_DROPIN_SHA256


def test_cutover_dropin_is_reviewed_v3_plus_state_directory_only():
    _, text = read_unit("40-cutover-candidate.conf")
    reduced = "".join(line + "\n" for line in text.splitlines()
                      if not line.startswith(("StateDirectory=", "StateDirectoryMode=")))
    assert hashlib.sha256(reduced.encode("ascii")).hexdigest() == REVIEWED_V3_DROPIN_SHA256


def test_cutover_dropin_neutralises_llm_credential():
    _, text = read_unit("40-cutover-candidate.conf")
    lines = text.splitlines()
    assert lines[0] == "[Service]"
    reset = lines.index("LoadCredential=")
    added = [line for line in lines if line.startswith("LoadCredential=")]
    assert added[1:] == ["LoadCredential=api.json:/etc/enhanced-cognee/api.json",
                         "LoadCredential=index.json:/etc/enhanced-cognee/index.json"]
    assert reset < lines.index(added[1])
    assert not any("llm.json" in line for line in lines)
    assert ("ExecStart=/opt/enhanced-cognee-memory/candidates/"
            "audit-c14f595c-20261101/runtime/bin/python -I -B -m src.memory_daemon api") in lines
    assert "WorkingDirectory=/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101" in lines
    assert "StateDirectory=enhanced-cognee-api" in lines
    assert "StateDirectory=enhanced-cognee-llm-budget" in lines
    assert "StateDirectoryMode=0700" in lines


def test_rollback_withhold_dropin_keeps_old_runtime_and_withholds_llm():
    data, text = read_unit("40-llm-withhold.conf")
    lines = text.splitlines()
    assert lines[0] == "[Service]"
    assert not any(line.startswith(("ExecStart", "WorkingDirectory")) for line in lines)
    assert not any("llm.json" in line for line in lines)
    assert "LoadCredential=" in lines
    assert lines.count("LoadCredential=") == 1


def test_llm_enable_dropin_is_minimal_and_lexically_later():
    _, text = read_unit("50-llm-enable.conf")
    assert text.splitlines() == [
        "[Service]",
        "LoadCredential=llm.json:/etc/enhanced-cognee/llm.json"]
    # The enable drop-in must sort after the cutover drop-in so its
    # LoadCredential appends after the reset.
    assert "40-cutover-candidate.conf" < "50-llm-enable.conf"


def test_backup_dropin_preserves_original_and_adds_ledger_step():
    _, text = read_unit("enhanced-cognee-backup-40-ledger.conf")
    lines = text.splitlines()
    assert lines[0] == "[Service]"
    assert lines[1] == "ExecStart="
    assert lines[2] == ("ExecStart=/opt/enhanced-cognee-memory/runtime/bin/python "
                        "-m src.memory_daemon backup")
    assert len(lines) == 4 and lines[3].startswith(
        "ExecStart=/usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/"
        "ledger_tools_20261105.py backup --ledger /var/lib/enhanced-cognee-llm-budget/"
        "tokens.sqlite3 --output-dir /var/backups/enhanced-cognee")


# ---------------------------------------------------------------------------
# Cutover document consistency (guards the 2026-11-05 review repairs)
# ---------------------------------------------------------------------------

CUTOVER_DOC = ROOT / "docs/reports/audits/2026-11-05-cutover-package/CUTOVER-COMMANDS.md"

# Re-derived from the live staged candidate bytes on 2026-11-05 (review
# defect 1: the 2026-11-03 owner step-2 receipt contained a one-character
# transcription error at hex position 21 that the package had propagated).
ENTERPRISE_AUTH_PIN = "78cf82b8d052c74438dc85b9b24393128e837dbb8bfee78eda8146dbef66ae1e"
STEP2_RECEIPT_TYPO_PIN = "78cf82b8d052c74438dc85e9b24393128e837dbb8bfee78eda8146dbef66ae1e"

# The merged LoadCredential readback verified working during independent
# review (systemd 255 systemctl show prints "[unprintable]" for it).
BUSCTL_READBACK = ("sudo busctl introspect org.freedesktop.systemd1 "
                   "/org/freedesktop/systemd1/unit/enhanced_2dcognee_2dapi_2eservice"
                   " | grep .LoadCredential")


def read_cutover_doc():
    return CUTOVER_DOC.read_text(encoding="ascii")


def test_doc_pins_live_candidate_enterprise_auth_hash():
    text = read_cutover_doc()
    assert ENTERPRISE_AUTH_PIN in text
    assert STEP2_RECEIPT_TYPO_PIN not in text


def test_doc_loadcredential_readbacks_use_busctl_only():
    text = read_cutover_doc()
    # systemctl show -p LoadCredential is unusable on this host (systemd 255
    # prints [unprintable]); every readback must use the busctl form instead,
    # in Blocks A, C, D1, F1, F2 and G.
    assert "-p LoadCredential" not in text.replace(
        'systemctl show -p LoadCredential prints "[unprintable]"', "")
    assert text.count(BUSCTL_READBACK) == 6
    assert "[unprintable]" in text


def test_doc_defers_ledger_init_into_service_namespace():
    text = read_cutover_doc()
    # The out-of-namespace one-shot init (old Block E1) must be gone...
    assert "LEDGER_INIT_OK" not in text
    assert "TokenBudget()" not in text
    # ...replaced by daemon-side initialization at Block G enablement, with
    # the honest statement that the empty private directory proves nothing.
    assert "INSIDE the service mount namespace" in text
    assert "NOT ledger proof" in text


def test_doc_captures_every_enhanced_cognee_timer_before_and_after():
    text = read_cutover_doc()
    for timer in ("enhanced-cognee-backup.timer",
                  "enhanced-cognee-profile-backup.timer",
                  "enhanced-cognee-qualified-fleet-backup-v2.timer"):
        # Once in the Block A before-capture, once in the Block D5 comparison.
        assert text.count(timer) == 2
