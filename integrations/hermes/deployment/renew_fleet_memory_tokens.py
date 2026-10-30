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
RECEIPTS = HOME / "fleet-token-receipts.json"
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


def profiles() -> list[str]:
    names = ["default"]
    receipts = json.loads(RECEIPTS.read_text())
    roles = sorted(name for name in receipts.get("receipts", {})
                   if name not in CANARIES)
    require(isinstance(roles, list) and len(roles) <= 64, "receipts_shape")
    return names + roles


def env_path(profile: str) -> Path:
    return HOME / ".env" if profile == "default" else HOME / "profiles" / profile / ".env"


def renew(profile: str) -> dict:
    process = subprocess.run(
        [sys.executable, "-I", str(PROVISIONER), "--profile", profile,
         "--ttl-hours", str(TTL_HOURS)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=180)
    try:
        receipt = json.loads(process.stdout)
    except ValueError:
        receipt = {"complete": False, "detail": "unparseable"}
    return {"profile": profile, "complete": bool(receipt.get("complete")),
            "expires_utc": receipt.get("expires_utc"),
            "error": receipt.get("detail") or receipt.get("error_kind")}


def main():
    require(os.geteuid() == 0 and os.uname().nodename == "Ubuntu-Hermes",
            "run_on_gateway_host_as_root")
    require(PROVISIONER.is_file(), "provisioner_missing")
    now = int(time.time())
    renewed, skipped, failed, expiries = [], [], [], {}
    for profile in profiles():
        path = env_path(profile)
        token = load_profile_token(path)
        try:
            current_exp = decode_exp(token) if token else None
        except ValueError:
            current_exp = None
        if current_exp is not None and not needs_renewal(current_exp, now):
            skipped.append(profile)
            expiries[profile] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime(current_exp))
            continue
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
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")
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
