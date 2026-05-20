"""pgvector adapter (Phase 5 vector pluggable).

pgvector (https://github.com/pgvector/pgvector) is an Apache-2.0 vector
extension to Postgres. This adapter wraps psycopg2 against a Postgres
instance with pgvector installed, exposing a ``QdrantClient``-shaped
surface so the existing call sites in
``src/agent_memory_integration.py``, ``src/enhanced_cognee_mcp.py``,
``src/intelligent_summarization.py``, ``src/memory_deduplication.py``,
and ``src/gdpr_manager.py`` work without code changes.

**Storage model:** one Postgres table per Qdrant "collection". Each
table has columns ``id TEXT PRIMARY KEY``, ``vector vector(N)``, and
``payload JSONB``. Tables are prefixed with ``PGVECTOR_TABLE_PREFIX``
(default ``ec_vec_``) to keep them in their own namespace inside the
shared Postgres DB.

**Supported (full):**
- ``get_collections()`` -> objects with ``.collections`` list of
  ``.name``-bearing objects
- ``get_collection(name)`` -> raises if not found (matches Qdrant)
- ``create_collection(name, vectors_config=VectorParams(size, distance))``
  with Cosine / Euclid / Dot product distance metrics
- ``upsert(name, points=[PointStruct(id, vector, payload)])``
- ``search(name, query_vector, limit, score_threshold)`` (no filter yet)
- ``count(name)`` -> object with ``.count``
- ``delete(name, points_selector)`` with two selector shapes:
    1. A plain list of point IDs
    2. A ``FilterSelector(filter=Filter(must=[FieldCondition(key, match=MatchValue(value))]))``
       restricted to a single ``must`` FieldCondition on a top-level
       payload key (used by ``gdpr_manager.delete_user_data``).

**Not supported (raises NotImplementedError):**
- Complex query filters in ``search()``
- Multi-condition / nested / negation filters in ``delete()``
- Named vectors, sparse vectors
- Payload field indexes
- Quantization / on-disk vectors / snapshots

Env-var fallbacks: ``PGVECTOR_HOST`` / ``PGVECTOR_PORT`` / ``PGVECTOR_DB`` /
``PGVECTOR_USER`` / ``PGVECTOR_PASSWORD`` / ``PGVECTOR_TABLE_PREFIX``,
falling through to ``POSTGRES_*`` (since pgvector typically lives in
the same Postgres as the rest of the stack).

Install with::

    pip install enhanced-cognee[vector-pgvector]

(``psycopg2`` is already in core deps; ``pgvector`` Python helper is
optional and only used for the IVFFLAT index hint -- not the
serialisation, which we do manually.)

Lazy-imports ``psycopg2`` so tests that mock it via ``sys.modules`` or
``psycopg2.connect`` keep working.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, List, Optional, Sequence


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_]")


def _safe_table_name(prefix: str, collection_name: str) -> str:
    """Map a Qdrant collection name to a safe Postgres table name."""
    sanitised = _SAFE_NAME_RE.sub("_", collection_name).lower().strip("_")
    return f"{prefix}{sanitised}"


def _distance_to_opclass(distance: Any) -> str:
    """Map qdrant Distance enum to a pgvector index opclass."""
    name = str(distance).rsplit(".", 1)[-1].lower()
    # qdrant uses Cosine / Euclid / Dot / Manhattan
    return {
        "cosine": "vector_cosine_ops",
        "euclid": "vector_l2_ops",
        "dot": "vector_ip_ops",
    }.get(name, "vector_cosine_ops")


def _distance_to_operator(distance: Any) -> str:
    """Map qdrant Distance enum to a pgvector distance operator.

    pgvector operators:
      ``<->``  L2 distance
      ``<#>``  negative inner product
      ``<=>``  cosine distance (1 - cosine_similarity)
    """
    name = str(distance).rsplit(".", 1)[-1].lower()
    return {
        "cosine": "<=>",
        "euclid": "<->",
        "dot": "<#>",
    }.get(name, "<=>")


# ---------------------------------------------------------------------------
# Result types -- mirror the duck-typed surface of qdrant-client's classes
# ---------------------------------------------------------------------------


class _CollectionDescription:
    """qdrant_client.http.models.CollectionDescription-shaped wrapper."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class _CollectionsResult:
    """qdrant_client.http.models.CollectionsResponse-shape."""

    __slots__ = ("collections",)

    def __init__(self, collections: List[_CollectionDescription]) -> None:
        self.collections = collections


class _CollectionInfo:
    """Trivial qdrant_client.http.models.CollectionInfo-shape."""

    __slots__ = ("status",)

    def __init__(self) -> None:
        self.status = "green"


class _CountResult:
    """qdrant_client.http.models.CountResult-shape."""

    __slots__ = ("count",)

    def __init__(self, count: int) -> None:
        self.count = count


class _SearchHit:
    """qdrant_client.http.models.ScoredPoint-shape."""

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


