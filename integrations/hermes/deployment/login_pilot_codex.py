"""Fresh native Codex OAuth for the restricted pilot, without model edits.

Run only the reviewed blob under hermes-runtime with explicit owner selection.
Existing auth stores are preserved/refused. Device codes are for the owner's
terminal only; OAuth tokens and native error bodies are never printed.
"""
from __future__ import annotations

import contextlib
import fcntl
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import uuid
from types import SimpleNamespace


HOME = Path("/var/lib/hermes-runtime")
PROFILE = HOME / ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
URL = "https://auth.openai.com/codex/device"
LABEL = "cognee-pilot-codex"
SECONDARY_LABEL = "cognee-pilot-codex-secondary"
EXPECTED_CONFIG = b"memory:\n  provider: enhanced_cognee\n"


class LoginError(RuntimeError):
    """Fixed public diagnostic only."""


def read_private(name, uid):
    if name not in {"config.yaml", "enhanced_cognee.json", ".env", "auth.json", "auth.lock"}:
        raise LoginError("Unapproved profile file.")
    fd = os.open(PROFILE / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                or before.st_size > 1048576):
            raise LoginError("Profile file protection needs review.")
        raw = handle.read(1048577)
        after = os.fstat(handle.fileno())
        if (len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise LoginError("A profile file changed while being checked.")
        return raw


def preflight(approved_login, *, existing_auth=False):
    account = pwd.getpwuid(os.geteuid())
    if (approved_login is not True or account.pw_name != "hermes-runtime" or account.pw_uid == 0
            or Path(account.pw_dir) != HOME or Path(os.environ.get("HOME", "")) != HOME
            or os.environ.get("HERMES_HOME") != str(PROFILE)
            or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
            or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)):
        raise LoginError("Use the approved restricted account and protected Python.")
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    if (fields.get("NoNewPrivs", "").strip() != "1"
            or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))):
        raise LoginError("Restricted process protection needs review.")
    for path in reversed((PROFILE, *PROFILE.parents)):
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, account.pw_uid}
                or info.st_mode & 0o022):
            raise LoginError("Profile ancestor protection needs review.")
    info = PROFILE.stat()
    if info.st_uid != account.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
        raise LoginError("Pilot directory privacy needs review.")
    paths = (HOME / ".hermes/auth.json", HOME / ".codex/auth.json")
    if not existing_auth:
        paths += (PROFILE / "auth.json", PROFILE / "auth.lock")
    for path in paths:
        if os.path.lexists(path):
            raise LoginError("Existing authentication state preserved; reconcile before another login.")
    if os.access("/home/vincentspereira/.hermes/auth.json", os.R_OK):
        raise LoginError("Human authentication store must remain inaccessible.")
    snapshots = {name: read_private(name, account.pw_uid)
                 for name in ("config.yaml", "enhanced_cognee.json", ".env")}
    if snapshots["config.yaml"] != EXPECTED_CONFIG:
        raise LoginError("Pilot settings differ; preserved without overwrite.")
    if existing_auth and os.path.lexists(PROFILE / "auth.lock"):
        read_private("auth.lock", account.pw_uid)
    return account.pw_uid, snapshots


class LoginOutput(io.TextIOBase):
    """Show only the native fixed URL, device code and waiting instruction."""

    def __init__(self, destination):
        self.destination = destination
        self.pending = ""
        self.expect_code = False
        self.code_shown = False

    def write(self, value):
        self.pending += value
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            if line == URL:
                print("Open this address in your browser: " + URL, file=self.destination, flush=True)
            elif line == "2. Enter this code:":
                self.expect_code = True
            elif self.expect_code and line:
                if not re.fullmatch(r"[A-Z0-9]{3,16}(?:-[A-Z0-9]{3,16}){1,3}", line):
                    raise LoginError("The native device-code format needs review.")
                print("Enter this private one-time code: " + line, file=self.destination, flush=True)
                print("Complete sign-in in your browser. Do not paste the code into chat.",
                      file=self.destination, flush=True)
                self.code_shown = True
                self.expect_code = False
        return len(value)

    def flush(self):
        self.destination.flush()


