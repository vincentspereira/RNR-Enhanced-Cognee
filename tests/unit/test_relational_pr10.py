"""Tests for the PR 10 relational adapters: DuckDB + MySQL/MariaDB.

The underlying drivers are mocked so no live database is required.
Each adapter is exercised against the asyncpg.Pool-shaped contract
that ``src/db_adapters/relational_postgres.py`` and ``relational_sqlite.py``
already implement: ``create_pool()`` -> Pool -> ``pool.acquire()`` ->
async-context-manager -> Connection with ``fetchval`` / ``fetchrow``
/ ``fetch`` / ``execute`` / ``executemany``.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src import db_factory


# ---------------------------------------------------------------------------
# Factory matrix
# ---------------------------------------------------------------------------


class TestRelationalFactoryMatrix:
    def test_all_providers_recognised(self):
        # PR 10 expands the matrix from {postgres, postgresql, sqlite}
        # to include duckdb + mysql/mariadb.
        assert "duckdb" in db_factory._VALID_RELATIONAL
        assert "mysql" in db_factory._VALID_RELATIONAL
        assert "mariadb" in db_factory._VALID_RELATIONAL
        # Existing providers preserved
        assert "postgres" in db_factory._VALID_RELATIONAL
        assert "sqlite" in db_factory._VALID_RELATIONAL

    def test_postgres_still_default(self, monkeypatch):
        for v in ("ENHANCED_RELATIONAL_PROVIDER", "RELATIONAL_BACKEND"):
            monkeypatch.delenv(v, raising=False)
        assert db_factory.get_provider_summary()["relational"] == "postgres"


# ---------------------------------------------------------------------------
# DuckDB adapter
# ---------------------------------------------------------------------------


class TestDuckDBAdapter:
    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("DUCKDB_DB_PATH", "/tmp/test_duck.db")
        # Don't actually need a real duckdb module for create_pool --
        # it doesn't import duckdb until acquire().
        from src.db_adapters import relational_duckdb

        async def _go():
            return await relational_duckdb.create_pool()

        import asyncio
        pool = asyncio.run(_go())
        assert pool._db_path == "/tmp/test_duck.db"
        assert pool._read_only is False

    def test_read_only_env(self, monkeypatch):
        monkeypatch.setenv("DUCKDB_DB_PATH", ":memory:")
        monkeypatch.setenv("DUCKDB_READ_ONLY", "true")
        from src.db_adapters import relational_duckdb

        import asyncio
        pool = asyncio.run(relational_duckdb.create_pool())
        assert pool._read_only is True

    def test_database_kwarg_overrides_env(self, monkeypatch):
        monkeypatch.setenv("DUCKDB_DB_PATH", "/tmp/env.db")
        from src.db_adapters import relational_duckdb

        import asyncio
        pool = asyncio.run(relational_duckdb.create_pool(database="/tmp/explicit.db"))
        assert pool._db_path == "/tmp/explicit.db"

    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "duckdb")
        monkeypatch.setenv("DUCKDB_DB_PATH", ":memory:")
        import asyncio
        pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_DuckDBPool"

    @pytest.mark.asyncio
    async def test_acquire_returns_connection(self):
        from src.db_adapters import relational_duckdb

        fake_duckdb = MagicMock()
        fake_raw_conn = MagicMock()
        fake_duckdb.connect.return_value = fake_raw_conn

        pool = relational_duckdb._DuckDBPool(":memory:")
        with patch.dict(sys.modules, {"duckdb": fake_duckdb}):
            async with pool.acquire() as conn:
                assert isinstance(conn, relational_duckdb._DuckDBConnection)
                assert conn._conn is fake_raw_conn
        # Connection closed on exit
        fake_raw_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetchval(self):
        from src.db_adapters import relational_duckdb

        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchone.return_value = (42,)
        fake_conn.execute.return_value = fake_cur

        conn = relational_duckdb._DuckDBConnection(fake_conn)
        result = await conn.fetchval("SELECT 42")
        assert result == 42

    @pytest.mark.asyncio
    async def test_fetchrow(self):
        from src.db_adapters import relational_duckdb

        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchone.return_value = (1, "Alice")
        fake_conn.execute.return_value = fake_cur

        conn = relational_duckdb._DuckDBConnection(fake_conn)
        result = await conn.fetchrow("SELECT id, name FROM users WHERE id = ?", 1)
        assert result == (1, "Alice")
        fake_conn.execute.assert_called_with(
            "SELECT id, name FROM users WHERE id = ?", [1]
        )

    @pytest.mark.asyncio
    async def test_fetch_all_rows(self):
        from src.db_adapters import relational_duckdb

        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchall.return_value = [(1, "a"), (2, "b")]
        fake_conn.execute.return_value = fake_cur

        conn = relational_duckdb._DuckDBConnection(fake_conn)
        result = await conn.fetch("SELECT * FROM users")
        assert result == [(1, "a"), (2, "b")]

    @pytest.mark.asyncio
    async def test_execute_returns_row_count_str(self):
        from src.db_adapters import relational_duckdb

        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_cur.fetchall.return_value = []  # INSERT returns no rows
        fake_conn.execute.return_value = fake_cur

        conn = relational_duckdb._DuckDBConnection(fake_conn)
        result = await conn.execute("INSERT INTO users (id) VALUES (?)", 1)
        assert result.startswith("OK")

    @pytest.mark.asyncio
    async def test_executemany(self):
        from src.db_adapters import relational_duckdb

        fake_conn = MagicMock()
        conn = relational_duckdb._DuckDBConnection(fake_conn)
        await conn.executemany(
            "INSERT INTO users VALUES (?, ?)",
            [(1, "a"), (2, "b")],
        )
        fake_conn.executemany.assert_called_once()


# ---------------------------------------------------------------------------
# MySQL / MariaDB adapter
# ---------------------------------------------------------------------------


class TestMySQLAdapter:
    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("MYSQL_HOST", "mysql.internal")
        monkeypatch.setenv("MYSQL_PORT", "3307")
        monkeypatch.setenv("MYSQL_DB", "ec_test")
        monkeypatch.setenv("MYSQL_USER", "ec_user")
        monkeypatch.setenv("MYSQL_PASSWORD", "secret")

        fake_asyncmy = MagicMock()
        fake_raw_pool = MagicMock()
        fake_asyncmy.create_pool = AsyncMock(return_value=fake_raw_pool)

        import asyncio
        with patch.dict(sys.modules, {"asyncmy": fake_asyncmy}):
            pool = asyncio.run(__import__(
                "src.db_adapters.relational_mysql", fromlist=["*"]
            ).create_pool())

        fake_asyncmy.create_pool.assert_called_once()
        kwargs = fake_asyncmy.create_pool.call_args.kwargs
        assert kwargs["host"] == "mysql.internal"
        assert kwargs["port"] == 3307
        assert kwargs["db"] == "ec_test"
        assert kwargs["user"] == "ec_user"
        assert kwargs["password"] == "secret"
        assert type(pool).__name__ == "_MySQLPool"

    def test_factory_dispatch_mysql(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "mysql")
        fake_asyncmy = MagicMock()
        fake_asyncmy.create_pool = AsyncMock(return_value=MagicMock())
        import asyncio
        with patch.dict(sys.modules, {"asyncmy": fake_asyncmy}):
            pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_MySQLPool"

    def test_factory_dispatch_mariadb(self, monkeypatch):
        # `mariadb` is an alias for the same adapter.
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "mariadb")
        fake_asyncmy = MagicMock()
        fake_asyncmy.create_pool = AsyncMock(return_value=MagicMock())
        import asyncio
        with patch.dict(sys.modules, {"asyncmy": fake_asyncmy}):
            pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_MySQLPool"

    @pytest.mark.asyncio
    async def test_acquire_returns_connection(self):
        from src.db_adapters import relational_mysql

        fake_raw_conn = MagicMock()
        fake_raw_pool = MagicMock()
        fake_raw_pool.acquire = AsyncMock(return_value=fake_raw_conn)

        pool = relational_mysql._MySQLPool(fake_raw_pool)
        async with pool.acquire() as conn:
            assert isinstance(conn, relational_mysql._MySQLConnection)
            assert conn._conn is fake_raw_conn

        fake_raw_pool.release.assert_called_once_with(fake_raw_conn)

    @pytest.mark.asyncio
    async def test_fetchval_returns_first_col(self):
        from src.db_adapters import relational_mysql

        fake_cur = MagicMock()
        fake_cur.execute = AsyncMock()
        fake_cur.fetchone = AsyncMock(return_value=(42,))

        class _CtxCursor:
            async def __aenter__(self_): return fake_cur
            async def __aexit__(self_, *a): return None

        fake_conn = MagicMock()
        fake_conn.cursor = MagicMock(return_value=_CtxCursor())

        conn = relational_mysql._MySQLConnection(fake_conn)
        result = await conn.fetchval("SELECT 42")
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_commits(self):
        from src.db_adapters import relational_mysql

        fake_cur = MagicMock()
        fake_cur.execute = AsyncMock()
        fake_cur.rowcount = 1

        class _CtxCursor:
            async def __aenter__(self_): return fake_cur
            async def __aexit__(self_, *a): return None

        fake_conn = MagicMock()
        fake_conn.cursor = MagicMock(return_value=_CtxCursor())
        fake_conn.commit = AsyncMock()

        conn = relational_mysql._MySQLConnection(fake_conn)
        result = await conn.execute("INSERT INTO t VALUES (1)")
        assert "OK" in result and "1" in result
        fake_conn.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pool_close(self):
        from src.db_adapters import relational_mysql

        fake_raw_pool = MagicMock()
        fake_raw_pool.close = MagicMock()
        fake_raw_pool.wait_closed = AsyncMock()

        pool = relational_mysql._MySQLPool(fake_raw_pool)
        await pool.close()
        fake_raw_pool.close.assert_called_once()
        fake_raw_pool.wait_closed.assert_awaited_once()


# ---------------------------------------------------------------------------
# Unknown provider raises
# ---------------------------------------------------------------------------


class TestUnknownProvider:
    def test_unknown_relational_provider_raises(self, monkeypatch):
        # `clickhouse` is not in the relational matrix (it's an OLAP
        # column store; users would target it via SQLAlchemy in
        # application code if needed).
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "clickhouse")
        import asyncio
        with pytest.raises(ValueError, match="Unknown ENHANCED_RELATIONAL_PROVIDER"):
            asyncio.run(db_factory.get_relational_pool())
