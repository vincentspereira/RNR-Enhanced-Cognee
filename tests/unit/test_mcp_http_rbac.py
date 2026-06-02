"""Integration tests for HTTP RBAC + authentication middleware in
src/enhanced_cognee_mcp.py.

Drives the real FastAPI middleware chain via TestClient and asserts the
authn/authz decisions (401 unauthenticated, 403 lacking permission, public
paths bypass, dev-open admin, api-key admin, bearer roles). DB clients are
not needed because the auth/authz decisions happen in middleware before any
route handler runs.
"""

from __future__ import annotations

import importlib as _importlib
import sys as _sys

import pytest
from fastapi import Request
from fastapi.testclient import TestClient


def _load_real_jwt():
    """Real PyJWT even if a sibling test swapped sys.modules['jwt'] for a mock."""
    cur = _sys.modules.get("jwt")
    if cur is not None and hasattr(cur, "__file__") and "Mock" not in type(cur).__name__:
        return cur
    saved = {
        name: _sys.modules.pop(name)
        for name in [m for m in list(_sys.modules) if m == "jwt" or m.startswith("jwt.")]
    }
    try:
        real = _importlib.import_module("jwt")
    finally:
        _sys.modules.update(saved)
    return real


REAL_JWT = _load_real_jwt()

_AUTH_ENV = (
    "ENHANCED_ENV",
    "ENHANCED_API_KEY",
    "ENHANCED_JWT_SECRET",
    "ENHANCED_OIDC_ISSUER",
    "ENHANCED_OIDC_JWKS_URI",
    "ENHANCED_OIDC_AUDIENCE",
    "ENHANCED_REQUIRE_TENANT",
    "ENHANCED_METRICS_PUBLIC",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _AUTH_ENV:
        monkeypatch.delenv(var, raising=False)
    # The middleware verifies bearer tokens via src.security.enterprise_auth.jwt;
    # force the real PyJWT there in case a sibling test mocked it (auto-reverted).
    import src.security.enterprise_auth as _ea
    monkeypatch.setattr(_ea, "jwt", REAL_JWT)
    yield


@pytest.fixture
def client(monkeypatch):
    """TestClient over a real server instance with enhanced_mode disabled.

    enhanced_mode=False keeps any lifespan startup a no-op (no DB). A
    /_probe/whoami route echoes the resolved principal so we can assert who the
    middleware authenticated without touching storage.
    """
    import src.enhanced_cognee_mcp as mod

    monkeypatch.setattr(mod.config, "enhanced_mode", False)
    srv = mod.EnhancedCogneeMCPServer()

    @srv.app.get("/_probe/whoami")
    def _whoami(request: Request):
        p = getattr(request.state, "principal", None)
        return {
            "subject": getattr(p, "subject", None),
            "role": getattr(getattr(p, "role", None), "value", None),
            "auth_method": getattr(p, "auth_method", None),
        }

    return TestClient(srv.app, raise_server_exceptions=False)


def _bearer(secret: str, **claims) -> dict:
    token = REAL_JWT.encode(claims, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Dev-open (no auth configured)
# ---------------------------------------------------------------------------


class TestDevOpen:
    def test_whoami_is_admin_dev_open(self, client):
        resp = client.get("/_probe/whoami")
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "admin"
        assert body["auth_method"] == "dev-open"


# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------


class TestApiKey:
    def test_missing_key_rejected(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret")
        resp = client.get("/_probe/whoami")
        assert resp.status_code == 401

    def test_correct_key_is_admin(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret")
        resp = client.get("/_probe/whoami", headers={"X-API-Key": "sk-secret"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "admin"
        assert body["auth_method"] == "api-key"

    def test_wrong_key_rejected(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret")
        resp = client.get("/_probe/whoami", headers={"X-API-Key": "nope"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Bearer / RBAC
# ---------------------------------------------------------------------------


class TestBearerRBAC:
    def test_no_bearer_when_jwt_configured_rejected(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        resp = client.post("/mcp/delete_memory", json={"memory_id": "x"})
        assert resp.status_code == 401

    def test_readonly_blocked_from_delete(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="ro", roles=["readonly"])
        resp = client.post("/mcp/delete_memory", json={"memory_id": "x"}, headers=headers)
        assert resp.status_code == 403

    def test_readonly_allowed_to_search(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="ro", roles=["readonly"])
        resp = client.post(
            "/mcp/search_memories", json={"query": "hi"}, headers=headers
        )
        # Authorization passed (handler ran); must not be an auth rejection.
        assert resp.status_code not in (401, 403)

    def test_admin_allowed_to_delete(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="boss", roles=["admin"])
        resp = client.post("/mcp/delete_memory", json={"memory_id": "x"}, headers=headers)
        assert resp.status_code not in (401, 403)

    def test_whoami_reflects_bearer_role(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="dana", roles=["user"])
        resp = client.get("/_probe/whoami", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["subject"] == "dana"
        assert body["role"] == "user"


# ---------------------------------------------------------------------------
# Public paths bypass auth
# ---------------------------------------------------------------------------


class TestPublicPaths:
    def test_health_live_public(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret")
        resp = client.get("/health/live")  # no key
        assert resp.status_code == 200

    def test_metrics_public_by_default(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret")
        resp = client.get("/metrics")  # no key
        assert resp.status_code == 200

    def test_metrics_lockable(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-secret")
        monkeypatch.setenv("ENHANCED_METRICS_PUBLIC", "0")
        resp = client.get("/metrics")  # no key, now protected
        assert resp.status_code == 401
