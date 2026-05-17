"""
Unit tests for src/sqlite_manager.py
Covers: add_document, get_document, search_documents, delete_document, _row_to_dict

NOTE: test_backup_manager.py stubs sys.modules['src.sqlite_manager'] and restores it
after its own module finishes. We import SQLiteManager lazily (inside fixture) so that
even if our file is collected after the stub is installed we get the real class once the
restore has run.  Running this file standalone always works.
"""

import importlib
import json
import os
import sys
import pytest


def _get_real_sqlite_manager():
    """Return the *real* SQLiteManager, bypassing any module-level stub."""
    real_mod = importlib.import_module("src.sqlite_manager")
    cls = getattr(real_mod, "SQLiteManager", None)
    # If we got the fake stub, reload to get the real one
    if cls is None or not hasattr(cls, "_init_schema"):
        importlib.reload(real_mod)
        cls = real_mod.SQLiteManager
    return cls


SQLiteManager = _get_real_sqlite_manager()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    """Return a fresh SQLite DB path in a temp directory."""
    return str(tmp_path / "test_backup.db")


@pytest.fixture
def manager(db_path):
    """SQLiteManager with a fresh, empty database."""
    return SQLiteManager(db_path)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestSQLiteManagerInit:
    @pytest.mark.unit
    def test_creates_parent_dirs(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "meta.db")
        mgr = SQLiteManager(deep_path)
        assert os.path.exists(deep_path)

    @pytest.mark.unit
    def test_creates_documents_table(self, manager, db_path):
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        names = {row[0] for row in tables}
        assert "documents" in names

    @pytest.mark.unit
    def test_double_init_does_not_fail(self, db_path):
        SQLiteManager(db_path)
        mgr2 = SQLiteManager(db_path)
        assert mgr2 is not None


# ---------------------------------------------------------------------------
# add_document
# ---------------------------------------------------------------------------

class TestAddDocument:
    @pytest.mark.unit
    def test_add_basic_document(self, manager):
        row_id = manager.add_document(
            data_id="doc1",
            data_text="Hello world",
            data_type="text",
            metadata={"key": "value"},
            user_id="user1",
            agent_id="agent1",
        )
        assert isinstance(row_id, str)
        assert len(row_id) > 0

    @pytest.mark.unit
    def test_add_with_none_fields(self, manager):
        row_id = manager.add_document()
        assert isinstance(row_id, str)

    @pytest.mark.unit
    def test_upsert_same_data_id_returns_same_internal_id(self, manager):
        id1 = manager.add_document(data_id="dup", data_text="first")
        id2 = manager.add_document(data_id="dup", data_text="second")
        assert id1 == id2

    @pytest.mark.unit
    def test_upsert_updates_text(self, manager):
        manager.add_document(data_id="up1", data_text="original")
        manager.add_document(data_id="up1", data_text="updated")
        doc = manager.get_document("up1")
        assert doc["data_text"] == "updated"

    @pytest.mark.unit
    def test_add_with_metadata_dict(self, manager):
        manager.add_document(data_id="meta1", metadata={"foo": "bar", "n": 42})
        doc = manager.get_document("meta1")
        assert doc["metadata"]["foo"] == "bar"
        assert doc["metadata"]["n"] == 42

    @pytest.mark.unit
    def test_add_without_metadata_gives_empty_dict(self, manager):
        manager.add_document(data_id="nometa")
        doc = manager.get_document("nometa")
        assert doc["metadata"] == {}

    @pytest.mark.unit
    def test_multiple_unique_data_ids_stored_separately(self, manager):
        for i in range(5):
            manager.add_document(data_id=f"doc_{i}", data_text=f"text {i}")
        # All five should be retrievable
        for i in range(5):
            doc = manager.get_document(f"doc_{i}")
            assert doc is not None
            assert doc["data_text"] == f"text {i}"


# ---------------------------------------------------------------------------
# get_document
# ---------------------------------------------------------------------------

class TestGetDocument:
    @pytest.mark.unit
    def test_get_by_data_id(self, manager):
        manager.add_document(data_id="find_me", data_text="hello")
        doc = manager.get_document("find_me")
        assert doc is not None
        assert doc["data_text"] == "hello"

    @pytest.mark.unit
    def test_get_by_internal_id(self, manager):
        internal_id = manager.add_document(data_id="int_id_test", data_text="content")
        doc = manager.get_document(internal_id)
        assert doc is not None
        assert doc["data_text"] == "content"

    @pytest.mark.unit
    def test_get_nonexistent_returns_none(self, manager):
        result = manager.get_document("does-not-exist")
        assert result is None

    @pytest.mark.unit
    def test_get_returns_all_fields(self, manager):
        manager.add_document(
            data_id="full",
            data_text="t",
            data_type="json",
            metadata={"x": 1},
            user_id="u1",
            agent_id="a1",
        )
        doc = manager.get_document("full")
        assert doc["data_id"] == "full"
        assert doc["data_type"] == "json"
        assert doc["user_id"] == "u1"
        assert doc["agent_id"] == "a1"
        assert "created_at" in doc


