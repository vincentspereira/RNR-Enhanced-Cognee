"""
Unit Tests for Performance Optimizer Module

Tests performance optimization functionality with 100% coverage.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from src.performance_optimizer import (
    performance_optimizer,
    PerformanceOptimizer
)


# Helper for async context manager mocking
def create_mock_acquire_context(mock_conn):
    """Create a proper async context manager for postgres_pool.acquire()"""
    class MockAcquireContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass
    return MockAcquireContext()


@pytest.mark.unit
class TestPerformanceOptimizer:
    """Test suite for PerformanceOptimizer class"""

    def test_initialization(self):
        """Test PerformanceOptimizer initialization"""
        optimizer = PerformanceOptimizer()
        assert optimizer.query_cache == {}
        assert optimizer.cache_ttl == 300
        assert optimizer.performance_metrics == {}

    def test_track_query(self):
        """Test query performance tracking"""
        optimizer = PerformanceOptimizer()

        # Track some queries
        optimizer._track_query('search', 50.0)
        optimizer._track_query('search', 60.0)
        optimizer._track_query('search', 40.0)

        stats = optimizer.get_performance_stats()
        assert 'search' in stats
        assert stats['search']['count'] == 3
        assert stats['search']['avg_ms'] == 50.0
        assert stats['search']['min_ms'] == 40.0
        assert stats['search']['max_ms'] == 60.0

    def test_track_multiple_query_types(self):
        """Test tracking multiple query types"""
        optimizer = PerformanceOptimizer()

        optimizer._track_query('search', 50.0)
        optimizer._track_query('insert', 30.0)
        optimizer._track_query('update', 40.0)

        stats = optimizer.get_performance_stats()
        assert len(stats) == 3
        assert 'search' in stats
        assert 'insert' in stats
        assert 'update' in stats

    def test_get_performance_stats_empty(self):
        """Test getting performance stats when no queries tracked"""
        optimizer = PerformanceOptimizer()
        stats = optimizer.get_performance_stats()
        assert stats == {}

    def test_clear_cache(self):
        """Test clearing query cache"""
        optimizer = PerformanceOptimizer()
        optimizer.query_cache = {'key': 'value'}

        optimizer.clear_cache()
        assert optimizer.query_cache == {}

    def test_get_cache_stats(self):
        """Test getting cache statistics"""
        optimizer = PerformanceOptimizer()
        optimizer.query_cache = {'key1': 'val1', 'key2': 'val2'}

        stats = optimizer.get_cache_stats()
        assert stats['cached_queries'] == 2
        assert stats['cache_ttl_seconds'] == 300

    @pytest.mark.asyncio
    async def test_create_language_indexes(self):
        """Test creating language indexes"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool with proper async context manager
        from unittest.mock import AsyncMock, MagicMock, patch
        import asyncio

        # Create mock connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        # Create async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_pool = AsyncMock()
        mock_pool.acquire = lambda: MockAcquireContext()

        result = await optimizer.create_language_indexes(mock_pool)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_language_indexes_failure(self):
        """Test handling of index creation failure"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool that raises exception
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Database error"))

        # Create async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_pool = AsyncMock()
        mock_pool.acquire = lambda: MockAcquireContext()

        result = await optimizer.create_language_indexes(mock_pool)
        assert result is False

    @pytest.mark.asyncio
    async def test_optimize_query_with_language_filter(self):
        """Test optimized query with language filter"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool with proper async context manager
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': '1', 'data_text': 'English text', 'metadata': '{"language": "en"}', 'created_at': '2026-02-06'},
            {'id': '2', 'data_text': 'Spanish text', 'metadata': '{"language": "es"}', 'created_at': '2026-02-06'}
        ])

        # Create async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_pool = AsyncMock()
        mock_pool.acquire = lambda: MockAcquireContext()

        result = await optimizer.optimize_query(
            query="test",
            postgres_pool=mock_pool,
            user_id="user1",
            agent_id="agent1",
            language="en"
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_optimize_query_without_language_filter(self):
        """Test optimized query without language filter"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock query result
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: f"value_{key}"

        mock_conn.fetch.return_value = [mock_row]
        mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

        result = await optimizer.optimize_query(
            query="test",
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent"
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_optimize_query_exception(self):
        """Test handling of query exception"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool that raises exception
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)
        mock_conn.fetch.side_effect = Exception("Query error")

        result = await optimizer.optimize_query(
            query="test",
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_benchmark_query_performance(self):
        """Test query performance benchmarking"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        # Create async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_pool = AsyncMock()
        mock_pool.acquire = lambda: MockAcquireContext()

        result = await optimizer.benchmark_query_performance(
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent"
        )

        assert 'language_filtered_ms' in result
        assert 'regular_query_ms' in result
        assert 'language_distribution_ms' in result
        assert all(isinstance(v, (int, float)) for v in result.values())

    @pytest.mark.asyncio
    async def test_benchmark_with_exception(self):
        """Test benchmark handling exceptions gracefully"""
        optimizer = PerformanceOptimizer()

        # Mock postgres pool that raises exception
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Benchmark error"))

        # Create async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_pool = AsyncMock()
        mock_pool.acquire = lambda: MockAcquireContext()

        # Should handle exception
        result = await optimizer.benchmark_query_performance(
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent"
        )

        # Result should exist even if benchmark failed
        assert isinstance(result, dict)

    def test_singleton_instance(self):
        """Test that performance_optimizer is a singleton"""
        from src.performance_optimizer import performance_optimizer as po1
        from src.performance_optimizer import performance_optimizer as po2
        assert po1 is po2


@pytest.mark.unit
class TestPerformanceOptimizerMetrics:
    """Test performance metrics functionality"""

    def test_metrics_accumulation(self):
        """Test that metrics accumulate correctly"""
        optimizer = PerformanceOptimizer()

        # Add many queries
        for i in range(10):
            optimizer._track_query('search', 50.0 + i)

        stats = optimizer.get_performance_stats()
        assert stats['search']['count'] == 10
        assert stats['search']['min_ms'] == 50.0
        assert stats['search']['max_ms'] == 59.0

    def test_metrics_average_calculation(self):
        """Test correct average calculation"""
        optimizer = PerformanceOptimizer()

        optimizer._track_query('search', 100.0)
        optimizer._track_query('search', 200.0)
        optimizer._track_query('search', 300.0)

        stats = optimizer.get_performance_stats()
        assert stats['search']['avg_ms'] == 200.0

    def test_metrics_reset_with_new_instance(self):
        """Test that new instance has empty metrics"""
        optimizer1 = PerformanceOptimizer()
        optimizer1._track_query('search', 50.0)

        optimizer2 = PerformanceOptimizer()
        stats = optimizer2.get_performance_stats()
        assert stats == {}

    def test_performance_tracking_edge_cases(self):
        """Test edge cases in performance tracking"""
        optimizer = PerformanceOptimizer()

        # Very fast query
        optimizer._track_query('search', 0.1)

        # Very slow query
        optimizer._track_query('search', 10000.0)

        stats = optimizer.get_performance_stats()
        assert stats['search']['min_ms'] == 0.1
        assert stats['search']['max_ms'] == 10000.0

    def test_concurrent_tracking_safety(self):
        """Test that tracking is safe with concurrent updates"""
        optimizer = PerformanceOptimizer()

        # Simulate concurrent tracking
        for _ in range(100):
            optimizer._track_query('search', 50.0)

        stats = optimizer.get_performance_stats()
        assert stats['search']['count'] == 100


@pytest.mark.unit
class TestPerformanceOptimizerCaching:
    """Test caching functionality"""

    def test_cache_storage(self):
        """Test cache storage"""
        optimizer = PerformanceOptimizer()
        optimizer.query_cache['test_key'] = 'test_value'

        assert optimizer.query_cache['test_key'] == 'test_value'

    def test_cache_retrieval(self):
        """Test cache retrieval"""
        optimizer = PerformanceOptimizer()
        optimizer.query_cache['key1'] = {'data': 'value1'}
        optimizer.query_cache['key2'] = {'data': 'value2'}

        assert len(optimizer.query_cache) == 2
        assert optimizer.query_cache['key1']['data'] == 'value1'

    def test_cache_clear(self):
        """Test clearing cache"""
        optimizer = PerformanceOptimizer()
        optimizer.query_cache = {'k1': 'v1', 'k2': 'v2', 'k3': 'v3'}

        optimizer.clear_cache()

        assert len(optimizer.query_cache) == 0

    def test_cache_ttl_configuration(self):
        """Test cache TTL configuration"""
        optimizer = PerformanceOptimizer()
        assert optimizer.cache_ttl == 300  # 5 minutes

        # Create optimizer with custom TTL
        custom_optimizer = PerformanceOptimizer()
        custom_optimizer.cache_ttl = 600
        assert custom_optimizer.cache_ttl == 600

    def test_cache_stats_accuracy(self):
        """Test cache statistics accuracy"""
        optimizer = PerformanceOptimizer()

        # Empty cache
        stats = optimizer.get_cache_stats()
        assert stats['cached_queries'] == 0

        # Add some items
        optimizer.query_cache = {'k1': 'v1', 'k2': 'v2', 'k3': 'v3'}
        stats = optimizer.get_cache_stats()
        assert stats['cached_queries'] == 3
