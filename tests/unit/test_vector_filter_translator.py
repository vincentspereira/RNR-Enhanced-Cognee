"""Tests for the shared vector-adapter filter translator.

The translator is the single source of truth for "what does qdrant
Filter -> backend dialect translation look like" so any divergence
here would silently propagate to all 5 vector adapters. These tests
nail down each translation path against a stub qdrant Filter shape.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.db_adapters import _vector_filter


# ---------------------------------------------------------------------------
# normalise()
# ---------------------------------------------------------------------------


class TestNormalise:
    def test_none_returns_empty_filter(self):
        f = _vector_filter.normalise(None)
        assert f.must == ()

    def test_filter_object_with_no_clauses_is_empty(self):
        filt = MagicMock(must=None, should=None, must_not=None)
        f = _vector_filter.normalise(filt)
        assert f.must == ()

    def test_filter_object_with_empty_clauses_is_empty(self):
        filt = MagicMock(must=[], should=[], must_not=[])
        f = _vector_filter.normalise(filt)
        assert f.must == ()

    def test_single_must_condition(self):
        cond = MagicMock(key="user_id", match=MagicMock(value="u1"))
        filt = MagicMock(must=[cond], should=None, must_not=None)

        f = _vector_filter.normalise(filt)
        assert len(f.must) == 1
        assert f.must[0].key == "user_id"
        assert f.must[0].value == "u1"

    def test_field_condition_shortcut(self):
        # If the caller passes a FieldCondition directly (some code paths do)
        cond = MagicMock(key="x", match=MagicMock(value="y"))
        f = _vector_filter.normalise(cond)
        assert f.must == (_vector_filter._EqualityCondition("x", "y"),)

    def test_should_clause_raises(self):
        cond = MagicMock(key="x", match=MagicMock(value="y"))
        filt = MagicMock(must=None, should=[cond], must_not=None)
        with pytest.raises(NotImplementedError, match="should"):
            _vector_filter.normalise(filt)

    def test_must_not_clause_raises(self):
        cond = MagicMock(key="x", match=MagicMock(value="y"))
        filt = MagicMock(must=None, should=None, must_not=[cond])
        with pytest.raises(NotImplementedError, match="must_not"):
            _vector_filter.normalise(filt)

    def test_multiple_must_raises(self):
        cond_a = MagicMock(key="a", match=MagicMock(value="x"))
        cond_b = MagicMock(key="b", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond_a, cond_b], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            _vector_filter.normalise(filt)

    def test_missing_match_raises(self):
        # A FieldCondition with no .match
        cond = MagicMock(spec=["key"])
        cond.key = "x"
        filt = MagicMock(must=[cond], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="MatchValue"):
            _vector_filter.normalise(filt)

    def test_non_string_key_raises(self):
        cond = MagicMock(key=42, match=MagicMock(value="y"))
        filt = MagicMock(must=[cond], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="string"):
            _vector_filter.normalise(filt)


# ---------------------------------------------------------------------------
# to_python_predicate()
# ---------------------------------------------------------------------------


class TestPythonPredicate:
    def test_empty_predicate_matches_everything(self):
        pred = _vector_filter.to_python_predicate(_vector_filter._NormalisedFilter())
        assert pred({}) is True
        assert pred({"any": "thing"}) is True
        assert pred(None) is True

    def test_single_condition_matches_dict_payload(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("user_id", "u1"),)
        )
        pred = _vector_filter.to_python_predicate(norm)
        assert pred({"user_id": "u1"}) is True
        assert pred({"user_id": "u2"}) is False
        assert pred({}) is False

    def test_single_condition_matches_json_string_payload(self):
        # Some adapters store the payload as JSON-encoded string
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("user_id", "u1"),)
        )
        pred = _vector_filter.to_python_predicate(norm)
        assert pred('{"user_id": "u1", "extra": 99}') is True
        assert pred('{"user_id": "u2"}') is False

    def test_bytes_payload_decodes_utf8(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("k", "v"),)
        )
        pred = _vector_filter.to_python_predicate(norm)
        assert pred(b'{"k": "v"}') is True

    def test_unparseable_payload_does_not_match(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("k", "v"),)
        )
        pred = _vector_filter.to_python_predicate(norm)
        assert pred("not_json") is False
        assert pred(12345) is False
        assert pred(None) is False


# ---------------------------------------------------------------------------
# to_sql_where()
# ---------------------------------------------------------------------------


class TestSqlWhere:
    def test_empty_filter_emits_empty_clause(self):
        sql, params = _vector_filter.to_sql_where(_vector_filter._NormalisedFilter())
        assert sql == ""
        assert params == []

    def test_single_condition_emits_payload_extract(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("user_id", "u1"),)
        )
        sql, params = _vector_filter.to_sql_where(norm)
        assert sql == "payload ->> %s = %s"
        assert params == ["user_id", "u1"]


# ---------------------------------------------------------------------------
# to_chroma_where()
# ---------------------------------------------------------------------------


class TestChromaWhere:
    def test_empty_filter_returns_none(self):
        assert _vector_filter.to_chroma_where(_vector_filter._NormalisedFilter()) is None

    def test_single_condition_returns_dict(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("user_id", "u1"),)
        )
        assert _vector_filter.to_chroma_where(norm) == {"user_id": "u1"}


# ---------------------------------------------------------------------------
# to_milvus_expr()
# ---------------------------------------------------------------------------


class TestMilvusExpr:
    def test_empty_filter_returns_empty_string(self):
        assert _vector_filter.to_milvus_expr(_vector_filter._NormalisedFilter()) == ""

    def test_single_condition_emits_like_expression(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("user_id", "u1"),)
        )
        expr = _vector_filter.to_milvus_expr(norm)
        # Format: payload like "%\"user_id\":\"u1\"%"
        assert 'payload like' in expr
        assert "user_id" in expr
        assert "u1" in expr

    def test_special_chars_in_value_are_escaped(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("k", 'value"with"quotes'),)
        )
        expr = _vector_filter.to_milvus_expr(norm)
        # Original quotes must be backslash-escaped so the SQL literal stays well-formed.
        assert '\\"with\\"' in expr


# ---------------------------------------------------------------------------
# to_lance_where()
# ---------------------------------------------------------------------------


class TestLanceWhere:
    def test_empty_filter_returns_empty_string(self):
        assert _vector_filter.to_lance_where(_vector_filter._NormalisedFilter()) == ""

    def test_single_condition_emits_like_clause(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("user_id", "u1"),)
        )
        where = _vector_filter.to_lance_where(norm)
        assert "payload LIKE" in where
        assert "user_id" in where and "u1" in where

    def test_single_quote_in_value_is_doubled(self):
        norm = _vector_filter._NormalisedFilter(
            must=(_vector_filter._EqualityCondition("k", "o'brien"),)
        )
        where = _vector_filter.to_lance_where(norm)
        # SQL single-quote literal escape doubles the quote
        assert "o''brien" in where


# ---------------------------------------------------------------------------
# to_weaviate_filter()
# ---------------------------------------------------------------------------


class TestWeaviateFilter:
    def test_empty_filter_returns_none(self):
        assert _vector_filter.to_weaviate_filter(_vector_filter._NormalisedFilter()) is None

    def test_single_condition_calls_by_property_payload(self):
        # Inject a fake weaviate.classes.query module so the test doesn't
        # need the real client lib installed.
        import sys

        fake_filter_cls = MagicMock()
        fake_chain = MagicMock(name="chain")
        fake_by_prop = MagicMock(name="by_prop")
        fake_by_prop.like.return_value = fake_chain
        fake_filter_cls.by_property.return_value = fake_by_prop

        fake_module = MagicMock()
        fake_module.Filter = fake_filter_cls
        sys.modules["weaviate.classes.query"] = fake_module

        try:
            norm = _vector_filter._NormalisedFilter(
                must=(_vector_filter._EqualityCondition("user_id", "u1"),)
            )
            result = _vector_filter.to_weaviate_filter(norm)

            assert result is fake_chain
            fake_filter_cls.by_property.assert_called_once_with("payload")
            args = fake_by_prop.like.call_args[0]
            # The substring contains the JSON-encoded key:value pair
            assert "user_id" in args[0]
            assert "u1" in args[0]
        finally:
            sys.modules.pop("weaviate.classes.query", None)
