"""Real PostgreSQL qualification; requires an explicitly disposable database.

RNR_QUALIFICATION_DATABASE_URL selects a test database. No default credentials
or production connection fallback is used. Fixtures are preserved for inspection.
"""
import asyncio
import os
import uuid

import asyncpg
import httpx
import jwt
import pytest
from cryptography.fernet import Fernet

from src.encryption_manager import EncryptionManager
from src.memory_service import MemoryConflict, MemoryScope, MemoryService
from src.memory_api import create_app
from src.security.enterprise_auth import AuthError


@pytest.mark.asyncio
async def test_expiry_transaction_rollback_and_shared_budget(database_url, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from src.security.enterprise_auth import principal_from_claims
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    tenant = "q_" + uuid.uuid4().hex[:20]
    scope = MemoryScope(tenant, "expiry", "alice", "hermes")
    svc = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    try:
        await svc.initialize()
        past = datetime.now(timezone.utc) - timedelta(days=1)
        expired = await svc.remember(scope, "Expired synthetic fixture", idempotency_key="expired", expires_at=past)
        assert (await svc.recall(scope, "fixture"))["results"] == []
        with pytest.raises(KeyError):
            await svc.get(scope, expired["id"])
        with pytest.raises(ValueError):
            await svc.remember(scope, "fixture", idempotency_key="naive", expires_at=datetime(2030, 1, 1))
        reviewer = MemoryScope(tenant, "expiry", "reviewer", "reviewer", admin=True)
        with pytest.raises(KeyError):
            await svc.share(reviewer, expired["id"], target_project="other", expected_version=1)
        original = svc._checkpoint

        async def failed_checkpoint(*args, **kwargs):
            raise RuntimeError("Synthetic failure after canonical insert")

        monkeypatch.setattr(svc, "_checkpoint", failed_checkpoint)
        with pytest.raises(RuntimeError):
            await svc.remember(scope, "Atomic synthetic fixture", idempotency_key="atomic")
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.records WHERE tenant=$1 AND idempotency_key='atomic'", tenant) == 0
        monkeypatch.setattr(svc, "_checkpoint", original)
        assert (await svc.remember(scope, "Atomic synthetic fixture", idempotency_key="atomic"))["version"] == 1
        bounded = MemoryService(pool, svc.cipher, candidate_budget_bytes=1)
        limited = await bounded.recall(scope, "fixture")
        assert limited["results"] == [] and limited["candidate_limit_reached"]
        full_content = "Resource fixture " + "x" * 6000
        large = await svc.remember(scope, full_content, idempotency_key="large")
        preview = (await svc.recall(scope, "Resource"))["results"][0]
        assert preview["content_truncated"] and len(preview["content"]) == 4096
        assert (await svc.get(scope, large["id"]))["content"] == full_content
        principal = principal_from_claims({"sub": "budget-user", "roles": ["readonly"], "tenant": tenant, "project_id": "expiry"}, "jwt")
        other_worker = MemoryService(pool, svc.cipher)
        # The budget is shared across service instances and concurrent workers.
        replies = await asyncio.gather(*[(svc if i % 2 else other_worker).admit_request(principal, 2) for i in range(8)], return_exceptions=True)
        assert sum(value is None for value in replies) == 2
        assert sum(isinstance(value, AuthError) and value.status_code == 429 for value in replies) == 6
    finally:
        await pool.close()


@pytest.fixture
def database_url():
    value = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not value:
        pytest.skip("Set RNR_QUALIFICATION_DATABASE_URL to a disposable PostgreSQL database")
    return value


@pytest.mark.asyncio
async def test_encryption_isolation_retries_versions_and_recovery(database_url):
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    key = Fernet.generate_key().decode()
    cipher = EncryptionManager(master_key=key)
    svc = MemoryService(pool, cipher)
    await svc.initialize()
    tenant = "q_" + uuid.uuid4().hex[:20]
    owner = MemoryScope(tenant, "engineering", "alice", "hermes")
    other = MemoryScope(tenant, "other", "alice", "hermes")
    stranger = MemoryScope("q_" + uuid.uuid4().hex[:20], "engineering", "alice", "hermes")
    reader = MemoryScope(tenant, "engineering", "bob", "assistant")
    reviewer = MemoryScope(tenant, "engineering", "reviewer", "reviewer", admin=True)
    fact = "The synthetic deployment uses cedar storage in Lisbon."
    try:
        # Concurrent retries acknowledge exactly one logical record and event.
        replies = await asyncio.gather(*[
            svc.remember(owner, fact, idempotency_key="one-logical-write") for _ in range(5)])
        ident = replies[0]["id"]
        assert {r["id"] for r in replies} == {ident}
        with pytest.raises(MemoryConflict):
            await svc.remember(owner, "Different content", idempotency_key="one-logical-write")
        async with pool.acquire() as conn:
            payload = await conn.fetchval("SELECT payload FROM shared_memory.records WHERE tenant=$1 AND id=$2", tenant, ident)
            assert payload.startswith("enc2:") and "Lisbon" not in payload
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_outbox WHERE tenant=$1", tenant) == 1
        assert (await svc.recall(other, "cedar"))["results"] == []
        assert (await svc.recall(stranger, "cedar"))["results"] == []
        assert (await svc.get(reader, ident))["content"] == fact
        with pytest.raises(KeyError):
            await svc.correct(reader, ident, expected_version=1, content="unauthorized")
        with pytest.raises(AuthError):
            await svc.share(owner, ident, target_project="other", expected_version=1)
        await svc.share(reviewer, ident, target_project="other", expected_version=1)
        shared = (await svc.recall(other, "cedar"))["results"]
        assert shared[0]["id"] == ident and shared[0]["shared"]
        assert (await svc.recall(other, "cedar", include_shared=False))["results"] == []
        assert (await svc.recall(stranger, "cedar"))["results"] == []
        await svc.share(reviewer, ident, target_project="other", expected_version=1, revoke=True)
        assert (await svc.recall(other, "cedar"))["results"] == []
        await svc.share(reviewer, ident, target_project="other", expected_version=1)
        changed = await svc.correct(owner, ident, expected_version=1, content="The deployment uses birch storage in Porto.")
        assert changed["version"] == 2
        assert (await svc.recall(other, "storage"))["results"] == []
        assert (await svc.recall(owner, "cedar"))["results"] == []
        with pytest.raises(MemoryConflict):
            await svc.correct(owner, ident, expected_version=1, content="stale update")
        # A fresh service/pool reads the committed version with the same key.
        await pool.close()
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
        svc = MemoryService(pool, EncryptionManager(master_key=key))
        assert (await svc.get(owner, ident))["version"] == 2
        await svc.correct(owner, ident, expected_version=2, retract=True)
        assert (await svc.recall(owner, "birch"))["results"] == []
        with pytest.raises(KeyError):
            await svc.get(owner, ident)
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_versions WHERE tenant=$1", tenant) == 3
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.record_outbox WHERE tenant=$1", tenant) == 3
        with pytest.raises(ValueError):
            await svc.remember(owner, "ghp_" + "a" * 35, idempotency_key="credential")
        with pytest.raises(ValueError):
            await svc.remember(owner, "ordinary content", idempotency_key="metadata", metadata={"key": "sk-" + "x" * 40})
        # Nonstandard JSON must fail before commit, rather than becoming a
        # stored record that the HTTP response cannot serialize.
        with pytest.raises(ValueError):
            await svc.remember(owner, "Synthetic finite-number fixture", idempotency_key="nonfinite", metadata={"value": float("nan")})
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT count(*) FROM shared_memory.records WHERE tenant=$1 AND idempotency_key='nonfinite'", tenant) == 0
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_authenticated_native_api_cannot_select_project(database_url, monkeypatch):
    import time
    secret = "qualification-only-signing-secret-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_JWT_SECRET", secret)
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    for name in ("ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI"):
        monkeypatch.delenv(name, raising=False)
    tenant = "q_" + uuid.uuid4().hex[:20]

    def credential(project="one", role="api_client", **extra):
        claims = dict(sub="profile-one", roles=[role], tenant=tenant, project_id=project,
                      agent_id="hermes", exp=int(time.time()) + 300)
        claims.update(extra)
        return {"Authorization": "Bearer " + jwt.encode(claims, secret, algorithm="HS256")}

    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
    try:
        svc = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
        await svc.initialize()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(svc)), base_url="http://qualification") as client:
            body = {"content": "Synthetic private project fact.", "idempotency_key": "native-one"}
            assert (await client.post("/v1/memories", json=body)).status_code == 401
            assert (await client.post("/v1/memories", json=body, headers=credential(role="readonly"))).status_code == 403
            assert (await client.post("/v1/memories", json=body | {"project_id": "other"}, headers=credential())).status_code == 403
            assert (await client.post("/v1/memories", json=body, headers=credential() | {"X-Tenant-ID": "other"})).status_code == 403
            stored = await client.post("/v1/memories", json=body, headers=credential())
            assert stored.status_code == 200, stored.text
            ident = stored.json()["id"]
            status = await client.get("/v1/memories/status", headers=credential())
            assert status.status_code == 200
            assert status.json()["project_id"] == "one" and status.json()["active_records"] == 1
            assert (await client.get("/v1/memories/status", headers=credential(exp=int(time.time()) - 1))).status_code == 401
            assert (await client.get("/v1/memories/" + ident, headers=credential(project="two"))).status_code == 404
            recalled = await client.post("/v1/memories/recall", json={"query": "private"}, headers=credential(role="readonly"))
            assert recalled.status_code == 200 and recalled.json()["results"][0]["id"] == ident
            assert (await client.post("/v1/memories/" + ident + "/share", json={"target_project": "two", "expected_version": 1}, headers=credential())).status_code == 403
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_local_semantic_paraphrase(database_url):
    cache = os.getenv("RNR_QUALIFICATION_MODEL_CACHE")
    if not cache:
        pytest.skip("Set RNR_QUALIFICATION_MODEL_CACHE to a prepared offline FastEmbed cache")
    from src.local_embeddings import LocalEmbeddings
    embedder = LocalEmbeddings("BAAI/bge-small-en-v1.5", cache)
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
    try:
        svc = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()), embedder)
        await svc.initialize()
        scope = MemoryScope("q_" + uuid.uuid4().hex[:20], "semantic", "alice", "hermes")
        expected = await svc.remember(scope, "The database backup is retained for thirty days.", idempotency_key="backup")
        await svc.remember(scope, "Lunch will be served at noon in the garden.", idempotency_key="lunch")
        recalled = await svc.recall(scope, "How long do we keep recovery copies?", limit=1)
        assert recalled["retrieval"] == "semantic"
        assert recalled["results"][0]["id"] == expected["id"]
    finally:
        await pool.close()
