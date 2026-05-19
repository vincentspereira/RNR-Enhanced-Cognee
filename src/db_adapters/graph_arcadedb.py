"""ArcadeDB graph adapter (Phase 2 default).

ArcadeDB (https://arcadedb.com) is a multi-model database with an
openCypher implementation and a Bolt protocol that is wire-compatible
with Neo4j. This means we can talk to ArcadeDB using the same Python
``neo4j`` driver we already depend on -- no extra dependency required.

The Bolt plugin must be enabled in the ArcadeDB server JVM options; see
``docs/ARCADEDB_MIGRATION.md`` for the docker-compose snippet. Defaults
in this adapter assume the ``docker/docker-compose-enhanced-cognee.yml``
service exposes Bolt on host port 27687 (same external port we used
for Neo4j; drop-in for existing NEO4J_URI=bolt://localhost:27687 setups
that migrate by flipping ENHANCED_GRAPH_PROVIDER alone).

Env-var fallbacks (in order):
    ARCADEDB_URI       (default ``bolt://localhost:27687``)
    ARCADEDB_USER      (default ``root`` -- ArcadeDB's built-in admin)
    ARCADEDB_PASSWORD  (default ``cognee_password`` to match Neo4j)

For backwards compat, callers that still pass ``NEO4J_*`` env vars are
respected via explicit kwargs from the call site -- the adapter only
reads its own ARCADEDB_* env vars when the caller does not override.

Lazy-imports ``neo4j`` so tests patching ``sys.modules['neo4j']`` or
``neo4j.GraphDatabase.driver`` still apply.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple


def _resolve_auth(
    uri: Optional[str],
    user: Optional[str],
    password: Optional[str],
) -> Tuple[str, Tuple[str, str]]:
    uri = uri or os.getenv("ARCADEDB_URI", "bolt://localhost:27687")
    user = user or os.getenv("ARCADEDB_USER", "root")
    password = password or os.getenv("ARCADEDB_PASSWORD", "cognee_password")
    return uri, (user, password)


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create a sync neo4j.Driver pointing at ArcadeDB's Bolt endpoint.

    Falls back to ARCADEDB_* env vars when args are omitted.
    """
    from neo4j import GraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return GraphDatabase.driver(resolved_uri, auth=auth, **kwargs)


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create an async neo4j.AsyncDriver pointing at ArcadeDB's Bolt endpoint."""
    from neo4j import AsyncGraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return AsyncGraphDatabase.driver(resolved_uri, auth=auth, **kwargs)
