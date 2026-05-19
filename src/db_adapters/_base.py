"""Adapter contracts for pluggable DB providers.

Phase 1 keeps the surface area minimal: each tier's adapter returns the
underlying driver/client object that callers already expect (asyncpg pool,
QdrantClient, neo4j Driver, redis.asyncio.Redis). The Protocol classes
below document the minimal interface each returned object must satisfy.

This lets us swap providers (e.g. Neo4j -> ArcadeDB in Phase 2) without
forcing every call site through a fat translation layer. Providers that
share a wire protocol (Valkey/Redis, ArcadeDB/Neo4j Bolt) are drop-in.
Providers that diverge (e.g. ApacheAGE) can return a shim object that
exposes the same Protocol surface.
"""

from __future__ import annotations

from typing import Any, AsyncContextManager, ContextManager, Protocol, runtime_checkable


@runtime_checkable
class RelationalPoolLike(Protocol):
    """asyncpg.Pool-compatible interface."""

    def acquire(self) -> AsyncContextManager[Any]: ...

    async def close(self) -> None: ...


@runtime_checkable
class VectorClientLike(Protocol):
    """qdrant_client.QdrantClient-compatible interface."""

    def get_collections(self) -> Any: ...

    def get_collection(self, collection_name: str) -> Any: ...


@runtime_checkable
class GraphDriverLike(Protocol):
    """neo4j.Driver-compatible interface (sync)."""

    def session(self, *args: Any, **kwargs: Any) -> ContextManager[Any]: ...

    def close(self) -> None: ...


@runtime_checkable
class AsyncGraphDriverLike(Protocol):
    """neo4j.AsyncDriver-compatible interface (async)."""

    def session(self, *args: Any, **kwargs: Any) -> AsyncContextManager[Any]: ...

    async def close(self) -> None: ...


@runtime_checkable
class CacheClientLike(Protocol):
    """redis.asyncio.Redis / valkey-compatible interface."""

    async def ping(self) -> Any: ...

    async def close(self) -> None: ...
