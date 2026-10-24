"""One-shot invented-data pilot access; stdlib operator, restricted profile writes.

Run only as the hash-verified published blob. No application imports as root;
only ordinary expiring tokens cross the pipe to the restricted child. This is
initial provisioning, not automatic renewal or provider/model activation.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import time
import uuid


HOME = Path("/var/lib/hermes-runtime")
PROFILE = HOME / ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
TOKEN_NAME = "ENHANCED_COGNEE_ACCESS_TOKEN"
IDENTITY = {"sub": "hermes_pilot_runtime", "agent_id": "hermes_pilot",
            "tenant": "qualification", "project_id": "hermes_pilot",
            "roles": ["api_client"], "capture_policy": "selected"}
LIMIT = 65536
PHASES = {"identity", "profile_preflight", "environment_preflight", "api_checks",
          "environment_backup", "environment_publication", "environment_readback"}


class ProvisionError(RuntimeError):
    """Fixed public errors only; never interpolate credentials or private input."""


def open_directory(path, allowed_owners):
    """Refuse redirected or writable ancestors, retaining directory descriptors."""
    if not path.is_absolute():
        raise ProvisionError("Use the fixed absolute directory.")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in (None, *path.parts[1:]):
            if name is not None:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            if info.st_uid not in allowed_owners or info.st_mode & 0o022:
                raise ProvisionError("A selected directory needs protection review.")
        return fd
    except BaseException:
        os.close(fd)
        raise


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_private_fd(fd, uid):
    before = os.fstat(fd)
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
            or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
            or before.st_size > LIMIT):
        raise ProvisionError("A selected private file needs protection review.")
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, LIMIT + 1)
    if len(raw) != before.st_size or fingerprint(before) != fingerprint(os.fstat(fd)):
        raise ProvisionError("A selected private file changed during inspection.")
    return raw, before


def read_private_at(directory, name, uid):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        return read_private_fd(fd, uid)
    finally:
        os.close(fd)


def load_signing_key():
    directory = open_directory(Path("/etc/enhanced-cognee"), {0})
    try:
        values = []
        for name in ("operator.json", "api.json"):
            raw, _ = read_private_at(directory, name, 0)
            key = json.loads(raw)["ENHANCED_JWT_SECRET"]
            if not isinstance(key, str) or len(key.encode()) < 32:
                raise ProvisionError("The protected signing configuration needs review.")
            values.append(key.encode())
        if not hmac.compare_digest(*values):
            raise ProvisionError("The protected operator/API signing keys differ.")
        return values[0]
    finally:
        os.close(directory)


def encode_segment(value):
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":"),
                                            ensure_ascii=True).encode()).rstrip(b"=")


def sign_claims(claims, key):
    """HS256 wire format matching memory_admin.issue_token; no extra authority."""
    message = encode_segment({"alg": "HS256", "typ": "JWT"}) + b"." + encode_segment(claims)
    signature = base64.urlsafe_b64encode(hmac.new(key, message, hashlib.sha256).digest()).rstrip(b"=")
    return (message + b"." + signature).decode("ascii")


def make_bundle(key, now):
    claims = dict(IDENTITY, iat=now, exp=now + 86400)
    token = sign_claims(claims, key)
    expired = sign_claims(dict(IDENTITY, iat=now - 7200, exp=now - 3600), key)
    parts = token.split(".")
    altered = encode_segment(dict(claims, project_id="hermes_pilot_other")).decode("ascii")
    return {"token": token, "expired": expired,
            "altered": parts[0] + "." + altered + "." + parts[2], "claims": claims}


def prepare_environment(raw, token):
    # This third-party parser runs only in the restricted child (or test runtime).
    # It parses values without loading them into the process environment.
    from dotenv.parser import parse_stream
    if not isinstance(raw, bytes) or len(raw) > LIMIT or b"\x00" in raw:
        raise ProvisionError("The existing environment file needs review.")
    if not isinstance(token, str) or not 0 < len(token) < 4096 or any(
            c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_." for c in token):
        raise ProvisionError("The ordinary pilot credential is malformed.")
    bindings = list(parse_stream(io.StringIO(raw.decode("utf-8"))))
    if any(binding.error or binding.key == TOKEN_NAME for binding in bindings):
        raise ProvisionError("An existing credential or environment syntax needs review; file preserved.")
    updated = raw + b"\n# Scoped Enhanced Cognee pilot credential\n" + TOKEN_NAME.encode() + b"=" + token.encode() + b"\n"
    after = list(parse_stream(io.StringIO(updated.decode("utf-8"))))
    before_pairs = [(row.key, row.value) for row in bindings if row.key is not None]
    after_pairs = [(row.key, row.value) for row in after if row.key not in (None, TOKEN_NAME)]
    if (len(updated) > LIMIT or any(row.error for row in after) or before_pairs != after_pairs
            or [row.value for row in after if row.key == TOKEN_NAME] != [token]):
        raise ProvisionError("The proposed environment did not preserve existing settings.")
    return updated


def api_status(token=None):
    # Fixed loopback destination, no proxy discovery, redirects or token in URL.
    from http.client import HTTPConnection
    connection = HTTPConnection("127.0.0.1", 28080, timeout=5)
    try:
        headers = {"Authorization": "Bearer " + token} if token else {}
        connection.request("GET", "/v1/memories/status", headers=headers)
        reply = connection.getresponse()
        if reply.status != 200:
            return reply.status, {}
        raw = reply.read(131073)
        if len(raw) > 131072:
            raise ProvisionError("The local API status response exceeded its limit.")
        return reply.status, json.loads(raw)
    finally:
        connection.close()


def qualify_access(bundle, request=api_status):
    for token in (None, bundle["expired"], bundle["altered"]):
        if request(token)[0] != 401:
            raise ProvisionError("The API did not reject an unauthenticated, expired or altered credential.")
    code, data = request(bundle["token"])
    if (code != 200 or not isinstance(data, dict) or data.get("ready") is not True
            or any(data.get(field) != IDENTITY[claim] for field, claim in (
                ("tenant_id", "tenant"), ("project_id", "project_id"), ("subject", "sub")))
            or data.get("schema_version") != 3 or data.get("encryption") != "AES-256-GCM"
            or type(data.get("active_records")) is not int or data["active_records"] != 0
            or type(data.get("pending_change_events")) is not int or data["pending_change_events"] != 0):
        raise ProvisionError("The authenticated API scope/readiness or fresh pilot namespace differs.")


def create_private_at(directory, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    with os.fdopen(fd, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def install_environment(directory, original_fd, original, token, uid, phase):
    updated = prepare_environment(original, token)
    phase("environment_backup")
    backup = ".env-before-cognee-pilot-" + uuid.uuid4().hex
    create_private_at(directory, backup, original)
    if read_private_at(directory, backup, uid)[0] != original:
        raise ProvisionError("The preserved environment copy did not verify.")
    stage = ".env-cognee-pilot-" + uuid.uuid4().hex
    create_private_at(directory, stage, updated)
    os.fsync(directory)
    phase("environment_publication")
    current, opened_info = read_private_fd(original_fd, uid)
    named_info = os.stat(".env", dir_fd=directory, follow_symlinks=False)
    if current != original or fingerprint(opened_info) != fingerprint(named_info):
        raise ProvisionError("The existing environment changed; prepared copies retained.")
    os.replace(stage, ".env", src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
    phase("environment_readback")
    if read_private_at(directory, ".env", uid)[0] != updated:
        raise ProvisionError("Pilot environment readback needs review; preserved copies retained.")
    return backup


def child_main(bundle):
    phase = "identity"
    def select_phase(value):
        nonlocal phase
        phase = value
    try:
        account = pwd.getpwuid(os.geteuid())
        fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
        if (account.pw_name != "hermes-runtime" or account.pw_uid == 0
                or Path(account.pw_dir) != HOME or Path.cwd() != HOME
                or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
                or fields.get("NoNewPrivs", "").strip() != "1"
                or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))):
            raise ProvisionError("The child identity needs review.")
        now = int(time.time())
        claims = bundle["claims"]
        if (set(bundle) != {"token", "expired", "altered", "claims"}
                or set(claims) != set(IDENTITY) | {"iat", "exp"}
                or any(claims.get(key) != value for key, value in IDENTITY.items())
                or type(claims["iat"]) is not int or type(claims["exp"]) is not int
                or claims["exp"] - claims["iat"] != 86400 or not 0 <= now - claims["iat"] <= 120):
            raise ProvisionError("The ordinary credential scope/lifetime needs review.")
        phase = "profile_preflight"
        directory = open_directory(PROFILE, {0, account.pw_uid})
        try:
            info = os.fstat(directory)
            if info.st_uid != account.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
                raise ProvisionError("The pilot directory needs review.")
            for name in ("config.yaml", "enhanced_cognee.json"):
                try:
                    os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise ProvisionError("The pilot already has configuration; preserved.")
            phase = "environment_preflight"
            env_fd = os.open(".env", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                fcntl.flock(env_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                original, _ = read_private_fd(env_fd, account.pw_uid)
                prepare_environment(original, bundle["token"])
                phase = "api_checks"
                qualify_access(bundle)
                backup = install_environment(directory, env_fd, original, bundle["token"],
                                             account.pw_uid, select_phase)
            finally:
                os.close(env_fd)
        finally:
            os.close(directory)
        print(json.dumps({"complete": True, "effective_user": account.pw_name,
                          "credential_installed": True, "environment_backup": backup,
                          "tenant": IDENTITY["tenant"], "project": IDENTITY["project_id"],
                          "subject": IDENTITY["sub"], "role": "api_client",
                          "capture_policy": "selected",
                          "expires_utc": datetime.fromtimestamp(claims["exp"], timezone.utc).isoformat(),
                          "authenticated_api_status_passed": True,
                          "unauthenticated_expired_altered_denied": True,
                          "provider_selected": False, "model_called": False,
                          "memory_records_written": False, "runtime_qualified": False}))
    except Exception:
        print(json.dumps({"complete": False, "failure_stage": phase}))
        raise SystemExit(1) from None


def run_child(account, source, bundle):
    code = ("import json,sys\nnamespace={'__name__':'reviewed_pilot_access'}\n"
            "exec(compile(" + repr(source) + ",'reviewed-pilot-access','exec'),namespace)\n"
            "namespace['child_main'](json.load(sys.stdin))\n")
    result = subprocess.run(
        ["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env", "-i",
         "HOME=" + str(HOME), "USER=hermes-runtime", "LOGNAME=hermes-runtime",
         "PATH=/usr/bin:/bin", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1",
         str(RELEASE / "venv/bin/python"), "-I", "-B", "-c", code],
        input=json.dumps(bundle).encode(), user=account.pw_uid, group=account.pw_gid,
        extra_groups=(), cwd=HOME, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    if len(result.stdout) > LIMIT:
        raise ProvisionError("The restricted child returned an unexpected receipt.")
    report = json.loads(result.stdout)
    if result.returncode:
        phase = report.get("failure_stage") if isinstance(report, dict) else None
        if isinstance(phase, str) and phase in PHASES:
            raise ProvisionError("Pilot provisioning failed at " + phase + "; existing and prepared files retained.")
        raise ProvisionError("The restricted child did not complete; prepared files retained.")
    expected = {"complete": True, "effective_user": "hermes-runtime", "credential_installed": True,
                "tenant": IDENTITY["tenant"], "project": IDENTITY["project_id"], "subject": IDENTITY["sub"],
                "role": "api_client", "capture_policy": "selected",
                "expires_utc": datetime.fromtimestamp(bundle["claims"]["exp"], timezone.utc).isoformat(),
                "authenticated_api_status_passed": True, "unauthenticated_expired_altered_denied": True,
                "provider_selected": False, "model_called": False,
                "memory_records_written": False, "runtime_qualified": False}
    backup = report.get("environment_backup", "") if isinstance(report, dict) else ""
    if (not isinstance(report, dict) or set(report) != set(expected) | {"environment_backup"}
            or any(type(report.get(key)) is not type(value) or report.get(key) != value for key, value in expected.items())
            or not isinstance(backup, str) or not backup.startswith(".env-before-cognee-pilot-")
            or len(backup.removeprefix(".env-before-cognee-pilot-")) != 32
            or any(c not in "0123456789abcdef" for c in backup.removeprefix(".env-before-cognee-pilot-"))):
        raise ProvisionError("The restricted child returned an unexpected receipt.")
    return report


def main(source):
    try:
        if (os.geteuid() != 0 or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes"
                or os.environ.get("SUDO_USER") != "vincentspereira"):
            raise ProvisionError("Use the approved human Ubuntu-Hermes operator through sudo.")
        if not isinstance(source, bytes) or len(source) > LIMIT:
            raise ProvisionError("Use the exact verified helper source.")
        account = pwd.getpwnam("hermes-runtime")
        if (account.pw_uid == 0 or Path(account.pw_dir) != HOME
                or set(os.getgrouplist(account.pw_name, account.pw_gid)) != {account.pw_gid}):
            raise ProvisionError("The restricted account needs review.")
        for path in (Path("/usr/bin/setpriv"), RELEASE / "venv/bin/python"):
            resolved = path.resolve(strict=True)
            info = resolved.stat()
            if (info.st_uid != 0 or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o6022
                    or (path != Path("/usr/bin/setpriv") and not resolved.is_relative_to(RELEASE))):
                raise ProvisionError("The protected child executables need review.")
        key = load_signing_key()
        bundle = make_bundle(key, int(time.time()))
        del key
        report = run_child(account, source, bundle)
    except ProvisionError as error:
        raise SystemExit("STOP: " + str(error)) from None
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, SyntaxError,
            subprocess.SubprocessError):
        raise SystemExit("STOP: Pilot access provisioning incomplete; no private details printed. Prepared files retained.") from None
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified operator command.")
