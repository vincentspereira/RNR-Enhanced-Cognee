# Phase 0 Pre-flight Report

**Date**: 2026-05-13
**Author**: Claude (Anthropic)
**Status**: COMPLETE

---

## 1. Executive Summary

Phase 0 pre-flight is complete. All four checklist items pass. The Enhanced Cognee development environment is ready to begin Phase 1 work.

| Check                            | Status  | Notes                                      |
| -------------------------------- | ------- | ------------------------------------------ |
| Docker stack starts cleanly      | OK      | All 4 Enhanced containers healthy          |
| Port assignments have no conflict | OK     | Enhanced uses 25xxx/26xxx/27xxx; no clashes|
| Unit test suite is green         | OK      | 461/461 tests pass in 13.89s               |
| .upstream-sync/ initialised      | OK      | last_seen_release.txt = v0.5.1             |

---

## 2. Docker Stack Status

All Enhanced Cognee containers are running and healthy:

| Container          | Port mapping         | Status        |
| ------------------ | -------------------- | ------------- |
| cognee-mcp-postgres | 25432 -> 5432       | Up, healthy   |
| cognee-mcp-qdrant   | 26333/26334 -> 6333/6334 | Up, healthy |
| cognee-mcp-neo4j    | 27474/27687 -> 7474/7687 | Up, healthy |
| cognee-mcp-redis    | 26379 -> 6379        | Up, healthy   |

The trading project also has running containers (postgres on 5432, redis on 6379, ClickHouse on 8123/9000).
No port conflicts exist between Enhanced Cognee and the trading project. Enhanced uses the 25xxx/26xxx/27xxx
range exclusively.

---

## 3. Test Suite

Command: `python -m pytest tests/unit/ -x -q --tb=short`
Result: **461 passed in 13.89s**

All Enhanced-unique modules have passing tests:
- test_cross_agent_sharing.py (24 tests)
- test_llm_session_state.py (108 tests)
- test_memory_deduplication.py (25 tests)
- test_memory_management.py (23 tests)
- test_memory_summarization.py (23 tests)
- test_performance_analytics.py (26 tests)
- test_realtime_sync.py (27 tests)
- test_remaining_modules.py (109 tests)
- test_security_modules.py (96 tests)

Integration tests exist under `tests/integration/` but were not run in Phase 0 (require Docker services
to be queried directly; deferred to Phase 1).

---

## 4. .upstream-sync/ Initialisation

Created:
- `.upstream-sync/last_seen_release.txt` = `v0.5.1`
- `docs/automation/upstream-diffs/` directory (for per-release diff reports)

The automation pipeline (Phase 5) will update `last_seen_release.txt` after each validated sync.

---

## 5. cognee-frontend/ Inventory

### Local Version
- package.json version: 1.0.0
- next.js: 16.1.1
- react: 19.2.0

### Upstream Version (v1.0.9)
- next.js: 16.0.8
- react: 19.1.2

### Assessment: Significantly behind upstream in component architecture

**Missing from local (upstream has these):**

| Package                          | Version | Purpose                              |
| -------------------------------- | ------- | ------------------------------------ |
| @mantine/core                    | latest  | Enterprise UI component library      |
| @mantine/dropzone                | latest  | File drop zone component             |
| @mantine/form                    | latest  | Form state management                |
| @mantine/hooks                   | latest  | React hooks collection               |
| @mantine/modals                  | latest  | Modal management                     |
| @mantine/notifications           | latest  | Toast notification system            |
| embla-carousel-react             | latest  | Carousel component                   |
| embla-carousel-autoplay          | latest  | Carousel autoplay plugin             |
| embla-carousel-fade              | latest  | Carousel fade transition             |
| react-markdown                   | 10.1.0  | Markdown rendering in chat           |
| react-error-boundary             | 6.0.0   | Error boundary component             |
| valibot                          | 1.2.0   | Schema validation library            |
| mantine-form-valibot-resolver    | 3.0.1   | Form + valibot integration           |

**Test infrastructure missing from local (upstream has):**
- @testing-library/react, @testing-library/jest-dom
- jest, jest-environment-jsdom, ts-jest, jest-fetch-mock

**Local-only (Enhanced enhancement):**
- @auth0/nextjs-auth0 (4.13.1) - Auth0 authentication

### Implication for Option A Rebase
The frontend will be updated as part of Option A. Auth0 integration is a local addition that needs
to be preserved during the rebase. Flag it explicitly in the Phase 4 rebase plan.

---

## 6. evals/ Inventory

