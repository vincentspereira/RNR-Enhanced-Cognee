# Enhanced Cognee — License Audit

Comprehensive review of every third-party component shipped with or runtime
required by Enhanced Cognee. Goal: zero license risk for self-hosted personal
or commercial use, including future monetisation.

**Audit date:** 2026-05-18 (revised 2026-05-19 -- Phase 2 ArcadeDB swap + Phase 4 SigNoz/Superset swap)
**Enhanced Cognee license:** Apache-2.0 (permissive, commercial-friendly)

> **Status (after Phase 4 ship 2026-05-19):** the entire default
> Enhanced Cognee deployment -- main 4-DB stack AND the optional
> monitoring stack -- is 100% MIT + Apache-2.0 / permissive. The
> previous Grafana / Loki / Tempo (AGPLv3) components have been
> removed; Neo4j (GPLv3) is retained as an opt-in legacy alternative
> behind `ENHANCED_GRAPH_PROVIDER=neo4j`. See `docs/PROFILES.md` and
> `docs/MONITORING.md`.

## TL;DR

| Component | License | Compatible with Apache-2.0? | Action Taken |
|---|---|---|---|
| PostgreSQL + pgvector | PostgreSQL (BSD-like) | YES | Keep |
| Qdrant | Apache-2.0 | YES | Keep |
| **ArcadeDB** (new default 2026-05-19) | **Apache-2.0** | YES | **Replaced Neo4j as default** |
| Neo4j Community Edition (legacy alternative) | GPLv3 | **CONDITIONAL** | Document; opt-in via `ENHANCED_GRAPH_PROVIDER=neo4j` |
| **Redis** | **BSL/SSPL since 7.4, AGPLv3 since 8.0** | **NO — restrictive** | **REPLACED with Valkey 8 (Apache-2.0)** |
| Python runtime | PSF License | YES | Keep |
| All Python pip packages | Various permissive (Apache/MIT/BSD/PSF) | YES | Keep (audited below) |
| Docker | Apache-2.0 | YES | Keep |
| Caddy | Apache-2.0 | YES | Keep |
| Prometheus | Apache-2.0 | YES | Keep (optional monitoring stack) |
| SigNoz / ClickHouse / Apache Superset (new in Phase 4) | MIT / Apache-2.0 / Apache-2.0 | YES | Default optional monitoring stack since 2026-05-19 |
| ~~Grafana / Loki / Tempo / Jaeger~~ (removed Phase 4) | AGPLv3 / AGPLv3 / AGPLv3 / Apache-2.0 | n/a | Removed 2026-05-19 -- see docs/MONITORING.md migration steps |

## Detailed Database License Analysis

### 1. PostgreSQL + pgvector — KEEP (no risk)

- **PostgreSQL:** PostgreSQL License (BSD-style permissive)
- **pgvector:** PostgreSQL License
- **Verdict:** Perfectly compatible. Commercial use, redistribution, modification
  all permitted with attribution. No copyleft.

### 2. Qdrant — KEEP (no risk)

- **License:** Apache-2.0
- **Verdict:** Perfectly compatible. Same license as Enhanced Cognee. Commercial
  use unrestricted.

### 3. ArcadeDB — KEEP (default graph DB since 2026-05-19; Phase 2)

- **License:** Apache-2.0
- **Verdict:** Perfectly compatible. Commercial use unrestricted, no copyleft.
  Replaced Neo4j Community as the default graph DB to remove the GPLv3
  asterisk from the stack. Bolt-protocol-compatible with the existing
  `neo4j` Python driver, so no code changes were required beyond the
  Phase 1 factory routing.
- **Migration guide:** [`docs/ARCADEDB_MIGRATION.md`](./ARCADEDB_MIGRATION.md).

### 3b. Neo4j Community Edition — LEGACY ALTERNATIVE (opt-in)

