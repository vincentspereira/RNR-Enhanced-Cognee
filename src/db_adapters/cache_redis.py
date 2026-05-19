"""Redis cache adapter (wire-compatible alias for the Valkey adapter)."""

from __future__ import annotations

from src.db_adapters.cache_valkey import (
    create_async_client,
    create_sync_client,
)

__all__ = ["create_async_client", "create_sync_client"]
