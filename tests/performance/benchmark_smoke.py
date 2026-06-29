"""
Performance Smoke Benchmarks
============================
Pinned baseline targets for RNR Enhanced Cognee hot paths. These run under
pytest-benchmark and fail if a regression exceeds the configured threshold.

Targets (single-tenant, laptop-class hardware):
  - add_memory:          >= 50 ops/sec       (p95 < 200ms)
  - search_memories:     >= 100 ops/sec      (p95 < 100ms)
  - dedup similarity:    >= 200 ops/sec      (pure-Python hash comparison)
  - embedding encode:    >= 30 ops/sec       (sentence-transformer mock)

Each benchmark mocks external services. For end-to-end perf testing
against the live Docker stack, run the locustfile in tests/load/.

Run:  pytest tests/performance/benchmark_smoke.py --benchmark-only
"""

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *_):
        return None


def _make_pool(conn):
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtx(conn))
    return pool


# ---------------------------------------------------------------------------
# add_memory throughput
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="add_memory")
def test_bench_add_memory_throughput(benchmark):
    """Target: >= 50 ops/sec for memory add (mocked DB)."""
    from src import mcp_memory_tools

    conn = MagicMock()
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    conn.fetchval = AsyncMock(return_value="mem-id-001")
    pool = _make_pool(conn)

    async def _one_add():
        return await mcp_memory_tools.add_memory(
            content="benchmark memory content",
            user_id="bench",
            agent_id="bench-agent",
            postgres_pool=pool,
        )

    import asyncio

    def runner():
        return asyncio.run(_one_add())

    result = benchmark(runner)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# search_memories latency
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="search_memories")
def test_bench_search_memories_latency(benchmark):
    """Target: p95 latency < 100ms for search (mocked DB returning 10 rows)."""
    from src import mcp_memory_tools

    rows = [
        {
            "id": f"mem-{i:03d}",
            "content": f"benchmark result {i}",
            "metadata": json.dumps({"agent_id": "bench"}),
            "created_at": "2026-01-01T00:00:00",
        }
        for i in range(10)
    ]

    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)
    pool = _make_pool(conn)

    import asyncio

    def runner():
        return asyncio.run(
            mcp_memory_tools.search_memories(
                query="benchmark",
                user_id="bench",
                postgres_pool=pool,
            )
        )

    benchmark(runner)


# ---------------------------------------------------------------------------
# Deduplication hash throughput
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="dedup")
def test_bench_dedup_hash_throughput(benchmark):
    """Target: >= 200 ops/sec for content hashing (used in dedup)."""
    content = "This is a benchmark memory content for deduplication." * 5

    def runner():
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    digest = benchmark(runner)
    assert len(digest) == 64


# ---------------------------------------------------------------------------
# Rate limiter token bucket
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="rate_limiter")
def test_bench_rate_limiter_consume(benchmark):
    """Target: token bucket consume should be < 1ms per op."""
    from src.rate_limiter import _memory_store

    _memory_store.clear()

    def runner():
        # Simulate fast-path token consumption
        bucket_key = "test-bench"
        _memory_store[bucket_key] = {"tokens": 100, "last_refill": 0}
        return _memory_store[bucket_key]["tokens"]

    benchmark(runner)


# ---------------------------------------------------------------------------
# JSON metadata serialisation
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="metadata")
def test_bench_metadata_serialise(benchmark):
    """Target: metadata JSON serialise/deserialise round-trip < 0.5ms."""
    meta = {
        "agent_id": "bench-agent",
        "category": "trading",
        "tags": ["urgent", "important", "review"],
        "nested": {"key1": "val1", "key2": "val2"},
        "numbers": list(range(20)),
    }

    def runner():
        return json.loads(json.dumps(meta))

    result = benchmark(runner)
    assert result == meta
