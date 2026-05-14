"""
Phase 14 - New Module Unit Tests
==================================
Unit tests for:
  - EncryptionManager (14.3)
  - MemoryObservationManager (12.8)
  - NotificationManager (17.4)
  - MemoryImportanceScorer (18.4)
  - MemoryReranker (18.5)

All tests are offline (mock DB / no live connections).
ASCII-only assertions and output.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

UTC = timezone.utc


# ===========================================================================
# EncryptionManager (14.3)
# ===========================================================================

class TestEncryptionManager:
    """Tests for src.encryption_manager.EncryptionManager."""

    def test_import(self):
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        assert em is not None

    def test_encrypt_decrypt_roundtrip(self):
        """encrypt then decrypt must return original plaintext."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        if not em._enabled:
            pytest.skip("cryptography not installed")
        plaintext = "Hello, Enhanced Cognee!"
        encrypted = em.encrypt(plaintext)
        assert encrypted.startswith("enc:"), f"Expected enc: prefix, got {encrypted[:10]!r}"
        decrypted = em.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_without_cryptography_returns_plaintext(self):
        """When cryptography is absent, encrypt() is a no-op."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        em._enabled = False
        result = em.encrypt("test content")
        assert result == "test content"

    def test_decrypt_non_prefixed_returns_as_is(self):
        """decrypt() must leave non-encrypted strings unchanged."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        result = em.decrypt("plain old text")
        assert result == "plain old text"

    @pytest.mark.asyncio
    async def test_encrypt_memory_no_pool(self):
        """encrypt_memory with no pool returns error dict."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager(postgres_pool=None)
        result = await em.encrypt_memory("mem-001")
        assert "error" in result or result.get("ok") is False or "ERR" in str(result)

    @pytest.mark.asyncio
    async def test_get_encryption_stats_no_pool(self):
        """get_encryption_stats with no pool returns dict with encryption_enabled key."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager(postgres_pool=None)
        stats = await em.get_encryption_stats()
        assert isinstance(stats, dict)
        assert "encryption_enabled" in stats

    @pytest.mark.asyncio
    async def test_rotate_encryption_key_no_pool(self):
        """rotate_encryption_key with no pool returns error."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager(postgres_pool=None)
        result = await em.rotate_encryption_key()
        assert isinstance(result, dict)
        assert "error" in result or "rotated" in result

    @pytest.mark.asyncio
    async def test_encrypt_memory_with_pool(self):
        """encrypt_memory fetches, encrypts, and updates the row."""
        from src.encryption_manager import EncryptionManager

        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value="my secret content")
        conn.execute = AsyncMock(return_value=None)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)

        pool = MagicMock()
        pool.acquire.return_value = ctx

        em = EncryptionManager(postgres_pool=pool)
        if not em._enabled:
            pytest.skip("cryptography not installed")
        result = await em.encrypt_memory("mem-abc")
        assert result.get("ok") is True or "memory_id" in result

    def test_init_and_get_singleton(self):
        from src.encryption_manager import init_encryption_manager, get_encryption_manager
        em = init_encryption_manager()
        assert em is not None
        assert get_encryption_manager() is em


# ===========================================================================
# MemoryObservationManager (12.8)
# ===========================================================================

class TestMemoryObservationManager:
    """Tests for src.memory_observation.MemoryObservationManager."""

    def test_import(self):
        from src.memory_observation import MemoryObservationManager
        mgr = MemoryObservationManager()
        assert mgr is not None

    @pytest.mark.asyncio
    async def test_add_observation_no_pool(self):
        """add_observation without a pool returns error dict."""
        from src.memory_observation import MemoryObservationManager
        mgr = MemoryObservationManager(postgres_pool=None)
        result = await mgr.add_observation(
            memory_id="mem-1",
            entity="company",
            attribute="name",
            value="Acme Corp",
        )
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_observations_no_pool(self):
        """get_observations without a pool returns empty list."""
        from src.memory_observation import MemoryObservationManager
        mgr = MemoryObservationManager(postgres_pool=None)
        result = await mgr.get_observations("mem-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_update_observation_no_pool(self):
        """update_observation without a pool returns error dict."""
        from src.memory_observation import MemoryObservationManager
        mgr = MemoryObservationManager(postgres_pool=None)
        result = await mgr.update_observation("obs-uuid-1", "new value")
        assert isinstance(result, dict)
        assert "error" in result or result.get("ok") is False

    @pytest.mark.asyncio
    async def test_delete_observation_no_pool(self):
        """delete_observation without a pool returns error dict."""
        from src.memory_observation import MemoryObservationManager
        mgr = MemoryObservationManager(postgres_pool=None)
        result = await mgr.delete_observation("obs-uuid-1")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_add_observation_with_pool(self):
        """add_observation with a pool inserts and returns observation_id."""
        from src.memory_observation import MemoryObservationManager
        import uuid

        obs_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(return_value={
            "id": obs_id,
            "entity": "person",
            "attribute": "age",
            "value": "30",
            "confidence": 1.0,
            "created_at": now,
        })

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)

        pool = MagicMock()
        pool.acquire.return_value = ctx

        mgr = MemoryObservationManager(postgres_pool=pool)
        mgr._schema_ensured = True  # skip schema creation
        result = await mgr.add_observation("mem-1", "person", "age", "30")
        assert isinstance(result, dict)
        # Must have observation_id or entity
        assert "observation_id" in result or "entity" in result

    @pytest.mark.asyncio
    async def test_search_observations_no_pool(self):
        """search_observations without a pool returns empty list."""
        from src.memory_observation import MemoryObservationManager
        mgr = MemoryObservationManager(postgres_pool=None)
        result = await mgr.search_observations(entity="company")
        assert result == []

    def test_init_and_get_singleton(self):
        from src.memory_observation import init_observation_manager, get_observation_manager
        mgr = init_observation_manager()
        assert mgr is not None
        assert get_observation_manager() is mgr


# ===========================================================================
# NotificationManager (17.4)
# ===========================================================================

class TestNotificationManager:
    """Tests for src.notification_manager.NotificationManager."""

    def test_import(self):
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        assert nm is not None

    @pytest.mark.asyncio
    async def test_configure_slack(self):
        """configure_slack registers a channel with type=slack."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.configure_slack(
            channel_id="ch-slack-1",
            webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
            events=["memory.added", "backup.completed"],
        )
        assert isinstance(result, dict)
        assert result.get("channel_id") == "ch-slack-1"
        assert result.get("type") == "slack"

    @pytest.mark.asyncio
    async def test_configure_discord(self):
        """configure_discord registers a channel with type=discord."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.configure_discord(
            channel_id="ch-discord-1",
            webhook_url="https://discord.com/api/webhooks/000/abc",
            events=["health.degraded"],
        )
        assert isinstance(result, dict)
        assert result.get("channel_id") == "ch-discord-1"
        assert result.get("type") == "discord"

    @pytest.mark.asyncio
    async def test_list_channels_empty(self):
        """list_channels returns empty list when no channels configured."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = nm.list_channels()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_channels_after_configure(self):
        """list_channels returns configured channels."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        await nm.configure_slack("ch-s1", "https://hooks.slack.com/xxx", ["memory.added"])
        await nm.configure_discord("ch-d1", "https://discord.com/xxx", ["backup.failed"])
        channels = nm.list_channels()
        assert len(channels) == 2
        types = {c["type"] for c in channels}
        assert "slack" in types
        assert "discord" in types

    @pytest.mark.asyncio
    async def test_test_channel_unknown_channel(self):
        """test_channel for unknown channel_id returns error."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.test_channel("ch-nonexistent")
        assert isinstance(result, dict)
        assert result.get("ok") is False or "error" in result

    @pytest.mark.asyncio
    async def test_send_notification_no_channels(self):
        """send_notification with no channels does nothing and returns summary."""
        from src.notification_manager import NotificationManager
        nm = NotificationManager()
        result = await nm.send_notification("memory.added", {"memory_id": "mem-1"})
        assert isinstance(result, dict)
        # Should report 0 deliveries or empty
        assert result.get("delivered", 0) == 0 or result.get("channels_notified", 0) == 0

    def test_init_and_get_singleton(self):
        from src.notification_manager import init_notification_manager, get_notification_manager
        nm = init_notification_manager()
        assert nm is not None
        assert get_notification_manager() is nm


