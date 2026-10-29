"""Public-boundary regressions for the October audit (fake stores only)."""
import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.security import enterprise_auth as auth
from tests.unit.test_mcp_http_rbac import REAL_JWT


def test_lifecycle_modules_import_before_any_tenant_is_selected():
    """Startup can describe tools; storage still requires a request tenant."""
    env = {key: value for key, value in os.environ.items()
           if not any(word in key.upper() for word in
                      ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "DATABASE_URL"))}
    env.update(ENHANCED_ENV="production", ENHANCED_REQUIRE_TENANT="1",
               COGNEE_LOG_FILE="false", ENHANCED_LOAD_DOTENV="0")
    code = """
from src.multi_tenant import get_tenant, tenant_scoped_table, MissingTenantError
assert get_tenant() is None
from src.memory_provenance import MemoryProvenanceTracker
from src.memory_confidence import MemoryConfidenceManager
from src.encryption_manager import EncryptionManager
assert MemoryProvenanceTracker.__doc__
assert MemoryConfidenceManager.__doc__
assert EncryptionManager.get_encryption_stats.__doc__
try:
    tenant_scoped_table('shared_memory.documents')
except MissingTenantError:
    pass
else:
    raise AssertionError('Import must not relax tenant enforcement')
"""
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_vector_category_discovery_and_query_use_the_same_tenant(monkeypatch):
    from src import enhanced_cognee_mcp as mod
    from src.multi_tenant import TenantContext, tenant_scoped_collection
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    monkeypatch.setattr(mod.config, "memory_categorization", True)
    monkeypatch.setattr(mod.config, "category_prefixes", {"custom_fixture": "custom_"})
    server = mod.EnhancedCogneeMCPServer()
    server.qdrant_client = MagicMock()
    with TenantContext("qualified_owner"):
        expected = tenant_scoped_collection(server._get_collection_name("custom_fixture", ""))

        def existing(name):
            if name != expected:
                raise LookupError("No unscoped collection exists")

        server.qdrant_client.get_collection.side_effect = existing
        server.qdrant_client.search.return_value = [SimpleNamespace(
            id="fixture", score=0.9, payload={"content": "Synthetic vector fixture",
                "agent_id": "fixture-agent", "memory_category": "custom_fixture",
                "created_at": "2026-10-19T00:00:00Z"})]
        results = await server.search_memory(mod.SearchQuery(query="fixture", embedding=[1.0, 0.0]))
        assert [row["id"] for row in results] == ["fixture"]
        assert server.qdrant_client.search.call_args.kwargs["collection_name"] == expected


@pytest.fixture
def boundary(monkeypatch):
    from src import enhanced_cognee_mcp as mod
    for name in ("ENHANCED_API_KEY", "ENHANCED_OIDC_ISSUER", "ENHANCED_OIDC_JWKS_URI", "ENHANCED_OIDC_AUDIENCE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENHANCED_ENV", "production")
    monkeypatch.setenv("ENHANCED_JWT_SECRET", "audit-regression-signing-key-at-least-32-bytes")
    monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
    monkeypatch.setattr(auth, "jwt", REAL_JWT)
    monkeypatch.setattr(mod.config, "enhanced_mode", False)
    srv = mod.EnhancedCogneeMCPServer()
    srv.add_memory = AsyncMock(return_value="synthetic-id")
    srv.search_memory = AsyncMock(return_value=[])
    return TestClient(srv.app, raise_server_exceptions=False), srv


def credentials(role="readonly", tenant="audit_a", **extra):
    claims = dict(sub="audit-agent", roles=[role], tenant=tenant, exp=int(time.time()) + 60, **extra)
    token = REAL_JWT.encode(claims, "audit-regression-signing-key-at-least-32-bytes", algorithm="HS256")
    return {"Authorization": "Bearer " + token}


def test_all_registered_tools_have_policy():
    tree = ast.parse(Path("bin/enhanced_cognee_mcp_server.py").read_text())
    names = [n.name for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
             and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                     and d.func.attr == "tool" for d in n.decorator_list)]
    assert len(names) >= 122
    assert all(auth.tool_required_permission(name) is not None for name in names)
    with pytest.raises(auth.AuthError):
        auth.tool_required_permission("unreviewed_new_tool")


