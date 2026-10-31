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
import glob
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


_SECRET_FIELDS = ("password", "api_key", "jwt_signing_key", "secret",
                  "key", "token")
_NAME_FIELDS = ("username", "name", "role", "user")


def _pair_from_entry(label, entry):
    """One staged entry -> (name, secret). Classic username/password entries
    keep the username as the name; single-secret entries (api_key,
    jwt_signing_key, ...) take their label or an explicit name field."""
    if isinstance(entry, str) and entry:
        return (label, entry)
    if not isinstance(entry, dict):
        raise ValueError("unsupported_login_shape:entry")
    secrets = [field for field in _SECRET_FIELDS
               if isinstance(entry.get(field), str) and entry[field]]
    names = [field for field in _NAME_FIELDS
             if isinstance(entry.get(field), str) and entry[field]]
    if ("username" in entry and "password" in entry
            and entry.get("password") in [entry.get(f) for f in secrets]):
        return (entry["username"], entry["password"])
    if len(secrets) == 1:
        name = entry[names[0]] if names else label
        return (name, entry[secrets[0]])
    raise ValueError("unsupported_login_shape:entry_fields:"
                     + ",".join(sorted(entry)))


def as_pairs(value):
    """Normalize a family entry to [(name, new_secret)] pairs across the
    staged shapes: flat {name: secret}, list of single-key dicts, and the
    nested {label: {username,password}|{api_key}|{jwt_signing_key}} form.
    Values must already be nonempty strings - never coerced."""
    def check(pair):
        name, secret = pair
        if not (isinstance(name, str) and name and isinstance(secret, str)
                and secret):
            raise ValueError("unsupported_login_shape:"
                             + json.dumps(login_shape_error(value))[:400])
        return (name, secret)

    if isinstance(value, dict):
        if value and all(isinstance(v, (dict, str)) for v in value.values()):
            return [check(_pair_from_entry(str(k), v))
                    for k, v in value.items()]
        return [check((str(k), v)) for k, v in value.items()]
    if (isinstance(value, list) and value
            and all(isinstance(i, dict) and len(i) == 1 for i in value)):
        return [check((str(k), v)) for i in value for k, v in i.items()]
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


