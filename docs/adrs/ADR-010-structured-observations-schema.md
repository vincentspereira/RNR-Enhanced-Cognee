# ADR-010: Structured Observations as Entity-Attribute-Value Triples

**Status:** Accepted
**Date:** 2026-05-14
**Deciders:** RNR Enhanced Cognee maintainers

---

## Context

RNR Enhanced Cognee stores two kinds of knowledge: unstructured full-text memories
(free-form text in shared_memory.documents) and structured facts extracted from
those memories by the extract_graph_v2 tool (e.g., "Paris is the capital of
France", "User prefers dark mode").

Structured facts were previously stored in two ways:
1. As JSON inside the document's metadata JSONB column (quick but hard to query).
2. As nodes and edges in Neo4j (queryable but requires a running Neo4j instance;
   not available in PostgreSQL-only deployments per ADR-005).

Neither approach supports simple, efficient PostgreSQL-side queries like "give me
all known attributes of the entity 'Paris'" or "detect conflicts where the same
entity has two different values for the same attribute".

As the project adds the check_duplicate, auto_deduplicate, and regex_extract_entities
tools in Phase 11, a queryable, indexed table for structured observations is needed
that works without Neo4j.

---

## Decision

Add a new table, shared_memory.observations, to the PostgreSQL schema. Each row
represents one structured fact as an Entity-Attribute-Value (EAV) triple:

    CREATE TABLE shared_memory.observations (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        memory_id       UUID NOT NULL REFERENCES shared_memory.documents(id)
                            ON DELETE CASCADE,
        agent_id        TEXT NOT NULL,
        entity          TEXT NOT NULL,
        attribute       TEXT NOT NULL,
        value           TEXT NOT NULL,
        confidence      FLOAT NOT NULL DEFAULT 0.5,
        source_tool     TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Fast lookup by entity
    CREATE INDEX ix_observations_entity
        ON shared_memory.observations (agent_id, entity);

    -- Fast lookup by entity + attribute
    CREATE INDEX ix_observations_entity_attr
        ON shared_memory.observations (agent_id, entity, attribute);

    -- Conflict detection: an entity can have at most one value per attribute
    -- per agent. Enforced at the application layer; the unique index accelerates
    -- the duplicate check.
    CREATE UNIQUE INDEX ux_observations_entity_attr_agent
        ON shared_memory.observations (agent_id, entity, attribute);

The unique index on (agent_id, entity, attribute) enforces the invariant that each
agent holds at most one value per attribute per entity. Conflict detection queries:

    -- Does this observation conflict with an existing one?
    SELECT value FROM shared_memory.observations
    WHERE agent_id = $1 AND entity = $2 AND attribute = $3;

    -- If a row is returned and value != $4, a conflict exists.

The observations table is introduced via an Alembic migration (see RB-010 for
migration failure recovery). The migration script is:

    alembic_enhanced/versions/0012_add_observations_table.py

Observations are populated by the extract_graph_v2 and regex_extract_entities MCP
tools. They are queried by the check_duplicate and auto_deduplicate tools. The
add_observations MCP tool allows callers to insert observations directly.

Neo4j is still used for graph traversal (relationships between entities, multi-hop
queries). The observations table serves as the PostgreSQL-resident, queryable store
of flat facts. The two stores are not kept in strict sync; they serve different
query patterns.

---

## Consequences

**Positive**
- Structured facts are queryable with simple SQL (SELECT by entity, SELECT by
  entity + attribute) without graph traversal or JSON path expressions.
- The unique index on (agent_id, entity, attribute) makes conflict detection a
  single indexed lookup rather than a full-table scan.
- The ON DELETE CASCADE foreign key ensures that deleting a document (e.g., for
  GDPR erasure) automatically deletes all observations derived from it.
- Observations work in PostgreSQL-only deployments (ADR-005 graceful degradation),
  providing structured fact storage even when Neo4j is offline.
- EAV rows are cheap to store and fast to query by entity and attribute; the schema
  is stable regardless of how many attribute types are added.

**Negative**
- A new Alembic migration is required. Existing deployments must run
  RNR-Enhanced-Cognee migrate upgrade head before the Phase 11 tools are usable.
  See RB-010 for migration failure recovery.
- EAV schemas are considered an anti-pattern in relational database design when
  the set of attributes is fixed and known in advance, because wide typed tables
  are more efficient. RNR Enhanced Cognee's observation attributes are open-ended
  (any entity, any attribute), so EAV is appropriate here, but developers must be
  aware that the value column is always TEXT and type coercion is the application's
  responsibility.
- The unique index on (agent_id, entity, attribute) means that a second fact about
  the same entity and attribute from a different source replaces the first rather
  than coexisting. This is a deliberate design choice (single authoritative value
  per attribute per agent) but may surprise callers who expect to store multiple
  values for the same attribute (e.g., multiple phone numbers for one entity).
  Multi-value attributes must be modeled as separate attribute names
  (e.g., "phone_1", "phone_2") or as a JSON array in the value column.

---

## Alternatives Considered

**Storing EAV inside document metadata JSONB**
Keep structured facts in the existing metadata JSONB column of shared_memory.documents.
Rejected because JSONB path queries (jsonb_path_query) are more complex than simple
indexed SELECT statements, GIN indexes on JSONB are larger and slower to build than
B-tree indexes on text columns, and conflict detection requires a non-trivial JSONB
containment check.

**Using Neo4j as the sole store for structured observations**
Store all structured facts exclusively as graph nodes and edges in Neo4j. Rejected
because Neo4j is an optional component (ADR-005) and cannot be the only store for
data that the check_duplicate and auto_deduplicate tools need during degraded
operation. Additionally, Neo4j Cypher queries are less familiar to contributors who
know SQL.

**RDF triples with a SPARQL endpoint**
Model facts as RDF subject-predicate-object triples and query them with SPARQL.
Rejected because RDF libraries for Python are large and complex (rdflib, Apache
Jena), SPARQL is unfamiliar to most contributors, and the added expressiveness of
full RDF (namespaces, ontologies, inference) is not needed for the simple fact
storage use case. EAV in PostgreSQL achieves the same result with no new libraries.

**Wide table with typed columns**
Create a separate table for each observation type (e.g., observations_location,
observations_preference). Rejected because the set of observation attribute types
is open-ended and grows as new extraction tools are added. Adding a new table for
each attribute type requires a schema migration per attribute, which is operationally
burdensome.
