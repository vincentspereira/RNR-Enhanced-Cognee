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

**License posture:** Apache-2.0 everywhere except Neo4j Community (GPLv3, used as a
separate network service — no copyleft attaches to Enhanced Cognee code) and the
*optional* monitoring stack (Grafana/Loki AGPLv3).

**Recommended next moves (in priority order):**

| # | Action                                              | Effort       | Driver                                                     |
| - | --------------------------------------------------- | ------------ | ---------------------------------------------------------- |
| 1 | Ship Phase 1 pluggable DB plumbing (env var routing)| 1 week       | Removes lock-in, enables BYO infra for enterprise prospects|
| 2 | Add **Apache AGE** as a graph-DB option             | 1-2 weeks    | Eliminates the only GPLv3 component in our default stack   |
| 3 | Wire integration tests against live stack in CI     | 3 hours      | Catches DB-driver regressions before main                  |
| 4 | MAS integration sprint                              | 1-2 weeks    | Delivers user-facing value                                 |
| 5 | Consider **ArcadeDB** as the secondary graph option | 1-2 weeks    | Customers wanting a fast dedicated graph DB without GPL    |
| 6 | Switch monitoring docs to recommend **SigNoz** + **VictoriaLogs** as Apache-2.0 alternative to Grafana + Loki | 1 week | Pure-Apache observability story for compliance-strict orgs |

Items 1-3 are essentially mandatory before commercial sale. Items 4-6 are
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

| If you need...                                                            | Use                            |
| ------------------------------------------------------------------------- | ------------------------------ |
| Production-grade, multi-database memory layer with 122 MCP tools          | **Enhanced Cognee**            |
| Lightweight Cognee with single-DB setup, no enterprise features           | Cognee (upstream)              |
| Hosted memory-as-a-service with no ops burden                             | Mem0                           |
| Long-term memory for chat agents with temporal knowledge graphs           | Zep (Apache-2.0)               |
| Stateful agent platform with built-in workflows                           | Letta (formerly MemGPT)        |
| Document-corpus retrieval with memory                                     | LlamaIndex                     |
| In-process Python memory for prototyping                                  | LangChain Memory               |
| Pure semantic search over a vector corpus (no graph, no agents)           | Qdrant / Weaviate / Chroma     |

A full side-by-side feature matrix lives in [`COMPARE_TO_ALTERNATIVES.md`](./COMPARE_TO_ALTERNATIVES.md).

---

## 3. License & Commercialisation Risk Map

### Risk by component

| Component                  | License       | Self-host commercial | Bundled-product distribution | SaaS commercial |
| -------------------------- | ------------- | -------------------- | ---------------------------- | --------------- |
| Enhanced Cognee (own code) | Apache-2.0    | OK                   | OK                           | OK              |
| Cognee (upstream)          | Apache-2.0    | OK                   | OK                           | OK              |
| PostgreSQL + pgvector      | PostgreSQL    | OK                   | OK                           | OK              |
| Qdrant                     | Apache-2.0    | OK                   | OK                           | OK              |
| Valkey                     | Apache-2.0    | OK                   | OK                           | OK              |
| Python pip deps (~50)      | Apache/MIT/BSD/PSF | OK              | OK                           | OK              |
| Caddy                      | Apache-2.0    | OK                   | OK                           | OK              |
| **Neo4j Community**        | **GPLv3**     | OK                   | **CAUTION**                  | OK              |
| **Grafana / Loki**         | **AGPLv3**    | OK                   | **CAUTION**                  | **CAUTION**     |
| psycopg2                   | LGPL          | OK                   | OK                           | OK              |

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
PostgreSQL 18 + pgvector  (port 25432)
Qdrant 1.12.0              (port 26333)
Neo4j 5.25-community       (port 27687)
Valkey 8                   (port 26379)
```

This guarantees zero regression for existing users.

#### Tier 2 — Env-var override

```bash
# Relational
ENHANCED_RELATIONAL_PROVIDER=postgres   # default; alternative: sqlite (testing/lean only)

