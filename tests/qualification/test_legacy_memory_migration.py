"""Copy-only migration against both legacy document ID/schema variants."""
import json
import os
import uuid

import asyncpg
import pytest
from cryptography.fernet import Fernet

from src.encryption_manager import EncryptionManager
from src.legacy_memory_migration import LegacyMemoryMigration, MigrationSelection
from src.memory_service import MemoryConflict, MemoryScope, MemoryService


@pytest.mark.asyncio
@pytest.mark.parametrize("id_type", ["UUID", "TEXT"])
async def test_legacy_copy_dry_run_retry_isolation_and_source_preservation(id_type):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Requires an explicitly disposable PostgreSQL database")
    tenant = "q_" + uuid.uuid4().hex[:20]
    selection = MigrationSelection(tenant, "reviewed_project", "alice", "migration")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    try:
        svc = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
        await svc.initialize()
        ident = uuid.uuid4()
        async with pool.acquire() as conn:
            # The two installation paths used different ID types/optional columns.
            extra = ", memory_category TEXT" if id_type == "UUID" else ""
            await conn.execute(f"""CREATE TABLE shared_memory.{selection.table} (
                id {id_type} PRIMARY KEY, content TEXT, metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT now(), agent_id TEXT {extra})""")
            await conn.execute(f"""INSERT INTO shared_memory.{selection.table}
                (id,content,metadata,agent_id) VALUES($1,$2,$3,$4)""",
                ident if id_type == "UUID" else str(ident), "Synthetic legacy migration fixture",
                json.dumps({"project_id": "must_not_choose_scope", "share": True}), "historical-agent")
        migration = LegacyMemoryMigration(svc, selection)
        preview = await migration.run()
        assert preview["mode"] == "dry_run" and preview["selected"] == 1
        assert (await svc.status(selection.scope))["active_records"] == 0
        assert (await migration.run(apply=True))["acknowledged"] == 1
        await migration.run(apply=True)
        assert (await svc.status(selection.scope))["active_records"] == 1
        result = (await svc.recall(selection.scope, "migration"))["results"][0]
        assert result["metadata"]["source_id"] == str(ident)
        assert result["metadata"]["legacy_metadata"]["project_id"] == "must_not_choose_scope"
        assert (await svc.recall(MemoryScope(tenant, "other", "alice", "hermes"), "migration"))["results"] == []
        assert (await migration.run(after_id=str(ident)))["selected"] == 0
        async with pool.acquire() as conn:
            assert await conn.fetchval(f"SELECT content FROM shared_memory.{selection.table}") == "Synthetic legacy migration fixture"
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_outbox WHERE tenant=$1", tenant) == 1
            payload = await conn.fetchval("SELECT payload FROM shared_memory.records WHERE tenant=$1", tenant)
            assert payload.startswith("enc2:") and "migration fixture" not in payload
            await conn.execute(f"UPDATE shared_memory.{selection.table} SET content='Changed historical fixture'")
        with pytest.raises(MemoryConflict):
            await migration.run(apply=True)
        # A conflicting source revision never overwrites the copied snapshot.
        assert (await svc.get(selection.scope, result["id"]))["content"] == "Synthetic legacy migration fixture"
        async with pool.acquire() as conn:
            await conn.execute(f"UPDATE shared_memory.{selection.table} SET metadata='[]'::jsonb")
        with pytest.raises(ValueError, match="JSON object"):
            await migration.run(apply=True)
        # Older Docker TTL lived in metadata rather than a dedicated column.
        expired_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        async with pool.acquire() as conn:
            await conn.execute(f"""INSERT INTO shared_memory.{selection.table}
                (id,content,metadata) VALUES($1,$2,$3)""",
                expired_id if id_type == "UUID" else str(expired_id),
                "uniquelyexpiredword", json.dumps({"expires_at": "2000-01-01T00:00:00Z"}))
        assert (await migration.run(apply=True, after_id=str(ident)))["acknowledged"] == 1
        assert (await svc.recall(selection.scope, "uniquelyexpiredword"))["results"] == []
        assert (await svc.status(selection.scope))["active_records"] == 1
    finally:
        await pool.close()


@pytest.mark.parametrize("tenant,project", [("a-b", "project"), ("a", "Project"), ("a", "x;DROP TABLE records")])
def test_migration_refuses_ambiguous_or_executable_selectors(tenant, project):
    with pytest.raises(ValueError):
        MigrationSelection(tenant, project, "alice", "operator")
