# Upstream Sync Runbook

**Project**: Enhanced Cognee  
**Upstream**: topoteretes/cognee (https://github.com/topoteretes/cognee)  
**Local baseline**: see `.upstream-sync/last_seen_release.txt`

---

## Overview

Enhanced Cognee is a fork of topoteretes/cognee with an extended MCP server,
4-database stack (PostgreSQL, Qdrant, Neo4j, Redis), and additional tooling.

This runbook describes how to:
1. Monitor for new upstream releases (automated via GitHub Actions)
2. Evaluate what needs porting
3. Implement and test the ports
4. Update the sync metadata

---

## 1. Automated Monitoring

The `.github/workflows/upstream_sync.yml` workflow runs every Monday at 08:00 UTC.

It will:
- Fetch the latest topoteretes/cognee release tag via GitHub API
- Compare against `.upstream-sync/last_seen_release.txt`
- If different: build a diff report, open a tracking GitHub issue, and send an email to vincentspereira@outlook.com

Required GitHub Secrets (set in repo settings):
- `GITHUB_TOKEN` (automatically provided)
- `MAIL_USERNAME` - Gmail address for SMTP
- `MAIL_PASSWORD` - Gmail app password (not account password)

---

## 2. Manual Sync Check

To check for new upstream releases without waiting for the weekly cron:

```bat
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
python scripts/upstream_diff.py --check-only
```

Exit 0 = up to date. Exit 1 = new release available.

---

## 3. Generating the Diff Report

```bat
python scripts/upstream_diff.py --token YOUR_GITHUB_TOKEN
```

Output: `.upstream-sync/last_diff_report.json`

The report contains:
- `delta.new_tasks` - new cognee/tasks/*.py files (candidates for new MCP tools)
- `delta.new_api_routes` - new FastAPI routes in cognee/api/v1/
- `delta.new_search_types` - new SearchType enum values not in local _VALID_SEARCH_TYPES
- `delta.changed_files` - cognee/ files whose content changed

---

## 4. Generating Stubs and TODO List

```bat
python scripts/auto_port.py
```

Output:
- `.upstream-sync/generated_stubs.py` - stub MCP tool functions for each new task
- `.upstream-sync/PORTING_TODO.md` - checkbox list of all porting steps

---

## 5. Porting Decisions

Not every upstream change needs a corresponding MCP tool. Evaluate each item:

### New Tasks
| Category | Action |
|----------|--------|
| Core cognify/search/forget tasks | Port as MCP tool stub, implement |
| Embedding model tasks | Usually internal - check if user-facing |
| DB migration tasks | Probably internal - skip unless it affects public API |
| Test/eval tasks | Skip |

### New API Routes
| Route pattern | Action |
|--------------|--------|
| `/v1/*` data operations | Port as MCP tool |
| `/v1/activity/*` | Check if needed for monitoring tools |
| `/v1/settings/*` | Check if config changes needed locally |
| Internal/health routes | Usually skip |

### New SearchType Values
Always add to `_VALID_SEARCH_TYPES` in `bin/enhanced_cognee_mcp_server.py` if they appear in upstream SearchType enum. Update the `test_valid_search_types_count` test to reflect the new count.

---

## 6. Implementation Steps

### Step 1: Create feature branch

```bat
git checkout -b feature/port-upstream-vX.Y.Z
```

### Step 2: Review changed files

For each file in `delta.changed_files`, check if local Enhanced patches need updating:

```bat
# View what changed in a specific file between releases
python scripts/upstream_diff.py --output temp_report.json
# Then open temp_report.json and review changed_files list
```

Key files to always review:
- `cognee/api/v1/*/` - API layer changes
- `cognee/tasks/*/` - New or changed task pipeline steps
- `cognee/shared/data_models.py` - SearchType enum and model changes
- `cognee/infrastructure/*/` - Infrastructure adapter changes

### Step 3: Implement new MCP tools

For each stub in `.upstream-sync/generated_stubs.py`:

1. Copy the stub into `bin/enhanced_cognee_mcp_server.py` after the last `@mcp.tool()` block
2. Implement the stub body, following Phase 2/3 tool patterns:
   - Import from cognee.* lazily (inside the function body)
   - Return ASCII-only strings (OK/ERR/WARN prefix)
   - Handle ImportError for optional deps gracefully
3. Also create a canonical module in `bin/mcp_modules/` for the new tools

### Step 4: Update SearchType values

If `delta.new_search_types` is non-empty:

```python
# In bin/enhanced_cognee_mcp_server.py, update _VALID_SEARCH_TYPES:
_VALID_SEARCH_TYPES = {
    "SUMMARIES", "CHUNKS", ...
    "NEW_TYPE_1", "NEW_TYPE_2",  # Added from vX.Y.Z
}
```

Also update the test:
```python
# In tests/unit/test_phase4_coverage.py -> test_valid_search_types_count:
assert len(node.value.elts) == 17  # was 15, now 17
```

### Step 5: Update tool count in tests

If new `@mcp.tool()` decorators were added, update `test_tool_count_is_70`:

```python
# In tests/unit/test_phase4_coverage.py -> test_tool_count_is_70:
assert count == 72, f"Expected 72 @mcp.tool() decorators, found {count}"
```

### Step 6: Run the test suite

```bat
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
python -m pytest tests/unit/ -q
```

All tests must pass before proceeding.

### Step 7: Run quality gates

```bat
python scripts/check_no_hardcoded_categories.py bin/enhanced_cognee_mcp_server.py
python scripts/check_ascii_output.py bin/enhanced_cognee_mcp_server.py
```

Both must exit 0.

### Step 8: Update sync metadata

```bat
# Update last_seen_release.txt
echo vX.Y.Z > .upstream-sync/last_seen_release.txt

# Update sync-metadata.json
# Edit .upstream-sync/sync-metadata.json:
#   "upstream_last_synced": "vX.Y.Z"
#   "upstream_target_rebase": "vX.Y.Z"
#   "last_sync_date": "YYYY-MM-DD"
#   "notes": "Phase N complete: ..."
```

### Step 9: Commit and create PR

```bat
git add -p  # stage changes selectively
git commit -m "feat: port upstream vX.Y.Z changes

- N new MCP tools: tool1, tool2, ...
- M new SearchType values: TYPE1, TYPE2
- Updated X cognee/ files for compatibility

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin feature/port-upstream-vX.Y.Z
```

Create a PR with label `upstream-sync` and close the tracking issue.

---

## 7. Breaking Change Handling

Some upstream releases include breaking changes to the cognee/ API.

Signs of a breaking change:
- A function signature changes in `cognee/api/v1/*/`
- A SearchType value is REMOVED from the enum
- A database schema migration is required
- A configuration key is renamed or removed

When breaking changes are detected:

1. **Check existing tests**: Run `python -m pytest tests/unit/ -v` and identify failures
2. **Assess impact on Enhanced tools**: Search for the changed symbol across the MCP server
3. **Update callers**: Fix each failing import/call
4. **Add compatibility shim if needed**: For removed SearchType values, keep them in `_VALID_SEARCH_TYPES` but map them to the nearest available type, returning a WARN message

---

## 8. Full Rebase (Major Version Bump)

For major upstream releases (e.g. v1.x -> v2.0), a selective cherry-pick is not enough.
Use the full rebase strategy (as used in Phase 1 for v0.5.1 -> v1.0.9):

1. Fetch upstream tag: `git fetch upstream vX.0.0`
2. Identify Enhanced-specific files via `.upstream-sync/enhanced-patches/`
   (see `enhanced-patches/README.md` for the manifest, including the
   privacy-first telemetry opt-in in `cognee/shared/utils.py`).
3. Check out cognee/ from upstream: `git checkout upstream/vX.0.0 -- cognee/`
4. Re-apply Enhanced patches from the patches directory
   - CRITICAL: re-apply the telemetry opt-in
     (`enhanced-patches/telemetry_opt_in.diff`) so product telemetry stays
     OPT-IN / air-gapped. Without it, upstream `send_telemetry` phones home to
     https://test.prometh.ai by default on every add/cognify/search.
5. Resolve conflicts manually
6. Run full test suite
7. Update `.upstream-sync/sync-metadata.json` with `"rebase_strategy": "Option A - full rebase onto vX.0.0"`

---

## 9. File Reference

| File | Purpose |
|------|---------|
| `.upstream-sync/last_seen_release.txt` | Local baseline tag (single line) |
| `.upstream-sync/sync-metadata.json` | Full sync state record |
| `.upstream-sync/last_diff_report.json` | Last generated diff report |
| `.upstream-sync/PORTING_TODO.md` | Last generated porting checklist |
| `.upstream-sync/generated_stubs.py` | Last generated MCP tool stubs |
| `.upstream-sync/enhanced-patches/` | Hand-maintained patch files for Enhanced customizations |
| `scripts/upstream_diff.py` | Diff report generator |
| `scripts/auto_port.py` | Stub and TODO generator |
| `.github/workflows/upstream_sync.yml` | Weekly automated monitor |
| `bin/mcp_modules/` | Modular MCP tool registry (Phase 5+) |

---

## 10. PR Labeling Guide

| Scenario | Labels |
|----------|--------|
| New tools from upstream task | `upstream-sync`, `enhancement` |
| Breaking change fix | `upstream-sync`, `breaking-change` |
| SearchType update only | `upstream-sync`, `chore` |
| Full rebase (major version) | `upstream-sync`, `breaking-change`, `major` |

---

**Maintained by**: Vincent S. Pereira  
**Last updated**: 2026-05-13
