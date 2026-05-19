"""Neo4j graph adapter (sync and async).

Phase 1 default. Will become a pluggable alternative when ArcadeDB takes
over as the default graph DB in Phase 2 (HANDOVER section 4 Phase 2,
STRATEGY.md DR-11).

Lazy-imports ``neo4j`` so callers patching ``sys.modules['neo4j']`` (test
pattern in tests/unit/test_backup_manager.py and test_recovery_manager.py)
still receive their mock.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple


def _resolve_auth(
    uri: Optional[str],
    user: Optional[str],
    password: Optional[str],
) -> Tuple[str, Tuple[str, str]]:
    uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:27687")
    user = user or os.getenv("NEO4J_USER", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD", "cognee_password")
    return uri, (user, password)


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create a sync neo4j.Driver. Falls back to NEO4J_* env vars."""
    from neo4j import GraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return GraphDatabase.driver(resolved_uri, auth=auth, **kwargs)


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create an async neo4j.AsyncDriver. Falls back to NEO4J_* env vars."""
    from neo4j import AsyncGraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return AsyncGraphDatabase.driver(resolved_uri, auth=auth, **kwargs)
