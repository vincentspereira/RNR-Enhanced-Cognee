"""
RNR Enhanced Cognee Performance Testing with Locust

Load testing scenarios for RNR Enhanced Cognee API endpoints.
Tests memory operations, agent coordination, and system performance under load.
"""

from locust import HttpUser, task, between, events
import json
import random
import time
from datetime import datetime, timezone
import numpy as np
from typing import Dict, List, Any

# Performance test configuration
PERFORMANCE_CONFIG = {
    "agents": [
        "algorithmic-trading-system",
        "code-reviewer",
        "security-auditor",
        "context-manager",
        "risk-management",
        "market-analysis"
    ],
    "memory_types": ["episodic", "semantic", "procedural", "factual"],
    "operations": ["store", "retrieve", "search", "update", "delete"],
    "load_patterns": {
        "light": {"users": 10, "spawn_rate": 1},
        "medium": {"users": 100, "spawn_rate": 5},
        "heavy": {"users": 1000, "spawn_rate": 20}
    }
}

# Sample test data generators
class TestDataGenerator:
    """Generate test data for performance testing"""

    @staticmethod
    def generate_memory_content(length: int = 100) -> str:
        """Generate random memory content"""
        words = ["enhanced", "cognee", "memory", "agent", "coordination",
                "trading", "analysis", "security", "performance", "testing"]
        return " ".join(random.choice(words) for _ in range(length))

    @staticmethod
    def generate_embedding(dim: int = 1536) -> List[float]:
        """Generate random embedding vector"""
        return [random.uniform(-1, 1) for _ in range(dim)]

    @staticmethod
    def generate_metadata() -> Dict[str, Any]:
        """Generate random metadata"""
        return {
            "agent_id": random.choice(PERFORMANCE_CONFIG["agents"]),
            "memory_type": random.choice(PERFORMANCE_CONFIG["memory_types"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "importance": random.uniform(0, 1),
            "category": random.choice(["trading", "security", "analysis", "coordination"]),
            "tags": [f"tag_{i}" for i in range(random.randint(1, 5))]
        }


class EnhancedCogneeUser(HttpUser):
    """RNR Enhanced Cognee API user for load testing"""

    wait_time = between(1, 3)
    weight = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_id = random.choice(PERFORMANCE_CONFIG["agents"])
        self.auth_token = None
        self.stored_memories = []
        self.test_data_generator = TestDataGenerator()

    def on_start(self):
        """Called when a user starts"""
        # Authenticate user
        self.authenticate()

        # Initialize user session
        self.initialize_session()

    def authenticate(self):
        """Authenticate with RNR Enhanced Cognee API"""
        auth_data = {
            "username": f"test_user_{self.agent_id}",
            "password": "test_password"
        }

        response = self.client.post("/api/v1/auth/login", json=auth_data)
        if response.status_code == 200:
            auth_result = response.json()
            self.auth_token = auth_result.get("token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })

    def initialize_session(self):
        """Initialize user session"""
        session_data = {
            "agent_id": self.agent_id,
            "session_type": "performance_test",
            "capabilities": ["memory_ops", "search", "coordination"]
        }

        response = self.client.post("/api/v1/session/init", json=session_data)
        if response.status_code != 200:
            self.logger.error(f"Failed to initialize session: {response.text}")

    @task(30)
    def store_memory(self):
        """Store a memory - high frequency operation"""
        memory_data = {
            "content": self.test_data_generator.generate_memory_content(150),
            "embedding": self.test_data_generator.generate_embedding(),
            "metadata": self.test_data_generator.generate_metadata()
        }

        start_time = time.time()

        with self.client.post("/api/v1/memory",
                              json=memory_data,
                              catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 201:
                memory_id = response.json().get("memory_id")
                if memory_id:
                    self.stored_memories.append(memory_id)

                # Log performance metrics
                events.request_success.fire(
                    request_type="POST",
                    name="/api/v1/memory/store",
                    response_time=duration * 1000,  # Convert to milliseconds
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="POST",
                    name="/api/v1/memory/store",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )

    @task(25)
    def search_memories(self):
        """Search for memories using vector similarity"""
        if not self.stored_memories:
            # Generate search query without requiring stored memories
            query_data = {
                "query": self.test_data_generator.generate_memory_content(50),
                "embedding": self.test_data_generator.generate_embedding(),
                "limit": random.randint(5, 20),
                "threshold": random.uniform(0.7, 0.9)
            }
        else:
            # Search for memories similar to stored ones
            query_data = {
                "embedding": self.test_data_generator.generate_embedding(),
                "agent_id": self.agent_id,
                "limit": random.randint(5, 20),
                "threshold": random.uniform(0.7, 0.9)
            }

        start_time = time.time()

        with self.client.post("/api/v1/memory/search",
                              json=query_data,
                              catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 200:
                events.request_success.fire(
                    request_type="POST",
                    name="/api/v1/memory/search",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="POST",
                    name="/api/v1/memory/search",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )

    @task(20)
    def retrieve_memory(self):
        """Retrieve a specific memory by ID"""
        if not self.stored_memories:
            # Skip if no memories stored yet
            return

        memory_id = random.choice(self.stored_memories)

        start_time = time.time()

        with self.client.get(f"/api/v1/memory/{memory_id}",
                            catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 200:
                events.request_success.fire(
                    request_type="GET",
                    name="/api/v1/memory/retrieve",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="GET",
                    name="/api/v1/memory/retrieve",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )

    @task(15)
    def get_agent_memories(self):
        """Get memories for a specific agent"""
        agent_id = random.choice(PERFORMANCE_CONFIG["agents"])
        params = {
            "agent_id": agent_id,
            "limit": random.randint(10, 50),
            "offset": random.randint(0, 100)
        }

        start_time = time.time()

        with self.client.get("/api/v1/memory",
                            params=params,
                            catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 200:
                events.request_success.fire(
                    request_type="GET",
                    name="/api/v1/memory/list",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="GET",
                    name="/api/v1/memory/list",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )

    @task(5)
    def agent_coordination(self):
        """Test agent coordination operations"""
        coordination_data = {
            "coordinator_id": self.agent_id,
            "task_type": random.choice(["memory_sync", "consensus", "resource_allocation"]),
            "participants": random.sample(PERFORMANCE_CONFIG["agents"],
                                       random.randint(2, 4)),
            "priority": random.choice(["low", "medium", "high"]),
            "deadline": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.time()

        with self.client.post("/api/v1/coordination/initiate",
                              json=coordination_data,
                              catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 200:
                events.request_success.fire(
                    request_type="POST",
                    name="/api/v1/coordination/initiate",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="POST",
                    name="/api/v1/coordination/initiate",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )

    @task(3)
    def system_health_check(self):
        """Lightweight system health check"""
        start_time = time.time()

        with self.client.get("/health", catch_response=True) as response:
            duration = time.time() - start_time

            if response.status_code == 200:
                events.request_success.fire(
                    request_type="GET",
                    name="/health",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="GET",
                    name="/health",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )

    @task(2)
    def update_memory(self):
        """Update an existing memory"""
        if not self.stored_memories:
            return

        memory_id = random.choice(self.stored_memories)
        update_data = {
            "content": self.test_data_generator.generate_memory_content(100),
            "metadata": self.test_data_generator.generate_metadata()
        }

        start_time = time.time()

        with self.client.put(f"/api/v1/memory/{memory_id}",
                            json=update_data,
                            catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 200:
                events.request_success.fire(
                    request_type="PUT",
                    name="/api/v1/memory/update",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="PUT",
                    name="/api/v1/memory/update",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )


class TradingSystemUser(EnhancedCogneeUser):
    """Specialized user for trading system operations"""

    weight = 3  # Higher priority for trading system

    wait_time = between(0.5, 2)  # Faster operations for trading

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_id = "algorithmic-trading-system"

    @task(40)
    def trading_memory_ops(self):
        """High-frequency trading memory operations"""
        trading_data = {
            "content": f"Market analysis: BTC/USD price {random.uniform(40000, 50000):.2f}",
            "embedding": self.test_data_generator.generate_embedding(),
            "metadata": {
                "agent_id": self.agent_id,
                "memory_type": "episodic",
                "symbol": random.choice(["BTC/USD", "ETH/USD", "AAPL", "GOOGL"]),
                "price": random.uniform(100, 50000),
                "volume": random.randint(1000000, 100000000),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "strategy": random.choice(["mean_reversion", "trend_following", "arbitrage"])
            }
        }

        start_time = time.time()

        with self.client.post("/api/v1/memory",
                              json=trading_data,
                              catch_response=True) as response:

            duration = time.time() - start_time

            if response.status_code == 201:
                memory_id = response.json().get("memory_id")
                if memory_id:
                    self.stored_memories.append(memory_id)

                events.request_success.fire(
                    request_type="POST",
                    name="/api/v1/memory/trading_ops",
                    response_time=duration * 1000,
                    response_length=len(response.content)
                )
            else:
                events.request_failure.fire(
                    request_type="POST",
                    name="/api/v1/memory/trading_ops",
                    response_time=duration * 1000,
                    response_length=len(response.content),
                    exception=f"HTTP {response.status_code}"
                )


# Event handlers for performance monitoring
def on_locust_init(environment, web_ui):
    """Called when Locust starts"""
    print("RNR Enhanced Cognee Performance Test Started")
    print(f"Target Host: {environment.host}")
    print(f"User Classes: {[user_class.__name__ for user_class in environment.user_classes]}")


def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Log successful requests"""
    print(f"✅ Success: {request_type} {name} - {response_time:.2f}ms")


def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Log failed requests"""
    print(f"❌ Failure: {request_type} {name} - {response_time:.2f}ms - {exception}")


# Register event handlers
events.request_success += on_request_success
events.request_failure += on_request_failure
events.init += on_locust_init


# Performance test scenarios
class PerformanceTestScenarios:
    """Predefined performance test scenarios"""

    @staticmethod
    def light_load_scenario():
        """Light load scenario for basic functionality testing"""
        return {
            "users": 10,
            "spawn_rate": 1,
            "run_time": "5m",
            "host": "http://localhost:28080"
        }

    @staticmethod
    def medium_load_scenario():
        """Medium load scenario for typical usage testing"""
        return {
            "users": 100,
            "spawn_rate": 5,
            "run_time": "10m",
            "host": "http://localhost:28080"
        }

    @staticmethod
    def heavy_load_scenario():
        """Heavy load scenario for stress testing"""
        return {
            "users": 1000,
            "spawn_rate": 20,
            "run_time": "15m",
            "host": "http://localhost:28080"
        }

    @staticmethod
    def endurance_scenario():
        """Endurance scenario for long-running stability testing"""
        return {
            "users": 50,
            "spawn_rate": 2,
            "run_time": "2h",
            "host": "http://localhost:28080"
        }


if __name__ == "__main__":
    # Run Locust with default scenario
    import os
    from locust import main

    # Default to medium load scenario
    scenario = PerformanceTestScenarios.medium_load_scenario()

    # Override with environment variables if provided
    users = int(os.getenv("LOCUST_USERS", scenario["users"]))
    spawn_rate = int(os.getenv("LOCUST_SPAWN_RATE", scenario["spawn_rate"]))
    run_time = os.getenv("LOCUST_RUN_TIME", scenario["run_time"])
    host = os.getenv("LOCUST_HOST", scenario["host"])

    # Command line arguments
    sys.argv = [
        "locust",
        f"--users={users}",
        f"--spawn-rate={spawn_rate}",
        f"--run-time={run_time}",
        f"--host={host}",
        "--headless",
        "--html=reports/locust_performance_report.html",
        "--csv=reports/locust_performance_stats"
    ]

    main()