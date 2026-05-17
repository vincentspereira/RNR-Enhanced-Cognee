"""
Unit tests for src/gdpr_manager.py
Covers: GDPRManager - delete_user_data, export_user_data, record_consent,
        check_consent, list_consents, verify_tenant_isolation,
        singleton helpers, dry-run paths, error paths.
Target: >= 85% line coverage.
"""

import io
import json
import zipfile
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.gdpr_manager import (
    GDPRManager,
    init_gdpr_manager,
    get_gdpr_manager,
    _gdpr_manager as _orig_gdpr_manager,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers: async-friendly mock pool
# ---------------------------------------------------------------------------

def _make_conn():
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value=None)
    return conn


class _MockAcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(conn=None):
    if conn is None:
        conn = _make_conn()
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_MockAcquireCtx(conn))
    return pool, conn


# ---------------------------------------------------------------------------
# GDPRManager.__init__
# ---------------------------------------------------------------------------

class TestGDPRManagerInit:
    def test_init_all_optional_none(self):
        pool, _ = _make_pool()
        mgr = GDPRManager(postgres_pool=pool)
        assert mgr.pool is pool
        assert mgr.qdrant is None
        assert mgr.neo4j is None
        assert mgr.redis is None

    def test_init_with_all_deps(self):
        pool, _ = _make_pool()
        qdrant = MagicMock()
        neo4j = MagicMock()
        redis = MagicMock()
        mgr = GDPRManager(pool, qdrant, neo4j, redis)
        assert mgr.qdrant is qdrant
        assert mgr.neo4j is neo4j
        assert mgr.redis is redis


# ---------------------------------------------------------------------------
# delete_user_data -- dry_run=False (full delete)
# ---------------------------------------------------------------------------