# ---------------------------------------------------------------------------
# search_documents
# ---------------------------------------------------------------------------

class TestSearchDocuments:
    @pytest.mark.unit
    def test_search_by_data_id_exact(self, manager):
        manager.add_document(data_id="search_exact", data_text="irrelevant")
        results = manager.search_documents("search_exact")
        assert len(results) == 1
        assert results[0]["data_id"] == "search_exact"

    @pytest.mark.unit
    def test_search_by_text_substring(self, manager):
        manager.add_document(data_id="t1", data_text="Python is great")
        manager.add_document(data_id="t2", data_text="Java is also great")
        manager.add_document(data_id="t3", data_text="Unrelated stuff")
        results = manager.search_documents("great")
        ids = {r["data_id"] for r in results}
        assert "t1" in ids
        assert "t2" in ids
        assert "t3" not in ids

    @pytest.mark.unit
    def test_search_with_user_id_filter(self, manager):
        manager.add_document(data_id="u_doc1", data_text="content1", user_id="alice")
        manager.add_document(data_id="u_doc2", data_text="content2", user_id="bob")
        results = manager.search_documents("content", user_id="alice")
        assert all(r["user_id"] == "alice" for r in results)
        assert len(results) == 1

    @pytest.mark.unit
    def test_search_with_user_id_filter_no_match(self, manager):
        manager.add_document(data_id="x1", data_text="xyz", user_id="carol")
        results = manager.search_documents("xyz", user_id="nobody")
        assert results == []

    @pytest.mark.unit
    def test_search_returns_empty_for_no_match(self, manager):
        results = manager.search_documents("zzz_does_not_exist")
        assert results == []

    @pytest.mark.unit
    def test_search_limit_respected(self, manager):
        for i in range(10):
            manager.add_document(data_id=f"lim_{i}", data_text="common text")
        results = manager.search_documents("common", limit=3)
        assert len(results) <= 3

    @pytest.mark.unit
    def test_search_returns_list_of_dicts(self, manager):
        manager.add_document(data_id="rtype", data_text="sample")
        results = manager.search_documents("sample")
        assert isinstance(results, list)
        assert isinstance(results[0], dict)


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    @pytest.mark.unit
    def test_delete_by_data_id(self, manager):
        manager.add_document(data_id="del1", data_text="delete me")
        result = manager.delete_document("del1")
        assert result is True
        assert manager.get_document("del1") is None

    @pytest.mark.unit
    def test_delete_by_internal_id(self, manager):
        internal_id = manager.add_document(data_id="del2", data_text="gone")
        result = manager.delete_document(internal_id)
        assert result is True

    @pytest.mark.unit
    def test_delete_nonexistent_returns_false(self, manager):
        result = manager.delete_document("does-not-exist-xyz")
        assert result is False

    @pytest.mark.unit
    def test_delete_does_not_affect_others(self, manager):
        manager.add_document(data_id="keep_me", data_text="keep")
        manager.add_document(data_id="remove_me", data_text="remove")
        manager.delete_document("remove_me")
        assert manager.get_document("keep_me") is not None


# ---------------------------------------------------------------------------
# _row_to_dict (static helper)
# ---------------------------------------------------------------------------

class TestRowToDict:
    @pytest.mark.unit
    def test_valid_json_metadata(self, manager):
        manager.add_document(data_id="j1", metadata={"a": 1})
        doc = manager.get_document("j1")
        assert doc["metadata"] == {"a": 1}

    @pytest.mark.unit
    def test_empty_metadata_string_gives_empty_dict(self, manager):
        # Insert with empty string metadata directly via add_document (no meta arg)
        manager.add_document(data_id="nomet")
        doc = manager.get_document("nomet")
        assert isinstance(doc["metadata"], dict)

    @pytest.mark.unit
    def test_metadata_preserved_after_upsert(self, manager):
        manager.add_document(data_id="upsert_meta", metadata={"v": 99})
        manager.add_document(data_id="upsert_meta", metadata={"v": 100})
        doc = manager.get_document("upsert_meta")
        assert doc["metadata"]["v"] == 100
