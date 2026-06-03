"""Integration tests for the generic MCP tool dispatch route
``POST /tools/{tool_name}`` in src/enhanced_cognee_mcp.py.

This route exposes ALL 122 MCP tools over HTTP (the surface the
enhanced_cognee_client SDK and examples/ target). The tests drive the real
FastAPI middleware chain via TestClient and assert:

  * authentication (401 when JWT configured + no token),
  * per-tool RBAC via the shared TOOL_PERMISSIONS table -- crucially that a
    read-only principal is blocked from BOTH a delete-tier tool AND an
    admin-tier tool (create_backup), which the pre-existing path-heuristic
    would have left reachable with only authentication,
  * unknown-tool -> 404,
  * both accepted payload shapes ({"arguments": {...}} from the SDK and a bare
    {...} from examples/) unwrap to the same tool arguments,
  * successful dispatch + result serialization.

The FastMCP tool backend is mocked, so no DB and no heavy bin-module import is
needed -- the auth/authz decisions happen in middleware before the handler, and
the dispatch/serialization logic is exercised against the fake registry.
"""

from __future__ import annotations

import importlib as _importlib
import sys as _sys

import pytest
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


class _FakeMCP:
    """Stand-in for the FastMCP registry. Records the last dispatched call and
    returns FastMCP's (content_blocks, structured_dict) tuple shape.
    """

    def __init__(self):
        self.last_name = None
        self.last_args = None

    async def call_tool(self, name, arguments):
        self.last_name = name
        self.last_args = dict(arguments)
        return ([], {"result": f"ok:{name}"})


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _AUTH_ENV:
        monkeypatch.delenv(var, raising=False)
    import src.security.enterprise_auth as _ea
    monkeypatch.setattr(_ea, "jwt", REAL_JWT)
    yield


@pytest.fixture
def fake_backend(monkeypatch):
    """Inject a mocked, already-initialised FastMCP backend into the module.

    Setting _bin_stack_ready=True short-circuits _ensure_bin_stack so no DB
    connection or bin-module import is attempted.
    """
    import src.enhanced_cognee_mcp as mod

    fake = _FakeMCP()
    monkeypatch.setattr(mod, "_bin_mcp", fake)
    monkeypatch.setattr(mod, "_bin_init_fn", lambda: None)
    monkeypatch.setattr(mod, "_bin_stack_ready", True)
    monkeypatch.setattr(
        mod,
        "_bin_tool_names",
        {"health", "add_memory", "search_memories", "delete_memory", "create_backup"},
    )
    return fake


@pytest.fixture
def server_app(monkeypatch, fake_backend):
    """A fresh FastAPI app instance with enhanced_mode disabled (no DB)."""
    import src.enhanced_cognee_mcp as mod

    monkeypatch.setattr(mod.config, "enhanced_mode", False)
    srv = mod.EnhancedCogneeMCPServer()
    return srv.app


@pytest.fixture
def client(server_app):
    """TestClient over the fresh server instance."""
    return TestClient(server_app, raise_server_exceptions=False)