# Vector
ENHANCED_VECTOR_PROVIDER=qdrant         # default; alternatives: pgvector, lancedb,
                                        # weaviate, milvus, chroma

# Graph - new default proposed below
ENHANCED_GRAPH_PROVIDER=apache_age      # NEW DEFAULT (Apache-2.0, runs in Postgres)
                                        # alternatives: arcadedb (Apache-2.0, dedicated),
                                        # neo4j (GPLv3, for compatibility),
                                        # memgraph (BSL, drop-in for Neo4j),
                                        # kuzu (MIT, embedded),
                                        # networkx_inmemory (testing only),
                                        # nebulagraph (Apache, large-scale),
                                        # arangodb (Apache, multi-model)

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

### 4.2 Recommended new default: **Apache AGE** over ArcadeDB

> The user asked for a recommendation between **ArcadeDB** and **Apache AGE**
> as the new default graph backend, with the other made available alongside Neo4j.

**Recommendation: Apache AGE becomes the new default. ArcadeDB and Neo4j are pluggable.**

#### Why Apache AGE wins as default

| Criterion                  | Apache AGE                                | ArcadeDB                              |
| -------------------------- | ----------------------------------------- | ------------------------------------- |
| License                    | Apache-2.0 (clean)                        | Apache-2.0 (clean)                    |
| Governance                 | Apache top-level project (since 2023)     | Single vendor (Arcade Data SRL)       |
| Container footprint        | **0** — runs inside existing Postgres     | 1 dedicated container                 |
| Operational complexity     | **Lower** — reuse Postgres ops (backup/HA/monitoring) | Separate ops tooling          |
| Maturity                   | v1.5.0 (2024); proven Postgres engine     | v23+; production but newer ecosystem  |
| Cypher dialect             | openCypher (full standard subset)         | Full Cypher + Bolt protocol           |
| Performance (our scale)    | Fine for memory-store workloads           | Faster for traversal-heavy queries    |
| Community size             | Smaller graph community, huge Postgres community | Smaller dedicated community     |
| Bolt compatibility         | No (Postgres protocol)                    | Yes (drop-in Neo4j driver)            |
| Best for                   | Memory store, moderate graph              | Pure graph workload, high scale       |

**Decision logic:** Enhanced Cognee is a memory store, not a graph analytics
platform. Our graph queries are small (find related memories, traverse
provenance chains, knowledge-graph compaction). Apache AGE's slightly slower
traversal vs ArcadeDB is irrelevant; its operational simplicity
(one-less-container, leverages Postgres tooling we already operate) and
Apache governance stability matter more.

ArcadeDB earns the **secondary slot** for customers with:
- Million-edge knowledge graphs where AGE feels slow
- Existing Neo4j Bolt clients that want drop-in compatibility
- Preference for a dedicated graph engine

Neo4j stays as a **third option** for organizations with existing Neo4j
infrastructure or Cypher codebases relying on APOC procedures.

### 4.3 Implementation phases (effort estimates)

| Phase | Scope                                                                  | Effort       |
| ----- | ---------------------------------------------------------------------- | ------------ |
| 1     | Env-var routing plumbing (`src/db_factory.py` + audit hard-coded imports)| 1 week     |
| 2     | Apache AGE adapter + integration tests + `apache_only` profile         | 1-2 weeks    |
| 3     | ArcadeDB adapter (drop-in via Bolt, mostly free)                        | 3-5 days     |
| 4     | `lean` profile (pgvector + networkx_inmemory + in_memory_cache)         | 3 days       |
| 5     | Remaining vector adapters (LanceDB, Weaviate, Milvus, Chroma)           | 2-3 weeks    |
| 6     | Documentation site (`docs/PROFILES.md` + per-adapter feature matrix)    | 1 week       |

