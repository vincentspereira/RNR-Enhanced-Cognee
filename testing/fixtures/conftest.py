"""
Enhanced Testing Fixtures and Shared Utilities

Comprehensive test fixtures for all RNR Enhanced Cognee testing categories.
Provides database connections, mock services, test data, and utilities.
"""

import pytest
import asyncio
import json
import time
import tempfile
import shutil
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Generator, Union
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import requests
import redis
import subprocess
import threading
import contextlib
from dataclasses import dataclass

# Import test data generator
from .test_data_generator import TestDataGenerator, DataCategory, MemoryType, TestMemoryData

# Import RNR Enhanced Cognee components (will be mocked if not available)
try:
    from src.agent_memory_integration import AgentMemoryIntegration
except ImportError:
    AgentMemoryIntegration = None

# ats/oma/smc agent modules archived in Phase 4 (hardcoded category violation).
AlgorithmicTradingSystem = None
CodeReviewer = None
ContextManager = None

# Test environment configuration
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
            "uri": os.getenv("NEO4J_URI", "bolt://localhost:27687"),
            "user": os.getenv("NEO4J_USER", "neo4j"),
            "password": os.getenv("NEO4J_PASSWORD", "test_password")
        },
        "redis": {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "26379")),
            "db": int(os.getenv("REDIS_DB", "0")),
            "password": os.getenv("REDIS_PASSWORD", "test_password")
        }
    },
    "api": {
        "base_url": os.getenv("API_BASE_URL", "http://localhost:28080"),
        "timeout": int(os.getenv("API_TIMEOUT", "30")),
        "retry_attempts": int(os.getenv("RETRY_ATTEMPTS", "3"))
    },
    "performance": {
        "concurrent_users": int(os.getenv("TEST_CONCURRENT_AGENTS", "100")),
        "test_duration": int(os.getenv("TEST_DURATION_SECONDS", "60")),
        "ramp_up_time": int(os.getenv("RAMP_UP_TIME_SECONDS", "10"))
    }
}


@pytest.fixture(scope="session")
def test_data_generator():
    """Provide test data generator instance"""
    return TestDataGenerator(seed=int(time.time() * 1000))


