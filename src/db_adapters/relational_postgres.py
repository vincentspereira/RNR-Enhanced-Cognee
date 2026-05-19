"""Postgres relational adapter (asyncpg).

Lazy-imports ``asyncpg`` so callers patching ``asyncpg.create_pool``
(test pattern in tests/unit/test_agent_memory_integration.py and
test_enhanced_cognee_mcp.py) still receive their mock.
"""

from __future__ import annotations

import os
from typing import Any, Optional


async def create_pool(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    min_size: int = 5,
    max_size: int = 20,
    **kwargs: Any,
):
    """Create an asyncpg pool. Falls back to POSTGRES_* env vars."""
    import asyncpg

    host = host or os.getenv("POSTGRES_HOST", "localhost")
    port = port or int(os.getenv("POSTGRES_PORT", "25432"))
    database = database or os.getenv("POSTGRES_DB", "cognee_db")
    user = user or os.getenv("POSTGRES_USER", "cognee_user")
    password = password or os.getenv("POSTGRES_PASSWORD", "cognee_password")
    return await asyncpg.create_pool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        min_size=min_size,
        max_size=max_size,
        **kwargs,
    )
