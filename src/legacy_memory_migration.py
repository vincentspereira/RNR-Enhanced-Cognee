"""Explicit, copy-only migration from legacy documents to encrypted records.

This is an operator command, never an agent tool. It does not guess project
ownership, alter a source table, copy old vectors, or grant cross-project access.
Dry-run is the default. Each acknowledged copy is independently retry-safe.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime

from src.memory_keys import canonical_cipher_from_environment
from src.memory_service import MemoryScope, MemoryService
from src.multi_tenant import validate_tenant_id


@dataclass(frozen=True)
class MigrationSelection:
    tenant: str
    project: str
    owner: str
    agent: str
    source_global: bool = False

    def __post_init__(self):
        validate_tenant_id(self.tenant)
        validate_tenant_id(self.project)
        for value in (self.owner, self.agent):
            if not value.strip() or len(value) > 200:
                raise ValueError("An explicit owner and agent of 1-200 characters are required")

    @property
    def table(self) -> str:
        return "documents" if self.source_global else "documents_t_" + self.tenant

    @property
    def scope(self) -> MemoryScope:
        return MemoryScope(self.tenant, self.project, self.owner, self.agent)


class LegacyMemoryMigration:
    def __init__(self, service: MemoryService, selection: MigrationSelection):
        self.service, self.selection = service, selection

    def prepare(self, row: dict) -> dict:
        """Normalize UUID/TEXT IDs and JSONB/JSON metadata without lossy casts."""
        ident = str(row.get("id") or "")
        content = row.get("content")
        if not ident or not isinstance(content, str):
            raise ValueError("Legacy rows require a nonempty ID and text content")
        if content.startswith(("enc:", "enc2:")):
            content = self.service.cipher.decrypt(content)
        self.service.admit(content)
        metadata = row.get("metadata")
        if metadata is None:
            metadata = {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        if not isinstance(metadata, dict):
            raise ValueError("Legacy metadata must be a JSON object")
        # Source fields remain inside encryption. Retain the old ID for lineage,
        # but do not accept old metadata as a project, owner, or sharing grant.
        lineage = {"source_table": self.selection.table, "source_id": ident,
                   "source_created_at": str(row.get("created_at") or ""),
                   "source_agent": str(row.get("agent_id") or ""),
                   "title": str(row.get("title") or ""), "legacy_metadata": metadata,
                   "import_authority": "operator_selected_unverified_source"}
        self.service.admit(json.dumps(lineage, ensure_ascii=True))
        category = str(row.get("memory_category") or "legacy_import")
        if not 1 <= len(category) <= 100:
            raise ValueError("Legacy category exceeds the supported length")
        def expiry_value(value):
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError("Legacy expiry must be an ISO timestamp")
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError("Legacy expiry must include a timezone")
            return parsed

        column_expiry = expiry_value(row.get("expire_at"))
        metadata_expiry = expiry_value(metadata.get("expires_at"))
        if column_expiry and metadata_expiry and column_expiry != metadata_expiry:
            raise ValueError("Legacy expiry fields conflict; review the source before copying")
        expiry = column_expiry or metadata_expiry
        # A scope-qualified stable key preserves the first imported snapshot.
        # Source changes on a later run conflict rather than silently overwriting.
        key = hashlib.sha256((self.selection.table + "\0" + ident).encode()).hexdigest()
        return dict(content=content, category=category, metadata=lineage,
                    expires_at=expiry, idempotency_key="legacy_copy:" + key)

    async def run(self, *, apply: bool = False, limit: int = 100, after_id: str = "") -> dict:
        if not 1 <= limit <= 500:
            raise ValueError("Migration batches must contain 1-500 rows")
        table = self.selection.table  # Constructed only from a canonical ID.
        async with self.service.pool.acquire() as conn:
            async with conn.transaction(isolation="repeatable_read", readonly=True):
                await conn.execute("SET LOCAL TIME ZONE 'UTC'")
                columns = await conn.fetch("""SELECT column_name FROM information_schema.columns
                    WHERE table_schema='shared_memory' AND table_name=$1""", table)
                if not {"id", "content"} <= {r["column_name"] for r in columns}:
                    raise ValueError("Selected legacy table is missing or has no supported document schema")
                # Do not pull historical vectors or arbitrary extra columns into memory.
                selected = [name for name in ("id", "content", "metadata", "title", "agent_id",
                                              "memory_category", "expire_at", "created_at")
                            if name in {r["column_name"] for r in columns}]
                # Limit source allocation before JSON decoding. Large rows fail this
                # preflight rather than causing a partial write in this batch.
                too_large = await conn.fetchval(f"""SELECT EXISTS(SELECT 1 FROM (
                    SELECT {','.join(selected)} FROM shared_memory.{table}
                    WHERE id::text > $1 ORDER BY id::text LIMIT $2
                    ) batch WHERE octet_length(row_to_json(batch)::text) > 262144)""", after_id, limit)
                if too_large:
                    raise ValueError("Selected legacy batch contains an oversized row; review it separately")
                total = await conn.fetchval(f"""SELECT coalesce(sum(octet_length(row_to_json(batch)::text)),0)
                    FROM (SELECT {','.join(selected)} FROM shared_memory.{table}
                    WHERE id::text > $1 ORDER BY id::text LIMIT $2) batch""", after_id, limit)
                if total > 16 * 1024 * 1024:
                    raise ValueError("Selected legacy batch exceeds the memory budget; reduce the batch size")
                rows = await conn.fetch(f"""SELECT row_to_json(batch)::text AS document FROM (
                    SELECT {','.join(selected)} FROM shared_memory.{table}
                    WHERE id::text > $1 ORDER BY id::text LIMIT $2) batch""", after_id, limit)
        # Validate the complete bounded batch before writing any of it.
        source = [json.loads(row["document"]) for row in rows]
        prepared = [self.prepare(row) for row in source]
        copied = 0
        if apply:
            for item in prepared:
                await self.service.remember(self.selection.scope, **item)
                copied += 1
        return {"mode": "applied" if apply else "dry_run", "source_table": table,
                "tenant": self.selection.tenant, "project": self.selection.project,
                "selected": len(prepared), "acknowledged": copied,
                "next_after_id": str(source[-1]["id"]) if source else after_id,
                "source_preserved": True, "sharing_grants_created": 0,
                "old_embeddings_copied": False}


async def _main(args):
    import asyncpg
    selection = MigrationSelection(args.tenant, args.project, args.owner, args.agent, args.source_global)
    cipher = canonical_cipher_from_environment()
    pool = await asyncpg.create_pool(os.environ["ENHANCED_MEMORY_DATABASE_URL"], min_size=1,
                                    max_size=2, command_timeout=30)
    try:
        service = MemoryService(pool, cipher)
        if args.apply:
            await service.initialize()
        result = await LegacyMemoryMigration(service, selection).run(
            apply=args.apply, limit=args.limit, after_id=args.after_id)
        print(json.dumps(result, ensure_ascii=True))
    finally:
        await pool.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tenant", "project", "owner", "agent"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--source-global", action="store_true",
                        help="Explicitly select the old unscoped table instead of this tenant's table")
    parser.add_argument("--apply", action="store_true", help="Copy the reviewed batch; default only validates")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--after-id", default="")
    args = parser.parse_args()
    try:
        asyncio.run(_main(args))
    except Exception:
        # Connection strings and source content must never appear in the output.
        parser.exit(1, "Migration stopped. No source records were changed. Review configuration, source validation, and retry conflicts.\n")


if __name__ == "__main__":
    main()