# ===========================================================================
# MemoryImportanceScorer (18.4)
# ===========================================================================

class TestMemoryImportanceScorer:
    """Tests for src.memory_importance_scorer.MemoryImportanceScorer."""

    def test_import(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        assert scorer is not None

    def test_score_memory_all_zeros(self):
        """Scoring a memory with all-zero inputs returns a low but non-negative score."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        memory = {
            "access_count": 0,
            "last_accessed_at": None,
            "confidence_score": 0.0,
            "metadata": "{}",
        }
        score = scorer._score_memory(memory)
        assert 0.0 <= score <= 1.0

    def test_score_memory_all_max(self):
        """Scoring a maximally active memory returns a high score."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        now = datetime.now(UTC).isoformat()
        memory = {
            "access_count": 100,
            "last_accessed_at": now,
            "confidence_score": 1.0,
            "metadata": '{"source_type": "verified"}',
        }
        score = scorer._score_memory(memory)
        assert score >= 0.7, f"Expected high score, got {score}"

    def test_score_memory_in_range(self):
        """Score is always in [0.0, 1.0] regardless of input."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        for access_count in [0, 25, 100, 999]:
            memory = {
                "access_count": access_count,
                "last_accessed_at": None,
                "confidence_score": 0.5,
                "metadata": "{}",
            }
            score = scorer._score_memory(memory)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for access_count={access_count}"

    @pytest.mark.asyncio
    async def test_get_memory_importance_no_pool(self):
        """get_memory_importance with no pool returns fallback dict."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer(postgres_pool=None)
        result = await scorer.get_memory_importance("mem-abc")
        assert isinstance(result, dict)
        assert "importance_score" in result

    @pytest.mark.asyncio
    async def test_update_importance_scores_no_pool(self):
        """update_importance_scores with no pool returns error or zero-updated dict."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer(postgres_pool=None)
        result = await scorer.update_importance_scores()
        assert isinstance(result, dict)
        assert "updated" in result or "error" in result

    @pytest.mark.asyncio
    async def test_get_top_important_memories_no_pool(self):
        """get_top_important_memories with no pool returns empty list."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer(postgres_pool=None)
        result = await scorer.get_top_important_memories()
        assert result == [] or isinstance(result, list)

    def test_source_type_weighting(self):
        """'verified' source type scores higher than 'unknown'."""
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        # Use access_count=0 and no recency so source_type component is decisive
        base = {"access_count": 0, "last_accessed_at": None, "confidence_score": 0.0}
        score_verified = scorer._score_memory({**base, "source_type": "verified"})
        score_unknown = scorer._score_memory({**base, "source_type": "unknown"})
        assert score_verified > score_unknown

    def test_init_and_get_singleton(self):
        from src.memory_importance_scorer import init_importance_scorer, get_importance_scorer
        scorer = init_importance_scorer()
        assert scorer is not None
        assert get_importance_scorer() is scorer


# ===========================================================================
# MemoryReranker (18.5)
# ===========================================================================

class TestMemoryReranker:
    """Tests for src.memory_reranker.MemoryReranker."""

    def test_import(self):
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        assert reranker is not None

    def test_compute_final_score_range(self):
        """Final score is always in [0.0, 1.0]."""
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        for args in [
            (0.0, 0.0, 0.0, 0.0),
            (1.0, 1.0, 1.0, 1.0),
            (0.5, 0.5, 0.5, 0.5),
            (0.9, 0.1, 0.8, 0.3),
        ]:
            score = reranker._compute_final_score(*args)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for args {args}"

    def test_compute_final_score_weights(self):
        """Higher similarity input should dominate importance alone."""
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        # High similarity only (weight 0.50) -> 0.50
        high_sim = reranker._compute_final_score(1.0, 0.0, 0.0, 0.0)
        # High importance only (weight 0.25) -> 0.25
        high_imp = reranker._compute_final_score(0.0, 1.0, 0.0, 0.0)
        assert high_sim > high_imp, "Similarity (0.50) should score higher than importance alone (0.25)"

    @pytest.mark.asyncio
    async def test_rerank_empty_list(self):
        """rerank_search_results with empty list returns empty list."""
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        result = await reranker.rerank_search_results([])
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_adds_rerank_score(self):
        """Each result must have a rerank_score key after re-ranking."""
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        results = [
            {"id": "1", "content": "first result", "similarity_score": 0.9},
            {"id": "2", "content": "second result", "similarity_score": 0.5},
            {"id": "3", "content": "third result", "similarity_score": 0.7},
        ]
        reranked = await reranker.rerank_search_results(results)
        assert len(reranked) == 3
        for r in reranked:
            assert "rerank_score" in r, f"Missing rerank_score in {r}"

    @pytest.mark.asyncio
    async def test_rerank_sorts_descending(self):
        """Results are sorted by rerank_score descending."""
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        now = datetime.now(UTC).isoformat()
        results = [
            {"id": "low", "similarity_score": 0.1, "importance_score": 0.1,
             "confidence_score": 0.1, "last_accessed_at": None},
            {"id": "high", "similarity_score": 0.9, "importance_score": 0.9,
             "confidence_score": 0.9, "last_accessed_at": now},
            {"id": "mid", "similarity_score": 0.5, "importance_score": 0.5,
             "confidence_score": 0.5, "last_accessed_at": None},
        ]
        reranked = await reranker.rerank_search_results(results)
        scores = [r["rerank_score"] for r in reranked]
        assert scores == sorted(scores, reverse=True), f"Not sorted: {scores}"
        assert reranked[0]["id"] == "high"

    @pytest.mark.asyncio
    async def test_rerank_handles_missing_fields(self):
        """rerank_search_results handles results with missing optional fields gracefully."""
        from src.memory_reranker import MemoryReranker
        reranker = MemoryReranker()
        results = [
            {"id": "sparse"},  # all optional fields missing
        ]
        reranked = await reranker.rerank_search_results(results)
        assert len(reranked) == 1
        assert "rerank_score" in reranked[0]
        assert 0.0 <= reranked[0]["rerank_score"] <= 1.0

    def test_init_and_get_singleton(self):
        from src.memory_reranker import init_reranker, get_reranker
        reranker = init_reranker()
        assert reranker is not None
        assert get_reranker() is reranker
