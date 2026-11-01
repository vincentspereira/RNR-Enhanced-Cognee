"""Selected capture, actual group authorization and restricted DB credentials."""
import json
import os
import uuid

import asyncpg
import pytest
from cryptography.fernet import Fernet

from src.encryption_manager import EncryptionManager
from src.memory_service import MemoryService, MemoryScope, MemoryConflict, MemoryClarificationRequired
from src.memory_admin import grant_runtime, create_config, issue_token
from src.security.enterprise_auth import AuthError
from src.security.memory_admission import require_no_credentials


@pytest.mark.parametrize("text", [
    "password: correct-horse-battery", "api_key=synthetic-access-value", "access token is abcdefghijklmnop", "password: abc",
    "-----BEGIN RSA PRIVATE KEY-----", "Bearer syntheticcredentialmaterial", "postgresql://user:password@host/db",
    "AKIA" + "A" * 16, "xoxb-" + "a" * 30, "a" * 43 + "=",
])
def test_credentials_rejected_under_every_capture_mode(text):
    with pytest.raises(ValueError, match="Credential-shaped"):
        require_no_credentials(text)


@pytest.fixture
def url():
    value = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not value:
        pytest.skip("Select an explicitly disposable qualification database")
    return value


@pytest.mark.asyncio
async def test_library_requires_membership_review_current_version_and_no_private_details(url):
    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    tenant = "q_" + uuid.uuid4().hex[:20]
    source = MemoryScope(tenant, "source", "alice", "hermes", selected_capture=True)
    reviewer = MemoryScope(tenant, "source", "reviewer", "operator", admin=True)
    reader = MemoryScope(tenant, "reader", "bob", "reader")
    other = MemoryScope("q_" + uuid.uuid4().hex[:20], "reader", "eve", "reader")
    try:
        await service.initialize()
        for field in ("category", "idempotency_key", "fact_key"):
            arguments = {"idempotency_key": "credential-field-" + field,
                         field: "password: synthetic-fixture-only"}
            with pytest.raises(ValueError, match="Credential-shaped"):
                await service.remember(source, "A safe invented decision.", **arguments)
        for field in ("category", "idempotency_key"):
            arguments = {"idempotency_key": "private-field-" + field, field: "alice@example.test"}
            with pytest.raises(MemoryClarificationRequired):
                await service.remember(source, "A safe invented decision.", **arguments)
        async with pool.acquire() as connection:
            assert await connection.fetchval("SELECT count(*) FROM shared_memory.records WHERE tenant=$1", tenant) == 0
        record = await service.remember(source, "The reusable deployment decision uses cedar.",
            fact_key="deployment.storage", idempotency_key="one", metadata={"internal_session": "local-only"},
            evidence={"kind": "decision"})
        with pytest.raises(ValueError, match="Credential-shaped"):
            await service.correct(source, record["id"], expected_version=1,
                content=record["content"], category="password: synthetic-fixture-only")
        assert (await service.get(source, record["id"]))["version"] == 1
        with pytest.raises(MemoryConflict):
            await service.remember(source, "The deployment decision uses birch.",
                fact_key="deployment.storage", idempotency_key="contradiction")
        with pytest.raises(MemoryClarificationRequired):
            await service.remember(source, "Contact the owner at alice@example.test", idempotency_key="private")
        with pytest.raises(AuthError):
            await service.set_library_member(source, library="portfolio", member_project="reader", admitted=True)
        await service.set_library_member(reviewer, library="portfolio", member_project="source", admitted=True, can_publish=True)
        await service.set_library_member(reviewer, library="portfolio", member_project="reader", admitted=True)
        assert (await service.recall(reader, "cedar"))["results"] == []
        await service.publish_library(reviewer, record["id"], library="portfolio", expected_version=1)
        shared = (await service.recall(reader, "cedar"))["results"][0]
        assert shared["shared"] and shared["metadata"] == {"source_project": "source"}
        assert "subject" not in shared["provenance"]
        assert (await service.get(reader, record["id"]))["id"] == record["id"]
        with pytest.raises(KeyError):
            await service.get(other, record["id"])
        assert (await service.recall(reader, "cedar", include_shared=False))["results"] == []
        await service.set_library_member(reviewer, library="portfolio", member_project="reader", admitted=False)
        with pytest.raises(KeyError):
            await service.get(reader, record["id"])
        await service.set_library_member(reviewer, library="portfolio", member_project="reader", admitted=True)
        await service.correct(source, record["id"], expected_version=1, content="The reusable deployment decision uses birch.")
        assert (await service.recall(reader, "birch"))["results"] == []
        with pytest.raises(MemoryConflict):
            await service.publish_library(reviewer, record["id"], library="portfolio", expected_version=1)
        await service.publish_library(reviewer, record["id"], library="portfolio", expected_version=2)
        await service.set_library_member(reviewer, library="portfolio", member_project="source", admitted=False)
        assert (await service.recall(reader, "birch"))["results"] == []
        await service.set_library_member(reviewer, library="portfolio", member_project="source", admitted=True, can_publish=True)
        assert (await service.recall(reader, "birch"))["results"] == []
        personal = await service.remember(reviewer, "Contact alice@example.test", idempotency_key="operator-private")
        with pytest.raises(ValueError, match="sanitized"):
            await service.publish_library(reviewer, personal["id"], library="portfolio", expected_version=1)
        assert (await service.get(reviewer, personal["id"]))["content"].endswith("example.test")
        private_link = await service.remember(reviewer, "Common uses Guide.", idempotency_key="private-link",
            knowledge_links=[{"subject": "Common", "predicate": "Contact person@example.test", "object": "Guide",
                              "span_start": 0, "span_end": 18}])
        with pytest.raises(ValueError, match="sanitized"):
            await service.publish_library(reviewer, private_link["id"], library="portfolio", expected_version=1)
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_runtime_role_uses_provisioned_schema_without_ddl_or_history_deletion(url, tmp_path):
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    role = "q_" + uuid.uuid4().hex[:20]
    path = tmp_path / "runtime.json"
    try:
        await MemoryService.provision(pool)
        await grant_runtime(pool, role=role, operator_url=url, output=str(path))
        assert path.stat().st_mode & 0o077 == 0
        runtime = await asyncpg.create_pool(json.loads(path.read_text())["ENHANCED_MEMORY_DATABASE_URL"], min_size=1, max_size=2)
        try:
            service = MemoryService(runtime, EncryptionManager(master_key=Fernet.generate_key().decode()))
            await service.check_schema()
            scope = MemoryScope(role, "project", "owner", "hermes")
            record = await service.remember(scope, "Synthetic restricted runtime fixture", idempotency_key="runtime")
            await service.correct(scope, record["id"], expected_version=1, content="Synthetic corrected runtime fixture")
            assert (await service.get(scope, record["id"]))["version"] == 2
            async with runtime.acquire() as conn:
                assert not await conn.fetchval("SELECT has_table_privilege(current_user,'shared_memory.records','DELETE')")
                assert not await conn.fetchval("SELECT has_table_privilege(current_user,'shared_memory.record_versions','DELETE')")
                assert not await conn.fetchval("SELECT has_table_privilege(current_user,'shared_memory.record_versions','UPDATE')")
                assert not await conn.fetchval("SELECT has_table_privilege(current_user,'shared_memory.record_audit','UPDATE')")
                assert not await conn.fetchval("SELECT has_schema_privilege(current_user,'shared_memory','CREATE')")
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await conn.execute("CREATE TABLE shared_memory.disallowed_runtime_table(id TEXT)")
        finally:
            await runtime.close()
    finally:
        await pool.close()


