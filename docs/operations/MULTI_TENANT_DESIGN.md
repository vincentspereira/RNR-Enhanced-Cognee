# Multi-Tenant Design for Enhanced Cognee

**Status:** Design only (Phase F3, deferred from initial launch)
**Per Q2 in PRODUCTION_READINESS_PLAN.md:** "agent decides on tenant definition"

## Tenant Definition

A **tenant** in Enhanced Cognee is **one customer organisation** (or one paying
human if self-serve). Each tenant gets:

- An isolated namespace for memories (schema-level in Postgres, collection-prefix
  in Qdrant, node-label in Neo4j, key-prefix in Redis)
- Its own per-agent identity space (so two tenants can both have a `trading-bot`
  agent without collision)
- Its own quota for LLM cost, storage, API calls
- Its own audit log (segregated from other tenants for compliance)
- Optional its own encryption key (Phase F-extended)

This maps cleanly to a B2B SaaS model: one tenant = one customer = one billing
account. Within a tenant, multiple human users / agents share the same data pool.

## Architecture

```
+-----------------------------------------------------------+
|              Enhanced Cognee Multi-Tenant                 |
+-----------------------------------------------------------+
|  +-------------+  +-------------+  +-------------+        |
|  |  Tenant A   |  |  Tenant B   |  |  Tenant C   |  ...   |
|  |  (acme.io)  |  |  (foo.dev)  |  | (bar.org)   |        |
|  +------+------+  +------+------+  +------+------+        |
|         |                |                |               |
|         v                v                v               |
|  +---------------------------------------------------+    |
|  |        Tenant Middleware (resolves tenant_id      |    |
|  |        from JWT / API key / header)               |    |
|  +---------------------+-----------------------------+    |
|                        |                                  |
+------------------------+----------------------------------+
                         |
       +-----------------+-----------------+
       |                                   |
       v                                   v
+----------------+                +----------------+
|   Postgres     |                |    Qdrant      |
|  schema-per-   |                |  collection-   |
|     tenant     |                |   per-tenant   |
+----------------+                +----------------+
       |                                   |
       v                                   v
+----------------+                +----------------+
|     Neo4j      |                |    Redis       |
|   tenant-id    |                |  key-prefix    |
|   node label   |                |    tenant:     |
+----------------+                +----------------+
```

## New MCP Tools

Four tools to add (would bring total from 122 to **126**):

### `create_tenant`

```
create_tenant(
    tenant_name: str,         # human-readable name (e.g. "ACME Corp")
    tenant_id: str,           # short slug (e.g. "acme") used in storage keys
    admin_email: str,         # owner contact
    plan: str = "free",       # free | pro | enterprise
    metadata: dict = None,
) -> dict
```

- Creates `shared_memory_<tenant_id>` schema in Postgres
- Creates `enhanced_<tenant_id>_*` collections in Qdrant on-demand
- Adds tenant_id label to all new Neo4j nodes
- Reserves `tenant:<tenant_id>:` key prefix in Redis
- Returns dict with API key for tenant admin to use

**Trigger Type:** M (manual — billing operation)

### `list_tenants`

```
list_tenants(include_disabled: bool = False) -> list[dict]
```

- Returns one row per tenant: id, name, plan, storage_used, memory_count, last_active
- Restricted to super-admin (a special internal agent_id)

**Trigger Type:** A (auto — admin dashboard refresh)

### `delete_tenant`

```
delete_tenant(
    tenant_id: str,
    confirm_delete_data: bool = False,
) -> dict
```

- DESTRUCTIVE: drops the tenant's Postgres schema, Qdrant collections,
  Neo4j nodes (with `tenant_id=...` label), Redis keys with the prefix
- Requires `confirm_delete_data=True` as a safety guard
- Triggers GDPR-style deletion audit log

**Trigger Type:** M (manual — irreversible)

### `get_tenant_stats`

```
get_tenant_stats(
    tenant_id: str = None,    # None = all tenants (super-admin only)
) -> dict
```

- Returns per-tenant: memory count, storage bytes, recent activity, LLM cost,
  quota utilisation
- Used by dashboards + alerting

**Trigger Type:** S (system — periodic snapshot)

## Implementation Steps (when this is built)

1. **Add `tenant_id` resolution middleware** to the MCP server (FastAPI variant
   only — stdio variant is single-tenant by definition)
   - Extracts tenant from JWT `tenant` claim or `X-Tenant-ID` header
   - Stores in request context for the duration of the request
   - All DB queries are then auto-scoped via thread-local or contextvar

2. **Schema-per-tenant in Postgres:**
   ```sql
   CREATE SCHEMA IF NOT EXISTS shared_memory_<tenant_id>;
   -- Rest of the DDL mirrors shared_memory but inside the tenant's schema
   ```

3. **Collection-prefix in Qdrant:**
   ```python
   collection_name = f"enhanced_{tenant_id}_{category}"
   ```

4. **Neo4j label segregation:**
   ```cypher
   CREATE (m:Memory:Tenant_<tenant_id> {id: $id, ...})
   ```
   Then queries are scoped via `MATCH (m:Memory:Tenant_<tenant_id>) ...`

5. **Redis key prefix:**
   ```python
   redis_key = f"tenant:{tenant_id}:{actual_key}"
   ```

6. **Per-tenant quotas** in `automation_config.json`:
   ```json
   {
     "tenants": {
       "acme": {"max_memories": 100000, "max_llm_cost_usd_per_month": 50},
       "foo":  {"max_memories": 10000,  "max_llm_cost_usd_per_month": 10}
     }
   }
   ```

7. **Migration path for single-tenant deployments:**
   - Add a `__default__` tenant on first startup
   - Migrate existing `shared_memory` schema to `shared_memory___default__`
   - Existing API calls continue to work (auto-resolve to default tenant)

## Storage Cost Implications

Going multi-tenant adds:

- One schema per tenant in Postgres (~negligible — schemas are free)
- One Qdrant collection per (tenant, category) pair — minor overhead
- Neo4j labels are free
- Redis prefix is free

**Total overhead:** approximately 5% storage growth for the cross-tenant index
structures. Worth it for the isolation guarantees.

## Security Considerations

- **Tenant ID injection:** all tenant IDs must be validated against a strict
  regex (`^[a-z0-9_]{3,32}$`) to prevent SQL injection via schema names
- **Cross-tenant queries:** explicitly forbidden; `gdpr_verify_tenant_isolation`
  (already shipped) periodically scans for leaks
- **API key scoping:** each tenant's API key only resolves their tenant_id; no
  shared keys
- **Audit log per tenant:** each tenant sees only their own audit entries

## When to Build This

Build multi-tenant when:
- You have 2+ paying customers
- You need formal SOC 2 / GDPR compliance with isolation guarantees
- You're monetising the deployment

Until then, single-tenant deployment is simpler and just as functional.
