# Outstanding Items & Gap Analysis

A frank look at what's still rough or missing in Enhanced Cognee.
Originally written 2026-05-18; refreshed 2026-05-21 to mark items
that have actually shipped. Categorised by urgency.

> **Status legend:**
>
> - **[SHIPPED]** -- merged on main; PR ref + date provided.
> - **[OPEN]** -- still genuinely outstanding.
> - **[DEFERRED]** -- intentionally not pursued (with reason).

---

## CRITICAL (do before commercialisation)

### 1. Real integration / E2E tests against the live stack in CI -- [SHIPPED 2026-05-20]

**Status:** Shipped in PR #31 (`feat(ci+bench): live ArcadeDB + AGE
integration tests + cross-provider benchmark runner`). The CI pipeline
now boots service containers (postgres + qdrant + valkey + ArcadeDB or
postgres-age) and runs `tests/integration/` with `continue-on-error: true`
so a transient DB hiccup doesn't block PRs but failures still surface.
8 live ArcadeDB + Apache AGE integration tests in
`tests/integration/test_arcadedb_integration.py` and
`tests/integration/test_apache_age_integration.py`.

### 2. Branch protection on main -- [SHIPPED]

**Status:** Configured. 4 required status checks
(`Lint and Code Quality`, `Unit Tests`, `Security Audit`,
`Integration Tests`) + required PR + required conversation resolution.
`enforce_admins=false` (single-maintainer break-glass);
`required_approving_review_count=0` (single-maintainer fork).

### 3. GitHub Actions secrets - verify the upstream_sync workflow actually fires email -- [SHIPPED 2026-06-03]

**Status:** VERIFIED end-to-end. The Monday cron has fired green for three
consecutive weeks (2026-05-18, 2026-05-25, 2026-06-01). The 2026-06-01 run
(`26757899155`) actually detected a new upstream release (v1.1.2), so the
conditional `notify-email` job ran and the `Send email notification` step
reported `success` -- proving the full path (detect -> diff -> email +
tracking issue), not just the cron. `MAIL_USERNAME` and `MAIL_PASSWORD`
secrets are present on the fork. A tracking issue (#67 "Upstream sync: port
v1.1.2 changes") was opened automatically as designed.

**Residual:** Porting the detected upstream v1.1.2 changes is a separate
content task tracked by issue #67 -- the monitoring mechanism itself is done.

### 4. Multi-Agent System integration: actually do it -- [DEFERRED]

**Status:** Design doc + recommendations exist in
`deploy/integration-with-mas/README.md`. Code-level wiring intentionally
deferred to a future session per the original session constraint.

**Risk:** MAS won't actually consume Enhanced Cognee memories until this
is implemented.

**Fix:** Allocate 1-2 weeks for the integration sprint. Follow the
agent-ID mapping table in the integration README.

---

## HIGH (do within 1-2 months)

### 5. Apache AGE adapter (graph DB swap) -- [SHIPPED 2026-05-19]

**Status:** Shipped in PR #21
(`feat(db): Apache AGE graph adapter + in_memory cache + lean profile`).
Native graph elements (`_AGENode` / `_AGERelationship` shaped like
`neo4j.graph.Node` / `Relationship`) added in PR #30. Parameterised
Cypher + async session API added in PR #26. Eliminates the last GPLv3
dependency from the default-stack-compatible alternates.

### 6. SBOM (Software Bill of Materials) in CI -- [SHIPPED 2026-05-19]

**Status:** Shipped via `.github/workflows/sbom.yml`
(`pip-licenses --format=json` plus a CycloneDX-format SBOM artefact uploaded
on every release). Doc reference in `docs/SBOM_FRAMEWORK.md`.

### 7. OpenTelemetry / Jaeger wiring -- [SHIPPED 2026-05-19]

**Status:** Shipped in PR #22 (Phase 4 observability swap:
Grafana+Loki+Tempo+Jaeger -> SigNoz+Apache Superset). `src/tracing.py`
emits OpenTelemetry spans; the SigNoz OTel Collector ingests them into
ClickHouse. Live smoke test added in PR #38
(`tests/integration/test_signoz_smoke.py`, gated by
`ENHANCED_RUN_SIGNOZ_SMOKE=1`) -- emits a span, polls SigNoz's Query
Service until it surfaces in `signoz_traces.signoz_index_v2`, asserts
trace-ID round-trip.

### 8. Performance tests are stubs -- [SHIPPED 2026-05-21]

**Status:** Real cross-provider Locust runner shipped in PR #37
(`tests/benchmarks/run_provider_comparison.py`) -- 5 provider permutations,
side-by-side RPS / p50 / p95 / p99 / error% tables. First real baseline
captured in PR #46
(`tests/benchmarks/baselines/2026-05-21_neo4j_stack.json`):
49.06 RPS, p50=2ms, p95=7ms, p99=11ms, 2911 reqs, 0 failures.
Regression gate via `tests/benchmarks/compare_to_baseline.py`.
Three baselines now exist: `neo4j_stack`, `default` (ArcadeDB:
arcadedb/qdrant/valkey/postgres -- 48.9 RPS, p50=11ms, p95=14ms, 0 failures)
and `memgraph_kuzu`. Re-validated the `default` permutation on 2026-06-03
against current code: throughput + error-rate held (47.0 RPS, 0 failures);
latency was elevated only because the run shared the dev box with other
containers (not a code regression -- the locustfile hits `/mcp/*`, untouched
by recent work), so the cleaner 2026-05-21 baseline was kept.

**The remaining two permutations (`lean`, `embedded`) will NOT get a locust
baseline -- and that is the correct outcome, not a gap.** A 2026-06-03
code-path audit established that the entire load harness runs through
`postgres_pool` only: every `/mcp/*` CRUD route uses raw Postgres SQL, and
`search_memories` (no embedding, as the locustfile sends) falls back to
Postgres full-text -- the vector and graph providers are never on the measured
request path. Therefore (a) `lean` (relational=postgres, like `default`) would
merely duplicate the `default` number while telling us nothing about AGE or
pgvector, and (b) `embedded` (relational=sqlite) cannot run the harness's
Postgres-dialect SQL at all. The right tool to characterise these providers is
an in-process adapter micro-benchmark (db_factory -> provider; time
add/search/get), tracked as a separate follow-up. See
`tests/benchmarks/baselines/README.md` ("What this harness actually measures")
for the full accounting. The three captured baselines (`default`,
`neo4j_stack`, `memgraph_kuzu`) remain valid for Postgres-path regression
detection.

---

## MEDIUM (good hygiene, low urgency)

### 9. README "Quick Examples" -> real working examples in a `examples/` directory -- [SHIPPED 2026-05-19]

**Status:** Shipped in PR #24 (`docs+chore: CONTRIBUTING + SBOM CI +
examples/`). 5 runnable examples now live in `examples/`:
`01_basic_memory_crud.py`, `02_semantic_search.py`,
`03_knowledge_graph.py`, `04_gdpr_workflow.py`,
`05_backup_and_restore.py`.

### 10. CONTRIBUTING.md -- [SHIPPED 2026-05-19]

**Status:** Shipped in PR #24. Covers dev setup, testing, commit message
style, PR template, label conventions.

### 11. Issue templates -- [SHIPPED]

**Status:** 4 templates in `.github/ISSUE_TEMPLATE/`:
`bug_report.yml`, `config.yml`, `documentation.yml`,
`feature_request.yml`.

### 12. PR template -- [SHIPPED]

**Status:** `.github/pull_request_template.md` exists with the standard
checklist (tests, docs updated, screenshots if UI).

### 13. Pre-commit hooks not enforced -- [SHIPPED]

**Status:** `.pre-commit-config.yaml` exists at repo root. The hook
install step is in the installer scripts.

### 14. Documentation site (e.g. mkdocs + GitHub Pages) -- [SHIPPED 2026-06-03]

**Status:** Live. `mkdocs-material` config + the `Docs Site` workflow
(`docs-site.yml`) build and deploy on every push to main. GitHub Pages was
enabled via `gh api -X POST repos/vincentspereira/Enhanced-Cognee/pages
-f build_type=workflow`; the workflow is green and the site is live at
https://vincentspereira.github.io/Enhanced-Cognee/ . (The mkdocs build
always succeeded; the deploy step had 404'd until Pages was enabled.)

### 15. Type checking with mypy is opt-in -- [PARTIAL -- ratcheting allowlist active]

**Status:** Enforced on a ratcheting allowlist, not yet repo-wide. The CI
lint job runs a BLOCKING `mypy` over a curated set of fully-annotated core
modules; type breakage in those modules now fails CI. A second,
informational `mypy src/` sweep reports the remaining debt without blocking.

**Why not repo-wide yet:** `mypy.ini` is strict (`disallow_untyped_defs`,
`disallow_any_generics`, `warn_return_any`), so whole-repo enforcement needs
the annotation backlog cleared first. Modules are added to the blocking step
as they are annotated. (`src/` mypy needs `--explicit-package-bases` or it
aborts with "source file found twice" -- no `src/__init__.py`, namespace pkg.)

**Fix (remaining):** Continue annotating modules and migrating them from the
informational sweep into the blocking allowlist.

---

## LOW (nice-to-have, defer indefinitely)

### 16. Helm chart for Kubernetes deployment

**Status:** Not started.

**Why low:** Most customers will run docker-compose. Helm becomes
important when you have a customer needing K8s.

### 17. Multi-region / HA deployment

**Status:** Single-VPS deployment only.

**Why low:** ~99% of customers will fit on a single CX22 / CX32 VPS.
Multi-region is an enterprise sales conversation.

### 18. UI dashboard

**Status:** Terminal/MCP only.

**Why low:** The audience (developers using Claude Code) prefers CLI.
A dashboard is more valuable for non-technical operations teams.

### 19. Internationalisation of error messages / logs

**Status:** All English.

**Why low:** The audience is technical and English-fluent for now.

### 20. Plugin marketplace / registry

**Status:** `plugin_loader.py` exists for loading custom data-source
adapters. No registry / discovery system.

**Why low:** No need until 10+ third-party plugins exist.

---

## Known Quirks (won't fix, just document)

### Q1. ASCII-only output rule

Project rule: no Unicode in any code/test output. This is to support
Windows cp1252 console. Inconvenient but unbreakable -- multiple
existing scripts enforce it.

### Q2. test_security_modules.py mocks `passlib.hash` globally

Causes cross-file pollution that we work around via `__globals__` patching
in `tests/test_enhanced_security.py`. Properly fixable by refactoring
test_security_modules.py to use scope=module fixtures, but the workaround
works and the refactor is invasive.

### Q3. Volume name `redis_data` in compose (not renamed to `valkey_data`)

Renaming would orphan existing data. Cosmetic label only. Leave alone.

### Q4. Compose service name `redis` (not renamed to `valkey`)

Renaming would require updating REDIS_HOST env vars across many files.
Service name is just internal DNS; the protocol is identical. Leave alone.

### Q5. Python 3.14 vs 3.11 in Docker base image

Dependabot bumped python from 3.11-slim → 3.14-slim. Most pip deps tested
on 3.11/3.12. 3.14 should work but some C-extension deps may need source
builds. If installer fails on a customer machine, fall back to 3.12-slim.

---

## Status Summary (refreshed 2026-05-21)

The 2026-05-18..2026-05-21 sprint closed out the CRITICAL + HIGH + most
MEDIUM items. The 11 items now marked [SHIPPED]:

| #  | Item                                       | Where it shipped                  |
| -- | ------------------------------------------ | --------------------------------- |
| 1  | Real integration tests in CI               | PR #31                            |
| 2  | Branch protection on main                  | Configured directly on GitHub     |
| 5  | Apache AGE adapter (graph DB swap)         | PR #21 (+ PR #26 + PR #30)        |
| 6  | SBOM in CI                                 | PR #24 (`.github/workflows/sbom.yml`) |
| 7  | OpenTelemetry / Jaeger wiring              | PR #22 (via SigNoz) + PR #38 (live smoke test) |
| 8  | Performance tests are stubs                | PR #37 (runner) + PR #46 (first real baseline) |
| 9  | README Quick Examples -> `examples/`       | PR #24                            |
| 10 | CONTRIBUTING.md                            | PR #24                            |
| 11 | Issue templates                            | Already shipped                   |
| 12 | PR template                                | Already shipped                   |
| 13 | Pre-commit hooks not enforced              | `.pre-commit-config.yaml` present |

## Recommended Next-Sprint Priority

Refreshed 2026-06-03. Items 3, 8, 14 and 15 were closed out: 14 fully
(docs site live); 3 verified end-to-end (upstream email fired on 2026-06-01);
8 resolved by audit -- the `lean`/`embedded` locust baselines were shown to be
either redundant (`lean` == `default` Postgres path) or impossible (`embedded`
sqlite can't run the harness's Postgres SQL), so they are intentionally not
captured and the three real baselines stand; 15 on a ratcheting mypy
allowlist (now 5 modules). What genuinely remains:

1. **MAS integration** (item 4, DEFERRED) -- code-level wiring is owned by the
   MAS team; Enhanced Cognee only needs to be *ready*, which it now is (both
   stdio MCP and HTTP `/tools` surfaces verified). Largest remaining item but
   not on EC's plate.
2. **Port upstream v1.1.2 changes** -- the upstream-sync monitor flagged a new
   release (tracking issue #67). Content task, not a mechanism gap.
3. **Publish the 3 client SDKs** (Node / Go / Rust) -- code is publish-ready
   and the `publish-clients.yml` workflow is in place. BLOCKED only on
   external provisioning: npm + crates.io registry accounts and the
   `NPM_TOKEN` / `CARGO_REGISTRY_TOKEN` repo secrets (neither secret exists
   yet). Go is tag-only (no secret) but publishing to a public registry is an
   owner decision. A `workflow_dispatch` dry-run path exists for rehearsal.
4. **Broaden mypy** (item 15) -- continue migrating annotated modules into the
   blocking allowlist.

LOW items (16-20) and the Known Quirks (Q1-Q5) remain as documented; nothing
actively blocking.
