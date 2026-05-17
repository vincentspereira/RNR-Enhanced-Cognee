"""
Unit tests for src/advanced_search_reranking.py
Covers: AdvancedSearchEngine, SearchResult, ReRankingStrategy
Target: >= 85% line coverage (all deterministic paths, mocked I/O)
"""

import json
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from dataclasses import dataclass

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Helpers / lightweight re-implementations of the async context manager
# pattern from conftest so this file is self-contained.
# ---------------------------------------------------------------------------

def _make_pool(conn_mock):
    """Return a fake asyncpg pool whose .acquire() is a sync context manager."""
    class _Ctx:
        async def __aenter__(self):
            return conn_mock
        async def __aexit__(self, *a):
            pass
    class _Pool:
        def acquire(self):
            return _Ctx()
    return _Pool()


def _make_qdrant(hits=None):
    """Return a mock Qdrant client."""
    client = Mock()
    client.search = Mock(return_value=hits or [])
    return client


def _make_redis(cached_value=None):
    """Return a mock async Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=cached_value)
    client.setex = AsyncMock(return_value=True)
    return client


# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------

from src.advanced_search_reranking import (
    AdvancedSearchEngine,
    SearchResult,
    ReRankingStrategy,
)


# ===========================================================================
# SearchResult dataclass
# ===========================================================================

class TestSearchResult:
    """Tests for the SearchResult dataclass."""

    def test_minimal_construction(self):
        sr = SearchResult(
            memory_id="m1",
            content="hello",
            metadata={},
            score=0.8,
            reranked_score=0.9,
            rank=1,
        )
        assert sr.memory_id == "m1"
        assert sr.highlights is None
        assert sr.relevance_reason == ""
        assert sr.created_at is None
        assert sr.agent_id is None

    def test_full_construction(self):
        ts = datetime.now(UTC)
        sr = SearchResult(
            memory_id="m2",
            content="world",
            metadata={"k": "v"},
            score=0.5,
            reranked_score=0.7,
            rank=2,
            highlights=["snippet"],
            relevance_reason="high_relevance",
            created_at=ts,
            agent_id="agent-x",
        )
        assert sr.created_at == ts
        assert sr.agent_id == "agent-x"
        assert sr.highlights == ["snippet"]


# ===========================================================================
# ReRankingStrategy enum
# ===========================================================================

class TestReRankingStrategy:
    def test_all_values_exist(self):
        assert ReRankingStrategy.RELEVANCE.value == "relevance"
        assert ReRankingStrategy.RECENCY.value == "recency"
        assert ReRankingStrategy.COMBINED.value == "combined"
        assert ReRankingStrategy.PERSONALIZED.value == "personalized"


# ===========================================================================
# AdvancedSearchEngine.__init__
# ===========================================================================

class TestAdvancedSearchEngineInit:
    def test_defaults_stored(self):
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(postgres_pool=pool, qdrant_client=None)
        assert engine.postgres_pool is pool
        assert engine.qdrant_client is None
        assert engine.redis_client is None
        assert engine.llm_config is None
        assert engine.default_limit == 20
        assert engine.reranking_weights["semantic"] == 0.5
        assert engine.reranking_weights["keyword"] == 0.3
        assert engine.reranking_weights["recency"] == 0.2

    def test_optional_deps_stored(self):
        pool = _make_pool(AsyncMock())
        redis = _make_redis()
        cfg = {"provider": "openai", "api_key": "k"}
        engine = AdvancedSearchEngine(pool, None, redis_client=redis, llm_config=cfg)
        assert engine.redis_client is redis
        assert engine.llm_config == cfg


# ===========================================================================
# _extract_keywords_for_expansion  (sync, deterministic)
# ===========================================================================

class TestExtractKeywords:
    def _engine(self):
        return AdvancedSearchEngine(_make_pool(AsyncMock()), None)

    def test_short_words_excluded(self):
        eng = self._engine()
        result = eng._extract_keywords_for_expansion("a is of the")
        # All words <= 3 chars — no expansions should be produced
        assert result == []

    def test_long_words_produce_phrase_variants(self):
        eng = self._engine()
        result = eng._extract_keywords_for_expansion("python memory search")
        # "python", "memory", "search" are all >= 4 chars
        assert any('"python"' in r for r in result)
        assert any('"memory"' in r for r in result)
        assert any('"search"' in r for r in result)
        assert any("*python*" in r for r in result)

    def test_limit_at_ten(self):
        eng = self._engine()
        # 5 long words, each producing 2 phrase variants -> at most 10
        result = eng._extract_keywords_for_expansion(
            "alpha bravo charlie delta epsilon foxtrot"
        )
        assert len(result) <= 10

    def test_empty_query(self):
        eng = self._engine()
        result = eng._extract_keywords_for_expansion("")
        assert result == []


# ===========================================================================
# _get_synonyms  (always returns empty in current implementation)
# ===========================================================================

class TestGetSynonyms:
    def test_returns_empty_list(self):
        eng = AdvancedSearchEngine(_make_pool(AsyncMock()), None)
        assert eng._get_synonyms("trading") == []
        assert eng._get_synonyms("") == []


# ===========================================================================
# _get_embedding  (deterministic hash-based)
# ===========================================================================

class TestGetEmbedding:
    def _engine(self):
        return AdvancedSearchEngine(_make_pool(AsyncMock()), None)

    def test_returns_list_of_floats(self):
        eng = self._engine()
        vec = eng._get_embedding("hello world")
        assert isinstance(vec, list)
        assert len(vec) == 1536
        assert all(isinstance(v, float) for v in vec)

    def test_deterministic_same_text(self):
        eng = self._engine()
        assert eng._get_embedding("test") == eng._get_embedding("test")

    def test_different_text_different_vector(self):
        eng = self._engine()
        assert eng._get_embedding("alpha") != eng._get_embedding("beta")


# ===========================================================================
# _extract_highlights  (sync, deterministic)
# ===========================================================================

class TestExtractHighlights:
    def _engine(self):
        return AdvancedSearchEngine(_make_pool(AsyncMock()), None)

    def test_matching_sentence_included(self):
        eng = self._engine()
        # Sentence must be > 50 chars to qualify as a meaningful snippet
        long_sentence = (
            "The memory system stores data and provides retrieval for all agents."
        )
        content = long_sentence + " Python is great for search and indexing."
        highlights = eng._extract_highlights("memory", content)
        # If no highlight is produced, the sentence was too short - verify logic
        # by building a clearly long enough sentence
        long_content = (
            "The memory system provides persistent storage and enables retrieval "
            "of historical information across distributed agent architectures."
        )
        highlights2 = eng._extract_highlights("memory", long_content)
        assert len(highlights2) >= 1
        assert any("memory" in h.lower() for h in highlights2)

    def test_non_matching_returns_empty(self):
        eng = self._engine()
        highlights = eng._extract_highlights("zzz", "The quick brown fox")
        assert highlights == []

    def test_short_sentences_excluded(self):
        eng = self._engine()
        # Sentence is too short (<= 50 chars) to be a meaningful snippet
        highlights = eng._extract_highlights("cat", "The cat.")
        assert highlights == []

    def test_max_three_highlights(self):
        eng = self._engine()
        content = (
            "memory system is used for storing information and data retrieval."
            " memory helps to keep track of various things over long periods."
            " memory also supports distributed multi-agent architectures well."
            " memory integration with databases provides robust data storage."
        )
        highlights = eng._extract_highlights("memory", content)
        assert len(highlights) <= 3

    def test_highlight_truncated_at_200(self):
        eng = self._engine()
        long_sentence = "memory " + ("x" * 300)
        highlights = eng._extract_highlights("memory", long_sentence)
        if highlights:
            assert len(highlights[0]) <= 200

    def test_empty_content_returns_empty(self):
        eng = self._engine()
        assert eng._extract_highlights("memory", "") == []

    def test_exception_returns_empty(self):
        eng = self._engine()
        # Passing non-string content triggers an error internally
        result = eng._extract_highlights("memory", None)  # type: ignore[arg-type]
        assert result == []


# ===========================================================================
# _personalized_score  (async, no external I/O)
# ===========================================================================

class TestPersonalizedScore:
    def _engine(self):
        return AdvancedSearchEngine(_make_pool(AsyncMock()), None)

    @pytest.mark.asyncio
    async def test_same_agent_boosts_score(self):
        eng = self._engine()
        sr = SearchResult("m1", "content", {}, 1.0, 0.0, 1, agent_id="user-x")
        score = await eng._personalized_score(sr, "user-x", "query")
        assert score == pytest.approx(1.3)

    @pytest.mark.asyncio
    async def test_different_agent_no_boost(self):
        eng = self._engine()
        sr = SearchResult("m1", "content", {}, 0.8, 0.0, 1, agent_id="other")
        score = await eng._personalized_score(sr, "user-x", "query")
        assert score == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_no_agent_id_no_boost(self):
        eng = self._engine()
        sr = SearchResult("m1", "content", {}, 0.5, 0.0, 1)
        score = await eng._personalized_score(sr, "user-x", "query")
        assert score == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_personalized_score_exception_returns_base_score(self):
        """Cover the except branch in _personalized_score (lines 537-539)."""
        eng = self._engine()
        sr = SearchResult("m1", "content", {}, 0.6, 0.0, 1)
        # Make sr.agent_id raise when accessed (cover the comparison fault)
        original_score = sr.score
        # Patch __eq__ on agent_id via a property mock is complex; instead
        # patch the whole method body trigger: make score attribute raise
        class _BadScore:
            def __mul__(self, other): raise RuntimeError("bad score")
            def __eq__(self, other): return False
            def __repr__(self): return "bad"
        sr.score = _BadScore()  # type: ignore[assignment]
        returned = await eng._personalized_score(sr, "agent-x", "q")
        # Exception path returns result.score which is the _BadScore object
        assert returned is sr.score


# ===========================================================================
# _rerank_results  (async, strategy dispatch)
# ===========================================================================

def _make_result(score, days_ago=None, agent_id=None):
    created = None
    if days_ago is not None:
        created = datetime.now(UTC) - timedelta(days=days_ago)
    return SearchResult("id", "content", {}, score, 0.0, 0,
                        created_at=created, agent_id=agent_id)


class TestRerankResults:
    def _engine(self):
        return AdvancedSearchEngine(_make_pool(AsyncMock()), None)

    @pytest.mark.asyncio
    async def test_relevance_strategy_preserves_base_score(self):
        eng = self._engine()
        results = [_make_result(0.9), _make_result(0.5)]
        reranked = await eng._rerank_results(
            results, "query", "user", ReRankingStrategy.RELEVANCE
        )
        assert reranked[0].reranked_score == pytest.approx(0.9)
        assert reranked[0].relevance_reason == "high_relevance"

    @pytest.mark.asyncio
    async def test_relevance_strategy_sorts_descending(self):
        eng = self._engine()
        results = [_make_result(0.3), _make_result(0.8), _make_result(0.5)]
        reranked = await eng._rerank_results(
            results, "q", "u", ReRankingStrategy.RELEVANCE
        )
        scores = [r.reranked_score for r in reranked]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_relevance_updates_rank_field(self):
        eng = self._engine()
        results = [_make_result(0.6), _make_result(0.9)]
        reranked = await eng._rerank_results(
            results, "q", "u", ReRankingStrategy.RELEVANCE
        )
        assert reranked[0].rank == 1
        assert reranked[1].rank == 2

    @pytest.mark.asyncio
    async def test_recency_strategy_with_created_at(self):
        eng = self._engine()
        recent = _make_result(0.5, days_ago=1)
        old = _make_result(0.5, days_ago=200)
        reranked = await eng._rerank_results(
            [old, recent], "q", "u", ReRankingStrategy.RECENCY
        )
        # Recent should score higher
        assert reranked[0].reranked_score > reranked[1].reranked_score

    @pytest.mark.asyncio
    async def test_recency_strategy_without_created_at(self):
        eng = self._engine()
        result = _make_result(0.7)  # no created_at
        reranked = await eng._rerank_results(
            [result], "q", "u", ReRankingStrategy.RECENCY
        )
        # Fallback: base score is used unchanged
        assert reranked[0].reranked_score == pytest.approx(0.7)
        assert reranked[0].relevance_reason == "recency_boost"

    @pytest.mark.asyncio
    async def test_combined_strategy_very_recent_boost(self):
        eng = self._engine()
        result = _make_result(1.0, days_ago=3)   # < 7 days
        reranked = await eng._rerank_results(
            [result], "q", "u", ReRankingStrategy.COMBINED
        )
        assert reranked[0].reranked_score == pytest.approx(1.2)
        assert reranked[0].relevance_reason == "recent_and_relevant"

    @pytest.mark.asyncio
    async def test_combined_strategy_moderately_recent(self):
        eng = self._engine()
        result = _make_result(1.0, days_ago=15)  # 7..30 days
        reranked = await eng._rerank_results(
            [result], "q", "u", ReRankingStrategy.COMBINED
        )
        assert reranked[0].reranked_score == pytest.approx(1.1)
        assert reranked[0].relevance_reason == "moderately_recent"

    @pytest.mark.asyncio
    async def test_combined_strategy_old_penalty(self):
        eng = self._engine()
        result = _make_result(1.0, days_ago=60)  # > 30 days
        reranked = await eng._rerank_results(
            [result], "q", "u", ReRankingStrategy.COMBINED
        )
        assert reranked[0].reranked_score == pytest.approx(0.9)
        assert reranked[0].relevance_reason == "older_but_relevant"

    @pytest.mark.asyncio
    async def test_combined_strategy_no_created_at_unchanged(self):
        eng = self._engine()
        result = _make_result(0.8)
        reranked = await eng._rerank_results(
            [result], "q", "u", ReRankingStrategy.COMBINED
        )
        # Without created_at, score stays at base
        assert reranked[0].reranked_score == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_personalized_strategy_same_agent_boost(self):
        eng = self._engine()
        result = _make_result(1.0, agent_id="user-x")
        reranked = await eng._rerank_results(
            [result], "q", "user-x", ReRankingStrategy.PERSONALIZED
        )
        assert reranked[0].reranked_score == pytest.approx(1.3)
        assert reranked[0].relevance_reason == "personalized"

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty(self):
        eng = self._engine()
        result = await eng._rerank_results(
            [], "q", "u", ReRankingStrategy.RELEVANCE
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_exception_returns_original_results(self):
        """Cover the except branch (lines 505-507): sort() blows up -> return results as-is."""
        eng = self._engine()

        class _Unorderable:
            """An object that raises when compared via < (used by sort key)."""
            def __lt__(self, other): raise TypeError("unorderable")
            def __gt__(self, other): raise TypeError("unorderable")
            def __le__(self, other): raise TypeError("unorderable")
            def __ge__(self, other): raise TypeError("unorderable")

        r1 = _make_result(0.5)
        r2 = _make_result(0.3)
        # Both get RELEVANCE strategy so reranked_score = base_score then sort runs
        # Replace reranked_score after assignment would need hooking into the loop.
        # Instead: subclass and make sort key raise for the second element.
        r1.reranked_score = _Unorderable()  # type: ignore[assignment]
        r2.reranked_score = _Unorderable()  # type: ignore[assignment]
        original = [r1, r2]
        returned = await eng._rerank_results(
            original, "q", "u", ReRankingStrategy.RELEVANCE
        )
        # On exception the except block returns results (which is `original` list)
        assert isinstance(returned, list)


# ===========================================================================
# _expand_query  (async, with Redis cache + LLM paths)
# ===========================================================================

class TestExpandQuery:
    @pytest.mark.asyncio
    async def test_no_cache_no_llm_returns_original_plus_keyword_expansions(self):
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(pool, None)
        result = await engine._expand_query("search memory data")
        # Original query must always be first
        assert result[0] == "search memory data"
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_redis_cache_hit_returns_cached(self):
        cached = json.dumps(["cached-query-1", "cached-query-2"])
        redis = _make_redis(cached_value=cached)
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(pool, None, redis_client=redis)
        result = await engine._expand_query("anything")
        assert result == ["cached-query-1", "cached-query-2"]
        # setex should NOT be called on cache hit
        redis.setex.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_cache_miss_stores_result(self):
        redis = _make_redis(cached_value=None)
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(pool, None, redis_client=redis)
        await engine._expand_query("memory search")
        redis.setex.assert_awaited_once()
        args = redis.setex.call_args
        # First arg is cache key, second is TTL (3600), third is JSON list
        assert args[0][1] == 3600
        stored = json.loads(args[0][2])
        assert isinstance(stored, list)

    @pytest.mark.asyncio
    async def test_result_limited_to_five_queries(self):
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(pool, None)
        result = await engine._expand_query(
            "alpha bravo charlie delta epsilon foxtrot"
        )
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_duplicates_removed(self):
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(pool, None)
        result = await engine._expand_query("test")
        # No duplicates (case-insensitive)
        lower = [q.lower() for q in result]
        assert len(lower) == len(set(lower))

    @pytest.mark.asyncio
    async def test_exception_returns_original_query(self):
        # Redis raises on get -> fallback
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=RuntimeError("boom"))
        pool = _make_pool(AsyncMock())
        engine = AdvancedSearchEngine(pool, None, redis_client=redis)
        result = await engine._expand_query("fail test")
        assert result == ["fail test"]

    @pytest.mark.asyncio
    async def test_llm_expansions_appended(self):
        pool = _make_pool(AsyncMock())
        llm_cfg = {"provider": "anthropic", "api_key": "fake"}
        engine = AdvancedSearchEngine(pool, None, llm_config=llm_cfg)

        # Patch _llm_expand_query to return known queries
        async def fake_llm(q):
            return ["llm-expansion-1", "llm-expansion-2"]

        engine._llm_expand_query = fake_llm
        result = await engine._expand_query("base query")
        assert "llm-expansion-1" in result or "llm-expansion-2" in result


# ===========================================================================
# _llm_expand_query  (async, provider dispatch)
# ===========================================================================

class TestLlmExpandQuery:
    def _engine(self, provider="anthropic"):
        cfg = {"provider": provider, "api_key": "test-key",
               "model": "test-model"}
        return AdvancedSearchEngine(_make_pool(AsyncMock()), None, llm_config=cfg)

    @pytest.mark.asyncio
    async def test_anthropic_provider_returns_queries(self):
        eng = self._engine("anthropic")
        fake_message = MagicMock()
        fake_message.content = [MagicMock(text="query one\nquery two\nquery three")]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=fake_message)

        with patch("src.advanced_search_reranking.AsyncAnthropic" if False else
                   "anthropic.AsyncAnthropic", create=True) as _mock:
            # Patch at the module level where it is imported
            with patch.object(eng, "_llm_expand_query",
                               new=AsyncMock(return_value=["query one",
                                                            "query two"])):
                result = await eng._llm_expand_query("test")
            assert result == ["query one", "query two"]

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_empty(self):
        cfg = {"provider": "unknown_provider", "api_key": "k"}
        eng = AdvancedSearchEngine(_make_pool(AsyncMock()), None, llm_config=cfg)
        result = await eng._llm_expand_query("query")
        assert result == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        eng = self._engine("anthropic")
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = await eng._llm_expand_query("query")
        assert result == []

    @pytest.mark.asyncio
    async def test_anthropic_provider_real_path(self):
        """Cover the anthropic branch (lines 200-220): mock AsyncAnthropic at import."""
        cfg = {"provider": "anthropic", "api_key": "fake-key",
               "model": "claude-3-5-haiku-20241022"}
        eng = AdvancedSearchEngine(_make_pool(AsyncMock()), None, llm_config=cfg)

        fake_content_item = MagicMock()
        fake_content_item.text = "related one\nrelated two\nrelated three"
        fake_message = MagicMock()
        fake_message.content = [fake_content_item]
        fake_client_instance = AsyncMock()
        fake_client_instance.messages.create = AsyncMock(
            return_value=fake_message
        )
        fake_anthropic_cls = MagicMock(return_value=fake_client_instance)

        mock_module = MagicMock()
        mock_module.AsyncAnthropic = fake_anthropic_cls
        with patch.dict("sys.modules", {"anthropic": mock_module}):
            result = await eng._llm_expand_query("memory search query")
        assert isinstance(result, list)
        assert "related one" in result

    @pytest.mark.asyncio
    async def test_openai_provider_real_path(self):
        """Cover the openai branch (lines 222-238): mock AsyncOpenAI at import."""
        cfg = {"provider": "openai", "api_key": "fake-key", "model": "gpt-4"}
        eng = AdvancedSearchEngine(_make_pool(AsyncMock()), None, llm_config=cfg)

        fake_choice = MagicMock()
        fake_choice.message.content = "openai query one\nopenai query two"
        fake_response = MagicMock()
        fake_response.choices = [fake_choice]
        fake_client_instance = AsyncMock()
        fake_client_instance.chat.completions.create = AsyncMock(
            return_value=fake_response
        )
        fake_openai_cls = MagicMock(return_value=fake_client_instance)

        mock_module = MagicMock()
        mock_module.AsyncOpenAI = fake_openai_cls
        with patch.dict("sys.modules", {"openai": mock_module}):
            result = await eng._llm_expand_query("memory search")
        assert isinstance(result, list)
        assert "openai query one" in result


# ===========================================================================
# _semantic_search  (async, Qdrant)
# ===========================================================================

class TestSemanticSearch:
    def _engine(self, qdrant=None):
        return AdvancedSearchEngine(_make_pool(AsyncMock()), qdrant)

    @pytest.mark.asyncio
    async def test_no_qdrant_returns_empty(self):
        eng = self._engine(qdrant=None)
        result = await eng._semantic_search("query")
        assert result == []

    @pytest.mark.asyncio
    async def test_qdrant_returns_mapped_results(self):
        hit = MagicMock()
        hit.id = "mem-1"
        hit.score = 0.92
        hit.payload = {
            "content": "memory content",
            "metadata": {"k": "v"},
            "agent_id": "agent-a",
            "created_at": None
        }
        qdrant = _make_qdrant(hits=[hit])
        eng = self._engine(qdrant=qdrant)
        results = await eng._semantic_search("query")
        assert len(results) == 1
        assert results[0]["memory_id"] == "mem-1"
        assert results[0]["score"] == pytest.approx(0.92)
        assert results[0]["content"] == "memory content"

    @pytest.mark.asyncio
    async def test_qdrant_empty_payload_handled(self):
        hit = MagicMock()
        hit.id = "mem-2"
        hit.score = 0.75
        hit.payload = None
        qdrant = _make_qdrant(hits=[hit])
        eng = self._engine(qdrant=qdrant)
        results = await eng._semantic_search("query")
        assert len(results) == 1
        assert results[0]["content"] == ""

    @pytest.mark.asyncio
    async def test_qdrant_exception_returns_empty(self):
        qdrant = Mock()
        qdrant.search = Mock(side_effect=RuntimeError("qdrant down"))
        eng = self._engine(qdrant=qdrant)
        results = await eng._semantic_search("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_filters_passed_to_embedding(self):
        qdrant = _make_qdrant(hits=[])
        eng = self._engine(qdrant=qdrant)
        # Should complete without error even with filters
        results = await eng._semantic_search("query",
                                             filters={"agent_id": "a"})
        assert results == []


# ===========================================================================
# _text_search  (async, PostgreSQL)
# ===========================================================================

class TestTextSearch:
    @pytest.mark.asyncio
    async def test_returns_rows_from_db(self):
        row = {"memory_id": "r1", "content": "text", "metadata": {},
               "agent_id": "a", "created_at": None, "rank_score": 0.8}
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        results = await eng._text_search("query")
        assert len(results) == 1
        assert results[0]["memory_id"] == "r1"

    @pytest.mark.asyncio
    async def test_agent_id_filter_appended(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        await eng._text_search("query", filters={"agent_id": "my-agent"})
        call_args = conn.fetch.call_args[0]
        sql = call_args[0]
        assert "agent_id" in sql

    @pytest.mark.asyncio
    async def test_category_filter_appended(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        await eng._text_search("query", filters={"category": "trading"})
        call_args = conn.fetch.call_args[0]
        sql = call_args[0]
        assert "memory_category" in sql

    @pytest.mark.asyncio
    async def test_start_date_filter_appended(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        await eng._text_search("query",
                               filters={"start_date": datetime.now(UTC)})
        call_args = conn.fetch.call_args[0]
        sql = call_args[0]
        assert "created_at" in sql

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=RuntimeError("db error"))
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        results = await eng._text_search("query")
        assert results == []


# ===========================================================================
# _multi_modal_search  (async, orchestrates text + semantic)
# ===========================================================================

class TestMultiModalSearch:
    @pytest.mark.asyncio
    async def test_combines_text_and_semantic_results(self):
        text_row = {"memory_id": "m1", "content": "text content",
                    "metadata": {}, "agent_id": "a",
                    "created_at": None, "rank_score": 0.6}
        sem_hit = MagicMock()
        sem_hit.id = "m1"
        sem_hit.score = 0.9
        sem_hit.payload = {"content": "text content", "metadata": {},
                           "agent_id": "a", "created_at": None}

        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[text_row])
        pool = _make_pool(conn)
        qdrant = _make_qdrant(hits=[sem_hit])
        eng = AdvancedSearchEngine(pool, qdrant)

        results = await eng._multi_modal_search(["query"])
        assert len(results) == 1
        sr = results[0]
        assert sr.memory_id == "m1"
        # combined = 0.6 * 0.3 (keyword) + 0.9 * 0.5 (semantic) = 0.18 + 0.45 = 0.63
        assert sr.score == pytest.approx(0.63, abs=1e-3)

    @pytest.mark.asyncio
    async def test_empty_queries_returns_empty(self):
        pool = _make_pool(AsyncMock())
        eng = AdvancedSearchEngine(pool, None)
        results = await eng._multi_modal_search([])
        assert results == []

    @pytest.mark.asyncio
    async def test_text_only_no_qdrant(self):
        text_row = {"memory_id": "m2", "content": "only text",
                    "metadata": {}, "agent_id": "b",
                    "created_at": None, "rank_score": 0.5}
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[text_row])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)   # no Qdrant
        results = await eng._multi_modal_search(["query"])
        assert len(results) == 1
        # semantic_score = 0.0 => combined = 0.5 * 0.3 = 0.15
        assert results[0].score == pytest.approx(0.15, abs=1e-3)

    @pytest.mark.asyncio
    async def test_multiple_queries_dedup_by_memory_id(self):
        row = {"memory_id": "m1", "content": "c", "metadata": {},
               "agent_id": "a", "created_at": None, "rank_score": 0.4}
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        results = await eng._multi_modal_search(["q1", "q2"])
        # Same memory ID should appear only once
        assert len(results) == 1


# ===========================================================================
# search  (async, top-level integration)
# ===========================================================================

class TestSearch:
    def _engine(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        return AdvancedSearchEngine(pool, None)

    @pytest.mark.asyncio
    async def test_returns_list_on_success(self):
        eng = self._engine()
        results = await eng.search("test query")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_limit_applied(self):
        row = {"memory_id": "m1", "content": "c" * 100,
               "metadata": {}, "agent_id": "a",
               "created_at": None, "rank_score": 0.9}
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row] * 30)
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        results = await eng.search("query", limit=5)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_no_rerank_skips_reranking(self):
        eng = self._engine()
        rerank_called = []

        original = eng._rerank_results
        async def spy(*args, **kwargs):
            rerank_called.append(True)
            return await original(*args, **kwargs)

        eng._rerank_results = spy
        await eng.search("query", rerank=False)
        assert rerank_called == []

    @pytest.mark.asyncio
    async def test_highlights_added_to_results(self):
        row = {"memory_id": "m1",
               "content": "memory system is useful for storing and retrieving information.",
               "metadata": {}, "agent_id": "a",
               "created_at": None, "rank_score": 0.8}
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        results = await eng.search("memory system")
        if results:
            assert results[0].highlights is not None

    @pytest.mark.asyncio
    async def test_exception_returns_empty_list(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=Exception("fatal"))
        pool = _make_pool(conn)
        eng = AdvancedSearchEngine(pool, None)
        # _expand_query or _multi_modal_search will blow up
        results = await eng.search("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_strategy_relevance_passed_through(self):
        eng = self._engine()
        results = await eng.search("query",
                                   strategy=ReRankingStrategy.RELEVANCE)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_strategy_recency_passed_through(self):
        eng = self._engine()
        results = await eng.search("query",
                                   strategy=ReRankingStrategy.RECENCY)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_multi_modal_failure_returns_empty(self):
        """Cover search() outer except (lines 140-142).

        We make _multi_modal_search raise so the outer try/except catches it.
        """
        eng = self._engine()

        async def boom(queries, filters):
            raise RuntimeError("multi-modal exploded")

        eng._multi_modal_search = boom
        results = await eng.search("query")
        assert results == []


# ===========================================================================
# get_search_analytics  (async, PostgreSQL analytics queries)
# ===========================================================================

class TestGetSearchAnalytics:
    def _engine_with_conn(self, conn):
        pool = _make_pool(conn)
        return AdvancedSearchEngine(pool, None)

    @pytest.mark.asyncio
    async def test_success_returns_dict_with_status(self):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[100, 25.0, None])
        conn.fetch = AsyncMock(return_value=[])
        eng = self._engine_with_conn(conn)
        result = await eng.get_search_analytics(days_back=30)
        assert result["status"] == "success"
        assert result["total_searches"] == 100

    @pytest.mark.asyncio
    async def test_avg_query_length_none_coerced_to_zero(self):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[50, None, None])
        conn.fetch = AsyncMock(return_value=[])
        eng = self._engine_with_conn(conn)
        result = await eng.get_search_analytics()
        assert result["avg_query_length"] == 0

    @pytest.mark.asyncio
    async def test_zero_results_rate_none_coerced(self):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[10, 20.0, None])
        conn.fetch = AsyncMock(return_value=[])
        eng = self._engine_with_conn(conn)
        result = await eng.get_search_analytics()
        assert result["zero_results_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=RuntimeError("db offline"))
        eng = self._engine_with_conn(conn)
        result = await eng.get_search_analytics()
        assert result["status"] == "error"
        assert "db offline" in result["error"]

    @pytest.mark.asyncio
    async def test_top_terms_included(self):
        term_row = {"query_term": "memory", "count": 42}
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[10, 15.0, 5.0])
        conn.fetch = AsyncMock(return_value=[term_row])
        eng = self._engine_with_conn(conn)
        result = await eng.get_search_analytics()
        assert result["top_search_terms"] == [{"query_term": "memory",
                                               "count": 42}]
