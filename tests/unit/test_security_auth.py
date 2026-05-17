"""
Unit tests for src/security/auth.py
Covers: Role, Permission, ROLE_PERMISSIONS, JWTAuthenticator (create_token,
        verify_token, refresh_token), APIKeyManager (stubbed pool),
        RBACManager (sync methods + stubbed async methods).
"""

import importlib
import sys
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure the real jwt package is used for src.security.auth, even if an
# earlier test file (e.g. tests/test_enhanced_security.py) has replaced
# sys.modules['jwt'] with a MagicMock.  We temporarily restore real jwt,
# force-reimport the auth module so it binds to the real jwt classes, then
# put sys.modules back.
_mock_jwt = sys.modules.get('jwt')
_real_jwt = None

try:
    # Remove any mock that might be there and import the real package from disk
    _passlib_keys = [k for k in list(sys.modules.keys()) if k == 'jwt' or k.startswith('jwt.')]
    _saved_jwt_mods = {k: sys.modules.pop(k) for k in _passlib_keys}
    import jwt as _real_jwt_import
    _real_jwt = _real_jwt_import
    # Force-reimport auth module with real jwt bound
    sys.modules.pop('src.security.auth', None)
    import src.security.auth as _auth_mod_real  # noqa: F401 - side-effect import
    # Restore any mock entries for other test files that expect them
    for k, v in _saved_jwt_mods.items():
        if k != 'jwt':  # keep real jwt itself
            sys.modules[k] = v
    # Ensure sys.modules['jwt'] is the real one so auth module keeps using it
    sys.modules['jwt'] = _real_jwt
except Exception:
    # If anything fails, restore previous state
    if _mock_jwt is not None:
        sys.modules['jwt'] = _mock_jwt

import jwt as pyjwt  # noqa: E402 -- must come after real-jwt restoration above

