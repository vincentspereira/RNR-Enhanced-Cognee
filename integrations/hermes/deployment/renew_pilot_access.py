"""Human-operated, fixed-scope pilot renewal using the reviewed issuer core.

Root only signs; the restricted child inspects and changes its own profile.
No unattended issuer, secret output, model call, memory mutation or deletion.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tarfile
import time
import uuid


def verified_sources(raw, expected):
    names = {"integrations/hermes/deployment/provision_pilot_access.py",
             "integrations/hermes/deployment/renew_pilot_access.py"}
    if set(expected) != names or not isinstance(raw, bytes) or len(raw) > 262144:
        raise ValueError("Unapproved renewal bundle")
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for index, member in enumerate(archive):
            if index >= 8: raise ValueError("Renewal bundle entry budget")
            if member.isdir() and member.name.rstrip("/") in {"integrations", "integrations/hermes", "integrations/hermes/deployment"}: continue
            if member.name not in names or member.name in result or not member.isfile() or not 0 < member.size <= 65536:
                raise ValueError("Unexpected renewal bundle member")
            source = archive.extractfile(member).read(65537)
            if len(source) != member.size or hashlib.sha256(source).hexdigest() != expected[member.name]:
                raise ValueError("Renewal source mismatch")
            result[member.name] = source
    if set(result) != names: raise ValueError("Incomplete renewal bundle")
    return result


def token_claims(core, token):
    """Unverified shape restriction only; live API tests establish acceptance."""
    if not isinstance(token, str) or not 32 <= len(token) < 4096 or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
        raise core["ProvisionError"]("The existing pilot credential needs review.")
    header, payload, _ = token.split(".")
    decode = lambda value: json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
    claims = decode(payload)
    if (decode(header) != {"alg": "HS256", "typ": "JWT"} or not isinstance(claims, dict)
            or set(claims) != set(core["IDENTITY"]) | {"iat", "exp"}
            or any(claims.get(k) != v for k, v in core["IDENTITY"].items())
            or type(claims["iat"]) is not int or type(claims["exp"]) is not int
            or claims["iat"] < 0 or claims["iat"] > int(time.time()) + 120
            or claims["exp"] - claims["iat"] != 86400):
        raise core["ProvisionError"]("The existing pilot credential scope/lifetime needs review.")
    return claims


def environment(core, raw, replacement=None):
    # Third-party parsing is confined to the restricted child/test runtime.
    from dotenv.parser import parse_stream
    if not isinstance(raw, bytes) or len(raw) > core["LIMIT"] or b"\x00" in raw:
        raise core["ProvisionError"]("The existing environment needs review.")
    bindings = list(parse_stream(io.StringIO(raw.decode("utf-8"))))
    selected = [row for row in bindings if row.key == core["TOKEN_NAME"]]
    if any(row.error for row in bindings) or len(selected) != 1:
        raise core["ProvisionError"]("Exactly one well-formed pilot credential is required.")
    old = selected[0].value
    token_claims(core, old)
    if replacement is None: return old
    token_claims(core, replacement)
    text = selected[0].original.string
    if text.count(old) != 1:
        raise core["ProvisionError"]("The credential assignment needs review.")
    updated = "".join(row.original.string.replace(old, replacement, 1) if row is selected[0]
                      else row.original.string for row in bindings).encode("utf-8")
    after = list(parse_stream(io.StringIO(updated.decode("utf-8"))))
    pairs = lambda rows: [(row.key, row.value) for row in rows if row.key not in (None, core["TOKEN_NAME"])]
    if (len(updated) > core["LIMIT"] or any(row.error for row in after)
            or pairs(after) != pairs(bindings) or environment(core, updated) != replacement):
        raise core["ProvisionError"]("Renewal did not preserve the environment.")
    return updated


def status(core, token):
    code, data = core["api_status"](token)
    if (code != 200 or not isinstance(data, dict) or data.get("ready") is not True
            or any(data.get(field) != core["IDENTITY"][claim] for field, claim in (
                ("tenant_id", "tenant"), ("project_id", "project_id"), ("subject", "sub")))
            or data.get("schema_version") != 3 or data.get("encryption") != "AES-256-GCM"
            or type(data.get("active_records")) is not int or data["active_records"] != 2
            or type(data.get("pending_change_events")) is not int or data["pending_change_events"] < 0):
        raise core["ProvisionError"]("The populated pilot API scope/readiness differs.")
    return data["active_records"]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def finish(core, directory, name, journal, outcome):
    receipt = {"journal_sha256": digest(json.dumps(journal, sort_keys=True).encode()), "outcome": outcome}
    core["create_private_at"](directory, name.removesuffix(".json") + ".done.json", json.dumps(receipt).encode())
    os.fsync(directory)


def reconcile(core, directory, uid, current):
    """Close known interrupted attempts without reverting or deleting anything."""
    names = [name for name in os.listdir(directory) if re.fullmatch(r"\.cognee-renewal-[0-9a-f]{32}\.json", name)]
    if len(names) > 128: raise core["ProvisionError"]("The renewal evidence ledger needs archival review.")
    recovered = 0
    for name in sorted(names):
        journal = json.loads(core["read_private_at"](directory, name, uid)[0])
        ident = name[len(".cognee-renewal-"):-len(".json")]
        backup, candidate = ".env-before-cognee-renew-" + ident, ".env-cognee-renew-" + ident
        if (not isinstance(journal, dict) or set(journal) != {"backup", "candidate", "before", "after"}
                or journal["backup"] != backup or journal["candidate"] != candidate
                or any(not isinstance(journal[k], str) or not re.fullmatch(r"[0-9a-f]{64}", journal[k]) for k in ("before", "after"))):
            raise core["ProvisionError"]("A renewal journal needs manual review; evidence retained.")
        done = name.removesuffix(".json") + ".done.json"
        try: completed = json.loads(core["read_private_at"](directory, done, uid)[0])
        except FileNotFoundError: completed = None
        if completed is not None:
            if completed not in [{"journal_sha256": digest(json.dumps(journal, sort_keys=True).encode()), "outcome": value}
                                 for value in ("published", "not_published")]:
                raise core["ProvisionError"]("A renewal completion receipt needs manual review.")
            continue
        before = core["read_private_at"](directory, backup, uid)[0]
        if digest(before) != journal["before"]:
            raise core["ProvisionError"]("A renewal recovery copy differs; evidence retained.")
        active = digest(current)
        if active == journal["before"]:
            staged = core["read_private_at"](directory, candidate, uid)[0]
            if digest(staged) != journal["after"]:
                raise core["ProvisionError"]("A staged renewal differs; evidence retained.")
            outcome = "not_published"
        elif active == journal["after"]: outcome = "published"
        else: raise core["ProvisionError"]("An interrupted renewal conflicts with current settings; review required.")
        finish(core, directory, name, journal, outcome)
        recovered += 1
    return recovered


def renew(core, directory, bundle, uid, checkpoint=lambda phase: None):
    now = int(time.time())
    claims = token_claims(core, bundle["token"])
    if (set(bundle) != {"token", "expired", "altered", "claims"} or claims != bundle["claims"]
            or not 0 <= now - claims["iat"] <= 120):
        raise core["ProvisionError"]("The new ordinary credential scope/lifetime needs review.")
    original, _ = core["read_private_at"](directory, ".env", uid)
    if environment(core, original) == bundle["token"]:
        raise core["ProvisionError"]("This credential is already installed; no renewal is needed.")
    recovered = reconcile(core, directory, uid, original)
    preserved = {name: core["read_private_at"](directory, name, uid)[0]
                 for name in ("config.yaml", "enhanced_cognee.json", "auth.json")}
    if (preserved["config.yaml"] != b"memory:\n  provider: enhanced_cognee\n"
            or json.loads(preserved["enhanced_cognee.json"]) != {"base_url": "http://127.0.0.1:28080",
                "timeout": 10, "include_shared": True, "capture_policy": "selected"}):
        raise core["ProvisionError"]("The pilot settings differ; preserved for review.")
    for token in (None, bundle["expired"], bundle["altered"]):
        if core["api_status"](token)[0] != 401:
            raise core["ProvisionError"]("A missing/expired/altered credential was not denied.")
    status(core, bundle["token"])
    updated = environment(core, original, bundle["token"])
    ident = uuid.uuid4().hex
    backup, candidate = ".env-before-cognee-renew-" + ident, ".env-cognee-renew-" + ident
    name = ".cognee-renewal-" + ident + ".json"
    core["create_private_at"](directory, backup, original)
    core["create_private_at"](directory, candidate, updated)
    if (core["read_private_at"](directory, backup, uid)[0] != original
            or core["read_private_at"](directory, candidate, uid)[0] != updated):
        raise core["ProvisionError"]("The renewal copies did not verify.")
    journal = {"backup": backup, "candidate": candidate, "before": digest(original), "after": digest(updated)}
    core["create_private_at"](directory, name, json.dumps(journal).encode())
    os.fsync(directory)
    checkpoint("prepared")
    if (core["read_private_at"](directory, ".env", uid)[0] != original
            or any(core["read_private_at"](directory, key, uid)[0] != value for key, value in preserved.items())):
        raise core["ProvisionError"]("The profile changed during renewal; copies retained.")
    os.replace(candidate, ".env", src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
    checkpoint("published")
    if (core["read_private_at"](directory, ".env", uid)[0] != updated
            or any(core["read_private_at"](directory, key, uid)[0] != value for key, value in preserved.items())):
        raise core["ProvisionError"]("Renewal readback needs review; copies retained.")
    status(core, environment(core, updated))
    checkpoint("verified")
    finish(core, directory, name, journal, "published")
    return {"complete": True, "stage": "credential_renewal", "effective_user": "hermes-runtime",
        "profile": "enhanced-cognee-pilot", "credential_renewed": True,
        "expires_utc": datetime.fromtimestamp(claims["exp"], timezone.utc).isoformat(),
        "interrupted_attempts_reconciled": recovered, "previous_environment_preserved": True,
        "settings_and_oauth_preserved": True, "authenticated_api_status_passed": True,
        "unauthenticated_expired_altered_denied": True, "signing_key_available_to_runtime": False,
        "model_called": False, "memory_records_written": False, "runtime_qualified": False}


def child_main(core, bundle):
    try:
        account = pwd.getpwuid(os.geteuid())
        fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
        if (account.pw_name != "hermes-runtime" or account.pw_uid == 0 or Path(account.pw_dir) != core["HOME"]
                or Path.cwd() != core["HOME"] or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
                or fields.get("NoNewPrivs", "").strip() != "1"
                or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))):
            raise core["ProvisionError"]("The renewal child identity needs review.")
        directory = core["open_directory"](core["PROFILE"], {0, account.pw_uid})
        try:
            info = os.fstat(directory)
            if info.st_uid != account.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
                raise core["ProvisionError"]("The pilot directory needs protection review.")
            lock = os.open(".cognee-renewal.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                           0o600, dir_fd=directory)
            try:
                core["read_private_fd"](lock, account.pw_uid)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                report = renew(core, directory, bundle, account.pw_uid)
            finally: os.close(lock)
        finally: os.close(directory)
        print(json.dumps(report))
    except Exception:
        print(json.dumps({"complete": False, "stage": "credential_renewal",
            "category": "renewal_incomplete_preserve_evidence_review_before_retry"}))
        raise SystemExit(1) from None


def run_child(core, account, sources, bundle):
    base = "integrations/hermes/deployment/"
    code = ("import json,sys\ncore={'__name__':'reviewed_issuer'}\n"
        "exec(compile(" + repr(sources[base + "provision_pilot_access.py"]) + ",'reviewed-issuer','exec'),core)\n"
        "renewal={'__name__':'reviewed_renewal'}\nexec(compile(" + repr(sources[base + "renew_pilot_access.py"])
        + ",'reviewed-renewal','exec'),renewal)\nrenewal['child_main'](core,json.load(sys.stdin))\n")
    result = subprocess.run(["/usr/bin/setpriv", "--no-new-privs", "--", "/usr/bin/env", "-i",
        "HOME=" + str(core["HOME"]), "USER=hermes-runtime", "LOGNAME=hermes-runtime",
        "PATH=/usr/bin:/bin", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1",
        str(core["RELEASE"] / "venv/bin/python"), "-I", "-B", "-c", code],
        input=json.dumps(bundle).encode(), user=account.pw_uid, group=account.pw_gid,
        extra_groups=(), cwd=core["HOME"], env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if result.returncode or len(result.stdout) > 16384:
        raise core["ProvisionError"]("Pilot renewal incomplete; private evidence retained for review.")
    report = json.loads(result.stdout)
    expected = {"complete": True, "stage": "credential_renewal", "effective_user": "hermes-runtime",
        "profile": "enhanced-cognee-pilot", "credential_renewed": True,
        "expires_utc": datetime.fromtimestamp(bundle["claims"]["exp"], timezone.utc).isoformat(),
        "previous_environment_preserved": True, "settings_and_oauth_preserved": True,
        "authenticated_api_status_passed": True, "unauthenticated_expired_altered_denied": True,
        "signing_key_available_to_runtime": False, "model_called": False, "memory_records_written": False,
        "runtime_qualified": False}
    count = report.get("interrupted_attempts_reconciled") if isinstance(report, dict) else None
    if (not isinstance(report, dict) or set(report) != set(expected) | {"interrupted_attempts_reconciled"}
            or any(type(report.get(key)) is not type(value) or report.get(key) != value for key, value in expected.items())
            or type(count) is not int or not 0 <= count <= 128):
        raise core["ProvisionError"]("The renewal child receipt needs review; private output suppressed.")
    return report


def main(*, core, sources):
    # The hash-verified core retains its operator/account/executable checks and
    # root-only key loader. Its root path never walks the runtime-owned profile.
    core["run_child"] = lambda account, source, bundle: run_child(core, account, sources, bundle)
    core["main"](sources["integrations/hermes/deployment/provision_pilot_access.py"])


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified operator renewal bundle.")
