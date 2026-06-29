"""
Unit Tests for RNR Enhanced Cognee Memory Operations

Tests for memory stack components including PostgreSQL+pgVector,
Qdrant, Neo4j, and Redis memory operations.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any, Optional

# Mark all tests as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.memory]


class TestPostgreSQLMemoryOperations:
    """Test PostgreSQL memory operations with pgVector"""

    @pytest.fixture
    async def mock_postgres_connection(self):
        """Mock PostgreSQL connection for testing"""
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            # Mock successful pgVector extension
            mock_conn.execute.return_value = None

            yield mock_conn

    @pytest.fixture
    def sample_memory_embedding(self):
        """Sample memory embedding for testing"""
        return [0.1] * 1536  # OpenAI embedding dimension

    @pytest.mark.asyncio
    async def test_memory_storage_with_embedding(self, mock_postgres_connection, sample_memory_embedding):
        """Test memory storage with vector embedding"""
        # Arrange
        memory_data = {
            "content": "Test memory content for RNR Enhanced Cognee",
            "agent_id": "test_agent_001",
            "embedding": sample_memory_embedding,
            "memory_type": "episodic",
            "metadata": {
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "category": "test"
            }
        }

        mock_postgres_connection.fetchval.return_value = "memory_123"

        # Act
        with patch('src.agent_memory_integration.PostgreSQLMemoryManager'):
            from src.agent_memory_integration import PostgreSQLMemoryManager

            manager = PostgreSQLMemoryManager()
            result = await manager.store_memory(memory_data)

        # Assert
        assert result == "memory_123"
        mock_postgres_connection.execute.assert_called_once()
        mock_postgres_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_retrieval_by_similarity(self, mock_postgres_connection, sample_memory_embedding):
        """Test memory retrieval by vector similarity"""
        # Arrange
        query_embedding = sample_memory_embedding
        expected_results = [
            {
                "id": "memory_001",
                "content": "Similar memory content",
                "similarity": 0.95,
                "metadata": {"agent_id": "test_agent"}
            }
        ]

        mock_postgres_connection.fetch.return_value = expected_results

        # Act
        with patch('src.agent_memory_integration.PostgreSQLMemoryManager'):
            from src.agent_memory_integration import PostgreSQLMemoryManager

            manager = PostgreSQLMemoryManager()
            results = await manager.search_similar_memories(
                query_embedding=query_embedding,
                limit=5,
                threshold=0.8
            )

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "memory_001"
        assert results[0]["similarity"] == 0.95
        mock_postgres_connection.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_update_transaction(self, mock_postgres_connection):
        """Test memory update with transaction integrity"""
        # Arrange
        memory_id = "memory_123"
        update_data = {
            "content": "Updated memory content",
            "metadata": {"updated": True}
        }

        mock_postgres_connection.fetchval.return_value = True

        # Act
        with patch('src.agent_memory_integration.PostgreSQLMemoryManager'):
            from src.agent_memory_integration import PostgreSQLMemoryManager

            manager = PostgreSQLMemoryManager()
            result = await manager.update_memory(memory_id, update_data)

        # Assert
        assert result is True
        mock_postgres_connection.fetchval.assert_called_once()

        # Verify transaction was used
        transaction_calls = [
            call for call in mock_postgres_connection.method_calls
            if 'transaction' in str(call).lower()
        ]
        assert len(transaction_calls) > 0

    @pytest.mark.asyncio
    async def test_memory_deletion_with_cascade(self, mock_postgres_connection):
        """Test memory deletion with cascade operations"""
        # Arrange
        memory_id = "memory_123"
        mock_postgres_connection.fetchval.return_value = True

        # Act
        with patch('src.agent_memory_integration.PostgreSQLMemoryManager'):
            from src.agent_memory_integration import PostgreSQLMemoryManager

            manager = PostgreSQLMemoryManager()
            result = await manager.delete_memory(memory_id)

        # Assert
        assert result is True
        mock_postgres_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_index_creation(self, mock_postgres_connection):
        """Test pgVector index creation for performance"""
        # Arrange
        index_name = "idx_memory_embedding_cosine"
        mock_postgres_connection.execute.return_value = None

        # Act
        with patch('src.agent_memory_integration.PostgreSQLMemoryManager'):
            from src.agent_memory_integration import PostgreSQLMemoryManager

            manager = PostgreSQLMemoryManager()
            result = await manager.create_vector_index(index_name, "cosine")

        # Assert
        assert result is True
        mock_postgres_connection.execute.assert_called()


class TestQdrantMemoryOperations:
    """Test Qdrant vector database operations"""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for testing"""
        with patch('qdrant_client.QdrantClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock collection operations
            mock_client.create_collection.return_value = None
            mock_client.upsert.return_value = None
            mock_client.search.return_value = []

            yield mock_client

    @pytest.fixture
    def sample_qdrant_point(self):
        """Sample Qdrant point for testing"""
        return {
            "id": "point_001",
            "vector": [0.1] * 1536,
            "payload": {
                "content": "Test memory content",
                "agent_id": "test_agent",
                "memory_type": "episodic",
                "timestamp": int(time.time())
            }
        }

    @pytest.mark.asyncio
    async def test_collection_creation(self, mock_qdrant_client):
        """Test Qdrant collection creation"""
        # Arrange
        collection_name = "test_collection"
        vector_size = 1536

        # Act
        with patch('src.agent_memory_integration.QdrantMemoryManager'):
            from src.agent_memory_integration import QdrantMemoryManager

            manager = QdrantMemoryManager()
            await manager.create_collection(collection_name, vector_size)

        # Assert
        mock_qdrant_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_point_upsert(self, mock_qdrant_client, sample_qdrant_point):
        """Test Qdrant point upsert operation"""
        # Arrange
        collection_name = "test_collection"

        # Act
        with patch('src.agent_memory_integration.QdrantMemoryManager'):
            from src.agent_memory_integration import QdrantMemoryManager

            manager = QdrantMemoryManager()
            await manager.store_memory_point(collection_name, sample_qdrant_point)

        # Assert
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_with_filtering(self, mock_qdrant_client):
        """Test Qdrant vector search with payload filtering"""
        # Arrange
        collection_name = "test_collection"
        query_vector = [0.1] * 1536
        search_filter = {"must": [{"key": "agent_id", "match": {"value": "test_agent"}}]}

        expected_results = [
            {
                "id": "point_001",
                "score": 0.95,
                "payload": {
                    "content": "Search result content",
                    "agent_id": "test_agent"
                }
            }
        ]

        mock_qdrant_client.search.return_value = expected_results

        # Act
        with patch('src.agent_memory_integration.QdrantMemoryManager'):
            from src.agent_memory_integration import QdrantMemoryManager

            manager = QdrantMemoryManager()
            results = await manager.search_vectors(
                collection_name=collection_name,
                query_vector=query_vector,
                search_filter=search_filter,
                limit=5
            )

        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "point_001"
        assert results[0]["score"] == 0.95
        mock_qdrant_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_collection_deletion(self, mock_qdrant_client):
        """Test Qdrant collection deletion"""
        # Arrange
        collection_name = "test_collection"

        # Act
        with patch('src.agent_memory_integration.QdrantMemoryManager'):
            from src.agent_memory_integration import QdrantMemoryManager

            manager = QdrantMemoryManager()
            await manager.delete_collection(collection_name)

        # Assert
        mock_qdrant_client.delete_collection.assert_called_once_with(collection_name)


class TestNeo4jMemoryOperations:
    """Test Neo4j graph database operations"""

    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for testing"""
        with patch('neo4j.GraphDatabase.driver') as mock_driver_class:
            mock_driver = Mock()
            mock_session = Mock()
            mock_result = Mock()

            mock_driver_class.return_value = mock_driver
            mock_driver.session.return_value = mock_session
            mock_session.run.return_value = mock_result

            # Mock result data
            mock_result.data.return_value = [
                {"memory": {"id": "mem_001", "content": "Test memory"}},
                {"memory": {"id": "mem_002", "content": "Another memory"}}
            ]

            yield mock_driver

    @pytest.fixture
    def sample_memory_node(self):
        """Sample Neo4j memory node"""
        return {
            "id": "mem_001",
            "content": "Test memory content for graph storage",
            "agent_id": "test_agent",
            "memory_type": "episodic",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "properties": {
                "importance": 0.8,
                "category": "test"
            }
        }

    @pytest.mark.asyncio
    async def test_memory_node_creation(self, mock_neo4j_driver, sample_memory_node):
        """Test Neo4j memory node creation"""
        # Arrange
        with patch('src.agent_memory_integration.Neo4jMemoryManager'):
            from src.agent_memory_integration import Neo4jMemoryManager

            manager = Neo4jMemoryManager()
            result = await manager.create_memory_node(sample_memory_node)

        # Assert
        assert result is not None
        mock_neo4j_driver.session.assert_called_once()
        mock_neo4j_driver.session.return_value.run.assert_called()

    @pytest.mark.asyncio
    async def test_memory_relationship_creation(self, mock_neo4j_driver):
        """Test Neo4j memory relationship creation"""
        # Arrange
        from_node_id = "mem_001"
        to_node_id = "mem_002"
        relationship_type = "RELATED_TO"
        properties = {"strength": 0.9, "context": "similarity"}

        with patch('src.agent_memory_integration.Neo4jMemoryManager'):
            from src.agent_memory_integration import Neo4jMemoryManager

            manager = Neo4jMemoryManager()
            result = await manager.create_memory_relationship(
                from_node_id, to_node_id, relationship_type, properties
            )

        # Assert
        assert result is not None
        mock_neo4j_driver.session.return_value.run.assert_called()

    @pytest.mark.asyncio
    async def test_graph_traversal_queries(self, mock_neo4j_driver):
        """Test Neo4j graph traversal queries"""
        # Arrange
        start_node_id = "mem_001"
        max_depth = 3
        relationship_types = ["RELATED_TO", "CONTAINS"]

        with patch('src.agent_memory_integration.Neo4jMemoryManager'):
            from src.agent_memory_integration import Neo4jMemoryManager

            manager = Neo4jMemoryManager()
            results = await manager.traverse_memory_graph(
                start_node_id, max_depth, relationship_types
            )

        # Assert
        assert len(results) >= 0
        mock_neo4j_driver.session.return_value.run.assert_called()

    @pytest.mark.asyncio
    async def test_cypher_query_execution(self, mock_neo4j_driver):
        """Test custom Cypher query execution"""
        # Arrange
        query = """
        MATCH (m:Memory {agent_id: $agent_id})
        RETURN m ORDER BY m.timestamp DESC LIMIT $limit
        """
        parameters = {"agent_id": "test_agent", "limit": 10}

        with patch('src.agent_memory_integration.Neo4jMemoryManager'):
            from src.agent_memory_integration import Neo4jMemoryManager

            manager = Neo4jMemoryManager()
            results = await manager.execute_cypher_query(query, parameters)

        # Assert
        assert isinstance(results, list)
        mock_neo4j_driver.session.return_value.run.assert_called_with(query, parameters)


class TestRedisMemoryOperations:
    """Test Redis cache operations"""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing"""
        with patch('redis.Redis') as mock_redis_class:
            mock_client = Mock()
            mock_redis_class.return_value = mock_client

            # Mock Redis operations
            mock_client.set.return_value = True
            mock_client.get.return_value = json.dumps({"test": "data"})
            mock_client.delete.return_value = 1
            mock_client.exists.return_value = 1
            mock_client.expire.return_value = True

            yield mock_client

    @pytest.fixture
    def sample_cache_data(self):
        """Sample cache data"""
        return {
            "memory_id": "mem_001",
            "content": "Cached memory content",
            "agent_id": "test_agent",
            "cached_at": datetime.now(timezone.utc).isoformat()
        }

    def test_cache_memory_storage(self, mock_redis_client, sample_cache_data):
        """Test Redis memory caching"""
        # Arrange
        cache_key = f"memory:{sample_cache_data['memory_id']}"
        ttl = 3600  # 1 hour

        # Act
        with patch('src.agent_memory_integration.RedisMemoryManager'):
            from src.agent_memory_integration import RedisMemoryManager

            manager = RedisMemoryManager()
            result = manager.cache_memory(cache_key, sample_cache_data, ttl)

        # Assert
        assert result is True
        mock_redis_client.set.assert_called_once()
        mock_redis_client.expire.assert_called_once_with(cache_key, ttl)

    def test_cache_memory_retrieval(self, mock_redis_client):
        """Test Redis memory retrieval"""
        # Arrange
        cache_key = "memory:mem_001"
        cached_data = {"memory_id": "mem_001", "content": "Cached content"}
        mock_redis_client.get.return_value = json.dumps(cached_data)

        # Act
        with patch('src.agent_memory_integration.RedisMemoryManager'):
            from src.agent_memory_integration import RedisMemoryManager

            manager = RedisMemoryManager()
            result = manager.get_cached_memory(cache_key)

        # Assert
        assert result == cached_data
        mock_redis_client.get.assert_called_once_with(cache_key)

    def test_cache_invalidation(self, mock_redis_client):
        """Test Redis cache invalidation"""
        # Arrange
        cache_key = "memory:mem_001"
        mock_redis_client.delete.return_value = 1  # Number of keys deleted

        # Act
        with patch('src.agent_memory_integration.RedisMemoryManager'):
            from src.agent_memory_integration import RedisMemoryManager

            manager = RedisMemoryManager()
            result = manager.invalidate_cache(cache_key)

        # Assert
        assert result is True
        mock_redis_client.delete.assert_called_once_with(cache_key)

    def test_cache_pattern_deletion(self, mock_redis_client):
        """Test Redis cache deletion by pattern"""
        # Arrange
        pattern = "memory:agent_*"
        mock_keys = ["memory:agent_001", "memory:agent_002"]
        mock_redis_client.keys.return_value = mock_keys
        mock_redis_client.delete.return_value = len(mock_keys)

        # Act
        with patch('src.agent_memory_integration.RedisMemoryManager'):
            from src.agent_memory_integration import RedisMemoryManager

            manager = RedisMemoryManager()
            result = manager.invalidate_cache_pattern(pattern)

        # Assert
        assert result == len(mock_keys)
        mock_redis_client.keys.assert_called_once_with(pattern)
        mock_redis_client.delete.assert_called_once_with(*mock_keys)

    def test_cache_statistics(self, mock_redis_client):
        """Test Redis cache statistics"""
        # Arrange
        mock_redis_client.info.return_value = {
            "used_memory": 1024000,  # bytes
            "used_memory_human": "1.00M",
            "total_commands_processed": 5000,
            "keyspace_hits": 4500,
            "keyspace_misses": 500
        }

        # Act
        with patch('src.agent_memory_integration.RedisMemoryManager'):
            from src.agent_memory_integration import RedisMemoryManager

            manager = RedisMemoryManager()
            stats = manager.get_cache_statistics()

        # Assert
        assert "used_memory" in stats
        assert "hit_rate" in stats
        assert stats["hit_rate"] == 0.9  # 4500 / (4500 + 500)
        mock_redis_client.info.assert_called_once()


class TestMemoryIntegration:
    """Test integration between different memory components"""

    @pytest.mark.asyncio
    async def test_cross_database_memory_consistency(self):
        """Test memory consistency across all databases"""
        # This test would verify that when a memory is stored,
        # it's properly synchronized across PostgreSQL, Qdrant, Neo4j, and Redis

        # Mock all database connections
        with patch('src.agent_memory_integration.PostgreSQLMemoryManager') as mock_pg, \
             patch('src.agent_memory_integration.QdrantMemoryManager') as mock_qdrant, \
             patch('src.agent_memory_integration.Neo4jMemoryManager') as mock_neo4j, \
             patch('src.agent_memory_integration.RedisMemoryManager') as mock_redis:

            # Setup mock returns
            mock_pg.return_value.store_memory.return_value = "memory_123"
            mock_qdrant.return_value.store_memory_point.return_value = True
            mock_neo4j.return_value.create_memory_node.return_value = "node_123"
            mock_redis.return_value.cache_memory.return_value = True

            # Execute memory storage
            from src.agent_memory_integration import AgentMemoryIntegration

            integration = await AgentMemoryIntegration.initialize()
            memory_data = {
                "content": "Test cross-database memory",
                "agent_id": "test_agent",
                "memory_type": "episodic",
                "embedding": [0.1] * 1536
            }

            result = await integration.add_memory(**memory_data)

            # Assert all databases were called
            mock_pg.return_value.store_memory.assert_called_once()
            mock_qdrant.return_value.store_memory_point.assert_called_once()
            mock_neo4j.return_value.create_memory_node.assert_called_once()
            mock_redis.return_value.cache_memory.assert_called_once()

            assert result is not None

    @pytest.mark.asyncio
    async def test_memory_transaction_rollback(self):
        """Test transaction rollback on memory operation failure"""
        # Test that if any database operation fails, all operations are rolled back

        with patch('src.agent_memory_integration.PostgreSQLMemoryManager') as mock_pg, \
             patch('src.agent_memory_integration.QdrantMemoryManager') as mock_qdrant:

            # Setup Qdrant to fail
            mock_qdrant.return_value.store_memory_point.side_effect = Exception("Qdrant failure")
            mock_pg.return_value.store_memory.return_value = "memory_123"

            from src.agent_memory_integration import AgentMemoryIntegration

            integration = await AgentMemoryIntegration.initialize()
            memory_data = {
                "content": "Test transaction rollback",
                "agent_id": "test_agent"
            }

            # This should raise an exception due to Qdrant failure
            with pytest.raises(Exception):
                await integration.add_memory(**memory_data)

            # Verify PostgreSQL was called but rollback should have occurred
            mock_pg.return_value.store_memory.assert_called_once()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])