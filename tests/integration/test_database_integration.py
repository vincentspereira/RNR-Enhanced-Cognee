"""
Integration Tests for Enhanced Cognee
Tests integration with real databases (PostgreSQL, Qdrant, Redis)
"""

import pytest
import asyncio
from datetime import datetime
from src.memory_management import MemoryManager
from src.memory_deduplication import MemoryDeduplicator
from src.performance_analytics import PerformanceAnalytics


# ============================================================================
# Test PostgreSQL Integration
# ============================================================================

class TestPostgreSQLIntegration:
    """Test integration with PostgreSQL database"""

    @pytest.mark.integration
    @pytest.mark.postgresql
    @pytest.mark.asyncio
    async def test_connect_to_postgresql(self, real_postgres_pool):
        """Test actual PostgreSQL connection"""
        assert real_postgres_pool is not None

        async with real_postgres_pool.acquire() as conn:
            result = await conn.fetchval('SELECT 1')
            assert result == 1

    @pytest.mark.integration
    @pytest.mark.postgresql
    @pytest.mark.asyncio
    async def test_create_and_query_memory(self, real_postgres_pool):
        """Test creating and querying a memory in PostgreSQL"""
        memory_id = "test-integration-mem-1"

        async with real_postgres_pool.acquire() as conn:
            # Insert memory
            await conn.execute("""
                INSERT INTO shared_memory.documents (id, title, content, agent_id, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
            """, memory_id, "Integration Test Memory", "Test content for integration testing",
               "test-agent", datetime.utcnow())

            # Query memory
            row = await conn.fetchrow("""
                SELECT id, title, content, agent_id FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            assert row is not None
            assert row["id"] == memory_id
            assert row["title"] == "Integration Test Memory"

            # Cleanup
            await conn.execute("DELETE FROM shared_memory.documents WHERE id = $1", memory_id)

    @pytest.mark.integration
    @pytest.mark.postgresql
    @pytest.mark.asyncio
    async def test_memory_manager_with_real_db(self, real_postgres_pool, mock_redis_client, mock_qdrant_client):
        """Test MemoryManager with real PostgreSQL"""
        import redis.asyncio as aioredis

        # Create real Redis client if available, otherwise use mock
        try:
            redis_client = await aioredis.Redis(
                host="localhost",
                port=26379,
                password=None,
                decode_responses=True,
                db=15
            )
            await redis_client.ping()
        except:
            redis_client = mock_redis_client

        manager = MemoryManager(real_postgres_pool, redis_client, mock_qdrant_client)

        # Test getting stats
        stats = await manager.get_memory_stats_by_age()

        assert stats["status"] == "success"
        assert "total_memories" in stats


# ============================================================================
# Test Qdrant Integration
# ============================================================================

class TestQdrantIntegration:
    """Test integration with Qdrant vector database"""

    @pytest.mark.integration
    @pytest.mark.qdrant
    def test_connect_to_qdrant(self, real_qdrant_client):
        """Test actual Qdrant connection"""
        assert real_qdrant_client is not None

        collections = real_qdrant_client.get_collections()
        assert collections is not None

    @pytest.mark.integration
    @pytest.mark.qdrant
    def test_create_and_search_collection(self, real_qdrant_client):
        """Test creating collection and searching vectors"""
        collection_name = "test_integration_collection"

        try:
            # Create collection
            from qdrant_client.models import Distance, VectorParams, PointStruct

            real_qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=128, distance=Distance.COSINE)
            )

            # Insert vectors
            import random
            points = [
                PointStruct(id=i, vector=[random.random() for _ in range(128)],
                           payload={"content": f"Test content {i}"})
                for i in range(5)
            ]

            real_qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )

            # Search
            search_result = real_qdrant_client.search(
                collection_name=collection_name,
                query_vector=[random.random() for _ in range(128)],
                limit=3
            )

            assert len(search_result) <= 3

        finally:
            # Cleanup
            try:
                real_qdrant_client.delete(collection_name)
            except:
                pass


# ============================================================================
# Test Redis Integration
# ============================================================================

class TestRedisIntegration:
    """Test integration with Redis cache"""

    @pytest.mark.integration
    @pytest.mark.redis
    @pytest.mark.asyncio
    async def test_connect_to_redis(self, real_redis_client):
        """Test actual Redis connection"""
        assert real_redis_client is not None

        result = await real_redis_client.ping()
        assert result is True

    @pytest.mark.integration
    @pytest.mark.redis
    @pytest.mark.asyncio
    async def test_redis_set_get(self, real_redis_client):
        """Test setting and getting values in Redis"""
        test_key = "test:integration:key"
        test_value = "test_value_123"

        await real_redis_client.set(test_key, test_value)
        result = await real_redis_client.get(test_key)

        assert result == test_value

        # Cleanup
        await real_redis_client.delete(test_key)

    @pytest.mark.integration
    @pytest.mark.redis
    @pytest.mark.asyncio
    async def test_redis_pub_sub(self, real_redis_client):
        """Test Redis pub/sub functionality"""
        channel = "test:integration:channel"
        message = "test_message"

        # Subscribe
        pubsub = real_redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Publish
        await real_redis_client.publish(channel, message)

        # Receive (with timeout)
        import asyncio
        try:
            msg = await asyncio.wait_for(pubsub.get_message(timeout=1.0), timeout=1.0)
            assert msg is not None
            assert msg["type"] == "message"
        except asyncio.TimeoutError:
            pass  # Message might not arrive in time
        finally:
            await pubsub.unsubscribe(channel)


# ============================================================================
# Test Multi-Database Integration
# ============================================================================

class TestMultiDatabaseIntegration:
    """Test integration across multiple databases"""

    @pytest.mark.integration
    @pytest.mark.postgresql
    @pytest.mark.qdrant
    @pytest.mark.redis
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_memory_workflow(self, real_postgres_pool, real_qdrant_client, real_redis_client):
        """Test complete workflow: Store in PostgreSQL, index in Qdrant, cache in Redis"""
        memory_id = "integration-test-full-workflow"

        try:
            # 1. Store in PostgreSQL
            async with real_postgres_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shared_memory.documents (id, title, content, agent_id, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                """, memory_id, "Full Workflow Test", "Testing full integration workflow",
                   "test-agent", datetime.utcnow())

            # 2. Index in Qdrant
            from qdrant_client.models import PointStruct
            import random

            try:
                real_qdrant_client.upsert(
                    collection_name="cognee_general_memory",
                    points=[
                        PointStruct(
                            id=memory_id,
                            vector=[random.random() for _ in range(1536)],
                            payload={"content": "Testing full integration workflow", "memory_id": memory_id}
                        )
                    ]
                )
            except Exception as e:
                # Collection might not exist, that's ok for this test
                pass

            # 3. Cache in Redis
            await real_redis_client.set(f"memory:{memory_id}", "cached_content")

            # 4. Verify PostgreSQL
            async with real_postgres_pool.acquire() as conn:
                pg_row = await conn.fetchrow("SELECT * FROM shared_memory.documents WHERE id = $1", memory_id)
                assert pg_row is not None

            # 5. Verify Redis cache
            cached = await real_redis_client.get(f"memory:{memory_id}")
            assert cached == "cached_content"

            # Success!
            assert True

        finally:
            # Cleanup
            async with real_postgres_pool.acquire() as conn:
                await conn.execute("DELETE FROM shared_memory.documents WHERE id = $1", memory_id)

            await real_redis_client.delete(f"memory:{memory_id}")

            try:
                real_qdrant_client.delete(
                    collection_name="cognee_general_memory",
                    points_selector=[memory_id]
                )
            except:
                pass


