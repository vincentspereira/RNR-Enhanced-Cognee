"""Memcached cache adapter (Phase 5 pluggable).

Memcached is a BSD-licensed in-memory K/V store. It has a fundamentally
narrower API than Redis -- no sorted sets, no hash tables, no pub/sub,
no key enumeration. This adapter exposes the small subset of the
``redis.asyncio.Redis`` surface that Enhanced Cognee actually uses
(``ping`` / ``get`` / ``set`` / ``delete`` / ``exists`` / ``expire`` /
``close``), wrapping ``pymemcache`` and running the sync calls via
``asyncio.to_thread`` so the async contract holds.

**Not supported (raises NotImplementedError):**

- ``keys(pattern)`` -- memcached intentionally does not expose key
  enumeration; this is a design choice rooted in their cache-eviction
  model and is not implementable on the client side.
- ``flushdb()`` -- intentional. Memcached's ``flush_all`` wipes the
  *entire* server (not just one DB), which is too dangerous to expose
  through the same API name. Use ``client._client.flush_all()`` if you
  really mean it.
- Pub/sub. Memcached has none.

Env-var fallbacks: ``MEMCACHED_HOST`` (default ``localhost``),
``MEMCACHED_PORT`` (default ``11211``). Authentication via SASL is
not wired -- if you need it, see ``pymemcache.client.base.Client``
constructor args and pass them through ``**kwargs``.

Install with::

    pip install enhanced-cognee[cache-memcached]
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional


class _MemcachedAsyncClient:
    """Narrow ``redis.asyncio.Redis``-shape over pymemcache."""

    def __init__(self, *, host: str, port: int, decode_responses: bool) -> None:
        from pymemcache.client.base import Client as _PMC

        self._client = _PMC((host, port), connect_timeout=5, timeout=5)
        self._decode_responses = decode_responses

    async def ping(self) -> bool:
        # pymemcache has no ping; `version()` is the canonical liveness probe
        version = await asyncio.to_thread(self._client.version)
        return version is not None

    async def get(self, key: str) -> Any:
        value = await asyncio.to_thread(self._client.get, key)
        if value is None:
            return None
        if self._decode_responses and isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8")
        return value

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        **kwargs: Any,
    ) -> bool:
        if isinstance(value, str):
            value = value.encode("utf-8")
        return await asyncio.to_thread(
            self._client.set, key, value, expire=ex or 0
        )

    async def delete(self, *keys: str) -> int:
        removed = 0
        for k in keys:
            ok = await asyncio.to_thread(self._client.delete, k)
            if ok:
                removed += 1
        return removed

    async def exists(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if await self.get(k) is not None:
                count += 1
        return count

    async def expire(self, key: str, seconds: int) -> bool:
        # pymemcache's touch() updates the expiry without changing the value
        return await asyncio.to_thread(self._client.touch, key, expire=seconds)

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)

    async def keys(self, pattern: str = "*") -> list:
        raise NotImplementedError(
            "memcached intentionally does not expose key enumeration. "
            "If you need keys(), pick ENHANCED_CACHE_PROVIDER=valkey / "
            "redis / in_memory instead."
        )

    async def flushdb(self) -> bool:
        raise NotImplementedError(
            "flushdb() is not wired for memcached because flush_all() "
            "wipes the *entire* server. If that's what you mean, call "
            "client._client.flush_all() directly."
        )

    def __await__(self):
        # Eager-init compat with the redis-py pattern.
        async def _self():
            return self

        return _self().__await__()


def create_async_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: bool = True,
    **kwargs: Any,
) -> _MemcachedAsyncClient:
    """Create an async-shaped memcached client.

    ``password`` is accepted for API compatibility but ignored --
    memcached SASL is not wired (use kwargs to pass through to
    pymemcache if you need it).
    """
    host = host or os.getenv("MEMCACHED_HOST", "localhost")
    port = port or int(os.getenv("MEMCACHED_PORT", "11211"))
    return _MemcachedAsyncClient(
        host=host, port=port, decode_responses=decode_responses
    )


def create_sync_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: bool = True,
    **kwargs: Any,
) -> _MemcachedAsyncClient:
    """Sync path -- returns the same async-shape client.

    The methods are coroutines either way; a strictly-sync caller
    would need ``asyncio.run`` to drive them. For a true blocking
    sync cache, pick ``valkey`` / ``redis`` providers instead.
    """
    return create_async_client(
        host=host,
        port=port,
        password=password,
        decode_responses=decode_responses,
        **kwargs,
    )
