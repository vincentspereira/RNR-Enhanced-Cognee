"""Multi-tenant data partitioning scaffold (PR 15).

Provides the **context** + **naming helpers** that wrap every
storage-tier call site with a per-tenant scope. Full enforcement at
each adapter is a follow-up workstream tracked in
``docs/operations/MULTI_TENANT_DESIGN.md``; this module is the
foundation.

## Why a scaffold first, not a full implementation?

Multi-tenancy touches every storage layer: Postgres schemas, Qdrant
collections, ArcadeDB graph databases, Valkey key prefixes,
LanceDB tables, etc. A full implementation would be a multi-PR
workstream. PR 15 ships the **central choke point** (this module)
+ the helpers; subsequent PRs wire the helpers into each adapter.

## Public API

```python
from src.multi_tenant import (
    TenantContext, set_tenant, get_tenant,
    tenant_scoped_table, tenant_scoped_collection, tenant_scoped_key,
    require_tenant,
)

# At request entry (e.g. MCP tool handler):
with TenantContext("acme-corp"):
    # All storage calls inside this block see tenant="acme-corp"
    await add_memory(content="...", agent_id="ats-1")

# Or imperatively:
set_tenant("acme-corp")
try:
    ...
finally:
    set_tenant(None)
```

## Naming convention

- Postgres tables: ``<base>_t_<tenant_id>`` (e.g. ``documents_t_acme_corp``)
- Qdrant collections: ``<base>__t__<tenant_id>``
- ArcadeDB / Neo4j: graph name ``<base>_t_<tenant_id>``
- Valkey / Redis keys: ``t:<tenant_id>:<base_key>``

All four use a sanitised tenant id (alphanumeric + underscore;
non-conforming chars become underscores) so the result is safe to
embed in unquoted SQL identifiers and Qdrant collection names.

## Defaults + safety

- ``get_tenant()`` returns ``None`` when no tenant has been set.
- ``tenant_scoped_*`` helpers fall back to the un-scoped name when
  the tenant is ``None`` -- this preserves backwards compatibility
  with the single-tenant codebase.
- ``require_tenant()`` raises ``MissingTenantError`` -- use it in
  code paths that must NEVER run unscoped (e.g. SaaS deployments
  where cross-tenant reads would be a breach).

## Env var: ``ENHANCED_REQUIRE_TENANT``

When set to ``1``, ``tenant_scoped_*`` helpers raise
``MissingTenantError`` if no tenant is set. Use this in production
SaaS deployments to fail loud on any code path that forgot to set
the tenant context.
"""

from __future__ import annotations

import contextvars
import os
import re
from typing import Any, Optional

_TENANT_CTX: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "enhanced_cognee_tenant", default=None
)

