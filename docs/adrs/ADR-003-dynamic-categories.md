# ADR-003: Dynamic Memory Categories (No Hardcoded Enums)

**Status:** Accepted
**Date:** 2026-01-22
**Deciders:** RNR Enhanced Cognee maintainers

---

## Context

The original implementation defined a Python enum to classify memories by project:

    class MemoryCategory(Enum):
        ATS = "ats"
        OMA = "oma"
        SMC = "smc"

All ingestion paths validated the category parameter against this enum. Any value
not in the list raised a ValueError and rejected the memory.

This design originated from the first project that used RNR Enhanced Cognee, which had
three subsystems: Algorithmic Trading System (ATS), Order Management Agent (OMA),
and Signal Management Component (SMC). When a second, unrelated project tried to
use RNR Enhanced Cognee with categories relevant to its own domain, every add_memory
call failed validation.

Phase 6 of the development plan (purge hardcoded ats/oma/smc from legacy src/
files) identified 23 call sites across the codebase where these three strings
appeared as literal values or enum comparisons.

---

## Decision

Memory categories are user-defined strings. The system does not maintain a closed
list of valid category names and does not validate the category parameter against
any enum or whitelist.

Category prefixes (used to namespace Qdrant collections and PostgreSQL partitions)
are loaded at startup from .enhanced-cognee-config.json in the project root, or
from environment variables as a fallback. If a category appears in a memory that
has no entry in the config file, a default prefix derived from the category name
is used.

Example configuration file:

    {
      "categories": {
        "trading": { "prefix": "trading_" },
        "development": { "prefix": "dev_" },
        "analysis": { "prefix": "analysis_" }
      }
    }

No code outside of .enhanced-cognee-config.json may contain the strings "ats",
"oma", or "smc" except in comments that explain the historical context.

---

## Consequences

**Positive**
- RNR Enhanced Cognee works for any project without code changes.
- Adding a new category requires only a config file edit, not a code change and
  redeploy.
- The system cannot silently miscategorize a memory due to an enum mismatch.
- Future projects do not inherit category names from earlier projects.

**Negative**
- Without validation, typos in category names create new, unintended categories.
  Operators should audit categories periodically using the list_data MCP tool.
- Some database tooling that relied on the fixed set of three Qdrant collections
  must be updated to query collections dynamically.

---

## Alternatives Considered

**Enum with extensible registration**
Allow external code to call MemoryCategory.register("my_category") at startup.
Rejected because it still requires code execution (not just config) to add a
category and imposes a startup ordering constraint.

**Schema-validated category list in a database table**
Store valid categories in a PostgreSQL table; validate each ingestion call against
it. Rejected because it adds a database round-trip to every write and makes the
server unusable if the category table has not been pre-populated.