class TestDeleteUserData:
    @pytest.mark.asyncio
    async def test_delete_happy_path(self):
        conn = _make_conn()
        conn.fetchval.side_effect = [
            5,   # SELECT COUNT(*) for _get_user_doc_ids (inner acquire)
            8,   # DELETE documents RETURNING COUNT(*)
            True,  # _table_exists -> SELECT EXISTS
            2,   # DELETE consent_records RETURNING COUNT(*)
        ]
        conn.fetch = AsyncMock(return_value=[{"id": "id1"}, {"id": "id2"}])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.delete_user_data("user1")
        assert result["user_id"] == "user1"
        assert result["dry_run"] is False
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_delete_dry_run(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.side_effect = [
            3,  # COUNT(*) for dry-run SELECT
        ]
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.delete_user_data("user1", dry_run=True)
        assert result["dry_run"] is True
        assert result["postgres_rows_deleted"] == 3
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_delete_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        result = await mgr.delete_user_data("user_x")
        assert result["postgres_rows_deleted"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_delete_postgres_exception(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("pg down"))
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.delete_user_data("user_err")
        assert any("postgresql" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_delete_with_qdrant(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        qdrant = MagicMock()
        mgr = GDPRManager(pool, qdrant_client=qdrant)
        result = await mgr.delete_user_data("user_q")
        assert result["qdrant_vectors_deleted"] == -1

    @pytest.mark.asyncio
    async def test_delete_qdrant_import_error(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        qdrant = MagicMock()
        qdrant.delete = MagicMock(side_effect=Exception("qdrant fail"))
        mgr = GDPRManager(pool, qdrant_client=qdrant)

        # Patch the import inside delete_user_data
        with patch.dict("sys.modules", {"qdrant_client.http.models": MagicMock()}):
            result = await mgr.delete_user_data("user_q2")
        # qdrant error should be recorded
        assert any("qdrant" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_delete_with_neo4j(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        rec = {"deleted": 7}
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        result_obj = MagicMock()
        result_obj.single = MagicMock(return_value=rec)
        session.run = MagicMock(return_value=result_obj)
        neo4j = MagicMock()
        neo4j.session = MagicMock(return_value=session)

        mgr = GDPRManager(pool, neo4j_driver=neo4j)
        result = await mgr.delete_user_data("user_n")
        assert result["neo4j_nodes_deleted"] == 7

    @pytest.mark.asyncio
    async def test_delete_neo4j_exception(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        neo4j = MagicMock()
        neo4j.session = MagicMock(side_effect=RuntimeError("neo4j down"))
        mgr = GDPRManager(pool, neo4j_driver=neo4j)
        result = await mgr.delete_user_data("user_ne")
        assert any("neo4j" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_delete_with_redis(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        redis = AsyncMock()
        redis.keys = AsyncMock(return_value=["k1", "k2"])
        redis.delete = AsyncMock()
        mgr = GDPRManager(pool, redis_client=redis)
        result = await mgr.delete_user_data("user_r")
        assert result["redis_keys_deleted"] == 2

    @pytest.mark.asyncio
    async def test_delete_redis_no_keys(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        redis = AsyncMock()
        redis.keys = AsyncMock(return_value=[])
        mgr = GDPRManager(pool, redis_client=redis)
        result = await mgr.delete_user_data("user_r2")
        assert result["redis_keys_deleted"] == 0

    @pytest.mark.asyncio
    async def test_delete_redis_exception(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        redis = AsyncMock()
        redis.keys = AsyncMock(side_effect=RuntimeError("redis down"))
        mgr = GDPRManager(pool, redis_client=redis)
        result = await mgr.delete_user_data("user_re")
        assert any("redis" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_delete_neo4j_single_none(self):
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval.return_value = 0

        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        result_obj = MagicMock()
        result_obj.single = MagicMock(return_value=None)
        session.run = MagicMock(return_value=result_obj)
        neo4j = MagicMock()
        neo4j.session = MagicMock(return_value=session)

        mgr = GDPRManager(pool, neo4j_driver=neo4j)
        result = await mgr.delete_user_data("user_none")
        assert result["neo4j_nodes_deleted"] == 0


# ---------------------------------------------------------------------------
# _get_user_doc_ids
# ---------------------------------------------------------------------------

class TestGetUserDocIds:
    @pytest.mark.asyncio
    async def test_returns_ids(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[{"id": "a"}, {"id": "b"}])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        ids = await mgr._get_user_doc_ids("u1")
        assert ids == ["a", "b"]

    @pytest.mark.asyncio
    async def test_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        ids = await mgr._get_user_doc_ids("u1")
        assert ids == []


# ---------------------------------------------------------------------------
# _table_exists
# ---------------------------------------------------------------------------

class TestTableExists:
    @pytest.mark.asyncio
    async def test_table_exists_true(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value=True)
        result = await GDPRManager._table_exists(conn, "consent_records")
        assert result is True

    @pytest.mark.asyncio
    async def test_table_exists_false(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value=False)
        result = await GDPRManager._table_exists(conn, "no_table")
        assert result is False


# ---------------------------------------------------------------------------
# export_user_data
# ---------------------------------------------------------------------------

class TestExportUserData:
    def _build_doc_rows(self):
        r = MagicMock()
        r.__getitem__ = lambda self, k: {
            "id": "doc1", "title": "T", "content": "C", "agent_id": "u1",
            "metadata": {}, "provenance": None, "confidence": 0.9,
            "memory_tier": "hot", "expire_at": None,
            "created_at": "2024-01-01", "updated_at": "2024-01-02"
        }[k]
        return [r]

    @pytest.mark.asyncio
    async def test_export_json_no_versions(self):
        conn = _make_conn()
        doc_row = MagicMock()
        doc_row.__getitem__ = lambda self, k: {
            "id": "d1", "title": "Title", "content": "body", "agent_id": "u1",
            "metadata": None, "provenance": None, "confidence": None,
            "memory_tier": "cold", "expire_at": None,
            "created_at": "2024-01-01", "updated_at": "2024-01-02"
        }[k]
        conn.fetch = AsyncMock(side_effect=[[doc_row], [], []])  # docs, versions, consents
        conn.fetchval = AsyncMock(return_value=False)  # _table_exists -> False
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        data, fname = await mgr.export_user_data("u1", include_versions=False)
        export = json.loads(data)
        assert export["user_id"] == "u1"
        assert len(export["memories"]) == 1
        assert fname.endswith(".json")

    @pytest.mark.asyncio
    async def test_export_as_zip(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=False)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        data, fname = await mgr.export_user_data("u2", as_zip=True)
        assert fname.endswith(".zip")
        buf = io.BytesIO(data)
        with zipfile.ZipFile(buf) as zf:
            assert len(zf.namelist()) == 1

    @pytest.mark.asyncio
    async def test_export_with_versions(self):
        conn = _make_conn()
        ver_row = MagicMock()
        ver_row.__getitem__ = lambda self, k: {
            "id": "v1", "memory_id": "d1", "version_number": 1,
            "content": "old", "change_reason": "edit", "created_at": "2024-01-01"
        }[k]
        conn.fetch = AsyncMock(side_effect=[[], [ver_row]])  # docs then versions
        conn.fetchval = AsyncMock(return_value=False)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        data, _ = await mgr.export_user_data("u3", include_versions=True)
        export = json.loads(data)
        assert len(export["version_history"]) == 1

    @pytest.mark.asyncio
    async def test_export_with_consent_records(self):
        conn = _make_conn()
        consent_row = MagicMock()
        consent_row.__getitem__ = lambda self, k: {
            "category": "marketing", "granted": True,
            "granted_at": "2024-01-01", "revoked_at": None
        }[k]
        conn.fetch = AsyncMock(side_effect=[[], [], [consent_row]])
        conn.fetchval = AsyncMock(return_value=True)  # table_exists -> True
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        data, _ = await mgr.export_user_data("u4")
        export = json.loads(data)
        assert len(export["consent_records"]) == 1
        assert export["consent_records"][0]["category"] == "marketing"

    @pytest.mark.asyncio
    async def test_export_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        data, fname = await mgr.export_user_data("u_none")
        export = json.loads(data)
        assert export["memories"] == []
        assert export["version_history"] == []

    @pytest.mark.asyncio
    async def test_export_postgres_exception(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("db gone"))
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        data, _ = await mgr.export_user_data("u_err")
        export = json.loads(data)
        assert "error" in export

    @pytest.mark.asyncio
    async def test_export_confidence_not_none(self):
        conn = _make_conn()
        doc_row = MagicMock()
        doc_row.__getitem__ = lambda self, k: {
            "id": "d2", "title": "T2", "content": "C2", "agent_id": "u5",
            "metadata": None, "provenance": "src", "confidence": "0.75",
            "memory_tier": "warm", "expire_at": "2025-01-01",
            "created_at": "2024-01-01", "updated_at": "2024-01-02"
        }[k]
        conn.fetch = AsyncMock(side_effect=[[doc_row], []])
        conn.fetchval = AsyncMock(return_value=False)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        data, _ = await mgr.export_user_data("u5", include_versions=True)
        export = json.loads(data)
        assert export["memories"][0]["confidence"] == 0.75


# ---------------------------------------------------------------------------
# record_consent
# ---------------------------------------------------------------------------

class TestRecordConsent:
    @pytest.mark.asyncio
    async def test_record_consent_granted(self):
        conn = _make_conn()
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        ok = await mgr.record_consent("u1", "marketing", True)
        assert ok is True
        conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_record_consent_revoked(self):
        conn = _make_conn()
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        ok = await mgr.record_consent("u1", "analytics", False)
        assert ok is True

    @pytest.mark.asyncio
    async def test_record_consent_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        ok = await mgr.record_consent("u1", "cat", True)
        assert ok is False

    @pytest.mark.asyncio
    async def test_record_consent_exception(self):
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("write fail"))
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        ok = await mgr.record_consent("u1", "cat", True)
        assert ok is False


# ---------------------------------------------------------------------------
# check_consent
# ---------------------------------------------------------------------------

class TestCheckConsent:
    @pytest.mark.asyncio
    async def test_check_consent_granted(self):
        conn = _make_conn()
        row = MagicMock()
        row.__getitem__ = lambda self, k: True if k == "granted" else None
        conn.fetchrow = AsyncMock(return_value=row)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.check_consent("u1", "marketing")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_consent_no_record(self):
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value=None)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.check_consent("u1", "unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_consent_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        result = await mgr.check_consent("u1", "cat")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_consent_exception(self):
        conn = _make_conn()
        conn.fetchrow = AsyncMock(side_effect=RuntimeError("db err"))
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.check_consent("u1", "cat")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_consent_revoked(self):
        conn = _make_conn()
        row = MagicMock()
        row.__getitem__ = lambda self, k: False if k == "granted" else None
        conn.fetchrow = AsyncMock(return_value=row)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.check_consent("u1", "analytics")
        assert result is False


# ---------------------------------------------------------------------------
# list_consents
# ---------------------------------------------------------------------------

class TestListConsents:
    @pytest.mark.asyncio
    async def test_list_consents_some(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value=True)  # table_exists
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "category": "analytics", "granted": True,
            "granted_at": "2024-01-01", "revoked_at": None, "updated_at": "2024-01-01"
        }[k]
        conn.fetch = AsyncMock(return_value=[row])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.list_consents("u1")
        assert len(result) == 1
        assert result[0]["category"] == "analytics"

    @pytest.mark.asyncio
    async def test_list_consents_table_missing(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value=False)
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.list_consents("u1")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_consents_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        result = await mgr.list_consents("u1")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_consents_exception(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(side_effect=RuntimeError("boom"))
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.list_consents("u1")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_consents_revoked_at_none(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value=True)
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "category": "prefs", "granted": False,
            "granted_at": None, "revoked_at": "2024-06-01", "updated_at": "2024-06-01"
        }[k]
        conn.fetch = AsyncMock(return_value=[row])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.list_consents("u1")
        assert result[0]["granted_at"] is None
        assert result[0]["revoked_at"] is not None


# ---------------------------------------------------------------------------
# verify_tenant_isolation
# ---------------------------------------------------------------------------

class TestVerifyTenantIsolation:
    @pytest.mark.asyncio
    async def test_clean_isolation(self):
        conn = _make_conn()
        row = MagicMock()
        row.__getitem__ = lambda self, k: "tenant_a" if k == "agent_id" else "id1"
        conn.fetch = AsyncMock(return_value=[row])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.verify_tenant_isolation("tenant_a")
        assert result["clean"] is True
        assert result["violations"] == []

    @pytest.mark.asyncio
    async def test_violation_detected(self):
        conn = _make_conn()
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "id": "mem1", "agent_id": "other_tenant"
        }[k]
        conn.fetch = AsyncMock(return_value=[row])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.verify_tenant_isolation("tenant_a")
        assert result["clean"] is False
        assert len(result["violations"]) == 1

    @pytest.mark.asyncio
    async def test_no_pool(self):
        mgr = GDPRManager(postgres_pool=None)
        result = await mgr.verify_tenant_isolation("t1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("boom"))
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.verify_tenant_isolation("t1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_tenant(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool, _ = _make_pool(conn)
        mgr = GDPRManager(pool)
        result = await mgr.verify_tenant_isolation("tenant_empty")
        assert result["sampled"] == 0
        assert result["clean"] is True


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

class TestSingletonHelpers:
    def test_init_gdpr_manager(self):
        pool, _ = _make_pool()
        mgr = init_gdpr_manager(pool)
        assert isinstance(mgr, GDPRManager)
        assert get_gdpr_manager() is mgr

    def test_init_with_all_clients(self):
        pool, _ = _make_pool()
        qdrant = MagicMock()
        neo4j = MagicMock()
        redis = MagicMock()
        mgr = init_gdpr_manager(pool, qdrant, neo4j, redis)
        assert mgr.qdrant is qdrant
        assert mgr.neo4j is neo4j
        assert mgr.redis is redis

    def test_get_gdpr_manager_none_initially(self):
        import src.gdpr_manager as mod
        original = mod._gdpr_manager
        mod._gdpr_manager = None
        assert get_gdpr_manager() is None
        mod._gdpr_manager = original
