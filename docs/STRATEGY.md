# Enhanced Cognee — Consolidated Strategy Document

**Audience:** maintainers, technical evaluators, future commercial customers, MAS integrators.
**Supersedes / collates:** PLUGGABLE_DB_BACKENDS.md, OUTSTANDING_ITEMS.md, LICENSE_AUDIT.md,
DEPLOYMENT_QUICKSTART.md, COMMERCIALISATION_LICENSE_GUIDE.md, COMPARE_TO_ALTERNATIVES.md.
The original six files remain in `docs/` for deep-dive reference; this one is the single
source of truth for **what we're doing, why, and what's next**.

**Last updated:** 2026-05-19

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Where Enhanced Cognee Fits in the Market](#2-where-enhanced-cognee-fits-in-the-market)
3. [License & Commercialisation Risk Map](#3-license--commercialisation-risk-map)
4. [Pluggable Database Backends — Final Design](#4-pluggable-database-backends--final-design)
5. [Component-by-Component Alternatives Analysis](#5-component-by-component-alternatives-analysis)
   - 5.1 [Graph Database (Neo4j alternatives)](#51-graph-database-neo4j-alternatives)
   - 5.2 [Observability / Dashboards (Grafana alternatives)](#52-observability--dashboards-grafana-alternatives)
   - 5.3 [Log Aggregation (Loki alternatives)](#53-log-aggregation-loki-alternatives)
6. [Deployment Paths](#6-deployment-paths)
7. [Outstanding Items & Gap Analysis](#7-outstanding-items--gap-analysis)
8. [Recommended 12-Week Roadmap](#8-recommended-12-week-roadmap)
9. [Appendix: Decision Records](#9-appendix-decision-records)

---

## 1. Executive Summary

Enhanced Cognee is a fork of upstream `topoteretes/cognee` that adds:

- 122 MCP tools (vs upstream's 0 — upstream is REST-only)
- 4-database stack (PostgreSQL + Qdrant + Neo4j + Valkey) vs upstream's single-DB
- Multi-language, GDPR, audit, undo/redo, encryption, importance scoring
- 4,158 passing tests, 95% coverage, zero failures, zero skipped, zero warnings

**License posture (current, after Phase 4 ship 2026-05-19):** 100% MIT +
Apache-2.0 / permissive across both the default main stack AND the
optional monitoring stack. ArcadeDB replaced Neo4j as the default graph
DB (Neo4j retained as opt-in via `ENHANCED_GRAPH_PROVIDER=neo4j`);
SigNoz + Apache Superset + Prometheus replaced Grafana + Loki + Tempo +
Jaeger. No AGPL, no GPL in the default deployment.

**Recommended next moves (in priority order):**

| #   | Action                                                                    | Effort    | Driver                                                                            |
| --- | ------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------------------- |
| 1   | Ship Phase 1 pluggable DB plumbing (env var routing) -- **SHIPPED 2026-05-19** | 1 week    | Removes lock-in, enables BYO infra for enterprise prospects                       |
| 2   | Swap default graph DB Neo4j -> **ArcadeDB** -- **SHIPPED 2026-05-19**       | 1-2 weeks | Apache-2.0 multi-model engine, Cypher + Bolt drop-in                              |
| 3   | Add **Apache AGE** as a pluggable graph option                            | 1 week    | Apache-2.0 Postgres extension; "one fewer container" path                         |
| 4   | Replace Grafana + Loki + Tempo + Jaeger with **SigNoz (MIT) + Apache Superset (Apache-2.0)**; keep Prometheus -- **SHIPPED 2026-05-19** | 1-2 weeks | Eliminates the AGPL-3.0 components in the optional monitoring stack; 100% permissive licensing |
| 5   | Wire integration tests against live stack in CI                           | 3 hours   | Catches DB-driver regressions before main                                         |
| 6   | MAS integration sprint                                                    | 1-2 weeks | Delivers user-facing value                                                        |
| 7   | Document **HyperDX (MIT)** as alternative to SigNoz                       | 2 hours   | Different UX style; same MIT licence at app layer (caveat: bundled MongoDB is SSPL — see §5.2) |

Items 1-5 are essentially mandatory before commercial sale. Items 6-7 are
strongly recommended for any customer-facing release.

---

## 2. Where Enhanced Cognee Fits in the Market

### When to choose us

- You want **all 4 storage tiers** (relational + vector + graph + cache) without
  cobbling them together yourself.
- You need **MCP tool access** from Claude Code, Cursor, Copilot, or any other
  MCP-compatible IDE — without writing a custom server.
- You're running an **agent fleet** (trading bot, SDLC agent, analysis agent)
  and need per-agent memory segregation, cross-agent sharing, and audit trails.
- You care about **GDPR compliance** (right to erasure, consent records,
  tenant isolation) out of the box.
- You want **self-hostable, free-software** infrastructure without vendor lock-in.

### When NOT to choose us

- You want a **single Python import** and an in-process dict — use LangChain Memory.
- You don't want to run Docker at all — use Mem0's hosted SaaS.
- You need **just** semantic search over a static document corpus — use Qdrant directly.
- You need **stateful agents with built-in workflow orchestration** — try Letta.
- Your use case is **research / experimentation** where production-grade is overkill.

### One-table comparison

| If you need...                                                   | Use                        |
| ---------------------------------------------------------------- | -------------------------- |
| Production-grade, multi-database memory layer with 122 MCP tools | **Enhanced Cognee**        |
| Lightweight Cognee with single-DB setup, no enterprise features  | Cognee (upstream)          |
| Hosted memory-as-a-service with no ops burden                    | Mem0                       |
| Long-term memory for chat agents with temporal knowledge graphs  | Zep (Apache-2.0)           |
| Stateful agent platform with built-in workflows                  | Letta (formerly MemGPT)    |
| Document-corpus retrieval with memory                            | LlamaIndex                 |
| In-process Python memory for prototyping                         | LangChain Memory           |
| Pure semantic search over a vector corpus (no graph, no agents)  | Qdrant / Weaviate / Chroma |

A full side-by-side feature matrix lives in [`COMPARE_TO_ALTERNATIVES.md`](./COMPARE_TO_ALTERNATIVES.md).

---

## 3. License & Commercialisation Risk Map

### Risk by component

| Component                  | License            | Self-host commercial | Bundled-product distribution | SaaS commercial |
| -------------------------- | ------------------ | -------------------- | ---------------------------- | --------------- |
| Enhanced Cognee (own code) | Apache-2.0         | OK                   | OK                           | OK              |
| Cognee (upstream)          | Apache-2.0         | OK                   | OK                           | OK              |
| PostgreSQL + pgvector      | PostgreSQL         | OK                   | OK                           | OK              |
| Qdrant                     | Apache-2.0         | OK                   | OK                           | OK              |
| Valkey                     | Apache-2.0         | OK                   | OK                           | OK              |
| Python pip deps (~50)      | Apache/MIT/BSD/PSF | OK                   | OK                           | OK              |
| Caddy                      | Apache-2.0         | OK                   | OK                           | OK              |
| **Neo4j Community**        | **GPLv3**          | OK                   | **CAUTION**                  | OK              |
| **Grafana / Loki**         | **AGPLv3**         | OK                   | **CAUTION**                  | **CAUTION**     |
| psycopg2                   | LGPL               | OK                   | OK                           | OK              |

### Scenarios

1. **You sell SaaS** (you host, customers use): **No issues.** Network-service
   model means GPL/AGPL distribution obligations never trigger.
2. **You sell self-hosted with support contracts**: **No issues.** Customer
   pulls their own Neo4j/Grafana images; you ship configuration only.
3. **You distribute a packaged product** (tarball, custom Docker image):
   - 3a. Ship Compose files, customer pulls their own images → **Safe.**
   - 3b. Bundle Neo4j JARs in your installer → **Triggers GPLv3 obligations.** Avoid.
   - 3c. Switch to Apache AGE on PostgreSQL → **Cleanest.** Recommended for
        purely Apache-2.0 distros.
4. **You embed Enhanced Cognee inside MAS** (or any other parent product):
   - 4a. Import as Python library → unrestricted.
   - 4b. MAS shells out to MCP server → unrestricted.
   - 4c. Vendored copy → unrestricted, preserve LICENSE + NOTICE.
5. **MAS-with-Enhanced-Cognee as closed-source commercial product**:
   Safe under Apache-2.0; apply Scenario-3 rules for Neo4j and Scenario-1
   rules for Grafana/Loki (keep them optional + separate compose file).

### Quick FAQ

- **Sell support contracts?** Yes (Apache-2.0 explicit).
- **Rename to "MyCompany Memory Platform" and sell?** Yes, preserve LICENSE and NOTICE.
- **Keep my modifications private?** Yes (Apache has no copyleft).
- **Bundle inside proprietary closed-source agent framework?** Yes (don't bundle
  Neo4j JARs or Grafana binaries).
- **Remove all GPL/AGPL components?** Yes — use the Apache AGE + SigNoz +
  VictoriaLogs swap detailed in §5 below.
- **Publish my source code?** Never required.

For the long-form rationale and the legal-review checklist, see
[`COMMERCIALISATION_LICENSE_GUIDE.md`](./COMMERCIALISATION_LICENSE_GUIDE.md)
and [`LICENSE_AUDIT.md`](./LICENSE_AUDIT.md).

---

## 4. Pluggable Database Backends — Final Design

**Decision:** Add pluggability **gradually** via env-var routing on top of the
existing 4-database default stack. Default behaviour is unchanged; new behaviour
is opt-in.

### 4.1 Three-tier architecture

#### Tier 1 — Production default (unchanged)

`docker compose -f docker/docker-compose-enhanced-cognee.yml up -d` continues
to ship the validated 4-DB stack:

```
PostgreSQL 18 + pgvector   (port 25432)
Qdrant 1.12.0              (port 26333)
ArcadeDB latest            (port 27687 Bolt, 22480 Studio HTTP) -- default since Phase 2 ship 2026-05-19
Valkey 8                   (port 26379)
```

Neo4j Community is retained as an opt-in alternative
(`ENHANCED_GRAPH_PROVIDER=neo4j`) for legacy users; see
[`docs/ARCADEDB_MIGRATION.md`](./ARCADEDB_MIGRATION.md) for the swap details.
This guarantees zero regression for existing users while removing GPLv3 from
the default stack.

#### Tier 2 — Env-var override

```bash
# Relational
ENHANCED_RELATIONAL_PROVIDER=postgres   # default; alternative: sqlite (testing/lean only)

# Vector
ENHANCED_VECTOR_PROVIDER=qdrant         # default; alternatives: pgvector, lancedb,
                                        # weaviate, milvus, chroma

# Graph - new default (revised 2026-05-19 per maintainer decision)
ENHANCED_GRAPH_PROVIDER=arcadedb        # NEW DEFAULT (Apache-2.0, multi-model with
                                        # Cypher + Bolt = Neo4j drop-in compatibility)
                                        # alternatives:
                                        #   neo4j               (GPLv3, kept for legacy compat)
                                        #   apache_age          (Apache-2.0, Postgres extension)
                                        #   arangodb            (Apache-2.0, multi-model, AQL)
                                        #   nebulagraph         (Apache-2.0, distributed at scale)
                                        #   kuzu                (MIT, embedded)
                                        #   networkx_inmemory   (BSD, testing / "lean" profile only)
                                        #   memgraph            (BSL 1.1, drop-in for Neo4j)
                                        #   tigergraph          (proprietary free tier)
                                        #   ladybug             (Apache-2.0, upstream Cognee default)

# Cache
ENHANCED_CACHE_PROVIDER=valkey          # default; alternatives: redis,
                                        # redis_compat (any wire-compatible),
                                        # memcached, in_memory
```

The MCP server reads these at startup; `src/db_factory.py` returns the
appropriate driver instance.

#### Tier 3 — Profile presets

```bash
ENHANCED_PROFILE=production   # postgres + qdrant + neo4j + valkey  (today's default)
ENHANCED_PROFILE=apache_only  # postgres + qdrant + apache_age + valkey  (pure Apache-2.0)
ENHANCED_PROFILE=lean         # postgres + pgvector + networkx_inmemory + in_memory_cache
                              # (one container; for laptops / small servers)
ENHANCED_PROFILE=byo          # all providers read from env vars; no Docker
                              # (cloud-managed infra)
```

Each profile is a YAML file in `deploy/profiles/`. The installer asks which
profile, sets env vars, optionally brings up matching containers.

### 4.2 Recommended new default: **ArcadeDB** (revised 2026-05-19)

> **Revised decision** per maintainer direction (2026-05-19): the new default
> graph DB is **ArcadeDB**, not Apache AGE. Apache AGE remains a pluggable
> alternative alongside Neo4j and the others.

**Recommendation: ArcadeDB becomes the new default. Apache AGE, Neo4j, ArangoDB,
NebulaGraph, Kuzu, NetworkX, Memgraph, TigerGraph, Ladybug are pluggable.**

#### Why ArcadeDB wins as default

| Criterion                 | ArcadeDB                                                               | Apache AGE                                            |
| ------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------- |
| License                   | Apache-2.0 (clean, "Open Source Forever")                              | Apache-2.0 (clean)                                    |
| Cypher compatibility      | **Full openCypher + native Bolt protocol**                             | openCypher (subset)                                   |
| Drop-in for Neo4j drivers | **Yes** (Bolt-compatible)                                              | No (Postgres wire only)                               |
| Multi-model               | **Graph + Document + KV + Time-series + Search + Vector + Geospatial** | Graph only                                            |
| Multi-protocol            | **HTTP, Bolt, Postgres wire, Redis, MongoDB drivers**                  | Postgres wire only                                    |
| Maturity                  | v26.5.1 (May 2026), 54 releases, 6,316 commits                         | v1.5.0 (2024); ASF top-level since 2023               |
| Performance               | Fast across all models; production-grade                               | Adequate for memory-store; slower for traversal-heavy |
| Operational footprint     | 1 dedicated container; Java 21+ runtime                                | 0 — runs inside existing Postgres                     |
| Migration cost from Neo4j | **Minimal — Cypher + Bolt drop-in**                                    | Some Cypher dialect cleanup; Bolt -> Postgres wire    |
| Best for                  | Production memory store + future flexibility                           | Pure-Postgres minimalist deployments                  |

**Decision logic:** ArcadeDB's full Cypher + Bolt compatibility means we can
swap Neo4j for ArcadeDB with **near-zero code changes** to the existing
`agent_memory_integration.py` Neo4j paths. We retain operational independence
(graph workload doesn't compete with Postgres for resources). The multi-model
support is a strategic plus — future features (time-series memory access
patterns, vector ops alongside graph, document overlays) can be served by the
same engine, reducing future container count rather than adding to it.

Apache AGE earns the **first pluggable slot** for customers wanting to
eliminate a container and run pure-Postgres:

- "One-container" minimalist deployments
- Organisations standardising on Postgres-only operations tooling
- Cases where graph workload is genuinely small (< 100k nodes)

Neo4j stays as a **second pluggable option** for organizations with:

- Existing Neo4j infrastructure or Cypher codebases relying on APOC procedures
- Legacy compatibility requirements
- Familiarity / training investment in Neo4j ecosystem

#### Acknowledged tradeoffs of ArcadeDB

- **Smaller community than Neo4j**: 885 GitHub stars (May 2026) vs Neo4j's
  100M+ Docker pulls. Documentation and third-party tutorials are sparser.
- **Java 21+ runtime**: adds JVM operational overhead vs a Postgres-only stack.
  Mitigated by using the official Docker image (`arcadedata/arcadedb`).
- **Newer in production**: less battle-tested at extreme scale than Neo4j.
  Acceptable for our memory-store workload (10k–10M nodes typical).
- **Single-vendor governance**: Arcade Data SRL maintains the project.
  Mitigated by Apache-2.0 licensing — forkable if vendor disappears.

### 4.3 Implementation phases (effort estimates, revised 2026-05-19)

| Phase | Scope                                                                                                                                                         | Effort                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| 1     | Env-var routing plumbing (`src/db_factory.py` + audit hard-coded imports) -- **SHIPPED 2026-05-19**                                                           | 1 week                      |
| 2     | **ArcadeDB adapter** as new default (Bolt drop-in for current Neo4j paths) + integration tests + container image swap in `docker-compose-enhanced-cognee.yml` -- **SHIPPED 2026-05-19** | 1-2 weeks                   |
| 3     | Apache AGE pluggable adapter + `lean` profile (one-container Postgres-only setup) -- **SHIPPED 2026-05-19**                                                   | 1 week                      |
| 4     | Remaining graph adapters as plug-ins (ArangoDB, NebulaGraph, Kuzu, NetworkX in-mem, Memgraph)                                                                 | 1-2 weeks (build on demand) |
| 5     | Vector adapters (pgvector, LanceDB, Weaviate, Milvus, Chroma)                                                                                                 | 2-3 weeks (build on demand) |
| 6     | Cache adapters (redis, redis_compat, memcached, in_memory)                                                                                                    | 3 days                      |
| 7     | Relational adapter for sqlite (testing / lean profile only)                                                                                                   | 2 days                      |
| 8     | Documentation site (`docs/PROFILES.md` + per-adapter feature matrix)                                                                                          | 1 week                      |

**Total: ~6-8 weeks** spread over 2-3 months alongside other work. Phases 2-3
are the critical path; phases 4-8 are demand-driven.

### 4.4 Backwards compatibility guarantee

The existing `docker compose -f docker/docker-compose-enhanced-cognee.yml up -d`
command must continue to give exactly today's stack. **All new providers are
opt-in via env vars.** No silent migrations.

When Apache AGE becomes the *recommended* default for new installs, existing
Neo4j users keep working without changes; we simply update the installer's
"What do you want to set up?" wizard.

### 4.5 When to do this vs defer

| Add pluggability NOW if...                                | Defer if...                             |
| --------------------------------------------------------- | --------------------------------------- |
| Paying customer requires it                               | No customer has asked                   |
| Compliance audit requires "swap any component in 4 weeks" | Single developer / small team self-host |
| MAS commercial product ships next quarter                 | MAS still in research / dogfooding      |
| Investor / acquirer diligence on architecture flexibility | Internal use only                       |
| You're already touching the DB layer for another reason   | Focused on other features               |

Concretely: **Phase 1 + Phase 2 (ArcadeDB default) + Phase 3 (Apache AGE pluggable)
before MAS goes to paying customers**. Phases 4-8 on demand.

For the full rationale, see [`PLUGGABLE_DB_BACKENDS.md`](./PLUGGABLE_DB_BACKENDS.md).

---

## 5. Component-by-Component Alternatives Analysis

### 5.1 Graph Database (Neo4j alternatives)

The user asked us to consider: ArcadeDB, ArangoDB, TigerGraph, NebulaGraph,
Apache AGE, NetworkX, Memgraph, Kuzu, Ladybug.

#### Filter 1: license-compatible with Enhanced Cognee's commercialisation goals

| Option         | License                   | Commercial-safe? | Notes                                                     |
| -------------- | ------------------------- | ---------------- | --------------------------------------------------------- |
| **Apache AGE** | Apache-2.0                | **YES**          | Postgres extension                                        |
| **ArcadeDB**   | Apache-2.0                | **YES**          | Dedicated multi-model engine                              |
| ArangoDB CE    | Apache-2.0                | YES              | AQL (not Cypher) — migration cost                         |
| NebulaGraph    | Apache-2.0                | YES              | nGQL (not Cypher); designed for billion+ scale            |
| Kuzu           | MIT                       | YES              | Embedded; columnar; Cypher-compatible                     |
| NetworkX       | BSD-3                     | YES              | Python-only, in-memory; prototyping only                  |
| Ladybug        | Apache-2.0 (topoteretes)  | YES              | Upstream Cognee's current default; limited adoption       |
| Neo4j CE       | GPLv3                     | Conditional      | OK as separate service; not bundleable                    |
| **Memgraph**   | **BSL 1.1**               | **NO**           | 4-yr delay to Apache; restrictive commercial use          |
| **TigerGraph** | **Proprietary free tier** | **NO**           | Not open source; commercial license needed for production |

#### Filter 2: feature fit for Enhanced Cognee's use case

We need:

- Cypher (or close equivalent) — minimises code changes from current Neo4j
- ACID transactions — for `get_memory_provenance`, `revert_memory`
- Adequate performance for 10k-1M node graphs (typical agent-memory scale)
- Operational maturity (backup, monitoring, version upgrades)

#### Final ranking (revised 2026-05-19)

| Rank | Option         | Recommendation                                                                             |
| ---- | -------------- | ------------------------------------------------------------------------------------------ |
| 1    | **ArcadeDB**   | **New default.** Apache-2.0, Cypher + Bolt drop-in for Neo4j, multi-model, multi-protocol. |
| 2    | **Apache AGE** | **First pluggable.** Apache-2.0, Postgres extension; one-fewer-container deployments.      |
| 3    | Neo4j CE       | **Second pluggable (legacy compat).** GPLv3 but field-proven, APOC ecosystem.              |
| 4    | ArangoDB       | **Third pluggable.** Apache-2.0, AQL query language; multi-model overlap with ArcadeDB.    |
| 5    | NebulaGraph    | **Fourth pluggable.** Apache-2.0, distributed, billions of vertices; nGQL rewrite cost.    |
| 6    | Kuzu           | Optional pluggable for embedded / single-process deployments (MIT).                        |
| 7    | NetworkX       | Optional pluggable for tests and "lean" profile (no persistence, BSD).                     |
| 8    | Ladybug        | Inherit upstream support; not promoted as a primary choice (Apache-2.0).                   |
| 9    | Memgraph       | Pluggable on demand only (BSL — restrictive commercial use until 2028+).                   |
| 10   | TigerGraph     | **Reject.** Not open source.                                                               |

### 5.2 Observability stack — **SigNoz (MIT) + Apache Superset (Apache-2.0)** replace Grafana + Loki + Tempo + Jaeger

**Revised recommendation (2026-05-19, after license re-evaluation):** Adopt
**SigNoz** as the unified observability product (logs + metrics + traces + APM
+ alerts + LLM observability) and **Apache Superset** as the analytical
dashboarding layer. **Keep Prometheus** for metrics scraping. **Remove Jaeger
entirely** — SigNoz ingests OTel traces natively and Jaeger becomes redundant.

> **Why this changed from the earlier OpenObserve proposal:** OpenObserve is
> AGPL-3.0, which is the same licence as Grafana + Loki + Tempo today. Replacing
> 5 AGPL services with 1 AGPL service is an operational win, not a licensing
> win. The maintainer wants a genuinely **permissive** stack — MIT + Apache-2.0
> throughout — that survives bundled-product distribution without copyleft
> entanglement.

#### What each component does

| Component         | Role                                                                       | Licence    | Repo                                                              |
| ----------------- | -------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------- |
| **Prometheus**    | Scrape `/metrics` endpoint exposed by `prometheus-client` (kept; unchanged)| Apache-2.0 | <https://github.com/prometheus/prometheus>                         |
| **SigNoz**        | Ingest OTel traces + logs + metrics; APM UI; flamegraphs; alerts; LLM obs  | **MIT**    | <https://github.com/SigNoz/signoz>                                 |
| **ClickHouse**    | SigNoz's backing store (multi-tenant; columnar; near-infinite scale)        | Apache-2.0 | <https://github.com/ClickHouse/ClickHouse>                         |
| **Apache Superset** | Custom analytical dashboards (queries ClickHouse and/or Postgres directly) | Apache-2.0 | <https://github.com/apache/superset>                               |

#### Maturity check (verified May 2026)

| Component       | Version | Stars  | Notes                                                            |
| --------------- | ------- | ------ | ---------------------------------------------------------------- |
| Prometheus      | v3.x    | 60k+   | CNCF graduated, industry standard                                |
| SigNoz          | v0.124.0 | 27k   | 249 releases, active dev, OpenTelemetry-native, MIT Expat        |
| ClickHouse      | v25.x   | 40k+   | Used at Cloudflare-, Uber-, Spotify-scale                        |
| Apache Superset | v6.1.0  | 72.9k  | 248 releases, mature ASF top-level project                       |

#### Why this combination wins

| Criterion                       | SigNoz + Apache Superset + Prometheus | Grafana + Loki + Tempo + Prom + Jaeger     | OpenObserve (rejected proposal) |
| ------------------------------- | ------------------------------------- | ------------------------------------------ | ------------------------------- |
| Licence purity                  | **100% permissive** (MIT + Apache-2.0)| 3-of-5 AGPL                                | AGPL-3.0                        |
| Distribution-safe (Scenario 3)  | **YES**                                | NO without separate-compose carve-out      | NO without same carve-out       |
| OTel-native ingestion           | **Yes (SigNoz)**                        | Partial (per-service)                      | Yes                             |
| Logs                            | SigNoz                                 | Loki                                       | OpenObserve                     |
| Metrics                         | Prometheus + SigNoz                     | Prometheus + Grafana                       | OpenObserve                     |
| Traces                          | **SigNoz (Jaeger gone)**               | Tempo + Jaeger                             | OpenObserve                     |
| APM dashboards                  | SigNoz (built-in)                       | Grafana custom                             | OpenObserve (built-in)          |
| Custom BI / analytical dashboards | **Apache Superset**                   | Grafana (limited for non-time-series)      | OpenObserve (limited)           |
| LLM observability               | **SigNoz (first-class)**               | Manual via Grafana panels                  | Roadmap                         |
| Alerting                        | SigNoz                                 | Grafana Alertmanager                       | OpenObserve                     |

#### Why two UI layers (SigNoz **and** Superset)?

Different jobs:

- **SigNoz** is observability-first. Flamegraphs, RED metrics, error rates,
  exception tracking, request waterfall — the things an on-call engineer
  cares about at 02:00 AM.
- **Apache Superset** is BI-first. Custom SQL, ad-hoc charts, scheduled
  reports, dashboards for non-engineering stakeholders. Queries the same
  ClickHouse store directly, so the data is consistent.

Together they replace what Grafana did *and* add analytical-dashboard
capabilities Grafana never had (Grafana can do some BI but Superset is
strictly better at it).

#### Licence verdict across deployment scenarios

| Scenario                                                  | Verdict                                                              |
| --------------------------------------------------------- | -------------------------------------------------------------------- |
| Self-hosted personal use                                  | **OK** — no licence issues                                           |
| Self-hosted commercial (support contracts)                | **OK** — no licence issues                                           |
| SaaS commercial (you host)                                | **OK** — no licence issues                                           |
| **Distribute Enhanced Cognee as a packaged product**      | **OK** — 100% permissive; can be bundled                              |
| Closed-source commercial product bundling Enhanced Cognee | **OK** — MIT + Apache-2.0 freely embeddable                          |

Note: this is the first observability stack that passes the bundled-product
Scenario 3 cleanly. Grafana + Loki + Tempo (AGPL) required a "customer pulls
their own image" carve-out; SigNoz + Superset + Prometheus do not.

#### Alternative: **HyperDX (MIT)** — same licence, different UX

If you prefer a Kibana-style query-driven UX over SigNoz's APM-first UX,
**HyperDX** (<https://github.com/hyperdxio/hyperdx>) is the MIT alternative:

| Attribute       | HyperDX                                                              |
| --------------- | -------------------------------------------------------------------- |
| Licence (app)   | **MIT**                                                              |
| Covers          | Logs + metrics + traces + session replay + exceptions                |
| Storage         | ClickHouse (mandatory) + **MongoDB** for metadata                    |
| Maturity        | 9.5k stars, v0.4.1 (May 2026), 163 releases                          |

⚠️ **HyperDX caveat — MongoDB SSPL:** HyperDX bundles MongoDB as its metadata
store. MongoDB is licensed under SSPL (Server Side Public License) since 2018,
which is non-permissive and has the same SaaS-clause issue that triggered our
Redis -> Valkey migration. For self-hosted commercial use this is fine
(SSPL only triggers when you SaaS-provide the SSPL component itself, which we
don't), but for **distributed-product scenarios** the MongoDB sub-dependency
is more restrictive than SigNoz's ClickHouse + nothing. If you need a fallback
that's strictly permissive end-to-end including metadata, SigNoz wins.

Pair HyperDX with **Apache Superset** the same way as SigNoz if you choose
this path.

#### Other options evaluated (and why not chosen)

| Option                                  | Licence         | Why not the primary                                                                  |
| --------------------------------------- | --------------- | ------------------------------------------------------------------------------------ |
| OpenObserve                             | AGPL-3.0        | Same licence risk as Grafana stack — doesn't improve our posture                     |
| VictoriaMetrics + VictoriaLogs + Jaeger + vmui | Apache-2.0 | vmui is a query explorer, not a dashboarding tool — no equivalent for Grafana panels |
| Quickwit                                | Apache-2.0      | Search engine only (no built-in UI); needs Grafana for dashboards                    |
| OpenSearch Observability Stack          | Apache-2.0      | JVM-heavy; ES-flavoured query layer; harder operational story                        |
| Coroot                                  | Apache-2.0      | Kubernetes-native; eBPF auto-instrumentation; not aligned with our compose deployment |
| Apache Superset alone                   | Apache-2.0      | No log / trace ingestion — needs a partner like SigNoz                                |

### 5.3 What this means for Enhanced Cognee's current observability touch-points

Enhanced Cognee touches observability in four places today; the SigNoz +
Apache Superset migration affects them as follows:

| Touch point                                         | Today                                                | After SigNoz + Apache Superset migration                                |
| --------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------- |
| `requirements.txt`: `prometheus-client==0.25.0`     | Used by `get_prometheus_metrics` MCP tool            | **Keep** — Prometheus stays as the scraper; SigNoz also reads it natively |
| `requirements.txt`: `opentelemetry-api/sdk==1.41.1` | Used by `src/tracing.py` (~70% scaffolded)           | **Keep** — point OTLP exporter at SigNoz collector (default port 4317)   |
| `monitoring/docker-compose-monitoring.yml`          | Bundles Grafana + Loki + Tempo + Prometheus + Jaeger | **Rewrite** — Prometheus + SigNoz stack + Apache Superset (Jaeger gone)  |
| `monitoring/dashboards/*.json`                      | Grafana JSON dashboards                              | **Migrate** — APM dashboards live in SigNoz natively; custom analytical dashboards rebuilt in Apache Superset (export as JSON to `monitoring/superset-dashboards/`) |
| `docs/MONITORING.md`                                | Grafana + Loki setup steps                           | **Rewrite** for the new stack — section per component                    |

**Total migration effort: ~1-2 weeks** (one engineer). Most of the time is
in rebuilding dashboards in two places (operations dashboards into SigNoz, BI
dashboards into Superset). The Python instrumentation (Prometheus +
OpenTelemetry) is unchanged.

#### Reference docker-compose snippet (target state)

```yaml
# monitoring/docker-compose-monitoring.yml (after migration)
services:
  prometheus:
    image: prom/prometheus:v3.x       # Apache-2.0
    ports: ["9090:9090"]

  signoz-otel-collector:               # MIT (Apache-2.0 collector binary)
    image: signoz/signoz-otel-collector:latest
    ports: ["4317:4317", "4318:4318"]  # OTLP gRPC / HTTP

  signoz-clickhouse:
    image: clickhouse/clickhouse-server:25.x   # Apache-2.0
    volumes: [clickhouse_data:/var/lib/clickhouse]

  signoz-zookeeper:
    image: bitnami/zookeeper:3.x       # Apache-2.0 (ClickHouse coordination)

  signoz-query-service:                # MIT
    image: signoz/query-service:latest
    depends_on: [signoz-clickhouse]

  signoz-frontend:                     # MIT
    image: signoz/frontend:latest
    ports: ["3301:3301"]
    depends_on: [signoz-query-service]

  signoz-alertmanager:                 # MIT
    image: signoz/alertmanager:latest
    depends_on: [signoz-query-service]

  superset:                            # Apache-2.0
    image: apache/superset:6.1.0
    ports: ["8088:8088"]
    environment:
      DATABASE_URL: postgresql://cognee_user:cognee_password@postgres-enhanced:5432/superset_metadata
    # Reuses our existing Postgres for metadata storage

volumes:
  clickhouse_data:
```

8 services total (vs 5 today). The licence purity is the win, not the
container count. For minimal deployments, SigNoz also offers an all-in-one
Docker image bundling its sub-services into a single container.

---

## 6. Deployment Paths

| Path                                 | When to use                                      | Time   |
| ------------------------------------ | ------------------------------------------------ | ------ |
| **A. Local (Windows / Mac / Linux)** | Personal use, dev, MAS integration               | 10 min |
| **B. VPS (Hetzner CX22 or similar)** | Production, shared with team, internet-reachable | 45 min |

### Path A: Local laptop deployment

Prerequisites: Docker Desktop, Python 3.11+, Claude Code installed.

```powershell
# 1. Bring up the stack
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

# 2. Verify
docker ps    # 4 containers, all (healthy)

# 3. Install MCP server in Claude Code
powershell -ExecutionPolicy Bypass -File deploy/local/install.ps1

# 4. Restart Claude Code → 122 tools available
```

### Path B: VPS deployment

Use `deploy/vps/install.sh`. Provisions Caddy, systemd units, the Compose stack,
and configures HTTPS via Let's Encrypt. Detailed steps in
[`DEPLOYMENT_QUICKSTART.md`](./DEPLOYMENT_QUICKSTART.md).

### Cost over time (self-hosted, 1 user)

| Month    | Enhanced Cognee | Mem0 (Pro) | Letta (Cloud) |
| -------- | --------------- | ---------- | ------------- |
| Month 1  | ~5 EUR (VPS)    | $19        | $25           |
| Month 12 | ~60 EUR/year    | $228/year  | $300/year     |
| Month 24 | ~120 EUR/year   | $456/year  | $600/year     |

After month ~3, self-hosted Enhanced Cognee is the most cost-effective option
for a single developer using Claude Code with personal memory.

---

## 7. Outstanding Items & Gap Analysis

### CRITICAL (do before commercialisation)

| #   | Item                                                            | Effort        |
| --- | --------------------------------------------------------------- | ------------- |
| C1  | Live integration / E2E tests against the live stack in CI       | 3 hours       |
| C2  | Branch protection on `main` (now done — required checks active) | Done          |
| C3  | Verify `upstream_sync` workflow fires email on Monday cron      | Wait + verify |
| C4  | Multi-Agent System integration: actually do the wiring          | 1-2 weeks     |

### HIGH (do within 1-2 months)

| #   | Item                                                            | Effort    |
| --- | --------------------------------------------------------------- | --------- |
| H1  | **Apache AGE adapter** (graph DB swap)                          | 1-2 weeks |
| H2  | SBOM (Software Bill of Materials) in CI                         | 2 hours   |
| H3  | OpenTelemetry / Jaeger wiring (~70% scaffolded already)         | 1-2 days  |
| H4  | Performance tests — run locust against live stack, document p95 | 2 hours   |

### MEDIUM (good hygiene, low urgency)

| #   | Item                                                     | Effort         |
| --- | -------------------------------------------------------- | -------------- |
| M1  | `examples/` directory with real Enhanced-Cognee examples | 4 hours        |
| M2  | `CONTRIBUTING.md`                                        | 2 hours        |
| M3  | Issue templates + PR template                            | 45 minutes     |
| M4  | Pre-commit hooks installed by default                    | 15 minutes     |
| M5  | mkdocs + GitHub Pages doc site                           | 4 hours        |
| M6  | Enforce mypy in lint job                                 | 1 hour + fixes |

### LOW (defer)

| #   | Item                                 | Why low                            |
| --- | ------------------------------------ | ---------------------------------- |
| L1  | Helm chart for Kubernetes deployment | Most customers use compose         |
| L2  | Multi-region / HA deployment         | Single-VPS covers ~99% of users    |
| L3  | UI dashboard (non-MCP)               | Audience prefers CLI/MCP           |
| L4  | i18n of error messages               | Audience is English-fluent         |
| L5  | Plugin marketplace                   | Need 10+ third-party plugins first |

### Known quirks (won't fix; documented)

- **Q1.** ASCII-only output rule (Windows cp1252 console support).
- **Q2.** `test_security_modules.py` does global `passlib.hash` monkey-patch;
  workaround via `__globals__` patching elsewhere.
- **Q3.** Compose volume name `redis_data` not renamed to `valkey_data`
  (renaming orphans existing data).
- **Q4.** Compose service name `redis` not renamed to `valkey` (internal DNS only).
- **Q5.** Docker base image bumped 3.11-slim → 3.14-slim by Dependabot; tested
  on 3.11/3.12, 3.14 should work but some C-extensions may need source builds.

Full long-form list in [`OUTSTANDING_ITEMS.md`](./OUTSTANDING_ITEMS.md).

---

## 8. Recommended 12-Week Roadmap (revised 2026-05-19)

| Week | Theme                              | Output                                                                                                                                                     |
| ---- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | CI hardening                       | Live integration + e2e tests in CI; branch protection done; SBOM step added.                                                                               |
| 2    | Phase 1 plumbing                   | `src/db_factory.py` + env-var routing for all 4 DB tiers; no functional change.                                                                            |
| 3-4  | **ArcadeDB swap (new default)** -- **SHIPPED 2026-05-19** | `arcadedb` provider working end-to-end; Bolt drop-in for existing Neo4j paths; docker-compose updated; passing all integration tests; benchmarks vs Neo4j. See `docs/ARCADEDB_MIGRATION.md`. |
| 5    | **SigNoz + Apache Superset observability swap** -- **SHIPPED 2026-05-19** | SigNoz (MIT) replaces Grafana+Loki+Tempo+Jaeger; Apache Superset (Apache-2.0) added for BI dashboards; Prometheus kept; APM dashboards migrate into SigNoz, custom dashboards into Superset; `init_tracing()` documents the SigNoz OTLP endpoint (4317). See `docs/MONITORING.md`. |
| 6    | **Apache AGE pluggable adapter** -- **SHIPPED 2026-05-19** | `apache_age` provider working; `lean` profile (one-container Postgres-only setup) shipped. See `docs/PROFILES.md`. |
| 7-8  | MAS integration sprint             | MAS reads/writes Enhanced Cognee memories; auth wiring; agent-ID mapping.                                                                                  |
| 9    | Vector + cache pluggable adapters  | `pgvector` + `in_memory` cache + `sqlite` relational shipped (covers "lean" profile completely).                                                           |
| 10   | `examples/` + docs site            | 4-5 Enhanced-specific examples; mkdocs-material at GitHub Pages.                                                                                           |
| 11   | Performance run                    | Locust against live stack; documented p50/p95/p99; perf regression dashboard.                                                                              |
| 12   | Polish + first commercial release  | `CONTRIBUTING.md`, issue templates, release notes, SBOM, "v1.0.0-commercial" tag.                                                                          |

**Total effort:** ~1 FTE for 3 months. Realistically spread to 4-6 months
alongside other work.

---

## 9. Appendix: Decision Records

| #     | Decision                                                                                                                                                 | Date                 | Rationale                                                                                                                                                                             |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DR-01 | Fork from `topoteretes/cognee` rather than build from scratch                                                                                            | 2025-Q4              | Inherit a mature pipeline + actively maintained upstream; add what's missing.                                                                                                         |
| DR-02 | 4-DB stack (Postgres + Qdrant + Neo4j + Redis-then-Valkey)                                                                                               | 2025-Q4              | Each DB optimised for its tier; complexity tradeoff acceptable for production use.                                                                                                    |
| DR-03 | Replace Redis with Valkey 8                                                                                                                              | 2026-Q1              | Redis 7.4 license shift (BSL/SSPL) incompatible with Apache-2.0 commercialisation.                                                                                                    |
| DR-04 | Keep Neo4j Community as default graph DB (Phase 1-14)                                                                                                    | 2025-Q4              | GPLv3 in self-host/SaaS model is safe; production-proven; APOC ecosystem.                                                                                                             |
| DR-05 | ~~Plan migration to Apache AGE as default graph DB~~ **SUPERSEDED by DR-11**                                                                             | 2026-05-19           | Original recommendation; superseded by maintainer decision later same day.                                                                                                            |
| DR-06 | ~~ArcadeDB as secondary pluggable graph DB~~ **SUPERSEDED by DR-11**                                                                                     | 2026-05-19           | Original recommendation; superseded by maintainer decision later same day.                                                                                                            |
| DR-07 | ~~Keep Grafana/Loki as default monitoring~~ **SUPERSEDED by DR-12**                                                                                      | 2026-05-19           | Original recommendation; superseded by maintainer decision later same day.                                                                                                            |
| DR-08 | Pluggable DB backends via env vars (gradual, Tier 1/2/3)                                                                                                 | 2026-05-19           | Default unchanged; new providers opt-in; minimises regression risk.                                                                                                                   |
| DR-09 | Apache-2.0 license for all Enhanced Cognee code                                                                                                          | 2025-Q4              | Maximally permissive; aligned with upstream and Python ecosystem norms.                                                                                                               |
| DR-10 | ASCII-only output rule                                                                                                                                   | 2025-Q4              | Windows cp1252 console support; enforced via pre-commit hook.                                                                                                                         |
| DR-11 | **ArcadeDB becomes new default graph DB; Apache AGE + Neo4j + ArangoDB + NebulaGraph + Kuzu + NetworkX + Memgraph + Ladybug + TigerGraph are pluggable** -- **SHIPPED 2026-05-19** | 2026-05-19 (revised); shipped 2026-05-19 | ArcadeDB's Cypher + Bolt compatibility = near-zero code change from current Neo4j paths; multi-model future-proofs the engine choice. AGE retained for "lean" Postgres-only profiles. Phase 2 implementation in PR #20: `src/db_adapters/graph_arcadedb.py` + factory default flip + docker-compose swap; see `docs/ARCADEDB_MIGRATION.md`. |
| DR-12 | ~~OpenObserve replaces Grafana + Loki + Tempo + Prometheus + Jaeger~~ **SUPERSEDED by DR-13**                                                            | 2026-05-19           | Original same-day recommendation; superseded because OpenObserve is AGPL-3.0 (same risk profile as Grafana + Loki + Tempo today), so the swap didn't actually improve licence posture. |
| DR-13 | **SigNoz (MIT) + Apache Superset (Apache-2.0) replace Grafana + Loki + Tempo + Jaeger; Prometheus kept** -- **SHIPPED 2026-05-19** | 2026-05-19 (revised); shipped 2026-05-19 | 100% permissive observability stack (MIT + Apache-2.0); SigNoz handles APM / traces / logs / metrics / alerts / LLM observability natively; Apache Superset adds BI-style analytical dashboards over the shared ClickHouse store; Jaeger removed (SigNoz ingests OTel traces directly). HyperDX (MIT) documented as alternative with MongoDB-SSPL caveat. Phase 4 implementation in PR #22: `monitoring/docker-compose-monitoring.yml` rewrite, `monitoring/docker-compose-monitoring-hyperdx.yml` alternative, `docs/MONITORING.md`, `src/tracing.py` endpoint docs. |

---

**End of strategy document.** For change requests or new decisions, append to the
Decision Records table and update the relevant section.
