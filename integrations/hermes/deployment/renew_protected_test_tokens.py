"""One-shot operator renewal for the two existing invented-data Hermes profiles.

Uses protected API/operator signing configuration, never changes it, and runs
all profile writes in a fresh unprivileged process. No model calls or daemon.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import pwd
import shlex
import stat
import subprocess
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import jwt


BINDINGS = {"enhanced-cognee-test": "hermes_test",
            "enhanced-cognee-test-two": "hermes_test_two"}
FIELDS = {"sub", "agent_id", "tenant", "project_id", "roles",
          "capture_policy", "iat", "exp"}
ORIGIN = "http://127.0.0.1:28080"
LIMIT = 1024 * 1024


class RenewalError(RuntimeError):
    """Messages are fixed operator diagnostics, never credential data."""


def private_bytes(path: Path, uid: int):
    if path != path.resolve(strict=True):
        raise RenewalError("A credential path contains a symlink.")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
                or before.st_mode & 0o077 or before.st_size > LIMIT):
            raise RenewalError("Credential ownership, permissions or size needs review.")
        raw = handle.read(LIMIT + 1)
        after = os.fstat(handle.fileno())
    if (len(raw) > LIMIT or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        raise RenewalError("A credential changed during inspection.")
    return raw, after


def token_line(raw: bytes):
    lines = raw.decode("utf-8").splitlines(keepends=True)
    found = []
    for index, line in enumerate(lines):
        key, separator, value = line.strip().removeprefix("export ").partition("=")
        if separator and key.strip() == "ENHANCED_COGNEE_ACCESS_TOKEN":
            parts = shlex.split(value, comments=True)
            if len(parts) != 1 or not parts[0]:
                raise RenewalError("The profile token assignment needs review.")
            found.append((index, parts[0]))
    if len(found) != 1:
        raise RenewalError("Expected exactly one profile token assignment.")
    return lines, found[0][0], found[0][1]


def verified_identity(token: str, secret: str, project: str, now: int):
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={
            "verify_exp": False, "verify_aud": False, "require": sorted(FIELDS)})
    except jwt.PyJWTError:
        raise RenewalError("An existing profile signature could not be verified.") from None
    if (set(claims) != FIELDS or claims["tenant"] != "qualification"
            or claims["project_id"] != project or claims["roles"] != ["api_client"]
            or claims["capture_policy"] != "selected"
            or type(claims["iat"]) is not int or type(claims["exp"]) is not int
            or not 0 < claims["exp"] - claims["iat"] <= 86400
            or claims["iat"] > now + 30
            or any(not isinstance(claims[key], str) or not 0 < len(claims[key]) <= 200
                   or any(ord(c) < 32 for c in claims[key]) for key in ("sub", "agent_id"))):
        raise RenewalError("The signed identity is outside the selected test scope.")
    return claims


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def api_status(token=None, origin=ORIGIN):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        with opener.open(Request(origin + "/v1/memories/status", headers=headers), timeout=5) as reply:
            raw = reply.read(262145)
            if len(raw) > 262144:
                raise RenewalError("The status response exceeded its size limit.")
            return reply.status, json.loads(raw)
    except HTTPError as error:
        code = error.code
        error.close()
        return code, {}
    except (URLError, OSError, TimeoutError, ValueError):
        raise RenewalError("The local API status check was unavailable.") from None


def check_identity_response(token, claims, request=api_status):
    code, data = request(token)
    if (code != 200 or not isinstance(data, dict) or data.get("ready") is not True
            or any(data.get(field) != claims[claim] for field, claim in (
                ("tenant_id", "tenant"), ("project_id", "project_id"), ("subject", "sub")))):
        raise RenewalError("Authenticated API readiness or signed scope did not match.")


def prepare(profile_root: Path, uid: int, secret: str, now: int, request=api_status):
    if not isinstance(secret, str) or len(secret.encode()) < 32:
        raise RenewalError("The protected signing configuration needs review.")
    if request(None)[0] not in (401, 403):
        raise RenewalError("The API did not reject the unauthenticated status request.")
    plans = []
    for name, project in BINDINGS.items():
        profile = profile_root / name
        if profile != profile.resolve(strict=True) or profile.stat().st_uid != uid:
            raise RenewalError("The selected profile directory needs review.")
        settings_raw, _ = private_bytes(profile / "enhanced_cognee.json", uid)
        settings = json.loads(settings_raw)
        if (str(settings.get("base_url", "")).rstrip("/") not in (ORIGIN, "http://localhost:28080")
                or settings.get("capture_policy") != "selected"):
            raise RenewalError("The selected test profile settings do not match.")
        raw, info = private_bytes(profile / ".env", uid)
        if secret.encode() in raw:
            raise RenewalError("Operator material was found in a profile; stop for review.")
        lines, index, old = token_line(raw)
        claims = verified_identity(old, secret, project, now)
        renew = claims["exp"] <= now
        renewed = dict(claims, iat=now, exp=now + 86400) if renew else claims
        token = jwt.encode(renewed, secret, algorithm="HS256") if renew else old
        check_identity_response(token, renewed, request)
        ending = "\r\n" if lines[index].endswith("\r\n") else "\n"
        lines[index] = "ENHANCED_COGNEE_ACCESS_TOKEN=" + token + ending
        directory = profile.stat()
        plans.append({"profile": str(profile), "name": name, "renew": renew,
            "token": token, "claims": renewed, "sha256": hashlib.sha256(raw).hexdigest(),
            "file_identity": [info.st_dev, info.st_ino],
            "directory_identity": [directory.st_dev, directory.st_ino],
            "replacement": base64.b64encode("".join(lines).encode("utf-8")).decode("ascii")})
    return plans


# This fixed child receives only ordinary profile data/client credentials. The
# protected signing secret is never passed through arguments, stdin or env.
WRITER = r'''
import base64, fcntl, hashlib, json, os, stat, sys, uuid
from pathlib import Path
try:
    p = json.load(sys.stdin)
    path = Path(p["profile"])
    if os.geteuid() == 0 or path != path.resolve(strict=True):
        raise ValueError()
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    directory_info = os.fstat(directory)
    if (directory_info.st_uid != os.geteuid()
            or [directory_info.st_dev, directory_info.st_ino] != p["directory_identity"]):
        raise ValueError()
    fd = os.open(".env", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, "rb") as source:
        fcntl.flock(source, fcntl.LOCK_EX | fcntl.LOCK_NB)
        info = os.fstat(source.fileno())
        raw = source.read(1048577)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077 or len(raw) > 1048576
                or [info.st_dev, info.st_ino] != p["file_identity"]
                or hashlib.sha256(raw).hexdigest() != p["sha256"]):
            raise ValueError()
        suffix = uuid.uuid4().hex
        backup = "env-before-protected-token-renewal-" + suffix
        temporary = "env-protected-renewal-" + suffix + ".tmp"
        for name, data in ((backup, raw), (temporary, base64.b64decode(p["replacement"], validate=True))):
            out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(out, "wb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        current_fd = os.open(".env", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(current_fd, "rb") as current:
            current_info = os.fstat(current.fileno())
            if (not stat.S_ISREG(current_info.st_mode)
                    or [current_info.st_dev, current_info.st_ino] != p["file_identity"]
                    or hashlib.sha256(current.read(1048577)).hexdigest() != p["sha256"]):
                raise ValueError()
        os.replace(temporary, ".env", src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    os.close(directory)
    print(json.dumps({"complete": True, "backup": backup}))
except Exception:
    print(json.dumps({"complete": False, "stage": "profile_update"}))
    sys.exit(1)
'''


def install(plan, uid, gid):
    payload = {key: plan[key] for key in (
        "profile", "sha256", "file_identity", "directory_identity", "replacement")}
    result = subprocess.run(["/usr/bin/python3", "-I", "-c", WRITER],
        input=json.dumps(payload), text=True, capture_output=True, timeout=30,
        user=uid, group=gid, extra_groups=(),
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode:
        raise RenewalError("A profile update failed; retained files need review. Earlier updates may have completed.")
    receipt = json.loads(result.stdout)
    if receipt.get("complete") is not True:
        raise RenewalError("A profile update was not acknowledged.")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Install after both profiles pass preflight")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.exit(1, "Use the supervised root operator, not an agent runtime.\n")
    try:
        owner = pwd.getpwnam("vincentspereira")
        if owner.pw_uid == 0:
            raise RenewalError("The profile owner must not be root.")
        configs = [json.loads(private_bytes(Path("/etc/enhanced-cognee") / name, 0)[0])
                   for name in ("api.json", "operator.json")]
        secret = configs[0]["ENHANCED_JWT_SECRET"]
        if not hmac.compare_digest(secret.encode(), configs[1]["ENHANCED_JWT_SECRET"].encode()):
            raise RenewalError("Protected API and operator signing configurations differ.")
        root = Path(owner.pw_dir) / ".hermes/profiles"
        plans = prepare(root, owner.pw_uid, secret, int(time.time()))
        for plan in plans:
            if args.apply and plan["renew"]:
                install(plan, owner.pw_uid, owner.pw_gid)
                installed, _ = private_bytes(Path(plan["profile"]) / ".env", owner.pw_uid)
                if installed != base64.b64decode(plan["replacement"]):
                    raise RenewalError("Post-update file verification failed; original backups were retained.")
                check_identity_response(token_line(installed)[2], plan["claims"])
            label = "renewed" if args.apply and plan["renew"] else "unchanged" if args.apply else "preflight passed"
            expiry = datetime.fromtimestamp(plan["claims"]["exp"], timezone.utc).isoformat()
            print(plan["name"] + " | " + label + " | authenticated HTTP 200 | expires UTC: " + expiry, flush=True)
    except RenewalError as error:
        parser.exit(1, "Test renewal stopped: " + str(error) + "\n")
    except Exception:
        parser.exit(1, "Test renewal stopped; no secret values printed. Retained files may need review.\n")


if __name__ == "__main__":
    main()
