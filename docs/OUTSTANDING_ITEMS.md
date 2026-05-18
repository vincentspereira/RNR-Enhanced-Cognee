# Outstanding Items & Gap Analysis

A frank look at what's still rough or missing in Enhanced Cognee as of
2026-05-18. Categorised by urgency.

---

## CRITICAL (do before commercialisation)

### 1. Real integration / E2E tests against the live stack in CI

**Status:** 158 live integration + e2e tests run locally; CI pipeline does
NOT yet run them (CI uses mocked DBs).

**Risk:** A regression in a real DB driver (asyncpg, qdrant-client, neo4j,
redis-py) could ship to main without anyone noticing.

**Fix:** Add a `integration-tests` job to `.github/workflows/ci-cd-pipeline.yml`
that spins up the docker-compose stack and runs `pytest tests/integration/
tests/e2e/`. Estimated effort: 2-3 hours.

### 2. Branch protection on main

**Status:** Not yet configured (banner visible on the GitHub page).

**Risk:** Anyone with write access can force-push or delete main.

**Fix:** Follow the steps in the prior summary -- 5 minutes via GitHub UI.

### 3. GitHub Actions secrets - verify the upstream_sync workflow actually fires email

**Status:** Workflow now uses the auto-create-label fix; Gmail App Password
is configured. Last manual run was tested, but the regular Monday cron has
not run yet.

**Risk:** If the cron fails silently, you won't notice upstream releases.

**Fix:** Wait for next Monday 08:00 UTC, then verify an email arrived (or
the no-op log entry appeared). If neither, debug.

### 4. Multi-Agent System integration: actually do it

**Status:** Design doc + recommendations exist in
`deploy/integration-with-mas/README.md`. Code-level wiring not yet done.

**Risk:** MAS won't actually consume Enhanced Cognee memories until this
is implemented.

**Fix:** Allocate 1-2 weeks for the integration sprint. Follow the
agent-ID mapping table in the integration README.

---

## HIGH (do within 1-2 months)

### 5. Apache AGE adapter (graph DB swap)

**Status:** Designed in `docs/PLUGGABLE_DB_BACKENDS.md`, not yet built.

**Why important:** Eliminates the last GPLv3 dependency. Especially
valuable if you commercialise.

**Effort:** 1 week.

### 6. SBOM (Software Bill of Materials) in CI

**Status:** Not yet wired.

**What:** Add a CI step that runs `pip-licenses --format=json` and uploads
the result as a release artefact.

**Why important:** Most enterprise customers require an SBOM for
procurement / security review.

**Effort:** 2 hours.

### 7. OpenTelemetry / Jaeger wiring

**Status:** `src/tracing.py` exists at ~70% coverage; the `@trace_tool`
decorator is implemented; just needs to be applied to MCP tool functions
and `init_tracing()` called at startup.

**Why important:** First production incident WILL need distributed traces.

**Effort:** 1-2 days.

### 8. Performance tests are stubs

**Status:** `tests/performance/benchmark_smoke.py` has 5 benchmarks but
they're rudimentary. `tests/load/locustfile.py` exists but hasn't been
run against the live stack.

**Why important:** You don't know what your real RPS / p95 ceiling is.

**Fix:** Run `locust -f tests/load/locustfile.py --headless --users 100`
against your local stack, document the p50/p95/p99 numbers in
`docs/PERFORMANCE.md`. Effort: 2 hours.

---

## MEDIUM (good hygiene, low urgency)

### 9. README "Quick Examples" → real working examples in a `examples/` directory

**Status:** README now has a Quick Examples section (added in this sprint).
But `examples/` directory still contains upstream Cognee examples, not
Enhanced-specific ones.

**Fix:** Add `examples/01_basic_memory.py`, `02_session_memory.py`,
`03_undo_redo.py`, `04_multi_agent_sharing.py`. Effort: 4 hours.

### 10. CONTRIBUTING.md

**Status:** Doesn't exist (we have CODE_OF_CONDUCT.md and SECURITY.md).

**Fix:** Write a CONTRIBUTING.md covering: dev setup (use `make install`),
testing (`make test`), commit message style, PR template, label conventions.
Effort: 2 hours.

### 11. Issue templates

**Status:** No `.github/ISSUE_TEMPLATE/`.

**Fix:** Add bug-report.yml, feature-request.yml, question.yml. Effort:
30 minutes.

### 12. PR template

**Status:** No `.github/pull_request_template.md`.

**Fix:** Standard checklist (tests, docs updated, screenshots if UI).
Effort: 15 minutes.

### 13. Pre-commit hooks not enforced

**Status:** `.pre-commit-config.yaml` exists; `make install` does NOT
install hooks.

**Fix:** Add `pre-commit install` to the installer scripts. Effort:
15 minutes.

### 14. Documentation site (e.g. mkdocs + GitHub Pages)

**Status:** Docs are spread across multiple .md files; no rendered site.

**Fix:** Set up `mkdocs-material` config, deploy to GitHub Pages on
release. Effort: 4 hours.

### 15. Type checking with mypy is opt-in

**Status:** mypy installed (in dev deps) but not enforced.

**Fix:** Add `mypy src/` to the lint job in CI. Effort: 1 hour (plus
fixing the type errors it surfaces).

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

## Recommended Next-Sprint Priority

If you have 1-2 weeks to invest:

1. **Live integration tests in CI** (item 1) -- prevents regressions
2. **Branch protection** (item 2) -- 5-minute fix
3. **Apache AGE adapter** (item 5) -- 1-week investment, removes biggest license worry
4. **MAS integration** (item 4) -- 1-2 weeks, delivers user value

If you have 1 week only:

1. Branch protection (5 minutes)
2. Live integration CI (3 hours)
3. MAS integration (rest of week)

The remaining items can wait until a paying customer asks or you have a
free afternoon.
