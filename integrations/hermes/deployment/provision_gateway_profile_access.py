#!/usr/bin/env python3
"""Issue a scoped Enhanced Cognee token for a fleet-gateway profile.

Human-operated, root-only, one profile per run, modeled on the retained
pilot provisioner's audited flow: issuer-signed expiring HS256 tokens,
unauthenticated/expired/altered denial checks, authenticated readiness and
scope checks, atomic environment publication with a retained backup and
readback. Unlike the pilot, an existing token line is replaced in place
(not refused), the TTL is selectable, and the fresh-namespace assertion is
opt-in for first issuance. Never prints the token; only the operator runs
it; no fleet-admission machinery is enabled.
"""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import time
import uuid

HOME = Path("/home/vincentspereira/.hermes")
API_HOST, API_PORT = "127.0.0.1", 28080
TOKEN_NAME = "ENHANCED_COGNEE_ACCESS_TOKEN"
ALLOWED_UID = 1000
COMMENT = "# Scoped Enhanced Cognee gateway credential"
MAX_ENV = 65536


def require(value, category="gateway_provision_refused"):
    if not value:
        raise ValueError(category)


def load_signer():
    """Reuse the retained pilot provisioner's audited key loading and signing."""
    candidate = Path("/opt/enhanced-cognee-memory/candidates/"
                     "21abf4857ca8dce8e0a3aafc725266c8d3754529/"
                     "operator-issuer-candidate/provision_pilot_access.py")
    raw = candidate.read_bytes()
    require(0 < len(raw) <= 65536)
    scope = {"__name__": "verified_pilot_issuer_core", "__file__": str(candidate)}
    exec(compile(raw, "<verified-pilot-issuer-core>", "exec"), scope)
    return scope


def identity_for(profile):
    marker = "default" if profile == "default" else profile
    return {"sub": "hermes_gateway_" + marker, "agent_id": "hermes_gateway_" + marker,
            "tenant": "hermes_gateway", "project_id": marker,
            "roles": ["api_client"], "capture_policy": "selected"}


def prepare_environment(original: bytes, token: str) -> bytes:
    """Append or replace the token line; every other binding is preserved."""
    import io
    from dotenv.parser import parse_stream
    require(isinstance(original, bytes) and 0 < len(original) <= MAX_ENV
            and b"\x00" not in original, "gateway_env_size_or_nul")
    require(isinstance(token, str) and 0 < len(token) < 4096
            and all(c.isalnum() or c in "-_." for c in token), "gateway_token_malformed")
    bindings = list(parse_stream(io.StringIO(original.decode("utf-8"))))
    require(not any(binding.error for binding in bindings), "gateway_env_syntax")
    marker = COMMENT.encode() + b"\n" + TOKEN_NAME.encode() + b"=" + token.encode() + b"\n"
    output = bytearray()
    replaced = False
    for line in original.splitlines(keepends=True):
        stripped = line.lstrip()
        if not stripped.startswith(b"#") and TOKEN_NAME.encode() + b"=" in line:
            if not replaced:
                output.extend(marker)
                replaced = True
            continue
        output.extend(line)
    if not replaced:
        output.extend(marker)
    updated = bytes(output)
    after = list(parse_stream(io.StringIO(updated.decode("utf-8"))))
    require(not any(binding.error for binding in after), "gateway_env_result_syntax")
    require(sum(1 for binding in after if binding.key == TOKEN_NAME) == 1,
            "gateway_env_token_not_single")
    before_pairs = [(b.key, b.value) for b in bindings if b.key not in (None, TOKEN_NAME)]
    after_pairs = [(b.key, b.value) for b in after if b.key not in (None, TOKEN_NAME)]
    require(before_pairs == after_pairs, "gateway_env_other_bindings_changed")
    require(len(updated) <= MAX_ENV, "gateway_env_grew_over_budget")
    return updated


def api_status(token=None):
    from http.client import HTTPConnection
    connection = HTTPConnection(API_HOST, API_PORT, timeout=5)
    try:
        headers = {"Authorization": "Bearer " + token} if token else {}
        connection.request("GET", "/v1/memories/status", headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            return response.status, {}
        raw = response.read(131073)
        require(len(raw) <= 131072, "gateway_api_status_oversized")
        return response.status, json.loads(raw)
    finally:
        connection.close()


def deny_checks(key, identity, now):
    """Unauthenticated, expired and altered credentials must all be denied."""
    def sign(claims):
        message = (json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":"))
                   .encode())
        import base64
        head = base64.urlsafe_b64encode(message).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":"),
                                                      ensure_ascii=True).encode()).rstrip(b"=")
        signature = base64.urlsafe_b64encode(hmac.new(
            key, head + b"." + payload, hashlib.sha256).digest()).rstrip(b"=")
        return (head + b"." + payload + b"." + signature).decode("ascii")
    expired = sign(dict(identity, iat=now - 7200, exp=now - 3600))
    altered_payload = dict(identity, project_id="hermes_gateway_other")
    head = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    import base64
    payload = base64.urlsafe_b64encode(json.dumps(
        altered_payload, separators=(",", ":"), ensure_ascii=True).encode()).rstrip(b"=")
    good = sign(dict(identity, iat=now, exp=now + 3600)).split(".")
    altered = head + "." + payload.decode("ascii") + "." + good[2]
    for denied in (None, expired, altered):
        code, _ = api_status(denied)
        require(code == 401, "gateway_api_denial_check_failed:" +
                ("unauthenticated" if denied is None else
                 "expired" if denied is expired else "altered"))


