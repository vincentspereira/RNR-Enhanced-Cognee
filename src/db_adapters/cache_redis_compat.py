"""Redis-compatible cache adapter (Phase 5 alias).

Labelled alias for any wire-compatible Redis fork or workalike (KeyDB,
Garnet, Dragonfly, etc.) that speaks the Redis protocol. Routes
through the same redis-py-backed implementation as ``cache_valkey``,
since they all answer the same wire commands.

The reason this exists as a *separate* labelled provider rather than
just being another `redis` alias: it signals **operational intent**
in the env vars. A deployment setting `ENHANCED_CACHE_PROVIDER=redis_compat`
is communicating "this isn't real Redis OR Valkey, it's a third-party
fork; please don't assume Redis 7.x licence terms or Valkey-specific
behaviour." That's useful documentation for the next operator who
looks at the stack.

The Python `redis` client library treats all four (Redis / Valkey /
KeyDB / Garnet / Dragonfly) identically because they all implement
RESP2/RESP3, so no separate Python dep is needed.

Env-var fallbacks: identical to ``cache_valkey`` -- ``REDIS_HOST`` /
``REDIS_PORT`` / ``REDIS_PASSWORD``. (We don't introduce a separate
``REDIS_COMPAT_*`` env-var family because in practice the operator
points the env var at whichever fork they actually run.)
"""

from __future__ import annotations

from src.db_adapters.cache_valkey import (
    create_async_client,
    create_sync_client,
)

__all__ = ["create_async_client", "create_sync_client"]
