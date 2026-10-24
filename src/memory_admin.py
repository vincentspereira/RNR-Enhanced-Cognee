"""Operator-only provisioning and scoped credentials; secrets go to private files."""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from src.memory_service import MemoryService
from src.multi_tenant import validate_tenant_id


def write_private_json(path: str, value: dict) -> None:
    target = Path(path)
    if not target.is_absolute() or target.parent != target.parent.resolve(strict=True):
        raise ValueError("Use an absolute secret-file path without symlink parents")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def create_config(path: str) -> None:
    write_private_json(path, {"ENCRYPTION_MASTER_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
                             "ENHANCED_JWT_SECRET": secrets.token_urlsafe(48),
                             "ENHANCED_BACKUP_SIGNING_KEY": secrets.token_urlsafe(48),
                             "ENHANCED_INDEX_KEY": secrets.token_urlsafe(48),
                             "ENHANCED_BACKUP_SIGNING_KEY_ID": "backup_v1",
                             "ENHANCED_ENV": "production", "ENHANCED_REQUIRE_TENANT": "1"})


def issue_token(*, tenant: str, project: str, subject: str, agent: str,
                output: str, expires_hours: int = 1, readonly: bool = False, reviewer: bool = False) -> None:
    import jwt
    validate_tenant_id(tenant)
    validate_tenant_id(project)
    if reviewer and readonly:
        raise ValueError("Choose one restricted token role")
    if not 1 <= expires_hours <= 24 or not all(0 < len(value.strip()) <= 200 for value in (subject, agent)):
        raise ValueError("Use bounded actor identifiers and a token lifetime of 1-24 hours")
    secret = os.environ["ENHANCED_JWT_SECRET"]
    if len(secret.encode()) < 32:
        raise ValueError("A persistent signing secret of at least 32 bytes is required")
    now = int(time.time())
    token = jwt.encode({"sub": subject, "agent_id": agent, "tenant": tenant,
                        "project_id": project, "roles": ["memory_reviewer" if reviewer else "readonly" if readonly else "api_client"],
                        "capture_policy": "selected", "iat": now, "exp": now + expires_hours * 3600},
                       secret, algorithm="HS256")
    write_private_json(output, {"ENHANCED_COGNEE_ACCESS_TOKEN": token})


async def grant_runtime(pool, *, role: str, operator_url: str, output: str) -> None:
    """No CREATE/ALTER/DROP/TRUNCATE rights and no canonical/history deletion."""
    validate_tenant_id(role)
    parsed = urlsplit(operator_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise ValueError("Use an explicit PostgreSQL operator URL")
    password = secrets.token_urlsafe(48)  # Generated alphabet contains no SQL quotes.
    host = parsed.netloc.rsplit("@", 1)[-1]
    options = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k in {"sslmode", "sslrootcert"}])
    runtime_url = urlunsplit((parsed.scheme, role + ":" + password + "@" + host, parsed.path, options, ""))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role):
                raise ValueError("Runtime role already exists; credentials were not changed")
            # Write first, so an existing output path cannot result in a role
            # being created without an acknowledged recovery file. A later DB
            # failure can leave an unused private file; it is never auto-deleted.
            write_private_json(output, {"ENHANCED_MEMORY_DATABASE_URL": runtime_url})
            await conn.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT")
            await conn.execute(f"GRANT USAGE ON SCHEMA shared_memory TO {role}")
            tables = ("records", "record_versions", "record_shares", "record_outbox", "request_budgets",
                      "record_audit", "library_members", "library_publications")
            for table in tables:
                operations = "SELECT,INSERT" if table in {"record_versions", "record_audit", "record_outbox"} else "SELECT,INSERT,UPDATE"
                await conn.execute(f"GRANT {operations} ON shared_memory.{table} TO {role}")
            for table in ("record_shares", "library_members", "library_publications"):
                await conn.execute(f"GRANT DELETE ON shared_memory.{table} TO {role}")
            await conn.execute(f"GRANT SELECT ON shared_memory.memory_service_schema TO {role}")
            for table in ("index_deliveries", "index_receipts", "index_workers"):
                await conn.execute(f"GRANT SELECT ON shared_memory.{table} TO {role}")
            for sequence in ("record_outbox_id_seq", "record_audit_id_seq"):
                await conn.execute(f"GRANT USAGE ON SEQUENCE shared_memory.{sequence} TO {role}")


