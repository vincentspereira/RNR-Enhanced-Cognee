"""Disable exactly two superseded PostgreSQL service logins; preserve roles/data.

Requires the retained rotation/projection/key receipts. No session termination,
role deletion, grant change, service restart, profile traversal or key rotation.
On failure restore the original login flags, retaining every attempt.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
from urllib.parse import unquote,urlsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
FIELDS = {"api":"ENHANCED_MEMORY_DATABASE_URL","worker":"ENHANCED_INDEX_DATABASE_URL"}


def require(value,reason):
    if not value:raise ValueError(reason)


def binding(url):
    uri = urlsplit(url)
    role = unquote(uri.username or "")
    require(uri.scheme in {"postgres","postgresql"} and uri.hostname in {"127.0.0.1","localhost"}
        and uri.port == 28434 and uri.path and uri.password
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}",role),"fixed_local_database_binding_required")
    return role,uri.path


def plan(old,current,operator,backup):
    protected = {binding(value["ENHANCED_MEMORY_DATABASE_URL"])[0] for value in (operator,backup)}
    new = {kind:binding(current[kind][field]) for kind,field in FIELDS.items()}
    previous = {kind:binding(old[kind][field]) for kind,field in FIELDS.items()}
    require(len({value[0] for value in previous.values()}) == 2,"distinct_old_service_roles_required")
    require(len({value[0] for value in new.values()}) == 2,"distinct_new_service_roles_required")
    require(not ({v[0] for v in previous.values()} & ({v[0] for v in new.values()} | protected)),
            "old_role_still_selected_or_administrative")
    database = binding(operator["ENHANCED_MEMORY_DATABASE_URL"])[1]
    require(all(v[1] == database for v in (*previous.values(),*new.values(),binding(backup["ENHANCED_MEMORY_DATABASE_URL"]))),
            "same_database_required")
    require(all(re.fullmatch("ec_"+kind+r"_[a-f0-9]{12}",new[kind][0]) for kind in FIELDS),
            "rotated_service_identity_required")
    return {kind:value[0] for kind,value in previous.items()}


async def verify_active(connect,current):
    for kind,field in FIELDS.items():
        conn = await connect(current[kind][field],timeout=10,command_timeout=10)
        try:
            require(await conn.fetchval("SELECT current_user") == binding(current[kind][field])[0],"active_identity_differs")
            require(await conn.fetchval("SELECT max(version) FROM shared_memory.memory_service_schema") == 3,"active_schema_not_verified")
            require(not await conn.fetchval("SELECT has_table_privilege(current_user,'shared_memory.records','DELETE')"),
                    "active_privilege_boundary_failed")
        finally:await conn.close()


async def deny_old(connect,old):
    for kind,field in FIELDS.items():
        try:
            conn = await connect(old[kind][field],timeout=10,command_timeout=10)
        except Exception as error:
            require(getattr(error,"sqlstate",None) in {"28000","28P01"},"old_login_denial_not_verified")
        else:
            await conn.close()
            raise ValueError("old_service_login_still_accepted")


async def login_flag(conn,role,enabled):
    identifier = await conn.fetchval("SELECT quote_ident($1::text)",role)
    await conn.execute("ALTER ROLE "+identifier+(" LOGIN" if enabled else " NOLOGIN"))


async def retire(connect,operator,current,old,roles,write,attempt,result,unchanged):
    conn = await connect(operator["ENHANCED_MEMORY_DATABASE_URL"],timeout=10,command_timeout=20)
    originals = {}
    touched = False
    try:
        await verify_active(connect,current)
        for role in roles.values():
            row = await conn.fetchrow("SELECT oid,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=$1",role)
            require(row is not None and row["rolcanlogin"] and not any(row[k] for k in
                ("rolsuper","rolcreatedb","rolcreaterole","rolreplication","rolbypassrls")),"restricted_old_login_required")
            require(await conn.fetchval("SELECT count(*) FROM pg_stat_activity WHERE usename=$1",role) == 0,
                    "old_service_sessions_present_no_termination")
            originals[role] = dict(row)
        write(attempt / "roles.before.private.json",json.dumps(originals).encode())
        unchanged()
        result["checkpoint"] = "disable_old_logins"
        touched = True
        async with conn.transaction():
            for role in roles.values():await login_flag(conn,role,False)
        for role in roles.values():
            require(await conn.fetchval("SELECT rolcanlogin FROM pg_roles WHERE rolname=$1",role) is False,
                    "old_login_flag_not_disabled")
            require(await conn.fetchval("SELECT count(*) FROM pg_stat_activity WHERE usename=$1",role) == 0,
                    "old_service_sessions_present_no_termination")
        result["checkpoint"] = "authentication_verification"
        await deny_old(connect,old)
        await verify_active(connect,current)
        unchanged()
        result.update(complete=True,checkpoint="complete",retired_service_login_count=2,
            old_service_logins_denied=True,replacement_service_logins_authenticated=True,
            old_sessions_absent=True,roles_and_grants_retained=True)
    except BaseException as error:
        result["category"] = "postgres_login_retirement_incomplete_preserve_evidence"
        allowed = {"active_identity_differs","active_schema_not_verified","active_privilege_boundary_failed",
            "restricted_old_login_required","old_service_sessions_present_no_termination","old_login_flag_not_disabled",
            "old_login_denial_not_verified","old_service_login_still_accepted","protected_configuration_changed_concurrently"}
        if type(error) is ValueError and str(error) in allowed:result["reason"] = str(error)
        if touched:
            try:
                async with conn.transaction():
                    for role,row in originals.items():
                        actual = await conn.fetchval("SELECT oid FROM pg_roles WHERE rolname=$1",role)
                        require(actual == row["oid"],"rollback_role_identity_changed")
                        await login_flag(conn,role,row["rolcanlogin"])
                require(all([await conn.fetchval("SELECT rolcanlogin FROM pg_roles WHERE rolname=$1",role)
                             == row["rolcanlogin"] for role,row in originals.items()]),"rollback_flag_not_verified")
                await verify_active(connect,current)
                result["rollback_login_flags_verified"] = True
            except BaseException:result["rollback_login_flags_verified"] = False
    finally:await conn.close()


def main():
    require(os.geteuid() == 0 and Path(sys.prefix) == BASE / "runtime" and len(sys.argv) == 1,
            "fixed_protected_operator_python_required")
    import asyncpg
    os.umask(0o077)
    raw = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == SHARED_SHA256,"reviewed_file_support_required")
    shared = {"__name__":"verified_login_retirement_files"}
    exec(compile(raw,"<verified-login-retirement-files>","exec"),shared)
    read,write = (shared[k] for k in ("read_file","private_write"))
    gates = ((STAGE / "postgres-service-rotation/summary.json","new_roles_authenticated_and_restricted"),
        (STAGE / "postgres-operator-backup-rotation/summary.json","old_operator_backup_passwords_denied"),
        (STAGE / "application-signing-rotation/summary.json","old_signing_key_fresh_token_denied"),
        (BASE / "operator-evidence/installed-worker-projection-after-rotation/summary.json","installed_worker_projection_qualified"))
    for path,field in gates:
        receipt = json.loads(read(path,0))
        require(receipt.get("complete") is True and receipt.get(field) is True,"prior_rotation_and_projection_pass_required")
    selected = {name:read(Path("/etc/enhanced-cognee") / (name+".json"),0) for name in (*FIELDS,"operator","backup")}
    configs = {name:json.loads(value) for name,value in selected.items()}
    old = {kind:json.loads(read(STAGE / "postgres-service-rotation" / (kind+".before.json"),0)) for kind in FIELDS}
    roles = plan(old,configs,configs["operator"],configs["backup"])
    attempt = STAGE / "postgres-legacy-login-retirement"
    attempt.mkdir(mode=0o700)
    result = dict(complete=False,evidence=str(attempt),source_revision=BASE.name,checkpoint="old_role_preflight",profiles_changed=False,
        services_restarted=False,canonical_memory_edits=False,keys_changed=False,all_credentials_rotated=False,
        fleet_launch_approved=False)
    def unchanged():
        require(all(read(Path("/etc/enhanced-cognee") / (name+".json"),0) == value for name,value in selected.items()),
                "protected_configuration_changed_concurrently")
    def interrupted(signum,frame):raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM,interrupted)
    write(attempt / "started.json",json.dumps(result).encode())
    asyncio.run(retire(asyncpg.connect,configs["operator"],configs,old,roles,write,attempt,result,unchanged))
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"postgres_retirement_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
