"""Tenant-isolation end-to-end tests.

These tests verify that the multi-tenant wiring shipped in PR 15
actually isolates tenants from each other -- i.e. tenant A cannot
read tenant B's data, and writes go to the right per-tenant table.

The Postgres pool is mocked so no live database is required; the
assertions inspect captured SQL strings to confirm the right
table name was used per-tenant.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.multi_tenant import (
    MissingTenantError,
    TenantContext,
    ensure_tenant_schema,
    get_tenant,
    set_tenant,
    tenant_scoped_collection,
    tenant_scoped_graph,
    tenant_scoped_key,
    tenant_scoped_table,
)


# ---------------------------------------------------------------------------
# Pool fixtures
# ---------------------------------------------------------------------------


class _CapturingConn:
    """Async-mock Postgres connection that records every SQL string executed."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, tuple]] = []

    async def execute(self, sql: str, *args):
        self.calls.append(("execute", sql, args))
        return "OK rows=1"

    async def fetchrow(self, sql: str, *args):
        self.calls.append(("fetchrow", sql, args))
        return {"id": "row-1", "agent_id": "a", "category": "x"}

    async def fetch(self, sql: str, *args):
        self.calls.append(("fetch", sql, args))
        return []

    async def fetchval(self, sql: str, *args):
        self.calls.append(("fetchval", sql, args))
        return 0


class _AcquireCM:
    def __init__(self, conn: _CapturingConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _CapturingConn:
        return self._conn

    async def __aexit__(self, *a) -> None:
        return None


def _make_pool() -> tuple[MagicMock, _CapturingConn]:
    conn = _CapturingConn()
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AcquireCM(conn))
    return pool, conn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrossTenantTableIsolation:
    """Tenant A's writes hit documents_t_a; tenant B's hit documents_t_b."""

    @pytest.mark.asyncio
    async def test_two_tenants_write_to_separate_tables(self):
        from src import mcp_memory_tools

        pool, conn = _make_pool()

        with patch("src.security_mcp.validate_memory_content", side_effect=lambda x: x), \
             patch("src.security_mcp.validate_agent_id", side_effect=lambda x: x), \
             patch("src.security_mcp.sanitize_string", side_effect=lambda x, max_length=None: x):

            await mcp_memory_tools.add_memory(
                content="data from tenant A",
                agent_id="agent-1",
                user_id="u",
                tenant_id="acme",
                postgres_pool=pool,
            )
            await mcp_memory_tools.add_memory(
                content="data from tenant B",
                agent_id="agent-2",
                user_id="u",
                tenant_id="globex",
                postgres_pool=pool,
            )

        # Capture all SQL
        sqls = [c[1] for c in conn.calls]
        joined = "\n".join(sqls)

        # Tenant A writes appear in tenant A's table
        a_inserts = [s for s in sqls if "INSERT" in s and "documents_t_acme" in s]
        b_inserts = [s for s in sqls if "INSERT" in s and "documents_t_globex" in s]

        assert len(a_inserts) == 1, f"Expected one tenant-A insert, got {a_inserts}"
        assert len(b_inserts) == 1, f"Expected one tenant-B insert, got {b_inserts}"

        # And neither tenant's insert hit the un-scoped table
        assert not any(
            "INSERT INTO shared_memory.documents " in s
            or s.endswith("INSERT INTO shared_memory.documents")
            for s in sqls
        ), "Tenant-scoped writes leaked into the un-scoped table"

    @pytest.mark.asyncio
    async def test_search_routes_to_tenant_specific_table(self):
        from src import mcp_memory_tools

        pool, conn = _make_pool()

        with patch("src.security_mcp.validate_agent_id", side_effect=lambda x: x), \
             patch("src.security_mcp.sanitize_string", side_effect=lambda x, max_length=None: x), \
             patch("src.security_mcp.validate_limit", side_effect=lambda x, *_a: x):

            await mcp_memory_tools.search_memories(
                query="X",
                tenant_id="acme",
                postgres_pool=pool,
            )
            await mcp_memory_tools.search_memories(
                query="X",
                tenant_id="globex",
                postgres_pool=pool,
            )

        sqls = [c[1] for c in conn.calls]
        # Each tenant's SELECT must hit its own table; no cross-pollination
        acme_selects = [s for s in sqls if "documents_t_acme" in s]
        globex_selects = [s for s in sqls if "documents_t_globex" in s]
        assert len(acme_selects) >= 1
        assert len(globex_selects) >= 1