@pytest.fixture(scope="session")
def temp_directory():
    """Provide temporary directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="enhanced_cognee_test_")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="session")
def test_reports_dir():
    """Create and provide test reports directory"""
    reports_dir = tempfile.mkdtemp(prefix="enhanced_cognee_reports_")

    # Create subdirectories
    subdirs = ["unit", "integration", "system", "performance", "security", "coverage"]
    for subdir in subdirs:
        os.makedirs(os.path.join(reports_dir, subdir), exist_ok=True)

    yield reports_dir
    shutil.rmtree(reports_dir)


@pytest.fixture(scope="session")
def environment_check():
    """Check if required test environment is available"""
    status = {
        "docker": False,
        "databases": {
            "postgresql": False,
            "qdrant": False,
            "neo4j": False,
            "redis": False
        },
        "api": False
    }

    # Check Docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
        status["docker"] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check database connectivity
    databases = TEST_CONFIG["database"]

    # PostgreSQL
    try:
        import asyncpg
        conn = asyncio.run(
            asyncpg.connect(
                host=databases["postgresql"]["host"],
                port=databases["postgresql"]["port"],
                database=databases["postgresql"]["database"],
                user=databases["postgresql"]["user"],
                password=databases["postgresql"]["password"]
            ),
            timeout=5
        )
        await conn.close()
        status["databases"]["postgresql"] = True
    except Exception:
        pass

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            host=databases["qdrant"]["host"],
            port=databases["qdrant"]["port"]
        )
        client.get_collections()
        status["databases"]["qdrant"] = True
    except Exception:
        pass

    # Redis
    try:
        r = redis.Redis(
            host=databases["redis"]["host"],
            port=databases["redis"]["port"],
            password=databases["redis"]["password"],
            db=databases["redis"]["db"]
        )
        r.ping()
        status["databases"]["redis"] = True
    except Exception:
        pass

    # Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            databases["neo4j"]["uri"],
            auth=(databases["neo4j"]["user"], databases["neo4j"]["password"])
        )
        driver.verify_connectivity()
        driver.close()
        status["databases"]["neo4j"] = True
    except Exception:
        pass

    # Check API
    try:
        response = requests.get(
            f"{TEST_CONFIG['api']['base_url']}/health",
            timeout=TEST_CONFIG["api"]["timeout"]
        )
        status["api"] = response.status_code == 200
    except Exception:
        pass

    # Log status
    print("Environment Status:")
    print(f"  Docker: {'✅' if status['docker'] else '❌'}")
    print(f"  PostgreSQL: {'✅' if status['databases']['postgresql'] else '❌'}")
    print(f"  Qdrant: {'✅' if status['databases']['qdrant'] else '❌'}")
    print(f"  Neo4j: {'✅' if status['databases']['neo4j'] else '❌'}")
    print(f"  Redis: {'✅' if status['databases']['redis'] else '❌'}")
    print(f"  API: {'✅' if status['api'] else '❌'}")

    return status


@pytest.fixture
async def mock_memory_integration():
    """Mock memory integration for testing"""
    with patch('src.agent_memory_integration.AgentMemoryIntegration') as mock_class:
        mock_integration = AsyncMock()
        mock_class.return_value = mock_integration

        # Mock database managers
        mock_integration.postgresql_manager = AsyncMock()
        mock_integration.qdrant_manager = AsyncMock()
        mock_integration.neo4j_manager = AsyncMock()
        mock_integration.redis_manager = AsyncMock()

        # Mock methods
        mock_integration.add_memory = AsyncMock(return_value=f"memory_{int(time.time())}")
        mock_integration.get_memory = AsyncMock(return_value={
            "id": f"memory_{int(time.time())}",
            "content": "Mock memory content",
            "metadata": {}
        })
        mock_integration.search_memories = AsyncMock(return_value=[])

        yield mock_integration


@pytest.fixture
def mock_api_server():
    """Mock API server for testing"""
    with patch('requests.Session') as mock_session:
        session = mock_session.return_value
        session.get = Mock()
        session.post = Mock()
        session.put = Mock()
        session.delete = Mock()

        # Configure response defaults
        for method in [session.get, session.post, session.put, session.delete]:
            method.return_value.status_code = 200
            method.return_value.json.return_value = {}
            method.return_value.headers = {"Content-Type": "application/json"}

        yield session


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing"""
    return {
        "content": "Sample memory content for RNR Enhanced Cognee testing",
        "agent_id": "test_agent",
        "memory_type": "episodic",
        "metadata": {
            "test": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "test"
        }
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "test_user",
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "role": "user"
    }


@pytest.fixture
def sample_trading_data():
    """Sample trading data for testing"""
    return {
        "symbol": "BTC/USD",
        "price": 45000.0,
        "volume": 1250000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indicators": {
            "rsi": 65.0,
            "macd": 0.5,
            "bollinger_upper": 46000.0,
            "bollinger_lower": 44000.0
        }
    }


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.metrics = {
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "response_times": [],
                "errors": []
            }

        def start_timing(self):
            self.start_time = time.time()

        def record_request(self, success: bool, response_time: float, error: str = None):
            self.metrics["requests"] += 1
            if success:
                self.metrics["successful"] += 1
            else:
                self.metrics["failed"] += 1
                if error:
                    self.metrics["errors"].append(error)

            self.metrics["response_times"].append(response_time)

        def get_summary(self):
            if not self.metrics["response_times"]:
                return {"avg_response_time": 0, "p95_response_time": 0}

            avg_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            sorted_times = sorted(self.metrics["response_times"])
            p95_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0

            return {
                "total_requests": self.metrics["requests"],
                "successful": self.metrics["successful"],
                "failed": self.metrics["failed"],
                "success_rate": self.metrics["successful"] / max(1, self.metrics["requests"]),
                "avg_response_time": avg_time,
                "p95_response_time": p95_time,
                "error_rate": self.metrics["failed"] / max(1, self.metrics["requests"])
            }

    return PerformanceMonitor()