def native_login(label=LABEL):
    if label not in {LABEL, SECONDARY_LABEL}:
        raise LoginError("Unapproved pilot credential label.")
    sys.path.insert(0, str(RELEASE / "repo"))
    import hermes_constants
    from hermes_cli import auth_commands
    for module in (hermes_constants, auth_commands):
        if not Path(module.__file__).resolve(strict=True).is_relative_to(RELEASE / "repo"):
            raise LoginError("Native module source differs from the protected release.")
    if Path(hermes_constants.get_hermes_home()).resolve() != PROFILE:
        raise LoginError("Native authentication scope differs from the pilot.")
    output = LoginOutput(sys.stdout)
    args = SimpleNamespace(provider="openai-codex", auth_type="oauth", label=label,
                           no_browser=True, browser=False, timeout=20.0, priority=None)
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
        auth_commands.auth_add_command(args)
    if not output.code_shown:
        raise LoginError("Fresh device-code sign-in was not observed; preserve resulting state.")


def verify_auth(uid):
    auth = json.loads(read_private("auth.json", uid))
    pool = auth.get("credential_pool", {})
    rows = pool.get("openai-codex", []) if isinstance(pool, dict) else []
    if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
            or rows[0].get("label") != LABEL or rows[0].get("auth_type") != "oauth"
            or rows[0].get("source") != "manual:device_code"
            or not all(isinstance(rows[0].get(name), str) and rows[0][name]
                       for name in ("access_token", "refresh_token"))):
        raise LoginError("Fresh pilot credential shape did not verify; preserve state for review.")


def secondary_rows(raw, *, added=False):
    """Accept only the known pilot pool; never infer an account from priority."""
    auth = json.loads(raw)
    pool = auth.get("credential_pool", {}) if isinstance(auth, dict) else {}
    rows = pool.get("openai-codex", []) if isinstance(pool, dict) else []
    labels = {LABEL, SECONDARY_LABEL} if added else {LABEL}
    if (not isinstance(rows, list) or len(rows) != len(labels)
            or any(not isinstance(row, dict) for row in rows)
            or {row.get("label") for row in rows} != labels):
        raise LoginError("Unexpected pilot account pool; preserve state for review.")
    for row in rows:
        if (row.get("auth_type") != "oauth" or row.get("source") != "manual:device_code"
                or row.get("base_url", "").rstrip("/") != "https://chatgpt.com/backend-api/codex"
                or not all(isinstance(row.get(key), str) and 32 <= len(row[key]) <= 32768
                    and row[key].isascii() and all(33 <= ord(c) <= 126 for c in row[key])
                    for key in ("access_token", "refresh_token"))):
            raise LoginError("Pilot credential protection needs review.")
    return {row["label"]: row for row in rows}


def account_identity(token):
    """Native unverified identity hint; never a validity or quota assertion."""
    sys.path.insert(0, str(RELEASE / "repo"))
    from agent import credential_pool
    if not Path(credential_pool.__file__).resolve(strict=True).is_relative_to(RELEASE / "repo"):
        raise LoginError("Native identity module differs from the protected release.")
    identity = credential_pool._codex_principal_identity(token)
    if (not isinstance(identity, tuple) or len(identity) != 2
            or not all(isinstance(value, str) and value for value in identity)):
        raise LoginError("Account identity hints unavailable; preserve state for review.")
    return identity