def qualify_access(token, identity, expect_fresh):
    code, data = api_status(token)
    require(code == 200 and isinstance(data, dict) and data.get("ready") is True,
            "gateway_api_authenticated_refused")
    require(all(data.get(field) == identity[claim] for field, claim in (
        ("tenant_id", "tenant"), ("project_id", "project_id"), ("subject", "sub"))),
        "gateway_api_scope_mismatch")
    require(data.get("schema_version") == 3 and data.get("encryption") == "AES-256-GCM",
            "gateway_api_schema_or_cipher_changed")
    if expect_fresh:
        require(data.get("active_records") == 0 and data.get("pending_change_events") == 0,
                "gateway_namespace_not_fresh")
    return {"ready": True, "active_records": data.get("active_records"),
            "pending_change_events": data.get("pending_change_events")}


def publish(env_path: Path, original: bytes, updated: bytes, uid: int):
    """Backup, atomic replace, readback. Refuses if the file changed meanwhile."""
    import stat as stat_module
    info = env_path.lstat()
    require(stat_module.S_ISREG(info.st_mode) and info.st_uid == uid
            and info.st_nlink == 1 and not info.st_mode & 0o022,
            "gateway_env_protection_review")
    directory_fd = os.open(env_path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        backup = ".env-before-gateway-" + uuid.uuid4().hex
        backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=directory_fd)
        with os.fdopen(backup_fd, "wb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        stage = ".env-gateway-" + uuid.uuid4().hex
        stage_fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           0o600, dir_fd=directory_fd)
        with os.fdopen(stage_fd, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        original_fd = os.open(env_path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            current = os.read(original_fd, MAX_ENV + 1)
            require(len(current) <= MAX_ENV and current == original,
                    "gateway_env_changed_during_preparation")
        finally:
            os.close(original_fd)
        os.replace(stage, env_path.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
        readback_fd = os.open(env_path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            require(os.read(readback_fd, MAX_ENV + 1) == updated, "gateway_env_readback_failed")
        finally:
            os.close(readback_fd)
        return backup
    finally:
        os.close(directory_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--ttl-hours", type=int, default=168)
    parser.add_argument("--fresh-namespace", action="store_true")
    args = parser.parse_args()
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes",
            "run_as_owner_sudo_on_gateway_host")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.profile) is not None
            and 1 <= args.ttl_hours <= 8760, "gateway_profile_or_ttl_invalid")
    if args.profile != "default":
        require((HOME / "profiles" / args.profile).is_dir(), "gateway_profile_dir_missing")
    env_path = HOME / ".env" if args.profile == "default" else \
        HOME / "profiles" / args.profile / ".env"
    require(env_path.is_file(), "gateway_env_file_missing")
    require(env_path.stat().st_uid == ALLOWED_UID, "gateway_env_owner_invalid")
    original = env_path.read_bytes()
    identity = identity_for(args.profile)
    signer = load_signer()
    key = signer["load_signing_key"]()
    now = int(time.time())
    token = signer["sign_claims"](dict(identity, iat=now, exp=now + args.ttl_hours * 3600), key)
    deny_checks(key, identity, now)
    checks = qualify_access(token, identity, args.fresh_namespace)
    updated = prepare_environment(original, token)
    backup = publish(env_path, original, updated, ALLOWED_UID)
    receipt = {"complete": True, "profile": args.profile, "env_path": str(env_path),
               "env_backup": backup, "ttl_hours": args.ttl_hours,
               "expires_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + args.ttl_hours * 3600)),
               "identity": identity, "api_checks": checks,
               "token_value_emitted": False, "fleet_admission_enabled": False,
               "fresh_namespace_asserted": bool(args.fresh_namespace)}
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        detail = str(exc)[:160] if isinstance(exc, ValueError) else ""
        print(json.dumps({"complete": False, "category": "gateway_provision_refused",
                          "error_kind": type(exc).__name__, "detail": detail}), flush=True)
        raise SystemExit(1)
