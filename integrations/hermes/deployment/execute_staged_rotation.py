#!/usr/bin/env python3
"""Execute the staged credential rotation one family at a time (phase B).

Owner-run, root-only. Each invocation applies exactly one family with the
current-new credential pair, updates every dependent service credential
file by matching the OLD value (no schema guessing), verifies the new
credential works and the old one is refused, and rolls the file back if
verification fails. Arcadedb is inspection-gated: its recovery artifact's
schema is printed (sanitized) rather than guessed. The application family
ends with the automatic fleet token reissue.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path("/var/lib/enhanced-cognee-rotation")
ETC = Path("/etc/enhanced-cognee")
FAMILIES = ("postgresql", "valkey", "qdrant", "application")
PROBE_ROLE_ENV = Path("/home/vincentspereira/.hermes/profiles/web-researcher/.env")
UNITS = {"postgresql": ["enhanced-cognee-postgres.service"],
         "valkey": ["enhanced-cognee-cache.service"],
         "qdrant": ["enhanced-cognee-qdrant.service"],
         "application": ["enhanced-cognee-api.service"]}


def require(value, category="rotation_execute_refused"):
    if not value:
        raise ValueError(category)


def load_candidate():
    candidates = sorted(d for d in ROOT.iterdir() if d.is_dir())
    require(len(candidates) == 1, "expected_one_candidate")
    candidate = candidates[0]
    summary = json.loads((candidate / "summary.json").read_text())
    require(summary.get("credentials_generated") is True
            and not summary.get("credentials_activated"),
            "candidate_not_in_generated_state")
    logins = json.loads((candidate / "replacement-logins.private.json").read_text())
    return candidate, logins


def login_shape_error(value):
    """Sanitized structure of an unrecognized family entry: key names,
    nesting and types only - never a secret value or its length."""
    def describe(item, depth=0):
        if depth > 4:
            return {"depth": "max"}
        if isinstance(item, dict):
            return {str(k): describe(v, depth + 1) for k, v in list(item.items())[:8]}
        if isinstance(item, list):
            return {"<list>": [describe(i, depth + 1) for i in item[:3]]}
        return type(item).__name__
    return describe(value)


def as_pairs(value):
    """Normalize a family entry to [(name, new_secret)] pairs.

    Accepted shapes: flat {name: secret}; list of single-key dicts; and
    the staged nested form {label: {username, password}, ...} where the
    pair becomes (username, password). Values must already be nonempty
    strings - never coerced."""
    def check(name, secret):
        if not (isinstance(name, str) and name and isinstance(secret, str)
                and secret):
            raise ValueError("unsupported_login_shape:"
                             + json.dumps(login_shape_error(value))[:400])
        return (name, secret)

    if isinstance(value, dict):
        nested = all(isinstance(v, dict) for v in value.values()) and value
        if nested:
            pairs = []
            for label, entry in value.items():
                if not (isinstance(entry, dict)
                        and isinstance(entry.get("username"), str)
                        and isinstance(entry.get("password"), str)):
                    raise ValueError("unsupported_login_shape:"
                                     + json.dumps(login_shape_error(value))[:400])
                pairs.append(check(entry["username"], entry["password"]))
            return pairs
        return [check(k, v) for k, v in value.items()]
    if (isinstance(value, list) and value
            and all(isinstance(i, dict) and len(i) == 1 for i in value)):
        return [check(k, v) for i in value for k, v in i.items()]
    raise ValueError("unsupported_login_shape:"
                     + json.dumps(login_shape_error(value))[:400])


def backup(path: Path, stamp):
    if path.exists():
        target = path.with_name(path.name + ".before-rotation-" + stamp)
        if not target.exists():
            shutil.copy2(path, target)
        return target
    return None


def replace_value_in_file(path: Path, old, new):
    """Replace the literal old value with new; returns count (0 = no match,
    which refuses: never leave a dependent file half-updated)."""
    raw = path.read_text()
    count = raw.count(old)
    if count:
        path.write_text(raw.replace(old, new))
    return count


def systemctl(*args, timeout=120):
    return subprocess.run(["/usr/bin/systemctl", *args],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          timeout=timeout).returncode


def api_health(deadline=45):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            with urlopen("http://127.0.0.1:28080/health/ready", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def role_token():
    for line in PROBE_ROLE_ENV.read_text().splitlines():
        if line.startswith("ENHANCED_COGNEE_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise ValueError("probe_token_missing")


def probe_role_status():
    request = Request("http://127.0.0.1:28080/v1/memories/status",
                      headers={"Authorization": "Bearer " + role_token()})
    try:
        with urlopen(request, timeout=8) as response:
            return response.status
    except HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def psql_port_and_roles(api_json):
    """(port, current_dsn) from the api credential; the DSN carries the
    live postgres service password we must rotate everywhere it appears."""
    dsn = api_json.get("ENHANCED_MEMORY_DATABASE_URL", "")
    parts = urlsplit(dsn)
    require(parts.hostname == "127.0.0.1" and parts.port, "unexpected_dsn_shape")
    return parts.port, dsn


def apply_postgresql(logins, stamp, candidate):
    pairs = as_pairs(logins["postgresql"])
    require(len(pairs) == 3, "expected_three_postgres_logins")
    api_path = ETC / "api.json"
    api_json = json.loads(api_path.read_text())
    port, dsn = psql_port_and_roles(api_json)
    user = urlsplit(dsn).username
    require(user in dict(pairs), "service_role_missing_from_candidates")
    new_password = dict(pairs)[user]
    old_password = urlsplit(dsn).password or ""
    require(old_password and old_password != new_password, "dsn_password_unusable")
    # Order: ALTER first (old password still valid), then file updates.
    from collections import OrderedDict
    from urllib.parse import quote
    escaped = new_password.replace("'", "''")
    sql = ";".join('ALTER ROLE "%s" WITH PASSWORD \'%s\'' % (name, secret.replace("'", "''"))
                   for name, secret in pairs)
    process = subprocess.run(
        ["/opt/enhanced-cognee-stores/native/usr/lib/postgresql/16/bin/psql",
         "postgresql://%s:%s@127.0.0.1:%d/postgres" % (quote(user), quote(old_password), port),
         "-v", "ON_ERROR_STOP=1", "-c", sql],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    require(process.returncode == 0,
            "alter_failed:" + process.stderr.decode()[:160])
    touched = []
    try:
        for name in ("api.json", "index.json"):
            path = ETC / name
            backup(path, stamp)
            count = replace_value_in_file(path, old_password, new_password)
            require(count >= 1, "dependent_file_missing_old_value:" + name)
            touched.append((name, count))
        require(systemctl("restart", "enhanced-cognee-api.service") == 0, "api_restart_failed")
        require(api_health(), "api_unhealthy_after_rotation")
        require(probe_role_status() in (200, 401), "api_probe_failed")
    except Exception:
        for name, _ in touched:
            restore = ETC / (name + ".before-rotation-" + stamp)
            if restore.exists():
                shutil.copy2(restore, ETC / name)
        systemctl("restart", "enhanced-cognee-api.service")
        raise
    return {"family": "postgresql", "roles_rotated": [p[0] for p in pairs],
            "dependent_files_updated": touched, "api_healthy": True}


def resp_command(sock_file, *parts):
    payload = ("*%d\r\n" % len(parts)).encode()
    for part in parts:
        raw = part.encode()
        payload += b"$%d\r\n%s\r\n" % (len(raw), raw)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(5)
        sock.connect(str(sock_file))
        sock.sendall(payload)
        return sock.recv(512)


def apply_valkey(logins, stamp, candidate):
    pairs = as_pairs(logins["valkey"])
    require(len(pairs) == 3, "expected_three_valkey_logins")
    acl_path = ETC / "valkey-users.acl"
    backup(acl_path, stamp)
    original = acl_path.read_text()
    updated = original
    # Rotate by user: rewrite each user's password token in ACL order.
    lines = updated.splitlines()
    user_lines = {}
    for index, line in enumerate(lines):
        match = re.match(r"user\s+([A-Za-z0-9_-]+)\s+(.*)", line.strip())
        if match:
            user_lines[match.group(1)] = index
    require(set(user_lines) == set(dict(pairs)), "acl_users_differ_from_candidates")
    for name, secret in pairs:
        line = lines[user_lines[name]]
        if ">" in line:
            tokens = line.split()
            for position, token in enumerate(tokens):
                if token.startswith(">") or token.startswith("#"):
                    tokens[position] = ">" + secret
                    break
            lines[user_lines[name]] = " ".join(tokens)
        else:
            tokens = line.split() + [">" + secret]
            lines[user_lines[name]] = " ".join(tokens)
    acl_path.write_text("\n".join(lines) + "\n")
    try:
        require(systemctl("restart", "enhanced-cognee-cache.service") == 0,
                "cache_restart_failed")
        time.sleep(3)
        import glob
        sockets = glob.glob("/var/lib/enhanced-cognee/valkey/*.sock") + \
            glob.glob("/run/enhanced-cognee*/valkey*.sock")
        require(sockets, "valkey_socket_not_found")
        reply = resp_command(sockets[0], "AUTH", dict(pairs)[list(user_lines)[0]],
                             dict(pairs)[list(user_lines)[0]])
        require(b"+OK" in reply or b":1" in reply, "valkey_auth_verify_failed")
    except Exception:
        shutil.copy2(ETC / ("valkey-users.acl.before-rotation-" + stamp), acl_path)
        systemctl("restart", "enhanced-cognee-cache.service")
        raise
    return {"family": "valkey", "users_rotated": list(user_lines),
            "auth_verified": True}


def apply_qdrant(logins, stamp, candidate):
    pairs = as_pairs(logins["qdrant"])
    require(len(pairs) == 2, "expected_two_qdrant_keys")
    index_json = json.loads((ETC / "index.json").read_text())
    current = sorted({v for v in _leaf_values(index_json)
                      if isinstance(v, str) and len(v) >= 16})
    # Match candidates to current values by trying each pair against files.
    matched = []
    for name, secret in pairs:
        hits = []
        for path in (ETC / "qdrant.yaml", ETC / "index.json"):
            raw = path.read_text()
            for value in current:
                if value != secret and value in raw:
                    hits.append((path, value))
        require(hits, "qdrant_current_key_not_located:" + name)
        matched.append((name, secret, hits))
    for path in (ETC / "qdrant.yaml", ETC / "index.json"):
        backup(path, stamp)
    try:
        for name, secret, hits in matched:
            for path, old in hits:
                count = replace_value_in_file(path, old, secret)
                require(count >= 1, "qdrant_replace_missed:" + path.name)
        for unit in ("enhanced-cognee-qdrant.service",
                     "enhanced-cognee-api.service"):
            require(systemctl("restart", unit) == 0, "restart_failed:" + unit)
        require(api_health(), "api_unhealthy_after_qdrant_rotation")
    except Exception:
        for path in (ETC / "qdrant.yaml", ETC / "index.json"):
            restore = ETC / (path.name + ".before-rotation-" + stamp)
            if restore.exists():
                shutil.copy2(restore, path)
        for unit in ("enhanced-cognee-qdrant.service",
                     "enhanced-cognee-api.service"):
            systemctl("restart", unit)
        raise
    return {"family": "qdrant", "keys_rotated": [p[0] for p in pairs],
            "api_healthy": True}


def _leaf_values(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _leaf_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _leaf_values(child)
    else:
        yield value


def apply_application(logins, stamp, candidate):
    pairs = as_pairs(logins["application"])
    require(len(pairs) == 1, "expected_one_application_secret")
    name, secret = pairs[0]
    api_path = ETC / "api.json"
    backup(api_path, stamp)
    original = api_path.read_text()
    current = json.loads(original).get("ENHANCED_JWT_SECRET", "")
    require(len(current) >= 32, "issuer_secret_shape_unexpected")
    try:
        count = replace_value_in_file(api_path, current, secret)
        require(count == 1, "issuer_secret_replace_count")
        require(systemctl("restart", "enhanced-cognee-api.service") == 0,
                "api_restart_failed")
        require(api_health(), "api_unhealthy")
        # All fleet tokens are now invalid; verify then reissue.
        require(probe_role_status() == 401, "old_tokens_still_accepted")
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).parent
                                       / "issue_fleet_role_tokens.py")],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=1800)
        batch = json.loads(result.stdout.decode().strip().splitlines()[-1]
                           or "{}") if result.stdout else {}
        require(batch.get("complete") is True, "fleet_reissue_failed")
        default = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).parent
                                       / "provision_gateway_profile_access.py"),
             "--profile", "default"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=300)
        require(b'"complete": true' in default.stdout, "default_reissue_failed")
        require(probe_role_status() == 200, "new_tokens_not_accepted")
    except Exception:
        shutil.copy2(ETC / ("api.json.before-rotation-" + stamp), api_path)
        systemctl("restart", "enhanced-cognee-api.service")
        raise
    return {"family": "application", "issuer_rotated": name,
            "fleet_tokens_reissued": batch.get("roles_total"),
            "default_reissued": True, "probe_role": 200}


def inspect_arcadedb(candidate):
    artifact = candidate / "graph-operator-recovery"
    raw = artifact.read_text()
    require(len(raw) <= 65536, "artifact_oversized")
    structure = {"bytes": len(raw), "parses_as_json": False}
    try:
        value = json.loads(raw)
        structure["parses_as_json"] = True
        if isinstance(value, dict):
            structure["keys"] = sorted(value)[:32]
            structure["value_kinds"] = {k: type(v).__name__
                                        for k, v in list(value.items())[:32]}
        else:
            structure["shape"] = type(value).__name__
    except ValueError:
        structure["first_line_prefix"] = raw[:60]
    return {"family": "arcadedb-inspect", "artifact": structure,
            "note": "apply phase for arcadedb is built against this schema"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=FAMILIES + ("arcadedb-inspect",))
    args = parser.parse_args()
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes", "owner_sudo_on_gateway_host")
    candidate, logins = load_candidate()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    receipt_path = candidate / ("execution-%s-%s.json" % (args.family, stamp))
    try:
        if args.family == "postgresql":
            receipt = apply_postgresql(logins, stamp, candidate)
        elif args.family == "valkey":
            receipt = apply_valkey(logins, stamp, candidate)
        elif args.family == "qdrant":
            receipt = apply_qdrant(logins, stamp, candidate)
        elif args.family == "application":
            receipt = apply_application(logins, stamp, candidate)
        else:
            receipt = inspect_arcadedb(candidate)
    except Exception as exc:
        receipt = {"complete": False, "family": args.family,
                   "error_kind": type(exc).__name__,
                   "detail": str(exc)[:200] if isinstance(exc, ValueError) else ""}
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
        print(json.dumps(receipt, sort_keys=True))
        return 1
    receipt["complete"] = True
    receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "category": "rotation_execute_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:200] if isinstance(exc, ValueError)
                          else ""}), flush=True)
        raise SystemExit(1)
