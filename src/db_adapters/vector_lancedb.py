"""LanceDB adapter (Phase 5 vector pluggable).

LanceDB (https://lancedb.github.io/lancedb/) is an MIT-licensed
embedded vector database built on Apache Arrow + Lance columnar
format. **Runs in-process** -- no Docker container, no network
protocol. Pairs naturally with the ``lean`` deployment profile when
the user wants vector search without bringing up Qdrant.

This adapter mirrors the same narrow ``QdrantClient`` surface that
``vector_pgvector`` ships: one Lance "table" per Qdrant "collection",
with ``id`` / ``vector`` / ``payload`` columns. The duck-typed
``_CollectionDescription`` / ``_SearchHit`` / etc. classes are
reused / mirrored so call sites don't have to special-case the
provider.

**Supported (covers every method our call sites use):**

- ``get_collections()`` / ``get_collection(name)`` / ``count(name)``
- ``create_collection(name, vectors_config=VectorParams(size, distance))``
- ``upsert(name, points=[PointStruct(id, vector, payload)])``
- ``search(name, query_vector, limit, score_threshold)``
- ``delete(name, points_selector)`` accepting:
    * plain list / tuple of IDs
    * ``FilterSelector(filter=Filter(must=[FieldCondition(key, match=MatchValue(value))]))``
      with a single must FieldCondition (matches the
      ``gdpr_manager.delete_user_data`` shape)

**Not supported (raises NotImplementedError):**

- ``query_filter`` in ``search()`` (post-filter in the caller for now)
- Multi-condition / nested / negation delete filters
- Named vectors, sparse vectors, hybrid search

Env-var fallbacks: ``LANCEDB_URI`` (default ``./lancedb_data`` -- a
filesystem directory that LanceDB creates on first ``connect()``).

Install with::

    pip install enhanced-cognee[vector-lancedb]

Lazy-imports ``lancedb`` so installs that don't opt into LanceDB
don't pay the import cost.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Result types -- duck-typed to match qdrant-client's classes (same shape
# as the pgvector adapter for call-site consistency)
# ---------------------------------------------------------------------------


class _CollectionDescription:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class _CollectionsResult:
    __slots__ = ("collections",)

    def __init__(self, collections: List[_CollectionDescription]) -> None:
        self.collections = collections


class _CollectionInfo:
    __slots__ = ("status",)

    def __init__(self) -> None:
        self.status = "green"


class _CountResult:
    __slots__ = ("count",)

    def __init__(self, count: int) -> None:
        self.count = count


class _SearchHit:
    __slots__ = ("id", "score", "payload", "version", "vector")

    def __init__(self, id: Any, score: float, payload: Any) -> None:
        self.id = id
        self.score = score
        self.payload = payload
        self.version = 0
        self.vector = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class _LanceDBClient:
    """QdrantClient-shaped wrapper around a LanceDB connection."""

    def __init__(self, uri: str) -> None:
        self._uri = uri
        self._db: Any = None
        # Remember the configured distance metric per collection so
        # search() can pick the right ranking. LanceDB defaults to L2
        # but we honour the user's VectorParams choice.
        self._distance_by_collection: dict = {}

    def _connect(self):
        if self._db is None:
            import lancedb

            self._db = lancedb.connect(self._uri)
        return self._db

    # -- collection CRUD -----------------------------------------------------

    def get_collections(self) -> _CollectionsResult:
        db = self._connect()
        try:
            names = list(db.table_names())
        except Exception:
            names = []
        return _CollectionsResult([_CollectionDescription(n) for n in names])

    def get_collection(self, collection_name: str) -> _CollectionInfo:
        db = self._connect()
        if collection_name not in db.table_names():
            raise RuntimeError(
                f"lancedb adapter: collection {collection_name!r} not found"
            )
        return _CollectionInfo()

    def create_collection(
        self, collection_name: str, vectors_config: Any, **kwargs: Any
    ) -> None:
        size = int(getattr(vectors_config, "size"))
        distance = getattr(vectors_config, "distance")
        db = self._connect()

        # LanceDB needs schema-on-create or a representative initial
        # row. We use a tiny zero-vector placeholder row and delete it
        # immediately so callers see an empty collection.
        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), size)),
                pa.field("payload", pa.string()),  # JSON-encoded
            ]
        )
        db.create_table(collection_name, schema=schema, exist_ok=True)
        self._distance_by_collection[collection_name] = distance

    # -- point CRUD ----------------------------------------------------------

    def upsert(
        self, collection_name: str, points: Sequence[Any], **kwargs: Any
    ) -> None:
        import json

        db = self._connect()
        table = db.open_table(collection_name)
        rows = []
        for p in points:
            payload = getattr(p, "payload", {}) or {}
            rows.append(
                {
                    "id": str(getattr(p, "id")),
                    "vector": list(getattr(p, "vector")),
                    "payload": json.dumps(payload),
                }
            )
        if not rows:
            return
        # LanceDB doesn't have native ON-CONFLICT; delete by id then add.
        ids = [r["id"] for r in rows]
        table.delete(f"id IN ({','.join(repr(i) for i in ids)})")
        table.add(rows)

    def count(self, collection_name: str, **kwargs: Any) -> _CountResult:
        db = self._connect()
        table = db.open_table(collection_name)
        try:
            return _CountResult(int(table.count_rows()))
        except AttributeError:
            # Older LanceDB: fall back to len(to_pandas())
            return _CountResult(int(len(table.to_pandas())))

    def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        query_filter: Any = None,
        **kwargs: Any,
    ) -> List[_SearchHit]:
        import json

        from src.db_adapters import _vector_filter

        normalised = _vector_filter.normalise(query_filter)
        where_clause = _vector_filter.to_lance_where(normalised)

        db = self._connect()
        table = db.open_table(collection_name)

        distance = self._distance_by_collection.get(collection_name)
        metric = _distance_to_lance_metric(distance)
        search = table.search(list(query_vector))
        if metric is not None:
            search = search.metric(metric)
        if where_clause:
            search = search.where(where_clause)
        df = search.limit(limit).to_pandas()

        hits: List[_SearchHit] = []
        for _, row in df.iterrows():
            raw_distance = float(row.get("_distance", 0.0))
            # LanceDB returns *distance* (smaller better); normalise to
            # a similarity score (higher better) so callers' threshold
            # comparisons behave the same as with qdrant.
            score = 1.0 - raw_distance
            if score_threshold is not None and score < score_threshold:
                continue
            payload_str = row.get("payload") or "{}"
            try:
                payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
            except Exception:
                payload = {}
            hits.append(_SearchHit(id=row["id"], score=score, payload=payload))
        return hits

    def delete(
        self,
        collection_name: str,
        points_selector: Any = None,
        **kwargs: Any,
    ) -> None:
        if points_selector is None:
            return

        db = self._connect()
        table = db.open_table(collection_name)

        # Shape 1: list-like of IDs
        if isinstance(points_selector, (list, tuple)):
            if not points_selector:
                return
            ids = [str(i) for i in points_selector]
            table.delete(f"id IN ({','.join(repr(i) for i in ids)})")
            return

        if hasattr(points_selector, "points") and not hasattr(points_selector, "filter"):
            ids = [str(i) for i in points_selector.points]
            table.delete(f"id IN ({','.join(repr(i) for i in ids)})")
            return

        # Shape 2: FilterSelector with a single must FieldCondition.
        # Limited because LanceDB's SQL-like filter doesn't easily
        # introspect JSON columns; we restrict to a single equality
        # check on a top-level payload key.
        filt = getattr(points_selector, "filter", None)
        if filt is None:
            raise NotImplementedError(
                f"lancedb adapter: unsupported delete selector shape "
                f"{type(points_selector).__name__!r}. Pass a list of "
                f"IDs or a FilterSelector with a single must FieldCondition."
            )

        must = list(getattr(filt, "must", []) or [])
        should = list(getattr(filt, "should", []) or [])
        must_not = list(getattr(filt, "must_not", []) or [])

        if should or must_not or len(must) != 1:
            raise NotImplementedError(
                "lancedb adapter: delete() supports only a single "
                "FieldCondition in `must`."
            )

        cond = must[0]
        key = getattr(cond, "key", None)
        match = getattr(cond, "match", None)
        value = getattr(match, "value", None) if match is not None else None
        if key is None or value is None:
            raise NotImplementedError(
                "lancedb adapter: delete() FieldCondition must expose "
                ".key and .match.value."
            )
        # Delete via a substring match on the JSON-encoded payload --
        # works for top-level string values, which is the GDPR shape.
        marker = f'"{key}": "{value}"'
        table.delete(f"payload LIKE '%{marker}%'")

    def close(self) -> None:
        # LanceDB connections are file-system handles; let GC clean up.
        self._db = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _distance_to_lance_metric(distance: Any) -> Optional[str]:
    """Map qdrant Distance enum to a LanceDB ``metric`` string."""
    if distance is None:
        return None
    name = str(distance).rsplit(".", 1)[-1].lower()
    return {
        "cosine": "cosine",
        "euclid": "l2",
        "dot": "dot",
    }.get(name)


# ---------------------------------------------------------------------------
# Factory entry point
# ---------------------------------------------------------------------------


def create_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    **kwargs: Any,
) -> _LanceDBClient:
    """Create a LanceDB client backed by a filesystem path.

    ``host`` / ``port`` / ``api_key`` are accepted for QdrantClient
    shape compatibility but ignored -- LanceDB is filesystem-backed.
    Override the storage path via ``LANCEDB_URI`` env var (default
    ``./lancedb_data``). ``url`` is also accepted and used as the URI
    if set (handy for ``url='./path'`` callers).
    """
    uri = url or os.getenv("LANCEDB_URI", "./lancedb_data")
    return _LanceDBClient(uri)
