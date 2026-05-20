"""Weaviate adapter (Phase 5 vector pluggable).

Weaviate (https://weaviate.io/) is a BSD-3-licensed vector database
with a rich GraphQL/REST API and native multi-tenancy. Targets users
who already run Weaviate or want its hybrid search + module ecosystem.

This adapter wraps the v4 ``weaviate`` Python client in the same narrow
``QdrantClient`` surface that the other Phase 5 vector adapters ship.
Weaviate's "Collection" abstraction maps cleanly onto Qdrant's, so the
mapping is structural rather than translational.

**Supported (covers every method our call sites use):**

- ``get_collections()`` / ``get_collection(name)`` / ``count(name)``
- ``create_collection(name, vectors_config=VectorParams(size, distance))``
  -- creates a Weaviate collection with a single ``payload`` text
  property and the right vector distance metric
- ``upsert(name, points=[PointStruct(id, vector, payload)])`` via
  ``data.insert(...)`` with explicit UUID + vector + payload-as-JSON
- ``search(name, query_vector, limit, score_threshold)`` via
  ``query.near_vector(...)``
- ``delete(name, points_selector)`` for ID list / single ``must``
  FieldCondition (GDPR shape)

**Not supported (raises NotImplementedError):**

- Rich ``query_filter`` in search (qdrant-Filter -> Weaviate-Filter
  translation is non-trivial; would route through ``where=...``)
- Multi-condition / nested / negation delete filters
- Weaviate's hybrid search (BM25 + vector) -- not exposed by the
  qdrant-shaped API

Env-var fallbacks:
  ``WEAVIATE_HOST`` (default ``localhost``) / ``WEAVIATE_PORT``
  (default ``8080``) / ``WEAVIATE_API_KEY`` (optional).
"""

from __future__ import annotations

import json
import os
import uuid as _uuid_mod
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


# Weaviate v4 distance metrics:
#   "cosine" / "l2-squared" / "dot" / "hamming" / "manhattan"
_DISTANCE_TO_WEAVIATE = {
    "cosine": "cosine",
    "euclid": "l2-squared",
    "dot": "dot",
}


def _distance_to_weaviate_metric(distance: Any) -> str:
    name = str(distance).rsplit(".", 1)[-1].lower()
    return _DISTANCE_TO_WEAVIATE.get(name, "cosine")


def _to_uuid(point_id: Any) -> str:
    """Weaviate requires UUIDs as object identifiers.

    If the caller's id is already a UUID string, pass it through;
    otherwise hash-derive a stable UUID5 so re-upserts of the same
    logical id collide on the same Weaviate object.
    """
    s = str(point_id)
    try:
        return str(_uuid_mod.UUID(s))
    except ValueError:
        return str(_uuid_mod.uuid5(_uuid_mod.NAMESPACE_OID, s))


