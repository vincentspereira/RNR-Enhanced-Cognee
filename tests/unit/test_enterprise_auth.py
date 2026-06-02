"""Unit tests for src/security/enterprise_auth.py.

Covers: Principal, role coercion + claim mapping, tenant extraction, route +
tool permission maps, authorize(), bearer (HS256 + mocked OIDC) verification,
authenticate_request() (dev-open / api-key / bearer / fail-closed), and the
stdio RBAC enforcement decision.
"""

from __future__ import annotations

import importlib as _importlib
import sys as _sys

import pytest


def _load_real_jwt():
    """Return the real PyJWT module even if a sibling test replaced
    ``sys.modules['jwt']`` with a MagicMock (tests/test_enhanced_security.py
    does this at import time). Leaves global sys.modules state untouched.
    """
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

from src.security.auth import Permission, Role
from src.security import enterprise_auth as ea


# ---------------------------------------------------------------------------
# Env isolation -- clear every auth knob before each test; tests opt back in.
# ---------------------------------------------------------------------------

_AUTH_ENV = (
    "ENHANCED_ENV",
    "ENHANCED_API_KEY",
    "ENHANCED_JWT_SECRET",
    "ENHANCED_JWT_ALGORITHMS",
    "ENHANCED_OIDC_ISSUER",
    "ENHANCED_OIDC_JWKS_URI",
    "ENHANCED_OIDC_AUDIENCE",
    "ENHANCED_OIDC_ALGORITHMS",
    "ENHANCED_OIDC_ROLE_CLAIM",
    "ENHANCED_OIDC_TENANT_CLAIM",
    "ENHANCED_OIDC_DEFAULT_ROLE",
    "ENHANCED_MCP_ROLE",
    "ENHANCED_MCP_ENFORCE_RBAC",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _AUTH_ENV:
        monkeypatch.delenv(var, raising=False)
    # Force the real PyJWT onto the module under test regardless of a sibling
    # test having swapped sys.modules['jwt'] for a mock (reverted after test).
    monkeypatch.setattr(ea, "jwt", REAL_JWT)
    # Clear discovery/JWKS caches so tests don't leak across each other.
    ea._JWKS_CLIENTS.clear()
    ea._DISCOVERY_CACHE.clear()
    yield


# ---------------------------------------------------------------------------
# Principal + role coercion
# ---------------------------------------------------------------------------


class TestPrincipal:
    def test_admin_has_all_permissions(self):
        p = ea.admin_principal("op", "api-key")
        assert p.role == Role.ADMIN
        for perm in Permission:
            assert p.has_permission(perm)

    def test_dev_principal_is_admin_open(self):
        p = ea.dev_principal()
        assert p.role == Role.ADMIN
        assert p.auth_method == "dev-open"


class TestRoleCoercion:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("admin", Role.ADMIN),
            ("Administrator", Role.ADMIN),
            ("user", Role.USER),
            ("editor", Role.USER),
            ("readonly", Role.READONLY),
            ("viewer", Role.READONLY),
            ("service_account", Role.API_CLIENT),
            ("nonsense", None),
            (None, None),
        ],
    )
    def test_coerce_role(self, value, expected):
        assert ea.coerce_role(value) == expected

    def test_role_from_claims_picks_highest(self):
        assert ea.role_from_claims({"roles": ["readonly", "admin"]}) == Role.ADMIN

    def test_role_from_claims_string_list(self):
        assert ea.role_from_claims({"roles": "viewer editor"}) == Role.USER

    def test_role_from_claims_keycloak_realm_access(self):
        claims = {"realm_access": {"roles": ["offline_access", "admin"]}}
        assert ea.role_from_claims(claims) == Role.ADMIN

    def test_role_from_claims_default_readonly(self):
        # Authenticated but no recognised role -> least privilege.
        assert ea.role_from_claims({"sub": "x"}) == Role.READONLY

    def test_role_from_claims_custom_default(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_OIDC_DEFAULT_ROLE", "user")
        assert ea.role_from_claims({"sub": "x"}) == Role.USER

    def test_custom_role_claim_name(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_OIDC_ROLE_CLAIM", "groups")
        assert ea.role_from_claims({"groups": ["admin"]}) == Role.ADMIN


class TestTenantFromClaims:
    def test_default_tenant_claim(self):
        assert ea.tenant_from_claims({"tenant": "acme"}) == "acme"

    def test_alternate_claims(self):
        assert ea.tenant_from_claims({"org_id": "globex"}) == "globex"

    def test_custom_tenant_claim(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_OIDC_TENANT_CLAIM", "company")
        assert ea.tenant_from_claims({"company": "initech"}) == "initech"

    def test_none_when_absent(self):
        assert ea.tenant_from_claims({"sub": "x"}) is None


# ---------------------------------------------------------------------------
# Permission maps + authorize
# ---------------------------------------------------------------------------


class TestRoutePermissions:
    def test_known_routes(self):
        assert ea.route_required_permission("POST", "/mcp/add_memory") == Permission.MEMORY_WRITE
        assert ea.route_required_permission("POST", "/mcp/delete_memory") == Permission.MEMORY_DELETE
        assert ea.route_required_permission("POST", "/mcp/search_memories") == Permission.MEMORY_READ
        assert ea.route_required_permission("GET", "/stats") == Permission.SYSTEM_MONITOR

    def test_public_paths_none(self):
        for p in ("/health", "/health/live", "/health/ready", "/metrics"):
            assert ea.route_required_permission("GET", p) is None

    def test_unknown_route_none(self):
        assert ea.route_required_permission("GET", "/_probe/whoami") is None

    def test_delete_verb_heuristic(self):
        assert ea.route_required_permission("DELETE", "/anything") == Permission.MEMORY_DELETE


class TestToolPermissions:
    def test_write_tools(self):
        assert ea.tool_required_permission("add_memory") == Permission.MEMORY_WRITE
        assert ea.tool_required_permission("cognify") == Permission.MEMORY_WRITE

    def test_delete_tools(self):
        assert ea.tool_required_permission("delete_memory") == Permission.MEMORY_DELETE
        assert ea.tool_required_permission("forget_memory") == Permission.MEMORY_DELETE

    def test_admin_tools(self):
        assert ea.tool_required_permission("create_backup") == Permission.SYSTEM_ADMIN

    def test_read_tools_unlisted(self):
        # Reads require only authentication (all roles hold MEMORY_READ).
        assert ea.tool_required_permission("search_memories") is None
        assert ea.tool_required_permission("get_stats") is None


class TestAuthorize:
    def test_none_permission_is_noop(self):
        ea.authorize(None, None)  # no raise

    def test_admin_allowed(self):
        ea.authorize(ea.admin_principal("a", "api-key"), Permission.MEMORY_DELETE)

    def test_readonly_denied_write(self):
        ro = ea.principal_from_claims({"sub": "r", "roles": ["readonly"]}, "jwt")
        with pytest.raises(ea.AuthError) as exc:
            ea.authorize(ro, Permission.MEMORY_WRITE)
        assert exc.value.status_code == 403

    def test_none_principal_denied(self):
        with pytest.raises(ea.AuthError) as exc:
            ea.authorize(None, Permission.MEMORY_READ)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Bearer token verification
# ---------------------------------------------------------------------------


class TestVerifyBearer:
    def test_hs256_roundtrip(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s3cret")
        token = REAL_JWT.encode({"sub": "alice", "roles": ["user"]}, "s3cret", algorithm="HS256")
        claims = ea.verify_bearer_token(token)
        assert claims["sub"] == "alice"

    def test_hs256_wrong_secret_rejected(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "right")
        token = REAL_JWT.encode({"sub": "alice"}, "wrong", algorithm="HS256")
        with pytest.raises(ea.AuthError) as exc:
            ea.verify_bearer_token(token)
        assert exc.value.status_code == 401

    def test_no_verifier_configured(self):
        token = REAL_JWT.encode({"sub": "x"}, "k", algorithm="HS256")
        with pytest.raises(ea.AuthError) as exc:
            ea.verify_bearer_token(token)
        assert exc.value.status_code == 401

    def test_audience_enforced(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        monkeypatch.setenv("ENHANCED_OIDC_AUDIENCE", "enhanced-cognee")
        good = REAL_JWT.encode(
            {"sub": "a", "aud": "enhanced-cognee"}, "s", algorithm="HS256"
        )
        assert ea.verify_bearer_token(good)["sub"] == "a"
        bad = REAL_JWT.encode({"sub": "a", "aud": "other"}, "s", algorithm="HS256")
        with pytest.raises(ea.AuthError):
            ea.verify_bearer_token(bad)

    def test_oidc_path_with_mocked_jwks(self, monkeypatch):
        # Exercise the asymmetric/OIDC branch without RSA/network by pointing
        # the JWKS client at a fake whose key is an HS256 secret and forcing
        # the HS256 algorithm.
        monkeypatch.setenv("ENHANCED_OIDC_JWKS_URI", "https://idp.example/jwks")
        monkeypatch.setenv("ENHANCED_OIDC_ALGORITHMS", "HS256")

        class _FakeKey:
            key = "oidc-secret"

        class _FakeClient:
            def get_signing_key_from_jwt(self, token):
                return _FakeKey()

        monkeypatch.setattr(ea, "_jwks_client", lambda uri: _FakeClient())
        token = REAL_JWT.encode({"sub": "bob", "roles": ["admin"]}, "oidc-secret", algorithm="HS256")
        claims = ea.verify_bearer_token(token)
        assert claims["sub"] == "bob"


# ---------------------------------------------------------------------------
# authenticate_request
# ---------------------------------------------------------------------------


class TestAuthenticateRequest:
    def test_dev_open_when_unconfigured(self):
        p = ea.authenticate_request({})
        assert p.role == Role.ADMIN
        assert p.auth_method == "dev-open"

    def test_production_unconfigured_fails_closed(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_ENV", "production")
        with pytest.raises(ea.AuthError) as exc:
            ea.authenticate_request({})
        assert exc.value.status_code == 401

    def test_api_key_admin(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-123")
        p = ea.authenticate_request({"x-api-key": "sk-123"})
        assert p.role == Role.ADMIN
        assert p.auth_method == "api-key"

    def test_api_key_wrong_rejected(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-123")
        with pytest.raises(ea.AuthError) as exc:
            ea.authenticate_request({"x-api-key": "nope"})
        assert exc.value.status_code == 401

    def test_api_key_missing_when_configured(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk-123")
        with pytest.raises(ea.AuthError) as exc:
            ea.authenticate_request({})
        assert exc.value.status_code == 401

    def test_bearer_readonly(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        token = REAL_JWT.encode({"sub": "ro", "roles": ["readonly"]}, "s", algorithm="HS256")
        p = ea.authenticate_request({"authorization": f"Bearer {token}"})
        assert p.role == Role.READONLY
        assert p.subject == "ro"

    def test_bearer_takes_precedence_over_api_key(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_API_KEY", "sk")
        monkeypatch.setenv("ENHANCED_JWT_SECRET", "s")
        token = REAL_JWT.encode({"sub": "u", "roles": ["user"]}, "s", algorithm="HS256")
        p = ea.authenticate_request(
            {"authorization": f"Bearer {token}", "x-api-key": "sk"}
        )
        assert p.role == Role.USER  # bearer used, not the admin api-key


# ---------------------------------------------------------------------------
# Config detection + stdio RBAC
# ---------------------------------------------------------------------------


class TestConfigDetection:
    def test_auth_configured_flags(self, monkeypatch):
        assert ea.auth_configured() is False
        monkeypatch.setenv("ENHANCED_API_KEY", "x")
        assert ea.auth_configured() is True

    def test_oidc_configured(self, monkeypatch):
        assert ea.oidc_configured() is False
        monkeypatch.setenv("ENHANCED_OIDC_ISSUER", "https://idp")
        assert ea.oidc_configured() is True


class TestStdioRBAC:
    def test_default_admin_not_enforced(self):
        assert ea.stdio_rbac_enforced() is False
        assert ea.local_principal().role == Role.ADMIN

    def test_readonly_role_enforced(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_MCP_ROLE", "readonly")
        assert ea.stdio_rbac_enforced() is True
        assert ea.local_principal().role == Role.READONLY

    def test_explicit_enforce_flag(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_MCP_ENFORCE_RBAC", "1")
        assert ea.stdio_rbac_enforced() is True

    def test_log_status_smoke(self, caplog):
        with caplog.at_level("INFO", logger="src.security.enterprise_auth"):
            ea.log_enterprise_auth_status()
        assert any("Enterprise auth" in r.getMessage() for r in caplog.records)