@pytest.mark.parametrize("tool", ["remember", "improve", "revert_memory", "undo_last", "load_document_with_plugin", "schedule_task", "verify_memory"])
def test_readonly_cannot_reach_mutating_tools(boundary, tool):
    client, _ = boundary
    assert client.post("/tools/" + tool, json={}, headers=credentials()).status_code == 403


def test_credential_tenant_cannot_be_overridden(boundary):
    client, srv = boundary
    headers = credentials("api_client") | {"X-Tenant-ID": "audit_b"}
    response = client.post("/mcp/add_memory", json={"content": "synthetic", "agent_id": "audit-agent"}, headers=headers)
    assert response.status_code == 403
    srv.add_memory.assert_not_called()


def test_writer_cannot_be_impersonated(boundary):
    client, srv = boundary
    response = client.post("/mcp/add_memory", json={"content": "synthetic", "agent_id": "other-agent"}, headers=credentials("api_client"))
    assert response.status_code == 403
    srv.add_memory.assert_not_called()


def test_credential_tenant_is_used_without_header(boundary):
    client, srv = boundary
    assert client.post("/mcp/add_memory", json={"content": "synthetic", "agent_id": "audit-agent"}, headers=credentials("api_client")).status_code == 200
    srv.add_memory.assert_awaited_once()


@pytest.mark.parametrize("stream", [True, False])
def test_body_limit_counts_received_bytes(boundary, monkeypatch, stream):
    client, srv = boundary
    monkeypatch.setenv("ENHANCED_MAX_PAYLOAD_BYTES", "128")
    body = json.dumps({"query": "a" * 512}).encode()
    headers = credentials() | {"Content-Type": "application/json"}
    response = client.post("/memory/search", headers=headers, content=iter([body]) if stream else body)
    assert response.status_code == 413
    srv.search_memory.assert_not_called()


def test_dashboard_requires_credentials(boundary):
    import dashboard.dashboard_api as dashboard
    client = TestClient(dashboard.app, raise_server_exceptions=False)
    assert client.delete("/api/memories/00000000-0000-0000-0000-000000000001").status_code == 401


def test_project_credential_cannot_enter_legacy_routes(boundary):
    client, srv = boundary
    response = client.post("/mcp/search_memories", json={"query": "fixture"}, headers=credentials(project_id="project_one"))
    assert response.status_code == 403
    srv.search_memory.assert_not_called()


def test_expiration_is_mandatory_for_production_tokens(boundary):
    client, _ = boundary
    token = REAL_JWT.encode({"sub": "audit-agent", "tenant": "audit_a", "roles": ["readonly"]},
                            "audit-regression-signing-key-at-least-32-bytes", algorithm="HS256")
    assert client.post("/mcp/search_memories", json={"query": "fixture"}, headers={"Authorization": "Bearer " + token}).status_code == 401


def test_invalid_nested_arguments_rejected(boundary):
    client, _ = boundary
    assert client.post("/tools/search_memories", json={"arguments": []}, headers=credentials()).status_code == 422


@pytest.mark.asyncio
async def test_slow_body_is_rejected_within_deadline(boundary, monkeypatch):
    import asyncio
    import httpx
    _, server = boundary
    monkeypatch.setenv("ENHANCED_BODY_TIMEOUT_SECONDS", "0.01")

    async def slow_body():
        yield b'{"query":'
        await asyncio.sleep(0.1)
        yield b'"fixture"}'

    headers = credentials() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://fixture") as client:
        response = await client.post("/memory/search", headers=headers, content=slow_body())
    assert response.status_code == 408
    server.search_memory.assert_not_called()


@pytest.mark.parametrize("tenant", ["audit-a", "Audit_a", "a" * 64, "audit.a", "123audit"])
def test_noncanonical_external_tenant_rejected(tenant):
    from src.multi_tenant import validate_tenant_id
    with pytest.raises(ValueError):
        validate_tenant_id(tenant)
