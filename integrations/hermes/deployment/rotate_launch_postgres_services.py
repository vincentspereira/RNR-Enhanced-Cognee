"""Stage and activate new least-privilege API/worker PostgreSQL identities.

Use the protected candidate Python. Preserve old roles and config for rollback.
No canonical edits, profile traversal, encryption/signing-key change or secret
output. Other store/operator credential rotations remain separate.
"""
from __future__ import annotations

import asyncio
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from urllib.parse import quote, urlsplit, urlunsplit

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
FIELDS = {"api":"ENHANCED_MEMORY_DATABASE_URL","worker":"ENHANCED_INDEX_DATABASE_URL"}
UNITS = {"api":"enhanced-cognee-api.service","worker":"enhanced-cognee-index.service"}


def identity(row):
    if (not isinstance(row,dict) or set(row) != {"username","password"}
            or not isinstance(row["username"],str) or not re.fullmatch(r"ec_(api|worker)_[a-f0-9]{12}",row["username"])
            or not isinstance(row["password"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}",row["password"])):
        raise ValueError("generated_service_identity_required")
    return row["username"],row["password"]


def grants(role,kind):
    if not re.fullmatch(r"ec_(api|worker)_[a-f0-9]{12}",role) or kind not in FIELDS:
        raise ValueError("fixed_service_role_required")
    target = '"'+role+'"'
    statements = ["GRANT USAGE ON SCHEMA shared_memory TO "+target]
    if kind == "api":
        for table in ("records","record_versions","record_shares","record_outbox","request_budgets","record_audit","library_members","library_publications"):
            operations = "SELECT,INSERT" if table in {"record_versions","record_audit","record_outbox"} else "SELECT,INSERT,UPDATE"
            statements.append("GRANT "+operations+" ON shared_memory."+table+" TO "+target)
        for table in ("record_shares","library_members","library_publications"):
            statements.append("GRANT DELETE ON shared_memory."+table+" TO "+target)
        for table in ("memory_service_schema","index_deliveries","index_receipts","index_workers"):
            statements.append("GRANT SELECT ON shared_memory."+table+" TO "+target)
        for sequence in ("record_outbox_id_seq","record_audit_id_seq"):
            statements.append("GRANT USAGE ON SEQUENCE shared_memory."+sequence+" TO "+target)
    else:
        for table in ("records","record_outbox","memory_service_schema"):
            statements.append("GRANT SELECT ON shared_memory."+table+" TO "+target)
        for table in ("index_deliveries","index_receipts","index_workers"):
            statements.append("GRANT SELECT,INSERT,UPDATE ON shared_memory."+table+" TO "+target)
        statements.extend(["GRANT INSERT ON shared_memory.record_outbox TO "+target,
            "GRANT UPDATE(processed_at) ON shared_memory.record_outbox TO "+target,
            "GRANT USAGE ON SEQUENCE shared_memory.record_outbox_id_seq TO "+target])
    return statements


def new_url(original,username,password):
    uri = urlsplit(original)
    if uri.scheme not in {"postgres","postgresql"} or uri.hostname not in {"127.0.0.1","localhost"} or uri.port != 28434:
        raise ValueError("fixed_local_postgres_binding_required")
    host = uri.netloc.rsplit("@",1)[-1]
    return urlunsplit((uri.scheme,quote(username,safe="")+":"+quote(password,safe="")+"@"+host,uri.path,uri.query,""))


async def provision(operator,configs,candidates):
    import asyncpg
    # Validate every fixed role and URL before a database statement is executed.
    identities = {kind:identity(candidates[kind]) for kind in FIELDS}
    for kind in FIELDS:
        if not identities[kind][0].startswith("ec_"+kind+"_"):
            raise ValueError("service_identity_kind_differs")
    urls = {kind:new_url(configs[kind][FIELDS[kind]],*identities[kind]) for kind in FIELDS}
    new_url(operator["ENHANCED_MEMORY_DATABASE_URL"],*identities["api"])
    conn = await asyncpg.connect(operator["ENHANCED_MEMORY_DATABASE_URL"],timeout=10,command_timeout=20)
    try:
        async with conn.transaction():
            for kind,(role,password) in identities.items():
                if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)",role):
                    raise ValueError("existing_role_preserved_no_overwrite")
                await conn.execute('CREATE ROLE "'+role+'" LOGIN PASSWORD \''+password+"' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT")
                for statement in grants(role,kind):
                    await conn.execute(statement)
    finally:
        await conn.close()
    for kind,url in urls.items():
        service = await asyncpg.connect(url,timeout=10,command_timeout=10)
        try:
            attrs = await service.fetchrow("SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")
            if any(attrs.values()) or await service.fetchval("SELECT has_table_privilege(current_user,'shared_memory.records','DELETE')"):
                raise ValueError("service_role_privilege_boundary_failed")
            if await service.fetchval("SELECT max(version) FROM shared_memory.memory_service_schema") != 3:
                raise ValueError("service_schema_access_failed")
            if kind == "worker" and await service.fetchval("SELECT has_table_privilege(current_user,'shared_memory.records','UPDATE')"):
                raise ValueError("worker_canonical_write_boundary_failed")
        finally:
            await service.close()
    return urls


def ready():
    deadline = time.monotonic()+60
    while time.monotonic() < deadline:
        connection = HTTPConnection("127.0.0.1",28080,timeout=3)
        try:
            connection.request("GET","/health/ready")
            reply = connection.getresponse()
            raw = reply.read(16385)
            if reply.status == 200 and len(raw) <= 16384 and json.loads(raw).get("ready") is True:
                return True
        except (OSError,ValueError):
            pass
        finally:
            connection.close()
        time.sleep(1)
    return False


def main():
    if os.geteuid() != 0 or Path(sys.prefix) != BASE / "runtime":
        raise ValueError("protected_operator_python_required")
    os.umask(0o077)
    source = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != SHARED_SHA256:
        raise ValueError("reviewed_support_required")
    shared = {"__name__":"verified_postgres_rotation_files"}
    exec(compile(source,"<verified-postgres-rotation-files>","exec"),shared)
    read,write,replace = (shared[k] for k in ("read_file","private_write","replace_file"))
    candidates = json.loads(read(STAGE / "replacement-logins.private.json",0))["postgresql"]
    operator = json.loads(read(Path("/etc/enhanced-cognee/operator.json"),0))
    original = {kind:read(Path("/etc/enhanced-cognee") / (kind+".json"),0) for kind in FIELDS}
    configs = {kind:json.loads(raw) for kind,raw in original.items()}
    attempt = STAGE / "postgres-service-rotation"
    attempt.mkdir(mode=0o700)
    for kind,raw in original.items():
        write(attempt / (kind+".before.json"),raw)
    result = {"complete":False,"evidence":str(attempt),"checkpoint":"new_roles",
        "profiles_changed":False,"encryption_keys_changed":False,"application_signing_key_changed":False,
        "all_credentials_rotated":False,"fleet_launch_approved":False,"old_roles_retained":True}
    touched = False
    def control(action,kind):
        shared["UNIT"] = UNITS[kind]
        shared["control"](action)
    def interrupted(signum,frame):
        raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM,interrupted)
    try:
        write(attempt / "before-create-roles.json",b'{"provisioning_started":true}')
        urls = asyncio.run(asyncio.wait_for(provision(operator,configs,candidates),timeout=120))
        write(attempt / "new-database-urls.private.json",json.dumps(urls).encode())
        result["new_roles_authenticated_and_restricted"] = True
        result["checkpoint"] = "service_configuration"
        touched = True
        control("stop","worker")
        control("stop","api")
        for kind in FIELDS:
            path = Path("/etc/enhanced-cognee") / (kind+".json")
            if read(path,0) != original[kind]:
                raise ValueError("service_configuration_changed_concurrently")
            configs[kind][FIELDS[kind]] = urls[kind]
            replace(path,json.dumps(configs[kind]).encode(),0)
        control("start","api")
        control("start","worker")
        if not ready():
            raise ValueError("new_service_credentials_not_ready")
        result.update(complete=True,checkpoint="complete",api_and_worker_database_credentials_changed=True,
                      api_ready=True,worker_projection_after_rotation_qualified=False)
    except BaseException as error:
        result["category"] = "postgres_service_rotation_incomplete_preserve_evidence"
        state = getattr(error,"sqlstate",None)
        if isinstance(state,str) and re.fullmatch(r"[A-Z0-9]{5}",state):
            result["postgres_sqlstate"] = state
        if touched:
            try:
                control("stop","worker")
                control("stop","api")
                for kind,raw in original.items():
                    replace(Path("/etc/enhanced-cognee") / (kind+".json"),raw,0)
                control("start","api")
                control("start","worker")
                result["rollback_api_ready"] = ready()
            except BaseException:
                result["rollback_api_ready"] = False
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"postgres_rotation_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
