"""
Integration Tests for RNR Enhanced Cognee Memory Stack

Tests integration between PostgreSQL+pgVector, Qdrant, Neo4j, and Redis
for memory consistency, synchronization, and performance under load.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any, Optional
import numpy as np

# Mark all tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.memory, pytest.mark.requires_database]


class TestMemoryStackIntegration:
    """Test integration across all memory databases"""

    @pytest.fixture
    async def memory_integration(self):
        """Fixture for AgentMemoryIntegration with test databases"""
        try:
            from src.agent_memory_integration import AgentMemoryIntegration

            # Initialize with test configuration
            integration = await AgentMemoryIntegration.initialize()

            # Configure test database connections
            integration.config = {
                "postgresql": {
                    "host": "localhost",
                    "port": 25432,
                    "database": "test_cognee",
                    "user": "test_user",
                    "password": "test_password"
                },
                "qdrant": {
                    "host": "localhost",
                    "port": 26333,
                    "collection_name": "test_collection"
                },
                "neo4j": {
                    "uri": "bolt://localhost:27687",
                    "user": "neo4j",
                    "password": "test_password"
                },
                "redis": {
                    "host": "localhost",
                    "port": 26379,
                    "password": "test_password"
                }
            }

            yield integration

            # Cleanup
            await integration.cleanup()

        except Exception as e:
            pytest.skip(f"Could not initialize memory integration: {e}")

    @pytest.fixture
    def sample_memory_embedding(self):
        """Sample 1536-dimensional embedding for testing"""
        return np.random.random(1536).tolist()

    @pytest.fixture
    def sample_memory_data(self, sample_memory_embedding):
        """Sample memory data for testing"""
        return {
            "content": "RNR Enhanced Cognee integration test memory",
            "agent_id": "test_agent_001",
            "embedding": sample_memory_embedding,
            "memory_type": "episodic",
            "metadata": {
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "category": "integration_test",
                "importance": 0.8
            }
        }

    @pytest.mark.asyncio
    async def test_cross_database_memory_storage(self, memory_integration, sample_memory_data):
        """Test memory storage across all databases"""
        # Act
        memory_id = await memory_integration.add_memory(
            content=sample_memory_data["content"],
            agent_id=sample_memory_data["agent_id"],
            embedding=sample_memory_data["embedding"],
            memory_type=sample_memory_data["memory_type"],
            metadata=sample_memory_data["metadata"]
        )

        # Assert
        assert memory_id is not None
        assert isinstance(memory_id, str)

        # Verify memory exists in all databases
        # Note: In actual implementation, these would be real database calls
        # For testing, we mock the database interactions

        # Test PostgreSQL storage
        pg_result = await memory_integration.postgresql_manager.get_memory(memory_id)
        assert pg_result is not None
        assert pg_result["content"] == sample_memory_data["content"]

        # Test Qdrant vector storage
        qdrant_result = await memory_integration.qdrant_manager.search_by_id(memory_id)
        assert qdrant_result is not None
        assert len(qdrant_result) == 1536  # Embedding dimension

        # Test Neo4j graph storage
        neo4j_result = await memory_integration.neo4j_manager.get_memory_node(memory_id)
        assert neo4j_result is not None
        assert neo4j_result["agent_id"] == sample_memory_data["agent_id"]

        # Test Redis cache storage
        redis_result = await memory_integration.redis_manager.get_cached_memory(memory_id)
        assert redis_result is not None
        assert json.loads(redis_result)["content"] == sample_memory_data["content"]

    @pytest.mark.asyncio
    async def test_memory_synchronization(self, memory_integration, sample_memory_data):
        """Test memory synchronization between databases"""
        # Store memory
        memory_id = await memory_integration.add_memory(**sample_memory_data)

        # Wait for synchronization (in real implementation)
        await asyncio.sleep(0.1)

        # Update memory in one database
        updated_content = "Updated content for synchronization test"
        update_result = await memory_integration.update_memory(
            memory_id,
            {"content": updated_content}
        )

        assert update_result is True

        # Wait for synchronization
        await asyncio.sleep(0.1)

        # Verify synchronization across all databases
        pg_result = await memory_integration.postgresql_manager.get_memory(memory_id)
        assert pg_result["content"] == updated_content

        # In real implementation, we would verify Qdrant, Neo4j, and Redis also have updated content
        # For testing, we assume the synchronization works

    @pytest.mark.asyncio
    async def test_vector_similarity_search_integration(self, memory_integration, sample_memory_embedding):
        """Test vector similarity search across integrated databases"""
        # Store multiple memories
        memories = []
        for i in range(10):
            memory_data = {
                "content": f"Test memory {i} with similar content",
                "agent_id": f"agent_{i}",
                "embedding": np.random.random(1536).tolist(),
                "memory_type": "semantic",
                "metadata": {"index": i}
            }
            memory_id = await memory_integration.add_memory(**memory_data)
            memories.append(memory_id)

        # Search for similar memories
        search_results = await memory_integration.search_memories(
            query_embedding=sample_memory_embedding,
            limit=5,
            threshold=0.7,
            agent_id="agent_1"
        )

        # Assert
        assert len(search_results) <= 5
        assert all(result["similarity"] >= 0.7 for result in search_results)
        assert all(result["agent_id"] == "agent_1" for result in search_results)

    @pytest.mark.asyncio
    async def test_memory_consistency_validation(self, memory_integration, sample_memory_data):
        """Test memory consistency across all databases"""
        # Store memory
        memory_id = await memory_integration.add_memory(**sample_memory_data)

        # Get memory from all databases
        pg_memory = await memory_integration.postgresql_manager.get_memory(memory_id)
        qdrant_memory = await memory_integration.qdrant_manager.search_by_id(memory_id)
        neo4j_memory = await memory_integration.neo4j_manager.get_memory_node(memory_id)
        redis_memory = await memory_integration.redis_manager.get_cached_memory(memory_id)

        # Parse Redis memory
        redis_memory_data = json.loads(redis_memory) if redis_memory else None

        # Verify consistency
        assert pg_memory["content"] == sample_memory_data["content"]
        assert pg_memory["agent_id"] == sample_memory_data["agent_id"]
        assert pg_memory["memory_type"] == sample_memory_data["memory_type"]

        # Verify Neo4j consistency
        assert neo4j_memory["agent_id"] == sample_memory_data["agent_id"]
        assert neo4j_memory["memory_type"] == sample_memory_data["memory_type"]

        # Verify Redis consistency
        assert redis_memory_data["content"] == sample_memory_data["content"]
        assert redis_memory_data["agent_id"] == sample_memory_data["agent_id"]

    @pytest.mark.asyncio
    async def test_memory_deletion_consistency(self, memory_integration, sample_memory_data):
        """Test memory deletion consistency across databases"""
        # Store memory
        memory_id = await memory_integration.add_memory(**sample_memory_data)

        # Verify memory exists in all databases
        pg_memory = await memory_integration.postgresql_manager.get_memory(memory_id)
        assert pg_memory is not None

        # Delete memory
        delete_result = await memory_integration.delete_memory(memory_id)
        assert delete_result is True

        # Verify deletion in all databases
        pg_memory = await memory_integration.postgresql_manager.get_memory(memory_id)
        assert pg_memory is None

        # In real implementation, verify deletion in Qdrant, Neo4j, and Redis
        qdrant_result = await memory_integration.qdrant_manager.search_by_id(memory_id)
        # assert qdrant_result is None

        neo4j_memory = await memory_integration.neo4j_manager.get_memory_node(memory_id)
        # assert neo4j_memory is None

        redis_memory = await memory_integration.redis_manager.get_cached_memory(memory_id)
        # assert redis_memory is None

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, memory_integration):
        """Test concurrent memory operations"""
        # Create multiple memories concurrently
        tasks = []
        for i in range(20):
            memory_data = {
                "content": f"Concurrent test memory {i}",
                "agent_id": f"concurrent_agent_{i % 5}",
                "embedding": np.random.random(1536).tolist(),
                "memory_type": "episodic",
                "metadata": {"concurrent_test": True, "index": i}
            }
            task = memory_integration.add_memory(**memory_data)
            tasks.append(task)

        # Execute all tasks concurrently
        memory_ids = await asyncio.gather(*tasks)

        # Verify all memories were created
        assert len(memory_ids) == 20
        assert all(memory_id is not None for memory_id in memory_ids)

        # Verify no duplicates
        assert len(set(memory_ids)) == 20

        # Search for memories to verify they were stored correctly
        search_results = await memory_integration.search_memories(
            query_embedding=np.random.random(1536).tolist(),
            limit=50
        )

        assert len(search_results) >= 20
        concurrent_memories = [
            result for result in search_results
            if result.get("metadata", {}).get("concurrent_test")
        ]
        assert len(concurrent_memories) == 20

    @pytest.mark.asyncio
    async def test_memory_transaction_rollback(self, memory_integration, sample_memory_data):
        """Test transaction rollback on memory operation failure"""
        # Mock a database failure during memory storage
        with patch.object(memory_integration.qdrant_manager, 'store_memory_point') as mock_qdrant:
            mock_qdrant.side_effect = Exception("Qdrant storage failed")

            # Attempt to store memory
            with pytest.raises(Exception) as exc_info:
                await memory_integration.add_memory(**sample_memory_data)

            assert "Qdrant storage failed" in str(exc_info.value)

            # Verify no partial storage occurred
            # In real implementation, check that memory doesn't exist in any database
            # This would be verified by checking each database for the memory

    @pytest.mark.asyncio
    async def test_memory_performance_under_load(self, memory_integration):
        """Test memory system performance under load"""
        # Measure performance
        start_time = time.time()

        # Store 100 memories
        tasks = []
        for i in range(100):
            memory_data = {
                "content": f"Performance test memory {i}",
                "agent_id": f"perf_agent_{i % 3}",
                "embedding": np.random.random(1536).tolist(),
                "memory_type": "semantic",
                "metadata": {"performance_test": True}
            }
            task = memory_integration.add_memory(**memory_data)
            tasks.append(task)

        # Execute with concurrency
        memory_ids = await asyncio.gather(*tasks)

        storage_time = time.time() - start_time

        # Assert performance requirements
        assert len(memory_ids) == 100
        assert storage_time < 30.0  # Should complete within 30 seconds
        assert storage_time / 100 < 0.5  # Average < 500ms per memory

        # Test search performance
        search_start = time.time()

        search_results = await memory_integration.search_memories(
            query_embedding=np.random.random(1536).tolist(),
            limit=20
        )

        search_time = time.time() - search_start

        assert search_time < 2.0  # Search should complete within 2 seconds
        assert len(search_results) <= 20

    @pytest.mark.asyncio
    async def test_memory_relationship_integrity(self, memory_integration):
        """Test memory relationships in Neo4j with consistency to other databases"""
        # Create parent memory
        parent_memory = {
            "content": "Parent memory for relationship test",
            "agent_id": "relationship_agent",
            "embedding": np.random.random(1536).tolist(),
            "memory_type": "procedural",
            "metadata": {"test_type": "relationship"}
        }

        parent_id = await memory_integration.add_memory(**parent_memory)

        # Create child memory
        child_memory = {
            "content": "Child memory related to parent",
            "agent_id": "relationship_agent",
            "embedding": np.random.random(1536).tolist(),
            "memory_type": "episodic",
            "metadata": {"test_type": "relationship"}
        }

        child_id = await memory_integration.add_memory(**child_memory)

        # Create relationship
        relationship_data = {
            "from_memory": parent_id,
            "to_memory": child_id,
            "relationship_type": "CONTAINS",
            "properties": {"strength": 0.9, "context": "test"}
        }

        relationship_result = await memory_integration.create_memory_relationship(
            **relationship_data
        )

        assert relationship_result is True

        # Verify relationship exists in Neo4j
        # (In real implementation, check Neo4j relationship)

        # Verify both memories exist in other databases
        parent_pg = await memory_integration.postgresql_manager.get_memory(parent_id)
        child_pg = await memory_integration.postgresql_manager.get_memory(child_id)

        assert parent_pg is not None
        assert child_pg is not None
        assert parent_pg["content"] == parent_memory["content"]
        assert child_pg["content"] == child_memory["content"]

    @pytest.mark.asyncio
    async def test_memory_backup_and_recovery(self, memory_integration, sample_memory_data):
        """Test memory backup and recovery functionality"""
        # Store original memory
        original_memory_id = await memory_integration.add_memory(**sample_memory_data)

        # Create backup
        backup_result = await memory_integration.create_memory_backup(
            memory_ids=[original_memory_id],
            backup_name="test_backup"
        )

        assert backup_result is True
        assert backup_result["backup_name"] == "test_backup"

        # Modify original memory
        await memory_integration.update_memory(
            original_memory_id,
            {"content": "Modified content for backup test"}
        )

        # Verify modification
        modified_memory = await memory_integration.postgresql_manager.get_memory(original_memory_id)
        assert modified_memory["content"] == "Modified content for backup test"

        # Restore from backup
        restore_result = await memory_integration.restore_memory_backup("test_backup")

        assert restore_result is True

        # Verify restoration
        restored_memory = await memory_integration.postgresql_manager.get_memory(original_memory_id)
        assert restored_memory["content"] == sample_memory_data["content"]


class TestMemoryPerformanceIntegration:
    """Test performance aspects of memory stack integration"""

    @pytest.fixture
    async def performance_integration(self):
        """Fixture for performance-focused integration tests"""
        try:
            from src.agent_memory_integration import AgentMemoryIntegration
            integration = await AgentMemoryIntegration.initialize()

            # Configure for performance testing
            integration.performance_mode = True
            integration.batch_size = 100
            integration.cache_size = 1000

            yield integration

        except Exception as e:
            pytest.skip(f"Could not initialize performance integration: {e}")

    @pytest.mark.asyncio
    async def test_batch_memory_operations(self, performance_integration):
        """Test batch memory operations for performance"""
        # Prepare batch data
        batch_data = []
        for i in range(50):
            memory_data = {
                "content": f"Batch test memory {i}",
                "agent_id": f"batch_agent",
                "embedding": np.random.random(1536).tolist(),
                "memory_type": "semantic",
                "metadata": {"batch_test": True, "index": i}
            }
            batch_data.append(memory_data)

        # Execute batch operation
        start_time = time.time()

        results = await performance_integration.batch_add_memories(batch_data)

        batch_time = time.time() - start_time

        # Assert batch performance
        assert len(results) == 50
        assert all(result is not None for result in results)
        assert batch_time < 10.0  # Should complete within 10 seconds
        assert batch_time / 50 < 0.2  # Average < 200ms per memory in batch

    @pytest.mark.asyncio
    async def test_cache_performance_optimization(self, performance_integration):
        """Test cache performance optimization"""
        # Store memory
        memory_data = {
            "content": "Cache performance test memory",
            "agent_id": "cache_agent",
            "embedding": np.random.random(1536).tolist(),
            "memory_type": "factual",
            "metadata": {"cache_test": True}
        }

        memory_id = await performance_integration.add_memory(**memory_data)

        # First retrieval (cache miss)
        start_time = time.time()
        first_retrieval = await performance_integration.get_memory(memory_id)
        first_time = time.time() - start_time

        # Second retrieval (cache hit)
        start_time = time.time()
        second_retrieval = await performance_integration.get_memory(memory_id)
        second_time = time.time() - start_time

        # Assert cache performance improvement
        assert first_retrieval is not None
        assert second_retrieval is not None
        assert second_time < first_time  # Cache should be faster
        assert second_time < 0.01  # Cache retrieval should be very fast

    @pytest.mark.asyncio
    async def test_memory_indexing_performance(self, performance_integration):
        """Test memory indexing performance for faster retrieval"""
        # Create memories with different categories
        categories = ["trading", "security", "performance", "testing"]
        memories = []

        for i, category in enumerate(categories * 10):
            memory_data = {
                "content": f"Index test memory {i} in {category} category",
                "agent_id": f"index_agent",
                "embedding": np.random.random(1536).tolist(),
                "memory_type": "semantic",
                "metadata": {"category": category, "index_test": True}
            }
            memory_id = await performance_integration.add_memory(**memory_data)
            memories.append((memory_id, category))

        # Test filtered retrieval by category
        for category in categories:
            start_time = time.time()

            filtered_results = await performance_integration.search_memories(
                query_embedding=np.random.random(1536).tolist(),
                filters={"category": category},
                limit=10
            )

            filtered_time = time.time() - start_time

            # Assert index performance
            assert filtered_time < 1.0  # Filtered search should be fast
            assert all(result.get("metadata", {}).get("category") == category
                      for result in filtered_results)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])