**Total: ~6-8 weeks** spread over 2-3 months alongside other work.

### 4.4 Backwards compatibility guarantee

The existing `docker compose -f docker/docker-compose-enhanced-cognee.yml up -d`
command must continue to give exactly today's stack. **All new providers are
opt-in via env vars.** No silent migrations.

When Apache AGE becomes the *recommended* default for new installs, existing
Neo4j users keep working without changes; we simply update the installer's
"What do you want to set up?" wizard.

### 4.5 When to do this vs defer

| Add pluggability NOW if...                                       | Defer if...                                  |
| ---------------------------------------------------------------- | -------------------------------------------- |
| Paying customer requires it                                      | No customer has asked                        |
| Compliance audit requires "swap any component in 4 weeks"        | Single developer / small team self-host      |
| MAS commercial product ships next quarter                        | MAS still in research / dogfooding           |
| Investor / acquirer diligence on architecture flexibility        | Internal use only                            |
| You're already touching the DB layer for another reason          | Focused on other features                    |

Concretely: **Phase 1 + Phase 2 (Apache AGE) before MAS goes to paying customers**.
Phases 3-6 on demand.

For the full rationale, see [`PLUGGABLE_DB_BACKENDS.md`](./PLUGGABLE_DB_BACKENDS.md).

---

## 5. Component-by-Component Alternatives Analysis

### 5.1 Graph Database (Neo4j alternatives)

The user asked us to consider: ArcadeDB, ArangoDB, TigerGraph, NebulaGraph,
Apache AGE, NetworkX, Memgraph, Kuzu, Ladybug.

#### Filter 1: license-compatible with Enhanced Cognee's commercialisation goals

| Option            | License                       | Commercial-safe? | Notes                                      |
| ----------------- | ----------------------------- | ---------------- | ------------------------------------------ |
| **Apache AGE**    | Apache-2.0                    | **YES**          | Postgres extension                         |
| **ArcadeDB**      | Apache-2.0                    | **YES**          | Dedicated multi-model engine               |
| ArangoDB CE       | Apache-2.0                    | YES              | AQL (not Cypher) — migration cost          |
| NebulaGraph       | Apache-2.0                    | YES              | nGQL (not Cypher); designed for billion+ scale |
| Kuzu              | MIT                           | YES              | Embedded; columnar; Cypher-compatible       |
| NetworkX          | BSD-3                         | YES              | Python-only, in-memory; prototyping only    |
| Ladybug           | Apache-2.0 (topoteretes)      | YES              | Upstream Cognee's current default; limited adoption |
| Neo4j CE          | GPLv3                         | Conditional      | OK as separate service; not bundleable      |
| **Memgraph**      | **BSL 1.1**                   | **NO**           | 4-yr delay to Apache; restrictive commercial use |
| **TigerGraph**    | **Proprietary free tier**     | **NO**           | Not open source; commercial license needed for production |

#### Filter 2: feature fit for Enhanced Cognee's use case

We need:
- Cypher (or close equivalent) — minimises code changes from current Neo4j
- ACID transactions — for `get_memory_provenance`, `revert_memory`
- Adequate performance for 10k-1M node graphs (typical agent-memory scale)
- Operational maturity (backup, monitoring, version upgrades)

#### Final ranking

| Rank | Option        | Recommendation                                                                                  |
| ---- | ------------- | ----------------------------------------------------------------------------------------------- |
| 1    | **Apache AGE** | **New default.** Apache-2.0, runs in Postgres, openCypher, fewer containers.                  |
| 2    | **ArcadeDB**  | **Secondary pluggable.** Apache-2.0, dedicated graph engine, full Cypher + Bolt.                |
| 3    | Neo4j CE      | **Third pluggable (kept for compatibility).** GPLv3 but field-proven, APOC ecosystem.           |
| 4    | Kuzu          | Optional pluggable for embedded / single-process deployments.                                   |
| 5    | NetworkX      | Optional pluggable for tests and "lean" profile (no persistence).                               |
| 6    | NebulaGraph   | Document but don't ship adapter; nGQL rewrite cost vs. value not justified yet.                 |
| 7    | ArangoDB      | Document but skip; AQL rewrite is large; multi-model overlap with ArcadeDB.                     |
| 8    | Ladybug       | Inherit upstream support but don't promote as a primary choice.                                 |
| 9    | Memgraph      | **Reject.** BSL incompatible with our commercialisation posture.                                |
| 10   | TigerGraph    | **Reject.** Not open source.                                                                    |