class _WeaviateClient:
    """QdrantClient-shaped wrapper over the weaviate-python v4 client."""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: Optional[str],
    ) -> None:
        self._host = host
        self._port = port
        self._api_key = api_key
        self._client: Any = None

    def _connect(self):
        if self._client is None:
            import weaviate
            from weaviate.auth import AuthApiKey

            auth = AuthApiKey(self._api_key) if self._api_key else None
            self._client = weaviate.connect_to_custom(
                http_host=self._host,
                http_port=self._port,
                http_secure=False,
                grpc_host=self._host,
                grpc_port=self._port + 1,  # weaviate convention
                grpc_secure=False,
                auth_credentials=auth,
            )
        return self._client

    def get_collections(self) -> _CollectionsResult:
        client = self._connect()
        cols = client.collections.list_all()
        # v4: dict of {name: Config}; keys are the user-facing names
        names = list(cols.keys()) if isinstance(cols, dict) else [getattr(c, "name") for c in cols]
        return _CollectionsResult([_CollectionDescription(n) for n in names])

    def get_collection(self, collection_name: str) -> _CollectionInfo:
        client = self._connect()
        if not client.collections.exists(collection_name):
            raise RuntimeError(
                f"weaviate adapter: collection {collection_name!r} not found"
            )
        return _CollectionInfo()

    def create_collection(
        self, collection_name: str, vectors_config: Any, **kwargs: Any
    ) -> None:
        from weaviate.classes.config import Configure, Property, DataType

        client = self._connect()
        if client.collections.exists(collection_name):
            return

        distance = getattr(vectors_config, "distance", None)
        metric = _distance_to_weaviate_metric(distance)
        client.collections.create(
            name=collection_name,
            properties=[
                Property(name="payload", data_type=DataType.TEXT),
            ],
            vectorizer_config=Configure.Vectorizer.none(),  # we provide vectors
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=metric),
        )

    def upsert(
        self, collection_name: str, points: Sequence[Any], **kwargs: Any
    ) -> None:
        client = self._connect()
        col = client.collections.get(collection_name)
        # v4 batch insert -- one round-trip per upsert call
        with col.batch.dynamic() as batch:
            for p in points:
                payload = getattr(p, "payload", {}) or {}
                batch.add_object(
                    uuid=_to_uuid(getattr(p, "id")),
                    vector=list(getattr(p, "vector")),
                    properties={"payload": json.dumps(payload)},
                )

    def count(self, collection_name: str, **kwargs: Any) -> _CountResult:
        client = self._connect()
        col = client.collections.get(collection_name)
        try:
            result = col.aggregate.over_all(total_count=True)
            n = int(getattr(result, "total_count", 0))
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

        # normalise() first so compound filters raise NotImplementedError
        # before we touch the weaviate import (keeps the rejection path
        # working in test envs that don't have weaviate installed).
        normalised = _vector_filter.normalise(query_filter)
        weaviate_filter = _vector_filter.to_weaviate_filter(normalised)

        from weaviate.classes.query import MetadataQuery

        client = self._connect()
        col = client.collections.get(collection_name)
        near_vector_kwargs: Dict[str, Any] = {
            "near_vector": list(query_vector),
            "limit": limit,
            "return_metadata": MetadataQuery(distance=True),
        }
        if weaviate_filter is not None:
            near_vector_kwargs["filters"] = weaviate_filter
        res = col.query.near_vector(**near_vector_kwargs)
        hits: List[_SearchHit] = []
        for obj in res.objects:
            dist = float(getattr(obj.metadata, "distance", 0.0) or 0.0)
            score = 1.0 - dist
            if score_threshold is not None and score < score_threshold:
                continue
            payload_raw = obj.properties.get("payload") if hasattr(obj.properties, "get") else None
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else (payload_raw or {})
            except Exception:
                payload = {}
            hits.append(_SearchHit(id=str(obj.uuid), score=score, payload=payload))
        return hits

    def delete(
        self,
        collection_name: str,
        points_selector: Any = None,
        **kwargs: Any,
    ) -> None:
        if points_selector is None:
            return

        # Shape 1: list-like of IDs
        if isinstance(points_selector, (list, tuple)):
            if not points_selector:
                return
            client = self._connect()
            col = client.collections.get(collection_name)
            for pid in points_selector:
                col.data.delete_by_id(_to_uuid(pid))
            return

        if hasattr(points_selector, "points") and not hasattr(points_selector, "filter"):
            client = self._connect()
            col = client.collections.get(collection_name)
            for pid in points_selector.points:
                col.data.delete_by_id(_to_uuid(pid))
            return

        # Shape 2: FilterSelector. All the validation happens BEFORE
        # we touch weaviate so unsupported shapes don't require the
        # weaviate package to be installed.
        filt = getattr(points_selector, "filter", None)
        if filt is None:
            raise NotImplementedError(
                f"weaviate adapter: unsupported delete selector shape "
                f"{type(points_selector).__name__!r}."
            )

        must = list(getattr(filt, "must", []) or [])
        should = list(getattr(filt, "should", []) or [])
        must_not = list(getattr(filt, "must_not", []) or [])
        if should or must_not or len(must) != 1:
            raise NotImplementedError(
                "weaviate adapter: delete() supports only a single must "
                "FieldCondition."
            )
        cond = must[0]
        key = getattr(cond, "key", None)
        match = getattr(cond, "match", None)
        value = getattr(match, "value", None) if match is not None else None
        if key is None or value is None:
            raise NotImplementedError(
                "weaviate adapter: delete() FieldCondition must expose "
                ".key and .match.value."
            )

        # Now we know we're going to use weaviate; import it.
        from weaviate.classes.query import Filter as WFilter

        client = self._connect()
        col = client.collections.get(collection_name)
        marker = f'"{key}": "{value}"'
        col.data.delete_many(
            where=WFilter.by_property("payload").like(f"*{marker}*"),
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
) -> _WeaviateClient:
    """Create a Weaviate v4 client.

    Env-var fallbacks: WEAVIATE_HOST / WEAVIATE_PORT / WEAVIATE_API_KEY.
    """
    h = host or os.getenv("WEAVIATE_HOST", "localhost")
    p = port or int(os.getenv("WEAVIATE_PORT", "8080"))
    k = api_key if api_key is not None else os.getenv("WEAVIATE_API_KEY")
    return _WeaviateClient(h, p, k)
