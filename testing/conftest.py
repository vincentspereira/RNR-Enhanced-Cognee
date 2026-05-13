"""
Enhanced Cognee Testing Configuration
Shared fixtures and configuration for all test categories
"""

import asyncio
import os
import sys
import pytest
import logging
import time
import json
from typing import Dict, List, Any, Optional, Generator
from unittest.mock import Mock, MagicMock
import tempfile
import shutil
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "cognee"))

# Enhanced Cognee imports
try:
    from src.agent_memory_integration import AgentMemoryIntegration
except ImportError as e:
    logging.warning(f"Could not import AgentMemoryIntegration: {e}")
    AgentMemoryIntegration = None

# ats/oma/smc agent modules were archived in Phase 4 (hardcoded category violation).
# Tests that depended on these are guarded with pytest.importorskip or mock-only.
AlgorithmicTradingSystem = None
CodeReviewer = None
ContextManager = None

# Test configuration
TEST_CONFIG = {
    "database": {
        "postgresql": {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "25432")),
            "database": os.getenv("POSTGRES_DB", "test_cognee"),
            "user": os.getenv("POSTGRES_USER", "test_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "test_password")
        },
        "qdrant": {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", "26333")),
            "collection_name": "test_collection"
        },
        "neo4j": {
            "uri": os.getenv("NEO4J_URI", "bolt://localhost:27474"),
            "user": os.getenv("NEO4J_USER", "neo4j"),
            "password": os.getenv("NEO4J_PASSWORD", "test_password")
        },
        "redis": {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "26379")),
            "db": int(os.getenv("REDIS_DB", "0"))
        }
    },
    "performance": {
        "concurrent_agents": int(os.getenv("TEST_CONCURRENT_AGENTS", "100")),
        "memory_operations_per_second": int(os.getenv("TEST_MEMORY_OPS", "1000")),
        "api_response_timeout": int(os.getenv("API_TIMEOUT", "30"))
    },
    "testing": {
        "timeout": int(os.getenv("TEST_TIMEOUT", "300")),
        "retry_attempts": int(os.getenv("TEST_RETRY_ATTEMPTS", "3")),
        "cleanup_after_test": os.getenv("CLEANUP_AFTER_TEST", "true").lower() == "true"
    }
}

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_REPORTS_DIR = Path(__file__).parent / "reports"

# Ensure directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_REPORTS_DIR.mkdir(exist_ok=True)


def pytest_configure(config):
    """Pytest configuration hook"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(TEST_REPORTS_DIR / "test_execution.log")
        ]
    )

    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location"""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "system" in str(item.fspath):
            item.add_marker(pytest.mark.system)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration to all tests"""
    return TEST_CONFIG


@pytest.fixture(scope="function")
async def memory_integration(test_config):
    """Fixture for AgentMemoryIntegration with test configuration"""
    try:
        integration = await AgentMemoryIntegration.initialize()
        # Use test database configuration
        integration.config.update(test_config["database"])
        yield integration
    except Exception as e:
        pytest.skip(f"Could not initialize memory integration: {e}")


@pytest.fixture
async def algorithmic_trading_agent():
    """Fixture for Algorithmic Trading System agent"""
    try:
        agent = AlgorithmicTradingSystem()
        await agent.initialize()
        yield agent
        await agent.cleanup()
    except Exception as e:
        pytest.skip(f"Could not initialize trading agent: {e}")


@pytest.fixture
async def code_reviewer_agent():
    """Fixture for Code Reviewer agent"""
    try:
        agent = CodeReviewer()
        await agent.initialize()
        yield agent
        await agent.cleanup()
    except Exception as e:
        pytest.skip(f"Could not initialize code reviewer agent: {e}")


@pytest.fixture
async def context_manager_agent():
    """Fixture for Context Manager agent"""
    try:
        agent = ContextManager()
        await agent.initialize()
        yield agent
        await agent.cleanup()
    except Exception as e:
        pytest.skip(f"Could not initialize context manager agent: {e}")


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "symbol": "BTC/USD",
        "timestamp": int(time.time()),
        "price": 45000.0,
        "volume": 125000000,
        "high": 46000.0,
        "low": 44000.0,
        "change": 0.025
    }


@pytest.fixture
def sample_code_snippet():
    """Sample code snippet for testing"""
    return """
def authenticate_user(username: str, password: str) -> bool:
    '''Authenticate user with username and password'''
    if not username or not password:
        return False

    # Hash password for security
    hashed_password = hash_password(password)

    # Check against database
    user = get_user_by_username(username)
    if user and user.password_hash == hashed_password:
        return True

    return False
"""


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing"""
    return {
        "content": "Test memory content for Enhanced Cognee",
        "agent_id": "test_agent",
        "memory_type": "episodic",
        "metadata": {
            "test": True,
            "timestamp": int(time.time()),
            "category": "test"
        }
    }


