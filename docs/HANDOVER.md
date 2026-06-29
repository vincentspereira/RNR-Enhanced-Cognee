# RNR Enhanced Cognee — Session Handover Brief

**Audience:** A fresh Claude Code Terminal session (paste this file's contents
into your first message, or `cat docs/HANDOVER.md` and ask Claude to read it).

**Created:** 2026-05-19 by the prior Claude Desktop session.

**Authoritative reference for everything below:** [`docs/STRATEGY.md`](./STRATEGY.md)

---

## 1. Project location and rules

- **Repo root:** `C:\Users\vince\Projects\AI Agents\RNR Enhanced Cognee\`
- **Upstream:** `topoteretes/cognee` (we are a fork at `vincentspereira/RNR-Enhanced-Cognee`)
- **Default branch:** `main` (protected — see §5 below)
- **Always read first:** the project's `CLAUDE.md` (project-wide rules) and
  the user's `~/.claude/CLAUDE.md` (personal rules).
- **HARD RULES** that apply to every file you touch:
  - **ASCII-only output** in code, tests, logs, scripts (Windows cp1252 console
    cannot print Unicode — use `OK`, `WARN`, `ERR`, `[OK]`, `[ERROR]`, etc.
    Never `✓`, `✗`, `→`, emojis).
  - **No hardcoded categories** (`ATS`/`OMA`/`SMC` etc.); load from
    `.enhanced-cognee-config.json`.
  - **No emojis in new files** unless the user explicitly requests it.

---

## 2. Where we are right now (state of the world)

### Tests
- **4,158 tests passing, 0 failed, 0 skipped, 0 warnings, 95% coverage.**
  Per-job CI now runs `tests/unit/` + `tests/system/`. Integration tests run
  separately and are `continue-on-error: true` (they require live external
  services that aren't all wired into CI yet).

### CI
- Authoritative workflow: `.github/workflows/ci-cd-pipeline.yml`.
- All other workflows in `.github/workflows/` that came from upstream are
  converted to `workflow_dispatch:` only (`test_suites.yml`, `testing.yml`,
  `release_test.yml`, `dockerhub.yml`, `dockerhub-mcp.yml`, `approve_dco.yaml`).
- 4 required status checks on `main`:
  `Lint and Code Quality`, `Unit Tests`, `Security Audit`, `Integration Tests`.
- Branch protection: required PR + required status checks + required
  conversation resolution. **`enforce_admins=false`** so admins can break-glass
  if needed; **`required_approving_review_count=0`** for single-maintainer fork.
- Use `gh pr merge --squash --delete-branch` (no admin override needed when
  all required checks are green).

### Stack
- **PostgreSQL 18 + pgvector** — port 25432
- **Qdrant 1.12.0** — port 26333
- **Neo4j 5.25-community** — port 27687 (default today; **scheduled to be
  replaced by ArcadeDB** — see §3)
- **Valkey 8** — port 26379 (already replaced Redis)
- **MCP server:** `bin/enhanced_cognee_mcp_server.py` (122 `@mcp.tool()` decorators)

### Most recent merged work
| PR  | Title                                                              |
| --- | ------------------------------------------------------------------ |
| #14 | docs: README refresh + license/pluggable-DB/gap-analysis docs      |
| #15 | chore(ci): fix CI workflows + docs polish                          |
| #16 | docs: README fixes (6 items) + new STRATEGY.md                     |

---

## 3. Updated decisions you must honour (revised 2026-05-19)

These OVERRIDE earlier proposals in older docs. The current `docs/STRATEGY.md`
already reflects them (see DR-11 and DR-12 in the Decision Records appendix).

### 3.1 Pluggable Database Backends — defaults and env-var names

| Tier        | Default       | Env var                       | Pluggable alternatives                                                                                          |
| ----------- | ------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Relational  | **postgres**  | `ENHANCED_RELATIONAL_PROVIDER`| `sqlite` (testing / lean profile only)                                                                          |
| Vector      | **qdrant**    | `ENHANCED_VECTOR_PROVIDER`    | `pgvector`, `lancedb`, `weaviate`, `milvus`, `chroma`                                                           |
| Graph       | **arcadedb**  | `ENHANCED_GRAPH_PROVIDER`     | `neo4j`, `apache_age`, `arangodb`, `tigergraph`, `nebulagraph`, `networkx_inmemory`, `memgraph`, `kuzu`, `ladybug` |
| Cache       | **valkey**    | `ENHANCED_CACHE_PROVIDER`     | `redis`, `redis_compat`, `memcached`, `in_memory`                                                               |

> **Important:** the graph default has flipped from the older proposal.
> ArcadeDB is now the default (because of Cypher + Bolt drop-in compatibility
> with our existing Neo4j paths). Apache AGE is one of the pluggable options,
> NOT the default. Don't get confused by older drafts that suggested AGE first.

### 3.2 Observability stack — SigNoz + Apache Superset (revised 2026-05-19)

Today's RNR Enhanced Cognee monitoring stack (in the optional
`monitoring/docker-compose-monitoring.yml`) bundles **Grafana + Loki + Tempo + Prometheus + Jaeger**.
Of those, Grafana, Loki, and Tempo are AGPLv3. Replace them with a fully
permissive stack:

| Tier                          | New component        | License    | Repo                                       |
| ----------------------------- | -------------------- | ---------- | ------------------------------------------ |
| Metrics scraping              | **Prometheus** (kept) | Apache-2.0 | <https://github.com/prometheus/prometheus> |
| Logs + metrics + traces + APM + alerts + LLM-obs | **SigNoz**         | **MIT**    | <https://github.com/SigNoz/signoz>         |
| SigNoz storage backend        | **ClickHouse**       | Apache-2.0 | <https://github.com/ClickHouse/ClickHouse> |
| BI / analytical dashboards    | **Apache Superset**  | Apache-2.0 | <https://github.com/apache/superset>       |

**Jaeger is removed entirely** — SigNoz ingests OTel traces directly via its
OpenTelemetry Collector. **Earlier OpenObserve recommendation is SUPERSEDED**
(AGPL-3.0 same as Grafana stack — not a licensing improvement). See
[`STRATEGY.md` §5.2](./STRATEGY.md#52-observability-stack--signoz-mit--apache-superset-apache-20-replace-grafana--loki--tempo--jaeger)
for the full rationale.

**Touch-points to change:**
- `monitoring/docker-compose-monitoring.yml` → swap Grafana + Loki + Tempo +
  Jaeger for SigNoz stack (signoz-frontend + query-service + otel-collector +
  clickhouse + zookeeper + alertmanager) + Apache Superset. Prometheus stays.
- `monitoring/dashboards/*.json` → split. APM-style dashboards (request
  latency, error rates, RED metrics) migrate to SigNoz natively. Custom
  analytical dashboards (memory growth over time, agent activity trends)
  rebuilt in Apache Superset and exported to `monitoring/superset-dashboards/`.
- `src/tracing.py` OTLP endpoint → point at SigNoz collector (default
  `http://localhost:4317` for gRPC or `4318` for HTTP).
- **Keep** `prometheus-client==0.25.0` and `opentelemetry-api/sdk==1.41.1`
  in `requirements.txt` — SigNoz consumes both natively.
- `docs/MONITORING.md` → rewrite for the new stack (section per component).
- `docs/COMMERCIALISATION_LICENSE_GUIDE.md` → update the FAQ "What if I want
  to remove all GPL/AGPL components entirely?" — the answer is now "the
  default stack already is".

**Alternative for teams that want a different UX (still MIT):** HyperDX
(<https://github.com/hyperdxio/hyperdx>) — MIT app, Kibana-style query-driven
exploration, but ⚠️ bundles MongoDB (SSPL) for its metadata store. Self-host
use is fine; distributed-product bundling is more restrictive than SigNoz's
ClickHouse-only path. Use SigNoz as primary; document HyperDX as fallback.

---

## 4. Your scope of work (this session)

### Phase 1 — Pluggable DB plumbing (target: 1 week)

The goal is to make env-var routing work for all 4 DB tiers **without changing
any external behaviour**. After Phase 1, the default Docker Compose still
gives you Postgres + Qdrant + Neo4j + Valkey; the difference is that
`ENHANCED_GRAPH_PROVIDER=foo` will route to a `foo` adapter.

Steps:

1. **Audit hard-coded providers in source.**
   ```bash
   # Common starting points
   grep -rn "QdrantClient\|GraphDatabase.driver\|asyncpg.create_pool\|redis.Redis" src/ bin/
   ```
   Likely culprits: `src/agent_memory_integration.py`, `src/db_pool_manager.py`,
   any `*_manager.py` or `*_service.py` that talks directly to a DB.

2. **Create `src/db_factory.py`.** Pattern:
   ```python
   # src/db_factory.py
   import os

   def get_vector_engine():
       provider = os.getenv("ENHANCED_VECTOR_PROVIDER", "qdrant").lower()
       if provider == "qdrant":
           from src.db_adapters.vector_qdrant import QdrantAdapter
           return QdrantAdapter()
       if provider == "pgvector":
           from src.db_adapters.vector_pgvector import PgVectorAdapter
           return PgVectorAdapter()
       raise ValueError(f"Unknown ENHANCED_VECTOR_PROVIDER={provider}")
   # ... same pattern for graph / cache / relational
   ```
   Each adapter implements a Protocol/ABC defined in `src/db_adapters/_base.py`.

3. **Migrate one tier at a time.** Start with **graph** since that's where the
   ArcadeDB swap will land (Phase 2). Keep Neo4j as the default adapter even
   after Phase 1 — defaults flip in Phase 2.

4. **Test changes against existing test suite.** All 3,737 unit tests +
   421 system tests must still pass.

### Phase 2 — ArcadeDB as new default graph DB (target: 1-2 weeks)

1. **Adapter** at `src/db_adapters/graph_arcadedb.py`. Use the
   [ArcadeDB Bolt driver](https://docs.arcadedb.com/#API-Bolt) — Cypher
   queries will mostly work as-is.
2. **Docker Compose update:** swap `neo4j:5.25-community` for
   `arcadedata/arcadedb:latest` in `docker/docker-compose-enhanced-cognee.yml`.
   Update healthcheck (ArcadeDB has an HTTP `/health` endpoint).
3. **Env-var defaults update:** flip `ENHANCED_GRAPH_PROVIDER` default to
   `arcadedb` in:
   - `bin/enhanced_cognee_mcp_server.py` (startup config)
   - `docker/docker-compose-enhanced-cognee.yml` (service env)
   - `deploy/local/install.ps1` and `deploy/vps/install.sh`
   - `.env.example` (if it exists)
4. **Cypher dialect smoke test:** sweep `src/` for `session.run(...)` calls and
   verify queries work in ArcadeDB. Most will. Document any that don't in
   `docs/ARCADEDB_MIGRATION.md`.
5. **Tests:** the existing integration tests (`tests/integration/test_neo4j_*.py`)
   should be renamed/duplicated to cover both Neo4j (now pluggable) and
   ArcadeDB (new default). Parametrise where reasonable.
6. **README update:** the Mermaid diagram + Database Layer section + Quick
   Install expected output (`neo4j-enhanced` → mention both, but the new
   container name will be `arcadedb-enhanced`).

### Phase 3 — Apache AGE pluggable + `lean` profile (target: 1 week)

1. **Adapter** at `src/db_adapters/graph_apache_age.py`. Cypher queries via
   the `age` Postgres extension; talk over `psycopg2`.
2. **`lean` profile** in `deploy/profiles/lean.yaml`:
   ```
   ENHANCED_RELATIONAL_PROVIDER=postgres
   ENHANCED_VECTOR_PROVIDER=pgvector
   ENHANCED_GRAPH_PROVIDER=apache_age
   ENHANCED_CACHE_PROVIDER=in_memory
   ```
   This profile gives you a one-container deployment (just Postgres with
   pgvector + age extensions, plus the MCP server itself).
3. **Documentation:** `docs/PROFILES.md` documenting the
   `production` / `apache_only` / `lean` / `byo` presets from STRATEGY.md §4.1.

### Phase 4 — SigNoz + Apache Superset observability swap (target: 1-2 weeks)

1. **Rewrite `monitoring/docker-compose-monitoring.yml`** to bring up the new
   stack (snippet in [`STRATEGY.md` §5.3](./STRATEGY.md#53-what-this-means-for-enhanced-cognees-current-observability-touch-points)):

   ```yaml
   services:
     prometheus:                # Apache-2.0 (kept)
     signoz-otel-collector:     # MIT app + Apache-2.0 collector binary
     signoz-clickhouse:         # Apache-2.0
     signoz-zookeeper:          # Apache-2.0 (ClickHouse coordination)
     signoz-query-service:      # MIT
     signoz-frontend:           # MIT
     signoz-alertmanager:       # MIT
     superset:                  # Apache-2.0 (reuses our Postgres for metadata)
   ```

   Delete the Grafana, Loki, Tempo, and Jaeger services from the compose file.

2. **Update `src/tracing.py`** OTLP endpoint to SigNoz's collector
   (`http://localhost:4317` gRPC default, or `4318` HTTP). Keep
   `opentelemetry-api/sdk` in `requirements.txt` unchanged.

3. **Migrate dashboards** in two places:
   - **APM-style dashboards** (request rates, error rates, p95 latency,
     trace flamegraphs) → these are native to SigNoz; just re-create what
     was in Grafana inside the SigNoz UI. Most are auto-generated from the
     OTel data — minimal hand-rolling needed.
   - **Custom analytical dashboards** (memory growth over time, agent
     activity heatmaps, LLM cost trends) → rebuild in Apache Superset
     querying ClickHouse directly. Export as JSON to
     `monitoring/superset-dashboards/`.

4. **Update `docs/MONITORING.md`** with the new setup. One section per
   component (Prometheus, SigNoz, ClickHouse, Apache Superset). Include the
   OTLP endpoint URLs the user can paste into their RNR Enhanced Cognee `.env`.

5. **Update `docs/COMMERCIALISATION_LICENSE_GUIDE.md`** — the FAQ "What if I
   want to remove all GPL/AGPL components entirely?" now answers "the default
   monitoring stack already is, after Phase 4 ships". Mark the previous
   Grafana/Loki AGPL paragraph as historical / pre-Phase-4.

6. **(Optional but recommended)** Add a `monitoring/docker-compose-monitoring-hyperdx.yml`
   file documenting the HyperDX (MIT) alternative deployment for teams that
   prefer Kibana-style query-driven UX. Flag the MongoDB-SSPL caveat in the
   file header.

**Acceptance criteria for Phase 4** in §9 below has been updated to match.

### Phase 5 — Other pluggable adapters (build on demand)

Vector adapters (`pgvector`, `lancedb`, `weaviate`, `milvus`, `chroma`),
cache adapters (`redis`, `redis_compat`, `memcached`, `in_memory`),
relational `sqlite`, and the long tail of graph adapters
(`arangodb`, `nebulagraph`, `kuzu`, `networkx_inmemory`, `memgraph`, `ladybug`).
Each is a 1-3 day adapter file + adapter-specific tests.

Build these only when a paying customer asks or you're already in that area.

---

## 5. Outstanding items & gap analysis

See [`docs/STRATEGY.md` §7](./STRATEGY.md#7-outstanding-items--gap-analysis) for
the full table. Highlights:

### CRITICAL (do before commercialisation)
- **C1.** Wire live integration / E2E tests into CI (3 hours).
- ~~C2. Branch protection on `main`~~ — DONE.
- **C3.** Verify `upstream_sync` weekly cron actually sends email (wait + verify).
- **C4.** MAS integration: actually wire it (1-2 weeks).

### HIGH (within 1-2 months)
- **H1.** ArcadeDB swap (Phase 2 above).
- **H2.** SBOM (Software Bill of Materials) step in CI (`pip-licenses` or
  `cyclonedx-py`) — 2 hours.
- **H3.** Finish OpenTelemetry / SigNoz wiring — 1-2 weeks.
- **H4.** Performance tests: run locust against live stack, document p50/p95/p99.

### MEDIUM
- **M1.** `examples/` directory: 4-5 Enhanced-Cognee-specific Python scripts.
- **M2.** `CONTRIBUTING.md`.
- **M3.** GitHub Issue/PR templates.
- **M4.** `pre-commit install` in installer scripts (currently optional).
- **M5.** mkdocs-material doc site → GitHub Pages.
- **M6.** Enforce mypy in lint job.

### LOW / DEFER
Helm chart, multi-region HA, UI dashboard, i18n, plugin registry. See
[STRATEGY.md §7](./STRATEGY.md#7-outstanding-items--gap-analysis).

### KNOWN QUIRKS (won't fix, just be aware)
- **Q1.** ASCII-only output rule (hard requirement).
- **Q2.** `test_security_modules.py` does global `passlib.hash` monkey-patch;
  workaround via `__globals__` patching elsewhere — don't refactor unless you
  have a reason to.
- **Q3.** Volume `redis_data` not renamed to `valkey_data` (renaming would
  orphan existing data — cosmetic only, leave it).
- **Q4.** Compose service name `redis` and env vars `REDIS_HOST/PORT` not
  renamed (would require touching every config file — internal DNS only).
- **Q5.** Docker base image bumped `python:3.11-slim` → `python:3.14-slim`
  by Dependabot; tests pass on 3.11/3.12, 3.14 should work but flag any
  C-extension build issues you hit on customer machines.

---

## 6. Documentation update checklist

When Phase 2 (ArcadeDB default) lands, update these files in the same PR:

- [ ] `README.md` — Comparison table, Mermaid diagram (graph box), Quick Install
      expected output, Architecture section.
- [ ] `docs/STRATEGY.md` — already updated 2026-05-19 to reflect the new
      direction. After Phase 2 implementation, change "scheduled" to "shipped"
      in DR-11 and the §8 roadmap.
- [ ] `docs/LICENSE_AUDIT.md` — replace "Neo4j Community (GPLv3)" line item
      with "ArcadeDB (Apache-2.0)" in the TL;DR table; move Neo4j to the
      "Alternative pluggable backends" section.
- [ ] `docs/COMMERCIALISATION_LICENSE_GUIDE.md` — Scenario 3 ("packaged
      product distribution") no longer needs the Neo4j workaround.
- [ ] `CLAUDE.md` (project root) — update the Stack section: "Neo4j" → "ArcadeDB".
- [ ] `.env.example` and `docker-compose-enhanced-cognee.yml` — env var defaults.
- [ ] `deploy/local/install.ps1` and `deploy/vps/install.sh` — match new defaults.

When Phase 4 (SigNoz + Apache Superset swap) lands:

- [ ] `monitoring/README.md` — rewrite for the new stack (Prometheus + SigNoz
      + Apache Superset; Grafana/Loki/Tempo/Jaeger gone).
- [ ] `docs/MONITORING.md` — rewrite with one section per component (and
      include OTLP endpoint URLs for `src/tracing.py` config).
- [ ] `docs/COMMERCIALISATION_LICENSE_GUIDE.md` — the FAQ "What if I want to
      remove all GPL/AGPL components entirely?" now answers "the default
      monitoring stack already is". Mark prior Grafana/Loki AGPL discussion
      as historical.
- [ ] `docs/LICENSE_AUDIT.md` — Grafana / Loki / Tempo rows move to "Removed
      in Phase 4" section; SigNoz, ClickHouse, Apache Superset added with
      their licences (MIT / Apache-2.0 / Apache-2.0).
- [ ] `monitoring/superset-dashboards/` directory created with exported
      analytical dashboards as JSON.
- [ ] (Optional) `monitoring/docker-compose-monitoring-hyperdx.yml` for the
      MIT alternative, with MongoDB-SSPL caveat in the header.

---

## 7. Working norms for this session

1. **Always create a feature branch.** `git checkout -b <type>/<topic>-YYYY-MM-DD`.
2. **Open a PR before merging** (branch protection requires it). Use
   `gh pr create --base main --head <branch>`. Wait for all 4 required CI
   checks to go green. Then `gh pr merge --squash --delete-branch`.
3. **Conventional Commits** prefixes: `feat(scope):`, `fix(scope):`,
   `chore(ci):`, `docs:`, `refactor:`, `test:`, `perf:`.
4. **Co-author trailer** on all commits Claude makes:
   ```
   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   ```
   (Adjust the model name to match whatever the current session is.)
5. **No file rewrites unless instructed.** Prefer `Edit` over `Write` for
   existing files.
6. **No new markdown files in the repo root** unless explicitly asked —
   put them in `docs/`.

---

## 8. Quick reference — files to read first

In order, when you start the new session:

1. `~/.claude/CLAUDE.md` — global Vincent rules (ASCII-only etc.)
2. `CLAUDE.md` (repo root) — RNR Enhanced Cognee project rules
3. **`docs/STRATEGY.md`** — single source of truth for direction and decisions
4. `docs/OUTSTANDING_ITEMS.md` — deep-dive on each gap (also collated in STRATEGY §7)
5. `docs/PLUGGABLE_DB_BACKENDS.md` — older deep-dive on pluggable design
   (note: superseded by STRATEGY §4 for the default-graph decision)
6. `docs/LICENSE_AUDIT.md` — per-component licence detail
7. `docs/COMMERCIALISATION_LICENSE_GUIDE.md` — scenarios for monetisation
8. `docs/DEPLOYMENT_QUICKSTART.md` — local vs VPS install paths
9. `docs/COMPARE_TO_ALTERNATIVES.md` — market positioning
10. `requirements.txt` — Python deps (look for phantoms or wrong pins before
    adding new dependencies)
11. `bin/enhanced_cognee_mcp_server.py` — the 122-tool MCP server entry point
12. `.github/workflows/ci-cd-pipeline.yml` — authoritative CI

---

## 9. Acceptance criteria for "Phase 1 + Phase 2 complete"

The user can declare the migration done when **all** of the following hold:

- [ ] `src/db_factory.py` exists; all DB instantiation routes through it.
- [ ] `ENHANCED_GRAPH_PROVIDER=arcadedb` (default) yields a working stack.
- [ ] `ENHANCED_GRAPH_PROVIDER=neo4j` still yields a working stack (no regression).
- [ ] `ENHANCED_GRAPH_PROVIDER=apache_age` yields a working stack.
- [ ] `docker compose -f docker/docker-compose-enhanced-cognee.yml up -d`
      brings up ArcadeDB instead of Neo4j by default.
- [ ] All 4,158+ tests still pass; coverage stays at or above 95%.
- [ ] CI integration tests run against the live ArcadeDB stack and pass.
- [ ] README + STRATEGY.md + LICENSE_AUDIT + COMMERCIALISATION_LICENSE_GUIDE
      all reflect the new default.
- [ ] Branch protection blocks any PR that fails the 4 required checks.

For "Phase 4 (SigNoz + Apache Superset) complete":

- [ ] `monitoring/docker-compose-monitoring.yml` brings up Prometheus + SigNoz
      stack (frontend + query-service + otel-collector + clickhouse +
      zookeeper + alertmanager) + Apache Superset. Grafana / Loki / Tempo /
      Jaeger services deleted from the compose file.
- [ ] OTel traces from `src/tracing.py` land in SigNoz (visible in the
      Traces tab of the SigNoz UI).
- [ ] Prometheus metrics from `get_prometheus_metrics` MCP tool are scraped
      by Prometheus and consumable by SigNoz.
- [ ] APM-style dashboard (latency, error rate, p95) visible in SigNoz UI.
- [ ] At least one custom analytical dashboard rebuilt in Apache Superset
      and exported as JSON to `monitoring/superset-dashboards/`.
- [ ] `docs/MONITORING.md` documents the new setup with one section per
      component.
- [ ] `docs/COMMERCIALISATION_LICENSE_GUIDE.md` updated — "remove all
      GPL/AGPL components" FAQ answers "the default already is".
- [ ] HyperDX (MIT) alternative documented as a fallback option with the
      MongoDB-SSPL caveat noted.

---

## 10. Anything else the user may have missed

Things you should proactively flag when starting the new session, in case
they weren't called out explicitly:

1. **`pyproject.toml`** still lists `neo4j>=5.28.0,<6` under the `neo4j` optional
   group. When ArcadeDB becomes the default, decide whether to also add an
   `arcadedb` optional dependency group, and whether to keep the `neo4j` one.

2. **CLAUDE.md (project root)** still mentions Neo4j on port 27687 as part of
   the "Memory Stack Architecture" section. Update when Phase 2 lands.

3. **Cognee upstream's `Ladybug` dependency.** `pyproject.toml` pins
   `ladybug==0.16.1` as a hard dependency because upstream Cognee imports it at
   module level. If Ladybug isn't installable on a customer machine (e.g.
   air-gapped without PyPI), RNR Enhanced Cognee won't import either. Worth
   evaluating whether to lazy-load it.

4. **The `AGENTS.md` file at repo root** is untracked (was visible in `git
   status` last session). Decide whether to commit, gitignore, or leave alone.

5. **`graphify-out/GRAPH_REPORT.md`** auto-regenerates on every commit (via
   post-commit hook). It IS gitignored, but the hook output is noisy in
   terminal — ignore it.

6. **The `.beads/` directory** sometimes throws `Warning: Failed to import bd
   changes after merge / Run 'bd import -i .beads/issues.jsonl' manually to
   see the error`. Ignore; it's a Vincent's local-tooling thing, unrelated to
   RNR Enhanced Cognee functionality.

7. **Hetzner CX22 VPS deployment** target: 4 GB RAM, 2 vCPUs. ArcadeDB on
   Java 21 will use 1-2 GB; Postgres + Qdrant + Valkey + MCP server need to
   fit in the remaining ~2 GB. The SigNoz + Apache Superset monitoring stack
   is heavier (ClickHouse, multiple SigNoz services) — for a 4 GB VPS,
   consider running observability on a separate small VPS, or use SigNoz's
   all-in-one Docker image to bundle its sub-services. Watch memory limits in
   `docker-compose-production.yml`.

8. **Test pin for `pytest-asyncio`:** was relaxed to `>=0.24.0,<2.0` (was
   `==0.23.4`). Don't tighten it back without a CI run.

9. **Phantom dependencies previously removed** from `requirements.txt`:
   `rich-cli==4.3.0` (didn't exist on PyPI), `notifier==1.3.3` (didn't exist
   on PyPI), `spacy==3.8.14` (didn't exist on PyPI). If you add new deps,
   verify them with `pip index versions <pkg>` first.

10. **The user prefers** that Claude reviews and merges PRs autonomously
    (per their earlier instruction). Use `gh pr merge --squash --delete-branch`
    once the 4 required checks are green; no need to ask for permission each time.

---

**End of handover brief.** When you're ready, start by running:

```bash
cat docs/STRATEGY.md     # 600-line strategy doc
cat docs/OUTSTANDING_ITEMS.md
git log --oneline -10    # see recent merged work
gh pr list --state merged --limit 5
```

Then plan your first concrete deliverable (probably Phase 1 plumbing) and
open a feature branch. Good luck.
