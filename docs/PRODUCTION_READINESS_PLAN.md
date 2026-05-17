# Enhanced Cognee — Production-Readiness Master Plan

**Created:** 2026-05-14
**Owner:** Vincent S. Pereira
**Status:** Active — Phase A pending start

---

## How To Use This Document

This is the single source of truth for getting Enhanced Cognee from "feature-complete"
to "deployed in production."

**For the human (Vincent):**

- Read the **Open Questions** section first. Each question is tagged with the phase it
  affects. Answer them in advance OR be ready to answer at the start of that phase.
- Track progress via the phase checkboxes.
- This doc is committed to git — review the diff when an agent updates it.

**For the agent (Sonnet / Opus / Claude Code):**

- Phases run sequentially: A -> B -> C -> D -> E. (F is parallel / optional polish.)
- Each task has a Definition of Done in its acceptance column. Do not mark complete
  without satisfying it.
- **CRITICAL RULE:** Before starting a phase, scan the Open Questions section. If any
  question tagged with the current phase is still unanswered, **stop and ask the user
  before doing any work**. Do not assume an answer.
- After completing each phase, update the checkbox below and commit this file.

---

## Current State Snapshot (as of plan creation)

| Metric                          | Value                                        |
| ------------------------------- | -------------------------------------------- |
| MCP tools shipped               | 122 (final classification: 21M / 45A / 56S)  |
| Total automated tests           | 838 (680 unit+system + 158 live integration) |
| Tests currently passing         | 831                                          |
| Tests currently failing         | 7 (all in `TestUndoManager` integration)     |
| Code coverage                   | 31% (target: 85%+)                           |
| Resource warnings from our code | 1 (audit_logger unclosed file handle)        |
| Docker stack                    | All 4 services healthy                       |
| CI/CD pipeline                  | Defined but secrets missing                  |
| Python SDK                      | `enhanced-cognee-client` published on PyPI   |
| Grafana dashboard               | Not yet built                                |

---

## Deployment Plan Targets (user-confirmed)

- **Initial:** Local / self-hosted on laptop, integrate with Multi-Agent System at
  `C:\Users\vince\Projects\AI Agents\Multi-Agent System`
- **Next:** Self-hosted on a low-cost VPS (Hetzner / DigitalOcean, target less than $10/month)
- **Future (only when monetising):** Higher-tier VPS or managed cloud
- **Cost constraint:** Zero spend during development and early production

---

## Phase Progress Tracker

- [x] **Phase A** — Stabilise 7 failing integration tests (DONE 2026-05-17, 845/845 pass)
- [ ] **Phase B** — Zero-warning hygiene
- [ ] **Phase C** — Coverage to 85%+
- [ ] **Phase D** — CI/CD secrets and missing infrastructure
- [ ] **Phase E** — Production deployment (laptop + VPS)
- [ ] **Phase F** — Quality polish (parallel / deferrable)

---

## Phase A — Stabilise the 7 Failing Integration Tests

**Goal:** All 838 tests pass. 0 failures.
**Effort:** 30-60 minutes.
**Blocks:** All subsequent phases.

### Failing tests

All 7 failures are in `tests/integration/test_backup_recovery_maintenance.py`:

- `TestUndoManager::test_undo_memory_add`
- `TestUndoManager::test_undo_memory_update`
- `TestUndoManager::test_undo_memory_delete`
- `TestUndoManager::test_undo_memory_summarize`
- `TestUndoManager::test_undo_memory_deduplicate`
- `TestUndoManager::test_undo_sharing_set`
- `TestBackupRecoveryIntegration::test_undo_redo_workflow`

All fail on `assert result["success"] == True`. This is a return-shape mismatch
between the UndoManager stubs (wired during the Phase 4 rewrite) and the integration
test contract.

### Tasks

| #   | Task                                                                                                                                                                          | Acceptance                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| A1  | Read `tests/integration/test_backup_recovery_maintenance.py` lines ~1420-1800. Document the exact return shape each `TestUndoManager` test expects (which keys, which types). | Written list of expected dict keys per test. |
| A2  | Read `src/undo_manager.py` `_undo_memory_*` and `_undo_sharing_set` methods. Document what they currently return.                                                             | Written list of actual return shapes.        |
| A3  | Pick alignment direction: align stubs to match tests (recommended — tests express the contract) OR align tests to match stubs.                                                | Decision recorded.                           |
| A4  | Implement the alignment. Expected stub return shape: `{"success": True, "undo_id": str, "operation_type": str, "restored_state": dict}`.                                      | All 7 stubs return the agreed shape.         |
| A5  | Re-run full test suite: `pytest tests/unit/ tests/system/ tests/integration/ tests/e2e/`.                                                                                     | 838 pass, 0 fail.                            |
| A6  | Commit with message `fix: align undo_manager return shapes with integration test contract`.                                                                                   | Commit pushed to main.                       |