@pytest.fixture
def database_connections():
    """Database connections for integration tests"""
    connections = {}

    try:
        # PostgreSQL connection
        import asyncpg
        pg_conn = asyncio.run(
            asyncpg.connect(
                host=TEST_CONFIG["database"]["postgresql"]["host"],
                port=TEST_CONFIG["database"]["postgresql"]["port"],
                database=TEST_CONFIG["database"]["postgresql"]["database"],
                user=TEST_CONFIG["database"]["postgresql"]["user"],
                password=TEST_CONFIG["database"]["postgresql"]["password"]
            ),
            timeout=10
        )
        connections["postgresql"] = pg_conn
    except Exception as e:
        pytest.skip(f"PostgreSQL connection failed: {e}")

    try:
        # Redis connection
        redis_conn = redis.Redis(
            host=TEST_CONFIG["database"]["redis"]["host"],
            port=TEST_CONFIG["database"]["redis"]["port"],
            password=TEST_CONFIG["database"]["redis"]["password"],
            db=TEST_CONFIG["database"]["redis"]["db"]
        )
        redis_conn.ping()
        connections["redis"] = redis_conn
    except Exception as e:
        pytest.skip(f"Redis connection failed: {e}")

    yield connections

    # Cleanup connections
    for conn_type, conn in connections.items():
        try:
            if conn_type == "postgresql":
                await conn.close()
            elif conn_type == "redis":
                conn.close()
        except:
            pass


@pytest.fixture
def test_authentication():
    """Authenticated session for testing"""
    import requests

    # Create test user
    user_data = {
        "username": f"auth_test_user_{int(time.time())}",
        "email": f"auth_test_{int(time.time())}@example.com",
        "password": "AuthTestPassword123!"
    }

    # Register user
    response = requests.post(
        f"{TEST_CONFIG['api']['base_url']}/api/v1/auth/register",
        json=user_data,
        timeout=TEST_CONFIG["api"]["timeout"]
    )

    # Login user
    login_response = requests.post(
        f"{TEST_CONFIG['api']['base_url']}/api/v1/auth/login",
        json={
            "username": user_data["username"],
            "password": user_data["password"]
        },
        timeout=TEST_CONFIG["api"]["timeout"]
    )

    if login_response.status_code == 200:
        token = login_response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        pytest.skip("Authentication failed")