def test_new_keys_tokens_are_private_nonoverwriting_and_not_admin(tmp_path, monkeypatch):
    import jwt
    config = tmp_path / "config.json"
    create_config(str(config))
    values = json.loads(config.read_text())
    assert config.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        create_config(str(config))
    monkeypatch.setenv("ENHANCED_JWT_SECRET", values["ENHANCED_JWT_SECRET"])
    token_file = tmp_path / "token.json"
    issue_token(tenant="test_owner", project="test_project", subject="test_profile", agent="hermes", output=str(token_file))
    payload = jwt.decode(json.loads(token_file.read_text())["ENHANCED_COGNEE_ACCESS_TOKEN"], values["ENHANCED_JWT_SECRET"], algorithms=["HS256"])
    assert payload["capture_policy"] == "selected" and payload["roles"] == ["api_client"]
    assert payload["exp"] - payload["iat"] == 3600


@pytest.mark.asyncio
async def test_actual_api_selected_privacy_and_library_admin_boundaries(url, monkeypatch):
    import time
    import httpx
    import jwt
    from src.memory_api import create_app
    secret = "synthetic-selected-policy-signing-key-32bytes"
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_JWT_SECRET", secret)
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    for key in ("ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI"):
        monkeypatch.delenv(key, raising=False)
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    tenant = "q_" + uuid.uuid4().hex[:20]

    def headers(role="api_client"):
        return {"Authorization": "Bearer " + jwt.encode({"tenant": tenant, "project_id": "source",
            "agent_id": "hermes", "sub": "owner", "roles": [role], "capture_policy": "selected",
            "exp": int(time.time()) + 60}, secret, algorithm="HS256")}

    try:
        await service.initialize()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(service)), base_url="http://fixture") as client:
            private = await client.post("/v1/memories", headers=headers(), json={
                "content": "Contact person@example.test", "idempotency_key": "private"})
            assert private.status_code == 409 and private.json()["clarification_required"]
            password = "password: synthetic-do-not-store"
            response = await client.post("/v1/memories", headers=headers(), json={"content": password, "idempotency_key": "credential"})
            assert response.status_code == 422 and password not in response.text
            invalid = await client.post("/v1/memories", headers=headers(), json={"content": password, "unsupported_field": password})
            assert invalid.status_code == 422 and password not in invalid.text
            membership = {"library": "portfolio", "member_project": "reader", "admitted": True}
            assert (await client.post("/v1/memories/library/membership", json=membership, headers=headers())).status_code == 403
            assert (await client.post("/v1/memories/library/membership", json=membership, headers=headers("admin"))).status_code == 200
    finally:
        await pool.close()
