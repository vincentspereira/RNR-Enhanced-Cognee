#!/usr/bin/env python3
"""Read-only cutover probe for the Enhanced Cognee memory API.

Subcommands (offline-testable, stdlib only, never prints secrets):

  usage   Mint a short-lived scoped token in-process from the root-only
          api.json credential and read /v1/memories/summarization/status for
          each requested tenant/project scope on the CURRENT (old) API. Used
          by cutover pre-checks to record today's model usage honestly.

  verify  After the cutover restart: check /health/ready, run one ordinary
          remember+recall round-trip over the same HTTP contract the Hermes
          plugin uses, and confirm the optional analysis endpoints are
          withheld (422 + status configured=false).

The access token and the JWT signing secret exist only inside this process.
Output is ASCII JSON on stdout. Exit codes: 0 pass, 1 failed check,
2 configuration/transport error. No service is modified by this tool.

Run as root with the OS interpreter:
  sudo /usr/bin/python3 -I -S -B cutover_probe_20261105.py <subcommand> ...
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request

ANALYSIS_NOT_CONFIGURED = "The model route is not configured for this service"
TIMEOUT = 10


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def mint_token(secret: str, *, subject: str, tenant: str, project: str,
               ttl: int = 600, now: float | None = None) -> str:
    """Compact HS256 JWT matching src/security/enterprise_auth.py acceptance.

    Production verification requires 'exp' and 'sub'; the scope is carried by
    the 'tenant' and 'project_id' claims (see MemoryScope.from_principal) and
    write access by the 'user' role.
    """
    if not secret or not secret.isascii():
        raise ValueError("A non-empty ASCII signing secret is required")
    issued = int(now if now is not None else time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "roles": ["user"], "tenant": tenant,
               "project_id": project, "iat": issued, "exp": issued + ttl}
    signing_input = (_b64url(json.dumps(header, separators=(",", ":"),
                                        sort_keys=True).encode("ascii"))
                     + "." + _b64url(json.dumps(payload, separators=(",", ":"),
                                                sort_keys=True).encode("ascii")))
    signature = hmac.new(secret.encode("ascii"), signing_input.encode("ascii"),
                         hashlib.sha256).digest()
    return signing_input + "." + _b64url(signature)


def load_signing_secret(credential_path: str) -> str:
    """Read the root-only api.json in-process; return ENHANCED_JWT_SECRET."""
    with open(credential_path, "rb") as handle:
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError("API credential file exceeded its size limit")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("API credential file is malformed")
    secret = value.get("ENHANCED_JWT_SECRET")
    if not isinstance(secret, str) or not secret:
        raise ValueError(
            "ENHANCED_JWT_SECRET is absent; consult the owner before proceeding")
    return secret


def api_request(origin: str, method: str, path: str, token: str,
                body: dict | None = None):
    """One bounded JSON request with the bearer token; returns (status, json)."""
    data = json.dumps(body, ensure_ascii=True).encode("ascii") if body is not None else None
    request = urllib.request.Request(origin.rstrip("/") + path, data=data, method=method,
                                     headers={"Authorization": "Bearer " + token,
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(262145)
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read(262145)
        status = exc.code
    if len(raw) > 262144:
        raise ValueError("Memory response exceeded its size budget")
    parsed = json.loads(raw) if raw else None
    return status, (parsed if isinstance(parsed, dict) else {"raw": "non-dict"})


def _scopes(pairs):
    result = []
    for pair in pairs:
        tenant, _, project = pair.partition("/")
        if not tenant or not project or "/" in project:
            raise ValueError("Scope must look like tenant/project")
        result.append((tenant, project))
    return result


def cmd_usage(args) -> int:
    scopes = _scopes(args.scope)
    secret = load_signing_secret(args.api_credential)
    findings, any_charged, any_unknown = [], False, False
    for tenant, project in scopes:
        token = mint_token(secret, subject="cutover-usage-check", tenant=tenant,
                           project=project, ttl=args.ttl)
        try:
            status, body = api_request(args.origin, "GET",
                                       "/v1/memories/summarization/status", token)
        except (OSError, ValueError) as exc:
            findings.append({"tenant": tenant, "project": project,
                             "error_kind": type(exc).__name__})
            any_unknown = True
            continue
        configured = body.get("configured") if isinstance(body, dict) else None
        used = body.get("used_today") if isinstance(body, dict) else None
        charged = bool(configured) and isinstance(used, int) and used > 0
        unknown = status != 200 or (bool(configured) and not isinstance(used, int))
        any_charged, any_unknown = any_charged or charged, any_unknown or unknown
        findings.append({"tenant": tenant, "project": project, "http_status": status,
                         "configured": configured, "used_today": used,
                         "charged_today": charged, "unknown": unknown})
    print(json.dumps({"probe": "usage", "origin": args.origin,
                      "checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                      "scopes": findings, "any_charged_today": any_charged,
                      "any_unknown_scope": any_unknown,
                      "rule": "optional analysis stays withheld until a clean "
                              "UTC-day boundary when any_charged_today or "
                              "any_unknown_scope is true"}, ensure_ascii=True))
    return 0


def cmd_verify(args) -> int:
    secret = load_signing_secret(args.api_credential)
    tenant, project = _scopes([args.scope])[0]
    token = mint_token(secret, subject="cutover-post-switch-check", tenant=tenant,
                       project=project, ttl=args.ttl)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checks = []

    def record(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    try:
        status, body = api_request(args.origin, "GET", "/health/ready", token)
        record("health_ready", status == 200 and body.get("ready") is True,
               {"http_status": status, "ready": body.get("ready")})

        record_id = None
        status, body = api_request(args.origin, "POST", "/v1/memories", token,
                                   {"content": "Cutover post-switch plugin-path check " + stamp,
                                    "idempotency_key": "cutover-check-" + stamp,
                                    "category": "cutover_check"})
        if isinstance(body, dict) and isinstance(body.get("id"), str):
            record_id = body["id"]
        record("remember_roundtrip", status == 200,
               {"http_status": status, "record_id": record_id})

        status, body = api_request(args.origin, "POST", "/v1/memories/recall", token,
                                   {"query": "Cutover post-switch plugin-path check",
                                    "limit": 5})
        record("recall_roundtrip", status == 200,
               {"http_status": status})

        status, body = api_request(args.origin, "POST", "/v1/memories/summarize", token,
                                   {"record_ids": [record_id or "cutover-check"]})
        record("analysis_withheld_422",
               status == 422 and body.get("detail") == ANALYSIS_NOT_CONFIGURED,
               {"http_status": status, "detail": body.get("detail")})

        status, body = api_request(args.origin, "GET",
                                   "/v1/memories/summarization/status", token)
        record("analysis_status_configured_false",
               status == 200 and body.get("configured") is False,
               {"http_status": status, "configured": body.get("configured"),
                "used_today": body.get("used_today")})
    except (OSError, ValueError) as exc:
        print(json.dumps({"probe": "verify", "overall": "error",
                          "error_kind": type(exc).__name__}, ensure_ascii=True))
        return 2

    overall = "pass" if all(item["ok"] for item in checks) else "fail"
    print(json.dumps({"probe": "verify", "checked_utc":
                      dt.datetime.now(dt.timezone.utc).isoformat(),
                      "overall": overall, "checks": checks}, ensure_ascii=True))
    return 0 if overall == "pass" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Enhanced Cognee cutover probe.").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    usage = sub.add_parser("usage", help="read today's model usage per scope")
    usage.add_argument("--api-credential", default="/etc/enhanced-cognee/api.json")
    usage.add_argument("--origin", default="http://127.0.0.1:28080")
    usage.add_argument("--scope", action="append", required=True,
                       metavar="TENANT/PROJECT")
    usage.add_argument("--ttl", type=int, default=600)
    usage.set_defaults(func=cmd_usage)

    verify = sub.add_parser("verify", help="post-switch read-only verification")
    verify.add_argument("--api-credential", default="/etc/enhanced-cognee/api.json")
    verify.add_argument("--origin", default="http://127.0.0.1:28080")
    verify.add_argument("--scope", required=True, metavar="TENANT/PROJECT")
    verify.add_argument("--ttl", type=int, default=600)
    verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({"probe": args.command, "overall": "error",
                          "error_kind": type(exc).__name__,
                          "message": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