@pytest.fixture
async def database_connections(test_config):
    """Fixture for database connections"""
    connections = {}

    try:
        # PostgreSQL connection
        import asyncpg
        pg_config = test_config["database"]["postgresql"]
        connections["postgresql"] = await asyncpg.connect(
            host=pg_config["host"],
            port=pg_config["port"],
            database=pg_config["database"],
            user=pg_config["user"],
            password=pg_config["password"]
        )
    except Exception as e:
        logging.warning(f"Could not connect to PostgreSQL: {e}")

    try:
        # Qdrant connection
        from qdrant_client import QdrantClient
        qdrant_config = test_config["database"]["qdrant"]
        connections["qdrant"] = QdrantClient(
            host=qdrant_config["host"],
            port=qdrant_config["port"]
        )
    except Exception as e:
        logging.warning(f"Could not connect to Qdrant: {e}")

    try:
        # Neo4j connection
        from neo4j import GraphDatabase
        neo4j_config = test_config["database"]["neo4j"]
        connections["neo4j"] = GraphDatabase.driver(
            neo4j_config["uri"],
            auth=(neo4j_config["user"], neo4j_config["password"])
        )
    except Exception as e:
        logging.warning(f"Could not connect to Neo4j: {e}")

    try:
        # Redis connection
        import redis
        redis_config = test_config["database"]["redis"]
        connections["redis"] = redis.Redis(
            host=redis_config["host"],
            port=redis_config["port"],
            db=redis_config["db"]
        )
    except Exception as e:
        logging.warning(f"Could not connect to Redis: {e}")

    yield connections

    # Cleanup
    for name, conn in connections.items():
        try:
            if name == "postgresql":
                await conn.close()
            elif name == "neo4j":
                conn.close()
            elif name == "redis":
                conn.close()
            elif name == "qdrant":
                # Qdrant client doesn't need explicit closing
                pass
        except Exception as e:
            logging.warning(f"Error closing {name} connection: {e}")


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_api_responses():
    """Mock API responses for testing"""
    with pytest.MonkeyPatch().context() as m:
        # Mock common API responses
        m.setattr("requests.get", Mock(return_value=Mock(status_code=200, json=lambda: {"status": "ok"})))
        m.setattr("requests.post", Mock(return_value=Mock(status_code=201, json=lambda: {"id": "test_id"})))
        yield


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.memory_usage = []
            self.cpu_usage = []

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

        def record_memory(self, usage_mb):
            self.memory_usage.append(usage_mb)

        def record_cpu(self, usage_percent):
            self.cpu_usage.append(usage_percent)

        @property
        def avg_memory(self):
            return sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0

        @property
        def avg_cpu(self):
            return sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0

    return PerformanceMonitor()


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup fixture to run after each test"""
    yield
    # Add any cleanup logic here
    if TEST_CONFIG["testing"]["cleanup_after_test"]:
        # Cleanup temporary files, reset test state, etc.
        pass


@pytest.fixture
def test_scenario_data():
    """Load test scenario data from JSON files"""
    scenario_data = {}

    # Load sample scenarios
    scenario_files = [
        "business_scenarios.json",
        "technical_scenarios.json",
        "performance_scenarios.json"
    ]

    for filename in scenario_files:
        file_path = TEST_DATA_DIR / filename
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    scenario_data[filename.replace('.json', '')] = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load scenario file {filename}: {e}")

    return scenario_data


# Skip conditions for different environments
def pytest_runtest_setup(item):
    """Setup function to determine if tests should be skipped"""
    # Skip integration tests if databases are not available
    if "integration" in item.keywords and not os.getenv("INTEGRATION_TESTS_ENABLED"):
        pytest.skip("Integration tests disabled")

    # Skip performance tests if not in performance testing environment
    if "performance" in item.keywords and not os.getenv("PERFORMANCE_TESTS_ENABLED"):
        pytest.skip("Performance tests disabled")

    # Skip chaos tests if not in chaos testing environment
    if "chaos" in item.keywords and not os.getenv("CHAOS_TESTS_ENABLED"):
        pytest.skip("Chaos tests disabled")


# Custom assertions
def assert_memory_data_valid(memory_data):
    """Custom assertion for memory data validation"""
    assert "content" in memory_data, "Memory data must have content"
    assert "agent_id" in memory_data, "Memory data must have agent_id"
    assert "memory_type" in memory_data, "Memory data must have memory_type"
    assert len(memory_data["content"]) > 0, "Memory content cannot be empty"


def assert_api_response_valid(response):
    """Custom assertion for API response validation"""
    assert response is not None, "API response cannot be None"
    assert hasattr(response, 'status_code'), "Response must have status_code"
    assert 200 <= response.status_code < 300, f"Response status code {response.status_code} indicates error"


def assert_performance_within_threshold(duration_ms, threshold_ms=100):
    """Custom assertion for performance threshold validation"""
    assert duration_ms <= threshold_ms, f"Duration {duration_ms}ms exceeds threshold {threshold_ms}ms"