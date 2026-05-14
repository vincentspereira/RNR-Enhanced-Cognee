# ADR-001: Use Four-Database Stack (PostgreSQL + Qdrant + Neo4j + Redis)

**Status:** Accepted
**Date:** 2026-01-15
**Deciders:** Enhanced Cognee maintainers

---

## Context

The Enhanced Cognee MCP server must support four distinct memory operations:

- Persistent, relational storage of memory documents with full SQL query capability
- Vector similarity search for semantic recall across large memory sets
- Graph-based relationship traversal between memory entities, agents, and concepts
- Low-latency caching for hot data and session state

A single database cannot excel at all four. Early prototypes using only PostgreSQL with
the pgvector extension showed adequate vector search performance at small scale but
degraded noticeably beyond 50,000 vectors. Graph traversal queries against a relational
schema were verbose and slow. Redis was absent, meaning every repeated query hit the
primary database.

Additionally, the project runs alongside other services on the same developer machine.
Standard ports (5432, 6333, 7687, 6379) are frequently occupied by upstream Cognee or
other tools.

---

## Decision

Use all four databases, each assigned to its optimal role:

| Database   | Role                              | Port  |
|------------|-----------------------------------|-------|
| PostgreSQL | Relational store, audit log, GDPR | 25432 |
| Qdrant     | Vector similarity search          | 26333 |
| Neo4j      | Knowledge graph, entity links     | 27687 |
| Redis      | Cache, session state, TTL keys    | 26379 |

Non-standard ports in the 25000-27000 range are chosen to avoid collisions with any
service using default ports. All port values are configurable via environment variables
(POSTGRES_PORT, QDRANT_PORT, NEO4J_PORT, REDIS_PORT).

---

## Consequences

**Positive**
- Each database handles exactly what it was designed for.
- PostgreSQL provides ACID guarantees and row-level security for GDPR compliance.
- Qdrant handles semantic search at scale without degrading relational queries.
- Neo4j enables rich graph queries that would require many joins in SQL.
- Redis reduces latency for repeated lookups by an order of magnitude.
- Non-standard ports eliminate conflicts with common developer tooling.

**Negative**
- Operators must run and monitor four Docker containers instead of one.
- Backup and restore procedures must cover all four stores (see RB-003).
- Database-specific connection failures require per-service degradation logic
  (addressed by ADR-005).
- Higher memory footprint on the host machine.

---

## Alternatives Considered

**Single PostgreSQL with pgvector only**
Simpler operationally. pgvector handles vector search adequately for small datasets.
Rejected because graph traversal performance is poor in SQL and there is no caching
layer.

**Single Redis for everything**
Redis supports both key-value and vector search (via RediSearch/RedisVL). Rejected
because Redis is an in-memory store with limited durability guarantees and does not
support complex relational queries or ACID transactions required for GDPR audit logs.