The local `evals/` directory is a fully functional multi-system benchmarking suite:
- Dataset: 24-item HotpotQA subset
- Systems: Mem0, Graphiti (LightRAG/FalkorDB), Cognee
- Multiple Cognee retriever configurations benchmarked: GRAPH_COMPLETION, GRAPH_COMPLETION_COT, GRAPH_COMPLETION_CONTEXT_EXTENSION
- Modal deployment scripts for distributed execution

Upstream also has an `evals/` directory. Since we're doing Option A (full rebase to v1.0.9), the
upstream evals/ will replace this; any local-only benchmark scripts should be merged into the result.

**Assessment**: Not parity-blocking. Defer evals/ merge to Phase 4.

---

## 7. cognee/ Module Inventory

Local cognee/ contains **910 Python files** across:

| Subdirectory        | Contains                                      |
| ------------------- | --------------------------------------------- |
| cognee/api/         | FastAPI routers                               |
| cognee/modules/     | Core modules (retrieval, users, pipelines...) |
| cognee/tasks/       | Pipeline tasks                                |
| cognee/infrastructure/ | Database adapters, loaders, utils          |
| cognee/memify_pipelines/ | Feedback + session bridging pipelines   |

Notable: cognee/ already contains `memify_pipelines/`, `tasks/memify/`, `tasks/codingagents/`.
These are **v0.5.1-era stubs** - the upstream v1.0.9 versions are significantly more developed.
They will be replaced in full during Option A rebase.

---

## 8. Critical Violation: src/agents/ Hardcoded Categories

**Status: CONFIRMED VIOLATION of CLAUDE.md "no hardcoded categories" rule**

Files found under hardcoded category directories:

| Directory              | Files                                                          |
| ---------------------- | -------------------------------------------------------------- |
| src/agents/ats/        | algorithmic_trading_system.py, ats_memory_wrapper.py, risk_management.py |
| src/agents/oma/        | code_reviewer.py, oma_memory_wrapper.py                        |
| src/agents/smc/        | context_manager.py, smc_memory_wrapper.py                      |
| src/agents/{ats,oma,smc}/ | (literal shell glob mistake directory - empty or near-empty) |

**Vincent confirmed**: Archive these directories; ensure nothing else breaks.

**Pre-archive check required**: Before archiving, each file must be read to:
1. Extract any generic logic that belongs in `src/agents/_base/`
2. Confirm no other module imports from `src/agents/ats/`, `src/agents/oma/`, `src/agents/smc/`
3. Archive to `.archive/YYYY-MM-DD_hardcoded_agents/`

This is a P0 task within Phase 4 Hardening (Section 8.1.1 of the main plan).

---

## 9. scripts/ Inventory

Existing scripts (not from the sync pipeline):

| Script                     | Purpose                                       |
| -------------------------- | --------------------------------------------- |
| backup_all.sh              | Full stack backup                             |
| backup_postgresql_16.sh    | PostgreSQL backup                             |
| migrate_to_postgresql_18.sh | Migration script                             |
| restore_all.sh             | Full stack restore                            |
| restore_neo4j.sh           | Neo4j restore                                 |
| restore_postgres.sh        | PostgreSQL restore                            |
| restore_qdrant.sh          | Qdrant restore                                |
| restore_redis.sh           | Redis restore                                 |
| security_audit.py          | Security audit script                         |
| update_pgvector.sh         | pgVector upgrade script                       |

Scripts needed (to be created in Phase 5):
- scripts/upstream_diff.py
- scripts/auto_port.py
- scripts/check_ascii_output.py
- scripts/check_no_hardcoded_categories.py
- scripts/upstream_check.py
- scripts/mcp_smoke_test.py

---

## 10. Key Decisions from Vincent's Approval

These answers from Section 13 of the main plan shape all subsequent phases:

| Question                  | Vincent's Decision                                                             |
| ------------------------- | ------------------------------------------------------------------------------ |
| Frontend scope            | Update cognee-frontend/ to match Original v1.0.9                               |
| Cloud mode                | Yes, support cognee.serve() cloud connectivity                                  |
| Graph backend             | Keep Neo4j (confirmed; no Ladybug swap)                                        |
| Rebase strategy           | Option A: Full rebase onto Original v1.0.9 stable                              |
| Auto-merge                | No auto-merge; Vincent is sole merger; guidance will be in UPSTREAM_SYNC_RUNBOOK.md |
| Notification channel      | Email to vincentspereira@outlook.com when automation opens a PR                |
| Breaking change handling  | See Section 11 below (recommendation accepted)                                 |
| src/agents/{ats,oma,smc}  | Archive; ensure nothing breaks                                                  |

