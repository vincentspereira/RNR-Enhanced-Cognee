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
def client(monkeypatch, fake_backend):
    """TestClient over a fresh server instance with enhanced_mode disabled."""
    import src.enhanced_cognee_mcp as mod

    monkeypatch.setattr(mod.config, "enhanced_mode", False)
    srv = mod.EnhancedCogneeMCPServer()
    return TestClient(srv.app, raise_server_exceptions=False)


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
