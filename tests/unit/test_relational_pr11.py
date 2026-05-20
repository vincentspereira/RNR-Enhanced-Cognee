"""Tests for the PR 11 enterprise relational adapters: MS SQL / Oracle / DB2.

All three drivers are mocked -- no live enterprise DB required. Each
adapter is verified against the asyncpg.Pool-shaped contract +
env-var fallback chain.
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src import db_factory


# ---------------------------------------------------------------------------
# Provider matrix
# ---------------------------------------------------------------------------


class TestEnterpriseRelationalMatrix:
    def test_all_pr11_providers_recognised(self):
        for p in ("mssql", "sqlserver", "oracle", "db2"):
            assert p in db_factory._VALID_RELATIONAL


# ---------------------------------------------------------------------------
# MS SQL Server
# ---------------------------------------------------------------------------


class TestMSSQLAdapter:
    def test_dsn_build(self):
        from src.db_adapters import relational_mssql

        dsn = relational_mssql._build_dsn(
            "sql.internal", 1433, "ec", "sa", "pw", "ODBC Driver 18 for SQL Server"
        )
        assert "Server=sql.internal,1433" in dsn
        assert "Database=ec" in dsn
        assert "UID=sa" in dsn
        assert "PWD=pw" in dsn
        assert "Encrypt=yes" in dsn

    def test_env_fallback_dsn_assembly(self, monkeypatch):
        monkeypatch.setenv("MSSQL_HOST", "sql.test")
        monkeypatch.setenv("MSSQL_PORT", "1434")
        monkeypatch.setenv("MSSQL_DB", "ec_test")
        monkeypatch.setenv("MSSQL_USER", "test_user")
        monkeypatch.setenv("MSSQL_PASSWORD", "test_pw")

        fake_aioodbc = MagicMock()
        fake_raw_pool = MagicMock()
        fake_aioodbc.create_pool = AsyncMock(return_value=fake_raw_pool)

        with patch.dict(sys.modules, {"aioodbc": fake_aioodbc}):
            pool = asyncio.run(__import__(
                "src.db_adapters.relational_mssql", fromlist=["*"]
            ).create_pool())

        fake_aioodbc.create_pool.assert_called_once()
        kwargs = fake_aioodbc.create_pool.call_args.kwargs
        assert "sql.test,1434" in kwargs["dsn"]
        assert "Database=ec_test" in kwargs["dsn"]
        assert type(pool).__name__ == "_MSSQLPool"

    def test_factory_dispatch_mssql(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "mssql")
        fake_aioodbc = MagicMock()
        fake_aioodbc.create_pool = AsyncMock(return_value=MagicMock())
        with patch.dict(sys.modules, {"aioodbc": fake_aioodbc}):
            pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_MSSQLPool"

    def test_factory_dispatch_sqlserver_alias(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "sqlserver")
        fake_aioodbc = MagicMock()
        fake_aioodbc.create_pool = AsyncMock(return_value=MagicMock())
        with patch.dict(sys.modules, {"aioodbc": fake_aioodbc}):
            pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_MSSQLPool"

    @pytest.mark.asyncio
    async def test_acquire_returns_connection(self):
        from src.db_adapters import relational_mssql

        fake_raw_conn = MagicMock()
        fake_raw_pool = MagicMock()
        fake_raw_pool.acquire = AsyncMock(return_value=fake_raw_conn)
        fake_raw_pool.release = AsyncMock()

        pool = relational_mssql._MSSQLPool(fake_raw_pool)
        async with pool.acquire() as conn:
            assert isinstance(conn, relational_mssql._MSSQLConnection)


# ---------------------------------------------------------------------------
# Oracle Database
# ---------------------------------------------------------------------------


class TestOracleAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "oracle")
        fake_oracledb = MagicMock()
        fake_oracledb.create_pool_async = MagicMock(return_value=MagicMock())
        with patch.dict(sys.modules, {"oracledb": fake_oracledb}):
            pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_OraclePool"

    def test_dsn_assembly_from_host_port_database(self, monkeypatch):
        # Clear ORACLE_DSN so the host/port/database fallback path runs
        monkeypatch.delenv("ORACLE_DSN", raising=False)
        monkeypatch.delenv("ORACLE_THICK_MODE", raising=False)
        monkeypatch.setenv("ORACLE_USER", "u")
        monkeypatch.setenv("ORACLE_PASSWORD", "p")

        fake_oracledb = MagicMock()
        fake_oracledb.create_pool_async = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, {"oracledb": fake_oracledb}):
            asyncio.run(__import__(
                "src.db_adapters.relational_oracle", fromlist=["*"]
            ).create_pool(host="ora.internal", port=1521, database="FREEPDB1"))

        kwargs = fake_oracledb.create_pool_async.call_args.kwargs
        assert kwargs["dsn"] == "ora.internal:1521/FREEPDB1"
        assert kwargs["user"] == "u"
        assert kwargs["password"] == "p"

    def test_env_dsn_overrides_host_port(self, monkeypatch):
        monkeypatch.setenv("ORACLE_DSN", "oracle.example.com:1521/MYPDB")
        monkeypatch.delenv("ORACLE_THICK_MODE", raising=False)

        fake_oracledb = MagicMock()
        fake_oracledb.create_pool_async = MagicMock(return_value=MagicMock())

        with patch.dict(sys.modules, {"oracledb": fake_oracledb}):
            asyncio.run(__import__(
                "src.db_adapters.relational_oracle", fromlist=["*"]
            ).create_pool(host="ignored", port=9999, database="ignored"))

        kwargs = fake_oracledb.create_pool_async.call_args.kwargs
        assert kwargs["dsn"] == "oracle.example.com:1521/MYPDB"

    def test_thick_mode_initialises_oracle_client(self, monkeypatch):
        monkeypatch.setenv("ORACLE_THICK_MODE", "true")
        monkeypatch.setenv("ORACLE_LIB_DIR", "/opt/instantclient_21_15")

        fake_oracledb = MagicMock()
        fake_oracledb.create_pool_async = MagicMock(return_value=MagicMock())
        fake_oracledb.init_oracle_client = MagicMock()

        with patch.dict(sys.modules, {"oracledb": fake_oracledb}):
            asyncio.run(__import__(
                "src.db_adapters.relational_oracle", fromlist=["*"]
            ).create_pool())

        fake_oracledb.init_oracle_client.assert_called_once_with(
            lib_dir="/opt/instantclient_21_15"
        )

    @pytest.mark.asyncio
    async def test_oracle_acquire(self):
        from src.db_adapters import relational_oracle

        fake_raw_conn = MagicMock()
        fake_raw_pool = MagicMock()
        fake_raw_pool.acquire = AsyncMock(return_value=fake_raw_conn)
        fake_raw_pool.release = AsyncMock()

        pool = relational_oracle._OraclePool(fake_raw_pool)
        async with pool.acquire() as conn:
            assert isinstance(conn, relational_oracle._OracleConnection)


# ---------------------------------------------------------------------------
# IBM Db2
# ---------------------------------------------------------------------------


class TestDB2Adapter:
    def test_dsn_assembly(self):
        from src.db_adapters import relational_db2

        dsn = relational_db2._build_dsn(
            "db2.internal", 50001, "ECDB", "u", "p", "TCPIP"
        )
        assert "DATABASE=ECDB" in dsn
        assert "HOSTNAME=db2.internal" in dsn
        assert "PORT=50001" in dsn
        assert "UID=u" in dsn

    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "db2")
        monkeypatch.setenv("DB2_HOST", "db2.test")
        monkeypatch.setenv("DB2_PORT", "50000")
        pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_DB2Pool"
        assert "HOSTNAME=db2.test" in pool._dsn

    def test_db2_dsn_includes_all_fields(self, monkeypatch):
        monkeypatch.setenv("DB2_HOST", "db2.host")
        monkeypatch.setenv("DB2_PORT", "50000")
        monkeypatch.setenv("DB2_DB", "MEMORY")
        monkeypatch.setenv("DB2_USER", "user1")
        monkeypatch.setenv("DB2_PASSWORD", "pw1")

        from src.db_adapters import relational_db2

        pool = asyncio.run(relational_db2.create_pool())
        assert "DATABASE=MEMORY" in pool._dsn
        assert "HOSTNAME=db2.host" in pool._dsn
        assert "UID=user1" in pool._dsn
        assert "PWD=pw1" in pool._dsn

    @pytest.mark.asyncio
    async def test_db2_acquire_opens_and_closes_connection(self):
        from src.db_adapters import relational_db2

        fake_ibm_db = MagicMock()
        fake_raw_conn = MagicMock()
        fake_ibm_db.connect = MagicMock(return_value=fake_raw_conn)
        fake_ibm_db.close = MagicMock()

        pool = relational_db2._DB2Pool("DATABASE=X;")
        with patch.dict(sys.modules, {"ibm_db": fake_ibm_db}):
            async with pool.acquire() as conn:
                assert isinstance(conn, relational_db2._DB2Connection)

        fake_ibm_db.connect.assert_called_once_with("DATABASE=X;", "", "")
        fake_ibm_db.close.assert_called_once_with(fake_raw_conn)