---

## 11. Breaking Change Handling Recommendation

For upstream releases containing mandatory schema migrations or breaking API changes, the recommended
approach is **(a) + (c) combined**:

**Always:**
1. Open a **draft PR** with labels `breaking-change` and `needs-review`
2. Never auto-port the breaking change code
3. Open a separate **GitHub Issue** titled "[Breaking Change] cognee <tag>: <brief description>"
   with a migration plan checklist

**The issue serves as:**
- A permanent record of the breaking change
- A checklist for Vincent to follow before merging the PR
- A place to track any downstream impact on Enhanced-unique modules

**Example for a schema migration:**
```
Issue: [Breaking Change] cognee v1.1.0: users table schema change
Checklist:
  [ ] Back up PostgreSQL data
  [ ] Review alembic migration script for Enhanced compatibility
  [ ] Run migration on staging
  [ ] Confirm Enhanced-specific tables not affected
  [ ] Approve and merge draft PR
  [ ] Update last_seen_release.txt to v1.1.0
```

This ensures Vincent has both the PR (code) and the issue (action plan) in one coordinated workflow.

---

## 12. Option A Rebase: What This Means for the Phase Plan

Vincent chose **Option A: Full rebase onto Original v1.0.9**.

This changes the phase execution order:

| Original Plan             | Revised (Option A)                                          |
| ------------------------- | ----------------------------------------------------------- |
| Phase 1: Cherry-pick P0 ports | Phase 1: Prepare rebase (freeze Enhanced, set up worktree)|
| Phase 2: Cherry-pick P1 ports | Phase 2: Execute rebase onto v1.0.9                       |
| Phase 3: Cherry-pick P2 ports | Phase 3: Restore Enhanced-unique features on top of rebase|
| Phase 4: Hardening + Rebase | Phase 4: Hardening (post-rebase cleanup)                  |
| Phase 5: Automation        | Phase 5: Automation (same)                                  |
| Phase 6: Docs              | Phase 6: Docs + rollout (same)                              |

**Rebase approach (detailed):**

1. Clone upstream cognee at v1.0.9 into a temporary directory
2. Identify all Enhanced-unique commits/changes (diff Enhanced vs v0.5.1 baseline)
3. Create a new branch `rebase/onto-v1.0.9`
4. Copy upstream v1.0.9 cognee/ into Enhanced
5. Overlay Enhanced-unique modules from `src/` (these are separate from `cognee/` and mostly unaffected)
6. Overlay Enhanced-specific changes to cognee/ (pyproject.toml port additions, etc.)
7. Resolve conflicts
8. Run full test suite
9. Open PR for Vincent's review

Gate G1 (Phase 1) is re-scoped: instead of approving cherry-pick P0 ports, it approves the rebase plan
and worktree setup.

---

## 13. Next Steps: Gate G1

Phase 0 is complete. The deliverable (this report) is ready.

**Gate G1 requires Vincent to approve:**

1. The revised Phase 1 scope: prepare the rebase worktree for Option A
2. The specific file list for the rebase (what gets replaced vs preserved)
3. The acceptance criteria: full test suite green post-rebase

**Proposed G1 tasks (TASKS-PHASE-1.md):**

- [ ] Create `TASKS-PHASE-1.md` with detailed rebase checklist
- [ ] Create rebase worktree branch: `rebase/onto-v1.0.9`
- [ ] Clone upstream v1.0.9 and diff against v0.5.1 to identify Enhanced patches
- [ ] Port cognee/ from v1.0.9 into Enhanced
- [ ] Overlay src/ Enhanced-unique modules (no changes needed, they are decoupled)
- [ ] Resolve pyproject.toml merge (keep Enhanced-added deps, take upstream version bumps)
- [ ] Run 461 unit tests; target: 461/461 pass
- [ ] Run integration tests against Docker stack; target: all pass
- [ ] Open PR: `[Phase 1] Rebase cognee/ onto v1.0.9`
- [ ] Assign reviewer: vincentspereira

The email notification for Phase 5 automation PRs will be wired in Phase 5. For Phase 1-4 manual PRs,
the PR description will include @vincentspereira review request via GitHub.

---

## 14. Approval

Please indicate approval to proceed to Phase 1 by replying "Proceed to Phase 1" or provide any
corrections/adjustments first.

**Drafted by**: Claude (Anthropic) on 2026-05-13
**Phase 0 Duration**: <1 hour (research + report)
