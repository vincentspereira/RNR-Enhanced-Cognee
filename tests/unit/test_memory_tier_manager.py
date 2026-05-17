"""
Unit tests for src/memory_tier_manager.py

Coverage targets:
- Constants / module-level values
- MemoryTierManager.__init__
- _ensure_schema: no pool, already ensured, exception path
- get_tier: no pool, success, exception
- get_tier_stats: no pool, with/without agent_id, exception
- set_tier: invalid tier, no pool, success (with/without redis), 0 rows, exception
- promote: archive->long_term, long_term->working, None->working, already working
- demote: working->long_term, long_term->archive, None->archive, already archive
- run_tier_maintenance: no pool, demotion logic, exception
- _cache_in_redis: no redis/no pool, success, exception
- init_tier_manager / get_tier_manager singletons
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.memory_tier_manager import (
    MemoryTierManager,
    TIER_WORKING,
    TIER_LONG_TERM,
    TIER_ARCHIVE,
    ALL_TIERS,
    HOT_ACCESS_THRESHOLD,
    PROMOTION_ACCESS_WINDOW_DAYS,
    DEMOTION_IDLE_DAYS,
    REDIS_WORKING_TTL,
    init_tier_manager,
    get_tier_manager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeConn:
    def __init__(self):
        self._fetchval_queue = []
        self._fetch_queue = []
        self.execute = AsyncMock(return_value="UPDATE 1")

    def _push_fetchval(self, *vals):
        self._fetchval_queue.extend(vals)

    def _push_fetch(self, rows):
        self._fetch_queue.append(rows)

    async def fetchval(self, *args, **kwargs):
        if self._fetchval_queue:
            return self._fetchval_queue.pop(0)
        return None

    async def fetch(self, *args, **kwargs):
        if self._fetch_queue:
            return self._fetch_queue.pop(0)
        return []

    async def fetchrow(self, *args, **kwargs):
        return None


class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(conn=None):
    if conn is None:
        conn = _FakeConn()
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtx(conn))
    return pool, conn


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_tier_constants():
    assert TIER_WORKING == "working"
    assert TIER_LONG_TERM == "long_term"
    assert TIER_ARCHIVE == "archive"
    assert TIER_WORKING in ALL_TIERS
    assert TIER_LONG_TERM in ALL_TIERS
    assert TIER_ARCHIVE in ALL_TIERS


def test_threshold_constants():
    assert HOT_ACCESS_THRESHOLD > 0
    assert PROMOTION_ACCESS_WINDOW_DAYS > 0
    assert DEMOTION_IDLE_DAYS > 0
    assert REDIS_WORKING_TTL > 0


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_stores_pool_and_redis():
    pool, _ = _make_pool()
    redis = MagicMock()
    mgr = MemoryTierManager(pool, redis)
    assert mgr.pool is pool
    assert mgr.redis is redis
    assert mgr._schema_ensured is False


def test_init_no_redis():
    pool, _ = _make_pool()
    mgr = MemoryTierManager(pool)
    assert mgr.redis is None


# ---------------------------------------------------------------------------
# _ensure_schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_schema_skipped_when_no_pool():
    mgr = MemoryTierManager(None)
    await mgr._ensure_schema()
    # Should not raise; schema_ensured stays False because no pool
    assert mgr._schema_ensured is False


@pytest.mark.asyncio
async def test_ensure_schema_runs_ddl():
    pool, conn = _make_pool()
    mgr = MemoryTierManager(pool)
    await mgr._ensure_schema()
    assert conn.execute.call_count == 2  # ALTER TABLE + CREATE INDEX
    assert mgr._schema_ensured is True


@pytest.mark.asyncio
async def test_ensure_schema_idempotent():
    pool, conn = _make_pool()
    mgr = MemoryTierManager(pool)
    await mgr._ensure_schema()
    await mgr._ensure_schema()  # second call is a no-op
    assert conn.execute.call_count == 2  # still just 2


@pytest.mark.asyncio
async def test_ensure_schema_exception_sets_flag():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("permission denied")
    mgr = MemoryTierManager(pool)
    await mgr._ensure_schema()  # should not raise
    assert mgr._schema_ensured is True  # set to True to avoid retry


# ---------------------------------------------------------------------------
# get_tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tier_no_pool():
    mgr = MemoryTierManager(None)
    result = await mgr.get_tier("mem-1")
    assert result is None


@pytest.mark.asyncio
async def test_get_tier_returns_value():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_LONG_TERM)
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.get_tier("mem-1")
    assert result == TIER_LONG_TERM


@pytest.mark.asyncio
async def test_get_tier_exception_returns_none():
    pool, conn = _make_pool()
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True

    async def _bad_fv(*args, **kwargs):
        raise RuntimeError("db error")

    conn.fetchval = _bad_fv
    result = await mgr.get_tier("mem-1")
    assert result is None


# ---------------------------------------------------------------------------
# get_tier_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tier_stats_no_pool():
    mgr = MemoryTierManager(None)
    stats = await mgr.get_tier_stats()
    assert stats == {"error": "pool unavailable"}


@pytest.mark.asyncio
async def test_get_tier_stats_no_agent():
    pool, conn = _make_pool()
    conn._push_fetch([
        {"tier": TIER_WORKING, "cnt": 3},
        {"tier": TIER_LONG_TERM, "cnt": 10},
        {"tier": TIER_ARCHIVE, "cnt": 2},
    ])
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    stats = await mgr.get_tier_stats()
    assert stats["working"] == 3
    assert stats["long_term"] == 10
    assert stats["archive"] == 2
    assert stats["total"] == 15
    assert stats["agent_id"] == "all"


@pytest.mark.asyncio
async def test_get_tier_stats_with_agent():
    pool, conn = _make_pool()
    conn._push_fetch([
        {"tier": TIER_LONG_TERM, "cnt": 5},
    ])
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    stats = await mgr.get_tier_stats(agent_id="agent-1")
    assert stats["long_term"] == 5
    assert stats["working"] == 0
    assert stats["archive"] == 0
    assert stats["agent_id"] == "agent-1"


@pytest.mark.asyncio
async def test_get_tier_stats_exception():
    pool, conn = _make_pool()
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True

    async def _bad_fetch(*args, **kwargs):
        raise RuntimeError("query failed")

    conn.fetch = _bad_fetch
    stats = await mgr.get_tier_stats()
    assert "error" in stats


# ---------------------------------------------------------------------------
# set_tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_tier_invalid_tier_returns_false():
    pool, _ = _make_pool()
    mgr = MemoryTierManager(pool)
    result = await mgr.set_tier("mem-1", "invalid_tier")
    assert result is False


@pytest.mark.asyncio
async def test_set_tier_no_pool_returns_false():
    mgr = MemoryTierManager(None)
    result = await mgr.set_tier("mem-1", TIER_WORKING)
    assert result is False


@pytest.mark.asyncio
async def test_set_tier_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.set_tier("mem-1", TIER_LONG_TERM)
    assert result is True


@pytest.mark.asyncio
async def test_set_tier_working_triggers_redis_cache():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    redis = AsyncMock()
    redis.setex = AsyncMock()
    mgr = MemoryTierManager(pool, redis)
    mgr._schema_ensured = True

    # _cache_in_redis will call pool.acquire; set up conn to return content row
    conn._push_fetchval(None)  # fetchrow inside _cache_in_redis

    async def _fake_fetchrow(*args, **kwargs):
        return {"content": "some content", "agent_id": "a1"}

    conn.fetchrow = _fake_fetchrow
    result = await mgr.set_tier("mem-1", TIER_WORKING)
    assert result is True


@pytest.mark.asyncio
async def test_set_tier_zero_rows_returns_false():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 0")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.set_tier("mem-1", TIER_ARCHIVE)
    assert result is False


@pytest.mark.asyncio
async def test_set_tier_exception_returns_false():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("connection error")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.set_tier("mem-1", TIER_WORKING)
    assert result is False


# ---------------------------------------------------------------------------
# promote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_promote_archive_to_long_term():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_ARCHIVE)  # get_tier returns archive
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.promote("mem-1")
    assert new_tier == TIER_LONG_TERM


@pytest.mark.asyncio
async def test_promote_long_term_to_working():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_LONG_TERM)
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.promote("mem-1")
    assert new_tier == TIER_WORKING


@pytest.mark.asyncio
async def test_promote_none_tier_treated_as_long_term():
    pool, conn = _make_pool()
    conn._push_fetchval(None)  # get_tier returns None
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.promote("mem-1")
    assert new_tier == TIER_WORKING


@pytest.mark.asyncio
async def test_promote_working_stays_working():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_WORKING)
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.promote("mem-1")
    assert new_tier == TIER_WORKING


# ---------------------------------------------------------------------------
# demote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demote_working_to_long_term():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_WORKING)
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.demote("mem-1")
    assert new_tier == TIER_LONG_TERM


@pytest.mark.asyncio
async def test_demote_long_term_to_archive():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_LONG_TERM)
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.demote("mem-1")
    assert new_tier == TIER_ARCHIVE


@pytest.mark.asyncio
async def test_demote_none_tier_treated_as_long_term():
    pool, conn = _make_pool()
    conn._push_fetchval(None)
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.demote("mem-1")
    assert new_tier == TIER_ARCHIVE


@pytest.mark.asyncio
async def test_demote_archive_stays_archive():
    pool, conn = _make_pool()
    conn._push_fetchval(TIER_ARCHIVE)
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    new_tier = await mgr.demote("mem-1")
    assert new_tier == TIER_ARCHIVE


# ---------------------------------------------------------------------------
# run_tier_maintenance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_tier_maintenance_no_pool():
    mgr = MemoryTierManager(None)
    result = await mgr.run_tier_maintenance()
    assert result == {"promoted": 0, "demoted": 0, "errors": 0}


@pytest.mark.asyncio
async def test_run_tier_maintenance_demotes_idle_memories():
    pool, conn = _make_pool()
    # fetch returns 2 ids to demote
    conn._push_fetch([{"id": "m1"}, {"id": "m2"}])
    # set_tier calls will use conn.execute which returns UPDATE 1
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.run_tier_maintenance()
    assert result["demoted"] == 2
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_run_tier_maintenance_handles_set_tier_failure():
    pool, conn = _make_pool()
    conn._push_fetch([{"id": "m1"}])
    conn.execute = AsyncMock(return_value="UPDATE 0")  # 0 rows updated = failure
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.run_tier_maintenance()
    assert result["errors"] == 1


@pytest.mark.asyncio
async def test_run_tier_maintenance_fetch_exception():
    pool, conn = _make_pool()
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True

    async def _bad_fetch(*args, **kwargs):
        raise RuntimeError("query failed")

    conn.fetch = _bad_fetch
    result = await mgr.run_tier_maintenance()
    assert result["errors"] == 1


@pytest.mark.asyncio
async def test_run_tier_maintenance_with_agent_filter():
    pool, conn = _make_pool()
    conn._push_fetch([])  # no memories to demote
    mgr = MemoryTierManager(pool)
    mgr._schema_ensured = True
    result = await mgr.run_tier_maintenance(agent_id="agent-1")
    assert result["demoted"] == 0


# ---------------------------------------------------------------------------
# _cache_in_redis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_in_redis_no_redis():
    pool, _ = _make_pool()
    mgr = MemoryTierManager(pool, redis_client=None)
    await mgr._cache_in_redis("mem-1")  # should not raise


@pytest.mark.asyncio
async def test_cache_in_redis_no_pool():
    mgr = MemoryTierManager(None, redis_client=MagicMock())
    await mgr._cache_in_redis("mem-1")  # should not raise


@pytest.mark.asyncio
async def test_cache_in_redis_stores_content():
    pool, conn = _make_pool()
    redis = AsyncMock()
    redis.setex = AsyncMock()

    async def _fake_fetchrow(*args, **kwargs):
        return {"content": "test content", "agent_id": "agent-1"}

    conn.fetchrow = _fake_fetchrow
    mgr = MemoryTierManager(pool, redis_client=redis)
    await mgr._cache_in_redis("mem-1")
    redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_in_redis_no_row_skips_setex():
    pool, conn = _make_pool()
    redis = AsyncMock()
    redis.setex = AsyncMock()

    async def _fake_fetchrow(*args, **kwargs):
        return None

    conn.fetchrow = _fake_fetchrow
    mgr = MemoryTierManager(pool, redis_client=redis)
    await mgr._cache_in_redis("mem-1")
    redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_cache_in_redis_exception_is_logged():
    pool, conn = _make_pool()
    redis = AsyncMock()
    redis.setex.side_effect = RuntimeError("redis error")

    async def _fake_fetchrow(*args, **kwargs):
        return {"content": "data", "agent_id": "a1"}

    conn.fetchrow = _fake_fetchrow
    mgr = MemoryTierManager(pool, redis_client=redis)
    await mgr._cache_in_redis("mem-1")  # must not raise


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------


def test_init_tier_manager_returns_instance():
    pool, _ = _make_pool()
    mgr = init_tier_manager(pool)
    assert isinstance(mgr, MemoryTierManager)


def test_get_tier_manager_returns_singleton():
    pool, _ = _make_pool()
    init_tier_manager(pool)
    mgr = get_tier_manager()
    assert mgr is not None
    assert isinstance(mgr, MemoryTierManager)


def test_init_tier_manager_with_redis():
    pool, _ = _make_pool()
    redis = MagicMock()
    mgr = init_tier_manager(pool, redis_client=redis)
    assert mgr.redis is redis