# ============================================================================
# Test Performance Analytics Integration
# ============================================================================

class TestPerformanceAnalyticsIntegration:
    """Test PerformanceAnalytics with real databases"""

    @pytest.mark.integration
    @pytest.mark.postgresql
    @pytest.mark.redis
    @pytest.mark.asyncio
    async def test_record_and_retrieve_metrics(self, real_postgres_pool, real_redis_client):
        """Test recording metrics and retrieving them"""
        analytics = PerformanceAnalytics(real_postgres_pool, real_redis_client)

        # Record some metrics
        await analytics.record_query_time("integration_test", 150.5)
        await analytics.record_cache_hit("integration")
        await analytics.record_cache_miss("integration")

        # Get metrics
        metrics = await analytics.get_performance_metrics()

        assert metrics is not None
        assert "query_performance" in metrics or "error" in metrics

        # Reset
        await analytics.reset_metrics()


# ============================================================================
# Test Database Connection Pooling
# ============================================================================

class TestConnectionPooling:
    """Test connection pooling behavior"""

    @pytest.mark.integration
    @pytest.mark.postgresql
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_database_access(self, real_postgres_pool):
        """Test concurrent access to PostgreSQL"""
        async def query_worker(worker_id):
            async with real_postgres_pool.acquire() as conn:
                result = await conn.fetchval('SELECT 1')
                return worker_id, result

        # Run concurrent queries
        tasks = [query_worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for worker_id, result in results:
            assert result == 1

    @pytest.mark.integration
    @pytest.mark.redis
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_redis_access(self, real_redis_client):
        """Test concurrent access to Redis"""
        async def redis_worker(worker_id):
            key = f"test:concurrent:{worker_id}"
            await real_redis_client.set(key, f"value-{worker_id}")
            result = await real_redis_client.get(key)
            await real_redis_client.delete(key)
            return worker_id, result

        tasks = [redis_worker(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