class MemoryTestHelper:
    """Helper class for memory testing"""

    @staticmethod
    async def create_test_memory(
        memory_integration,
        content: str,
        agent_id: str = "test_agent",
        memory_type: MemoryType = MemoryType.EPISODIC,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create test memory"""
        memory_data = {
            "content": content,
            "agent_id": agent_id,
            "memory_type": memory_type.value,
            "metadata": metadata or {}
        }

        return await memory_integration.add_memory(**memory_data)

    @staticmethod
    async def create_test_memories_batch(
        memory_integration,
        count: int,
        category: DataCategory = DataCategory.MEMORY
    ) -> List[str]:
        """Create batch of test memories"""
        test_data_gen = TestDataGenerator()
        test_memories = test_data_gen.generate_memory_data(category, count)

        memory_ids = []
        for memory in test_memories:
            memory_id = await memory_integration.add_memory(
                content=memory.content,
                agent_id=memory.agent_id,
                memory_type=memory.memory_type,
                metadata=memory.metadata,
                embedding=memory.embedding
            )
            memory_ids.append(memory_id)

        return memory_ids

    @staticmethod
    def assert_memory_data(memory_data: Dict[str, Any], expected_fields: List[str]):
        """Assert memory data contains expected fields"""
        for field in expected_fields:
            assert field in memory_data, f"Missing required field: {field}"

    @staticmethod
    def assert_memory_content(memory_data: Dict[str, Any], content_patterns: List[str]):
        """Assert memory content contains expected patterns"""
        content = memory_data.get("content", "").lower()
        for pattern in content_patterns:
            assert pattern.lower() in content, f"Pattern '{pattern}' not found in memory content"


class APITestHelper:
    """Helper class for API testing"""

    @staticmethod
    def assert_api_response(
        response: requests.Response,
        expected_status: int = 200,
        expected_fields: List[str] = None
    ):
        """Assert API response meets expectations"""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}"

        if expected_fields:
            try:
                data = response.json()
                for field in expected_fields:
                    assert field in data, f"Missing field in response: {field}"
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON")

    @staticmethod
    def assert_security_headers(response: requests.Response):
        """Assert security headers are present"""
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]

        for header in security_headers:
            if header not in response.headers:
                pytest.warn(f"Security header not present: {header}")


class PerformanceTestHelper:
    """Helper class for performance testing"""

    @staticmethod
    def assert_performance_thresholds(
        metrics: Dict[str, Any],
        thresholds: Dict[str, Any]
    ):
        """Assert performance metrics meet thresholds"""
        for metric, threshold in thresholds.items():
            if metric in metrics:
                value = metrics[metric]
                if isinstance(threshold, (int, float)):
                    assert value <= threshold, \
                        f"Performance metric {metric} ({value}) exceeds threshold ({threshold})"
                elif isinstance(threshold, str) and ">" in threshold:
                    # Handle string thresholds like "<100ms"
                    threshold_value = float(threshold.replace(">", "").replace("ms", ""))
                    assert value <= threshold_value, \
                        f"Performance metric {metric} ({value}) exceeds threshold ({threshold})"


@pytest.fixture
def memory_test_helper():
    """Provide memory test helper"""
    return MemoryTestHelper()


@pytest.fixture
def api_test_helper():
    """Provide API test helper"""
    return APITestHelper()


@pytest.fixture
def performance_test_helper():
    """Provide performance test helper"""
    return PerformanceTestHelper()


# Async context manager for timing operations
@contextlib.asynccontextmanager
async def timed_operation(operation_name: str):
    """Context manager for timing operations"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        print(f"Operation '{operation_name}' completed in {duration:.2f}s")


# Context manager for capturing logs
@contextlib.contextmanager
def capture_logs():
    """Context manager for capturing logs"""
    import logging
    import io

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    yield log_capture

    root_logger.removeHandler(handler)


# Context manager for measuring resource usage
@contextlib.contextmanager
def measure_resource_usage():
    """Context manager for measuring resource usage"""
    import psutil

    # Get initial resource usage
    initial_cpu = psutil.cpu_percent()
    initial_memory = psutil.virtual_memory().percent
    initial_disk = psutil.disk_usage('/').percent

    yield {
        "initial_cpu": initial_cpu,
        "initial_memory": initial_memory,
        "initial_disk": initial_disk
    }


# Custom assertions
def assert_valid_memory_data(data: Dict[str, Any]):
    """Assert memory data is valid"""
    required_fields = ["content", "agent_id", "memory_type", "metadata"]
    MemoryTestHelper.assert_memory_data(data, required_fields)

    # Validate memory type
    try:
        MemoryType(data["memory_type"])
    except ValueError:
        pytest.fail(f"Invalid memory type: {data['memory_type']}")

    # Validate timestamp if present
    if "timestamp" in data:
        try:
            if isinstance(data["timestamp"], str):
                datetime.fromisoformat(data["timestamp"])
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {data['timestamp']}")


def assert_valid_agent_id(agent_id: str):
    """Assert agent ID is valid"""
    assert agent_id, "Agent ID cannot be empty"
    assert isinstance(agent_id, str), "Agent ID must be string"
    assert len(agent_id) > 0, "Agent ID cannot be empty"

    # Check if agent ID follows expected pattern
    valid_patterns = [
        "algorithmic-trading-system",
        "code-reviewer",
        "security-auditor",
        "context-manager"
    ]

    assert any(pattern in agent_id for pattern in valid_patterns), \
        f"Invalid agent ID pattern: {agent_id}"


if __name__ == "__main__":
    # Example usage of fixtures
    print("RNR Enhanced Cognee Test Fixtures")
    print("Available fixtures:")
    print("- test_data_generator")
    print("- temp_directory")
    print("- test_reports_dir")
    print("- environment_check")
    print("- mock_memory_integration")
    print("- mock_api_server")
    print("- sample_memory_data")
    print("- sample_user_data")
    print("- sample_trading_data")
    print("- performance_monitor")
    print("- database_connections")
    print("- test_authentication")
    print("- memory_test_helper")
    print("- api_test_helper")
    print("- performance_test_helper")