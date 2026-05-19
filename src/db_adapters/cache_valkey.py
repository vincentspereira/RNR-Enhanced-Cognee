"""Valkey cache adapter.

Valkey is wire-compatible with Redis and uses the same Python client
(`redis-py`), so this adapter and `cache_redis.py` share the same
implementation. The split exists so that ENHANCED_CACHE_PROVIDER=valkey
and ENHANCED_CACHE_PROVIDER=redis route to distinct labelled adapters.

Lazy-imports the redis module so test patches against
``redis.asyncio.Redis`` or ``redis.Redis`` (or sys.modules) still apply.
"""

from __future__ import annotations

import os
from typing import Any, Optional


def create_async_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: bool = True,
    **kwargs: Any,
):
    """Create an async Valkey/Redis client. Falls back to REDIS_* env vars.

    The constructor is synchronous; the connection pool initialises
    lazily on the first command (or eagerly via ``await client``).
    """
    import redis.asyncio as aioredis

    host = host or os.getenv("REDIS_HOST", "localhost")
    port = port or int(os.getenv("REDIS_PORT", "26379"))
    if password is None:
        password = os.getenv("REDIS_PASSWORD") or None
    return aioredis.Redis(
        host=host,
        port=port,
        password=password,
        decode_responses=decode_responses,
        **kwargs,
    )


def create_sync_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: bool = True,
    **kwargs: Any,
):
    """Create a sync Valkey/Redis client. Falls back to REDIS_* env vars."""
    import redis as sync_redis

    host = host or os.getenv("REDIS_HOST", "localhost")
    port = port or int(os.getenv("REDIS_PORT", "26379"))
    if password is None:
        password = os.getenv("REDIS_PASSWORD") or None
    return sync_redis.Redis(
        host=host,
        port=port,
        password=password,
        decode_responses=decode_responses,
        **kwargs,
    )