def preserve_auth(raw):
    """Private no-overwrite recovery copy; never print or publish its contents."""
    name = "auth-before-secondary-" + uuid.uuid4().hex + ".json"
    fd = os.open(PROFILE / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return name


def main_secondary(*, approved_login=False):
    phase = "restricted_preflight"
    snapshots = {}
    uid = None
    backup = None
    lock = None
    try:
        uid, snapshots = preflight(approved_login, existing_auth=True)
        os.chdir(HOME)
        os.umask(0o077)
        logging.disable(logging.CRITICAL)
        phase = "existing_pilot_auth"
        # Separate from native auth.lock: native auth_add must acquire that lock itself.
        lock = os.open(PROFILE / ".secondary-login.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        info = os.fstat(lock)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise LoginError("Pilot sign-in lock protection needs review.")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = read_private("auth.json", uid)
        old = secondary_rows(before)[LABEL]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            old_identity = account_identity(old["access_token"])
        phase = "openid_dns"
        result = subprocess.run([str(RELEASE / "venv/bin/python"), "-I", "-B", "-c",
            "import socket; socket.getaddrinfo('auth.openai.com',443,type=socket.SOCK_STREAM)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
        if result.returncode:
            raise LoginError("OpenAI sign-in hostname did not resolve; no login started.")
        phase = "preserve_existing_auth"
        if read_private("auth.json", uid) != before:
            raise LoginError("Pilot authentication changed; reconcile before login.")
        backup = preserve_auth(before)
        phase = "device_signin"
        print("Sign in with your SECOND OpenAI account in a private browser window."
              " Existing pilot credentials will be retained.", flush=True)
        native_login(SECONDARY_LABEL)
        phase = "credential_verification"
        after = read_private("auth.json", uid)
        rows = secondary_rows(after, added=True)
        if any(rows[LABEL].get(key) != value for key, value in old.items()):
            raise LoginError("Original pilot credential changed; preserve all state for review.")
        # Account IDs stay private. These are decoded hints, not a signature check.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            new_identity = account_identity(rows[SECONDARY_LABEL]["access_token"])
        if new_identity == old_identity or rows[SECONDARY_LABEL]["access_token"] == old["access_token"]:
            raise LoginError("This appears to be the same account; retain both entries and review before tests.")
        if any(read_private(name, uid) != raw for name, raw in snapshots.items()):
            raise LoginError("Pilot settings changed; preserve state and reconcile.")
        print(json.dumps({"complete": True, "effective_user": "hermes-runtime",
            "profile": "enhanced-cognee-pilot", "secondary_pilot_oauth_saved": True,
            "credential_label": SECONDARY_LABEL, "existing_credential_fields_preserved": True,
            "private_auth_backup": backup, "account_identity_hints_differ": True,
            "account_identity_signature_verified": False, "pilot_settings_unchanged": True,
            "human_credentials_copied": False, "model_defaults_changed": False,
            "model_called": False, "quota_availability_tested": False,
            "memory_records_written": False, "runtime_qualified": False}, indent=2))
    except (Exception, SystemExit) as error:
        unchanged = None
        if snapshots:
            try: unchanged = all(read_private(name, uid) == raw for name, raw in snapshots.items())
            except Exception: pass
        print(json.dumps({"complete": False, "failure_stage": phase,
            "reason": str(error) if isinstance(error, LoginError) else "Secondary sign-in incomplete; private details suppressed.",
            "pilot_settings_unchanged": unchanged, "private_auth_backup": backup,
            "auth_state_present_preserve_for_review": os.path.lexists(PROFILE / "auth.json"),
            "model_called": False, "memory_records_written": False,
            "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None
    finally:
        if lock is not None:
            os.close(lock)


def main(*, approved_login=False):
    phase = "restricted_preflight"
    snapshots = {}
    uid = None
    try:
        uid, snapshots = preflight(approved_login)
        os.chdir(HOME)
        os.umask(0o077)
        logging.disable(logging.CRITICAL)
        phase = "openid_dns"
        result = subprocess.run([str(RELEASE / "venv/bin/python"), "-I", "-B", "-c",
            "import socket; socket.getaddrinfo('auth.openai.com',443,type=socket.SOCK_STREAM)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
        if result.returncode:
            raise LoginError("OpenAI sign-in hostname did not resolve; no login started.")
        phase = "device_signin"
        native_login()
        phase = "credential_verification"
        verify_auth(uid)
        if any(read_private(name, uid) != raw for name, raw in snapshots.items()):
            raise LoginError("Pilot settings changed; preserve state and reconcile.")
        print(json.dumps({"complete": True, "effective_user": "hermes-runtime",
            "profile": "enhanced-cognee-pilot", "fresh_pilot_oauth_saved": True,
            "pilot_settings_unchanged": True, "human_credentials_copied": False,
            "model_defaults_changed": False, "model_called": False,
            "memory_records_written": False, "runtime_qualified": False}, indent=2))
    except (Exception, SystemExit) as error:
        unchanged = None
        if snapshots:
            try:
                unchanged = all(read_private(name, uid) == raw for name, raw in snapshots.items())
            except Exception:
                pass
        print(json.dumps({"complete": False, "failure_stage": phase,
            "reason": str(error) if isinstance(error, LoginError) else "Native sign-in incomplete; private details suppressed.",
            "pilot_settings_unchanged": unchanged,
            "auth_state_present_preserve_for_review": os.path.lexists(PROFILE / "auth.json"),
            "model_called": False, "memory_records_written": False,
            "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified restricted operator command.")
