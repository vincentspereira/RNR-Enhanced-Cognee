"""Rotate existing PostgreSQL operator/backup passwords with protected rollback.

Existing administrator names/ownership remain stable. No service restart,
profile access, canonical edit, encryption/recovery/signing key change.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.parse import quote,unquote,urlsplit,urlunsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
FIELD = "ENHANCED_MEMORY_DATABASE_URL"


def binding(url):
    uri = urlsplit(url)
    username,password = unquote(uri.username or ""),unquote(uri.password or "")
    if (uri.scheme not in {"postgres","postgresql"} or uri.hostname not in {"127.0.0.1","localhost"}
            or uri.port != 28434 or not username or len(username) > 63 or not password or not uri.path
            or any(c in username+password for c in "\x00\r\n")):
        raise ValueError("fixed_protected_postgres_binding_required")
    return uri,username,password


def prepare(operator,backup,operator_password):
    if not isinstance(operator_password,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}",operator_password):
        raise ValueError("generated_operator_password_required")
    parsed = {name:binding(value[FIELD]) for name,value in (("operator",operator),("backup",backup))}
    if parsed["operator"][0].path != parsed["backup"][0].path:
        raise ValueError("same_database_binding_required")
    old = {}
    for _,name,password in parsed.values():
        if name in old and old[name] != password:
            raise ValueError("operator_backup_password_binding_differs")
        old[name] = password
    operator_name = parsed["operator"][1]
    replacements = {name:operator_password if name == operator_name else secrets.token_urlsafe(32) for name in old}
    configs = {}
    for name,original in (("operator",operator),("backup",backup)):
        uri,username,_ = parsed[name]
        host = uri.netloc.rsplit("@",1)[-1]
        url = urlunsplit((uri.scheme,quote(username,safe="")+":"+quote(replacements[username],safe="")+"@"+host,uri.path,uri.query,""))
        configs[name] = dict(original,**{FIELD:url})
    return old,replacements,configs


async def passwords(conn,values):
    async with conn.transaction():
        for name,password in values.items():
            # Native PostgreSQL quoting handles even legacy password punctuation.
            identifier = await conn.fetchval("SELECT quote_ident($1::text)",name)
            literal = await conn.fetchval("SELECT quote_literal($1::text)",password)
            await conn.execute("ALTER ROLE "+identifier+" PASSWORD "+literal)


async def verify(configs):
    import asyncpg
    for value in configs.values():
        conn = await asyncpg.connect(value[FIELD],timeout=10,command_timeout=10)
        try:
            if await conn.fetchval("SELECT max(version) FROM shared_memory.memory_service_schema") != 3:
                raise ValueError("schema_access_not_verified")
        finally:
            await conn.close()


async def old_logins_denied(original):
    import asyncpg
    seen = set()
    for raw in original.values():
        url = json.loads(raw)[FIELD]
        _,username,_ = binding(url)
        if username in seen:
            continue
        seen.add(username)
        try:
            conn = await asyncpg.connect(url,timeout=10,command_timeout=10)
        except Exception as error:
            if getattr(error,"sqlstate",None) in {"28P01","28000"}:
                continue
            raise
        else:
            await conn.close()
            raise ValueError("old_operator_or_backup_password_still_accepted")


async def rotate(shared,original,configs,old,replacements,attempt,result):
    import asyncpg
    read,write,replace = (shared[k] for k in ("read_file","private_write","replace_file"))
    conn = await asyncpg.connect(json.loads(original["operator"])[FIELD],timeout=10,command_timeout=20)
    touched = False
    try:
        actual = await conn.fetchval("SELECT current_user")
        if actual != binding(json.loads(original["operator"])[FIELD])[1]:
            raise ValueError("operator_identity_binding_differs")
        write(attempt / "before-alter.json",b'{"password_rotation_started":true}')
        touched = True
        await passwords(conn,replacements)
        result["checkpoint"] = "new_authentication"
        await verify(configs)
        await old_logins_denied(original)
        for name in original:
            path = Path("/etc/enhanced-cognee") / (name+".json")
            if read(path,0) != original[name]:
                raise ValueError("protected_configuration_changed_concurrently")
        result["checkpoint"] = "configuration_publication"
        for name,value in configs.items():
            replace(Path("/etc/enhanced-cognee") / (name+".json"),json.dumps(value).encode(),0)
        await verify(configs)
        result.update(complete=True,checkpoint="complete",postgres_operator_password_changed=True,
            backup_database_password_changed=True,rotated_role_count=len(replacements),
            new_operator_and_backup_authenticated=True,old_operator_backup_passwords_denied=True,
            old_passwords_retained_for_rollback=True)
    except BaseException as error:
        result["category"] = "postgres_operator_rotation_incomplete_preserve_evidence"
        allowed = {"operator_identity_binding_differs","schema_access_not_verified",
                   "old_operator_or_backup_password_still_accepted","protected_configuration_changed_concurrently"}
        result["reason"] = str(error) if type(error) is ValueError and str(error) in allowed else "database_or_protected_file_error"
        state = getattr(error,"sqlstate",None)
        if isinstance(state,str) and re.fullmatch(r"[A-Z0-9]{5}",state):
            result["postgres_sqlstate"] = state
        if touched:
            try:
                await passwords(conn,old)
                conflict = False
                for name,raw in original.items():
                    path = Path("/etc/enhanced-cognee") / (name+".json")
                    current = read(path,0)
                    if current == json.dumps(configs[name]).encode():
                        replace(path,raw,0)
                    elif current != raw:
                        conflict = True
                await verify({name:json.loads(raw) for name,raw in original.items()})
                result["rollback_operator_and_backup_authenticated"] = not conflict
            except BaseException:
                result["rollback_operator_and_backup_authenticated"] = False
    finally:
        await conn.close()


def main():
    if os.geteuid() != 0 or Path(sys.prefix) != BASE / "runtime":
        raise ValueError("protected_operator_python_required")
    os.umask(0o077)
    raw = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHARED_SHA256:
        raise ValueError("reviewed_support_required")
    shared = {"__name__":"verified_operator_rotation_files"}
    exec(compile(raw,"<verified-operator-rotation-files>","exec"),shared)
    read,write = shared["read_file"],shared["private_write"]
    derived = json.loads(read(STAGE / "derived-service-rotation-valid-probe/summary.json",0))
    if derived.get("complete") is not True:
        raise ValueError("derived_service_rotation_required")
    candidate = json.loads(read(STAGE / "replacement-logins.private.json",0))
    original = {name:read(Path("/etc/enhanced-cognee") / (name+".json"),0) for name in ("operator","backup")}
    old,replacements,configs = prepare(json.loads(original["operator"]),json.loads(original["backup"]),
                                       candidate["postgresql"]["operator"]["password"])
    attempt = STAGE / "postgres-operator-backup-rotation"
    attempt.mkdir(mode=0o700)
    for name,raw in original.items():
        write(attempt / (name+".before.json"),raw)
    write(attempt / "replacement-configs.private.json",json.dumps(configs).encode())
    result = {"complete":False,"evidence":str(attempt),"checkpoint":"operator_connection",
        "operator_helper_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "profiles_changed":False,"services_restarted":False,"encryption_keys_changed":False,
        "recovery_keys_changed":False,"application_signing_key_changed":False,
        "all_credentials_rotated":False,"fleet_launch_approved":False}
    asyncio.run(rotate(shared,original,configs,old,replacements,attempt,result))
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"operator_password_rotation_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