### 5.2 Observability / Dashboards (Grafana alternatives)

Grafana switched to AGPLv3 in 2021. Self-hosted use is fine, but distributing
Grafana inside a packaged commercial product triggers obligations. Alternatives:

| Option                          | License         | Coverage                              | When to choose                                              |
| ------------------------------- | --------------- | ------------------------------------- | ----------------------------------------------------------- |
| **SigNoz**                      | **MIT**         | Metrics + Logs + Traces (full APM)    | **Best Grafana replacement.** Datadog-like UX, ClickHouse-backed, OpenTelemetry-native. |
| **VictoriaMetrics + vmui**      | **Apache-2.0**  | Metrics only                          | When you only need Prometheus-style metrics and ultra-low resource footprint. |
| OpenSearch Observability Stack  | Apache-2.0      | Logs + Metrics + Traces               | When already invested in Elastic-style stack; heavier than alternatives. |
| Coroot                          | Apache-2.0      | Metrics + Traces (eBPF auto-instr.)   | Kubernetes-native deployments needing zero-config tracing.   |
| Apache Superset                 | Apache-2.0      | BI dashboards (not native time-series)| When you need rich SQL-driven dashboards over warehoused data. |
| Redash                          | BSD-2           | SQL-driven dashboards                 | Lighter Superset alternative; less observability-specific.   |
| Apache HertzBeat                | Apache-2.0      | Infrastructure monitoring             | Less mature in Western ecosystems; primarily for infra (not app) monitoring. |
| Datav (XO)                      | Apache-2.0      | Dashboarding                          | Newer; smaller community; evaluate case-by-case.            |
| **Grafana (status quo)**        | AGPLv3          | Metrics + Logs + Traces               | Keep using if you self-host AND don't distribute.            |

#### Recommendation

- **Default recommendation: keep Grafana** for the optional monitoring stack
  because (a) self-host model + opt-in compose file = AGPLv3 obligations don't
  attach to Enhanced Cognee, (b) it's vastly better documented than alternatives,
  (c) most operators already know it.
- **For commercialised distributions: switch to SigNoz.** MIT-licensed
  Datadog-like full-stack APM, OpenTelemetry-native, one binary deploys it all.
- **For pure-metrics minimalist setups: VictoriaMetrics + vmui.** Apache-2.0,
  10x lower memory than Prometheus + Grafana.

Document the swap path in `docs/OBSERVABILITY_SWAP.md` (TBD).

### 5.3 Log Aggregation (Loki alternatives)

Loki is also AGPLv3 (Grafana Labs). Alternatives:

| Option                            | License         | Notes                                                                |
| --------------------------------- | --------------- | -------------------------------------------------------------------- |
| **VictoriaLogs**                  | **Apache-2.0**  | **Recommended.** Same vendor as VictoriaMetrics, LogsQL query language, 10x compression vs ELK. |
| OpenSearch (Log Analytics)        | Apache-2.0      | AWS fork of Elasticsearch; heavier but rich search.                  |
| Quickwit                          | Apache-2.0      | Sub-second search at petabyte scale; new project (2022+).            |
| ClickHouse (raw)                  | Apache-2.0      | General columnar DB; used internally by SigNoz for logs.             |
| Log Bull                          | Need to verify  | Newer project; evaluate before committing.                           |
| **Loki (status quo)**             | AGPLv3          | Keep for self-host; swap for commercial distribution.                |

