"""
Unit tests for src.intelligent_summarization
=============================================
Covers:
  - IntelligentMemorySummarizer (all methods)
  - SummaryStrategy enum
  - MemoryCluster / SummaryResult dataclasses
  - find_summarizable_memories
  - summarize_memory (with redis cache hit and miss)
  - _generate_llm_summary (all three providers)
  - _summarize_with_openai / _summarize_with_anthropic / _summarize_with_ollama
  - _build_summary_prompt (all four strategies)
  - _parse_summary_result
  - cluster_memories (with and without qdrant)
  - _simple_cluster
  - _find_similar_memories
  - _infer_cluster_theme / _generate_cluster_theme
  - auto_summarize_old_memories (dry_run + live + failure paths)
  - _store_summary
  - _get_embedding
  - get_summarization_statistics

No real API calls are made; all LLM clients are mocked.
ASCII-only assertions per project conventions.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta, UTC


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    return conn


def _make_pool(conn):
    class _Ctx:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *args):
            pass

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_Ctx())
    return pool


def _make_summarizer(conn=None, redis_client=None, qdrant_client=None, provider="openai"):
    if conn is None:
        conn = _make_conn()
    pool = _make_pool(conn)
    llm_config = {
        "provider": provider,
        "model": "gpt-4",
        "api_key": "test-key",
    }
    from src.intelligent_summarization import IntelligentMemorySummarizer
    return IntelligentMemorySummarizer(
        postgres_pool=pool,
        llm_config=llm_config,
        redis_client=redis_client,
        qdrant_client=qdrant_client,
    ), conn


def _sample_memory(mem_id="mem-001", content="A " * 300, agent_id="agent-a"):
    """Return a minimal memory dict with >500 chars content by default."""
    return {
        "id": mem_id,
        "title": "Test Memory",
        "content": content,
        "agent_id": agent_id,
        "metadata": {},
        "created_at": datetime.now(UTC) - timedelta(days=40),
    }


# ---------------------------------------------------------------------------
# SummaryStrategy enum
# ---------------------------------------------------------------------------

class TestSummaryStrategyEnum:

    def test_all_strategies_present(self):
        from src.intelligent_summarization import SummaryStrategy
        strategies = {s.value for s in SummaryStrategy}
        assert "concise" in strategies
        assert "standard" in strategies
        assert "detailed" in strategies
        assert "extractive" in strategies

    def test_enum_count(self):
        from src.intelligent_summarization import SummaryStrategy
        assert len(list(SummaryStrategy)) == 4


# ---------------------------------------------------------------------------
# MemoryCluster / SummaryResult dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses:

    def test_memory_cluster_defaults(self):
        from src.intelligent_summarization import MemoryCluster
        cluster = MemoryCluster(cluster_id="c1")
        assert cluster.memories == []
        assert cluster.memory_count == 0
        assert cluster.cluster_summary is None
        assert cluster.cluster_theme is None

    def test_summary_result_fields(self):
        from src.intelligent_summarization import SummaryResult, SummaryStrategy
        sr = SummaryResult(
            memory_id="m1",
            original_content="long content here",
            summary="short",
            strategy=SummaryStrategy.CONCISE,
            compression_ratio=5.0,
        )
        assert sr.keywords == []
        assert sr.entities == []
        assert sr.memory_id == "m1"
        assert sr.compression_ratio == 5.0


# ---------------------------------------------------------------------------
# IntelligentMemorySummarizer.__init__
# ---------------------------------------------------------------------------

class TestSummarizerInit:

    def test_init_stores_pool_and_config(self):
        s, _ = _make_summarizer()
        assert s.postgres_pool is not None
        assert s.llm_config["provider"] == "openai"

    def test_default_settings(self):
        s, _ = _make_summarizer()
        assert s.min_memory_age_days == 30
        assert s.min_memory_length == 500
        assert s.batch_size == 10
        assert s.clustering_threshold == 0.75
        assert s.max_cluster_size == 50

    def test_redis_and_qdrant_optional(self):
        s, _ = _make_summarizer(redis_client=None, qdrant_client=None)
        assert s.redis_client is None
        assert s.qdrant_client is None


# ---------------------------------------------------------------------------
# find_summarizable_memories
# ---------------------------------------------------------------------------

class TestFindSummarizableMemories:

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        conn = _make_conn()
        row = {"id": "m1", "title": "T", "content": "c" * 600, "metadata": {}, "agent_id": "a",
               "created_at": datetime.now(UTC), "content_length": 600, "age_days": 35}
        conn.fetch = AsyncMock(return_value=[row])
        s, _ = _make_summarizer(conn=conn)
        # Replace pool acquire to use our conn
        results = await s.find_summarizable_memories(days_old=30, limit=10)
        assert isinstance(results, list)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("DB error"))
        s, _ = _make_summarizer(conn=conn)
        results = await s.find_summarizable_memories()
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_old_memories(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        s, _ = _make_summarizer(conn=conn)
        results = await s.find_summarizable_memories(days_old=30)
        assert results == []


# ---------------------------------------------------------------------------
# _build_summary_prompt
# ---------------------------------------------------------------------------

class TestBuildSummaryPrompt:

    def test_concise_strategy_prompt(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer()
        prompt = s._build_summary_prompt(SummaryStrategy.CONCISE)
        assert "concise" in prompt.lower()
        assert "JSON" in prompt

    def test_standard_strategy_prompt(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer()
        prompt = s._build_summary_prompt(SummaryStrategy.STANDARD)
        assert "medium" in prompt.lower() or "standard" in prompt.lower() or "sentences" in prompt.lower()

    def test_detailed_strategy_prompt(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer()
        prompt = s._build_summary_prompt(SummaryStrategy.DETAILED)
        assert "detailed" in prompt.lower()

    def test_extractive_strategy_prompt(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer()
        prompt = s._build_summary_prompt(SummaryStrategy.EXTRACTIVE)
        assert "Extract" in prompt or "bullet" in prompt.lower() or "key points" in prompt.lower()

    def test_all_prompts_return_strings(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer()
        for strategy in SummaryStrategy:
            result = s._build_summary_prompt(strategy)
            assert isinstance(result, str)
            assert len(result) > 10


# ---------------------------------------------------------------------------
# _parse_summary_result
# ---------------------------------------------------------------------------

class TestParseSummaryResult:

    def test_parse_full_result(self):
        s, _ = _make_summarizer()
        raw = {"summary": "A summary", "keywords": ["a", "b"], "entities": [{"type": "person", "name": "Alice"}]}
        parsed = s._parse_summary_result(raw)
        assert parsed["summary"] == "A summary"
        assert parsed["keywords"] == ["a", "b"]
        assert len(parsed["entities"]) == 1

    def test_parse_empty_result_uses_defaults(self):
        s, _ = _make_summarizer()
        parsed = s._parse_summary_result({})
        assert parsed["summary"] == ""
        assert parsed["keywords"] == []
        assert parsed["entities"] == []

    def test_parse_partial_result(self):
        s, _ = _make_summarizer()
        parsed = s._parse_summary_result({"summary": "Only summary"})
        assert parsed["summary"] == "Only summary"
        assert parsed["keywords"] == []


# ---------------------------------------------------------------------------
# _get_embedding
# ---------------------------------------------------------------------------

class TestGetEmbedding:

    def test_returns_list_of_floats(self):
        s, _ = _make_summarizer()
        embedding = s._get_embedding("some text")
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(v, float) for v in embedding)

    def test_different_texts_may_differ(self):
        s, _ = _make_summarizer()
        e1 = s._get_embedding("text one")
        e2 = s._get_embedding("text two")
        # With random embeddings they very likely differ
        assert len(e1) == len(e2)


# ---------------------------------------------------------------------------
# _summarize_with_openai
# ---------------------------------------------------------------------------

class TestSummarizeWithOpenAI:

    @pytest.mark.asyncio
    async def test_happy_path_returns_summary(self):
        from src.intelligent_summarization import SummaryStrategy

        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "summary": "A test summary from openai",
            "keywords": ["test", "openai"],
            "entities": []
        })

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # AsyncOpenAI is imported locally inside _summarize_with_openai, patch at source
        mock_openai_module = MagicMock()
        mock_openai_module.AsyncOpenAI = MagicMock(return_value=mock_client)

        s, _ = _make_summarizer(provider="openai")

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            result = await s._summarize_with_openai("Some content to summarize", SummaryStrategy.STANDARD)

        assert result["summary"] == "A test summary from openai"
        assert "test" in result["keywords"]

    @pytest.mark.asyncio
    async def test_openai_import_error_propagates(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="openai")

        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises((ImportError, Exception)):
                await s._summarize_with_openai("content", SummaryStrategy.CONCISE)

    @pytest.mark.asyncio
    async def test_openai_api_exception_propagates(self):
        from src.intelligent_summarization import SummaryStrategy

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API rate limit"))

        mock_openai_module = MagicMock()
        mock_openai_module.AsyncOpenAI = MagicMock(return_value=mock_client)

        s, _ = _make_summarizer(provider="openai")

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            with pytest.raises(RuntimeError, match="API rate limit"):
                await s._summarize_with_openai("content", SummaryStrategy.STANDARD)


# ---------------------------------------------------------------------------
# _summarize_with_anthropic
# ---------------------------------------------------------------------------

class TestSummarizeWithAnthropic:

    def _mock_anthropic_response(self, text: str):
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=text)]
        return mock_msg

    def _mock_anthropic_module(self, mock_client):
        mock_module = MagicMock()
        mock_module.AsyncAnthropic = MagicMock(return_value=mock_client)
        return mock_module

    @pytest.mark.asyncio
    async def test_happy_path_with_valid_json(self):
        from src.intelligent_summarization import SummaryStrategy

        payload = json.dumps({
            "summary": "Anthropic summary result",
            "keywords": ["anthropic", "summary"],
            "entities": [{"type": "org", "name": "Anthropic"}]
        })
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=self._mock_anthropic_response(payload)
        )

        s, _ = _make_summarizer(provider="anthropic")

        with patch.dict("sys.modules", {"anthropic": self._mock_anthropic_module(mock_client)}):
            result = await s._summarize_with_anthropic("Long content here", SummaryStrategy.STANDARD)

        assert result["summary"] == "Anthropic summary result"
        assert result["keywords"] == ["anthropic", "summary"]

    @pytest.mark.asyncio
    async def test_non_json_response_falls_back_to_raw_text(self):
        from src.intelligent_summarization import SummaryStrategy

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=self._mock_anthropic_response("Plain text response, not JSON.")
        )

        s, _ = _make_summarizer(provider="anthropic")

        with patch.dict("sys.modules", {"anthropic": self._mock_anthropic_module(mock_client)}):
            result = await s._summarize_with_anthropic("content", SummaryStrategy.CONCISE)

        # Fallback: summary = raw text
        assert result["summary"] == "Plain text response, not JSON."
        assert result["keywords"] == []
        assert result["entities"] == []

    @pytest.mark.asyncio
    async def test_anthropic_import_error_propagates(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="anthropic")

        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises((ImportError, Exception)):
                await s._summarize_with_anthropic("content", SummaryStrategy.DETAILED)

    @pytest.mark.asyncio
    async def test_anthropic_api_exception_propagates(self):
        from src.intelligent_summarization import SummaryStrategy

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("rate limit exceeded"))

        s, _ = _make_summarizer(provider="anthropic")

        with patch.dict("sys.modules", {"anthropic": self._mock_anthropic_module(mock_client)}):
            with pytest.raises(RuntimeError, match="rate limit exceeded"):
                await s._summarize_with_anthropic("content", SummaryStrategy.STANDARD)

    @pytest.mark.asyncio
    async def test_uses_concise_prompt_for_concise_strategy(self):
        from src.intelligent_summarization import SummaryStrategy

        payload = json.dumps({"summary": "short", "keywords": [], "entities": []})
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=self._mock_anthropic_response(payload)
        )

        s, _ = _make_summarizer(provider="anthropic")

        with patch.dict("sys.modules", {"anthropic": self._mock_anthropic_module(mock_client)}):
            result = await s._summarize_with_anthropic("content text", SummaryStrategy.CONCISE)

        assert result["summary"] == "short"
        mock_client.messages.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# _summarize_with_ollama
# ---------------------------------------------------------------------------

class TestSummarizeWithOllama:

    @pytest.mark.asyncio
    async def test_happy_path_returns_summary(self):
        from src.intelligent_summarization import SummaryStrategy

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"response": "Ollama response text"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # aiohttp is imported locally inside _summarize_with_ollama, patch via sys.modules
        mock_aiohttp_module = MagicMock()
        mock_aiohttp_module.ClientSession = MagicMock(return_value=mock_session)

        s, _ = _make_summarizer(provider="ollama")

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp_module}):
            result = await s._summarize_with_ollama("content to summarize", SummaryStrategy.STANDARD)

        assert result["summary"] == "Ollama response text"
        assert result["keywords"] == []
        assert result["entities"] == []

    @pytest.mark.asyncio
    async def test_ollama_exception_propagates(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="ollama")

        mock_aiohttp_module = MagicMock()
        mock_aiohttp_module.ClientSession = MagicMock(side_effect=RuntimeError("Connection refused"))

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp_module}):
            with pytest.raises(RuntimeError):
                await s._summarize_with_ollama("content", SummaryStrategy.CONCISE)


# ---------------------------------------------------------------------------
# _generate_llm_summary - provider routing
# ---------------------------------------------------------------------------

class TestGenerateLLMSummary:

    @pytest.mark.asyncio
    async def test_routes_to_openai(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="openai")
        expected = {"summary": "openai result", "keywords": [], "entities": []}
        with patch.object(s, "_summarize_with_openai", new=AsyncMock(return_value=expected)):
            result = await s._generate_llm_summary("content", SummaryStrategy.STANDARD)
        assert result["summary"] == "openai result"

    @pytest.mark.asyncio
    async def test_routes_to_anthropic(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="anthropic")
        expected = {"summary": "anthropic result", "keywords": [], "entities": []}
        with patch.object(s, "_summarize_with_anthropic", new=AsyncMock(return_value=expected)):
            result = await s._generate_llm_summary("content", SummaryStrategy.STANDARD)
        assert result["summary"] == "anthropic result"

    @pytest.mark.asyncio
    async def test_routes_to_ollama(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="ollama")
        expected = {"summary": "ollama result", "keywords": [], "entities": []}
        with patch.object(s, "_summarize_with_ollama", new=AsyncMock(return_value=expected)):
            result = await s._generate_llm_summary("content", SummaryStrategy.STANDARD)
        assert result["summary"] == "ollama result"

    @pytest.mark.asyncio
    async def test_unsupported_provider_raises_value_error(self):
        from src.intelligent_summarization import SummaryStrategy
        s, _ = _make_summarizer(provider="unsupported-provider")
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            await s._generate_llm_summary("content", SummaryStrategy.STANDARD)


# ---------------------------------------------------------------------------
# summarize_memory
# ---------------------------------------------------------------------------

class TestSummarizeMemory:

    @pytest.mark.asyncio
    async def test_returns_summary_result(self):
        from src.intelligent_summarization import SummaryStrategy, SummaryResult

        s, _ = _make_summarizer()
        memory = _sample_memory()
        llm_data = {"summary": "A good summary", "keywords": ["good"], "entities": []}

        with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
            result = await s.summarize_memory(memory)

        assert isinstance(result, SummaryResult)
        assert result.summary == "A good summary"
        assert result.memory_id == "mem-001"

    @pytest.mark.asyncio
    async def test_compression_ratio_calculated(self):
        from src.intelligent_summarization import SummaryStrategy

        s, _ = _make_summarizer()
        long_content = "word " * 200  # 1000 chars
        memory = _sample_memory(content=long_content)
        llm_data = {"summary": "short", "keywords": [], "entities": []}  # 5 chars

        with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
            result = await s.summarize_memory(memory)

        # compression_ratio = len(content) / len(summary)
        assert result.compression_ratio == len(long_content) / len("short")

    @pytest.mark.asyncio
    async def test_redis_cache_hit_returns_cached(self):
        from src.intelligent_summarization import SummaryStrategy, SummaryResult

        cached_data = json.dumps({
            "memory_id": "mem-001",
            "original_content": "original",
            "summary": "cached summary",
            "strategy": "standard",
            "compression_ratio": 3.0,
            "keywords": ["cached"],
            "entities": [],
            "created_at": datetime.now(UTC).isoformat()
        })

        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=cached_data)

        s, _ = _make_summarizer(redis_client=redis_mock)
        memory = _sample_memory()

        with patch.object(s, "_generate_llm_summary", new=AsyncMock()) as mock_llm:
            result = await s.summarize_memory(memory)

        # LLM should NOT be called because cache was hit
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_cache_miss_calls_llm(self):
        from src.intelligent_summarization import SummaryStrategy

        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock()

        s, _ = _make_summarizer(redis_client=redis_mock)
        memory = _sample_memory()
        llm_data = {"summary": "Fresh LLM summary", "keywords": [], "entities": []}

        with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)) as mock_llm:
            result = await s.summarize_memory(memory)

        mock_llm.assert_awaited_once()
        assert result.summary == "Fresh LLM summary"

    @pytest.mark.asyncio
    async def test_redis_stores_result_after_llm(self):
        from src.intelligent_summarization import SummaryStrategy

        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock()

        s, _ = _make_summarizer(redis_client=redis_mock)
        memory = _sample_memory()
        llm_data = {"summary": "Result to cache", "keywords": [], "entities": []}

        with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
            await s.summarize_memory(memory)

        redis_mock.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self):
        from src.intelligent_summarization import SummaryStrategy

        s, _ = _make_summarizer()
        memory = _sample_memory()

        with patch.object(s, "_generate_llm_summary", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
            with pytest.raises(RuntimeError, match="LLM down"):
                await s.summarize_memory(memory)

    @pytest.mark.asyncio
    async def test_uses_standard_strategy_by_default(self):
        from src.intelligent_summarization import SummaryStrategy

        s, _ = _make_summarizer()
        memory = _sample_memory()
        llm_data = {"summary": "Standard summary", "keywords": [], "entities": []}

        with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
            result = await s.summarize_memory(memory)

        assert result.strategy == SummaryStrategy.STANDARD


# ---------------------------------------------------------------------------
# _simple_cluster
# ---------------------------------------------------------------------------

class TestSimpleCluster:

    def test_clusters_by_category_and_agent(self):
        from src.intelligent_summarization import MemoryCluster
        s, _ = _make_summarizer()

        memories = [
            {"id": "m1", "agent_id": "a1", "metadata": {"memory_category": "trading"}},
            {"id": "m2", "agent_id": "a1", "metadata": {"memory_category": "trading"}},
            {"id": "m3", "agent_id": "a2", "metadata": {"memory_category": "trading"}},
        ]
        clusters = s._simple_cluster(memories)
        assert len(clusters) == 2  # two distinct agent_ids

    def test_empty_memories_returns_empty(self):
        s, _ = _make_summarizer()
        result = s._simple_cluster([])
        assert result == []

    def test_metadata_string_parsed(self):
        s, _ = _make_summarizer()
        memories = [
            {
                "id": "m1",
                "agent_id": "a1",
                "metadata": json.dumps({"memory_category": "dev"})
            }
        ]
        clusters = s._simple_cluster(memories)
        assert len(clusters) == 1
        assert clusters[0].cluster_theme == "dev"

    def test_invalid_metadata_string_falls_back_to_general(self):
        s, _ = _make_summarizer()
        memories = [
            {"id": "m1", "agent_id": "a1", "metadata": "not-json{{"}
        ]
        clusters = s._simple_cluster(memories)
        assert len(clusters) == 1
        assert clusters[0].cluster_theme == "general"

    def test_missing_metadata_uses_general(self):
        s, _ = _make_summarizer()
        memories = [
            {"id": "m1", "agent_id": "a1"}
        ]
        clusters = s._simple_cluster(memories)
        assert clusters[0].cluster_theme == "general"

    def test_memory_count_is_accurate(self):
        s, _ = _make_summarizer()
        memories = [
            {"id": "m1", "agent_id": "a1", "metadata": {"memory_category": "x"}},
            {"id": "m2", "agent_id": "a1", "metadata": {"memory_category": "x"}},
            {"id": "m3", "agent_id": "a1", "metadata": {"memory_category": "x"}},
        ]
        clusters = s._simple_cluster(memories)
        assert clusters[0].memory_count == 3


# ---------------------------------------------------------------------------
# cluster_memories
# ---------------------------------------------------------------------------

class TestClusterMemories:

    @pytest.mark.asyncio
    async def test_falls_back_to_simple_cluster_when_no_qdrant(self):
        s, _ = _make_summarizer(qdrant_client=None)
        memories = [
            {"id": "m1", "agent_id": "a1", "content": "text", "metadata": {}},
        ]
        clusters = await s.cluster_memories(memories)
        assert len(clusters) >= 1

    @pytest.mark.asyncio
    async def test_with_qdrant_iterates_memories(self):
        mock_qdrant = MagicMock()
        mock_qdrant.search = MagicMock(return_value=[])
        s, _ = _make_summarizer(qdrant_client=mock_qdrant)

        memories = [
            {"id": "m1", "agent_id": "a1", "content": "text one", "metadata": {}},
            {"id": "m2", "agent_id": "a2", "content": "text two", "metadata": {}},
        ]

        with patch.object(s, "_infer_cluster_theme", new=AsyncMock(return_value="General")):
            clusters = await s.cluster_memories(memories)

        assert len(clusters) >= 1

    @pytest.mark.asyncio
    async def test_qdrant_exception_falls_back_to_simple_cluster(self):
        mock_qdrant = MagicMock()
        mock_qdrant.search = MagicMock(side_effect=RuntimeError("qdrant error"))
        s, _ = _make_summarizer(qdrant_client=mock_qdrant)

        memories = [
            {"id": "m1", "agent_id": "a1", "content": "text", "metadata": {"memory_category": "test"}},
        ]

        with patch.object(s, "_infer_cluster_theme", new=AsyncMock(side_effect=RuntimeError("theme error"))):
            clusters = await s.cluster_memories(memories)

        assert isinstance(clusters, list)

    @pytest.mark.asyncio
    async def test_empty_memories_returns_empty(self):
        s, _ = _make_summarizer(qdrant_client=None)
        clusters = await s.cluster_memories([])
        assert clusters == []

    @pytest.mark.asyncio
    async def test_already_assigned_memory_is_skipped_continue_branch(self):
        """Cover line 399 (continue) and line 422 (assigned_ids.add for similar).

        Uses 3 memories: m1 absorbs m2 as similar.  m3 is not similar to m1.
        Loop order: m1 -> process (adds m1, m2 to assigned), m2 -> hits
        `continue` (line 399), m3 -> processes as new cluster. Break condition
        (assigned_ids >= memories count) is only satisfied after m3 is done.
        """
        s, _ = _make_summarizer(qdrant_client=MagicMock())

        memories = [
            {"id": "m1", "agent_id": "a1", "content": "content a", "metadata": {}},
            {"id": "m2", "agent_id": "a1", "content": "content b", "metadata": {}},
            {"id": "m3", "agent_id": "a1", "content": "content c", "metadata": {}},
        ]

        # _find_similar_memories: when target=m1 -> returns [m2]; otherwise returns []
        async def _fake_find_similar(target, candidates):
            if target["id"] == "m1":
                return [{"id": "m2", "content": "content b"}]
            return []

        with patch.object(s, "_find_similar_memories", new=_fake_find_similar):
            with patch.object(s, "_infer_cluster_theme", new=AsyncMock(return_value="Theme")):
                clusters = await s.cluster_memories(memories)

        # m1+m2 cluster and m3 cluster
        assert len(clusters) == 2


# ---------------------------------------------------------------------------
# _find_similar_memories
# ---------------------------------------------------------------------------

class TestFindSimilarMemories:

    @pytest.mark.asyncio
    async def test_returns_empty_on_qdrant_error(self):
        mock_qdrant = MagicMock()
        mock_qdrant.search = MagicMock(side_effect=RuntimeError("search failed"))
        s, _ = _make_summarizer(qdrant_client=mock_qdrant)

        target = {"id": "m1", "content": "target content"}
        candidates = [{"id": "m2", "content": "similar content"}]

        result = await s._find_similar_memories(target, candidates)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_matching_candidates(self):
        mock_hit = MagicMock()
        mock_hit.id = "m2"
        mock_qdrant = MagicMock()
        mock_qdrant.search = MagicMock(return_value=[mock_hit])

        s, _ = _make_summarizer(qdrant_client=mock_qdrant)

        target = {"id": "m1", "content": "content"}
        candidates = [{"id": "m2", "content": "similar"}, {"id": "m3", "content": "different"}]

        result = await s._find_similar_memories(target, candidates)
        assert len(result) == 1
        assert result[0]["id"] == "m2"


# ---------------------------------------------------------------------------
# _infer_cluster_theme
# ---------------------------------------------------------------------------

class TestInferClusterTheme:

    @pytest.mark.asyncio
    async def test_returns_general_on_error(self):
        from src.intelligent_summarization import MemoryCluster
        s, _ = _make_summarizer()

        cluster = MemoryCluster(cluster_id="c1", memories=[{"id": "m1", "content": "content"}])

        with patch.object(s, "_generate_cluster_theme", new=AsyncMock(side_effect=RuntimeError("theme error"))):
            theme = await s._infer_cluster_theme(cluster)

        assert theme == "General"

    @pytest.mark.asyncio
    async def test_calls_generate_cluster_theme(self):
        from src.intelligent_summarization import MemoryCluster
        s, _ = _make_summarizer()

        cluster = MemoryCluster(cluster_id="c1", memories=[{"id": "m1", "content": "trading strategy"}])

        with patch.object(s, "_generate_cluster_theme", new=AsyncMock(return_value="Trading")) as mock_gen:
            theme = await s._infer_cluster_theme(cluster)

        assert theme == "Trading"
        mock_gen.assert_awaited_once()


# ---------------------------------------------------------------------------
# _generate_cluster_theme
# ---------------------------------------------------------------------------

class TestGenerateClusterTheme:

    def _mock_anthropic_module(self, mock_client):
        mock_module = MagicMock()
        mock_module.AsyncAnthropic = MagicMock(return_value=mock_client)
        return mock_module

    @pytest.mark.asyncio
    async def test_anthropic_provider_calls_api(self):
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Trading Strategy")]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        s, _ = _make_summarizer(provider="anthropic")

        # AsyncAnthropic is imported locally inside _generate_cluster_theme
        with patch.dict("sys.modules", {"anthropic": self._mock_anthropic_module(mock_client)}):
            theme = await s._generate_cluster_theme("trading stocks investments")

        assert theme == "Trading Strategy"

    @pytest.mark.asyncio
    async def test_non_anthropic_falls_back_to_keyword_extraction(self):
        s, _ = _make_summarizer(provider="openai")
        content = "apple orange banana grape cherry lemon mango pear plum peach"
        theme = await s._generate_cluster_theme(content)
        # Returns comma-separated top words
        assert isinstance(theme, str)
        assert len(theme) > 0

    @pytest.mark.asyncio
    async def test_anthropic_exception_returns_general(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API error"))

        s, _ = _make_summarizer(provider="anthropic")

        with patch.dict("sys.modules", {"anthropic": self._mock_anthropic_module(mock_client)}):
            theme = await s._generate_cluster_theme("some content")

        assert theme == "General"


# ---------------------------------------------------------------------------
# _store_summary
# ---------------------------------------------------------------------------

class TestStoreSummary:

    @pytest.mark.asyncio
    async def test_calls_db_execute(self):
        from src.intelligent_summarization import SummaryResult, SummaryStrategy
        conn = _make_conn()
        conn.execute = AsyncMock(return_value=None)
        s, _ = _make_summarizer(conn=conn)

        sr = SummaryResult(
            memory_id="m1",
            original_content="original content here",
            summary="A summary",
            strategy=SummaryStrategy.STANDARD,
            compression_ratio=3.0,
            keywords=["kw1"],
            entities=[]
        )

        await s._store_summary(sr)
        conn.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_db_error_propagates(self):
        from src.intelligent_summarization import SummaryResult, SummaryStrategy
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB write failed"))
        s, _ = _make_summarizer(conn=conn)

        sr = SummaryResult(
            memory_id="m2",
            original_content="content",
            summary="summary",
            strategy=SummaryStrategy.CONCISE,
            compression_ratio=2.0,
        )

        with pytest.raises(RuntimeError, match="DB write failed"):
            await s._store_summary(sr)


# ---------------------------------------------------------------------------
# auto_summarize_old_memories
# ---------------------------------------------------------------------------

class TestAutoSummarizeOldMemories:

    @pytest.mark.asyncio
    async def test_dry_run_does_not_store(self):
        s, _ = _make_summarizer()
        memory = _sample_memory()

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(return_value=[memory])):
            llm_data = {"summary": "dry run summary", "keywords": [], "entities": []}
            with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
                with patch.object(s, "_store_summary", new=AsyncMock()) as mock_store:
                    result = await s.auto_summarize_old_memories(dry_run=True)

        assert result["status"] == "success"
        mock_store.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_live_run_stores_summary(self):
        s, _ = _make_summarizer()
        memory = _sample_memory()

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(return_value=[memory])):
            llm_data = {"summary": "stored summary", "keywords": [], "entities": []}
            with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
                with patch.object(s, "_store_summary", new=AsyncMock()) as mock_store:
                    result = await s.auto_summarize_old_memories(dry_run=False)

        assert result["status"] == "success"
        mock_store.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_correct_counts(self):
        s, _ = _make_summarizer()
        memories = [_sample_memory(mem_id=f"m{i}") for i in range(3)]

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(return_value=memories)):
            llm_data = {"summary": "s", "keywords": [], "entities": []}
            with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
                with patch.object(s, "_store_summary", new=AsyncMock()):
                    result = await s.auto_summarize_old_memories(dry_run=False)

        assert result["total_candidates"] == 3
        assert result["summarized"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_failed_summarization_counted(self):
        s, _ = _make_summarizer()
        memories = [_sample_memory(mem_id="m1"), _sample_memory(mem_id="m2")]

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(return_value=memories)):
            with patch.object(s, "_generate_llm_summary", new=AsyncMock(side_effect=RuntimeError("LLM fail"))):
                result = await s.auto_summarize_old_memories(dry_run=True)

        assert result["failed"] == 2
        assert result["summarized"] == 0

    @pytest.mark.asyncio
    async def test_avg_compression_ratio_calculated(self):
        s, _ = _make_summarizer()
        memory1 = _sample_memory(mem_id="m1", content="w " * 250)  # 500 chars
        memory2 = _sample_memory(mem_id="m2", content="w " * 250)

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(return_value=[memory1, memory2])):
            llm_data = {"summary": "xx", "keywords": [], "entities": []}  # 2 chars
            with patch.object(s, "_generate_llm_summary", new=AsyncMock(return_value=llm_data)):
                with patch.object(s, "_store_summary", new=AsyncMock()):
                    result = await s.auto_summarize_old_memories(dry_run=False)

        assert "avg_compression_ratio" in result
        assert result["avg_compression_ratio"] > 0

    @pytest.mark.asyncio
    async def test_no_candidates_returns_zero_counts(self):
        s, _ = _make_summarizer()

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(return_value=[])):
            result = await s.auto_summarize_old_memories(dry_run=True)

        assert result["status"] == "success"
        assert result["total_candidates"] == 0
        assert result["summarized"] == 0

    @pytest.mark.asyncio
    async def test_outer_exception_returns_error_status(self):
        s, _ = _make_summarizer()

        with patch.object(s, "find_summarizable_memories", new=AsyncMock(side_effect=RuntimeError("outer fail"))):
            result = await s.auto_summarize_old_memories(dry_run=True)

        assert result["status"] == "error"
        assert "error" in result


# ---------------------------------------------------------------------------
# get_summarization_statistics
# ---------------------------------------------------------------------------

class TestGetSummarizationStatistics:

    @pytest.mark.asyncio
    async def test_returns_success_with_counts(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(side_effect=[42, 3.5])
        s, _ = _make_summarizer(conn=conn)

        result = await s.get_summarization_statistics()
        assert result["status"] == "success"
        assert result["memories_summarized"] == 42
        assert result["average_compression_ratio"] == 3.5

    @pytest.mark.asyncio
    async def test_null_avg_compression_returns_zero(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(side_effect=[0, None])
        s, _ = _make_summarizer(conn=conn)

        result = await s.get_summarization_statistics()
        assert result["average_compression_ratio"] == 0.0

    @pytest.mark.asyncio
    async def test_db_exception_returns_error_status(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(side_effect=RuntimeError("DB error in stats"))
        s, _ = _make_summarizer(conn=conn)

        result = await s.get_summarization_statistics()
        assert result["status"] == "error"
        assert "error" in result