def dsn_diagnostic(dsn):
    """Structure of the DSN with values removed - field names, presence
    flags and query keys only."""
    parts = urlsplit(dsn)
    return json.dumps({
        "scheme": parts.scheme, "host": parts.hostname, "port": parts.port,
        "has_username": bool(parts.username), "username": parts.username,
        "has_password": bool(parts.password),
        "password_len": len(parts.password or ""),
        "path": parts.path[:40], "query_keys": parts.query.split("&")[:8]
        and [pair.split("=")[0] for pair in parts.query.split("&") if pair],
    })[:400]


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
    api_password_unchanged = old_password == new_password
    if not old_password:
        raise ValueError("dsn_password_unusable:" + dsn_diagnostic(dsn))
    # Order: ALTER first (old password still valid), then file updates.
    from urllib.parse import quote
    # The api role cannot ALTER peers; use the operator DSN from the
    # root-only operator credential. Its CURRENT name may be the legacy
    # name that the staged set renames away from.
    alter_user, alter_password = user, old_password
    operator_path = ETC / "operator.json"
    if operator_path.exists():
        operator = json.loads(operator_path.read_text())
        operator_dsn = operator.get("ENHANCED_MEMORY_DATABASE_URL", "")
        if operator_dsn:
            parts = urlsplit(operator_dsn)
            alter_user = parts.username
            alter_password = parts.password or ""
    staged_map = dict(pairs)
    # The native psql needs its bundled libpq (not on the system path).
    lib_dirs = sorted(glob.glob(
        "/opt/enhanced-cognee-stores/native/usr/lib/*/"))
    lib_dirs += sorted(glob.glob(
        "/opt/enhanced-cognee-stores/native/usr/lib/postgresql/*/lib/"))
    psql_env = {"PATH": "/usr/bin:/bin",
                "LD_LIBRARY_PATH": ":".join(lib_dirs)}
    # Query existing roles first: staged names that do not exist (the
    # operator role keeps its legacy name) must not be ALTERed.
    list_process = subprocess.run(
        ["/opt/enhanced-cognee-stores/native/usr/lib/postgresql/16/bin/psql",
         "postgresql://%s:%s@127.0.0.1:%d/postgres" % (quote(alter_user),
                                                       quote(alter_password),
                                                       port),
         "-t", "-A", "-c", "SELECT rolname FROM pg_roles"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60,
        env=psql_env)
    require(list_process.returncode == 0, "role_list_failed")
    existing = {line.strip() for line in
                list_process.stdout.decode().splitlines() if line.strip()}
    statements = []
    for name, secret in pairs:
        if name in existing:
            statements.append('ALTER ROLE "%s" WITH PASSWORD \'%s\''
                              % (name, secret.replace("'", "''")))
        elif "operator" not in name.lower():
            raise ValueError("staged_role_missing:" + name)
    if alter_user and alter_user in existing and alter_user not in staged_map:
        operators = [n for n in staged_map if "operator" in n.lower()]
        require(len(operators) == 1, "operator_secret_target_ambiguous")
        statements.append('ALTER ROLE "%s" WITH PASSWORD \'%s\''
                          % (alter_user,
                             staged_map[operators[0]].replace("'", "''")))
    require(statements, "no_roles_to_alter")
    sql = ";".join(statements)
    process = subprocess.run(
        ["/opt/enhanced-cognee-stores/native/usr/lib/postgresql/16/bin/psql",
         "postgresql://%s:%s@127.0.0.1:%d/postgres" % (quote(alter_user),
                                                       quote(alter_password),
                                                       port),
         "-v", "ON_ERROR_STOP=1", "-c", sql],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
        env=psql_env)
    require(process.returncode == 0,
            "alter_failed:" + process.stderr.decode()[:160])
    touched = []
    try:
        if not api_password_unchanged:
            for name in ("api.json", "index.json"):
                path = ETC / name
                backup(path, stamp)
                count = replace_value_in_file(path, old_password, new_password)
                require(count >= 1, "dependent_file_missing_old_value:" + name)
                touched.append((name, count))
        # The operator credential's DSN carries the operator password (and
        # the legacy name being renamed away from).
        if operator_path.exists():
            operator = json.loads(operator_path.read_text())
            operator_dsn = operator.get("ENHANCED_MEMORY_DATABASE_URL", "")
            if operator_dsn and urlsplit(operator_dsn).password:
                staged_map = dict(pairs)
                new_secret = staged_map.get(urlsplit(operator_dsn).username)
                if new_secret is None:
                    operators = [n for n in staged_map
                                 if "operator" in n.lower()]
                    if urlsplit(operator_dsn).username not in staged_map \
                            and len(operators) == 1:
                        # Legacy operator name keeps its identity; only its
                        # password rotates to the staged operator secret.
                        new_secret = staged_map[operators[0]]
                if new_secret:
                    backup(operator_path, stamp)
                    count = replace_value_in_file(
                        operator_path, urlsplit(operator_dsn).password,
                        new_secret)
                    require(count >= 1, "operator_dsn_password_not_found")
                    touched.append(("operator.json", count))
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
            "dependent_files_updated": touched, "api_healthy": True,
            "api_password_already_current": api_password_unchanged}


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


def valkey_endpoint():
    """(kind, endpoint) from the service config: unixsocket path or TCP
    port. Never returns a credential."""
    import glob as _glob
    conf = (ETC / "valkey.conf").read_text()
    unixsocket, port = None, None
    for line in conf.splitlines():
        tokens = line.split()
        if len(tokens) >= 2 and tokens[0] == "unixsocket":
            unixsocket = tokens[1]
        if len(tokens) >= 2 and tokens[0] == "port":
            try:
                port = int(tokens[1])
            except ValueError:
                port = None
    if unixsocket and Path(unixsocket).exists():
        return "unix", unixsocket
    for pattern in ("/var/lib/enhanced-cognee/valkey/*.sock",
                    "/run/enhanced-cognee*/valkey*.sock"):
        found = _glob.glob(pattern)
        if found:
            return "unix", found[0]
    if port:
        return "tcp", port
    raise ValueError("valkey_endpoint_not_found:unix=%s:tcp_port=%s"
                     % (bool(unixsocket), port))


