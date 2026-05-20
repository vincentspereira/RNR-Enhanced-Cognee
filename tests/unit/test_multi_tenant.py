"""Tests for the multi-tenant scaffold (PR 15)."""

from __future__ import annotations

import asyncio

import pytest

from src.multi_tenant import (
    MissingTenantError,
    TenantContext,
    get_tenant,
    require_tenant,
    sanitise_tenant_id,
    set_tenant,
    tenant_scoped_collection,
    tenant_scoped_graph,
    tenant_scoped_key,
    tenant_scoped_table,
    reset_tenant,
)


# ---------------------------------------------------------------------------
# Sanitisation
# ---------------------------------------------------------------------------


class TestSanitise:
    def test_pass_through_safe_id(self):
        assert sanitise_tenant_id("acme_corp_2026") == "acme_corp_2026"

    def test_non_alphanumeric_replaced(self):
        assert sanitise_tenant_id("acme-corp.io") == "acme_corp_io"
        assert sanitise_tenant_id("acme corp/eu") == "acme_corp_eu"

    def test_leading_digit_prefixed(self):
        assert sanitise_tenant_id("123corp") == "t123corp"

    def test_empty_returns_empty(self):
        assert sanitise_tenant_id("") == ""


# ---------------------------------------------------------------------------
# Context manager + getters
# ---------------------------------------------------------------------------


class TestTenantContext:
    def test_default_no_tenant(self):
        # Each test gets a fresh contextvar copy thanks to pytest's
        # per-test isolation -- but be defensive.
        assert get_tenant() is None

    def test_context_manager_sets_and_unsets(self):
        with TenantContext("acme"):
            assert get_tenant() == "acme"
        assert get_tenant() is None

    def test_nested_contexts_shadow(self):
        with TenantContext("outer"):
            assert get_tenant() == "outer"
            with TenantContext("inner"):
                assert get_tenant() == "inner"
            assert get_tenant() == "outer"
        assert get_tenant() is None

    def test_empty_tenant_id_raises(self):
        with pytest.raises(ValueError):
            TenantContext("")

    def test_imperative_set_reset(self):
        token = set_tenant("imp1")
        try:
            assert get_tenant() == "imp1"
        finally:
            reset_tenant(token)
        assert get_tenant() is None

    def test_context_manager_sanitises_id(self):
        with TenantContext("acme-corp.io"):
            assert get_tenant() == "acme_corp_io"

    def test_require_tenant_raises_when_unset(self):
        assert get_tenant() is None
        with pytest.raises(MissingTenantError):
            require_tenant()

    def test_require_tenant_returns_tenant(self):
        with TenantContext("acme"):
            assert require_tenant() == "acme"


# ---------------------------------------------------------------------------
# Async context manager
# ---------------------------------------------------------------------------


class TestAsyncTenantContext:
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        assert get_tenant() is None
        async with TenantContext("acme"):
            assert get_tenant() == "acme"
        assert get_tenant() is None

    @pytest.mark.asyncio
    async def test_tenant_isolated_across_tasks(self):
        # Each task should have its own copy of the contextvar.
        async def inner_task(tenant_id: str) -> str:
            async with TenantContext(tenant_id):
                await asyncio.sleep(0.01)
                return get_tenant() or ""

        results = await asyncio.gather(
            inner_task("a"), inner_task("b"), inner_task("c")
        )
        assert sorted(results) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


class TestNamingHelpers:
    def test_table_unscoped_when_no_tenant(self):
        assert tenant_scoped_table("documents") == "documents"

    def test_table_scoped(self):
        with TenantContext("acme"):
            assert tenant_scoped_table("documents") == "documents_t_acme"

    def test_collection_unscoped_when_no_tenant(self):
        assert tenant_scoped_collection("ats") == "ats"

    def test_collection_scoped(self):
        with TenantContext("acme"):
            assert tenant_scoped_collection("ats") == "ats__t__acme"

    def test_key_unscoped_when_no_tenant(self):
        assert tenant_scoped_key("agent:1:sess") == "agent:1:sess"

    def test_key_scoped(self):
        with TenantContext("acme"):
            assert tenant_scoped_key("agent:1:sess") == "t:acme:agent:1:sess"

    def test_graph_unscoped_when_no_tenant(self):
        assert tenant_scoped_graph("cognee_graph") == "cognee_graph"

    def test_graph_scoped(self):
        with TenantContext("acme"):
            assert tenant_scoped_graph("cognee_graph") == "cognee_graph_t_acme"


