"""
Unit Tests for Performance Analytics Module
Tests metrics collection, performance tracking, Prometheus export
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from src.performance_analytics import PerformanceAnalytics, PerformanceMetrics


# ============================================================================
# Test PerformanceAnalytics Initialization
# ============================================================================

class TestPerformanceAnalyticsInit:
    """Test PerformanceAnalytics initialization"""

    @pytest.mark.unit
    def test_init_with_valid_dependencies(self, mock_postgres_pool, mock_redis_client):
        """Test initialization with all dependencies"""
        analytics = PerformanceAnalytics(mock_postgres_pool, mock_redis_client)

        assert analytics.postgres_pool is not None
        assert analytics.redis_client is not None
        assert analytics.query_times == []
        assert analytics.counters is not None

    @pytest.mark.unit
    def test_init_with_max_query_times(self, mock_postgres_pool, mock_redis_client):
        """Test initialization with custom max_query_times"""
        analytics = PerformanceAnalytics(mock_postgres_pool, mock_redis_client)

        assert hasattr(analytics, 'max_query_times')
        assert analytics.max_query_times == 1000


# ============================================================================
# Test Query Recording
# ============================================================================

class TestRecordQueryTime:
    """Test record_query_time method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_query_time_success(self, performance_analytics):
        """Test recording query execution time"""
        initial_count = len(performance_analytics.query_times)

        await performance_analytics.record_query_time("test_operation", 123.45)

        assert len(performance_analytics.query_times) == initial_count + 1
        assert performance_analytics.query_times[-1]["operation"] == "test_operation"
        assert performance_analytics.query_times[-1]["duration_ms"] == 123.45

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_query_time_limit(self, performance_analytics):
        """Test query_times list is limited to max_query_times"""
        # Fill beyond limit
        for i in range(1100):
            await performance_analytics.record_query_time(f"op-{i}", 100.0)

        # Should be limited to max_query_times
        assert len(performance_analytics.query_times) <= performance_analytics.max_query_times

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_query_time_redis_storage(self, performance_analytics):
        """Test recording to Redis for Prometheus metrics"""
        await performance_analytics.record_query_time("test_operation", 250.0)

        # Should have called Redis incrbyfloat
        performance_analytics.redis_client.incrbyfloat.assert_called_once()


# ============================================================================
# Test Cache Recording
# ============================================================================