#### Recommendation

- **Default recommendation: keep Loki** for the optional monitoring stack
  (same logic as Grafana — opt-in separate compose).
- **For commercialised distributions: VictoriaLogs.** Consistent observability
  story with VictoriaMetrics, Apache-2.0, low resource footprint.
- **If already using SigNoz: SigNoz's built-in ClickHouse log store** —
  one product for metrics + logs + traces.

### 5.4 Combined Apache-only observability stack

For customers requiring zero AGPL components anywhere:

```
SigNoz (MIT)                    Metrics + Logs + Traces + APM UI
  └─ ClickHouse (Apache-2.0)    Underlying storage
  └─ OpenTelemetry Collector    Instrumentation (Apache-2.0)
```

OR (split):

```
VictoriaMetrics (Apache-2.0)    Metrics storage
VictoriaLogs (Apache-2.0)       Log storage
vmui (Apache-2.0)               Built-in dashboards
Jaeger (Apache-2.0)             Traces
```

Both stacks ship as Docker Compose files in the proposed `monitoring/apache-only/`
directory (TBD).

---

## 6. Deployment Paths

| Path                                | When to use                                | Time   |
| ----------------------------------- | ------------------------------------------ | ------ |
| **A. Local (Windows / Mac / Linux)** | Personal use, dev, MAS integration       | 10 min |
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

| Month    | Enhanced Cognee  | Mem0 (Pro)  | Letta (Cloud) |
| -------- | ---------------- | ----------- | ------------- |
| Month 1  | ~5 EUR (VPS)     | $19         | $25           |
| Month 12 | ~60 EUR/year     | $228/year   | $300/year     |
| Month 24 | ~120 EUR/year    | $456/year   | $600/year     |

After month ~3, self-hosted Enhanced Cognee is the most cost-effective option
for a single developer using Claude Code with personal memory.

---

## 7. Outstanding Items & Gap Analysis

### CRITICAL (do before commercialisation)

| #  | Item                                                           | Effort      |
| -- | -------------------------------------------------------------- | ----------- |
| C1 | Live integration / E2E tests against the live stack in CI      | 3 hours     |
| C2 | Branch protection on `main` (now done — required checks active)| Done        |
| C3 | Verify `upstream_sync` workflow fires email on Monday cron     | Wait + verify |
| C4 | Multi-Agent System integration: actually do the wiring         | 1-2 weeks   |

### HIGH (do within 1-2 months)

| #  | Item                                                           | Effort      |
| -- | -------------------------------------------------------------- | ----------- |
| H1 | **Apache AGE adapter** (graph DB swap)                         | 1-2 weeks   |
| H2 | SBOM (Software Bill of Materials) in CI                        | 2 hours     |
| H3 | OpenTelemetry / Jaeger wiring (~70% scaffolded already)        | 1-2 days    |
| H4 | Performance tests — run locust against live stack, document p95| 2 hours     |

### MEDIUM (good hygiene, low urgency)

| #  | Item                                                           | Effort      |
| -- | -------------------------------------------------------------- | ----------- |
| M1 | `examples/` directory with real Enhanced-Cognee examples       | 4 hours     |
| M2 | `CONTRIBUTING.md`                                              | 2 hours     |
| M3 | Issue templates + PR template                                  | 45 minutes  |
| M4 | Pre-commit hooks installed by default                          | 15 minutes  |
| M5 | mkdocs + GitHub Pages doc site                                 | 4 hours     |
| M6 | Enforce mypy in lint job                                       | 1 hour + fixes |

### LOW (defer)

| #  | Item                                                           | Why low                       |
| -- | -------------------------------------------------------------- | ----------------------------- |
| L1 | Helm chart for Kubernetes deployment                           | Most customers use compose    |
| L2 | Multi-region / HA deployment                                   | Single-VPS covers ~99% of users |
| L3 | UI dashboard (non-MCP)                                         | Audience prefers CLI/MCP      |
| L4 | i18n of error messages                                         | Audience is English-fluent    |
| L5 | Plugin marketplace                                             | Need 10+ third-party plugins first |

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

