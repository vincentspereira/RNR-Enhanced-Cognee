"""Actual canonical storage preserves evidence and correction lineage."""
import os
import uuid

import asyncpg
import pytest
from cryptography.fernet import Fernet

from src.encryption_manager import EncryptionManager
from src.memory_contracts import MemoryEvidence
from src.memory_service import MemoryConflict, MemoryScope, MemoryService


@pytest.mark.parametrize("evidence", [
    {"kind": "verified_fact"}, {"verified": True}, {"authority": "operator"},
    {"confidence": float("nan")}, {"confidence": 1.1},
    {"source_uri": "https://user:password@example.test/source"},
    {"source_uri": "https://example.test/source?token=secret"},
    {"span_start": 2, "span_end": 1, "source_id": "source"},
    {"span_start": 1}, {"span_start": 0, "span_end": 2},
])
def test_source_declarations_cannot_claim_verification_or_invalid_spans(evidence):
    with pytest.raises(ValueError):
        MemoryEvidence.model_validate(evidence)


@pytest.mark.asyncio
async def test_encrypted_source_lineage_and_retraction_are_not_silently_rewritten():
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Set an explicitly disposable qualification database")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    scope = MemoryScope("q_" + uuid.uuid4().hex[:20], "evidence", "alice", "hermes")
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    evidence = {"kind": "inference", "source_id": "synthetic_source",
                "source_uri": "https://example.test/reference", "source_sha256": "a" * 64,
                "span_start": 10, "span_end": 25, "confidence": 0.6}
    try:
        await service.initialize()
        original = await service.remember(scope, "Synthetic proposed explanation", category="custom_project_kind",
                                          evidence=evidence, idempotency_key="source-one")
        assert original["evidence"]["declaration"] == evidence
        assert original["evidence"]["authority"] == "actor_submitted_unverified"
        assert original["category"] == "custom_project_kind"
        assert (await service.remember(scope, "Synthetic proposed explanation", category="custom_project_kind",
                                       evidence=evidence, idempotency_key="source-one"))["id"] == original["id"]
        with pytest.raises(MemoryConflict):
            await service.remember(scope, "Synthetic proposed explanation", category="custom_project_kind",
                                   evidence=evidence | {"kind": "fact"}, idempotency_key="source-one")
        async with pool.acquire() as conn:
            encrypted = await conn.fetchval("SELECT payload FROM shared_memory.records WHERE tenant=$1 AND id=$2",
                                            scope.tenant, original["id"])
            assert "synthetic_source" not in encrypted and "example.test" not in encrypted
        await service.correct(scope, original["id"], expected_version=1, content="Synthetic revised explanation")
        revised = await service.get(scope, original["id"])
        assert revised["evidence"]["source_review_required"]
        assert revised["evidence"]["prior_evidence_version"] == 1
        assert revised["evidence"]["declaration"]["kind"] == "unclassified"
        assert revised["provenance"]["supersedes_version"] == 1
        assert revised["provenance"]["previous_content_sha256"] == original["provenance"]["content_sha256"]
        assert revised["provenance"]["corrected_at"]
        await service.correct(scope, original["id"], expected_version=2, content="Synthetic explicitly sourced revision",
                              evidence={"kind": "decision", "source_id": "new_source"})
        revised = await service.get(scope, original["id"])
        assert revised["evidence"]["declaration"]["source_id"] == "new_source"
        await service.correct(scope, original["id"], expected_version=3, retract=True)
        with pytest.raises(MemoryConflict):
            await service.correct(scope, original["id"], expected_version=4, content="Accidental resurrection")
        assert (await service.recall(scope, "Synthetic"))["results"] == []
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_versions WHERE tenant=$1",
                                       scope.tenant) == 4
    finally:
        await pool.close()
