# ADR-005: Graceful Degradation for All Optional Components

**Status:** Accepted
**Date:** 2026-02-05
**Deciders:** Enhanced Cognee maintainers

---

## Context

The full Enhanced Cognee stack requires four running Docker containers. During
development and in lightweight deployments, a contributor may want to run only
PostgreSQL (the primary store) without Qdrant, Neo4j, or Redis. A data analyst
may run Qdrant and PostgreSQL but not Neo4j. A CI environment may have none of
the databases and rely only on the SQLite lite mode.

In early Phase 9 development, the MCP server raised an unhandled ImportError or
ConnectionRefusedError during startup if any of the four databases was unreachable.
The entire server exited before any tool was callable. Users saw no helpful
message; the MCP client simply reported "server failed to start".

This made local development painful: developers running a single database for
focused work had to start all four containers or edit the source before the server
would run.

---

## Decision

Every module introduced in Phases 9 through 12 that connects to an optional
component must follow this pattern:

1. Wrap the connection attempt in a try/except block inside __init__ or a
   dedicated async initialise() method.
2. On failure, log a [WARN] message that names the component and explains which
   tools will be unavailable.
3. Set the connection attribute to None.
4. In every method that uses the connection, check for None first and return an
   [ERR] string describing the missing dependency rather than raising an exception.
5. Never raise an unhandled exception during server startup due to a missing
   optional component.

The health MCP tool reports the status of each component individually using
[OK] or [FAIL], so operators can see at a glance which components are online.

Example pattern:

    class MemoryVersioner:
        def __init__(self, postgres_pool):
            self.pool = postgres_pool  # None is valid

        async def get_history(self, memory_id):
            if not self.pool:
                return "[ERR] Versioning unavailable: PostgreSQL not connected"
            ...

---

## Consequences

**Positive**
- The MCP server starts successfully even when only one or zero databases are
  reachable.
- Developers can work on PostgreSQL-only features without running the full stack.
- The health tool gives operators a precise picture of what is and is not working.
- Partial availability is preferable to complete unavailability for most use cases.

**Negative**
- Callers receive [ERR] strings from some tools instead of expected data. Callers
  must handle this case rather than assuming a successful response means valid data.
- The degraded-mode code paths receive less test coverage in CI environments that
  do not start all four databases.

---

## Alternatives Considered

**Hard dependency on all four databases**
Fail fast at startup if any database is unreachable. Rejected because it blocks
all development workflows that do not require every component.

**Startup gate check**
Add a preflight script that checks all connections before launching the server, and
refuse to start if any check fails. Rejected for the same reason as hard dependency,
and because it prevents starting in a partial configuration for read-only tools that
do not need every database.
