"""
Enhanced Cognee Load Test Profile
=================================
Three workload classes against the FastAPI MCP HTTP variant
(src/enhanced_cognee_mcp.py served on http://localhost:8000):

  - ReadHeavy:  90% search_memories, 10% get_memories
  - WriteHeavy: 70% add_memory, 30% update_memory
  - Mixed:      50% search, 30% add, 10% delete, 10% list

Target SLA (single-tenant, dev VPS):
  - p95 latency under 200ms
  - >= 100 RPS sustained on a 2-core VPS
  - 0% error rate under 100 concurrent users

Run:
  locust -f tests/load/locustfile.py --headless \
         --users 100 --spawn-rate 10 --run-time 60s \
         --host http://localhost:8000
"""

import random
import uuid

from locust import HttpUser, between, task


# ---------------------------------------------------------------------------
# Shared payload helpers
# ---------------------------------------------------------------------------

SAMPLE_CONTENTS = [
    "User prefers async/await over callback patterns",
    "Trading strategy: momentum breakout with 2x ATR stop",
    "Bug: race condition in deduplication when N > 1000",
    "Customer reported login flow takes 4s on slow networks",
    "Decision: use PostgreSQL pgvector instead of standalone Qdrant for prototype",
    "Note: rate limiter token bucket should reset every 60s",
    "Architecture: 4-database stack -- postgres, qdrant, neo4j, redis",
    "Performance: dedup must complete within 5s for 10k memories",
]


def _random_content():
    return random.choice(SAMPLE_CONTENTS) + f" -- {uuid.uuid4().hex[:8]}"


def _random_search():
    return random.choice([
        "trading", "strategy", "bug", "architecture",
        "performance", "user", "customer", "memory",
    ])


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

class ReadHeavyUser(HttpUser):
    """90% read traffic. Represents AI agent context-loading workload."""

    wait_time = between(0.1, 0.5)
    weight = 3  # 3 of every 6 users are read-heavy

    @task(9)
    def search_memories(self):
        self.client.post(
            "/mcp/search_memories",
            json={"query": _random_search(), "limit": 10},
            name="search_memories",
        )

    @task(1)
    def get_memories(self):
        self.client.post(
            "/mcp/get_memories",
            json={"agent_id": "load-test", "limit": 20},
            name="get_memories",
        )


class WriteHeavyUser(HttpUser):
    """70% write traffic. Represents bulk-ingest workload."""

    wait_time = between(0.2, 1.0)
    weight = 2  # 2 of every 6 users are write-heavy

    @task(7)
    def add_memory(self):
        self.client.post(
            "/mcp/add_memory",
            json={
                "content": _random_content(),
                "user_id": "load-test",
                "agent_id": "loader",
            },
            name="add_memory",
        )

    @task(3)
    def update_memory(self):
        self.client.post(
            "/mcp/update_memory",
            json={
                "memory_id": str(uuid.uuid4()),
                "content": _random_content(),
            },
            name="update_memory",
        )


class MixedWorkloadUser(HttpUser):
    """Realistic mixed workload."""

    wait_time = between(0.1, 0.8)
    weight = 1  # 1 of every 6 users is mixed

    @task(5)
    def search(self):
        self.client.post(
            "/mcp/search_memories",
            json={"query": _random_search(), "limit": 5},
            name="mixed_search",
        )

    @task(3)
    def add(self):
        self.client.post(
            "/mcp/add_memory",
            json={
                "content": _random_content(),
                "user_id": "load-test",
                "agent_id": "mixed",
            },
            name="mixed_add",
        )

    @task(1)
    def delete(self):
        self.client.post(
            "/mcp/delete_memory",
            json={"memory_id": str(uuid.uuid4())},
            name="mixed_delete",
        )

    @task(1)
    def list_agents(self):
        self.client.get("/mcp/list_agents", name="mixed_list_agents")


# ---------------------------------------------------------------------------
# Healthcheck-only profile (use for smoke testing the load harness itself)
# ---------------------------------------------------------------------------

class HealthCheckUser(HttpUser):
    """Pings /health repeatedly; useful for sanity-checking the harness."""

    wait_time = between(0.5, 1.0)
    weight = 0  # opt-in only via --tags healthcheck

    @task
    def health(self):
        self.client.get("/health", name="health")