## 8. Recommended 12-Week Roadmap

| Week  | Theme                              | Output                                                                            |
| ----- | ---------------------------------- | --------------------------------------------------------------------------------- |
| 1     | CI hardening                       | Live integration + e2e tests in CI; branch protection done; SBOM step added.      |
| 2     | Phase 1 plumbing                   | `src/db_factory.py` + env-var routing for all 4 DB tiers; no functional change.   |
| 3-4   | Apache AGE adapter                 | `apache_age` provider working end-to-end; passing all integration tests.          |
| 5-6   | MAS integration sprint             | MAS reads/writes Enhanced Cognee memories; auth wiring; agent-ID mapping.         |
| 7     | ArcadeDB adapter                   | `arcadedb` provider working; documentation; benchmark vs AGE.                     |
| 8     | OpenTelemetry + observability      | `init_tracing()` wired; SigNoz config added; OBSERVABILITY_SWAP.md doc.           |
| 9     | Lean profile + `examples/`         | One-container `lean` profile; 4-5 Enhanced-specific example scripts.              |
| 10    | Documentation site                 | mkdocs-material at `vincentspereira.github.io/Enhanced-Cognee/`.                  |
| 11    | Performance run                    | Locust against live stack; documented p50/p95/p99; perf regression dashboard.     |
| 12    | Polish + first commercial release  | `CONTRIBUTING.md`, issue templates, release notes, SBOM, "v1.0.0-commercial" tag. |

**Total effort:** ~1 FTE for 3 months. Realistically spread to 4-6 months
alongside other work.

---

## 9. Appendix: Decision Records

| #     | Decision                                                         | Date       | Rationale                                                                             |
| ----- | ---------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------- |
| DR-01 | Fork from `topoteretes/cognee` rather than build from scratch    | 2025-Q4    | Inherit a mature pipeline + actively maintained upstream; add what's missing.         |
| DR-02 | 4-DB stack (Postgres + Qdrant + Neo4j + Redis-then-Valkey)       | 2025-Q4    | Each DB optimised for its tier; complexity tradeoff acceptable for production use.    |
| DR-03 | Replace Redis with Valkey 8                                      | 2026-Q1    | Redis 7.4 license shift (BSL/SSPL) incompatible with Apache-2.0 commercialisation.    |
| DR-04 | Keep Neo4j Community as default graph DB (Phase 1-14)            | 2025-Q4    | GPLv3 in self-host/SaaS model is safe; production-proven; APOC ecosystem.             |
| DR-05 | **Plan migration to Apache AGE as default graph DB**             | **2026-05-19** | Eliminates only GPLv3 component; one fewer container; reuses Postgres ops tooling. |
| DR-06 | ArcadeDB as secondary pluggable graph DB                         | 2026-05-19 | Apache-2.0 dedicated graph engine for customers wanting Bolt drop-in or higher scale. |
| DR-07 | Keep Grafana/Loki as default monitoring; document SigNoz / VictoriaLogs as Apache-2.0 swap | 2026-05-19 | AGPLv3 is fine for self-host; provide swap path for distributed products.          |
| DR-08 | Pluggable DB backends via env vars (gradual, Tier 1/2/3)         | 2026-05-19 | Default unchanged; new providers opt-in; minimises regression risk.                   |
| DR-09 | Apache-2.0 license for all Enhanced Cognee code                  | 2025-Q4    | Maximally permissive; aligned with upstream and Python ecosystem norms.               |
| DR-10 | ASCII-only output rule                                           | 2025-Q4    | Windows cp1252 console support; enforced via pre-commit hook.                         |

---

**End of strategy document.** For change requests or new decisions, append to the
Decision Records table and update the relevant section.