class _PgVectorClient:
    """QdrantClient-shaped wrapper around psycopg2 + pgvector."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_prefix: str,
        distance_by_table: Optional[dict] = None,
    ) -> None:
        self._conn_params = dict(
            host=host, port=port, dbname=database, user=user, password=password
        )
        self._table_prefix = table_prefix
        # Remember the distance metric per table so search() can pick the
        # right pgvector operator. Populated by create_collection().
        self._distance_by_table: dict = distance_by_table or {}

    # -- connection helpers --------------------------------------------------

    def _connect(self):
        import psycopg2

        return psycopg2.connect(**self._conn_params)

    def _table_for(self, collection_name: str) -> str:
        return _safe_table_name(self._table_prefix, collection_name)

    # -- collection CRUD -----------------------------------------------------

    def get_collections(self) -> _CollectionsResult:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename LIKE %s "
                "ORDER BY tablename",
                (f"{self._table_prefix}%",),
            )
            rows = cur.fetchall()
        prefix_len = len(self._table_prefix)
        return _CollectionsResult(
            [_CollectionDescription(row[0][prefix_len:]) for row in rows]
        )

    def get_collection(self, collection_name: str) -> _CollectionInfo:
        """Return collection info, or raise if the table doesn't exist."""
        table = self._table_for(collection_name)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT EXISTS("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = 'public' AND table_name = %s"
                ")",
                (table,),
            )
            exists = cur.fetchone()[0]
        if not exists:
            raise RuntimeError(
                f"pgvector adapter: collection {collection_name!r} not found "
                f"(table {table!r} does not exist). Did you call "
                f"create_collection() yet?"
            )
        return _CollectionInfo()

    def create_collection(
        self, collection_name: str, vectors_config: Any, **kwargs: Any
    ) -> None:
        """Create the table + IVFFLAT index for a new collection.

        ``vectors_config`` must be a ``VectorParams``-shaped object with
        ``.size`` (int) and ``.distance`` (qdrant Distance enum or str).
        """
        size = int(getattr(vectors_config, "size"))
        distance = getattr(vectors_config, "distance")
        opclass = _distance_to_opclass(distance)
        table = self._table_for(collection_name)

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            # Format the table identifier into the DDL after sanitising
            # via _safe_table_name; the regex above strips anything but
            # [a-zA-Z0-9_] so injection is not possible from this path.
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS "{table}" ('
                f'  id TEXT PRIMARY KEY,'
                f'  vector vector({size}),'
                f'  payload JSONB'
                f')'
            )
            # IVFFLAT requires sample data to be useful; lists=100 is a
            # reasonable default. Users with large collections should
            # REINDEX after bulk-loading.
            cur.execute(
                f'CREATE INDEX IF NOT EXISTS "{table}_vec_idx" '
                f'ON "{table}" USING ivfflat (vector {opclass}) '
                f'WITH (lists = 100)'
            )
            conn.commit()

        self._distance_by_table[table] = distance

    # -- point CRUD ----------------------------------------------------------

    def upsert(self, collection_name: str, points: Sequence[Any], **kwargs: Any) -> None:
        """Upsert one or more PointStruct-shaped points."""
        table = self._table_for(collection_name)
        with self._connect() as conn:
            cur = conn.cursor()
            for p in points:
                point_id = getattr(p, "id")
                vector = getattr(p, "vector")
                payload = getattr(p, "payload", {}) or {}
                cur.execute(
                    f'INSERT INTO "{table}" (id, vector, payload) '
                    f'VALUES (%s, %s::vector, %s::jsonb) '
                    f'ON CONFLICT (id) DO UPDATE SET '
                    f'  vector = EXCLUDED.vector, '
                    f'  payload = EXCLUDED.payload',
                    (str(point_id), _vector_to_str(vector), json.dumps(payload)),
                )
            conn.commit()

    def count(self, collection_name: str, **kwargs: Any) -> _CountResult:
        table = self._table_for(collection_name)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            row = cur.fetchone()
        return _CountResult(int(row[0]) if row else 0)

    def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        query_filter: Any = None,
        **kwargs: Any,
    ) -> List[_SearchHit]:
        """Vector similarity search.

        Returns a list of ``_SearchHit`` (``.id`` / ``.score`` / ``.payload``).
        Score is the cosine similarity (or 1 - distance for other metrics)
        normalised to "higher is better" so that callers can use the same
        comparison as with qdrant.
        """
        from src.db_adapters import _vector_filter

        normalised = _vector_filter.normalise(query_filter)
        where_sql, where_params = _vector_filter.to_sql_where(normalised)

        table = self._table_for(collection_name)
        distance = self._distance_by_table.get(table)
        operator = _distance_to_operator(distance) if distance else "<=>"

        where_clause = f"WHERE {where_sql} " if where_sql else ""

        with self._connect() as conn:
            cur = conn.cursor()
            # 1 - distance gives a similarity score in [0, 1] for cosine;
            # for L2 / inner-product this isn't strictly a similarity but
            # callers compare with > threshold which still behaves sensibly.
            cur.execute(
                f'SELECT id, payload, 1 - (vector {operator} %s::vector) AS score '
                f'FROM "{table}" '
                f'{where_clause}'
                f'ORDER BY vector {operator} %s::vector '
                f'LIMIT %s',
                (
                    _vector_to_str(query_vector),
                    *where_params,
                    _vector_to_str(query_vector),
                    limit,
                ),
            )
            rows = cur.fetchall()

        hits: List[_SearchHit] = []
        for row_id, payload, score in rows:
            if score_threshold is not None and score < score_threshold:
                continue
            hits.append(_SearchHit(id=row_id, score=float(score), payload=payload))
        return hits

    def delete(
        self,
        collection_name: str,
        points_selector: Any = None,
        **kwargs: Any,
    ) -> None:
        """Delete points by ID list or by a single-FieldCondition filter.

        Two selector shapes accepted:
          1. A plain list / tuple of point IDs.
          2. A ``FilterSelector(filter=Filter(must=[FieldCondition(key=...,
             match=MatchValue(value=...))]))`` -- restricted to a single
             ``must`` FieldCondition on a top-level payload key. This is
             enough to support ``gdpr_manager.delete_user_data``.

        More complex filter shapes raise NotImplementedError -- callers
        should query the points first and pass the IDs explicitly.
        """
        table = self._table_for(collection_name)

        if points_selector is None or (
            hasattr(points_selector, "__len__")
            and not hasattr(points_selector, "filter")
            and len(points_selector) == 0
        ):
            return  # nothing to do

        # Shape 1: list-like of IDs
        if isinstance(points_selector, (list, tuple)):
            ids = [str(i) for i in points_selector]
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    f'DELETE FROM "{table}" WHERE id = ANY(%s)', (ids,)
                )
                conn.commit()
            return

        # Shape 1b: a points_selector object with a .points list
        if hasattr(points_selector, "points") and not hasattr(points_selector, "filter"):
            ids = [str(i) for i in points_selector.points]
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    f'DELETE FROM "{table}" WHERE id = ANY(%s)', (ids,)
                )
                conn.commit()
            return

        # Shape 2: FilterSelector with a single must FieldCondition
        filt = getattr(points_selector, "filter", None)
        if filt is None:
            raise NotImplementedError(
                f"pgvector adapter: unsupported delete selector shape "
                f"{type(points_selector).__name__!r}. Pass a list of "
                f"IDs or a FilterSelector with a single must FieldCondition."
            )

        must = list(getattr(filt, "must", []) or [])
        should = list(getattr(filt, "should", []) or [])
        must_not = list(getattr(filt, "must_not", []) or [])

        if should or must_not or len(must) != 1:
            raise NotImplementedError(
                "pgvector adapter: delete() supports only a single "
                "FieldCondition in `must` (no `should` / `must_not` / "
                "compound filters). Query the points first and pass IDs."
            )

        cond = must[0]
        key = getattr(cond, "key", None)
        match = getattr(cond, "match", None)
        value = getattr(match, "value", None) if match is not None else None
        if key is None or value is None:
            raise NotImplementedError(
                "pgvector adapter: delete() FieldCondition must expose "
                "`.key` and `.match.value`. Got: "
                f"key={key!r}, match={match!r}."
            )

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f'DELETE FROM "{table}" WHERE payload ->> %s = %s',
                (str(key), str(value)),
            )
            conn.commit()

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        # Each operation opens its own short-lived connection; nothing
        # persistent to close.
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vector_to_str(vec: Sequence[float]) -> str:
    """Format a Python sequence as a pgvector literal string."""
    return "[" + ",".join(repr(float(v)) for v in vec) + "]"