### Gate

Before Phase B starts: all 838 tests must be green.

---

## Phase B — Zero-Warning Hygiene

**Goal:** `pytest -W error` returns 0 warnings, 0 skipped tests, 0 failures.
**Effort:** 1-2 hours.

### Known warnings

1. **Ours:** `src/audit_logger.py:162` — `ResourceWarning: unclosed file`
2. **External (litellm):** `DeprecationWarning: asyncio.iscoroutinefunction`
3. **External (neo4j):** `ResourceWarning: unclosed BoltDriver`
4. **External (qdrant):** `RuntimeWarning: Unable to close http connection`
5. **External (redis):** `ResourceWarning: unclosed Connection`
6. **External (stdlib asyncio):** `ResourceWarning: loop is closed`

### Tasks

| #   | Task                                                                                                                                                                               | Acceptance                                                           |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| B1  | Fix `src/audit_logger.py:162`. Use a context manager (`with open(...) as f:`) or close the file in `__del__`. Add a regression test.                                               | Warning no longer appears in test output.                            |
| B2  | Add `pytest.ini` `filterwarnings` block to suppress the 5 external library warnings. Each suppression must include a comment with the upstream issue URL.                          | These warnings no longer surface.                                    |
| B3  | Grep for `@pytest.mark.skip`, `pytest.skip(`, `@pytest.mark.skipif`. For each: either delete the test (if it tests dead code) or remove the skip and make it pass unconditionally. | `pytest -v` shows 0 SKIPPED lines.                                   |
| B4  | Add `filterwarnings = error::DeprecationWarning, error::ResourceWarning` to `pytest.ini` so new warnings break CI.                                                                 | Adding a deliberately deprecated call to a test file fails the test. |
| B5  | Commit and push.                                                                                                                                                                   | All 838 tests pass with `pytest -W error`.                           |

### Gate

`pytest -W error -q tests/` returns 0 warnings, 0 skips, 0 failures.

---

## Phase C — Coverage to 85%+

**Goal:** `pytest --cov=src --cov-fail-under=85` succeeds.
**Effort:** 2-3 days of focused work; parallelisable across multiple sessions.

### Coverage tiers (current state)

**T1 — Highest priority (production hot path, currently <30%):**

- `src/scheduler.py` (0%)
- `src/enhanced_cognee_mcp.py` (0%)
- `src/recovery_manager.py` (11%)
- `src/transaction_manager.py` (15%)
- `src/maintenance_scheduler.py` (16%)
- `src/undo_manager.py` (18%)
- `src/mcp_memory_tools.py` (21%)
- `src/intelligent_summarization.py` (22%)
- `src/scheduled_deduplication.py` (27%)
- `src/sqlite_manager.py` (27%)
- `src/rate_limiter.py` (28%)

**T2 — Medium priority (30-50%):**

- `src/gdpr_manager.py` (31%)
- `src/graph_compactor.py` (32%)
- `src/llm_cost_tracker.py` (32%)
- `src/memory_consolidator.py` (32%)
- `src/scheduled_summarization.py` (18%)
- `src/memory_provenance.py` (28%)
- `src/security/security_deployment.py` (28%)