# ---------------------------------------------------------------------------
# Dotted table names + ensure_tenant_schema + MCP-tool wiring
# ---------------------------------------------------------------------------


class TestDottedTableScoping:
    """tenant_scoped_table handles `schema.table` correctly."""

    def test_dotted_name_preserves_schema(self):
        from src.multi_tenant import tenant_scoped_table
        with TenantContext("acme"):
            assert tenant_scoped_table("shared_memory.documents") == \
                "shared_memory.documents_t_acme"

    def test_dotted_name_unscoped_when_no_tenant(self):
        from src.multi_tenant import tenant_scoped_table
        assert tenant_scoped_table("shared_memory.documents") == \
            "shared_memory.documents"

    def test_bare_name_still_works(self):
        from src.multi_tenant import tenant_scoped_table
        with TenantContext("acme"):
            assert tenant_scoped_table("documents") == "documents_t_acme"


class TestEnsureTenantSchema:
    """`ensure_tenant_schema` issues idempotent CREATE TABLE via the pool."""

    @pytest.mark.asyncio
    async def test_no_op_when_no_tenant(self):
        from unittest.mock import MagicMock
        from src.multi_tenant import ensure_tenant_schema

        pool = MagicMock()
        await ensure_tenant_schema(pool, tenant_id=None)
        pool.acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_issues_two_create_table_statements(self):
        from unittest.mock import AsyncMock, MagicMock
        from src.multi_tenant import ensure_tenant_schema

        fake_conn = MagicMock()
        fake_conn.execute = AsyncMock()

        class _AcquireCM:
            async def __aenter__(self_):
                return fake_conn
            async def __aexit__(self_, *a):
                return None

        pool = MagicMock()
        pool.acquire = MagicMock(return_value=_AcquireCM())

        await ensure_tenant_schema(pool, tenant_id="acme")

        assert fake_conn.execute.await_count == 2
        sqls = [call.args[0] for call in fake_conn.execute.await_args_list]
        assert any("documents_t_acme" in s for s in sqls)
        assert any("embeddings_t_acme" in s for s in sqls)
        assert all("CREATE TABLE IF NOT EXISTS" in s for s in sqls)


