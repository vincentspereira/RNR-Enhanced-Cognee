"""Vector-adapter filter translation layer.

Centralises the qdrant-shaped ``Filter`` -> backend-specific translation
that pgvector / lancedb / chroma / weaviate / milvus all need. The
qdrant API surface RNR Enhanced Cognee uses is narrow -- almost exclusively
single ``must=[FieldCondition(key, match=MatchValue(value))]`` filters
on a top-level payload key (see ``src/gdpr_manager.py::delete_user_data``
and the locust load-gen workloads). This module pins that narrow
contract so each adapter doesn't have to re-implement the same five
duck-type checks.

What it covers:
  - Normalise a qdrant Filter / FilterSelector / FieldCondition into an
    internal ``_NormalisedFilter`` (a list of ``_EqualityCondition``s).
  - Translate that normalised form into the matching backend dialect:
      * ``to_python_predicate(normalised)`` -- callable(payload) -> bool
        for adapters that filter at the application layer.
      * ``to_sql_where(normalised)`` -- ``(sql_fragment, params)`` tuple
        for pgvector / Postgres-flavoured backends.
      * ``to_chroma_where(normalised)`` -- a dict for Chroma's
        ``where={"key": value}`` form.
      * ``to_weaviate_filter(normalised)`` -- a weaviate v4 ``Filter``
        chain.
      * ``to_milvus_expr(normalised)`` -- a Milvus filter expression string.

What it deliberately rejects (raises ``NotImplementedError``):
  - ``should`` and ``must_not`` clauses
  - More than one ``must`` condition
  - Anything other than ``match=MatchValue(value=...)`` on a string key

The errors all point at this module and explain how the caller should
pre-filter (e.g. query first, pass IDs) so the limitation isn't a
silent footgun.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class _EqualityCondition:
    """A single ``key = value`` payload-equality filter."""

    key: str
    value: Any


@dataclass(frozen=True)
class _NormalisedFilter:
    """Normalised filter form -- ordered list of equality conditions.

    Today every condition is implicitly AND-combined (qdrant's
    ``must`` semantics). The list type is kept so the same code can
    be extended later without rewriting every adapter call site.
    """

    must: Tuple[_EqualityCondition, ...] = ()


def normalise(qdrant_filter: Any) -> _NormalisedFilter:
    """Convert a qdrant-shaped Filter into the internal form.

    Accepted shapes (defensive duck-typing, no qdrant import required):
      * ``None`` -> empty filter (caller should treat as "match all").
      * A ``Filter`` object exposing ``.must`` / ``.should`` / ``.must_not``
        attributes (qdrant client v1.x).
      * A ``FieldCondition`` object exposing ``.key`` / ``.match.value`` --
        for callers that pass a single condition directly. Detected via
        a string-typed ``.key`` so MagicMock auto-attrs on a Filter
        stub don't accidentally enter this path.

    Raises ``NotImplementedError`` for compound forms (multiple
    conditions, ``should`` / ``must_not``) with a clear pointer to
    the supported narrow shape.
    """
    if qdrant_filter is None:
        return _NormalisedFilter()

    # Prefer the Filter shape (has must/should/must_not as list-like).
    # If any of those resolve to a list/tuple/None, we treat the input
    # as a Filter; otherwise we fall through to the FieldCondition path.
    must_raw = getattr(qdrant_filter, "must", _MISSING)
    should_raw = getattr(qdrant_filter, "should", _MISSING)
    must_not_raw = getattr(qdrant_filter, "must_not", _MISSING)
    looks_like_filter = any(
        _is_clause_value(v) for v in (must_raw, should_raw, must_not_raw)
    )

    if looks_like_filter:
        must = list(must_raw) if _is_listlike(must_raw) else []
        should = list(should_raw) if _is_listlike(should_raw) else []
        must_not = list(must_not_raw) if _is_listlike(must_not_raw) else []

        if should or must_not:
            raise NotImplementedError(
                "Vector adapter filter translator: `should` / `must_not` "
                "clauses are not supported. Query the points first and "
                "filter the IDs at the application layer. See "
                "src/db_adapters/_vector_filter.py and docs/PROFILES.md."
            )

        if len(must) > 1:
            raise NotImplementedError(
                "Vector adapter filter translator: only a single `must` "
                "FieldCondition is supported. For compound filters, "
                "query the points first and pass IDs explicitly. See "
                "src/db_adapters/_vector_filter.py."
            )

        if not must:
            return _NormalisedFilter()

        return _NormalisedFilter(must=(_extract_condition(must[0]),))

    # Direct FieldCondition shortcut -- requires a string .key
    if (
        getattr(qdrant_filter, "match", None) is not None
        and isinstance(getattr(qdrant_filter, "key", None), str)
    ):
        return _NormalisedFilter(must=(_extract_condition(qdrant_filter),))

    raise NotImplementedError(
        "Vector adapter filter translator: input is neither a qdrant "
        "Filter (with .must / .should / .must_not) nor a FieldCondition "
        "(with string .key and .match). Got: "
        f"{type(qdrant_filter).__name__}."
    )


_MISSING = object()


def _is_clause_value(value: Any) -> bool:
    """A clause value is None or list/tuple. Excludes MagicMock auto-attrs."""
    if value is _MISSING:
        return False
    return value is None or isinstance(value, (list, tuple))


def _is_listlike(value: Any) -> bool:
    return isinstance(value, (list, tuple))


def _extract_condition(cond: Any) -> _EqualityCondition:
    key = getattr(cond, "key", None)
    match = getattr(cond, "match", None)
    value = getattr(match, "value", None) if match is not None else None
    if key is None or value is None:
        raise NotImplementedError(
            "Vector adapter filter translator: only "
            "`FieldCondition(key=..., match=MatchValue(value=...))` "
            "is supported. Got: "
            f"key={key!r}, match={match!r}."
        )
    if not isinstance(key, str):
        raise NotImplementedError(
            "Vector adapter filter translator: FieldCondition `.key` "
            f"must be a string. Got: {type(key).__name__}."
        )
    return _EqualityCondition(key=key, value=value)


# ---------------------------------------------------------------------------
# Backend translations
# ---------------------------------------------------------------------------


def to_python_predicate(normalised: _NormalisedFilter) -> Callable[[Any], bool]:
    """Application-layer predicate -- for adapters with no native filter.

    The predicate accepts the *raw payload* (typically a dict or a JSON
    string). It returns True when every must-condition matches.
    """
    if not normalised.must:
        return lambda payload: True

    conds = list(normalised.must)

    def _pred(payload: Any) -> bool:
        d = _payload_to_dict(payload)
        for cond in conds:
            if d.get(cond.key) != cond.value:
                return False
        return True

    return _pred


def _payload_to_dict(payload: Any) -> Dict[str, Any]:
    """Best-effort dict view of a payload.

    Accepts dicts (returns as-is), JSON-encoded strings (parses), or
    None (returns empty dict). Anything else is treated as opaque and
    yields a non-matching empty dict.
    """
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return {}
    if isinstance(payload, str):
        import json

        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def to_sql_where(normalised: _NormalisedFilter) -> Tuple[str, List[Any]]:
    """Translate to a SQL ``WHERE`` fragment + parameter list.

    The fragment uses Postgres JSONB ``->>`` text-extraction so it
    works against pgvector's ``payload JSONB`` column. Returns an
    empty string + empty params when the filter is a no-op.
    """
    if not normalised.must:
        return "", []

    fragments: List[str] = []
    params: List[Any] = []
    for cond in normalised.must:
        fragments.append("payload ->> %s = %s")
        params.append(cond.key)
        params.append(str(cond.value))
    return " AND ".join(fragments), params


def to_chroma_where(normalised: _NormalisedFilter) -> Optional[Dict[str, Any]]:
    """Translate to a Chroma ``where={"key": value}`` dict.

    Returns ``None`` for a no-op filter so callers can pass it
    unconditionally to ``collection.query(..., where=where_dict)``.
    """
    if not normalised.must:
        return None
    return {cond.key: cond.value for cond in normalised.must}


def to_weaviate_filter(normalised: _NormalisedFilter) -> Any:
    """Translate to a weaviate v4 ``Filter`` chain.

    The weaviate client is lazy-imported because not every install
    has it. Returns ``None`` for a no-op filter.
    """
    if not normalised.must:
        return None
    from weaviate.classes.query import Filter  # local import (optional dep)

    # Each condition becomes a `LIKE %value%` so we match against
    # the JSON-encoded payload column the adapter writes. This
    # mirrors the GDPR-shaped substring match the existing
    # vector_weaviate.delete() path uses.
    chain = None
    for cond in normalised.must:
        sub = Filter.by_property("payload").like(f'*"{cond.key}":"{cond.value}"*')
        chain = sub if chain is None else chain & sub
    return chain


def to_milvus_expr(normalised: _NormalisedFilter) -> str:
    """Translate to a Milvus filter expression string.

    Returns the empty string for a no-op filter. The match uses
    Milvus's ``like`` on the JSON-encoded ``payload`` column.
    """
    if not normalised.must:
        return ""
    pieces: List[str] = []
    for cond in normalised.must:
        # Escape backslashes/quotes to keep the expr a safe literal.
        safe_key = str(cond.key).replace("\\", "\\\\").replace('"', '\\"')
        safe_value = str(cond.value).replace("\\", "\\\\").replace('"', '\\"')
        pieces.append(
            f'payload like "%\\"{safe_key}\\":\\"{safe_value}\\"%"'
        )
    return " and ".join(pieces)


def to_lance_where(normalised: _NormalisedFilter) -> str:
    """Translate to a LanceDB SQL ``WHERE`` clause fragment.

    LanceDB's ``table.search(...).where(<sql>)`` accepts a SQL-ish
    filter. The ``payload`` column is a JSON-encoded text column;
    we match on its full text via ``LIKE``.
    """
    if not normalised.must:
        return ""
    pieces: List[str] = []
    for cond in normalised.must:
        safe_key = str(cond.key).replace("'", "''")
        safe_value = str(cond.value).replace("'", "''")
        # Match the substring '"key":"value"' inside the JSON-encoded
        # payload column. Keep the quoting consistent with how the
        # adapter writes the column.
        pieces.append(
            f"payload LIKE '%\"{safe_key}\":\"{safe_value}\"%'"
        )
    return " AND ".join(pieces)
