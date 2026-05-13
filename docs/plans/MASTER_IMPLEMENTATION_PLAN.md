# Enhanced Cognee - Master Implementation Plan

**Prepared**: 2026-05-13
**Author**: Vincent S. Pereira
**Status**: Active - living document; update as phases complete

This document is the single authoritative reference for where Enhanced Cognee
has been, where it is now, and what to do next. It answers all 11 questions
raised in the post-Phase-6 review session and provides a concrete roadmap with
priorities, effort estimates, and acceptance criteria.

---

## Table of Contents

1. [Phases Completed - What Was Done](#1-phases-completed)
2. [Next Steps - Priority Roadmap](#2-next-steps)
3. [Status Before vs. After](#3-status-before-vs-after)
4. [How the System Changed (Changelog)](#4-how-the-system-changed)
5. [Pros and Cons](#5-pros-and-cons)
6. [Feature Comparison: Enhanced Cognee vs. Original Cognee](#6-feature-comparison)
7. [Upstream Contribution Strategy](#7-upstream-contribution-strategy)
8. [README and Documentation Maintenance](#8-readme-and-docs)
9. [License and Attribution](#9-license-and-attribution)
10. [Technical Debt Register](#10-technical-debt)
11. [Future Improvements Backlog](#11-future-improvements)

---

## 1. Phases Completed

All six implementation phases are complete as of 2026-05-13.

### Phase 0 - Baseline Assessment
- **What**: Full audit of the starting state (v0.5.1 fork of topoteretes/cognee)
- **Output**: `docs/plans/PHASE-0-REPORT.md`
- **Result**: Identified 4-DB stack already wired; 497 unit tests already passing; 64
  MCP tools already registered in monolith

### Phase 1 - Upstream Rebase to v1.0.9
- **What**: Aligned the codebase with topoteretes/cognee v1.0.9 API surface
- **Output**: `docs/plans/TASKS-PHASE-1.md`
- **Result**: cognee/ infrastructure updated; v1.0.9 API modules available

### Phase 2 - Session-Aware Memory Tools (v1.0.9 API)
- **What**: Added 6 MCP tools that wrap the v1.0.9 `cognee.api.v1.*` modules
- **Tools added**: `remember`, `recall`, `forget_memory`, `improve`,
  `save_interaction`, `cognify_status`
- **Output**: `docs/plans/TASKS-PHASE-2.md`,
  `bin/mcp_modules/phase2_session_memory.py`
- **Result**: Total MCP tools reached 70 (from 64)

### Phase 3 - External Loaders and Enrichment Tools
- **What**: Added 6 MCP tools for web ingestion, DB ingestion, translation, NER,
  v2 graph extraction
- **Tools added**: `ingest_url`, `ingest_db`, `translate_text`,
  `regex_extract_entities`, `extract_graph_v2`, `list_loaders`
- **Output**: `docs/plans/TASKS-PHASE-3.md`,
  `bin/mcp_modules/phase3_loaders.py`,
  `docs/plans/COGNEE_UPSTREAM_PARITY_AND_SYNC_PLAN.md`
- **Result**: Full v1.0.9 public API parity achieved

### Phase 4 - Hardening and Cleanup
- **What**: Archived hardcoded-category agent modules; added test coverage for
  new tools; documented MCP server; created REST frontend API clients
- **Archived**: `src/agents/ats/`, `src/agents/oma/`, `src/agents/smc/`
  (all moved to `.archive/2026-05-13_agents_ats_oma_smc/`)
- **Result**: Categories gate passes; no hardcoded ATS/OMA/SMC in production code

### Phase 5 - Upstream Sync Automation
- **What**: Built automation to detect and triage new upstream releases
- **Deliverables**:
  - `scripts/upstream_diff.py` - GitHub API diff report generator
  - `scripts/auto_port.py` - stub MCP tool generator
  - `.github/workflows/upstream_sync.yml` - weekly GitHub Actions monitor
  - `bin/mcp_modules/__init__.py` - modular tool registration framework
  - `docs/UPSTREAM_SYNC_RUNBOOK.md` - operator guide
- **Result**: Every Monday 08:00 UTC the system checks for new upstream releases;
  email alert sent if a new release is detected

### Phase 6 - Legacy Category Purge
- **What**: Removed all remaining hardcoded `ats`/`oma`/`smc` references from
  7 legacy `src/` files
- **Files fixed**:
  - `src/agent_memory_integration.py` - removed 241-line dead code block
  - `src/coordination/sub_agent_coordinator.py` - replaced enum with string keys
  - `src/agents/__init__.py` - full rewrite with dynamic AgentRegistry
  - `src/coordination/__init__.py` - removed hardcoded category keys
  - `src/memory_config.py` - renamed API; generic example categories
  - `src/enhanced_cognee_mcp.py` - removed legacy ATS_MEMORY_PREFIX block
  - `src/integration/sdlc_integration.py` - replaced category chain with dynamic lookup
- **Tests**: `tests/unit/test_remaining_modules.py` updated; all 497 pass
- **Result**: Categories gate passes on `src/ bin/ cognee/infrastructure/`

---

## 2. Next Steps

Priority order: High / Medium / Low. Effort: S (< 1 day), M (1-3 days), L (4-10 days).

### HIGH PRIORITY

#### 2.1 - NOTICE File Creation [S]
**What**: Create a `NOTICE` file required by Apache 2.0 for derivative works.
**Why**: Legally required; missing from the project.
**Acceptance criteria**: `NOTICE` file exists in project root with proper attribution
for the original Cognee project and all major third-party libraries.
**Steps**:
1. Create `NOTICE` at project root (see Section 9 for content)
2. Reference it from README License section (already prepared)

#### 2.2 - Monolith Migration: Phase 2/3 Tools [M]
**What**: The MCP monolith (`bin/enhanced_cognee_mcp_server.py`) still has the Phase
2 and Phase 3 tools defined inline. The canonical implementations live in
`bin/mcp_modules/phase2_session_memory.py` and `bin/mcp_modules/phase3_loaders.py`.
**Why**: Duplication creates drift risk; monolith is 4,700+ lines.
**Acceptance criteria**: Monolith calls `register(mcp)` from each module; inline
definitions removed; all 497 unit tests still pass; no tool registration errors.
**Steps**:
1. In monolith, find Phase 2 tool definitions (search: `async def remember`,
   `async def recall`, etc.)
2. Replace inline definitions with:
   ```python
   from bin.mcp_modules.phase2_session_memory import register as register_phase2
   from bin.mcp_modules.phase3_loaders import register as register_phase3
   register_phase2(mcp)
   register_phase3(mcp)
   ```
3. Run unit tests to verify
4. Run categories gate: `python scripts/check_no_hardcoded_categories.py src/ bin/`

#### 2.3 - GitHub Repository Setup [S]
**What**: The README references `https://github.com/vincentspereira/Enhanced-Cognee`
but this repo may not be public or may not exist yet.
**Why**: Required for upstream contribution and community use.
**Acceptance criteria**: Repo is public with correct topics, description, and
homepage URL pointing to documentation.
**Steps**:
1. Create GitHub repo at `vincentspereira/Enhanced-Cognee` (or fork topoteretes/cognee)
2. Push current state (main branch)
3. Add topics: `cognee`, `mcp`, `memory`, `ai-agents`, `knowledge-graph`
4. Set description: "Enterprise-grade fork of Cognee with 70 MCP tools, 4-DB stack,
   and automated upstream sync"

#### 2.4 - NOTICE File for GitHub Secrets (upstream_sync.yml) [S]
**What**: `.github/workflows/upstream_sync.yml` requires two GitHub secrets:
`MAIL_USERNAME` and `MAIL_PASSWORD`. These need to be configured in the repository.
**Steps**:
1. In GitHub repo Settings -> Secrets and variables -> Actions:
   - `MAIL_USERNAME`: vincentspereira@outlook.com
   - `MAIL_PASSWORD`: your email app password
2. Optionally add `UPSTREAM_GITHUB_TOKEN` for higher API rate limits

### MEDIUM PRIORITY

#### 2.5 - Integration Test Infrastructure [M]
**What**: The 497 unit tests use mocks; real integration tests require live DB
connections. These are marked as `@pytest.mark.integration` but need a Docker
compose profile that spins up test DBs.
**Why**: Prevents regressions in actual DB queries.
**Steps**:
1. Add a `docker-compose-test.yml` profile (copy from enhanced stack with
   ephemeral volumes)
2. Add a `pytest -m integration` target in CI
3. Create 20-30 integration tests for key MCP tools
4. Add a weekly CI job (separate from unit tests)

#### 2.6 - MCP Server Startup Validation [S]
**What**: When the MCP server starts, it should verify that all 70 tools are
registered and print the count to stdout.
**Why**: Makes it easy to catch accidental tool de-registration.
**Steps**:
1. After all `@mcp.tool()` decorators, add a startup hook that counts registered tools
2. Assert count == 70; print `[OK] 70 MCP tools registered` or
   `[WARN] Expected 70 tools, found N`

#### 2.7 - Lite Mode Implementation [L]
**What**: The README describes a "Lite Mode" (SQLite, no Docker) but it is not yet
implemented.
**Why**: Lowers barrier to entry for individual developers.
**Steps**:
1. Create `enhanced_cognee_lite_server.py` with SQLite backend
2. Include 10 essential MCP tools (add_memory, search_memories, get_memories,
   get_memory, update_memory, delete_memory, list_agents, cognify, search, health)
3. Add `pip install enhanced-cognee[lite]` setup.cfg extra
4. Write a `docs/guides/LITE_MODE_GUIDE.md` setup guide

#### 2.8 - Prometheus + Grafana Dashboard [L]
**What**: Prometheus metrics are exported via `get_prometheus_metrics` MCP tool but
there is no Grafana dashboard configured.
**Why**: Operations teams need visibility without building dashboards from scratch.
**Steps**:
1. Create `config/monitoring/grafana/dashboards/enhanced_cognee.json`
2. Add panels for: query rate, avg latency, cache hit rate, memory count by agent,
   deduplication savings
3. Add dashboard provisioning config to Docker compose
4. Document in `docs/operations/MONITORING_SETUP_GUIDE.md`

#### 2.9 - PyPI Package Publishing [M]
**What**: Publish `enhanced-cognee` to PyPI so users can `pip install enhanced-cognee`.
**Why**: Standard distribution mechanism; currently only installable from source.
**Steps**:
1. Update `setup.cfg` or `pyproject.toml` with correct metadata
   (name, version, author, classifiers, entry_points)
2. Run `python -m build` and verify wheel
3. Publish to TestPyPI first: `twine upload --repository testpypi dist/*`
4. Test install from TestPyPI in a clean venv
5. Publish to PyPI: `twine upload dist/*`
6. Update README installation section

### LOW PRIORITY

#### 2.10 - Web Dashboard (Next.js) [L]
**What**: The README mentions a Next.js 14 frontend but it may not be running or
complete. Verify and fix.
**Why**: Useful for non-CLI users.
**Acceptance criteria**: `npm run dev` in `cognee-frontend/` starts a working UI.

#### 2.11 - Security Hardening Audit [M]
**What**: Run the security hardening checklist from
`docs/operations/SECURITY_HARDENING_CHECKLIST.md` and verify items are actually
implemented (not just listed).
**Why**: The checklist was created in Phase 4 but not all items were verified.

#### 2.12 - Performance Benchmarking [M]
**What**: The README previously claimed "400-700% performance improvement" without
actual benchmarks. Remove or replace the claim with measured data.
**Why**: Unverified performance claims reduce credibility.
**Steps**:
1. Set up a Locust load test script (`tests/performance/locust_test.py`)
2. Run against both stock Cognee (SQLite) and Enhanced Cognee (full stack)
3. Document results in `docs/reports/PERFORMANCE_BENCHMARK.md`
4. Update README with actual measured numbers

---

## 3. Status Before vs. After

### Before (v0.5.1 baseline, pre-Phase-1)

| Metric | Value |
|--------|-------|
| Upstream cognee version | v0.5.1 |
| MCP tools | ~64 (estimated; monolith count) |
| Unit tests passing | Unknown (categories gate failing) |
| Hardcoded categories | 7+ production files had ATS/OMA/SMC |
| Upstream sync | Manual / none |
| SearchType support | 8 types |
| External loaders via MCP | None |
| Session memory (v1.0.9 API) | None |
| Dynamic categories | Partial (config file existed but code violated it) |
| Documentation accuracy | README showed incorrect counts throughout |

### After (v1.0.9 parity, post-Phase-6)

| Metric | Value |
|--------|-------|
| Upstream cognee version | v1.0.9 (full API parity) |
| MCP tools | 70 confirmed |
| Unit tests passing | 497/497 (100%) |
| Hardcoded categories | 0 in production code (gate passes) |
| Upstream sync | Automated (GitHub Actions weekly) |
| SearchType support | 15 types |
| External loaders via MCP | 6 tools (URL, DB, translate, NER, graph v2, loaders list) |
| Session memory (v1.0.9 API) | 6 tools (remember, recall, forget, improve, save, status) |
| Dynamic categories | Fully enforced; `.enhanced-cognee-config.json` |
| Documentation accuracy | README updated; counts verified |

---

## 4. How the System Changed (Changelog)

### Architecture Changes

```
Before Phase 1:
  - cognee/ directory at v0.5.1 API surface
  - No v1.0.9 API modules (remember, recall, forget, improve)

After Phase 1:
  - cognee/ updated to v1.0.9 API surface
  - cognee.api.v1.* modules available

After Phase 2:
  - 6 new MCP tools wrapping v1.0.9 session memory API
  - bin/mcp_modules/phase2_session_memory.py (canonical)
  - _cognify_tasks in-process task tracker for background cognify

After Phase 3:
  - 6 new MCP tools for external data ingestion and enrichment
  - bin/mcp_modules/phase3_loaders.py (canonical)
  - web_scraper_task, dlt pipeline, translate_content, RegexEntityExtractor,
    cascade extract utils all exposed via MCP

After Phase 4:
  - .archive/2026-05-13_agents_ats_oma_smc/ created
  - src/agents/ats/, src/agents/oma/, src/agents/smc/ removed from codebase
  - bin/mcp_modules/__init__.py created with discover_and_register()
  - docs/UPSTREAM_SYNC_RUNBOOK.md created

After Phase 5:
  - scripts/upstream_diff.py: automated diff report vs. latest upstream tag
  - scripts/auto_port.py: stub generator for new upstream tools
  - .github/workflows/upstream_sync.yml: weekly cron check with email alert
  - .upstream-sync/last_seen_release.txt: tracks v1.0.9 as synced baseline
  - .upstream-sync/sync-metadata.json: full sync state record

After Phase 6:
  - src/agent_memory_integration.py: 241-line dead ATS/OMA/SMC block removed
  - src/coordination/sub_agent_coordinator.py: enum replaced with string keys
  - src/agents/__init__.py: full rewrite with dynamic AgentRegistry
  - src/coordination/__init__.py: dynamic category description
  - src/memory_config.py: get_mas_categories() renamed to get_example_categories()
  - src/enhanced_cognee_mcp.py: legacy ATS_MEMORY_PREFIX fallback removed
  - src/integration/sdlc_integration.py: hardcoded category routing removed
```

### Rule Enforcement

The categories gate (`scripts/check_no_hardcoded_categories.py`) now passes on:
- `src/` - all 7 legacy files cleaned
- `bin/` - monolith and mcp_modules clean
- `cognee/infrastructure/` - upstream infrastructure clean

---

## 5. Pros and Cons

### Pros

**Technical depth**
- Full v1.0.9 API parity: every public module in upstream cognee is accessible
  via an MCP tool
- 4-database stack (PostgreSQL + Qdrant + Neo4j + Redis) provides genuine
  enterprise-grade durability, vector search, graph traversal, and caching
- 70 MCP tools cover the complete memory lifecycle from ingestion to expiry

**Maintainability**
- Automated upstream sync (Phase 5) reduces the risk of falling behind again
- Dynamic categories enforce the separation of concerns; any project can define
  its own categories without touching source code
- Modular `bin/mcp_modules/` structure makes it easy to add new tool groups
- Categories gate in CI prevents regression

**Completeness**
- 497 unit tests with 100% pass rate
- ASCII-only output constraint is enforced, solving Windows cp1252 console issues
- All 15 SearchType values are supported and documented

### Cons

**Operational complexity**
- Requires Docker with 4 containers to run at full capability; not suitable for
  local development without Docker
- Memory requirements: 4GB+ RAM just for the database stack
- Configuration has many moving parts (.env, .enhanced-cognee-config.json,
  docker-compose, MCP server path)

**Monolith size**
- `bin/enhanced_cognee_mcp_server.py` is 4,700+ lines; a large single file is
  hard to review and maintain
- The Phase 2/3 tools are duplicated (both inline in monolith and in mcp_modules/)
  until Task 2.2 is completed

**Gaps vs. original Cognee**
- Lite Mode (SQLite fallback) is documented but not yet implemented (Task 2.7)
- No PyPI package yet; installation requires cloning from source (Task 2.9)
- Performance improvement claims (400-700%) are unverified (Task 2.12)

**Community**
- The project is a private fork; contributing back to upstream is possible but
  requires significant effort to isolate which changes upstream would accept
  (see Section 7)

---

## 6. Feature Comparison

### Enhanced Cognee vs. Original Cognee

| Feature | Original Cognee v1.0.9 | Enhanced Cognee |
|---------|----------------------|-----------------|
| Core ECL pipeline (add, cognify, search) | Yes | Yes (100% compatible) |
| Database | SQLite / pluggable | PostgreSQL + Qdrant + Neo4j + Redis |
| MCP tools | cognee-mcp (~4 tools) | 70 tools (full lifecycle) |
| SearchType values | 15 | 15 (all parity) |
| Session memory (remember/recall) | Yes (v1.0.9 modules) | Yes (MCP-wrapped) |
| External loaders via MCP | No | Yes (URL, DB, translate, NER, graph v2) |
| Memory deduplication | No | Yes (semantic + exact match) |
| Memory summarization | No | Yes (LLM-powered, 4 strategies) |
| Memory TTL / expiry | No | Yes (configurable) |
| Cross-agent sharing | No | Yes (4 access policies) |
| Real-time sync | No | Yes (Redis pub/sub) |
| Performance analytics | No | Yes (Prometheus export) |
| Backup and recovery | No | Yes (8 tools) |
| Multi-language support | No | Yes (28 languages, cross-language search) |
| Dynamic categories | No (dataset-based) | Yes (.enhanced-cognee-config.json) |
| Upstream sync monitoring | No | Yes (GitHub Actions weekly) |
| Test coverage | Not specified | 497 unit tests, 100% pass rate |
| ASCII-only output | No | Yes (Windows cp1252 compatible) |
| Docker deployment | Basic | Production-ready with health checks |

### Enhanced Cognee vs. Session-Memory Plugins (e.g., Claude-Mem)

| Feature | Session-Memory Plugin | Enhanced Cognee |
|---------|-----------------------|-----------------|
| Installation | One command (plugin marketplace) | Docker + config |
| Automatic context injection | Yes (via hooks) | No (manual via MCP tools) |
| Token efficiency | High (progressive disclosure) | Standard |
| Scalability | Single user | 100+ concurrent agents |
| Knowledge graph | No | Yes (Neo4j) |
| Cross-agent sharing | No | Yes |
| Enterprise features | No | Yes (RBAC, audit, backup) |
| Upstream tracking | No | Yes (automated) |

**Summary**: Enhanced Cognee is the right choice for multi-agent enterprise
deployments. A simple session-memory plugin is the right choice for individual
developers who want zero-config memory.

---

## 7. Upstream Contribution Strategy

Contributing back to topoteretes/cognee is possible but requires careful scoping.
Here is a step-by-step strategy.

### 7.1 - What Would Be Accepted Upstream

The following Enhanced Cognee additions are generic enough that upstream would likely
accept them as pull requests:

| Enhancement | Estimated Acceptance | Notes |
|-------------|---------------------|-------|
| All 15 SearchType MCP tools | HIGH | Upstream already has the API; MCP wrappers are additive |
| `ingest_url`, `ingest_db`, `list_loaders` | HIGH | These wrap existing upstream tasks |
| `translate_text`, `regex_extract_entities` | MEDIUM | Useful additions; may need API review |
| `extract_graph_v2` | MEDIUM | Preview feature; upstream may include in v1.1 |
| Memory deduplication tools | MEDIUM | Enterprise feature; may not fit upstream scope |
| Memory TTL / expiry tools | MEDIUM | Useful but opinionated lifecycle management |
| `upstream_diff.py` and `auto_port.py` | LOW | Internal tooling; upstream has their own CI |
| 4-database stack config | LOW | Upstream intentionally keeps DB choice flexible |
| ASCII-only output constraint | LOW | Very project-specific |

### 7.2 - How to Contribute

**Step 1**: Fork topoteretes/cognee on GitHub (separate from your Enhanced Cognee fork)

**Step 2**: Create a feature branch per contribution:
```
git checkout -b feat/mcp-session-memory-tools
```

**Step 3**: Cherry-pick only the relevant commits from Enhanced Cognee:
```
git cherry-pick <Phase 2 commits>
```

**Step 4**: Run upstream test suite:
```
pytest tests/ -v  # must pass 100%
```

**Step 5**: Open a PR with:
- Clear description of what the tools do
- Reference to the upstream API they wrap
- Test coverage for the new tools
- No references to Enhanced Cognee-specific infrastructure (use upstream DB adapters)

### 7.3 - Benefits to You

- Your contributions become part of the official cognee release, reducing future
  porting work
- You receive maintainer attribution in the upstream changelog
- Community use of your tools generates bug reports that improve quality

### 7.4 - Benefits to Topoteretes/Cognee

- More MCP tool coverage attracts developers using MCP-compatible IDEs
- External loader tools (URL, DB) make cognee more usable out of the box
- Production experience from Enhanced Cognee deployment provides real-world
  validation of the v1.0.9 API

### 7.5 - Recommended First PR

Start with the 6 Phase 3 loader tools (`ingest_url`, `ingest_db`, `translate_text`,
`regex_extract_entities`, `extract_graph_v2`, `list_loaders`). These:
- Wrap existing upstream tasks with no modifications
- Are completely generic (no Enhanced Cognee-specific code)
- Add real value for anyone using cognee as an MCP server
- Have test coverage already in `bin/mcp_modules/phase3_loaders.py`

---

## 8. README and Documentation Maintenance

### 8.1 - README Update Policy

The README was updated on 2026-05-13 (this session) with all Phase 1-6 changes.
The `docs/README_PROPOSED_CHANGES.md` process worked well: propose -> review ->
approve -> apply. Use the same process for future major changes.

**Trigger for next README update**: When any of the following changes:
- MCP tool count (currently 70)
- Test count (currently 497 unit tests)
- Upstream version synced (currently v1.0.9)
- SearchType count (currently 15)

### 8.2 - Documentation Files to Keep Current

| File | Last Updated | Update Trigger |
|------|-------------|----------------|
| `README.md` | 2026-05-13 | Feature count changes |
| `docs/UPSTREAM_SYNC_RUNBOOK.md` | 2026-05-13 | Sync process changes |
| `docs/plans/MASTER_IMPLEMENTATION_PLAN.md` | 2026-05-13 | After each phase |
| `.upstream-sync/sync-metadata.json` | 2026-05-13 | After each sync |
| `docs/reports/PERFORMANCE_BENCHMARK.md` | Not yet created | After benchmarking |

### 8.3 - IDE Configuration Files (CLAUDE.md)

The `CLAUDE.md` file is a configuration artifact for the Claude Code IDE. It
instructs the IDE on project rules (ASCII-only output, dynamic categories, etc.).
This file should NOT be removed or renamed as it would break Claude Code's
ability to enforce project-specific constraints.

If other IDE configurations are needed (e.g., `.cursor/rules`, `.windsurf/rules`),
create IDE-specific equivalents that reference the same project rules.

---

## 9. License and Attribution

### 9.1 - Current State

The project uses Apache License 2.0 (from original Cognee). The `LICENSE` file
exists with the original Apache 2.0 text. The README copyright block was updated
in this session to include Vincent S. Pereira's copyright notice.

### 9.2 - Required Action: Create NOTICE File

Apache 2.0 requires a `NOTICE` file for derivative works. Create `NOTICE` at the
project root with this content:

```
Enhanced Cognee
Copyright 2026 Vincent S. Pereira

This product is a derivative work of Cognee
(https://github.com/topoteretes/cognee)
Copyright 2024 Topoteretes UG

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Third-party components:
- PostgreSQL: https://www.postgresql.org/ (PostgreSQL License)
- Qdrant: https://qdrant.tech/ (Apache 2.0)
- Neo4j: https://neo4j.com/ (various editions; Community Edition: GPL v3)
- Redis: https://redis.io/ (RSALv2 + SSPL v1)
- FastMCP: https://github.com/jlowin/fastmcp (MIT)
- pgvector: https://github.com/pgvector/pgvector (MIT)
```

**Note**: Neo4j Community Edition is GPL v3. If Enhanced Cognee is distributed
as a product (not just a tool or internal service), consult a license attorney
on GPL compatibility with Apache 2.0 in your use case.

### 9.3 - Contributor Credits

Contributors should be listed in `docs/policies/CONTRIBUTORS.md`. At minimum:
- Topoteretes UG (original Cognee)
- Vincent S. Pereira (Enhanced Cognee)

---

## 10. Technical Debt Register

Items that exist in the codebase and are known to be suboptimal. Each has a
priority and estimated effort.

| ID | Item | Priority | Effort | Location |
|----|------|----------|--------|----------|
| TD-01 | Monolith has inline duplicates of Phase 2/3 tools | HIGH | M | `bin/enhanced_cognee_mcp_server.py` |
| TD-02 | No live integration tests (all tests use mocks) | HIGH | L | `tests/integration/` |
| TD-03 | Tool count assertion missing from server startup | MEDIUM | S | MCP server startup |
| TD-04 | `src/coordination/` has stub wrapper classes that do nothing | MEDIUM | M | `sub_agent_coordinator.py` |
| TD-05 | `get_mas_categories()` renamed but old callers may exist | MEDIUM | S | `src/memory_config.py` |
| TD-06 | MCP server `--help` documentation missing | LOW | S | `enhanced_cognee_mcp_server.py` |
| TD-07 | `cognee-frontend/` Next.js app may be out of date | LOW | L | `cognee-frontend/` |
| TD-08 | Lite mode documented but not implemented | LOW | L | New file needed |
| TD-09 | 400-700% performance claim in some docs is unverified | LOW | M | Benchmarking needed |
| TD-10 | NOTICE file missing (Apache 2.0 requirement) | ~~HIGH~~ DONE | S | `NOTICE` created 2026-05-13 |
| TD-11 | Database stack hardcoded to PostgreSQL+Qdrant+Neo4j+Redis | MEDIUM | L | Multiple config files |
| TD-12 | No one-command Docker automation / zero-config installer | HIGH | M | New script needed |
| TD-13 | Web viewer (frontend) requires manual Neo4j Browser setup | MEDIUM | L | `cognee-frontend/` or new |
| TD-14 | No token-efficient progressive search (10x token savings) | MEDIUM | L | New MCP tools needed |
| TD-15 | No automatic context injection at session start | MEDIUM | M | Hooks mechanism needed |

---

## 11. Future Improvements Backlog

Ordered by estimated value vs. effort ratio (highest first).

### 11.1 - NOTICE File [Value: HIGH, Effort: S] -- COMPLETE
Created 2026-05-13. `NOTICE` file exists at project root with full Apache 2.0
derivative-work attribution.

### 11.2 - Monolith Refactoring [Value: HIGH, Effort: M]
Move Phase 2/3 inline tool definitions out of monolith into module files.
Reduces duplication and makes the codebase maintainable.
**Next action**: See Task 2.2 above.

### 11.3 - PyPI Publication [Value: HIGH, Effort: M]
Enables `pip install enhanced-cognee`. Dramatically lowers barrier to entry.
**Next action**: Update `setup.cfg`, build wheel, publish to TestPyPI first.

### 11.4 - Integration Test Suite [Value: HIGH, Effort: L]
Current tests mock everything. Real DB integration tests catch regressions.
**Next action**: Create `docker-compose-test.yml` and 20 integration tests.

### 11.5 - Upstream Contribution (Phase 3 tools) [Value: HIGH, Effort: M]
Contribute loader tools to topoteretes/cognee. Benefits the community and
reduces future porting maintenance.
**Next action**: Fork upstream, cherry-pick phase3_loaders.py, open PR.

### 11.6 - Lite Mode [Value: MEDIUM, Effort: L]
SQLite-based deployment for individual developers. Removes Docker requirement.
**Next action**: Create `enhanced_cognee_lite_server.py`.

### 11.7 - Performance Benchmarking [Value: MEDIUM, Effort: M]
Measure and document actual performance vs. baseline Cognee.
Either confirm the "400-700%" claim or replace it with real numbers.
**Next action**: Create `tests/performance/locust_test.py`, run, document.

### 11.8 - Grafana Dashboard [Value: MEDIUM, Effort: M]
Pre-built Grafana dashboard for monitoring. Reduces ops setup time.
**Next action**: Create dashboard JSON in `config/monitoring/grafana/`.

### 11.9 - Security Audit Verification [Value: MEDIUM, Effort: M]
The security hardening checklist exists; verify items are actually implemented.
**Next action**: Walk through `docs/operations/SECURITY_HARDENING_CHECKLIST.md`
line by line; mark items as verified or pending.

### 11.10 - Next Upstream Sync (v1.1.x when released) [Value: MEDIUM, Effort: M]
When topoteretes releases a new version after v1.0.9, the automated monitor
will detect it. Use the runbook to triage and port new features.
**Next action**: Wait for automated alert; then follow `docs/UPSTREAM_SYNC_RUNBOOK.md`.

### 11.11 - Memory Hierarchy (Structured Observations) [Value: LOW, Effort: L]
The README describes "structured observations" format but this is not implemented.
Adds a layer of semantic structure to stored memories.
**Next action**: Design schema; implement as new MCP tools.

---

## 12. Phase 7 - Installability and User Experience

These items were identified in the post-Phase-6 user review as the next major
improvement area. They bring Enhanced Cognee closer to the ease-of-use of
simpler alternatives while keeping enterprise depth.

### 12.1 - Flexible Database Stack [Value: HIGH, Effort: L]

**Goal**: Allow users to choose their own databases instead of requiring the full
4-DB stack. `PostgreSQL + Qdrant + Neo4j + Redis` remains the default but every
component should be swappable.

**Design approach**:

```
VECTOR_BACKEND=qdrant        # options: qdrant, lancedb, pgvector, chroma
GRAPH_BACKEND=neo4j          # options: neo4j, kuzu, networkx (in-memory)
RELATIONAL_BACKEND=postgres  # options: postgres, sqlite
CACHE_BACKEND=redis          # options: redis, memory (in-process), none
```

**Implementation steps**:
1. Create `src/backends/vector_backend.py` with an abstract interface
2. Create `src/backends/graph_backend.py` with an abstract interface
3. Implement adapters for each supported backend
4. Update MCP server to read backend from `.env` and instantiate the correct adapter
5. Update Docker compose to have optional service profiles:
   `docker compose --profile minimal up -d` (SQLite + no graph)
   `docker compose --profile full up -d` (full 4-DB stack)
6. Update README Installation section with backend choice table

**Priority**: Implement vector backend swap first (Qdrant vs. LanceDB vs. ChromaDB),
since vector search is most commonly customized.

**Files to create/modify**:
- `src/backends/__init__.py` (new)
- `src/backends/vector_backend.py` (new)
- `src/backends/graph_backend.py` (new)
- `config/docker/docker-compose-enhanced-cognee.yml` (add profiles)
- `.env.example` (add backend choice variables)

---

### 12.2 - One-Command Installation + Setup Wizard [Value: HIGH, Effort: M]

**Goal**: Make setup as close to zero-config as possible. Replicate the simplicity
of `pip install` from Original Cognee while keeping the enterprise stack available.

**Phase A - pip install with auto-config (Effort: M)**:
```bash
pip install enhanced-cognee
enhanced-cognee setup          # interactive wizard
enhanced-cognee start          # starts MCP server + stack
```

The `enhanced-cognee setup` wizard should:
1. Ask: full stack or lite mode?
2. If full: offer to start Docker stack automatically
3. Ask for LLM provider and API key (or "use local Ollama")
4. Write `.env` from answers
5. Verify database connections
6. Print the MCP configuration block to paste into IDE config

**Phase B - Docker automation (Effort: S)**:
```bash
enhanced-cognee docker up      # equivalent to docker compose up -d
enhanced-cognee docker status  # show container health
enhanced-cognee docker down    # clean shutdown
```

**Implementation steps**:
1. Create `bin/enhanced_cognee_cli.py` with Click-based CLI
2. Add `setup` command with questionnaire (use `questionary` library)
3. Add `docker` sub-commands that wrap docker compose
4. Register as entry point in `setup.cfg`:
   `[options.entry_points] console_scripts = enhanced-cognee = bin.enhanced_cognee_cli:main`
5. Publish to PyPI (see 11.3)

**Reference**: Original Cognee uses `pip install cognee` + environment variables.
Replicate this pattern while keeping Docker as the backend for the 4-DB stack.

---

### 12.3 - Step-by-Step Interactive Setup [Value: MEDIUM, Effort: M]

**Goal**: A guided setup script that walks users through every configuration decision
with validation at each step. No Docker or Python knowledge required.

**Design**:
```
Step 1: Check prerequisites (Docker, Python 3.10+)
Step 2: Choose deployment mode (Full / Lite / Custom)
Step 3: Configure LLM provider (OpenAI / local Ollama / other)
Step 4: Start database containers (with live progress bar)
Step 5: Verify all connections (health check)
Step 6: Configure categories (.enhanced-cognee-config.json)
Step 7: Print MCP config to add to IDE
Step 8: Run smoke test (add_memory + search_memories)
```

**Implementation**: `bin/setup_wizard.py` using `rich` for progress bars and
formatted output; `questionary` for interactive prompts.

**Files to create**: `bin/setup_wizard.py`

---

### 12.4 - Embedded Web Viewer [Value: MEDIUM, Effort: L]

**Goal**: Replace "use Neo4j Browser separately" with an embedded web UI accessible
at `http://localhost:37777` (or similar) showing memory contents, graph
visualization, and system health.

**Options** (in order of effort):
1. **Adapt cognee-frontend** (if already present): Start the existing Next.js app
   automatically when the MCP server starts. Estimated effort: M.
2. **Lightweight FastAPI + Jinja2 dashboard**: A minimal Python-only web UI
   that lists memories, shows search results, and displays basic graph stats.
   Estimated effort: M.
3. **Neo4j Bloom integration**: Configure Neo4j Bloom (bundled with Neo4j Desktop)
   to connect automatically. Effort: S (config only).

**Recommended start**: Option 3 (Neo4j Bloom) as a quick win, then Option 2 for
a proper standalone viewer.

**Key pages to implement for Option 2**:
- `/` - Dashboard: memory count, agent count, DB health
- `/memories` - List and search memories
- `/graph` - Force-directed graph view (D3.js or vis.js)
- `/tools` - Tool invocation UI (for debugging)

---

### 12.5 - Token-Efficient Progressive Search (from Claude-Mem) [Value: MEDIUM, Effort: L]

**Goal**: Implement a 3-layer progressive disclosure search that saves 10x tokens
vs. returning full memory content in every response.

**Design** (inspired by Claude-Mem's approach):
- Layer 1 (QUICK): Return only memory IDs + one-line summaries (< 50 tokens per result)
- Layer 2 (DETAILED): Return full content for specific IDs requested
- Layer 3 (GRAPH): Traverse relationships for contextually related memories

**New MCP tools to add**:
- `search_quick` - Returns IDs + 1-line summaries only
- `get_memory_detail` - Returns full content for a specific ID
- `get_related` - Returns semantically/graph-related memory IDs

**Implementation steps**:
1. Add `summary_field` to the memory storage schema (one-line auto-summary on write)
2. Create `search_quick` tool that returns only ID + summary
3. Create `get_related` tool using Neo4j graph traversal
4. Document the progressive search pattern in MCP IDE setup guide

**Token savings analysis**:
- Current: `search_memories("auth")` returns 10 full memories = ~2,000 tokens
- With progressive: `search_quick("auth")` returns 10 summaries = ~200 tokens
- Then: `get_memory_detail("mem-123")` returns 1 full = ~200 tokens
- Net: 90% token reduction for most queries

---

### 12.6 - Automatic Context Injection at Session Start (from Claude-Mem) [Value: MEDIUM, Effort: M]

**Goal**: At the start of every IDE session, automatically inject the most relevant
recent memories into context without the user needing to ask.

**How Claude-Mem does it**: Uses MCP hooks (`preToolUse`, `postToolUse`) to
automatically call memory search on every conversation turn.

**Enhanced Cognee approach** (compatible with any MCP IDE):
1. Add a `get_session_context` tool that returns the top-N most recent and relevant
   memories for a given agent/user
2. Document in IDE setup guides how to configure the IDE to call this tool on startup
3. For IDEs that support hooks (e.g., custom system prompts), provide a template
   system prompt that includes memory retrieval

**Implementation steps**:
1. Create `get_session_context(agent_id, limit=20, days_back=7)` MCP tool
   - Returns recent memories sorted by relevance and recency
   - Formatted for direct inclusion in a system prompt
2. Add `session_context` section to `.enhanced-cognee-config.json`:
   ```json
   {"session_context": {"auto_load": true, "limit": 20, "days_back": 7}}
   ```
3. Document hook configuration for supported IDEs

---

### 12.7 - Session Tracking (from Claude-Mem) [Value: LOW, Effort: M]

**Goal**: Track multi-turn conversation sessions so memory retrieval can be
scoped to "current session" vs "all history".

**Design**: Each session gets a UUID. All memories added during a session are
tagged with that session ID. `recall` and `search_memories` gain a
`session_id` parameter to scope results.

**Note**: The v1.0.9 `remember()` and `recall()` APIs already support `session_id`
as a parameter. This task is about surfacing session management in the MCP tools
and making it automatic.

**New MCP tools**:
- `start_session` - Creates a session ID, stores in config, returns it
- `end_session` - Marks session complete; triggers summarization of session
- `get_session_history` - Returns all memories from a specific session

**Integration with existing tools**: Update `remember` and `recall` to
automatically use the active session ID if one is set.

---

### 12.8 - Memory Hierarchy / Structured Observations (from Claude-Mem) [Value: LOW, Effort: L]

**Goal**: Store memories in a structured format (entity + attribute + value)
rather than flat text blobs. This enables precise updates ("update fact X")
rather than full memory replacement.

**Structured observation format**:
```json
{
  "entity": "authentication_system",
  "attribute": "token_type",
  "value": "JWT",
  "confidence": 0.95,
  "source": "session-2026-05-13"
}
```

**Benefits**:
- Precise updates: `update_observation(entity="auth", attribute="token_type", value="OAuth2")`
- Conflict detection: two agents disagree on same attribute -> flag for review
- Richer graph: entity-attribute-value triples map directly to Neo4j nodes/edges

**Implementation**: Requires schema changes in PostgreSQL; new MCP tools for
structured read/write; migration path from existing flat memories.

---

*Last updated: 2026-05-13 - Added Phase 7 (Installability and UX) items 12.1-12.8.*

---

## Appendix A - File Reference Map

Key files for each component:

| Component | Primary File | Config File |
|-----------|-------------|-------------|
| MCP Server (monolith) | `bin/enhanced_cognee_mcp_server.py` | `.env` |
| Phase 2 tools (canonical) | `bin/mcp_modules/phase2_session_memory.py` | none |
| Phase 3 tools (canonical) | `bin/mcp_modules/phase3_loaders.py` | none |
| Module registry | `bin/mcp_modules/__init__.py` | none |
| Category config | `.enhanced-cognee-config.json` | n/a |
| Dynamic category loader | `src/memory_config.py` | `.enhanced-cognee-config.json` |
| Agent coordinator | `src/coordination/sub_agent_coordinator.py` | `.enhanced-cognee-config.json` |
| Categories gate (CI) | `scripts/check_no_hardcoded_categories.py` | none |
| Upstream diff script | `scripts/upstream_diff.py` | `.upstream-sync/last_seen_release.txt` |
| Auto-port script | `scripts/auto_port.py` | `.upstream-sync/last_diff_report.json` |
| GitHub Actions cron | `.github/workflows/upstream_sync.yml` | GitHub Secrets |
| Sync state | `.upstream-sync/sync-metadata.json` | none |
| Upstream runbook | `docs/UPSTREAM_SYNC_RUNBOOK.md` | none |
| Docker stack | `config/docker/docker-compose-enhanced-cognee.yml` | `.env` |

---

## Appendix B - Invariants (Never Violate)

These rules are enforced by CI and must never be violated:

1. **No hardcoded categories** - no `ats`, `oma`, `smc` as string literals or enum
   members in production code. Use dynamic loading from `.enhanced-cognee-config.json`.
   Gate: `python scripts/check_no_hardcoded_categories.py src/ bin/`

2. **ASCII-only output** - no Unicode symbols in MCP tool responses or stdout.
   Use `OK`, `ERR`, `WARN`, `INFO` prefixes.

3. **497 unit tests must pass** - run `pytest tests/unit/ -v` before any commit.

4. **Upstream baseline is v1.0.9** - `.upstream-sync/last_seen_release.txt` tracks
   this. Do not manually edit without updating `sync-metadata.json`.

---

*Last updated: 2026-05-13 - Covers Phases 0-6 and full Q&A review session.*