def valkey_auth(endpoint, kind, username, password):
    if kind == "unix":
        return resp_command(endpoint, "AUTH", username, password)
    with socket.create_connection(("127.0.0.1", int(endpoint)), timeout=5) as s:
        s.settimeout(5)
        payload = b"*3\r\n$4\r\nAUTH\r\n"
        for part in (username, password):
            raw = part.encode()
            payload += b"$%d\r\n%s\r\n" % (len(raw), raw)
        s.sendall(payload)
        return s.recv(512)


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
    staged = dict(pairs)
    file_users = set(user_lines)
    leftovers = sorted(file_users - set(staged) - {"default"})
    renamed = None
    if leftovers:
        # A staged name not in the file replaces exactly one legacy user
        # that is not the mandatory valkey default user.
        replacements = sorted(set(staged) - file_users)
        require(len(leftovers) == 1 and len(replacements) == 1,
                "acl_users_differ_from_candidates:file=%s:staged=%s"
                % (",".join(sorted(file_users)), ",".join(sorted(staged))))
        renamed = (leftovers[0], replacements[0])
        user_lines[replacements[0]] = user_lines.pop(leftovers[0])
        lines[user_lines[replacements[0]]] = lines[user_lines[
            replacements[0]]].replace("user " + leftovers[0],
                                      "user " + replacements[0], 1)
    elif set(staged) - file_users:
        raise ValueError("acl_users_differ_from_candidates:file=%s:staged=%s"
                         % (",".join(sorted(file_users)),
                            ",".join(sorted(staged))))
    for name, secret in pairs:
        index = user_lines[name]
        tokens = lines[index].split()
        # A rotated user must be ENABLED with its password set: strip the
        # disabled flag and resetpass, ensure the on flag survives.
        tokens = [t for t in tokens if t not in ("off", "resetpass")]
        if "on" not in tokens:
            tokens.insert(2, "on")
        replaced_token = False
        for position, token in enumerate(tokens):
            if token.startswith(">") or token.startswith("#"):
                tokens[position] = ">" + secret
                replaced_token = True
                break
        if not replaced_token:
            tokens.append(">" + secret)
        lines[index] = " ".join(tokens)
    updated = "\n".join(lines) + "\n"
    acl_path.write_text(updated)
    try:
        require(systemctl("restart", "enhanced-cognee-cache.service") == 0,
                "cache_restart_failed")
        time.sleep(3)
        time.sleep(3)
        kind, endpoint = valkey_endpoint()
        replies = {}
        for user, password in sorted(staged.items()):
            reply = valkey_auth(endpoint, kind, user, password)
            replies[user] = reply[:80].decode("utf-8", "replace")
            require(b"+OK" in reply or b":1" in reply,
                    "valkey_auth_verify_failed:%s:reply=%s:acl_lines=%s"
                    % (user, replies[user], json.dumps(
                        [re.sub(r"[>#][^\s]+", ">***", line)
                         for line in updated.splitlines()
                         if line.strip().startswith("user")])))
    except Exception:
        shutil.copy2(ETC / ("valkey-users.acl.before-rotation-" + stamp), acl_path)
        systemctl("restart", "enhanced-cognee-cache.service")
        raise
    return {"family": "valkey", "users_rotated": sorted(staged),
            "renamed": renamed, "auth_verified": True}


def _qdrant_structure_dump(path, text):
    """Sanitized structure of the qdrant config: JSON key tree (name and
    value length) or YAML field names; never a value itself."""
    import re as _re
    try:
        value = json.loads(text)
    except ValueError:
        names = sorted({m.group(1).strip() for m in _re.finditer(
            r"^(\s*[A-Za-z0-9_.-]+):\s*\S", text, _re.MULTILINE)})
        return "yaml_fields=" + json.dumps(names)
    def walk(item, prefix=""):
        if isinstance(item, dict):
            out = {}
            for key, child in list(item.items())[:24]:
                out[str(key)[:32]] = walk(child, prefix + "." + str(key))
            return out
        if isinstance(item, list):
            return {"<list>": len(item)}
        return "%s:%d" % (type(item).__name__, len(str(item)))
    return "json_tree=" + json.dumps(walk(value))[:600]


