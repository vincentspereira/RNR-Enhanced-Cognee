"""Current encrypted backup and NEW-database canonical recovery, operator only.

Run with the staged protected Python in isolated mode. No live memory edits,
service switch, index clearing, profile change or deletion. Actual derived-store
replay is a separate unresolved gate; this action never labels it a pass.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import uuid
from urllib.parse import urlsplit, urlunsplit


BACKUPS = Path("/var/backups/enhanced-cognee")
IDENTITY = Path("/etc/enhanced-cognee/age-recovery-identity.txt")
REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
RUNTIME = Path("/opt/enhanced-cognee-memory/candidates") / REVISION / "runtime"


def private_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 65536:
            raise ValueError("operator_configuration_protection")
        value = json.loads(stream.read(65537))
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise ValueError("operator_configuration_shape")
    return value


async def snapshot(pool):
    # Counts and encrypted-row hashes only; no decrypted content is retained.
    result = {}
    async with pool.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            names = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='shared_memory' AND table_type='BASE TABLE'")
            for item in names:
                name = item["table_name"]
                if not re.fullmatch(r"[a-z_]{1,63}", name):
                    raise ValueError("unexpected_canonical_table")
                if name in {"record_outbox", "request_budgets"} or name.startswith("index_"):
                    continue
                rows = await conn.fetch(f'SELECT row_to_json(t)::text AS row FROM shared_memory."{name}" t ORDER BY row_to_json(t)::text LIMIT 10001')
                if len(rows) > 10000:
                    raise ValueError("recovery_comparison_budget")
                digest = hashlib.sha256()
                for row in rows:
                    digest.update(row["row"].encode())
                    digest.update(b"\n")
                result[name] = {"rows": len(rows), "sha256": digest.hexdigest()}
    return result


async def qualify(result, evidence):
    import asyncpg
    from src.memory_backup import restore
    from src.memory_keys import canonical_cipher_from_environment
    from src.memory_service import MemoryService, MemoryScope

    operator = private_json(Path("/etc/enhanced-cognee/operator.json"))
    backup = private_json(Path("/etc/enhanced-cognee/backup.json"))
    required = {"ENHANCED_MEMORY_DATABASE_URL", "ENHANCED_BACKUP_SIGNING_KEY", "ENHANCED_BACKUP_RECIPIENT"}
    if not required <= backup.keys() or not operator.get("ENHANCED_MEMORY_DATABASE_URL"):
        raise ValueError("operator_recovery_configuration_missing")
    os.environ.clear()
    os.environ.update(PATH="/usr/local/bin:/usr/bin:/bin", LANG="C.UTF-8",
                      HOME=str(evidence), ENHANCED_LOAD_DOTENV="0", COGNEE_LOG_FILE="false",
                      COGNEE_TELEMETRY_ENABLED="0", HF_HUB_OFFLINE="1")
    os.environ.update(operator)
    for key in ("ENHANCED_BACKUP_SIGNING_KEY", "ENHANCED_BACKUP_SIGNING_KEY_ID"):
        if key in backup:
            os.environ[key] = backup[key]
    info = IDENTITY.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError("recovery_identity_protection")
    cipher = canonical_cipher_from_environment()
    source = await asyncpg.create_pool(operator["ENHANCED_MEMORY_DATABASE_URL"], min_size=1, max_size=2, command_timeout=30)
    try:
        before = await snapshot(source)
        generations = set(BACKUPS.glob("memory_*.dump.age"))
        process = await asyncio.create_subprocess_exec("/usr/bin/systemctl", "start", "enhanced-cognee-backup.service",
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        if await asyncio.wait_for(process.wait(), timeout=660):
            raise ValueError("current_database_backup_failed")
        created = set(BACKUPS.glob("memory_*.dump.age")) - generations
        if len(created) != 1:
            raise ValueError("current_backup_generation_ambiguous")
        path = created.pop()
        result["current_encrypted_backup_created"] = True
        result["generation"] = path.name
        target_name = "memory_restore_launch_" + uuid.uuid4().hex[:16]
        result["new_disposable_database"] = target_name
        await restore(str(path), str(IDENTITY), target_name)
        result["authenticated_decryption_and_restore"] = True
        uri = urlsplit(operator["ENHANCED_MEMORY_DATABASE_URL"])
        target_url = urlunsplit((uri.scheme, uri.netloc, "/" + target_name, uri.query, ""))
        target = await asyncpg.create_pool(target_url, min_size=1, max_size=2, command_timeout=30)
        try:
            restored = await snapshot(target)
            after = await snapshot(source)
            if before != restored or before != after:
                raise ValueError("canonical_snapshot_changed_or_differs")
            result["canonical_history_sharing_snapshot_matches"] = True
            result["canonical_table_counts"] = {name: item["rows"] for name, item in restored.items()}
            service = MemoryService(target, cipher)
            await service.check_schema()
            decrypted = 0
            async with target.acquire() as conn:
                for table in ("records", "record_versions"):
                    rows = await conn.fetch(f"SELECT payload FROM shared_memory.{table} LIMIT 10001")
                    if len(rows) > 10000:
                        raise ValueError("recovery_decryption_budget")
                    for row in rows:
                        json.loads(cipher.decrypt(row["payload"]))
                        decrypted += 1
                row = await conn.fetchrow("SELECT tenant,project,id,owner_subject,writer_agent FROM shared_memory.records WHERE state='active' AND (expires_at IS NULL OR expires_at>now()) LIMIT 1")
            if row is None:
                raise ValueError("no_active_record_for_scope_check")
            own = MemoryScope(row["tenant"], row["project"], row["owner_subject"], row["writer_agent"])
            await service.get(own, row["id"])
            other = "denied_" + uuid.uuid4().hex[:16]
            try:
                await service.get(MemoryScope(row["tenant"], other, "invented_denied", "invented_denied"), row["id"])
            except KeyError:
                result["restored_other_scope_denied"] = True
            else:
                raise ValueError("restored_scope_denial_failed")
            result["decrypted_payload_count"] = decrypted
            result["canonical_recovery_qualified"] = True
            result["complete"] = True
        finally:
            await target.close()
    finally:
        await source.close()


def main():
    import sys
    if os.geteuid() != 0 or Path(sys.prefix) != RUNTIME:
        raise SystemExit("ERR: use the staged protected Python as operator")
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    evidence = Path(tempfile.mkdtemp(prefix="ec-launch-recovery-", dir="/var/tmp"))
    result = {"source_revision": REVISION, "complete": False, "evidence": str(evidence),
              "canonical_recovery_qualified": False, "derived_store_recovery_qualified": False,
              "service_runtime_changed": False, "live_memory_edits": False,
              "fleet_launch_approved": False}
    try:
        asyncio.run(qualify(result, evidence))
    except BaseException as error:
        categories = {"operator_configuration_protection", "operator_configuration_shape", "operator_recovery_configuration_missing",
                      "recovery_identity_protection", "current_database_backup_failed", "current_backup_generation_ambiguous",
                      "unexpected_canonical_table", "recovery_comparison_budget", "canonical_snapshot_changed_or_differs",
                      "recovery_decryption_budget", "no_active_record_for_scope_check", "restored_scope_denial_failed"}
        result["category"] = str(error) if type(error) is ValueError and str(error) in categories else "recovery_failed_evidence_retained"
    (evidence / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