class TestMCPMemoryToolsTenantWiring:
    """add_memory routes through the tenant-scoped table when tenant_id set."""

    @pytest.mark.asyncio
    async def test_add_memory_uses_tenant_table(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from src import mcp_memory_tools

        executed_sql: list = []
        fake_conn = MagicMock()

        async def _capture(sql, *args):
            executed_sql.append(sql)
            return None

        fake_conn.execute = _capture

        class _AcquireCM:
            async def __aenter__(self_):
                return fake_conn
            async def __aexit__(self_, *a):
                return None

        fake_pool = MagicMock()
        fake_pool.acquire = MagicMock(return_value=_AcquireCM())

        with patch("src.security_mcp.validate_memory_content", return_value="hello"), \
             patch("src.security_mcp.validate_agent_id", return_value="agent-1"), \
             patch("src.security_mcp.sanitize_string", return_value="user-1"):
            result = await mcp_memory_tools.add_memory(
                content="hello",
                agent_id="agent-1",
                user_id="user-1",
                tenant_id="acme",
                postgres_pool=fake_pool,
            )

        assert result["status"] == "success"
        joined = "\n".join(executed_sql)
        # Both the schema-bootstrap CREATE TABLEs and the INSERT
        # should have hit the tenant-scoped table name.
        assert "documents_t_acme" in joined
        assert "INSERT INTO shared_memory.documents_t_acme" in joined

    @pytest.mark.asyncio
    async def test_delete_memory_uses_tenant_table(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from src import mcp_memory_tools

        executed_sql: list = []
        fake_conn = MagicMock()

        async def _capture_execute(sql, *args):
            executed_sql.append(("execute", sql))
            return None

        async def _capture_fetchrow(sql, *args):
            executed_sql.append(("fetchrow", sql))
            return {"id": "abc", "agent_id": "agent-1", "category": "x"}

        fake_conn.execute = _capture_execute
        fake_conn.fetchrow = _capture_fetchrow

        class _AcquireCM:
            async def __aenter__(self_):
                return fake_conn
            async def __aexit__(self_, *a):
                return None

        fake_pool = MagicMock()
        fake_pool.acquire = MagicMock(return_value=_AcquireCM())

        with patch("src.security_mcp.validate_uuid", return_value="00000000-0000-0000-0000-000000000001"), \
             patch("src.security_mcp.validate_agent_id", return_value="agent-1"), \
             patch("src.security_mcp.confirmation_manager.require_confirmation"), \
             patch("src.security_mcp.require_agent_authorization", new_callable=AsyncMock):
            await mcp_memory_tools.delete_memory(
                memory_id="00000000-0000-0000-0000-000000000001",
                agent_id="agent-1",
                tenant_id="acme",
                confirm_token="CONFIRM",
                postgres_pool=fake_pool,
            )

        # Both the existence-check fetchrow and the DELETE must hit the
        # tenant-scoped table.
        joined = "\n".join(sql for _kind, sql in executed_sql)
        assert "documents_t_acme" in joined
        assert "DELETE FROM shared_memory.documents_t_acme" in joined

    @pytest.mark.asyncio
    async def test_list_agents_uses_tenant_table(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from src import mcp_memory_tools

        executed_sql: list = []
        fake_conn = MagicMock()

        async def _capture_fetch(sql, *args):
            executed_sql.append(sql)
            return []

        fake_conn.fetch = _capture_fetch

        class _AcquireCM:
            async def __aenter__(self_):
                return fake_conn
            async def __aexit__(self_, *a):
                return None

        fake_pool = MagicMock()
        fake_pool.acquire = MagicMock(return_value=_AcquireCM())

        await mcp_memory_tools.list_agents(
            tenant_id="acme", postgres_pool=fake_pool
        )

        joined = "\n".join(executed_sql)
        assert "documents_t_acme" in joined

    @pytest.mark.asyncio
    async def test_add_memory_unscoped_when_no_tenant_id(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from src import mcp_memory_tools

        executed_sql: list = []
        fake_conn = MagicMock()

        async def _capture(sql, *args):
            executed_sql.append(sql)
            return None

        fake_conn.execute = _capture

        class _AcquireCM:
            async def __aenter__(self_):
                return fake_conn
            async def __aexit__(self_, *a):
                return None

        fake_pool = MagicMock()
        fake_pool.acquire = MagicMock(return_value=_AcquireCM())

        with patch("src.security_mcp.validate_memory_content", return_value="hi"), \
             patch("src.security_mcp.validate_agent_id", return_value="agent-1"), \
             patch("src.security_mcp.sanitize_string", return_value="user-1"):
            result = await mcp_memory_tools.add_memory(
                content="hi",
                agent_id="agent-1",
                user_id="user-1",
                postgres_pool=fake_pool,
            )

        assert result["status"] == "success"
        joined = "\n".join(executed_sql)
        # No tenant -> original un-scoped table
        assert "INSERT INTO shared_memory.documents" in joined
        assert "documents_t_" not in joined


# ---------------------------------------------------------------------------
# ENHANCED_REQUIRE_TENANT enforcement
# ---------------------------------------------------------------------------


class TestRequireTenantEnvVar:
    def test_raises_when_required_but_unset(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
        with pytest.raises(MissingTenantError):
            tenant_scoped_table("documents")
        with pytest.raises(MissingTenantError):
            tenant_scoped_collection("ats")
        with pytest.raises(MissingTenantError):
            tenant_scoped_key("k")
        with pytest.raises(MissingTenantError):
            tenant_scoped_graph("g")

    def test_passes_when_tenant_set(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_REQUIRE_TENANT", "1")
        with TenantContext("acme"):
            assert tenant_scoped_table("documents") == "documents_t_acme"

    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_REQUIRE_TENANT", raising=False)
        # No exception even without a tenant set
        assert tenant_scoped_table("documents") == "documents"