- **License:** GPLv3 (Community Edition); commercial license for Enterprise
- **Status (since 2026-05-19):** No longer the default. Available via
  `ENHANCED_GRAPH_PROVIDER=neo4j`. The compose file ships ArcadeDB; users
  who opt in to Neo4j add the snippet from
  [`docs/ARCADEDB_MIGRATION.md` §3.3](./ARCADEDB_MIGRATION.md#33-keep-using-neo4j-instead).
- **The concern:** GPLv3 is copyleft. If you *distribute* Neo4j as part of your
  application binary or container image, you may need to release your own code
  under GPL-compatible terms.
- **What's actually OK:**
  - **Running Neo4j as a separate service** (which we do via Docker) — no
    copyleft obligation on Enhanced Cognee's own code. This is the "mere
    aggregation" + "network service" pattern.
  - **Connecting via the network protocol (Bolt)** — no copyleft obligation.
  - **Self-hosted personal use** — no concern at all.
  - **Self-hosted commercial SaaS** — no concern at all, because you're not
    redistributing Neo4j to end users.
- **What would NOT be OK:**
  - Embedding Neo4j's Java JAR directly into your binary distribution
  - Forking Neo4j source and shipping derivative code under a non-GPL license
  - Reselling Neo4j Community as if it were your own product

**Verdict:** Safe for the network-service deployment model. Phase 2 removed
this asterisk from the *default* stack -- users who keep Neo4j explicitly
take on the conditional handling described above.

### 4. Redis — REPLACED with Valkey

#### Why Redis became a problem

- **Redis 7.4:** Switched to dual-license **BSL 1.1 + SSPL** (March 2024).
  - BSL is "source-available" but NOT open-source by OSI definition.
  - SSPL is explicitly non-free (Mongo's license that triggered the Valkey fork).
- **Redis 8.0:** Re-added AGPLv3 as an option (May 2025). AGPLv3 is open-source
  but heavily copyleft — any service exposing AGPL software over a network must
  share its full source code.
- **For an Apache-2.0 project like Enhanced Cognee:**
  - Self-hosted use: OK under any of the above (we're not distributing Redis).
  - Commercial SaaS use under SSPL: would require open-sourcing your entire
    service stack (per SSPL §13).
  - Distributing Enhanced Cognee with bundled Redis: license incompatibility.

#### Why Valkey is the right choice

- **License:** Apache-2.0 (same as Enhanced Cognee — zero friction)
- **Fork point:** Redis 7.2.4 (before the license change), maintained by The
  Linux Foundation under the Valkey project.
- **API compatibility:** 100% wire-protocol compatible with Redis. The
  `redis-py` Python client works without any code change.
- **Backers:** AWS, Google, Oracle, Ericsson, Snap — substantial corporate support.
- **Maturity:** Valkey 8.0 (released Sep 2024) outperforms Redis 7.4 on most
  benchmarks; Valkey 8.1 (Apr 2025) adds further improvements.
- **Migration cost:** **swap one Docker image line, restart container.**

#### What changed in Enhanced Cognee for this migration

1. `docker/docker-compose-enhanced-cognee.yml`: `redis:7.4-alpine` →
   `valkey/valkey:8-alpine`
2. `docker/docker-compose-production.yml`: same image swap
3. Container name `redis-enhanced-cognee` → `valkey-enhanced-cognee` (cosmetic)
4. Healthcheck `redis-cli ping` → `valkey-cli ping` (both binaries exist in
   Valkey image)
5. No Python code changes (redis-py talks to Valkey transparently)
6. No environment variable renames (REDIS_HOST etc. still apply; the env vars
   are just names — they could be VALKEY_HOST but keeping REDIS_* avoids
   breakage in users' existing configs)
7. Documentation updated to mention Valkey alongside Redis

**Verdict:** Migration complete. Apache-2.0 throughout. Zero functional change.

## Python Dependencies License Audit

All top-level pip dependencies and key transitive deps:

| Package | Version | License | Compatible? |
|---|---|---|---|
| anthropic | 0.97.0 | Apache-2.0 | YES |
| argon2-cffi | 23.1.0 | MIT | YES |
| asyncpg | 0.31.0 | Apache-2.0 | YES |
| cryptography | 46.0.4 | Apache-2.0 / BSD dual | YES |
| fastapi | 0.135.3 | MIT | YES |
| fastapi-users | 14.0.1 | MIT | YES |
| httpx | 0.28.1 | BSD-3-Clause | YES |
| litellm | 1.81.7 | MIT | YES |
| neo4j (Python driver) | 6.1.0 | Apache-2.0 | YES |
| openai (Python SDK) | 2.16.0 | Apache-2.0 | YES |
| passlib | 1.7.4 | BSD-2-Clause | YES |
| pgvector (Python) | 0.4.2 | MIT | YES |
| prometheus_client | 0.24.1 | Apache-2.0 | YES |
| psycopg2 | 2.9.11 | LGPL | YES (we use the binary release; LGPL is OK as long as users can replace the lib) |
| pytest + plugins | 9.0.2 | MIT | YES |
| qdrant-client | 1.16.2 | Apache-2.0 | YES |
| redis (Python client) | 7.1.0 | MIT | YES (this is the client library; it still works with Valkey) |
| SQLAlchemy | 2.0.46 | MIT | YES |
| uvicorn | various | BSD | YES |

**Verdict:** Every Python dependency uses a permissive license compatible with
Apache-2.0. No GPL or copyleft contamination in our dependency graph.

## Monitoring Stack (optional)

| Component | License | Notes |
|---|---|---|
| Prometheus | Apache-2.0 | Fully compatible |
| Grafana OSS | AGPLv3 (since 2021) | Run as a service (we do) — no copyleft on Enhanced Cognee. Only an issue if you redistribute Grafana embedded in your product. |
| Loki | AGPLv3 | Same as Grafana — service-only model means no copyleft on us. |
| Promtail | Apache-2.0 | Fully compatible |
| Jaeger | Apache-2.0 | Fully compatible (added in OpenTelemetry guide) |

**Mitigation for AGPL components:** the monitoring stack ships as a *separate*
`monitoring/docker-compose-monitoring.yml` that operators bring up themselves.
Enhanced Cognee doesn't bundle Grafana or Loki in any distributable artefact;
we just provide configuration templates. AGPL obligations apply to the operator
of Grafana/Loki, not to Enhanced Cognee.

If you want a pure-Apache monitoring stack:
- Replace Grafana with **VictoriaMetrics' vmui** (Apache-2.0) — limited but functional
- Replace Loki with **VictoriaLogs** (Apache-2.0) — protocol compatible

These are not the default because Grafana/Loki are vastly more popular and
better documented. Operators can swap if their compliance requires it.

## Neo4j Alternatives (for the truly copyleft-averse)

If GPLv3 Neo4j is unacceptable for your deployment, drop-in alternatives:

| Alternative | License | Compatibility | Migration cost |
|---|---|---|---|
| **Memgraph Community** | BSL 1.1 (4-year delay to Apache) | Cypher-compatible | Low |
| **ArangoDB Community** | Apache-2.0 | AQL query language (not Cypher) | Medium (rewrite queries) |
| **Kuzu** | MIT | Cypher-compatible, embedded | Low (but embedded model differs) |
| **TigerGraph Community** | Free tier license | GSQL (not Cypher) | High |
| **Apache AGE on PostgreSQL** | Apache-2.0 | openCypher | Low if already using Postgres |

**Recommendation:** **Apache AGE on PostgreSQL** is the most attractive long-term
swap. It runs *inside* our existing pgvector Postgres instance — eliminates a
database, reduces operational burden, and is fully Apache-2.0. The cost is a
medium-effort code change to swap the Neo4j driver for AGE-flavoured Cypher.

This is **not** done in this migration — Neo4j stays because the GPL concern is
theoretical for our self-hosted model. Documented as a future optimisation.

## Compliance Status

For each license that imposes requirements, here is our compliance:

### Apache-2.0 (Enhanced Cognee itself + most deps)

- [x] LICENSE file at repo root contains Apache-2.0 text
- [x] NOTICE file lists all Apache-2.0 components (now created)
- [x] Each Apache-2.0 dep's copyright notice preserved in source (via pip's
      auto-installed metadata)
- [x] Modifications to Apache-2.0 code (none — we use everything unmodified)
      are documented

### MIT (BSD-3 / BSD-2 / PSF) — most other deps

- [x] License text and copyright preserved (pip metadata)
- [x] No additional obligations beyond attribution

### LGPL (psycopg2)

- [x] We link dynamically (the standard pip install) — LGPL allows this
- [x] Users can replace `psycopg2` with `psycopg2-binary` or build from source
      — no shipped binary modification

### GPLv3 (Neo4j Community)

- [x] Run Neo4j as a separate network service (Docker container) — no copyleft
      obligation on Enhanced Cognee
- [x] Use Neo4j's Apache-2.0 Bolt Python driver — no GPL contamination
- [x] Do not redistribute Neo4j binaries inside Enhanced Cognee artefacts
- [x] Document this in `docs/LICENSE_AUDIT.md` (this file)

### PostgreSQL License

- [x] License text preserved (Postgres ships with it)
- [x] Attribution maintained in our README

## NOTICE File

A `NOTICE` file at the repo root lists all third-party components. The pip
ecosystem already preserves individual package licenses inside `site-packages/`,
but consolidating them in `NOTICE` is a good practice for Apache-2.0 distros.

See `NOTICE` (created by this migration).

## Action Items Completed

- [x] Replace Redis with Valkey 8 in both Docker compose files
- [x] Update Docker container names (cosmetic)
- [x] Update healthcheck commands (`redis-cli` → `valkey-cli`)
- [x] Document the migration in this audit file
- [x] Add `NOTICE` file at repo root listing all components
- [x] Update README to mention Valkey
- [x] Verify the change doesn't break anything (`make smoke` post-swap)

## Action Items Deferred

- [ ] **Migrate Neo4j to Apache AGE on PostgreSQL** — significant code change,
      no immediate license risk; queued for a future sprint
- [ ] **Swap Grafana/Loki for VictoriaMetrics/VictoriaLogs** — only if a future
      customer requires pure-Apache monitoring; not blocking
- [ ] **Wire automated SBOM (Software Bill of Materials) generation** into CI —
      e.g. `pip-licenses` or `cyclonedx-py` running on every release
- [ ] **Run an SBOM scan and publish at each release** — useful for downstream
      consumers' compliance teams

## Summary

Enhanced Cognee is now **100% free for personal and commercial use**, including
future SaaS monetisation, with the following caveats:

1. **Neo4j GPLv3:** Safe in our self-hosted-service deployment model. Not safe
   if you embed Neo4j JARs in a distributable binary.
2. **Grafana/Loki AGPLv3:** Safe because they're optional, separate-stack, and
   not redistributed by Enhanced Cognee.
3. **All other components:** Permissive licenses, zero restrictions.

The Redis → Valkey swap eliminates the largest license risk that existed prior
to this audit.

## See also

- [`FEATURE_LICENSE_MATRIX.md`](FEATURE_LICENSE_MATRIX.md) -- per-feature view of the same licensing data, organised by what feature you are about to port into a downstream project (e.g. the user's Multi-Agent System / MAS). Cross-references this file for the per-dependency analysis.
- [`COMMERCIALISATION_LICENSE_GUIDE.md`](COMMERCIALISATION_LICENSE_GUIDE.md) -- if you ever ship Enhanced Cognee itself as a paid product.
- [`PROFILES.md`](PROFILES.md) -- per-profile adapter matrix and caveats.
