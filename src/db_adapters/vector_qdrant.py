"""Qdrant vector adapter.

Lazy-imports ``qdrant_client`` so callers patching it via ``sys.modules``
or class-level patches still receive their mock.
"""

from __future__ import annotations

import os
import warnings
from typing import Any, Optional


def create_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    prefer_grpc: bool = False,
    check_compatibility: bool = False,
    timeout: Optional[int] = None,
    **kwargs: Any,
):
    """Create a QdrantClient. Falls back to QDRANT_* env vars.

    If `url` is provided, it takes precedence over host/port (matches
    existing usage in bin/enhanced_cognee_mcp_server.py).
    """
    from qdrant_client import QdrantClient

    if url is None:
        host = host or os.getenv("QDRANT_HOST", "localhost")
        port = port or int(os.getenv("QDRANT_PORT", "26333"))
    api_key = api_key if api_key is not None else os.getenv("QDRANT_API_KEY")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if url is not None:
            return QdrantClient(
                url=url,
                api_key=api_key,
                check_compatibility=check_compatibility,
                **kwargs,
            )
        if timeout is not None:
            return QdrantClient(
                host=host,
                port=port,
                api_key=api_key,
                prefer_grpc=prefer_grpc,
                check_compatibility=check_compatibility,
                timeout=timeout,
                **kwargs,
            )
        return QdrantClient(
            host=host,
            port=port,
            api_key=api_key,
            prefer_grpc=prefer_grpc,
            check_compatibility=check_compatibility,
            **kwargs,
        )
