"""Real PostgreSQL delivery/authorization tests; sink doubles inject failures.

The separate default-stack test exercises the actual Qdrant/ArcadeDB/Valkey
transports. These tests establish lease/crash/version behavior independently.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit
import uuid

import asyncpg
from cryptography.fernet import Fernet
import pytest
import pytest_asyncio

from src.encryption_manager import EncryptionManager
from src.index_contracts import IndexIdentity, validated_links
from src.index_outbox import IndexWorker
from src.memory_admin import grant_worker, grant_runtime
from src.memory_service import MemoryService, MemoryScope, MemoryClarificationRequired
from src.recall_service import DerivedRecall
from src.security.enterprise_auth import AuthError


class TinyEmbedder:
    model = "qualification_fixture_v1"

    async def embed(self, text):
        return [1., 0., 0.]


class FixtureSinks:
    model = TinyEmbedder.model
    dimensions = 3

    def __init__(self):
        self.identity = IndexIdentity("synthetic-identity-key-at-least-32-bytes", "fixture")
        self.records = {}
        self.edges = []
        self.fail = False
        self.cancel = False
        self.entered = asyncio.Event()
        self.release = None

    def entity(self, tenant, value):
        return self.identity.entity(tenant, value)

    async def project(self, row, payload, vector, *, active):
        self.records[row["id"]] = (row["version"], active)
        if self.cancel:
            raise asyncio.CancelledError
        self.entered.set()
        if self.release:
            await self.release.wait()
        if self.fail:
            raise RuntimeError("Synthetic partial delivery")
        self.edges = [e for e in self.edges if e["record_id"] != row["id"]]
        if active:
            self.edges.extend(dict(project=row["project"], record_id=row["id"], version=row["version"],
                link_index=i, source_key=self.entity(row["tenant"], link["subject"]),
                target_key=self.entity(row["tenant"], link["object"]))
                for i, link in enumerate(payload.get("knowledge_links", [])))

    async def neighbors(self, tenant, entity, *, identifiers, limit):
        return [e for e in self.edges if e["source_key"] == self.entity(tenant, entity)][:limit]

    async def search(self, tenant, vector, identifiers, limit):
        # Malicious/stale index response must never manufacture a result.
        return [{"id": "unowned", "score": .99, "payload": {"tenant": tenant}}] + [
                {"id": ident, "score": .99, "payload": {"tenant": tenant, "project": "other",
                 "record_id": ident, "version": 999, "model": self.model}} for ident in identifiers]


@pytest.mark.asyncio
async def test_graph_citations_obey_response_budget(pipeline):
    p = pipeline
    for subject, targets in (("Root", ["MiddleA", "MiddleB"]),
                             ("MiddleA", [f"Target{i}" for i in range(16)]),
                             ("MiddleB", [f"Other{i}" for i in range(16)])):
        content = " ".join([subject, *targets]) + " " + "x"*2400
        await p.service.remember(p.scope, content, idempotency_key="budget-"+subject,
            evidence={"source_id": "synthetic-budget", "source_uri": "https://example.invalid/"+"a"*1800},
            knowledge_links=[{"subject": subject, "predicate": "links to", "object": target,
                              "span_start": 0, "span_end": len(content)} for target in targets])
    while await p.worker.run_once():
        pass
    result = await p.service.connections(p.scope, "Root", depth=2, limit=20)
    assert result["paths"] and result["budget_limit_reached"]
    assert len(json.dumps(result, ensure_ascii=True).encode()) < 129*1024
    assert all(edge["source_excerpt_truncated"] for chain in result["paths"] for edge in chain)


@pytest_asyncio.fixture
async def pipeline():
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Select an explicitly disposable PostgreSQL server")
    name = "index_q_" + uuid.uuid4().hex[:20]
    operator = await asyncpg.connect(url)
    await operator.execute(f"CREATE DATABASE {name}")
    await operator.close()
    parsed = urlsplit(url)
    selected = urlunsplit((parsed.scheme, parsed.netloc, "/" + name, parsed.query, ""))
    pool = await asyncpg.create_pool(selected, min_size=1, max_size=5)
    sinks = FixtureSinks()
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()),
                            TinyEmbedder(), derived=DerivedRecall(sinks))
    await service.initialize()
    scope = MemoryScope("qualification", "source", "owner", "agent")
    try:
        yield SimpleNamespace(pool=pool, sinks=sinks, service=service, scope=scope,
                              worker=IndexWorker(service, sinks), url=selected)
    finally:
        await pool.close()


def link(content, subject, predicate, target):
    return {"subject": subject, "predicate": predicate, "object": target, "span_start": 0, "span_end": len(content)}


async def seed(p, content="Cedar depends on Birch.", subject="Cedar", target="Birch", key="one"):
    return await p.service.remember(p.scope, content, idempotency_key=key,
        knowledge_links=[link(content, subject, "depends on", target)])


@pytest.mark.asyncio
@pytest.mark.parametrize("materialization", ["on", "off"])
async def test_one_claim_leases_exactly_one_event_for_each_query_plan(pipeline, materialization):
    p = pipeline
    for number in range(36):
        await seed(p, key="burst-" + str(number))
    async with p.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL enable_material=" + materialization)

            class TransactionPool:
                @asynccontextmanager
                async def acquire(self):
                    yield conn

            worker = IndexWorker(p.service, p.sinks)
            worker.pool = TransactionPool()
            first = await worker._claim()
            assert first is not None
            assert await conn.fetchval("""SELECT count(*) FROM shared_memory.index_deliveries
                WHERE pipeline=$1 AND lease_id=$2""", worker.pipeline, first["lease_id"]) == 1
            second = await worker._claim()
            assert second["event_id"] != first["event_id"]
            assert await conn.fetchval("""SELECT count(*) FROM shared_memory.index_deliveries
                WHERE pipeline=$1 AND lease_id IS NOT NULL""", worker.pipeline) == 2


@pytest.mark.asyncio
async def test_concurrent_claims_do_not_hide_unreturned_events(pipeline):
    p = pipeline
    for number in range(36):
        await seed(p, key="concurrent-burst-" + str(number))
    jobs = await asyncio.gather(*(IndexWorker(p.service, p.sinks)._claim() for _ in range(5)))
    assert all(job is not None for job in jobs)
    assert len({job["event_id"] for job in jobs}) == len({job["lease_id"] for job in jobs}) == 5
    async with p.pool.acquire() as conn:
        leased = await conn.fetchval("""SELECT count(*) FROM shared_memory.index_deliveries
            WHERE pipeline=$1 AND lease_id IS NOT NULL""", p.worker.pipeline)
    assert leased == 5


def test_graph_declarations_correspond_to_source_and_keys_hide_labels():
    text = "Cedar depends on Birch."
    assert validated_links(text, [link(text, "Cedar", "depends", "Birch")])
    with pytest.raises(ValueError):
        validated_links(text, [link(text, "Cedar", "depends", "PrivateProject")])
    with pytest.raises(ValueError):
        validated_links(text, [link(text, "Cedar", "depends", "Birch")] * 17)
    identity = IndexIdentity("synthetic-identity-key-at-least-32-bytes", "fixture")
    assert identity.entity("one", "Cedar") != identity.entity("two", "Cedar")
    assert identity.entity("one", "CEDAR") == identity.entity("one", "Cedar")


@pytest.mark.asyncio
async def test_retry_partial_delivery_and_worker_restart(pipeline):
    p = pipeline
    record = await seed(p)
    p.sinks.fail = True
    assert await p.worker.run_once()
    async with p.pool.acquire() as conn:
        job = await conn.fetchrow("SELECT * FROM shared_memory.index_deliveries")
        assert job["completed_at"] is None and job["error_code"] == "projection_unavailable"
        assert await conn.fetchval("SELECT count(*) FROM shared_memory.index_receipts") == 0
        await conn.execute("UPDATE shared_memory.index_deliveries SET retry_at=now()+interval '1 minute'")
    assert not await p.worker.run_once()
    assert (await p.service.status(p.scope))["change_feed_worker"] == "degraded"
    async with p.pool.acquire() as conn:
        await conn.execute("UPDATE shared_memory.index_deliveries SET retry_at=now()")
    assert (await p.service.recall(p.scope, "Cedar"))["results"][0]["id"] == record["id"]
    p.sinks.fail = False
    restarted = IndexWorker(p.service, p.sinks)
    assert await restarted.run_once() and not await restarted.run_once()
    assert p.sinks.records[record["id"]] == (1, True)
    async with p.pool.acquire() as conn:
        assert await conn.fetchval("SELECT attempts FROM shared_memory.index_deliveries") == 2
        assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_versions") == 1


@pytest.mark.asyncio
async def test_cancelled_delivery_reclaims_lease_without_losing_memory(pipeline):
    p = pipeline
    record = await seed(p)
    p.sinks.cancel = True
    with pytest.raises(asyncio.CancelledError):
        await p.worker.run_once()
    assert not await p.worker.run_once()  # A live lease cannot be stolen.
    async with p.pool.acquire() as conn:
        await conn.execute("UPDATE shared_memory.index_deliveries SET lease_until=now()-interval '1 second'")
    p.sinks.cancel = False
    assert await IndexWorker(p.service, p.sinks).run_once()
    assert (await p.service.get(p.scope, record["id"]))["version"] == 1
    assert len(p.sinks.edges) == 1


@pytest.mark.asyncio
async def test_multiple_workers_correction_and_retraction(pipeline):
    p = pipeline
    record = await seed(p)
    replies = await asyncio.gather(*(IndexWorker(p.service, p.sinks).run_once() for _ in range(4)))
    assert sum(replies) == 1
    assert len(p.sinks.edges) == 1
    changed = "Cedar depends on Maple."
    await p.service.correct(p.scope, record["id"], expected_version=1, content=changed,
                            knowledge_links=[link(changed, "Cedar", "depends on", "Maple")])
    assert await p.worker.run_once()
    assert p.sinks.records[record["id"]] == (2, True)
    assert p.sinks.edges[0]["target_key"] == p.sinks.entity(p.scope.tenant, "Maple")
    await p.service.correct(p.scope, record["id"], expected_version=2, retract=True)
    # Authoritative denial applies even before the delayed projection cleanup.
    assert (await p.service.connections(p.scope, "Cedar"))["paths"] == []
    assert await p.worker.run_once()
    assert p.sinks.records[record["id"]] == (3, False) and not p.sinks.edges
    async with p.pool.acquire() as conn:
        assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_versions") == 3


@pytest.mark.asyncio
async def test_inflight_snapshot_cannot_overwrite_a_correction(pipeline):
    p = pipeline
    record = await seed(p)
    p.sinks.release = asyncio.Event()
    delivered = asyncio.create_task(p.worker.run_once())
    await asyncio.wait_for(p.sinks.entered.wait(), 3)
    correction = asyncio.create_task(p.service.correct(p.scope, record["id"], expected_version=1,
        content="Cedar depends on Maple."))
    await asyncio.sleep(.05)
    assert not correction.done()
    p.sinks.release.set()
    await delivered
    await correction
    assert await p.worker.run_once()
    assert p.sinks.records[record["id"]] == (2, True) and not p.sinks.edges


@pytest.mark.asyncio
async def test_multihop_rechecks_each_source_and_sharing_revocation(pipeline):
    p = pipeline
    first = await seed(p)
    second = await seed(p, "Birch is hosted in Lisbon.", "Birch", "Lisbon", "two")
    await p.worker.run_once()
    await p.worker.run_once()
    result = await p.service.connections(p.scope, "Cedar", depth=2)
    assert len(result["paths"][-1]) == 2
    assert result["paths"][-1][-1]["object"] == "Lisbon"
    assert all(edge["version"] == 1 for edge in result["paths"][-1])
    other = MemoryScope(p.scope.tenant, "reader", "reader", "agent")
    assert (await p.service.connections(other, "Cedar"))["paths"] == []
    reviewer = MemoryScope(p.scope.tenant, p.scope.project, "reviewer", "operator", admin=True)
    await p.service.share(reviewer, first["id"], target_project="reader", expected_version=1)
    assert max(map(len, (await p.service.connections(other, "Cedar"))["paths"])) == 1
    await p.service.share(reviewer, second["id"], target_project="reader", expected_version=1)
    assert max(map(len, (await p.service.connections(other, "Cedar"))["paths"])) == 2
    await p.service.share(reviewer, second["id"], target_project="reader", expected_version=1, revoke=True)
    assert max(map(len, (await p.service.connections(other, "Cedar"))["paths"])) == 1
    await p.service.correct(p.scope, first["id"], expected_version=1, content="Cedar has a new dependency.")
    assert (await p.service.connections(p.scope, "Cedar"))["paths"] == []
    async with p.pool.acquire() as conn:
        await conn.execute("UPDATE shared_memory.index_workers SET heartbeat=now()-interval '60 seconds'")
    with pytest.raises(AuthError) as error:
        await p.service.connections(p.scope, "Cedar")
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_expired_projection_is_inactivated_and_scope_history_stays_private(pipeline):
    p = pipeline
    record = await p.service.remember(p.scope, "Cedar expiry fixture", idempotency_key="expired",
        expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
    assert await p.worker.run_once()
    assert p.sinks.records[record["id"]] == (1, False)
    while await p.worker.run_once():
        pass
    assert (await p.service.list_records(p.scope))["results"] == []
    assert (await p.service.history(p.scope, record["id"]))["versions"][0]["content"] == "Cedar expiry fixture"
    with pytest.raises(KeyError):
        await p.service.history(MemoryScope(p.scope.tenant, "source", "stranger", "agent"), record["id"])


@pytest.mark.asyncio
async def test_worker_role_cannot_edit_records_and_runtime_cannot_claim_deliveries(pipeline, tmp_path):
    p = pipeline
    worker_file, runtime_file = tmp_path / "worker.json", tmp_path / "runtime.json"
    await grant_worker(p.pool, role="worker_" + uuid.uuid4().hex[:20], operator_url=p.url, output=str(worker_file))
    await grant_runtime(p.pool, role="runtime_" + uuid.uuid4().hex[:20], operator_url=p.url, output=str(runtime_file))
    record = await seed(p)
    worker_pool = await asyncpg.create_pool(json.loads(worker_file.read_text())["ENHANCED_INDEX_DATABASE_URL"], min_size=1, max_size=2)
    runtime_pool = await asyncpg.create_pool(json.loads(runtime_file.read_text())["ENHANCED_MEMORY_DATABASE_URL"], min_size=1, max_size=1)
    try:
        worker_service = MemoryService(worker_pool, p.service.cipher, p.service.embedder)
        assert await IndexWorker(worker_service, p.sinks).run_once()
        async with worker_pool.acquire() as conn:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute("UPDATE shared_memory.records SET version=99")
        async with runtime_pool.acquire() as conn:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute("UPDATE shared_memory.index_deliveries SET completed_at=now()")
        assert (await p.service.get(p.scope, record["id"]))["version"] == 1
    finally:
        await worker_pool.close()
        await runtime_pool.close()


@pytest.mark.asyncio
async def test_selected_corrections_reject_private_metadata_and_history_withholds_secrets(pipeline):
    p = pipeline
    record = await seed(p)
    selected = MemoryScope(p.scope.tenant, p.scope.project, p.scope.subject, p.scope.agent, selected_capture=True)
    with pytest.raises(MemoryClarificationRequired):
        await p.service.correct(selected, record["id"], expected_version=1, content=record["content"],
                                metadata={"contact": "person@example.invalid"})
    assert (await p.service.get(selected, record["id"]))["version"] == 1