_SAFE_RE = re.compile(r"[^a-zA-Z0-9_]")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MissingTenantError(RuntimeError):
    """Raised when a code path requires a tenant but none is set."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sanitise_tenant_id(tenant_id: str) -> str:
    """Return a SQL/Qdrant-safe form of the tenant id.

    Non-alphanumeric chars become underscores; leading digits are
    prefixed with `t` so the result is a valid identifier.
    """
    if not tenant_id:
        return ""
    safe = _SAFE_RE.sub("_", tenant_id)
    if safe and safe[0].isdigit():
        safe = "t" + safe
    return safe


def set_tenant(tenant_id: Optional[str]) -> contextvars.Token[Optional[str]]:
    """Set the active tenant for the current context.

    Returns a Token that can be passed back to ``set_tenant`` to
    restore the previous value -- but the ``TenantContext`` context
    manager below is the recommended API.
    """
    safe = sanitise_tenant_id(tenant_id) if tenant_id else None
    return _TENANT_CTX.set(safe)


def get_tenant() -> Optional[str]:
    """Return the active tenant id, or None if none is set."""
    return _TENANT_CTX.get()


def reset_tenant(token: contextvars.Token[Optional[str]]) -> None:
    """Restore the tenant context to its prior value (companion to set_tenant)."""
    _TENANT_CTX.reset(token)


def require_tenant() -> str:
    """Return the active tenant id; raise ``MissingTenantError`` if none."""
    t = _TENANT_CTX.get()
    if t is None:
        raise MissingTenantError(
            "No tenant set in context. Wrap the call in `with TenantContext(...):` "
            "or call `set_tenant(...)` first."
        )
    return t


class TenantContext:
    """Context manager that sets the tenant for its lifetime.

    Usage:
        with TenantContext("acme-corp"):
            ...  # storage calls scoped to acme-corp

    Nested contexts shadow outer ones; on exit the previous tenant
    is restored (or None if there was no outer).
    """

    __slots__ = ("_tenant", "_token")

    def __init__(self, tenant_id: str) -> None:
        if not tenant_id:
            raise ValueError("TenantContext requires a non-empty tenant_id")
        self._tenant = tenant_id
        self._token: Optional[contextvars.Token[Optional[str]]] = None

    def __enter__(self) -> "TenantContext":
        self._token = set_tenant(self._tenant)
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc: Optional[BaseException],
        tb: Optional[Any],
    ) -> None:
        if self._token is not None:
            reset_tenant(self._token)
            self._token = None

    async def __aenter__(self) -> "TenantContext":
        self._token = set_tenant(self._tenant)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc: Optional[BaseException],
        tb: Optional[Any],
    ) -> None:
        if self._token is not None:
            reset_tenant(self._token)
            self._token = None


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


def tenant_required() -> bool:
    """Whether a tenant context is mandatory for storage-tier calls.

    Resolution order:
      1. Explicit ``ENHANCED_REQUIRE_TENANT`` (1/true/yes/on -> required;
         anything else -> not required) always wins.
      2. Otherwise, required by default in production (``ENHANCED_ENV`` in
         {production, prod}) and optional elsewhere.

    This gives "multi-tenant enforced by default" semantics for production
    SaaS deployments while keeping local / single-tenant dev frictionless.
    Operators running a genuinely single-tenant production install can opt
    out with ``ENHANCED_REQUIRE_TENANT=0``.
    """
    raw = os.getenv("ENHANCED_REQUIRE_TENANT")
    if raw is not None:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return os.getenv("ENHANCED_ENV", "").strip().lower() in ("production", "prod")


def _maybe_require_tenant() -> Optional[str]:
    t = _TENANT_CTX.get()
    if t is None and tenant_required():
        raise MissingTenantError(
            "A tenant context is required (ENHANCED_REQUIRE_TENANT or "
            "production default) but none is active. Wrap every storage call "
            "in `with TenantContext(...):` or send an X-Tenant-ID header."
        )
    return t


def tenant_scoped_table(base_table: str) -> str:
    """Return the tenant-scoped form of a Postgres table identifier.

    Accepts both bare names and schema-qualified names:

        "documents"               -> "documents_t_<tenant>"
        "shared_memory.documents" -> "shared_memory.documents_t_<tenant>"

    Both forms preserve the schema qualifier so SQL like
    ``INSERT INTO shared_memory.documents_t_acme ...`` is valid.
    """
    t = _maybe_require_tenant()
    if t is None:
        return base_table
    if "." in base_table:
        schema, table = base_table.rsplit(".", 1)
        return f"{schema}.{table}_t_{t}"
    return f"{base_table}_t_{t}"


async def ensure_tenant_schema(pool: Any, tenant_id: Optional[str] = None) -> None:
    """Create the per-tenant Postgres tables on first use.

    Idempotent: uses ``CREATE TABLE IF NOT EXISTS``. Mirrors the
    columns from the canonical ``shared_memory.documents`` /
    ``shared_memory.embeddings`` schema in
    ``docker/init-scripts/01-init-pgvector.sql``. Call this once at
    MCP server startup (per tenant) or lazily on first write.

    Pass an explicit ``tenant_id`` to bootstrap a specific tenant
    out-of-band; otherwise reads the current TenantContext.
    """
    t = tenant_id or _TENANT_CTX.get()
    if t is None:
        return  # single-tenant mode -- nothing to create
    safe_t = sanitise_tenant_id(t)

    async with pool.acquire() as conn:
        await conn.execute(
            f'CREATE TABLE IF NOT EXISTS shared_memory.documents_t_{safe_t} '
            f'(LIKE shared_memory.documents INCLUDING ALL)'
        )
        await conn.execute(
            f'CREATE TABLE IF NOT EXISTS shared_memory.embeddings_t_{safe_t} '
            f'(LIKE shared_memory.embeddings INCLUDING ALL)'
        )


def tenant_scoped_collection(base_collection: str) -> str:
    """Return ``<base>__t__<tenant>`` (or ``<base>`` if no tenant).

    Qdrant / LanceDB / Chroma / Weaviate / Milvus collection name.
    Double-underscore separator avoids collisions with valid
    single-underscore segments in user-supplied collection names.
    """
    t = _maybe_require_tenant()
    if t is None:
        return base_collection
    return f"{base_collection}__t__{t}"


def tenant_scoped_key(base_key: str) -> str:
    """Return ``t:<tenant>:<base>`` (or ``<base>`` if no tenant).

    Valkey / Redis cache key. Colon-separator matches the standard
    Redis namespace convention.
    """
    t = _maybe_require_tenant()
    if t is None:
        return base_key
    return f"t:{t}:{base_key}"


def tenant_scoped_graph(base_graph: str) -> str:
    """Return ``<base>_t_<tenant>`` (or ``<base>`` if no tenant).

    Graph database name (ArcadeDB / Neo4j / AGE).
    """
    t = _maybe_require_tenant()
    if t is None:
        return base_graph
    return f"{base_graph}_t_{t}"
