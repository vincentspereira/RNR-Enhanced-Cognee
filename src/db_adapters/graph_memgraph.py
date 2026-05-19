"""Memgraph graph adapter (Phase 5 pluggable).

Memgraph (https://memgraph.com/) is a Bolt-protocol-compatible graph
database. The ``neo4j`` Python driver works against it unchanged, so
this adapter is structurally identical to ``graph_arcadedb.py`` and
``graph_neo4j.py`` -- only the default URI / user / password differ.

License note: Memgraph is BSL 1.1 (Business Source License) with a
4-year delay to Apache-2.0. **This is not OSI-permissive today.** Use
this adapter only if you have an internal-use deployment where BSL is
acceptable, or if you're past the BSL change-date of the version you
run. For commercially-distributable Apache-2.0 stack, prefer
``arcadedb`` (default) or ``apache_age``.

Env-var fallbacks: ``MEMGRAPH_URI`` (default ``bolt://localhost:7687``
-- Memgraph's standard port; note this differs from our ArcadeDB
27687-on-host default), ``MEMGRAPH_USER`` (default empty string;
Memgraph allows passwordless by default), ``MEMGRAPH_PASSWORD``
(default empty string).

Lazy-imports ``neo4j`` so test patches against ``sys.modules['neo4j']``
or ``neo4j.GraphDatabase.driver`` keep working.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple


def _resolve_auth(
    uri: Optional[str],
    user: Optional[str],
    password: Optional[str],
) -> Tuple[str, Tuple[str, str]]:
    uri = uri or os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
    user = user if user is not None else os.getenv("MEMGRAPH_USER", "")
    password = (
        password if password is not None else os.getenv("MEMGRAPH_PASSWORD", "")
    )
    return uri, (user, password)


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create a sync neo4j.Driver pointing at Memgraph's Bolt endpoint."""
    from neo4j import GraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return GraphDatabase.driver(resolved_uri, auth=auth, **kwargs)


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create an async neo4j.AsyncDriver pointing at Memgraph's Bolt endpoint."""
    from neo4j import AsyncGraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return AsyncGraphDatabase.driver(resolved_uri, auth=auth, **kwargs)
