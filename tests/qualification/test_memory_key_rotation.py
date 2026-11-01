"""Real encrypted current/history rotation and failure rollback, using invented keys."""
import json
import os
import uuid

import asyncpg
import pytest
from cryptography.fernet import Fernet

from src.encryption_manager import EncryptionManager
from src.memory_keys import MemoryKeyring, canonical_cipher_from_environment
from src.memory_key_rotation import rewrap_project
from src.memory_service import MemoryScope, MemoryService


def test_named_keys_fail_closed_and_keep_legacy_reads(monkeypatch):
    old, new = (Fernet.generate_key().decode() for _ in range(2))
    legacy = EncryptionManager(master_key=old).encrypt("Synthetic legacy content")
    ring = MemoryKeyring({"next_key": new}, "next_key", legacy_key=old)
    assert ring.decrypt(legacy) == "Synthetic legacy content"
    named = ring.encrypt("Synthetic named content")
    assert named.startswith("enc2:kid:next_key:")
    assert ring.decrypt(named) == "Synthetic named content"
    with pytest.raises(RuntimeError):
        MemoryKeyring({"other": old}, "other").decrypt(named)
    with pytest.raises(RuntimeError):
        MemoryKeyring({"next_key": new}, "next_key").decrypt(legacy)
    with pytest.raises(ValueError):
        MemoryKeyring({"duplicate_one": old, "duplicate_two": old}, "duplicate_one")
    with pytest.raises(ValueError):
        ring.decrypt("Plaintext must never be accepted")
    # An explicitly configured but invalid ring never silently uses an old key.
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", old)
    monkeypatch.setenv("ENHANCED_MEMORY_KEYRING_JSON", "invalid JSON")
    with pytest.raises(ValueError, match="startup refused"):
        canonical_cipher_from_environment()


@pytest.mark.asyncio
async def test_rotation_keeps_history_scope_and_versions_and_rolls_back_failed_batch(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Select an explicitly disposable qualification database")
    old, new = (Fernet.generate_key().decode() for _ in range(2))
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    tenant = "q_" + uuid.uuid4().hex[:20]
    scope = MemoryScope(tenant, "rotation", "alice", "hermes")
    other = MemoryScope(tenant, "other", "alice", "hermes")
    legacy = MemoryService(pool, EncryptionManager(master_key=old))
    ring = MemoryKeyring({"current": new}, "current", legacy_key=old)
    try:
        await legacy.initialize()
        record = await legacy.remember(scope, "Synthetic initial source", idempotency_key="one")
        await legacy.correct(scope, record["id"], expected_version=1, content="Synthetic corrected source")
        untouched = await legacy.remember(other, "Synthetic other project", idempotency_key="other")
        async with pool.acquire() as conn:
            before = await conn.fetchval("SELECT payload FROM shared_memory.records WHERE tenant=$1 AND project=$2",
                                         tenant, scope.project)
        preview = await rewrap_project(pool, ring, tenant=tenant, project=scope.project, actor="operator")
        assert preview["payloads_needing_rewrap"] == 3 and preview["mode"] == "dry_run"
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT payload FROM shared_memory.records WHERE tenant=$1 AND project=$2",
                                       tenant, scope.project) == before
        encrypt = ring.encrypt
        count = 0

        def fail_after_first(plaintext):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("Synthetic mid-rotation failure")
            return encrypt(plaintext)

        monkeypatch.setattr(ring, "encrypt", fail_after_first)
        with pytest.raises(RuntimeError):
            await rewrap_project(pool, ring, tenant=tenant, project=scope.project, actor="operator", apply=True)
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT payload FROM shared_memory.records WHERE tenant=$1 AND project=$2",
                                       tenant, scope.project) == before
        monkeypatch.setattr(ring, "encrypt", encrypt)
        result = await rewrap_project(pool, ring, tenant=tenant, project=scope.project, actor="operator", apply=True)
        assert result["payloads_needing_rewrap"] == 3
        assert not result["keys_deleted"] and not result["backups_changed"]
        new_only = MemoryService(pool, MemoryKeyring({"current": new}, "current"))
        assert (await new_only.get(scope, record["id"]))["content"] == "Synthetic corrected source"
        assert (await new_only.get(scope, record["id"]))["version"] == 2
        with pytest.raises(RuntimeError):
            await new_only.get(other, untouched["id"])
        assert (await legacy.get(other, untouched["id"]))["content"] == "Synthetic other project"
        async with pool.acquire() as conn:
            history = await conn.fetch("SELECT payload FROM shared_memory.record_versions WHERE tenant=$1 AND project=$2 ORDER BY version",
                                       tenant, scope.project)
            assert [json.loads(new_only.cipher.decrypt(row["payload"]))["content"] for row in history] == [
                "Synthetic initial source", "Synthetic corrected source"]
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_audit WHERE tenant=$1 AND action='key_rewrapped:current'", tenant) == 1
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_outbox WHERE tenant=$1 AND project=$2", tenant, scope.project) == 2
        repeat = await rewrap_project(pool, ring, tenant=tenant, project=scope.project, actor="operator", apply=True)
        assert repeat["payloads_needing_rewrap"] == 0
    finally:
        await pool.close()
