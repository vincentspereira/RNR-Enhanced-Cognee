"""A separate expiring reviewer token can approve sharing without write/admin powers."""
import json
import os
import uuid

import asyncpg
from cryptography.fernet import Fernet
import httpx
import jwt
import pytest

from src.encryption_manager import EncryptionManager
from src.memory_admin import issue_token
from src.memory_api import create_app
from src.memory_service import MemoryService, MemoryScope
from src.security.auth import Permission, Role
from src.security.enterprise_auth import principal_from_claims


@pytest.mark.asyncio
async def test_review_token_cannot_edit_retract_or_administer_system(tmp_path, monkeypatch):
    url = os.getenv("RNR_QUALIFICATION_DATABASE_URL")
    if not url:
        pytest.skip("Select an explicitly disposable PostgreSQL database")
    secret = "synthetic-reviewer-verifier-key-at-least-32-bytes"
    monkeypatch.setenv("ENHANCED_JWT_SECRET", secret)
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    for key in ("ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI"):
        monkeypatch.delenv(key, raising=False)
    tenant = "review_"+uuid.uuid4().hex[:20]
    path = tmp_path / "reviewer.json"
    issue_token(tenant=tenant, project="source", subject="human_reviewer", agent="review_console",
                output=str(path), reviewer=True)
    token = json.loads(path.read_text())["ENHANCED_COGNEE_ACCESS_TOKEN"]
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    principal = principal_from_claims(claims, "jwt")
    assert principal.role == Role.MEMORY_REVIEWER
    assert principal.has_permission(Permission.MEMORY_ADMIN)
    assert not {Permission.MEMORY_WRITE, Permission.MEMORY_DELETE, Permission.SYSTEM_ADMIN, Permission.SYSTEM_CONFIG} & principal.permissions
    assert claims["exp"]-claims["iat"] == 3600
    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    service = MemoryService(pool, EncryptionManager(master_key=Fernet.generate_key().decode()))
    await service.initialize()
    scope = MemoryScope(tenant, "source", "writer", "hermes")
    record = await service.remember(scope, "Use reviewed summaries for common project guidance.", idempotency_key="review-one")
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(service)), base_url="http://localhost",
                                     headers={"Authorization": "Bearer "+token}) as http:
            assert (await http.get("/v1/memories/"+record["id"])).status_code == 200
            for method, path, body in (("POST", "/v1/memories", {"content": "Unapproved edit", "idempotency_key": "no"}),
                ("PATCH", "/v1/memories/"+record["id"], {"content": "Unapproved edit", "expected_version": 1}),
                ("POST", "/v1/memories/"+record["id"]+"/retract", {"expected_version": 1}),
                ("POST", "/tools/create_backup", {"arguments": {}}),
                ("POST", "/tools/rotate_encryption_key", {"arguments": {}})):
                assert (await http.request(method, path, json=body)).status_code == 403
            for project in ("source", "destination"):
                member = await http.post("/v1/memories/library/membership", json={"library": "shared_notes",
                    "member_project": project, "admitted": True, "can_publish": project == "source"})
                assert member.status_code == 200
            publication = await http.post("/v1/memories/"+record["id"]+"/library", json={"library": "shared_notes", "expected_version": 1})
            assert publication.status_code == 200
            destination = jwt.encode({**claims, "roles": ["api_client"], "project_id": "destination"}, secret, algorithm="HS256")
            shared = await http.get("/v1/memories/"+record["id"], headers={"Authorization": "Bearer "+destination})
            assert shared.status_code == 200 and shared.json()["shared"]
            assert (await http.get("/v1/memories/status", headers={"X-Tenant-ID": "another"})).status_code == 403
            assert (await http.post("/v1/memories/library/membership", json={"library": "shared_notes",
                "member_project": "destination", "admitted": False})).status_code == 200
            assert (await http.get("/v1/memories/"+record["id"], headers={"Authorization": "Bearer "+destination})).status_code == 404
        assert (await service.get(scope, record["id"]))["version"] == 1
    finally:
        await pool.close()
