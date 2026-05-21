"""Tests for the PR 12 cloud DW relational adapters: Snowflake / Databricks."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest

from src import db_factory


# ---------------------------------------------------------------------------
# Provider matrix
# ---------------------------------------------------------------------------


class TestCloudDWMatrix:
    def test_all_pr12_providers_recognised(self):
        assert "snowflake" in db_factory._VALID_RELATIONAL
        assert "databricks" in db_factory._VALID_RELATIONAL


# ---------------------------------------------------------------------------
# Snowflake
# ---------------------------------------------------------------------------


class TestSnowflakeAdapter:
    def test_missing_account_raises(self, monkeypatch):
        monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
        from src.db_adapters import relational_snowflake

        with pytest.raises(ValueError, match="SNOWFLAKE_ACCOUNT"):
            asyncio.run(relational_snowflake.create_pool())

    def test_env_fallback_builds_connect_kwargs(self, monkeypatch):
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "abc12345.us-east-1")
        monkeypatch.setenv("SNOWFLAKE_USER", "sf_user")
        monkeypatch.setenv("SNOWFLAKE_PASSWORD", "sf_pw")
        monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "TEST_WH")
        monkeypatch.setenv("SNOWFLAKE_DATABASE", "TEST_DB")
        monkeypatch.setenv("SNOWFLAKE_SCHEMA", "TEST_SCHEMA")
        monkeypatch.setenv("SNOWFLAKE_ROLE", "TEST_ROLE")

        from src.db_adapters import relational_snowflake

        pool = asyncio.run(relational_snowflake.create_pool())
        kwargs = pool._connect_kwargs
        assert kwargs["account"] == "abc12345.us-east-1"
        assert kwargs["user"] == "sf_user"
        assert kwargs["password"] == "sf_pw"
        assert kwargs["warehouse"] == "TEST_WH"
        assert kwargs["database"] == "TEST_DB"
        assert kwargs["schema"] == "TEST_SCHEMA"
        assert kwargs["role"] == "TEST_ROLE"

    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "snowflake")
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test.us-east-1")
        pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_SnowflakePool"

    @pytest.mark.asyncio
    async def test_acquire_opens_and_closes_connection(self):
        from src.db_adapters import relational_snowflake

        # Build fake snowflake.connector module + connect()
        fake_snowflake = MagicMock()
        fake_connector = MagicMock()
        fake_raw_conn = MagicMock()
        fake_connector.connect = MagicMock(return_value=fake_raw_conn)
        fake_snowflake.connector = fake_connector

        pool = relational_snowflake._SnowflakePool({"account": "x", "user": "y"})
        with patch.dict(
            sys.modules,
            {"snowflake": fake_snowflake, "snowflake.connector": fake_connector},
        ):
            async with pool.acquire() as conn:
                assert isinstance(conn, relational_snowflake._SnowflakeConnection)

        fake_connector.connect.assert_called_once()
        fake_raw_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Databricks
# ---------------------------------------------------------------------------


class TestDatabricksAdapter:
    def test_missing_required_envs_raises(self, monkeypatch):
        for v in (
            "DATABRICKS_SERVER_HOSTNAME",
            "DATABRICKS_HTTP_PATH",
            "DATABRICKS_ACCESS_TOKEN",
        ):
            monkeypatch.delenv(v, raising=False)
        from src.db_adapters import relational_databricks

        with pytest.raises(ValueError, match="DATABRICKS_"):
            asyncio.run(relational_databricks.create_pool())

    def test_env_fallback_assembles_config(self, monkeypatch):
        monkeypatch.setenv(
            "DATABRICKS_SERVER_HOSTNAME", "abc-12345.cloud.databricks.com"
        )
        monkeypatch.setenv(
            "DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc123"
        )
        monkeypatch.setenv("DATABRICKS_ACCESS_TOKEN", "dapi-abc-123")
        monkeypatch.setenv("DATABRICKS_CATALOG", "test_catalog")

        from src.db_adapters import relational_databricks

        pool = asyncio.run(relational_databricks.create_pool())
        assert pool._server_hostname == "abc-12345.cloud.databricks.com"
        assert pool._http_path == "/sql/1.0/warehouses/abc123"
        assert pool._access_token == "dapi-abc-123"
        assert pool._catalog == "test_catalog"

    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "databricks")
        monkeypatch.setenv("DATABRICKS_SERVER_HOSTNAME", "test.databricks.com")
        monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/x")
        monkeypatch.setenv("DATABRICKS_ACCESS_TOKEN", "test-token")
        pool = asyncio.run(db_factory.get_relational_pool())
        assert type(pool).__name__ == "_DatabricksPool"

    def test_database_kwarg_overrides_schema(self, monkeypatch):
        monkeypatch.setenv("DATABRICKS_SERVER_HOSTNAME", "x.databricks.com")
        monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/x")
        monkeypatch.setenv("DATABRICKS_ACCESS_TOKEN", "x")
        monkeypatch.setenv("DATABRICKS_SCHEMA", "env_schema")

        from src.db_adapters import relational_databricks

        pool = asyncio.run(
            relational_databricks.create_pool(database="explicit_schema")
        )
        assert pool._schema == "explicit_schema"

    @pytest.mark.asyncio
    async def test_acquire_opens_and_closes_connection(self):
        from src.db_adapters import relational_databricks

        fake_databricks = MagicMock()
        fake_sql_mod = MagicMock()
        fake_raw_conn = MagicMock()
        fake_sql_mod.connect = MagicMock(return_value=fake_raw_conn)
        fake_databricks.sql = fake_sql_mod

        pool = relational_databricks._DatabricksPool(
            "host.databricks.com",
            "/sql/path",
            "tok",
            "hive_metastore",
            "default",
        )
        with patch.dict(
            sys.modules,
            {"databricks": fake_databricks, "databricks.sql": fake_sql_mod},
        ):
            async with pool.acquire() as conn:
                assert isinstance(conn, relational_databricks._DatabricksConnection)

        fake_sql_mod.connect.assert_called_once()
        fake_raw_conn.close.assert_called_once()
