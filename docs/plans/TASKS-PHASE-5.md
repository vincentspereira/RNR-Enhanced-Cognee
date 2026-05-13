# Phase 5 - Automation Scaffolding

**Branch**: feature/phase-5-automation  
**Date**: 2026-05-13  
**Status**: Complete

## Objectives

Build automation infrastructure to detect, evaluate, and stub-port future upstream
topoteretes/cognee releases without manual GitHub polling.

## Deliverables

### P5.1 - scripts/upstream_diff.py (DONE)

Compares the local fork against the latest upstream tag via GitHub API.

Outputs a structured JSON diff report at `.upstream-sync/last_diff_report.json` with:
- `delta.new_tasks` - new cognee/tasks/*.py files (MCP tool candidates)
- `delta.new_api_routes` - new FastAPI routes in cognee/api/v1/
- `delta.new_search_types` - new SearchType values not in local _VALID_SEARCH_TYPES
- `delta.changed_files` - cognee/ files whose content changed

Usage:
```bat
python scripts/upstream_diff.py --check-only         # CI gate (exit 1 if new release)
python scripts/upstream_diff.py --token $GITHUB_TOKEN  # full report
```

### P5.2 - scripts/auto_port.py (DONE)

Reads the diff report and generates:
- `.upstream-sync/generated_stubs.py` - stub MCP tool functions for each new task
- `.upstream-sync/PORTING_TODO.md` - checkbox porting checklist

Skips stubs for tasks whose tool names already exist in the MCP server.

Usage:
```bat
python scripts/auto_port.py
python scripts/auto_port.py --dry-run  # preview without writing files
```

### P5.3 - .github/workflows/upstream_sync.yml (DONE)

GitHub Actions cron workflow (every Monday 08:00 UTC):

Jobs:
1. `check-upstream` - fetch and compare upstream tag
2. `build-diff-report` - run upstream_diff.py + auto_port.py (if new release)
3. `open-tracking-issue` - create GitHub issue with TODO excerpt (if new release)
4. `notify-email` - send email to vincentspereira@outlook.com (if new release)
5. `no-new-release` - log OK status (if current)

Required GitHub secrets: MAIL_USERNAME, MAIL_PASSWORD  
GITHUB_TOKEN is auto-provided.

### P5.4 - bin/mcp_modules/ (DONE)

Module framework for future MCP server decomposition:

```
bin/mcp_modules/
  __init__.py               - discover_and_register() auto-discovery utility
  phase2_session_memory.py  - Canonical Phase 2 tools (register(mcp) pattern)
  phase3_loaders.py         - Canonical Phase 3 tools (register(mcp) pattern)
```

Migration strategy: monolith remains unchanged; new tools in Phase 6+ go to modules first.
Full split deferred to a future sprint once the pattern is validated.

### P5.5 - docs/UPSTREAM_SYNC_RUNBOOK.md (DONE)

Comprehensive operator runbook covering:
- Automated monitoring setup
- Manual sync check commands
- Porting decision matrix (which upstream changes need MCP tools)
- Step-by-step implementation guide (branch, implement, test, update metadata, PR)
- Breaking change handling
- Full rebase strategy for major version bumps
- PR labeling guide

## Test Results

- All 497/497 unit tests pass (no new tests added in Phase 5 - automation scripts are not unit-testable without mocking GitHub API)
- All 5 Python files pass `py_compile`
- Quality gates pass (categories + ASCII)

## CI Gates

```
python scripts/check_no_hardcoded_categories.py bin/enhanced_cognee_mcp_server.py  -> exit 0
python scripts/check_ascii_output.py bin/enhanced_cognee_mcp_server.py             -> exit 0
python -m pytest tests/unit/ -q                                                     -> 497/497
```

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/upstream_diff.py` | 293 | Upstream diff generator |
| `scripts/auto_port.py` | 274 | Stub + TODO generator |
| `.github/workflows/upstream_sync.yml` | 162 | Weekly cron + email workflow |
| `bin/mcp_modules/__init__.py` | 68 | Module framework + auto-discovery |
| `bin/mcp_modules/phase2_session_memory.py` | 277 | Canonical Phase 2 tool module |
| `bin/mcp_modules/phase3_loaders.py` | 241 | Canonical Phase 3 tool module |
| `docs/UPSTREAM_SYNC_RUNBOOK.md` | 196 | Operator runbook |

## No changes to

- `bin/enhanced_cognee_mcp_server.py` - 70 tools unchanged
- `.upstream-sync/last_seen_release.txt` - still v1.0.9
- Test counts - 497 tests remain
