"""
Test Configuration and Fixtures for Enhanced Cognee
Provides fixtures and utilities for comprehensive testing
"""

import os
import sys
import pytest
import asyncio
import logging
from typing import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
import json

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "bin"))
sys.path.insert(0, str(project_root / "src"))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test environment variables
os.environ.update({
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "25432",
    "POSTGRES_DB": "cognee_test_db",
    "POSTGRES_USER": "cognee_test_user",
    "POSTGRES_PASSWORD": "cognee_test_password",
    "QDRANT_HOST": "localhost",
    "QDRANT_PORT": "26333",
    "NEO4J_URI": "bolt://localhost:27687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "cognee_test_password",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "26379",
    "ENHANCED_COGNEE_MODE": "true"
})


# ============================================================================
# Async Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Database Fixtures
# ============================================================================

@pytest.fixture
async def mock_postgres_pool() -> AsyncGenerator:
    """Mock PostgreSQL connection pool"""

    # Create a connection mock
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=0)
    mock_conn.execute = AsyncMock(return_value=None)

    # Create an async context manager for the connection
    class MockConnectionContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    # Create pool object without using Mock() to avoid AsyncMock wrapping
    class MockPool:
        def __init__(self):
            self._conn_ctx = MockConnectionContext()

        def acquire(self):
            """Return connection context - must NOT be async"""
            return self._conn_ctx

    mock_pool = MockPool()
    yield mock_pool


@pytest.fixture
def mock_qdrant_client() -> Mock:
    """Mock Qdrant client"""
    mock_client = Mock()
    mock_client.get_collections = Mock(return_value=Mock(collections=[]))
    mock_client.search = Mock(return_value=[])
    mock_client.upsert = Mock()
    mock_client.create_collection = Mock()
    mock_client.delete = Mock()

    return mock_client


@pytest.fixture
def mock_neo4j_driver() -> Mock:
    """Mock Neo4j driver"""
    mock_driver = Mock()
    mock_session = Mock()
    mock_session.run = Mock(return_value=[])
    mock_session.close = Mock()
    mock_driver.session = Mock(return_value=mock_session)
    mock_driver.close = Mock()

    return mock_driver


@pytest.fixture
async def mock_redis_client() -> AsyncGenerator:
    """Mock Redis client"""
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.publish = AsyncMock(return_value=1)
    mock_client.subscribe = AsyncMock()
    mock_client.unsubscribe = AsyncMock()
    mock_client.incrbyfloat = AsyncMock(return_value=1.0)
    mock_client.info = AsyncMock(return_value={"connected_clients": 5})
    mock_client.aclose = AsyncMock()

    # Mock pubsub
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = AsyncMock(return_value=[])
    mock_client.pubsub = Mock(return_value=mock_pubsub)

    yield mock_client


@pytest.fixture
def mock_llm_config() -> dict:
    """Mock LLM configuration"""
    return {
        "provider": "openai",
        "model": "gpt-4",
        "api_key": "test-key",
        "temperature": 0.7
    }


# ============================================================================
# Real Database Fixtures (for integration tests)
# ============================================================================

@pytest.fixture
async def real_postgres_pool():
    """
    Real PostgreSQL connection pool for integration tests
    Requires PostgreSQL to be running
    """
    try:
        import asyncpg

        pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "25432")),
            database=os.getenv("POSTGRES_DB", "cognee_test_db"),
            user=os.getenv("POSTGRES_USER", "cognee_test_user"),
            password=os.getenv("POSTGRES_PASSWORD", "cognee_test_password"),
            min_size=1,
            max_size=5
        )

        yield pool

        await pool.close()

    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture(scope="session")
def real_qdrant_client():
    """
    Real Qdrant client for integration tests
    Requires Qdrant to be running
    """
    try:
        from qdrant_client import QdrantClient
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            client = QdrantClient(
                url=f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '26333')}",
                api_key=os.getenv("QDRANT_API_KEY"),
                check_compatibility=False
            )

        yield client

    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")