from src.security.auth import (
    Role, Permission, ROLE_PERMISSIONS,
    JWTAuthenticator, APIKeyManager, RBACManager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(conn):
    """Minimal async-context-manager pool stub."""
    class _Ctx:
        async def __aenter__(self): return conn
        async def __aexit__(self, *a): pass

    class _Pool:
        def acquire(self): return _Ctx()

    return _Pool()


# ---------------------------------------------------------------------------
# Role / Permission / ROLE_PERMISSIONS
# ---------------------------------------------------------------------------

class TestRoleAndPermission:
    @pytest.mark.unit
    def test_role_values(self):
        assert Role.ADMIN == "admin"
        assert Role.USER == "user"
        assert Role.READONLY == "readonly"
        assert Role.API_CLIENT == "api_client"

    @pytest.mark.unit
    def test_permission_values(self):
        assert Permission.MEMORY_READ == "memory:read"
        assert Permission.SYSTEM_ADMIN == "system:admin"

    @pytest.mark.unit
    def test_admin_has_all_permissions(self):
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        for perm in Permission:
            assert perm in admin_perms

    @pytest.mark.unit
    def test_readonly_has_read_but_not_write(self):
        ro_perms = ROLE_PERMISSIONS[Role.READONLY]
        assert Permission.MEMORY_READ in ro_perms
        assert Permission.MEMORY_WRITE not in ro_perms
        assert Permission.MEMORY_DELETE not in ro_perms

    @pytest.mark.unit
    def test_api_client_lacks_admin(self):
        api_perms = ROLE_PERMISSIONS[Role.API_CLIENT]
        assert Permission.SYSTEM_ADMIN not in api_perms
        assert Permission.MEMORY_READ in api_perms

    @pytest.mark.unit
    def test_user_lacks_memory_admin(self):
        user_perms = ROLE_PERMISSIONS[Role.USER]
        assert Permission.MEMORY_ADMIN not in user_perms


# ---------------------------------------------------------------------------
# JWTAuthenticator
# ---------------------------------------------------------------------------

class TestJWTAuthenticator:
    @pytest.fixture
    def auth(self):
        return JWTAuthenticator(secret_key="test-secret", token_expiry_hours=1)

    @pytest.mark.unit
    def test_auto_generates_secret_when_none(self):
        auth = JWTAuthenticator()
        assert auth.secret_key is not None
        assert len(auth.secret_key) > 0

    @pytest.mark.unit
    def test_create_token_returns_string(self, auth):
        token = auth.create_token("user1")
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.unit
    def test_create_token_default_role_user(self, auth):
        token = auth.create_token("user1")
        payload = auth.verify_token(token)
        assert payload["role"] == Role.USER

    @pytest.mark.unit
    def test_create_token_custom_role(self, auth):
        token = auth.create_token("admin1", role=Role.ADMIN)
        payload = auth.verify_token(token)
        assert payload["role"] == Role.ADMIN

    @pytest.mark.unit
    def test_create_token_includes_additional_claims(self, auth):
        token = auth.create_token("user1", additional_claims={"org": "acme"})
        payload = auth.verify_token(token)
        assert payload["org"] == "acme"

    @pytest.mark.unit
    def test_verify_token_returns_payload(self, auth):
        token = auth.create_token("user42")
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "user42"

    @pytest.mark.unit
    def test_verify_token_contains_iat_and_exp(self, auth):
        token = auth.create_token("user1")
        payload = auth.verify_token(token)
        assert "iat" in payload
        assert "exp" in payload

    @pytest.mark.unit
    def test_verify_invalid_token_returns_none(self, auth):
        result = auth.verify_token("not.a.valid.token")
        assert result is None

    @pytest.mark.unit
    def test_verify_token_wrong_secret_returns_none(self, auth):
        other_auth = JWTAuthenticator(secret_key="other-secret")
        token = other_auth.create_token("user1")
        result = auth.verify_token(token)
        assert result is None

    @pytest.mark.unit
    def test_verify_expired_token_returns_none(self, auth):
        # Create a token that is already expired
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": "user1",
            "role": Role.USER,
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(payload, "test-secret", algorithm="HS256")
        result = auth.verify_token(expired_token)
        assert result is None

    @pytest.mark.unit
    def test_refresh_valid_token_returns_same_token(self, auth):
        token = auth.create_token("user1")
        refreshed = auth.refresh_token(token)
        assert refreshed == token

    @pytest.mark.unit
    def test_refresh_expired_token_returns_new_token(self, auth):
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": "user1",
            "role": Role.USER,
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(payload, "test-secret", algorithm="HS256")
        new_token = auth.refresh_token(expired_token)
        assert new_token is not None
        # New token should be valid
        new_payload = auth.verify_token(new_token)
        assert new_payload["user_id"] == "user1"

    @pytest.mark.unit
    def test_refresh_invalid_token_returns_none(self, auth):
        result = auth.refresh_token("garbage-token")
        assert result is None

    @pytest.mark.unit
    def test_different_algorithms_produce_different_tokens(self):
        auth_hs256 = JWTAuthenticator(secret_key="secret", algorithm="HS256")
        auth_hs384 = JWTAuthenticator(secret_key="secret", algorithm="HS384")
        token1 = auth_hs256.create_token("u1")
        token2 = auth_hs384.create_token("u1")
        assert token1 != token2


# ---------------------------------------------------------------------------
# APIKeyManager (DB-stubbed)
# ---------------------------------------------------------------------------

class TestAPIKeyManager:
    @pytest.fixture
    def conn(self):
        c = AsyncMock()
        c.execute = AsyncMock(return_value=None)
        c.fetchrow = AsyncMock(return_value=None)
        c.fetch = AsyncMock(return_value=[])
        return c

    @pytest.fixture
    def manager(self, conn):
        pool = _make_pool(conn)
        return APIKeyManager(db_pool=pool), conn

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_api_key_returns_cogne_prefix(self, manager):
        import json as _json
        import src.security.auth as _auth_mod
        _auth_mod.json = _json  # patch missing import in source
        mgr, conn = manager
        api_key = await mgr.create_api_key("user1", "my-key")
        assert api_key.startswith("cogne_")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_api_key_calls_insert(self, manager):
        import json as _json
        import src.security.auth as _auth_mod
        _auth_mod.json = _json
        mgr, conn = manager
        await mgr.create_api_key("user1", "my-key")
        conn.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_api_key_with_scopes(self, manager):
        import json as _json
        import src.security.auth as _auth_mod
        _auth_mod.json = _json
        mgr, conn = manager
        api_key = await mgr.create_api_key("user1", "scoped", scopes=["read", "write"])
        assert isinstance(api_key, str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_api_key_not_found_returns_none(self, manager):
        mgr, conn = manager
        conn.fetchrow = AsyncMock(return_value=None)
        result = await mgr.verify_api_key("cogne_invalid")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_api_key_calls_update(self, manager):
        mgr, conn = manager
        conn.execute = AsyncMock(return_value="UPDATE 1")
        result = await mgr.revoke_api_key("key-id", "user1")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found_returns_false(self, manager):
        mgr, conn = manager
        conn.execute = AsyncMock(return_value="UPDATE 0")
        result = await mgr.revoke_api_key("nonexistent", "user1")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_user_keys_returns_list(self, manager):
        mgr, conn = manager
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.list_user_keys("user1")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# RBACManager
# ---------------------------------------------------------------------------

class TestRBACManager:
    @pytest.fixture
    def conn(self):
        c = AsyncMock()
        return c

    @pytest.fixture
    def rbac(self, conn):
        pool = _make_pool(conn)
        return RBACManager(db_pool=pool), conn

    # Synchronous methods
    @pytest.mark.unit
    def test_admin_has_memory_write(self):
        _, conn = None, None
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        assert rbac.has_permission(Role.ADMIN, Permission.MEMORY_WRITE) is True

    @pytest.mark.unit
    def test_readonly_lacks_memory_write(self):
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        assert rbac.has_permission(Role.READONLY, Permission.MEMORY_WRITE) is False

    @pytest.mark.unit
    def test_unknown_role_returns_false(self):
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        # Passing a non-Role enum value
        assert rbac.has_permission("nonexistent_role", Permission.MEMORY_READ) is False

    @pytest.mark.unit
    def test_has_any_permission_true(self):
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        result = rbac.has_any_permission(
            Role.USER,
            [Permission.MEMORY_READ, Permission.SYSTEM_ADMIN]
        )
        assert result is True  # USER has MEMORY_READ

    @pytest.mark.unit
    def test_has_any_permission_false(self):
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        result = rbac.has_any_permission(
            Role.READONLY,
            [Permission.MEMORY_WRITE, Permission.SYSTEM_ADMIN]
        )
        assert result is False

    @pytest.mark.unit
    def test_has_all_permissions_true(self):
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        result = rbac.has_all_permissions(
            Role.ADMIN,
            [Permission.MEMORY_READ, Permission.MEMORY_WRITE]
        )
        assert result is True

    @pytest.mark.unit
    def test_has_all_permissions_false(self):
        pool = _make_pool(AsyncMock())
        rbac = RBACManager(db_pool=pool)
        result = rbac.has_all_permissions(
            Role.READONLY,
            [Permission.MEMORY_READ, Permission.MEMORY_WRITE]
        )
        assert result is False

    # Async DB methods
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_permission_user_not_found_returns_false(self, rbac):
        mgr, conn = rbac
        conn.fetchrow = AsyncMock(return_value=None)
        result = await mgr.check_permission("ghost-user", Permission.MEMORY_READ)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_permission_admin_role_returns_true(self, rbac):
        mgr, conn = rbac
        conn.fetchrow = AsyncMock(return_value={"role": "admin"})
        result = await mgr.check_permission("admin-user", Permission.MEMORY_WRITE)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_permission_readonly_lacks_write(self, rbac):
        mgr, conn = rbac
        conn.fetchrow = AsyncMock(return_value={"role": "readonly"})
        result = await mgr.check_permission("ro-user", Permission.MEMORY_WRITE)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_grant_permission_granter_not_admin_returns_false(self, rbac):
        mgr, conn = rbac
        conn.fetchval = AsyncMock(return_value="user")  # granter is not admin
        conn.execute = AsyncMock(return_value=None)
        result = await mgr.grant_permission("target", Permission.MEMORY_WRITE, "non-admin-granter")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_grant_permission_admin_granter_returns_true(self, rbac):
        mgr, conn = rbac
        conn.fetchval = AsyncMock(return_value="admin")
        conn.execute = AsyncMock(return_value=None)
        result = await mgr.grant_permission("target", Permission.MEMORY_WRITE, "admin-granter")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_permission_success(self, rbac):
        mgr, conn = rbac
        conn.execute = AsyncMock(return_value="DELETE 1")
        result = await mgr.revoke_permission("user1", Permission.MEMORY_WRITE, "admin")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_permission_not_found_returns_false(self, rbac):
        mgr, conn = rbac
        conn.execute = AsyncMock(return_value="DELETE 0")
        result = await mgr.revoke_permission("user1", Permission.MEMORY_WRITE, "admin")
        assert result is False