# ---------------------------------------------------------------------------
# Factory entry point
# ---------------------------------------------------------------------------


def create_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _PgVectorClient:
    """Create a pgvector client.

    Env-var fallbacks (each falls through to ``POSTGRES_*``):
      PGVECTOR_HOST / PGVECTOR_PORT / PGVECTOR_DB / PGVECTOR_USER /
      PGVECTOR_PASSWORD / PGVECTOR_TABLE_PREFIX (default ``ec_vec_``).
    """
    host = host or os.getenv("PGVECTOR_HOST") or os.getenv("POSTGRES_HOST", "localhost")
    port = port or int(
        os.getenv("PGVECTOR_PORT") or os.getenv("POSTGRES_PORT", "25432")
    )
    database = database or os.getenv("PGVECTOR_DB") or os.getenv(
        "POSTGRES_DB", "cognee_db"
    )
    user = user or os.getenv("PGVECTOR_USER") or os.getenv(
        "POSTGRES_USER", "cognee_user"
    )
    password = password or os.getenv("PGVECTOR_PASSWORD") or os.getenv(
        "POSTGRES_PASSWORD", "cognee_password"
    )
    table_prefix = os.getenv("PGVECTOR_TABLE_PREFIX", "ec_vec_")

    return _PgVectorClient(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        table_prefix=table_prefix,
    )
