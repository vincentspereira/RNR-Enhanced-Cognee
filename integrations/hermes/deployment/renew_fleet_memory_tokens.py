#!/usr/bin/env python3
"""Timer job: renew fleet memory tokens inside their final 7 days.

Runs as root from /opt/enhanced-cognee-memory/fleet-renewal beside the
installed provisioner. Reads each profile's current token expiry from its
own .env (unverified claim decode, the retained pilot-renewal pattern),
renews only profiles within the window by invoking the provisioner, and
records a sanitized state file. A failure for one profile never blocks the
others; prior tokens simply keep their old expiry. Never prints token
values.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HOME = Path("/home/vincentspereira/.hermes")
RENEWAL_ROOT = Path("/opt/enhanced-cognee-memory/fleet-renewal")
PROVISIONER = RENEWAL_ROOT / "provision_gateway_profile_access.py"
STATE = RENEWAL_ROOT / "state.json"
RECEIPTS = HOME / "fleet-token-receipts.json"  # historical only; never trusted for inventory
INVENTORY = RENEWAL_ROOT / "roles.json"
PROVISIONER_PYTHON = Path("/opt/enhanced-cognee-memory/candidates/"
    "21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime/bin/python")
TOKEN_NAME = "ENHANCED_COGNEE_ACCESS_TOKEN"
WINDOW_SECONDS = 7 * 86400
TTL_HOURS = 720
CANARIES = {"enhanced-cognee-test", "enhanced-cognee-test-two"}


def require(value, category="fleet_token_renewal_refused"):
    if not value:
        raise ValueError(category)


def decode_exp(token: str) -> int:
    """Unverified expiry decode with strict shape restriction."""
    require(isinstance(token, str) and 32 <= len(token) < 4096
            and re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token)
            is not None, "token_shape")
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    require(isinstance(claims, dict) and type(claims.get("exp")) is int
            and claims["exp"] > 0, "claims_shape")
    # Keep the existing positive-expiry policy and a four-digit UTC year.
    require(claims["exp"] <= 253402300799, "claims_expiry")
    try:
        require(1 <= time.gmtime(claims["exp"]).tm_year <= 9999, "claims_expiry")
    except (ValueError, OverflowError, OSError):
        raise ValueError("claims_expiry") from None
    return claims["exp"]


def load_profile_token(env_path: Path) -> str | None:
    try:
        raw = env_path.read_text()
    except OSError:
        return None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(TOKEN_NAME + "=") and not stripped.startswith("#"):
            return stripped.split("=", 1)[1].strip()
    return None


def needs_renewal(exp: int, now: int, window: int = WINDOW_SECONDS) -> bool:
    return exp - now <= window


def trusted_path(path: Path, *, uid=0, trust_root=Path("/")) -> None:
    """Reject replaceable files/ancestors and symlinks; test root is explicit."""
    import stat
    path, trust_root = Path(path).absolute(), Path(trust_root).absolute()
    require(path == trust_root or trust_root in path.parents, "outside_trust_root")
    current = path
    while True:
        info = current.lstat()
        require(not stat.S_ISLNK(info.st_mode) and info.st_uid == uid
                and not info.st_mode & 0o022, "untrusted_runtime_path")
        if current == trust_root:
            break
        current = current.parent


def validate_runtime() -> None:
    # Trust both the alias directory actually used by exec and its real target.
    trusted_path(Path("/usr/bin/python3").parent)
    trusted_path(Path("/usr/bin/python3").resolve())
    trusted_path(PROVISIONER_PYTHON.parent)
    trusted_path(PROVISIONER_PYTHON.resolve())
    trusted_path(PROVISIONER_PYTHON.parent.parent / "pyvenv.cfg")
    trusted_path(Path(__file__))
    trusted_path(PROVISIONER)
    trusted_path(INVENTORY)


def profiles() -> list[str]:
    """A root-owned data inventory, never executable code from a checkout."""
    trusted_path(INVENTORY)
    raw = INVENTORY.read_bytes()
    require(0 < len(raw) <= 16384, "inventory_size")
    data = json.loads(raw)
    require(isinstance(data, dict) and set(data) == {"schema", "profiles"}
            and type(data["schema"]) is int and data["schema"] == 1,
            "inventory_shape")
    roles = data["profiles"]
    require(isinstance(roles, list) and len(roles) == 45
            and all(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name)
                    and name not in CANARIES for name in roles)
            and len(set(roles)) == len(roles) and roles == sorted(roles)
            and "default" in roles, "inventory_membership")
    return roles

def env_path(profile: str) -> Path:
    return HOME / ".env" if profile == "default" else HOME / "profiles" / profile / ".env"


def renew(profile: str) -> dict:
    # Only fixed categories leave this boundary: subprocess output may be secret.
    failure = {"profile": profile, "complete": False, "expires_utc": None,
               "error": "invalid_receipt"}
    try:
        started = int(time.time())
        process = subprocess.run(
            [str(PROVISIONER_PYTHON), "-I", "-B", str(PROVISIONER), "--profile", profile,
             "--ttl-hours", str(TTL_HOURS)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=180)
        require(process.returncode == 0, "process_failed")
        require(len(process.stdout) <= 16384, "receipt_size")
        receipt = json.loads(process.stdout)
        require(isinstance(receipt, dict) and receipt.get("complete") is True
                and receipt.get("profile") == profile, "receipt_shape")
        expiry = receipt.get("expires_utc")
        require(isinstance(expiry, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", expiry)
                is not None, "receipt_expiry")
        import calendar
        expires = calendar.timegm(time.strptime(expiry, "%Y-%m-%dT%H:%M:%SZ"))
        require(started + TTL_HOURS * 3600 - 300 <= expires
                <= int(time.time()) + TTL_HOURS * 3600 + 300, "receipt_expiry")
        return {"profile": profile, "complete": True, "expires_utc": expiry,
                "error": None}
    except subprocess.TimeoutExpired:
        return dict(failure, error="timeout")
    except OSError:
        return dict(failure, error="process_unavailable")
    except (ValueError, TypeError, OverflowError):
        return failure


def atomic_write(path: Path, raw: bytes, mode=0o600):
    """Publish within a trusted directory; readers see old or complete new bytes."""
    import uuid
    stage = path.with_name("." + path.name + "-stage-" + uuid.uuid4().hex)
    fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(stage, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if stage.exists():
            stage.unlink()


def main():
    require(os.geteuid() == 0 and os.uname().nodename == "Ubuntu-Hermes",
            "run_on_gateway_host_as_root")
    validate_runtime()
    require(PROVISIONER.is_file(), "provisioner_missing")
    now = int(time.time())
    renewed, skipped, failed, expiries = [], [], [], {}
    for profile in profiles():
        try:
            path = env_path(profile)
            token = load_profile_token(path)
            current_exp = decode_exp(token) if token else None
            if current_exp is not None and not needs_renewal(current_exp, now):
                expiry = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(current_exp))
                skipped.append(profile)
                expiries[profile] = expiry
                continue
        except (ValueError, TypeError, OverflowError, OSError):
            # Invalid/unreadable expiry follows the existing renewal policy,
            # only after the protected runtime and inventory passed preflight.
            pass
        result = renew(profile)
        if result["complete"]:
            renewed.append(profile)
            expiries[profile] = result["expires_utc"]
        else:
            failed.append(result)
    state = {"last_run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
             "renewed": renewed, "skipped": skipped, "failed": failed,
             "expires_utc": expiries, "ttl_hours": TTL_HOURS,
             "window_days": WINDOW_SECONDS // 86400,
             "token_values_emitted": False}
    atomic_write(STATE, (json.dumps(state, indent=1, sort_keys=True) + "\n").encode())
    print(json.dumps({"complete": not failed, "renewed": len(renewed),
                      "skipped": len(skipped), "failed": failed,
                      "state": str(STATE)}, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False,
                          "category": "fleet_token_renewal_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160] if isinstance(exc, ValueError) else ""},
                         sort_keys=True))
        raise SystemExit(1)
