"""ChromaDB adapter (Phase 5 vector pluggable).

ChromaDB (https://www.trychroma.com/) is an Apache-2.0 vector store
with native collection semantics that map naturally onto Qdrant's.
Supports both an in-process ``PersistentClient`` (filesystem-backed)
and a network ``HttpClient`` -- this adapter picks based on whether
``CHROMA_HOST`` is set.

This adapter mirrors the same narrow ``QdrantClient`` surface that
the other Phase 5 vector adapters ship. Chroma's API is structurally
closer to Qdrant than LanceDB / pgvector, so the implementation is
shorter -- mostly straight pass-throughs.

**Supported (covers every method our call sites use):**

- ``get_collections()`` / ``get_collection(name)`` / ``count(name)``
- ``create_collection(name, vectors_config=VectorParams(size, distance))``
- ``upsert(name, points=[PointStruct(id, vector, payload)])``
- ``search(name, query_vector, limit, score_threshold)``
- ``delete(name, points_selector)`` accepting:
    * plain list / tuple of IDs
    * ``FilterSelector(filter=Filter(must=[FieldCondition(key, match=MatchValue(value))]))``
      with a single ``must`` FieldCondition

**Not supported (raises NotImplementedError):**

- Rich ``query_filter`` in search (Chroma supports ``where=...`` but
  the qdrant Filter -> Chroma where translation is non-trivial)
- Multi-condition / nested / negation delete filters

Env-var fallbacks:
  - Network mode if ``CHROMA_HOST`` is set: ``CHROMA_HOST`` /
    ``CHROMA_PORT`` (default 8000)
  - Otherwise persistent in-process mode at ``CHROMA_PATH``
    (default ``./chroma_data``)
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Sequence


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


_DISTANCE_TO_CHROMA = {
    "cosine": "cosine",
    "euclid": "l2",
    "dot": "ip",
}


def _distance_to_chroma_metric(distance: Any) -> str:
    name = str(distance).rsplit(".", 1)[-1].lower()
    return _DISTANCE_TO_CHROMA.get(name, "cosine")


class _ChromaClient:
    """QdrantClient-shaped wrapper around a ChromaDB client."""

    def __init__(
        self,
        host: Optional[str],
        port: Optional[int],
        path: str,
    ) -> None:
        self._host = host
        self._port = port
        self._path = path
        self._client: Any = None

    def _connect(self):
        if self._client is None:
            import chromadb

            if self._host:
                self._client = chromadb.HttpClient(
                    host=self._host, port=self._port or 8000
                )
            else:
                self._client = chromadb.PersistentClient(path=self._path)
        return self._client

    def get_collections(self) -> _CollectionsResult:
        client = self._connect()
        try:
            cols = client.list_collections()
        except Exception:
            cols = []
        # Chroma returns Collection objects with .name
        names = [getattr(c, "name", str(c)) for c in cols]
        return _CollectionsResult([_CollectionDescription(n) for n in names])

    def get_collection(self, collection_name: str) -> _CollectionInfo:
        client = self._connect()
        try:
            client.get_collection(name=collection_name)
        except Exception as exc:
            raise RuntimeError(
                f"chroma adapter: collection {collection_name!r} not found"
            ) from exc
        return _CollectionInfo()

    def create_collection(
        self, collection_name: str, vectors_config: Any, **kwargs: Any
    ) -> None:
        client = self._connect()
        distance = getattr(vectors_config, "distance", None)
        metric = _distance_to_chroma_metric(distance)
        client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": metric}
        )

    def upsert(
        self, collection_name: str, points: Sequence[Any], **kwargs: Any
    ) -> None:
        client = self._connect()
        col = client.get_collection(name=collection_name)
        ids, vectors, payloads = [], [], []
        for p in points:
            ids.append(str(getattr(p, "id")))
            vectors.append(list(getattr(p, "vector")))
            payloads.append(getattr(p, "payload", {}) or {})
        if not ids:
            return
        col.upsert(ids=ids, embeddings=vectors, metadatas=payloads)

    def count(self, collection_name: str, **kwargs: Any) -> _CountResult:
        client = self._connect()
        col = client.get_collection(name=collection_name)
        return _CountResult(int(col.count()))

    def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        query_filter: Any = None,
        **kwargs: Any,
    ) -> List[_SearchHit]:
        if query_filter is not None:
            raise NotImplementedError(
                "chroma adapter: query_filter is not yet wired through "
                "the qdrant Filter -> chroma where-clause translator. "
                "Filter at the application layer."
            )
        client = self._connect()
        col = client.get_collection(name=collection_name)
        results = col.query(
            query_embeddings=[list(query_vector)],
            n_results=limit,
        )
        # Chroma returns lists keyed by query index; we sent 1 query so
        # we read index 0.
        ids = (results.get("ids") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]

        hits: List[_SearchHit] = []
        for hit_id, dist, meta in zip(ids, distances, metadatas):
            # Chroma returns *distance* (smaller better); normalise.
            score = 1.0 - float(dist)
            if score_threshold is not None and score < score_threshold:
                continue
            hits.append(_SearchHit(id=hit_id, score=score, payload=meta or {}))
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
        col = client.get_collection(name=collection_name)

        if isinstance(points_selector, (list, tuple)):
            if not points_selector:
                return
            col.delete(ids=[str(i) for i in points_selector])
            return

        if hasattr(points_selector, "points") and not hasattr(points_selector, "filter"):
            col.delete(ids=[str(i) for i in points_selector.points])
            return

        filt = getattr(points_selector, "filter", None)
        if filt is None:
            raise NotImplementedError(
                f"chroma adapter: unsupported delete selector shape "
                f"{type(points_selector).__name__!r}."
            )

        must = list(getattr(filt, "must", []) or [])
        should = list(getattr(filt, "should", []) or [])
        must_not = list(getattr(filt, "must_not", []) or [])
        if should or must_not or len(must) != 1:
            raise NotImplementedError(
                "chroma adapter: delete() supports only a single must "
                "FieldCondition."
            )
        cond = must[0]
        key = getattr(cond, "key", None)
        match = getattr(cond, "match", None)
        value = getattr(match, "value", None) if match is not None else None
        if key is None or value is None:
            raise NotImplementedError(
                "chroma adapter: delete() FieldCondition must expose "
                ".key and .match.value."
            )
        col.delete(where={key: value})

    def close(self) -> None:
        self._client = None


def create_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    **kwargs: Any,
) -> _ChromaClient:
    """Create a Chroma client. Network mode if CHROMA_HOST set, else
    persistent in-process mode at CHROMA_PATH.
    """
    chroma_host = host or os.getenv("CHROMA_HOST")
    chroma_port = port or (int(os.getenv("CHROMA_PORT", "8000")) if chroma_host else None)
    chroma_path = os.getenv("CHROMA_PATH", "./chroma_data")
    return _ChromaClient(chroma_host, chroma_port, chroma_path)