class TestTenantContextLeakage:
    """A context exit must restore the prior tenant exactly -- no leakage."""

    def test_context_does_not_leak(self):
        assert get_tenant() is None
        with TenantContext("acme"):
            assert get_tenant() == "acme"
        assert get_tenant() is None

    def test_nested_contexts_unwind_correctly(self):
        with TenantContext("outer"):
            assert get_tenant() == "outer"
            with TenantContext("inner"):
                assert get_tenant() == "inner"
                with TenantContext("innermost"):
                    assert get_tenant() == "innermost"
                assert get_tenant() == "inner"
            assert get_tenant() == "outer"
        assert get_tenant() is None

    @pytest.mark.asyncio
    async def test_async_tasks_do_not_share_tenant(self):
        results: dict[str, str | None] = {}

        async def task(name: str, tenant: str | None) -> None:
            if tenant is None:
                results[name] = get_tenant()
                return
            async with TenantContext(tenant):
                await asyncio.sleep(0.01)
                results[name] = get_tenant()

        # Three concurrent tasks each with their own tenant
        await asyncio.gather(
            task("a", "tenant_a"),
            task("b", "tenant_b"),
            task("c", "tenant_c"),
            task("none", None),
        )

        assert results == {
            "a": "tenant_a",
            "b": "tenant_b",
            "c": "tenant_c",
            "none": None,
        }


class TestEnforceTenantEndToEnd:
    """ENHANCED_REQUIRE_TENANT=1 must block all un-scoped storage helpers."""

    def test_all_helpers_raise_when_unset(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
        for helper in (
            tenant_scoped_table,
            tenant_scoped_collection,
            tenant_scoped_key,
            tenant_scoped_graph,
        ):
            with pytest.raises(MissingTenantError):
                helper("anything")

    def test_all_helpers_pass_when_set(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
        with TenantContext("acme"):
            # All four must succeed without raising
            tenant_scoped_table("documents")
            tenant_scoped_collection("ats")
            tenant_scoped_key("session:1")
            tenant_scoped_graph("cognee")


class TestEnsureTenantSchemaIsolation:
    """The lazy bootstrap creates the right per-tenant tables."""

    @pytest.mark.asyncio
    async def test_bootstrap_creates_tenant_a_tables_only(self):
        pool, conn = _make_pool()
        await ensure_tenant_schema(pool, tenant_id="acme")

        sqls = [c[1] for c in conn.calls]
        assert any("documents_t_acme" in s for s in sqls)
        assert any("embeddings_t_acme" in s for s in sqls)
        # No other tenant's tables touched
        assert not any("documents_t_globex" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_bootstrap_is_idempotent(self):
        pool, conn = _make_pool()
        # Call twice; both should issue CREATE TABLE IF NOT EXISTS
        await ensure_tenant_schema(pool, tenant_id="acme")
        await ensure_tenant_schema(pool, tenant_id="acme")
        sqls = [c[1] for c in conn.calls]
        # Idempotent guard present in every CREATE
        creates = [s for s in sqls if "CREATE TABLE" in s]
        assert len(creates) == 4  # 2 calls × 2 tables
        for s in creates:
            assert "CREATE TABLE IF NOT EXISTS" in s

    @pytest.mark.asyncio
    async def test_bootstrap_does_nothing_when_no_tenant(self):
        pool, conn = _make_pool()
        await ensure_tenant_schema(pool, tenant_id=None)
        assert conn.calls == []


class TestTenantSanitisation:
    """SQL-unsafe characters in tenant IDs are coerced to underscores."""

    def test_dash_replaced_with_underscore(self):
        with TenantContext("acme-corp"):
            assert tenant_scoped_table("docs") == "docs_t_acme_corp"

    def test_dot_replaced_with_underscore(self):
        with TenantContext("acme.io"):
            assert tenant_scoped_table("docs") == "docs_t_acme_io"

    def test_slash_replaced_with_underscore(self):
        with TenantContext("acme/eu-west"):
            assert tenant_scoped_table("docs") == "docs_t_acme_eu_west"

    def test_leading_digit_prefixed(self):
        with TenantContext("123corp"):
            assert tenant_scoped_table("docs") == "docs_t_t123corp"


class TestUnscopedBackwardsCompat:
    """When no tenant is set, every helper returns the un-scoped name."""

    def test_all_helpers_pass_through_unscoped(self):
        assert get_tenant() is None
        assert tenant_scoped_table("documents") == "documents"
        assert tenant_scoped_table("shared_memory.documents") == "shared_memory.documents"
        assert tenant_scoped_collection("ats") == "ats"
        assert tenant_scoped_key("session:1") == "session:1"
        assert tenant_scoped_graph("cognee_graph") == "cognee_graph"
