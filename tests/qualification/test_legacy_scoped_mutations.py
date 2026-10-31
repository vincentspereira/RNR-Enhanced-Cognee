"""Legacy positive SQL checks use isolated invented tenant tables."""
import json
import hashlib
import os
import uuid

import asyncpg
import pytest

from src.memory_provenance import MemoryProvenanceTracker
from src.multi_tenant import TenantContext, tenant_scoped_table
from src.realtime_sync import RealTimeMemorySync


@pytest.mark.asyncio
async def test_provenance_transformation_and_agent_copy_stay_in_the_selected_tenant(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Select an explicitly disposable qualification database")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    tenant = "q_" + uuid.uuid4().hex[:20]
    other_tenant = "q_" + uuid.uuid4().hex[:20]
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    try:
        tables = []
        for namespace in (tenant, other_tenant):
            with TenantContext(namespace):
                table = tenant_scoped_table("shared_memory.documents")
                tables.append(table)
                async with pool.acquire() as conn:
                    await conn.execute(f"""CREATE TABLE {table}(
                        id TEXT PRIMARY KEY, title TEXT, content TEXT, agent_id TEXT,
                        memory_category TEXT, metadata JSONB, provenance JSONB,
                        created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now())""")
                    await conn.execute(f"""INSERT INTO {table}
                        (id,title,content,agent_id,memory_category,metadata,provenance)
                        VALUES('same_id','Synthetic title',$1,'source_agent','custom_fixture',$2,$3)""",
                        "Synthetic " + namespace, json.dumps({"fixture": namespace}),
                        json.dumps({"transformations": []}))
        with TenantContext(tenant):
            tracker = MemoryProvenanceTracker(pool)
            assert await tracker.add_transformation("same_id", "source_annotation", {"fixture": "bounded"})
            source = await tracker.get_provenance("same_id")
            assert source["transformations"][0]["type"] == "source_annotation"
            assert not await tracker.mark_verified("same_id")
            with pytest.raises(ValueError):
                await tracker.set_provenance("same_id", "actor", extra={"verified": True})
            assert await tracker.set_provenance("same_id", "synthetic_source",
                                                content_for_checksum="Synthetic " + tenant)
            assert not await tracker.mark_verified("same_id", expected_checksum="wrong")
            assert await tracker.mark_verified("same_id", verified_by="reviewer",
                expected_checksum=hashlib.sha256(("Synthetic " + tenant).encode()).hexdigest())
            verified = await tracker.get_provenance("same_id")
            assert verified["verified"] and verified["verification_type"] == "checksum_integrity"
            result = await RealTimeMemorySync(None, pool).sync_agent_state("source_agent", "target_agent")
            assert result["memories_synced"] == 1 and not result["errors"]
        async with pool.acquire() as conn:
            copied = await conn.fetchrow(f"SELECT * FROM {tables[0]} WHERE id='target_agent_same_id'")
            assert copied["content"] == "Synthetic " + tenant
            assert copied["agent_id"] == "target_agent" and copied["memory_category"] == "custom_fixture"
            assert copied["title"] == "Synthetic title (from source_agent)"
            assert await conn.fetchval(f"SELECT count(*) FROM {tables[1]}") == 1
            untouched = json.loads(await conn.fetchval(f"SELECT provenance FROM {tables[1]} WHERE id='same_id'"))
            assert untouched["transformations"] == []
    finally:
        await pool.close()