@pytest.fixture
async def real_redis_client():
    """
    Real Redis client for integration tests
    Requires Redis to be running
    """
    try:
        import redis.asyncio as aioredis

        client = await aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "26379")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            db=15  # Use separate DB for tests
        )

        yield client

        await client.aclose()

    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


# ============================================================================
# Module Instance Fixtures
# ============================================================================

@pytest.fixture
async def memory_manager(mock_postgres_pool, mock_redis_client, mock_qdrant_client):
    """Memory Manager instance with mocked dependencies"""
    from src.memory_management import MemoryManager

    return MemoryManager(mock_postgres_pool, mock_redis_client, mock_qdrant_client)


@pytest.fixture
async def memory_deduplicator(mock_postgres_pool, mock_qdrant_client):
    """Memory Deduplicator instance with mocked dependencies"""
    from src.memory_deduplication import MemoryDeduplicator

    return MemoryDeduplicator(mock_postgres_pool, mock_qdrant_client)


@pytest.fixture
async def memory_summarizer(mock_postgres_pool, mock_llm_config):
    """Memory Summarizer instance with mocked dependencies"""
    from src.memory_summarization import MemorySummarizer

    return MemorySummarizer(mock_postgres_pool, mock_llm_config)


@pytest.fixture
async def performance_analytics(mock_postgres_pool, mock_redis_client):
    """Performance Analytics instance with mocked dependencies"""
    from src.performance_analytics import PerformanceAnalytics

    return PerformanceAnalytics(mock_postgres_pool, mock_redis_client)


@pytest.fixture
async def cross_agent_sharing(mock_postgres_pool):
    """Cross-Agent Sharing instance with mocked dependencies"""
    from src.cross_agent_sharing import CrossAgentMemorySharing

    return CrossAgentMemorySharing(mock_postgres_pool)


@pytest.fixture
async def realtime_sync(mock_redis_client, mock_postgres_pool):
    """Real-Time Sync instance with mocked dependencies"""
    from src.realtime_sync import RealTimeMemorySync

    return RealTimeMemorySync(mock_redis_client, mock_postgres_pool)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_memory():
    """Sample memory data"""
    return {
        "id": "test-memory-123",
        "title": "Test Memory",
        "content": "This is a test memory content with sufficient length for testing.",
        "agent_id": "test-agent",
        "memory_category": "test",
        "metadata": {"test": "data"}
    }


@pytest.fixture
def sample_memories():
    """List of sample memories"""
    return [
        {
            "id": f"memory-{i}",
            "title": f"Memory {i}",
            "content": f"Content for memory {i}" * 10,
            "agent_id": f"agent-{i % 5}",
            "memory_category": "test"
        }
        for i in range(1, 11)
    ]


@pytest.fixture
def sample_embedding():
    """Sample vector embedding"""
    import random
    return [random.random() for _ in range(1536)]


@pytest.fixture
def create_async_context_manager():
    """Fixture that returns a function to create async context managers.

    This helper fixture provides a function that creates an async context
    manager for a mock connection. Use this in tests that need to mock
    postgres_pool.acquire().

    Example:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        ctx_mgr = create_async_context_manager(mock_conn)
        cross_agent_sharing.postgres_pool.acquire = Mock(return_value=ctx_mgr)
    """
    def _create_context_manager(mock_conn):
        class MockConnectionContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass
        return MockConnectionContext()

    return _create_context_manager


# ============================================================================
# Test Utilities
# ============================================================================

@pytest.fixture
def assert_no_warnings(caplog):
    """Assert no warnings were logged during test"""
    yield
    for record in caplog.records:
        assert record.levelno != logging.WARNING, f"Warning found: {record.message}"


@pytest.fixture
def temp_db_cleanup(monkeypatch):
    """Cleanup temporary test database after tests"""
    yield

    # Cleanup code here if needed


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "system: System tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers"""
    # Mark slow tests
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)
        if "e2e" in item.keywords:
            item.add_marker(pytest.mark.slow)


def pytest_report_header(config):
    """Add custom header to pytest output"""
    return [
        "Enhanced Cognee Test Suite",
        f"Coverage Target: 98%",
        f"Test Requirements: 100% success, 0 warnings, 0 skipped"
    ]