class TestRecordCache:
    """Test cache hit/miss recording"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_cache_hit(self, performance_analytics):
        """Test recording cache hits"""
        await performance_analytics.record_cache_hit("default")

        assert performance_analytics.counters["cache_hit:default"] == 1

        # Record another
        await performance_analytics.record_cache_hit("default")
        assert performance_analytics.counters["cache_hit:default"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_cache_miss(self, performance_analytics):
        """Test recording cache misses"""
        await performance_analytics.record_cache_miss("redis")

        assert performance_analytics.counters["cache_miss:redis"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_cache_multiple_types(self, performance_analytics):
        """Test recording different cache types"""
        await performance_analytics.record_cache_hit("l1")
        await performance_analytics.record_cache_hit("l2")
        await performance_analytics.record_cache_miss("l1")

        assert performance_analytics.counters["cache_hit:l1"] == 1
        assert performance_analytics.counters["cache_hit:l2"] == 1
        assert performance_analytics.counters["cache_miss:l1"] == 1


# ============================================================================
# Test Error Recording
# ============================================================================

class TestRecordError:
    """Test error recording"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_error(self, performance_analytics, caplog):
        """Test recording errors"""
        await performance_analytics.record_error("database", "query_failed")

        assert performance_analytics.counters["error:database"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_error_multiple(self, performance_analytics):
        """Test recording multiple errors"""
        await performance_analytics.record_error("database", "op1")
        await performance_analytics.record_error("network", "op2")
        await performance_analytics.record_error("database", "op3")

        assert performance_analytics.counters["error:database"] == 2
        assert performance_analytics.counters["error:network"] == 1


# ============================================================================
# Test Performance Metrics Retrieval
# ============================================================================

class TestGetPerformanceMetrics:
    """Test get_performance_metrics method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_metrics_with_data(self, performance_analytics, create_async_context_manager):
        """Test getting metrics with recorded data"""
        # Record some data
        await performance_analytics.record_query_time("op1", 100.0)
        await performance_analytics.record_query_time("op2", 200.0)
        await performance_analytics.record_cache_hit()
        await performance_analytics.record_cache_miss()

        # Mock database queries
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=50)
        mock_conn.fetch = AsyncMock(return_value=[{"agent_id": "agent1", "count": 10}])
        ctx_mgr = create_async_context_manager(mock_conn)
        performance_analytics.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        metrics = await performance_analytics.get_performance_metrics()

        assert metrics["query_performance"]["total_queries"] == 2
        assert metrics["cache_performance"]["hits"] == 1
        assert metrics["cache_performance"]["misses"] == 1
        assert "memory_stats" in metrics

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_metrics_percentiles(self, performance_analytics, create_async_context_manager):
        """Test percentile calculations"""
        # Record multiple query times
        times = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
        for t in times:
            await performance_analytics.record_query_time("test", t)

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=10)
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        performance_analytics.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        metrics = await performance_analytics.get_performance_metrics()

        qp = metrics["query_performance"]
        assert "p50_time_ms" in qp
        assert "p95_time_ms" in qp
        assert qp["min_time_ms"] == 50.0
        assert qp["max_time_ms"] == 500.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, performance_analytics, create_async_context_manager):
        """Test getting metrics with no data"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        performance_analytics.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        metrics = await performance_analytics.get_performance_metrics()

        assert "query_performance" not in metrics or metrics["query_performance"]["total_queries"] == 0


# ============================================================================
# Test Prometheus Export
# ============================================================================

class TestGetPrometheusMetrics:
    """Test get_prometheus_metrics method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prometheus_format(self, performance_analytics, create_async_context_manager):
        """Test Prometheus format output"""
        # Record some data
        await performance_analytics.record_query_time("test", 150.0)
        await performance_analytics.record_cache_hit()
        await performance_analytics.record_cache_miss()

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=100)
        ctx_mgr = create_async_context_manager(mock_conn)
        performance_analytics.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        prometheus_text = await performance_analytics.get_prometheus_metrics()

        assert isinstance(prometheus_text, str)
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text
        assert "enhanced_cognee_" in prometheus_text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prometheus_metrics_includes_all(self, performance_analytics, create_async_context_manager):
        """Test all metrics are included in Prometheus export"""
        await performance_analytics.record_query_time("op1", 100.0)
        await performance_analytics.record_cache_hit()
        await performance_analytics.record_cache_miss()

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=50)
        ctx_mgr = create_async_context_manager(mock_conn)
        performance_analytics.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        prometheus_text = await performance_analytics.get_prometheus_metrics()

        assert "enhanced_cognee_query_time_seconds" in prometheus_text
        assert "enhanced_cognee_cache_hits" in prometheus_text
        assert "enhanced_cognee_cache_misses" in prometheus_text
        assert "enhanced_cognee_total_memories" in prometheus_text


# ============================================================================
# Test Slow Query Detection
# ============================================================================

class TestGetSlowQueries:
    """Test get_slow_queries method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_slow_queries_above_threshold(self, performance_analytics):
        """Test detecting queries above threshold"""
        # Record mix of fast and slow queries
        await performance_analytics.record_query_time("fast", 50.0)
        await performance_analytics.record_query_time("slow", 1500.0)
        await performance_analytics.record_query_time("slow2", 2000.0)

        slow_queries = await performance_analytics.get_slow_queries(threshold_ms=1000)

        assert len(slow_queries) == 2
        assert all(q["duration_ms"] > 1000 for q in slow_queries)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_slow_queries_limit(self, performance_analytics):
        """Test limit parameter for slow queries"""
        # Record many slow queries
        for i in range(20):
            await performance_analytics.record_query_time(f"slow-{i}", 1500.0 + i)

        slow_queries = await performance_analytics.get_slow_queries(
            threshold_ms=1000,
            limit=10
        )

        assert len(slow_queries) == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_slow_queries_sorted(self, performance_analytics):
        """Test slow queries are sorted by duration"""
        await performance_analytics.record_query_time("slow3", 2000.0)
        await performance_analytics.record_query_time("slow1", 1500.0)
        await performance_analytics.record_query_time("slow2", 1800.0)

        slow_queries = await performance_analytics.get_slow_queries(threshold_ms=1000)

        # Should be sorted descending
        assert slow_queries[0]["duration_ms"] >= slow_queries[1]["duration_ms"]


# ============================================================================
# Test Metrics Reset
# ============================================================================

class TestResetMetrics:
    """Test reset_metrics method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_clears_all(self, performance_analytics):
        """Test reset clears all metrics"""
        # Record data
        await performance_analytics.record_query_time("test", 100.0)
        await performance_analytics.record_cache_hit()
        await performance_analytics.record_error("test", "op")

        # Reset
        await performance_analytics.reset_metrics()

        assert len(performance_analytics.query_times) == 0
        assert len(performance_analytics.counters) == 0


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in PerformanceAnalytics"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_metrics_db_error(self, performance_analytics, create_async_context_manager):
        """Test handling database errors when getting metrics"""
        # Record query time
        await performance_analytics.record_query_time("test", 100.0)

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("DB error"))
        ctx_mgr = create_async_context_manager(mock_conn)
        performance_analytics.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        metrics = await performance_analytics.get_performance_metrics()

        # Should include error but still have basic metrics
        assert "error" in metrics

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, performance_analytics):
        """Test handling Redis errors during recording"""
        performance_analytics.redis_client.incrbyfloat = AsyncMock(
            side_effect=Exception("Redis error")
        )

        # Should not raise exception
        await performance_analytics.record_query_time("test", 100.0)

        # Query time should still be recorded locally
        assert len(performance_analytics.query_times) == 1


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zero_query_time(self, performance_analytics):
        """Test recording zero query time"""
        await performance_analytics.record_query_time("instant", 0.0)

        assert performance_analytics.query_times[-1]["duration_ms"] == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_negative_query_time(self, performance_analytics):
        """Test recording negative query time (edge case)"""
        await performance_analytics.record_query_time("negative", -10.0)

        # Should still record
        assert performance_analytics.query_times[-1]["duration_ms"] == -10.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_very_large_query_time(self, performance_analytics):
        """Test recording very large query time"""
        await performance_analytics.record_query_time("very_slow", 1000000.0)

        assert performance_analytics.query_times[-1]["duration_ms"] == 1000000.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_operation_name(self, performance_analytics):
        """Test recording with empty operation name"""
        await performance_analytics.record_query_time("", 100.0)

        assert performance_analytics.query_times[-1]["operation"] == ""


# ============================================================================
# Test PerformanceMetrics Dataclass
# ============================================================================

class TestPerformanceMetricsDataclass:
    """Test PerformanceMetrics dataclass"""

    @pytest.mark.unit
    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics instance"""
        metrics = PerformanceMetrics(
            query_times_ms=[100.0, 200.0, 300.0],
            cache_hits=10,
            cache_misses=5,
            memory_operations=100,
            error_count=2,
            total_memories=50,
            active_agents=5
        )

        assert metrics.total_memories == 50
        assert metrics.active_agents == 5
        assert len(metrics.query_times_ms) == 3
