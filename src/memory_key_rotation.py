"""Bounded operator-only rewrapping of canonical current and historical payloads.

Dry-run by default. Rotation retains record IDs, versions, provenance and history.
It does not remove retired keys, modify backups, or authorize private activation.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

from src.memory_keys import MemoryKeyring, canonical_cipher_from_environment
from src.multi_tenant import validate_tenant_id


async def rewrap_project(pool, cipher: MemoryKeyring, *, tenant: str, project: str,
                         actor: str, apply: bool = False, limit: int = 100,
                         after_id: str = "") -> dict:
    validate_tenant_id(tenant)
    validate_tenant_id(project)
    if not isinstance(cipher, MemoryKeyring) or not 1 <= limit <= 500 or not actor.strip() or len(actor) > 200:
        raise ValueError("Rotation requires named keys, an operator actor and a bounded batch")
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Lock canonical rows first, matching mutation lock order. Lock timeout
            # fails the batch cleanly instead of waiting indefinitely on a writer.
            await conn.execute("SET LOCAL lock_timeout='5s'")
            rows = await conn.fetch("""SELECT id,version,octet_length(payload) AS size FROM shared_memory.records
                WHERE tenant=$1 AND project=$2 AND id>$3 ORDER BY id LIMIT $4 FOR UPDATE""",
                tenant, project, after_id, limit)
            versions = await conn.fetch("""SELECT record_id,version,octet_length(payload) AS size
                FROM shared_memory.record_versions WHERE tenant=$1 AND project=$2
                AND record_id=ANY($3::text[]) ORDER BY record_id,version LIMIT 5001 FOR UPDATE""",
                tenant, project, [row["id"] for row in rows])
            if len(versions) > 5000:
                raise ValueError("Rotation history exceeds its version budget; reduce the batch")
            if sum(row["size"] for row in [*rows, *versions]) > 16 * 1024 * 1024:
                raise ValueError("Rotation exceeds its encrypted byte budget; reduce the batch")
            record_ids = [row["id"] for row in rows]
            rows = await conn.fetch("""SELECT id,version,payload FROM shared_memory.records
                WHERE tenant=$1 AND project=$2 AND id=ANY($3::text[]) ORDER BY id""",
                tenant, project, record_ids)
            versions = await conn.fetch("""SELECT record_id,version,payload FROM shared_memory.record_versions
                WHERE tenant=$1 AND project=$2 AND record_id=ANY($3::text[]) ORDER BY record_id,version""",
                tenant, project, record_ids)
            # Validate all ciphertexts before making any writes. The transaction
            # also rolls back the whole batch if a later encryption/update fails.
            prepared = []
            for history, items in ((False, rows), (True, versions)):
                for row in items:
                    plaintext = cipher.decrypt(row["payload"])
                    if cipher.key_id(row["payload"]) != cipher.active:
                        prepared.append((history, row, plaintext))
            if apply:
                for history, row, plaintext in prepared:
                    payload = cipher.encrypt(plaintext)
                    if history:
                        await conn.execute("""UPDATE shared_memory.record_versions SET payload=$5
                            WHERE tenant=$1 AND project=$2 AND record_id=$3 AND version=$4""",
                            tenant, project, row["record_id"], row["version"], payload)
                    else:
                        await conn.execute("""UPDATE shared_memory.records SET payload=$4
                            WHERE tenant=$1 AND project=$2 AND id=$3""",
                            tenant, project, row["id"], payload)
                for row in rows:
                    if any((item["record_id"] if history else item["id"]) == row["id"]
                           for history, item, _ in prepared):
                        await conn.execute("""INSERT INTO shared_memory.record_audit
                            (tenant,project,actor,agent,record_id,version,action)
                            VALUES($1,$2,$3,'operator_key_rotation',$4,$5,$6)""",
                            tenant, project, actor, row["id"], row["version"], "key_rewrapped:" + cipher.active)
    return {"mode": "applied" if apply else "dry_run", "selected_records": len(rows),
            "selected_versions": len(versions), "payloads_needing_rewrap": len(prepared),
            "active_key_id": cipher.active, "next_after_id": rows[-1]["id"] if rows else after_id,
            "keys_deleted": False, "backups_changed": False}


async def _run(args):
    import asyncpg
    cipher = canonical_cipher_from_environment()
    pool = await asyncpg.create_pool(os.environ["ENHANCED_MEMORY_DATABASE_URL"],
                                    min_size=1, max_size=2, command_timeout=30)
    try:
        print(json.dumps(await rewrap_project(pool, cipher, **vars(args)), ensure_ascii=True))
    finally:
        await pool.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tenant", "project", "actor"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--after-id", default="")
    parser.add_argument("--apply", action="store_true")
    try:
        asyncio.run(_run(parser.parse_args()))
    except Exception:
        parser.exit(1, "Rotation stopped; this batch was not committed. Review keys, limits and retained backup requirements.\n")


if __name__ == "__main__":
    main()