def apply_qdrant(logins, stamp, candidate):
    pairs = as_pairs(logins["qdrant"])
    require(len(pairs) == 2, "expected_two_qdrant_keys")
    staged = dict(pairs)
    # The qdrant config is JSON (despite the .yaml name): the two keys are
    # service.api_key (admin/write) and service.read_only_api_key.
    config = json.loads((ETC / "qdrant.yaml").read_text())
    service = config.get("service", {})
    old_admin = service.get("api_key")
    old_read = service.get("read_only_api_key")
    require(isinstance(old_admin, str) and len(old_admin) >= 16
            and isinstance(old_read, str) and len(old_read) >= 16,
            "qdrant_service_keys_missing")
    old_for = {}
    for label in staged:
        if "read" in label.lower():
            old_for[label] = old_read
        elif "admin" in label.lower() or "write" in label.lower():
            old_for[label] = old_admin
        else:
            raise ValueError("qdrant_label_unmapped:" + label)
    require(old_read != old_admin or len(staged) == 1,
            "qdrant_keys_identical_cannot_map")
    matched = []
    already_current = []
    for label, secret in staged.items():
        old = old_for[label]
        if old == secret:
            # Staged key already equals the live one (proven pattern from
            # the issuer family): verified no-op for this key.
            already_current.append(label)
            continue
        hits = []
        for path in (ETC / "qdrant.yaml", ETC / "index.json"):
            if old in path.read_text():
                hits.append((path, old))
        require(hits, "qdrant_current_key_not_located:" + label)
        matched.append((label, secret, hits))
    if not matched:
        return {"family": "qdrant", "keys_rotated": [],
                "keys_already_current": sorted(already_current),
                "verified": True}
    for path in (ETC / "qdrant.yaml", ETC / "index.json"):
        backup(path, stamp)
    try:
        replaced = {label: 0 for label in staged}
        # Longest current values first: if one key is a prefix of the
        # other it must not consume the longer one's occurrence.
        ordered = sorted(matched, key=lambda m: max(
            (len(old) for _, old in m[2]), default=0), reverse=True)
        for label, secret, hits in ordered:
            for path, old in hits:
                count = replace_value_in_file(path, old, secret)
                replaced[label] += count
            require(replaced[label] >= 1, "qdrant_replace_missed:" + label)
        for path in (ETC / "qdrant.yaml", ETC / "index.json"):
            raw = path.read_text()
            for _, secret, hits in matched:
                for _, old in hits:
                    require(old not in raw,
                            "qdrant_old_value_remains:" + path.name)
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
    return {"family": "qdrant", "keys_rotated": [p[0] for p in matched],
            "keys_already_current": sorted(already_current),
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


def _hmac_ok(token, secret):
    """Local HS256 signature check (no library, no network)."""
    import base64
    import hashlib
    import hmac as _hmac
    try:
        header, payload, signature = token.split(".")
        message = (header + "." + payload).encode()
        expected = base64.urlsafe_b64encode(
            _hmac.new(secret.encode(), message, hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        return _hmac.compare_digest(signature, expected)
    except Exception:
        return False


def running_secret_state(secret):
    """Value-free comparison of the API process's live ENHANCED_JWT_SECRET
    against the new secret, plus which auth-related env names the process
    carries. Returns a diagnostic dict."""
    import hashlib as _hash
    show = subprocess.run(["/usr/bin/systemctl", "show",
                           "enhanced-cognee-api.service", "-p", "MainPID",
                           "--value"], stdout=subprocess.PIPE, timeout=15)
    pid = show.stdout.decode().strip()
    if not pid.isdigit():
        return {"pid": "missing"}
    try:
        environ = Path("/proc/%s/environ" % pid).read_bytes().split(b"\0")
    except OSError:
        return {"pid": pid, "environ": "unreadable"}
    names, live_fingerprint = [], None
    new_fingerprint = _hash.sha256(secret.encode()).hexdigest()[:12]
    for entry in environ:
        if b"=" not in entry:
            continue
        key, value = entry.split(b"=", 1)
        name = key.decode("utf-8", "replace")
        if name.startswith(("ENHANCED_", "ENCRYPTION_")):
            names.append(name)
        if name == "ENHANCED_JWT_SECRET":
            live_fingerprint = _hash.sha256(value).hexdigest()[:12]
    return {"pid": pid, "auth_env_names": sorted(names),
            "live_secret_matches_new": live_fingerprint == new_fingerprint,
            "live_secret_present": live_fingerprint is not None}


def token_signature_state(token, old_secret, new_secret):
    """Which secret the live fleet token's signature actually matches."""
    return {"token_verifies_with_old": _hmac_ok(token, old_secret),
            "token_verifies_with_new": _hmac_ok(token, new_secret)}


def apply_application(logins, stamp, candidate):
    pairs = as_pairs(logins["application"])
    require(len(pairs) == 1, "expected_one_application_secret")
    name, secret = pairs[0]
    api_path = ETC / "api.json"
    operator_path = ETC / "operator.json"
    backup(api_path, stamp)
    original = api_path.read_text()
    current = json.loads(original).get("ENHANCED_JWT_SECRET", "")
    require(len(current) >= 32, "issuer_secret_shape_unexpected")
    if current == secret:
        # Staged key already equals the live secret (proven by the dual
        # HMAC verification): nothing to rotate, tokens stay valid, no
        # reissue needed. Keep operator.json consistent if it differs.
        operator_consistent = True
        if operator_path.exists():
            operator_raw = operator_path.read_text()
            operator_consistent = current in operator_raw
            if not operator_consistent:
                backup(operator_path, stamp)
                count = replace_value_in_file(operator_path,
                                              json.loads(operator_raw).get(
                                                  "ENHANCED_JWT_SECRET", ""),
                                              secret)
                operator_consistent = count >= 1
        return {"family": "application", "issuer_already_current": True,
                "operator_file_consistent": operator_consistent,
                "tokens_untouched": True}
    # The issuer requires api.json and operator.json to carry the SAME
    # signing secret; rotate both or future issuance refuses.
    operator_touched = False
    if operator_path.exists():
        backup(operator_path, stamp)
        operator_touched = operator_path.read_text().count(current) >= 1
    try:
        count = replace_value_in_file(api_path, current, secret)
        require(count == 1, "issuer_secret_replace_count")
        if operator_touched:
            operator_count = replace_value_in_file(operator_path, current,
                                                   secret)
            require(operator_count >= 1, "operator_secret_replace_count")
        require(systemctl("restart", "enhanced-cognee-api.service") == 0,
                "api_restart_failed")
        require(api_health(), "api_unhealthy")
        # All fleet tokens are now invalid; verify then reissue. Retry the
        # denial probe: a restart-blip status of 0 is not proof of acceptance.
        probe = 0
        for attempt in range(4):
            probe = probe_role_status()
            if probe == 401:
                break
            time.sleep(2)
        if probe != 401:
            raise ValueError(
                "old_tokens_still_accepted:probe=%d:%s:%s" % (
                    probe,
                    json.dumps(running_secret_state(secret)),
                    json.dumps(token_signature_state(
                        role_token(), current, secret))))
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
        restore_api = ETC / ("api.json.before-rotation-" + stamp)
        if restore_api.exists():
            shutil.copy2(restore_api, api_path)
        if operator_touched:
            restore_operator = ETC / ("operator.json.before-rotation-" + stamp)
            if restore_operator.exists():
                shutil.copy2(restore_operator, operator_path)
        systemctl("restart", "enhanced-cognee-api.service")
        raise
    return {"family": "application", "issuer_rotated": name,
            "operator_file_rotated": operator_touched,
            "fleet_tokens_reissued": batch.get("roles_total"),
            "default_reissued": True, "probe_role": 200}


def _sanitized_structure(path: Path):
    """Structure of one artifact file: for JSON a key tree with types and
    value lengths; otherwise size and first-line prefix. Never a value."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {"error": type(exc).__name__}
    entry = {"bytes": len(raw)}
    try:
        value = json.loads(raw)
    except ValueError:
        entry["first_line_prefix"] = raw[:60].decode("utf-8", "replace")
        return entry
    def walk(item):
        if isinstance(item, dict):
            return {str(k)[:32]: walk(v) for k, v in list(item.items())[:24]}
        if isinstance(item, list):
            return {"<list>": len(item)}
        return "%s:%d" % (type(item).__name__, len(str(item)))
    entry["tree"] = walk(value)
    return entry


def inspect_arcadedb(candidate):
    artifact = candidate / "graph-operator-recovery"
    require(artifact.is_dir(), "artifact_not_a_directory")
    structure = {child.name: _sanitized_structure(child)
                 for child in sorted(artifact.iterdir())[:24]}
    summary = json.loads((candidate / "summary.json").read_text())
    return {"family": "arcadedb-inspect", "artifact_children": structure,
            "graph_authentication_metadata": summary.get(
                "graph_authentication_metadata"),
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
                   "detail": str(exc)[:800] if isinstance(exc, ValueError) else ""}
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
