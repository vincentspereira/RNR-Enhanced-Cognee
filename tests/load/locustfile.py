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


# ---------------------------------------------------------------------------
# Phase 5 (H4) extended scenarios -- knowledge-graph / semantic / GDPR /
# backup. Added 2026-05-20. These cover the workloads NOT exercised by
# the memory-CRUD-focused profiles above. Run them with explicit
# class selection:
#   locust -f tests/load/locustfile.py SemanticSearchUser \
#          --headless --users 10 --spawn-rate 1 --run-time 1m \
#          --host http://localhost:8000
# ---------------------------------------------------------------------------


SEMANTIC_QUERIES = [
    "Which graph database is the default?",
    "What MCP tools does Enhanced Cognee expose?",
    "Why did Redis get replaced?",
    "How does ArcadeDB compare to Neo4j?",
    "What is the lean deployment profile?",
    "Which providers are pluggable for graph?",
]


class SemanticSearchUser(HttpUser):
    """`search` over the knowledge graph after `cognify`-ed corpus.

    Read-only scenario assuming the corpus has been pre-populated via
    examples/02_semantic_search.py. Heavier per-call than memory-CRUD
    search because it routes through the LLM-backed retrieval pipeline.
    """

    wait_time = between(1.0, 3.0)
    weight = 0  # opt-in

    @task
    def semantic_search(self):
        self.client.post(
            "/mcp/search",
            json={"query": random.choice(SEMANTIC_QUERIES), "limit": 5},
            name="semantic_search",
        )


class KnowledgeGraphUser(HttpUser):
    """`remember` + `recall` -- direct KG ops, no LLM-backed cognify."""

    wait_time = between(0.5, 1.5)
    weight = 0  # opt-in

    @task(2)
    def remember(self):
        self.client.post(
            "/mcp/remember",
            json={
                "fact": _random_content(),
                "agent_id": "loadtest-kg",
            },
            name="remember",
        )

    @task(4)
    def recall(self):
        self.client.post(
            "/mcp/recall",
            json={
                "query": _random_search(),
                "agent_id": "loadtest-kg",
            },
            name="recall",
        )


class GDPRWorkflowUser(HttpUser):
    """Consent + export + delete -- statutory-window latency-sensitive flows.

    GDPR ops are rare in real traffic but regulators expect responses
    inside statutory windows. This scenario stresses the worst case.
    """

    wait_time = between(2.0, 5.0)
    weight = 0  # opt-in

    def on_start(self):
        self.user_id = f"loadtest-gdpr-{uuid.uuid4().hex[:8]}"
        # Establish consent + data footprint so export/erasure are non-trivial
        self.client.post(
            "/mcp/gdpr_record_consent",
            json={
                "user_id": self.user_id,
                "purpose": "memory-storage",
                "granted": True,
            },
            name="gdpr_consent_seed",
        )
        for _ in range(3):
            self.client.post(
                "/mcp/add_memory",
                json={
                    "content": _random_content(),
                    "user_id": self.user_id,
                    "agent_id": "loadtest-gdpr-agent",
                },
                name="gdpr_data_seed",
            )

    @task(3)
    def export_user_data(self):
        self.client.post(
            "/mcp/gdpr_export_user_data",
            json={"user_id": self.user_id},
            name="gdpr_export",
        )

    @task(2)
    def list_consents(self):
        self.client.post(
            "/mcp/gdpr_list_consents",
            json={"user_id": self.user_id},
            name="gdpr_list_consents",
        )

    @task(1)
    def delete_then_reseed(self):
        self.client.post(
            "/mcp/gdpr_delete_user_data",
            json={"user_id": self.user_id},
            name="gdpr_delete",
        )
        # Re-seed so the user keeps generating measurable load
        self.client.post(
            "/mcp/gdpr_record_consent",
            json={
                "user_id": self.user_id,
                "purpose": "memory-storage",
                "granted": True,
            },
            name="gdpr_consent_reseed",
        )


class BackupVerifyUser(HttpUser):
    """`create_backup` + `verify_backup` -- the heaviest single MCP op.

    One concurrent backup is genuinely stress-class because it
    serialises every DB. Run with low user counts (1-3) to characterise
    backup duration; bump up if you want to measure contention.
    """

    wait_time = between(60.0, 120.0)
    weight = 0  # opt-in

    @task(1)
    def backup_then_verify(self):
        with self.client.post(
            "/mcp/create_backup",
            json={"description": "loadtest"},
            name="create_backup",
            catch_response=True,
            timeout=120,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            try:
                body = resp.json()
            except Exception as exc:
                resp.failure(f"non-JSON: {exc}")
                return
        bid = body.get("backup_id") if isinstance(body, dict) else None
        if isinstance(bid, str):
            self.client.post(
                "/mcp/verify_backup",
                json={"backup_id": bid},
                name="verify_backup",
            )

    @task(3)
    def list_backups(self):
        self.client.post("/mcp/list_backups", json={}, name="list_backups")