def _bearer(secret: str, **claims) -> dict:
    token = REAL_JWT.encode(claims, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestToolsAuth:
    def test_no_token_rejected_when_jwt_configured(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        resp = client.post("/tools/health", json={"arguments": {}})
        assert resp.status_code == 401

    def test_dev_open_allows_when_no_auth_configured(self, client):
        # No auth env -> dev-open admin principal; dispatch should succeed.
        resp = client.post("/tools/health", json={"arguments": {}})
        assert resp.status_code == 200
        assert resp.json() == {"result": "ok:health"}


# ---------------------------------------------------------------------------
# Per-tool RBAC (the security-critical assertions)
# ---------------------------------------------------------------------------


class TestToolsRBAC:
    def test_readonly_blocked_from_delete_tool(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="ro", roles=["readonly"])
        resp = client.post("/tools/delete_memory", json={"arguments": {"memory_id": "x"}}, headers=headers)
        assert resp.status_code == 403

    def test_readonly_blocked_from_admin_tool(self, client, monkeypatch):
        # create_backup maps to SYSTEM_ADMIN. Before /tools routed through
        # TOOL_PERMISSIONS, the path heuristic returned None for this tool,
        # leaving it reachable with only authentication. This guards that gap.
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="ro", roles=["readonly"])
        resp = client.post("/tools/create_backup", json={"arguments": {}}, headers=headers)
        assert resp.status_code == 403

    def test_readonly_allowed_read_tool(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="ro", roles=["readonly"])
        resp = client.post("/tools/search_memories", json={"arguments": {"query": "hi"}}, headers=headers)
        assert resp.status_code not in (401, 403)

    def test_admin_allowed_delete_tool(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="boss", roles=["admin"])
        resp = client.post("/tools/delete_memory", json={"arguments": {"memory_id": "x"}}, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"result": "ok:delete_memory"}

    def test_admin_allowed_admin_tool(self, client, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        headers = _bearer("s", sub="boss", roles=["admin"])
        resp = client.post("/tools/create_backup", json={"arguments": {}}, headers=headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Dispatch behaviour: unknown tool, payload shapes, serialization
# ---------------------------------------------------------------------------


class TestToolsDispatch:
    def test_unknown_tool_404(self, client):
        resp = client.post("/tools/does_not_exist", json={"arguments": {}})
        assert resp.status_code == 404

    def test_sdk_envelope_shape_unwrapped(self, client, fake_backend):
        resp = client.post(
            "/tools/add_memory",
            json={"arguments": {"content": "x", "agent_id": "a"}},
        )
        assert resp.status_code == 200
        assert fake_backend.last_name == "add_memory"
        assert fake_backend.last_args == {"content": "x", "agent_id": "a"}

    def test_bare_args_shape_passed_through(self, client, fake_backend):
        # examples/ POST the arguments at the top level (no "arguments" wrapper).
        resp = client.post(
            "/tools/add_memory",
            json={"content": "x", "agent_id": "a"},
        )
        assert resp.status_code == 200
        assert fake_backend.last_name == "add_memory"
        assert fake_backend.last_args == {"content": "x", "agent_id": "a"}

    def test_result_serialized_to_json(self, client):
        resp = client.post("/tools/health", json={"arguments": {}})
        assert resp.status_code == 200
        assert resp.json() == {"result": "ok:health"}


# ---------------------------------------------------------------------------
# The real SDK class against the real route (in-process via ASGITransport)
#
# This is the MAS-facing artifact: enhanced_cognee_client.EnhancedCogneeClient
# talking to POST /tools/{tool_name}. Driving it through httpx's ASGITransport
# exercises the SDK's _call() -> route -> response.json() round-trip
# deterministically (no socket, CI-runnable) -- the seam the SDK's own
# transport-mocked unit tests cannot cover.
# ---------------------------------------------------------------------------


async def _sdk_over_asgi(server_app, token):
    """Build an EnhancedCogneeClient whose transport targets the ASGI app."""
    import httpx
    from enhanced_cognee_client import EnhancedCogneeClient

    sdk = EnhancedCogneeClient(host="testserver", port=80, api_key=token)
    await sdk._client.aclose()  # discard the auto-created socket client
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    sdk._client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server_app),
        base_url=sdk._base_url,
        headers=headers,
    )
    return sdk


class TestSdkAgainstRoute:
    async def test_sdk_add_memory_dispatches(self, server_app, monkeypatch, fake_backend):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        token = REAL_JWT.encode({"sub": "sdk", "roles": ["admin"]}, "s", algorithm="HS256")
        sdk = await _sdk_over_asgi(server_app, token)
        try:
            res = await sdk.add_memory(content="x", agent_id="a")
            assert res == {"result": "ok:add_memory"}
            assert fake_backend.last_name == "add_memory"
            assert fake_backend.last_args == {
                "content": "x", "user_id": "default", "agent_id": "a", "metadata": None,
            }
        finally:
            await sdk.close()

    async def test_sdk_search_memories_wraps_result(self, server_app, monkeypatch, fake_backend):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        token = REAL_JWT.encode({"sub": "sdk", "roles": ["admin"]}, "s", algorithm="HS256")
        sdk = await _sdk_over_asgi(server_app, token)
        try:
            # The route returns a dict; the SDK wraps a non-list result in a list.
            res = await sdk.search_memories(query="q", agent_id="a")
            assert res == [{"result": "ok:search_memories"}]
        finally:
            await sdk.close()

    async def test_sdk_health_dev_open(self, server_app, fake_backend):
        # No auth configured -> dev-open admin; the SDK (no api_key) still works.
        sdk = await _sdk_over_asgi(server_app, token=None)
        try:
            res = await sdk.health()
            assert res == {"result": "ok:health"}
        finally:
            await sdk.close()

    async def test_sdk_auth_error_returns_error_dict(self, server_app, monkeypatch, fake_backend):
        # JWT configured but the SDK sends no token -> 401 -> SDK maps to an error dict.
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        sdk = await _sdk_over_asgi(server_app, token=None)
        try:
            res = await sdk.add_memory(content="x", agent_id="a")
            assert "error" in res and "401" in res["error"]
        finally:
            await sdk.close()