async def grant_worker(pool, *, role: str, operator_url: str, output: str) -> None:
    """Separate worker: canonical reads, durable delivery writes, no memory edits."""
    validate_tenant_id(role)
    parsed = urlsplit(operator_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise ValueError("Use an explicit PostgreSQL operator URL")
    password = secrets.token_urlsafe(48)
    host = parsed.netloc.rsplit("@", 1)[-1]
    options = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k in {"sslmode", "sslrootcert"}])
    url = urlunsplit((parsed.scheme, role + ":" + password + "@" + host, parsed.path, options, ""))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role):
                raise ValueError("Worker role already exists; credentials were not changed")
            write_private_json(output, {"ENHANCED_INDEX_DATABASE_URL": url})
            await conn.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT")
            await conn.execute(f"GRANT USAGE ON SCHEMA shared_memory TO {role}")
            for table in ("records", "record_outbox", "memory_service_schema"):
                await conn.execute(f"GRANT SELECT ON shared_memory.{table} TO {role}")
            for table in ("index_deliveries", "index_receipts", "index_workers"):
                await conn.execute(f"GRANT SELECT,INSERT,UPDATE ON shared_memory.{table} TO {role}")
            await conn.execute(f"GRANT INSERT ON shared_memory.record_outbox TO {role}")
            await conn.execute(f"GRANT UPDATE(processed_at) ON shared_memory.record_outbox TO {role}")
            await conn.execute(f"GRANT USAGE ON SEQUENCE shared_memory.record_outbox_id_seq TO {role}")


async def upgrade_runtime(pool, *, role: str) -> None:
    """Add schema-3 read grants without replacing a password/recovery file."""
    validate_tenant_id(role)
    async with pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role)
            if not exists:
                raise ValueError("Provision the runtime role first")
            for table in ("index_deliveries", "index_receipts", "index_workers"):
                await conn.execute(f"GRANT SELECT ON shared_memory.{table} TO {role}")


async def _database(args):
    import asyncpg
    url = os.environ["ENHANCED_MEMORY_DATABASE_URL"]
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2, command_timeout=30)
    try:
        if args.command == "init-schema":
            await MemoryService.provision(pool)
        elif args.command == "grant-worker":
            await grant_worker(pool, role=args.role, operator_url=url, output=args.output)
        elif args.command == "upgrade-runtime":
            await upgrade_runtime(pool, role=args.role)
        else:
            await grant_runtime(pool, role=args.role, operator_url=url, output=args.output)
    finally:
        await pool.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    config = sub.add_parser("create-config")
    config.add_argument("--output", required=True)
    token = sub.add_parser("issue-token")
    for name in ("tenant", "project", "subject", "agent", "output"):
        token.add_argument("--" + name, required=True)
    token.add_argument("--expires-hours", type=int, default=1)
    roles = token.add_mutually_exclusive_group()
    roles.add_argument("--readonly", action="store_true")
    roles.add_argument("--reviewer", action="store_true")
    sub.add_parser("init-schema")
    role = sub.add_parser("grant-runtime")
    role.add_argument("--role", required=True)
    role.add_argument("--output", required=True)
    worker = sub.add_parser("grant-worker")
    worker.add_argument("--role", required=True)
    worker.add_argument("--output", required=True)
    upgrade = sub.add_parser("upgrade-runtime")
    upgrade.add_argument("--role", required=True)
    index_key = sub.add_parser("create-index-key")
    index_key.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "create-config":
            create_config(args.output)
        elif args.command == "create-index-key":
            write_private_json(args.output, {"ENHANCED_INDEX_KEY": secrets.token_urlsafe(48)})
        elif args.command == "issue-token":
            issue_token(**{key: value for key, value in vars(args).items() if key != "command"})
        else:
            asyncio.run(_database(args))
        print("Operator action completed. Secret values are not printed; keep generated files private.")
    except Exception:
        parser.exit(1, "Operator action stopped. No secret values were printed. Review schema, permissions and existing output files.\n")


if __name__ == "__main__":
    main()