**T3 — Decent (50-79%):** llm/*, security/*, integration/*, notification_manager, etc.

**T4 — Already good (80%+):** memory_reranker (95%), memory_summarization (96%),
performance_analytics (94%), structured_memory (91%), multi_language_search (89%),
progressive_disclosure (88%), memory_deduplication (87%), memory_management (80%).

**T5 — Skip (out of scope):** `cognee/*` upstream code.

### Tasks

| #   | Task                                                                                                                                                                                                         | Acceptance                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- |
| C1  | Create `.coveragerc` with `omit = cognee/*, tests/*, .venv/*, src/lite_mode/*`.                                                                                                                              | `pytest --cov=src` reports only our `src/` lines. |
| C2  | For each T1 module: create `tests/unit/test_<module>_full.py`. Cover happy path, validation errors, DB failures (mock asyncpg exceptions), edge cases (empty, oversized, concurrent). Target 85% per module. | Each T1 module reaches >=85% line coverage.       |
| C3  | Repeat C2 for T2 modules.                                                                                                                                                                                    | Each T2 module reaches >=85%.                     |
| C4  | Add `--cov-fail-under=85` to `pytest.ini` so future PRs cannot regress coverage.                                                                                                                             | CI fails on coverage regression.                  |
| C5  | Generate HTML coverage report. Add a coverage badge to README via Codecov (free for public repos) or shields.io.                                                                                             | Badge shows >=85%.                                |

### Gate

`pytest --cov=src --cov-fail-under=85 tests/` returns 0 failures.

---

## Phase D — CI/CD Secrets and Missing Infrastructure

**Goal:** Every push to `main` triggers a fully-green workflow run.
**Effort:** 2-3 hours.

### Tasks

| #   | Task                                                                                                                                                                        | Acceptance                                                                                                                    |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| D1  | **Gmail App Password setup** (see Appendix A below). Add `MAIL_USERNAME` and `MAIL_PASSWORD` to GitHub repo Secrets. Verify by manually running `upstream_sync.yml`.        | Email arrives at vincentspereira@outlook.com.                                                                                 |
| D2  | Create `tests/performance/` with `benchmark_smoke.py` using `pytest-benchmark`. Cover: add_memory throughput, search latency p50/p95/p99, deduplication speed.              | `pytest tests/performance/ --benchmark-only` runs.                                                                            |
| D3  | Create `tests/load/locustfile.py` (referenced in CI but missing). Three user classes: ReadHeavy, WriteHeavy, MixedWorkload. Target 100 concurrent users at 10 RPS.          | `locust -f tests/load/locustfile.py --headless --users 100 --spawn-rate 10 --run-time 30s --host http://localhost:8000` runs. |
| D4  | Audit `.github/workflows/ci-cd-pipeline.yml`. Fix any step that references a missing file. Set `continue-on-error: false` everywhere it currently swallows errors silently. | Manual workflow_dispatch run on main shows all jobs green.                                                                    |
| D5  | Add a `Makefile` or `invoke` tasks.py with one-command shortcuts: `make test`, `make coverage`, `make lint`, `make stack-up`, `make stack-down`, `make smoke`.              | Each command works locally.                                                                                                   |

### Gate

Push to `main` -> every workflow goes green.

---

## Phase E — Production Deployment (Laptop + VPS)

**Goal:** Repeatable "one-script deploy" for both targets. Zero cloud bills initially.
**Effort:** 4-6 hours.

### Tasks

| #   | Task                                                                                                                                                                                                                                                                                                              | Acceptance                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| E1  | Create `deploy/local/install.ps1` (Windows) and `deploy/local/install.sh` (Linux/macOS). Idempotent. Steps: clone repo, build `.venv`, `pip install -e .`, `docker compose -f docker/docker-compose-enhanced-cognee.yml up -d`, register MCP server in `~/.claude.json`.                                          | Fresh machine reaches working MCP server in under 5 minutes. |
| E2  | Create `deploy/vps/README.md`: step-by-step Ubuntu 24.04 setup on a low-cost VPS (Hetzner CX22 ~4.50 EUR/mo or DigitalOcean $6/mo). Install Docker, clone, run compose, UFW (only 22 + 443 open), Caddy for automatic HTTPS, systemd for auto-restart. No Kubernetes, no managed DBs.                             | Documented runbook.                                          |
| E3  | Add `deploy/vps/Caddyfile` template. Reverse-proxies HTTPS to FastAPI MCP variant (`src/enhanced_cognee_mcp.py`) with automatic Let's Encrypt cert.                                                                                                                                                               | TLS works on port 443.                                       |
| E4  | Add `deploy/vps/backup.sh` cron script. Nightly export of postgres + redis + neo4j to `/var/backups/enhanced-cognee/`. 30-day rotation.                                                                                                                                                                           | Backups appear after one run.                                |
| E5  | Create `deploy/integration-with-mas/README.md`. How to wire Enhanced Cognee as memory layer for `C:\Users\vince\Projects\AI Agents\Multi-Agent System`. Includes: `mcpServers` config block, agent-id conventions (trading-bot, sdlc-agent, analysis-agent), category prefixes (`trading_`, `dev_`, `analysis_`). | MAS can call all 122 tools end-to-end.                       |
| E6  | Create `docs/operations/RUNBOOK.md`. "What to do when..." for 10 common incidents: postgres down, qdrant slow, undo log full, backup failure, disk full, network partition, container OOM, SSL cert expiry, MCP server hang, schema migration failure. Each section has copy-pasteable commands.                  | Each section actionable.                                     |

### Gate

Fresh laptop installs and runs the full stack with one command.

---

## Phase F — Quality Polish (Parallel / Deferrable)

**Goal:** Long-term maintainability and observability.
**Effort:** 1-2 days, parallel to other phases.

### Tasks

| #   | Task                                                                                                                                                                                                           | Acceptance                                |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| F1  | Build `monitoring/grafana-dashboard.json`. Panels: tool call rate by trigger type (M/A/S), p50/p95/p99 latency per tool, postgres pool usage, qdrant query rate, undo operations per hour, LLM cost burn-down. | Importing into Grafana shows live data.   |
| F2  | Add startup assertion in `bin/enhanced_cognee_mcp_server.py`: `assert len(mcp._tools) == 122`.                                                                                                                 | Server refuses to start if count drifts.  |
| F3  | Multi-tenant tools: `create_tenant`, `list_tenants`, `delete_tenant`, `get_tenant_stats`. Required if monetising (one customer = one tenant).                                                                  | 4 new MCP tools (total then 126).         |
| F4  | Migrate `pip install -e .` to `uv pip install` everywhere. Document in install scripts.                                                                                                                        | Install time drops 90s -> 10s.            |
| F5  | Add `pre-commit` config: ruff, black, mypy, pytest-fast on changed files only.                                                                                                                                 | Commits get auto-checked.                 |
| F6  | Open-source release polish: `CODE_OF_CONDUCT.md`, `SECURITY.md`, semantic-release config.                                                                                                                      | Repo ready for external contributors.     |
| F7  | TD-01 cleanup: dedupe `bin/mcp_modules/` against `bin/enhanced_cognee_mcp_server.py`.                                                                                                                          | LOC reduced; tests still pass.            |
| F8  | Add `/health` HTTP probe to MCP server (separate from MCP-tool `health()`). For systemd/Caddy/uptime monitors.                                                                                                 | Returns 200/503 on plain HTTP.            |
| F9  | Wire OpenTelemetry tracing (`src/tracing.py` already at 36%) to a free self-hosted Jaeger instance.                                                                                                            | Distributed traces visible.               |
| F10 | Database migrations: introduce Alembic or Yoyo. Convert all `_ensure_schema()` calls to versioned migrations.                                                                                                  | Schema versions explicit and reversible.  |
| F11 | Encrypt `.env` at rest using `sops` + `age`.                                                                                                                                                                   | DB passwords no longer plaintext on disk. |
| F12 | Enable Dependabot for `pip` and `actions` ecosystems.                                                                                                                                                          | Weekly PRs for CVEs.                      |
| F13 | Add "Compare to alternatives" table to top of README (Enhanced Cognee vs vanilla Cognee vs Mem0 vs Letta).                                                                                                     | First-time visitor decides in <30s.       |
| F14 | Add rate limiting to FastAPI MCP transport (slowapi or starlette-limiter) for when it's internet-exposed.                                                                                                      | Per-IP throttle enforced.                 |

---

## Appendix A — Gmail App Password Setup (Concrete Steps)

You confirmed "Gmail account" — so:

1. **Open Gmail account security:** https://myaccount.google.com/security
2. **Enable 2-Step Verification** if not already on. (Required — Google blocks app
   passwords without 2FA.)
3. **Open App Passwords page:** https://myaccount.google.com/apppasswords
4. **Create an app password:**
   - App name: `Enhanced Cognee Upstream Sync`
   - Click Create
   - Google shows a 16-character password like `abcd efgh ijkl mnop`. **Copy
     immediately — shown only once.** Spaces can be kept or stripped (both work).
5. **Add to GitHub repo secrets:**
   - Open https://github.com/vincentspereira/Enhanced-Cognee/settings/secrets/actions
   - Click "New repository secret"
     - Name: `MAIL_USERNAME`
     - Value: `vincyspereira@gmail.com` (your full Gmail address, exactly that)
   - Click "Add secret"
   - Click "New repository secret" again
     - Name: `MAIL_PASSWORD`
     - Value: the 16-character app password from step 4
   - Click "Add secret"
6. **Verify by manual trigger:**
   - Browser: https://github.com/vincentspereira/Enhanced-Cognee/actions
   - Left sidebar: click "Upstream Sync Monitor"
   - Right side: click "Run workflow" dropdown
   - Branch: `main`. baseline_override: leave blank.
   - Click green "Run workflow" button.
   - Wait 10 seconds, F5 to refresh, click the new run.
   - If a new upstream release exists, `notify-email` runs and you get an email at
     vincentspereira@outlook.com within 1-2 minutes.
   - If you want to force-test even with no new release: set `baseline_override` to
     `v0.0.0` when running the workflow.
   - On failure: open the failed step's logs, look for SMTP errors. "Authentication
     failed" = wrong app password. "Username not accepted" = MAIL_USERNAME typo.

**Cost:** Free. Gmail free accounts allow ~500 outbound app-password emails/day.

---

## Open Questions (Awaiting Vincent's Decision)

> **AGENT RULE:** Before starting a phase tagged with an unanswered question,
> stop and ask the user. Do not assume answers.

| #       | Question                                                                                                                                                                                                        | Affects Phase | Status     |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ---------- |
| Q1      | For Phase E5 (MAS integration), should Enhanced Cognee be the *only* memory system the Multi-Agent System uses, or share with its existing memory layer? Affects category prefix design and migration strategy. | E             | ANSWERED   |
| Reply 1 | Enhanced Cognee should share the memory system with MAS's existing memory layer                                                                                                                                 |               |            |
| Q2      | For Phase F3 (multi-tenant), what is a "tenant"? One human user, one organisation, or one application? Affects isolation model and pricing.                                                                     | F             | ANSWERED   |
| Reply 2 | You may decide on this                                                                                                                                                                                          |               |            |
| Q3      | For Phase F1 (Grafana), do you already run Grafana somewhere, or should the plan include a `docker-compose-monitoring.yml` to spin up Prometheus + Grafana + Loki alongside the main stack?                     | F             | ANSWERED   |
| Reply 3 | Let this system be a separate system and hence, let the plan include a `docker-compose-monitoring.yml` to spin up Prometheus + Grafana + Loki alongside the main stack                                          |               |            |
| Q4      | For Phase D2/D3 (performance + load tests), what throughput targets? Suggested defaults: 100 add_memory/sec, 500 search_memories/sec, p95 latency under 200ms. Confirm or override.                             | D             | ANSWERED   |
| Reply 4 | You may decide whatever is the best for this system                                                                                                                                                             |               |            |
| Q5      | For Phase E2 (VPS), preferred provider? Hetzner CX22 (4.50 EUR/mo, EU data centre) or DigitalOcean Droplet ($6/mo, multiple regions)?                                                                           | E             | ANSWERED   |
| Reply 5 | I don't have any preferred provider. You may decide on the best for this system                                                                                                                                 |               |            |
| Q6      | For Phase C (coverage), if a T1 module turns out to be dead code (not imported anywhere in the MCP tool path), delete it OR write tests anyway?                                                                 | C             | ANSWERED   |
| Reply 6 | If a T1 module turns out to be dead code (not imported anywhere in the MCP tool path), then delete it                                                                                                           |               |            |
| Q7      | For Phase F6 (open-source polish), do you intend to accept external contributors before monetisation? Affects how strict the CONTRIBUTING and CODE_OF_CONDUCT files need to be.                                 | F             | ANSWERED   |
| Reply 7 | I may or may not accept external contributors before monetisation as I have not yet decided on this. But make provisions as though I may accept extrenal contributions.                                         |               |            |
| Q8      | For Phase E1 (laptop install), should the installer auto-start the Docker stack on Windows boot (via Task Scheduler) or be manual?                                                                              | E             | ANSWERED   |
| Reply 8 | Yes, let the installer auto-start the Docker stack on Windows boot (via Task Scheduler)                                                                                                                         |               |            |
| Q9      | For Phase F11 (encrypted secrets), the sops + age toolchain has a learning curve. Alternative: just use Docker secrets + a locked-down `.env` (chmod 600). Pick one.                                            | F             | ANSWERED   |
| Reply 9 | You may decide on the best for this system                                                                                                                                          |               |            |

---  

## Time Budget

| Phase        | Effort   | Cumulative |
| ------------ | -------- | ---------- |
| A            | 1h       | 1h         |
| B            | 2h       | 3h         |
| C            | 2-3 days | 3 days     |
| D            | 3h       | 3 days, 3h |
| E            | 6h       | 4 days     |
| F (parallel) | 2 days   | 6 days     |

**Critical path to "fully ready for self-hosted production":** A + B + C + D + E
= roughly 4 working days.

**Fastest visible-result path tonight:** A (1h) + B1 (15 min) = under 90 minutes
to "838 tests pass, 0 failures, 0 warnings from our code".

---

## Change Log

- **2026-05-14:** Plan created. All 6 phases scoped. 9 open questions logged.
