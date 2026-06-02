"""Enterprise authentication + authorization for Enhanced Cognee.

This module is the single source of truth for *who is calling* (authentication)
and *what they may do* (authorization) across both server surfaces:

  - the HTTP FastAPI server (``src/enhanced_cognee_mcp.py``) -- per-route RBAC,
    bearer (OIDC/JWT) + API-key authentication, enforced via middleware.
  - the stdio MCP server (``bin/enhanced_cognee_mcp_server.py``) -- per-tool RBAC
    via a single ``mcp.tool()`` wrapper.

It builds on the existing primitives in ``src/security/auth.py`` (``Role``,
``Permission``, ``ROLE_PERMISSIONS``, ``JWTAuthenticator``) and adds:

  * ``Principal``            -- the authenticated caller (subject/role/perms/tenant).
  * ``verify_bearer_token``  -- OIDC (JWKS / RS256) with HS256 fallback.
  * ``authenticate_request`` -- resolve a Principal from request headers.
  * route + tool -> permission maps, and ``authorize`` to enforce them.

Design principle -- **fail-open in dev, fail-closed in prod** (consistent with
``src/mcp_security.enforce_production_auth``):

  * When NO authentication is configured and ``ENHANCED_ENV`` is not production,
    callers are treated as a local admin so single-user / local Claude Code use
    stays frictionless.
  * When authentication IS configured (API key, JWT secret, or OIDC issuer),
    every non-public request must present valid credentials or it is rejected.
  * In production, the server refuses to start without auth configured
    (``enforce_production_auth``), so a Principal is always required.

ASCII-only output (Windows cp1252 safe).

Env knobs
---------
Authentication:
  ENHANCED_API_KEY              Static operator key (maps to an admin Principal).
  ENHANCED_JWT_SECRET           HS256 shared secret for symmetric bearer tokens.
  ENHANCED_JWT_ALGORITHMS       Comma list for the HS path (default "HS256").
  ENHANCED_OIDC_ISSUER          OIDC issuer URL (enables discovery + iss check).
  ENHANCED_OIDC_JWKS_URI        Explicit JWKS URL (skips discovery).
  ENHANCED_OIDC_AUDIENCE        Expected "aud" claim (verified when set).
  ENHANCED_OIDC_ALGORITHMS      Comma list for the OIDC path (default "RS256").

Claim mapping:
  ENHANCED_OIDC_ROLE_CLAIM      Claim holding role(s) (default "roles").
  ENHANCED_OIDC_TENANT_CLAIM    Claim holding the tenant id (default "tenant").
  ENHANCED_OIDC_DEFAULT_ROLE    Role for an authenticated caller with no
                                recognised role (default "readonly").

stdio RBAC:
  ENHANCED_MCP_ROLE             Role assumed by the local stdio caller
                                (default "admin"; set to "readonly" etc. to lock
                                a deployment down).
  ENHANCED_MCP_ENFORCE_RBAC     Force per-tool RBAC enforcement even for admin.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple, cast

import jwt

from src.security.auth import Permission, Role, ROLE_PERMISSIONS

logger = logging.getLogger(__name__)

# Public paths that never require authentication or authorization (probes +
# metrics scraping). Kept here so both the middleware and tests agree.
PUBLIC_PATHS = frozenset(
    {"/health", "/health/live", "/health/ready", "/metrics"}
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Authentication / authorization failure carrying an HTTP status code.

    ``status_code`` is 401 (unauthenticated) or 403 (authenticated but lacking
    the required permission). ``detail`` is an ASCII-safe message.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Principal:
    """An authenticated caller.

    ``permissions`` is the effective permission set (derived from ``role`` via
    ``ROLE_PERMISSIONS``). ``auth_method`` records how the caller was
    authenticated ("oidc" / "jwt" / "api-key" / "dev-open" / "stdio").
    """

    subject: str
    role: Role
    permissions: FrozenSet[Permission] = field(default_factory=frozenset)
    tenant_id: Optional[str] = None
    auth_method: str = "none"
    claims: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions


def _permissions_for_role(role: Role) -> FrozenSet[Permission]:
    return frozenset(ROLE_PERMISSIONS.get(role, []))


def admin_principal(subject: str, auth_method: str) -> Principal:
    return Principal(
        subject=subject,
        role=Role.ADMIN,
        permissions=_permissions_for_role(Role.ADMIN),
        auth_method=auth_method,
    )


def dev_principal() -> Principal:
    """Implicit local admin used when no auth is configured (dev only)."""
    return Principal(
        subject="dev-local",
        role=Role.ADMIN,
        permissions=_permissions_for_role(Role.ADMIN),
        auth_method="dev-open",
    )


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def _is_production() -> bool:
    return os.getenv("ENHANCED_ENV", "").strip().lower() in ("production", "prod")


def _env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def api_key_configured() -> bool:
    return bool(os.getenv("ENHANCED_API_KEY"))


def jwt_secret_configured() -> bool:
    return bool(os.getenv("ENHANCED_JWT_SECRET"))


def oidc_configured() -> bool:
    return bool(
        os.getenv("ENHANCED_OIDC_ISSUER") or os.getenv("ENHANCED_OIDC_JWKS_URI")
    )


def auth_configured() -> bool:
    """True if any authentication method is configured."""
    return (
        api_key_configured()
        or jwt_secret_configured()
        or oidc_configured()
    )


# ---------------------------------------------------------------------------
# OIDC / JWT verification
# ---------------------------------------------------------------------------

# Cache PyJWKClient instances per JWKS URI (each caches signing keys itself).
_JWKS_CLIENTS: Dict[str, Any] = {}
# Cache discovered jwks_uri per issuer so we hit the discovery doc only once.
_DISCOVERY_CACHE: Dict[str, str] = {}


def _jwks_client(jwks_uri: str) -> Any:
    client = _JWKS_CLIENTS.get(jwks_uri)
    if client is None:
        # PyJWKClient (PyJWT >= 2.x) fetches + caches the JWK set.
        client = jwt.PyJWKClient(jwks_uri)
        _JWKS_CLIENTS[jwks_uri] = client
    return client


def _discover_jwks_uri(issuer: str) -> Optional[str]:
    """Resolve the JWKS URI from an issuer's OIDC discovery document.

    Reads ``<issuer>/.well-known/openid-configuration`` once (then caches the
    result). Returns None if discovery fails -- the caller falls back to the
    HS256 path or rejects the token.
    """
    if issuer in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[issuer]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # nosec B310 (https issuer)
            doc = json.loads(resp.read().decode("utf-8"))
        jwks_uri = doc.get("jwks_uri")
        if jwks_uri:
            _DISCOVERY_CACHE[issuer] = jwks_uri
            return cast(str, jwks_uri)
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("OIDC discovery failed for issuer %s: %s", issuer, exc)
    return None


def verify_bearer_token(token: str) -> Dict[str, Any]:
    """Verify a bearer JWT and return its claims.

    Tries the asymmetric OIDC path first (JWKS / RS256 family), then the
    symmetric HS256 path (``ENHANCED_JWT_SECRET``). Raises ``AuthError(401)``
    on any failure or when no verifier is configured.
    """
    issuer = os.getenv("ENHANCED_OIDC_ISSUER")
    jwks_uri = os.getenv("ENHANCED_OIDC_JWKS_URI")
    if not jwks_uri and issuer:
        jwks_uri = _discover_jwks_uri(issuer)

    if jwks_uri:
        audience = os.getenv("ENHANCED_OIDC_AUDIENCE")
        algorithms = _env_list("ENHANCED_OIDC_ALGORITHMS", "RS256")
        try:
            signing_key = _jwks_client(jwks_uri).get_signing_key_from_jwt(token)
            return cast(Dict[str, Any], jwt.decode(
                token,
                signing_key.key,
                algorithms=algorithms,
                audience=audience or None,
                issuer=issuer or None,
                options={
                    "verify_aud": bool(audience),
                    "verify_iss": bool(issuer),
                },
            ))
        except AuthError:
            raise
        except Exception as exc:
            raise AuthError(401, f"OIDC token verification failed: {exc}")

    secret = os.getenv("ENHANCED_JWT_SECRET")
    if secret:
        audience = os.getenv("ENHANCED_OIDC_AUDIENCE")
        algorithms = _env_list("ENHANCED_JWT_ALGORITHMS", "HS256")
        try:
            return cast(Dict[str, Any], jwt.decode(
                token,
                secret,
                algorithms=algorithms,
                audience=audience or None,
                options={"verify_aud": bool(audience)},
            ))
        except Exception as exc:
            raise AuthError(401, f"JWT verification failed: {exc}")

    raise AuthError(
        401,
        "Bearer token presented but no JWT/OIDC verifier is configured. "
        "Set ENHANCED_OIDC_ISSUER/ENHANCED_OIDC_JWKS_URI or ENHANCED_JWT_SECRET.",
    )


# ---------------------------------------------------------------------------
# Claims -> Principal
# ---------------------------------------------------------------------------

# Synonyms for each role, so tokens minted by external IdPs map cleanly.
_ROLE_SYNONYMS = {
    Role.ADMIN: {"admin", "administrator", "superuser", "owner", "root"},
    Role.USER: {"user", "member", "editor", "write", "writer", "contributor"},
    Role.API_CLIENT: {"api", "api_client", "apiclient", "service", "service_account", "client"},
    Role.READONLY: {"readonly", "read-only", "read_only", "read", "viewer", "reader", "guest"},
}
_ROLE_RANK = {Role.ADMIN: 3, Role.USER: 2, Role.API_CLIENT: 1, Role.READONLY: 0}


def coerce_role(value: Any) -> Optional[Role]:
    """Map an arbitrary role string to a ``Role`` (None if unrecognised)."""
    if value is None:
        return None
    v = str(value).strip().lower()
    for role, names in _ROLE_SYNONYMS.items():
        if v == role.value or v in names:
            return role
    return None


def _extract_role_strings(claims: Mapping[str, Any]) -> list[str]:
    roles: list[str] = []
    claim_name = os.getenv("ENHANCED_OIDC_ROLE_CLAIM", "roles")

    def _add(val: Any) -> None:
        if isinstance(val, str):
            roles.extend(val.replace(",", " ").split())
        elif isinstance(val, (list, tuple, set)):
            roles.extend(str(v) for v in val)

    _add(claims.get(claim_name))
    # Always also consider a singular "role" claim.
    if claim_name != "role":
        _add(claims.get("role"))
    # Keycloak-style realm_access.roles / resource_access.*.roles.
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        _add(realm_access.get("roles"))
    return [r.lower() for r in roles]


def role_from_claims(claims: Mapping[str, Any]) -> Role:
    """Pick the highest-privilege recognised role from a token's claims.

    Falls back to ``ENHANCED_OIDC_DEFAULT_ROLE`` (default readonly) for an
    authenticated caller whose roles we don't recognise -- least privilege.
    """
    found = [r for r in (coerce_role(s) for s in _extract_role_strings(claims)) if r]
    if found:
        return max(found, key=lambda r: _ROLE_RANK[r])
    default = coerce_role(os.getenv("ENHANCED_OIDC_DEFAULT_ROLE", "readonly"))
    return default or Role.READONLY


def tenant_from_claims(claims: Mapping[str, Any]) -> Optional[str]:
    claim_name = os.getenv("ENHANCED_OIDC_TENANT_CLAIM", "tenant")
    value = (
        claims.get(claim_name)
        or claims.get("tenant_id")
        or claims.get("tid")
        or claims.get("org_id")
    )
    return str(value) if value else None


def principal_from_claims(claims: Mapping[str, Any], auth_method: str) -> Principal:
    role = role_from_claims(claims)
    subject = str(
        claims.get("sub")
        or claims.get("user_id")
        or claims.get("email")
        or claims.get("preferred_username")
        or "unknown"
    )
    return Principal(
        subject=subject,
        role=role,
        permissions=_permissions_for_role(role),
        tenant_id=tenant_from_claims(claims),
        auth_method=auth_method,
        claims=dict(claims),
    )


# ---------------------------------------------------------------------------
# Request authentication
# ---------------------------------------------------------------------------


def _get_header(headers: Mapping[str, str], name: str) -> Optional[str]:
    """Case-insensitive header lookup that works for dicts and Starlette Headers."""
    getter = getattr(headers, "get", None)
    if getter is not None:
        # Starlette Headers.get is already case-insensitive.
        val = headers.get(name)
        if val is not None:
            return val
        val = headers.get(name.title())
        if val is not None:
            return val
    # Last resort: linear scan for plain dicts with arbitrary casing.
    try:
        for key, value in headers.items():
            if key.lower() == name.lower():
                return value
    except Exception:
        pass
    return None


def authenticate_request(headers: Mapping[str, str]) -> Principal:
    """Resolve a ``Principal`` from request headers.

    Order: Bearer token (OIDC/JWT) -> X-API-Key -> dev-open fallback.
    Raises ``AuthError`` (401) when authentication is required but missing or
    invalid.
    """
    authz = _get_header(headers, "authorization")
    if authz and authz.lower().startswith("bearer "):
        token = authz[7:].strip()
        method = "oidc" if oidc_configured() else "jwt"
        return principal_from_claims(verify_bearer_token(token), method)

    api_key = _get_header(headers, "x-api-key")
    expected = os.getenv("ENHANCED_API_KEY")
    if expected:
        if api_key and secrets.compare_digest(str(api_key), str(expected)):
            return admin_principal("api-key", "api-key")
        if api_key:
            raise AuthError(401, "Invalid API key")
        # No API key provided -- fall through to the "missing credentials" check.

    if auth_configured():
        raise AuthError(
            401,
            "Authentication required: present a Bearer token or X-API-Key.",
        )

    # Nothing configured. Fail-closed in production (defense in depth; startup
    # should already have been blocked by enforce_production_auth).
    if _is_production():
        raise AuthError(
            401,
            "Authentication required (production) but no auth method is configured.",
        )
    return dev_principal()


# ---------------------------------------------------------------------------
# Authorization -- route + tool permission maps
# ---------------------------------------------------------------------------

# Exact (METHOD, path) -> required permission for the HTTP surface.
_ROUTE_PERMISSIONS: Dict[Tuple[str, str], Permission] = {
    ("POST", "/memory/add"): Permission.MEMORY_WRITE,
    ("POST", "/memory/search"): Permission.MEMORY_READ,
    ("POST", "/knowledge/add_relation"): Permission.MEMORY_WRITE,
    ("POST", "/mcp/add_memory"): Permission.MEMORY_WRITE,
    ("POST", "/mcp/search_memories"): Permission.MEMORY_READ,
    ("POST", "/mcp/get_memories"): Permission.MEMORY_READ,
    ("POST", "/mcp/update_memory"): Permission.MEMORY_WRITE,
    ("POST", "/mcp/delete_memory"): Permission.MEMORY_DELETE,
    ("GET", "/mcp/list_agents"): Permission.MEMORY_READ,
    ("GET", "/stats"): Permission.SYSTEM_MONITOR,
}


def route_required_permission(method: str, path: str) -> Optional[Permission]:
    """Permission required for an HTTP route (None = authenticated access only).

    Public probe/metrics paths return None. Known routes use the explicit map.
    Unknown routes fall back to a conservative heuristic (delete verbs require
    MEMORY_DELETE) but otherwise require no specific permission so custom routes
    are not silently broken -- authentication still applies to them.
    """
    if path in PUBLIC_PATHS:
        return None
    exact = _ROUTE_PERMISSIONS.get((method.upper(), path))
    if exact is not None:
        return exact
    lowered = path.lower()
    if method.upper() == "DELETE" or "delete" in lowered:
        return Permission.MEMORY_DELETE
    return None


# MCP tool name -> required permission for the stdio surface. Tools not listed
# require no specific permission (read-ish / introspection tools).
TOOL_PERMISSIONS: Dict[str, Permission] = {
    # Writes
    "add_memory": Permission.MEMORY_WRITE,
    "update_memory": Permission.MEMORY_WRITE,
    "add_observation": Permission.MEMORY_WRITE,
    "update_observation": Permission.MEMORY_WRITE,
    "save_interaction": Permission.MEMORY_WRITE,
    "cognify": Permission.MEMORY_WRITE,
    "ingest_url": Permission.MEMORY_WRITE,
    "ingest_db": Permission.MEMORY_WRITE,
    "consolidate_memories": Permission.MEMORY_WRITE,
    "promote_memory_tier": Permission.MEMORY_WRITE,
    "set_memory_confidence": Permission.MEMORY_WRITE,
    "set_memory_ttl": Permission.MEMORY_WRITE,
    "set_memory_sharing": Permission.MEMORY_WRITE,
    "encrypt_memory": Permission.MEMORY_WRITE,
    # Deletes / destructive
    "delete_memory": Permission.MEMORY_DELETE,
    "delete_observation": Permission.MEMORY_DELETE,
    "forget_memory": Permission.MEMORY_DELETE,
    "archive_category": Permission.MEMORY_DELETE,
    "expire_memories": Permission.MEMORY_DELETE,
    "deduplicate": Permission.MEMORY_DELETE,
    "auto_deduplicate": Permission.MEMORY_DELETE,
    "compact_knowledge_graph": Permission.MEMORY_DELETE,
    # System / admin
    "create_backup": Permission.SYSTEM_ADMIN,
    "restore_backup": Permission.SYSTEM_ADMIN,
    "rollback_restore": Permission.SYSTEM_ADMIN,
    "verify_backup": Permission.SYSTEM_MONITOR,
    "rotate_encryption_key": Permission.SYSTEM_ADMIN,
    "gdpr_delete_user_data": Permission.SYSTEM_ADMIN,
    "set_cost_budget": Permission.SYSTEM_CONFIG,
    "configure_slack_notifications": Permission.SYSTEM_CONFIG,
    "configure_discord_notifications": Permission.SYSTEM_CONFIG,
    "register_webhook": Permission.SYSTEM_CONFIG,
    "disable_webhook": Permission.SYSTEM_CONFIG,
}


def tool_required_permission(tool_name: str) -> Optional[Permission]:
    return TOOL_PERMISSIONS.get(tool_name)


def authorize(principal: Optional[Principal], permission: Optional[Permission]) -> None:
    """Raise ``AuthError(403)`` if ``principal`` lacks ``permission``.

    A None permission is a no-op (route/tool requires only authentication).
    """
    if permission is None:
        return
    if principal is None or not principal.has_permission(permission):
        role = getattr(getattr(principal, "role", None), "value", "anonymous")
        needed = getattr(permission, "value", str(permission))
        raise AuthError(
            403,
            f"Permission denied: '{needed}' is required "
            f"(caller role '{role}' lacks it).",
        )


# ---------------------------------------------------------------------------
# stdio (local) principal + RBAC enforcement decision
# ---------------------------------------------------------------------------


def local_principal() -> Principal:
    """Principal for the local stdio MCP caller.

    Role comes from ``ENHANCED_MCP_ROLE`` (default admin). This lets an operator
    lock a deployment down (e.g. ENHANCED_MCP_ROLE=readonly) without code edits.
    """
    role = coerce_role(os.getenv("ENHANCED_MCP_ROLE", "admin")) or Role.ADMIN
    return Principal(
        subject="mcp-stdio",
        role=role,
        permissions=_permissions_for_role(role),
        auth_method="stdio",
    )


def stdio_rbac_enforced() -> bool:
    """Whether per-tool RBAC should be enforced on the stdio surface.

    Enforced when the operator pins a non-admin role OR explicitly opts in via
    ``ENHANCED_MCP_ENFORCE_RBAC``. Default-admin local use is unaffected.
    """
    if os.getenv("ENHANCED_MCP_ENFORCE_RBAC", "").strip().lower() in (
        "1", "true", "yes", "on",
    ):
        return True
    role = coerce_role(os.getenv("ENHANCED_MCP_ROLE", "admin"))
    return role is not None and role != Role.ADMIN


# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------


def log_enterprise_auth_status() -> None:
    """Emit one INFO line summarising the enterprise auth configuration."""
    if oidc_configured():
        method = "oidc"
    elif jwt_secret_configured():
        method = "jwt-hs256"
    elif api_key_configured():
        method = "api-key"
    else:
        method = "none(dev-open)" if not _is_production() else "none(PROD-INSECURE)"
    logger.info(
        "Enterprise auth: method=%s rbac=on tenant_default_required=%s",
        method,
        _is_production(),
    )
