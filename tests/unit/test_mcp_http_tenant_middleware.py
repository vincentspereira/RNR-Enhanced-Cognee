"""Tests for the FastAPI tenant middleware in enhanced_cognee_mcp.

Asserts that the `X-Tenant-ID` request header propagates into the
TenantContext for the duration of the request handler, so any
downstream storage call sees the right tenant.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


def _make_server():
    from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer

    srv = EnhancedCogneeMCPServer()
    return srv


@pytest.fixture
def test_client_with_probe(monkeypatch):
    """A FastAPI TestClient with a probe route that captures the active tenant."""
    from fastapi.testclient import TestClient
    from src.multi_tenant import get_tenant

    srv = _make_server()

    captured: dict[str, Any] = {"tenant": "NOT_SET"}

    @srv.app.get("/_probe/tenant")
    def _probe() -> dict[str, Any]:
        captured["tenant"] = get_tenant()
        return {"tenant": captured["tenant"]}

    return TestClient(srv.app), captured


class TestTenantHeader:
    def test_no_header_leaves_context_none(self, test_client_with_probe):
        client, captured = test_client_with_probe
        resp = client.get("/_probe/tenant")
        assert resp.status_code == 200
        assert resp.json() == {"tenant": None}
        assert captured["tenant"] is None

    def test_header_sets_tenant_context(self, test_client_with_probe):
        client, captured = test_client_with_probe
        resp = client.get("/_probe/tenant", headers={"X-Tenant-ID": "acme"})
        assert resp.status_code == 200
        assert resp.json() == {"tenant": "acme"}
        assert captured["tenant"] == "acme"

    def test_header_is_case_insensitive(self, test_client_with_probe):
        client, captured = test_client_with_probe
        resp = client.get("/_probe/tenant", headers={"x-tenant-id": "globex"})
        assert resp.status_code == 200
        assert resp.json() == {"tenant": "globex"}
        assert captured["tenant"] == "globex"

    def test_context_isolated_across_requests(self, test_client_with_probe):
        client, captured = test_client_with_probe

        r1 = client.get("/_probe/tenant", headers={"X-Tenant-ID": "first"})
        assert r1.json()["tenant"] == "first"

        r2 = client.get("/_probe/tenant", headers={"X-Tenant-ID": "second"})
        assert r2.json()["tenant"] == "second"

        # And without the header, context is None
        r3 = client.get("/_probe/tenant")
        assert r3.json()["tenant"] is None

    def test_tenant_id_sanitised(self, test_client_with_probe):
        """Dash in the header becomes underscore in TenantContext."""
        client, captured = test_client_with_probe
        resp = client.get("/_probe/tenant", headers={"X-Tenant-ID": "acme-corp"})
        assert resp.json()["tenant"] == "acme_corp"
