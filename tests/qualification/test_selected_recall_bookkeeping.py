"""Internal IDs/vectors must not make an admitted selected memory unreadable."""
import json
import os
import types
import uuid

import asyncpg
from cryptography.fernet import Fernet
import pytest

from src.encryption_manager import EncryptionManager
from src.memory_service import MemoryService, MemoryScope, MemoryClarificationRequired
from src.security.memory_admission import contains_private_details, contains_private_memory_details


class FixtureEmbedding:
    model = "synthetic_precision_vector"

    async def embed(self, content):
        return [.12345678901234567, .75]


@pytest.mark.asyncio
async def test_selected_get_list_semantic_recall_and_history_ignore_only_internal_fields(monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Choose an explicitly disposable PostgreSQL database")
    tenant = "privacy_"+uuid.uuid4().hex[:20]
    identifiers = iter([uuid.UUID("b8ece469-4102-4246-a532-360fded131d3"),
                        uuid.UUID("b8ece469-4102-4246-a532-360fded131d4")])
    monkeypatch.setattr("src.memory_service.uuid", types.SimpleNamespace(uuid4=lambda: next(identifiers)))
    assert contains_private_details(json.dumps({"id": "b8ece469-4102-4246-a532-360fded131d3"}))
    assert contains_private_details(json.dumps({"embedding": await FixtureEmbedding().embed("fixture")}))
    assert not contains_private_memory_details({"id": "b8ece469-4102-4246-a532-360fded131d3",
                                               "embedding": await FixtureEmbedding().embed("fixture"), "content": "Use cedar."})
    assert contains_private_memory_details({"metadata": {"id": "Contact person@example.test"}})
    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()), FixtureEmbedding())
    selected = MemoryScope(tenant, "project", "owner", "hermes", selected_capture=True)
    manual = MemoryScope(tenant, "project", "owner", "hermes")
    try:
        await service.initialize()
        record = await service.remember(selected, "Use cedar for the synthetic deployment.", idempotency_key="safe")
        assert (await service.get(selected, record["id"]))["content"] == record["content"]
        assert [r["id"] for r in (await service.list_records(selected))["results"]] == [record["id"]]
        recall = await service.recall(selected, "deployment")
        assert recall["retrieval"] == "semantic" and [r["id"] for r in recall["results"]] == [record["id"]]
        assert not (await service.history(selected, record["id"]))["versions"][0].get("content_withheld")
        personal = await service.remember(manual, "Contact person@example.test", idempotency_key="manual-private")
        with pytest.raises(MemoryClarificationRequired):
            await service.get(selected, personal["id"])
        assert [r["id"] for r in (await service.list_records(selected))["results"]] == [record["id"]]
        assert [r["id"] for r in (await service.recall(selected, "deployment"))["results"]] == [record["id"]]
        assert (await service.history(selected, personal["id"]))["versions"][0]["content_withheld"]
    finally:
        await pool.close()
