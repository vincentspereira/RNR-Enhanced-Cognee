"""Milvus adapter (Phase 5 vector pluggable).

Milvus (https://milvus.io/) is an Apache-2.0 vector database aimed at
billion-scale workloads. Wraps the ``pymilvus`` v2 ``MilvusClient``
API in the same narrow ``QdrantClient`` surface that the other Phase
5 vector adapters ship.

Storage model: one Milvus collection per Qdrant collection. Each
collection has a schema with ``id`` (varchar PK), ``vector``
(float-vector with the configured dimension), and ``payload`` (json).

**Supported (covers every method our call sites use):**

- ``get_collections()`` / ``get_collection(name)`` / ``count(name)``
- ``create_collection(name, vectors_config=VectorParams(size, distance))``
- ``upsert(name, points=[PointStruct(id, vector, payload)])``
- ``search(name, query_vector, limit, score_threshold)``
- ``delete(name, points_selector)`` for ID list / single ``must``
  FieldCondition

**Not supported (raises NotImplementedError):**

- Rich ``query_filter`` in search
- Multi-condition / nested / negation delete filters

Env-var fallbacks:
  ``MILVUS_HOST`` (default ``localhost``) / ``MILVUS_PORT``
  (default ``19530``) / ``MILVUS_TOKEN`` (optional Zilliz / cluster
  auth token; falls through to ``MILVUS_USER:MILVUS_PASSWORD`` if set).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence


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


# Milvus accepts: COSINE / L2 / IP / HAMMING / JACCARD
_DISTANCE_TO_MILVUS = {
    "cosine": "COSINE",
    "euclid": "L2",
    "dot": "IP",
}


def _distance_to_milvus_metric(distance: Any) -> str:
    name = str(distance).rsplit(".", 1)[-1].lower()
    return _DISTANCE_TO_MILVUS.get(name, "COSINE")


class _MilvusClient:
    """QdrantClient-shaped wrapper around pymilvus MilvusClient."""

    def __init__(
        self,
        uri: str,
        token: Optional[str],
    ) -> None:
        self._uri = uri
        self._token = token
        self._client: Any = None
        self._distance_by_collection: dict = {}

    def _connect(self):
        if self._client is None:
            from pymilvus import MilvusClient

            kwargs: dict = {"uri": self._uri}
            if self._token:
                kwargs["token"] = self._token
            self._client = MilvusClient(**kwargs)
        return self._client

    def get_collections(self) -> _CollectionsResult:
        client = self._connect()
        try:
            names = list(client.list_collections())
        except Exception:
            names = []
        return _CollectionsResult([_CollectionDescription(n) for n in names])

    def get_collection(self, collection_name: str) -> _CollectionInfo:
        client = self._connect()
        if not client.has_collection(collection_name):
            raise RuntimeError(
                f"milvus adapter: collection {collection_name!r} not found"
            )
        return _CollectionInfo()

    def create_collection(
        self, collection_name: str, vectors_config: Any, **kwargs: Any
    ) -> None:
        from pymilvus import DataType

        client = self._connect()
        if client.has_collection(collection_name):
            return

        size = int(getattr(vectors_config, "size"))
        distance = getattr(vectors_config, "distance", None)
        metric = _distance_to_milvus_metric(distance)

        # MilvusClient quick-create supports a metric_type + dimension
        # shortcut without manually declaring a Schema.
        client.create_collection(
            collection_name=collection_name,
            dimension=size,
            metric_type=metric,
            primary_field_name="id",
            id_type=DataType.VARCHAR,
            vector_field_name="vector",
            auto_id=False,
            max_length=512,
        )
        self._distance_by_collection[collection_name] = metric

    def upsert(
        self, collection_name: str, points: Sequence[Any], **kwargs: Any
    ) -> None:
        client = self._connect()
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
        # MilvusClient v2: upsert(...) is the idempotent op
        client.upsert(collection_name=collection_name, data=rows)

    def count(self, collection_name: str, **kwargs: Any) -> _CountResult:
        client = self._connect()
        try:
            stats = client.get_collection_stats(collection_name=collection_name)
            n = int(stats.get("row_count", 0))
        except Exception:
            n = 0
        return _CountResult(n)

    def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        query_filter: Any = None,
        **kwargs: Any,
    ) -> List[_SearchHit]:
        from src.db_adapters import _vector_filter

        normalised = _vector_filter.normalise(query_filter)
        expr = _vector_filter.to_milvus_expr(normalised)

        client = self._connect()
        search_kwargs: Dict[str, Any] = {
            "collection_name": collection_name,
            "data": [list(query_vector)],
            "limit": limit,
            "output_fields": ["id", "payload"],
        }
        if expr:
            search_kwargs["filter"] = expr
        results = client.search(**search_kwargs)
        # MilvusClient returns list-of-list (one inner list per query
        # vector); we always send 1 query.
        first = results[0] if results else []
        hits: List[_SearchHit] = []
        metric = self._distance_by_collection.get(collection_name, "COSINE")
        for hit in first:
            raw = float(hit.get("distance", 0.0))
            # Milvus COSINE returns *similarity* directly (higher better);
            # L2 / IP return distance / dot-product. Normalise to
            # "higher = better" for the caller's threshold comparison.
            if metric == "COSINE":
                score = raw
            elif metric == "L2":
                score = 1.0 - raw
            else:  # IP / dot
                score = raw
            if score_threshold is not None and score < score_threshold:
                continue
            entity = hit.get("entity") or hit
            payload_raw = entity.get("payload") if hasattr(entity, "get") else None
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else (payload_raw or {})
            except Exception:
                payload = {}
            hits.append(
                _SearchHit(id=str(hit.get("id", entity.get("id", ""))),
                           score=score, payload=payload)
            )
        return hits

    def delete(
        self,
        collection_name: str,
        points_selector: Any = None,
        **kwargs: Any,
    ) -> None:
        if points_selector is None:
            return
        client = self._connect()

        if isinstance(points_selector, (list, tuple)):
            if not points_selector:
                return
            client.delete(
                collection_name=collection_name,
                ids=[str(i) for i in points_selector],
            )
            return

        if hasattr(points_selector, "points") and not hasattr(points_selector, "filter"):
            client.delete(
                collection_name=collection_name,
                ids=[str(i) for i in points_selector.points],
            )
            return

        filt = getattr(points_selector, "filter", None)
        if filt is None:
            raise NotImplementedError(
                f"milvus adapter: unsupported delete selector shape "
                f"{type(points_selector).__name__!r}."
            )

        must = list(getattr(filt, "must", []) or [])
        should = list(getattr(filt, "should", []) or [])
        must_not = list(getattr(filt, "must_not", []) or [])
        if should or must_not or len(must) != 1:
            raise NotImplementedError(
                "milvus adapter: delete() supports only a single must "
                "FieldCondition."
            )
        cond = must[0]
        key = getattr(cond, "key", None)
        match = getattr(cond, "match", None)
        value = getattr(match, "value", None) if match is not None else None
        if key is None or value is None:
            raise NotImplementedError(
                "milvus adapter: delete() FieldCondition must expose "
                ".key and .match.value."
            )
        # Use Milvus' filter expression on the payload column. We store
        # payload as JSON so we use a `LIKE` over the serialised text.
        marker = f'%"{key}": "{value}"%'
        client.delete(
            collection_name=collection_name,
            filter=f'payload like "{marker}"',
        )

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


def create_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    **kwargs: Any,
) -> _MilvusClient:
    """Create a Milvus v2 client.

    URI is built as ``http://host:port`` unless an explicit ``url``
    kwarg is passed. Env-var fallbacks: MILVUS_HOST / MILVUS_PORT /
    MILVUS_TOKEN (falls through to MILVUS_USER:MILVUS_PASSWORD).
    """
    if url is None:
        h = host or os.getenv("MILVUS_HOST", "localhost")
        p = port or int(os.getenv("MILVUS_PORT", "19530"))
        url = f"http://{h}:{p}"

    token = api_key or os.getenv("MILVUS_TOKEN")
    if not token:
        user = os.getenv("MILVUS_USER")
        password = os.getenv("MILVUS_PASSWORD")
        if user and password:
            token = f"{user}:{password}"

    return _MilvusClient(url, token)
