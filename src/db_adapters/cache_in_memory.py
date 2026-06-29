"""In-memory cache adapter (no external dependency).

Exposes the minimum subset of the ``redis.asyncio.Redis`` API surface
that RNR Enhanced Cognee call sites use today (``ping`` / ``get`` / ``set``
/ ``delete`` / ``close``). Suitable for the ``lean`` deployment profile
(see ``docs/PROFILES.md``) and for tests that need a cache stand-in
without an external service.

Not a full Redis API. If a call site needs more (pub/sub, sorted sets,
hash tables, expiry, etc.) the caller should select a real cache
provider via ``ENHANCED_CACHE_PROVIDER=valkey`` / ``redis`` instead.

Thread-/async-safety: not designed for high concurrency. Backed by a
plain dict guarded by an ``asyncio.Lock``. Single-process deployments
only.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional


class _InMemoryAsyncClient:
    """``redis.asyncio.Redis``-shaped wrapper around a dict."""

    def __init__(self, *, decode_responses: bool = True) -> None:
        self._store: dict = {}
        self._expiry: dict = {}
        self._lock = asyncio.Lock()
        self._decode_responses = decode_responses

    async def ping(self) -> bool:
        return True

    def _expired(self, key: str) -> bool:
        exp = self._expiry.get(key)
        return exp is not None and exp < time.monotonic()

    def _maybe_decode(self, value: Any) -> Any:
        if value is None:
            return None
        if self._decode_responses and isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8")
        return value

    async def get(self, key: str) -> Any:
        async with self._lock:
            if self._expired(key):
                self._store.pop(key, None)
                self._expiry.pop(key, None)
                return None
            return self._maybe_decode(self._store.get(key))

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        **kwargs: Any,
    ) -> bool:
        async with self._lock:
            self._store[key] = value
            if ex is not None:
                self._expiry[key] = time.monotonic() + ex
            else:
                self._expiry.pop(key, None)
            return True

    async def delete(self, *keys: str) -> int:
        async with self._lock:
            removed = 0
            for k in keys:
                if k in self._store:
                    self._store.pop(k, None)
                    self._expiry.pop(k, None)
                    removed += 1
            return removed

    async def exists(self, *keys: str) -> int:
        async with self._lock:
            return sum(
                1 for k in keys if k in self._store and not self._expired(k)
            )

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            if key not in self._store:
                return False
            self._expiry[key] = time.monotonic() + seconds
            return True

    async def keys(self, pattern: str = "*") -> list:
        async with self._lock:
            if pattern == "*":
                return [self._maybe_decode(k) for k in self._store]
            import fnmatch

            return [
                self._maybe_decode(k)
                for k in self._store
                if fnmatch.fnmatchcase(k, pattern)
            ]

    async def flushdb(self) -> bool:
        async with self._lock:
            self._store.clear()
            self._expiry.clear()
            return True

    async def close(self) -> None:
        # Nothing to release; dict GCs with the client.
        return None

    # Allow ``await client`` so callers that follow the redis-py pattern of
    # eagerly resolving the connection do not break.
    def __await__(self):
        async def _self():
            return self

        return _self().__await__()


def create_async_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: bool = True,
    **kwargs: Any,
) -> _InMemoryAsyncClient:
    """Create an in-memory async cache client.

    Connection-shaped kwargs (``host`` / ``port`` / ``password``) are
    accepted for API compatibility with the redis/valkey adapter but
    have no effect; everything lives in process memory.
    """
    return _InMemoryAsyncClient(decode_responses=decode_responses)


def create_sync_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: bool = True,
    **kwargs: Any,
) -> _InMemoryAsyncClient:
    """Sync clients fall through to the async-shaped class.

    The async client's methods are coroutines, so a strictly-sync caller
    would still need to ``asyncio.run`` them; this is acceptable for the
    in-memory profile where no real I/O happens. Callers that need a
    blocking redis-py-style sync client should pick the ``valkey`` or
    ``redis`` provider instead.
    """
    return _InMemoryAsyncClient(decode_responses=decode_responses)
