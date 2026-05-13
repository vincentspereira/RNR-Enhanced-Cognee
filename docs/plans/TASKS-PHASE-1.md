# Phase 1 Task List: Option A Rebase onto v1.0.9

**Approved by**: Vincent S. Pereira (2026-05-13)
**Strategy**: Option A - full rebase of cognee/ core onto upstream v1.0.9 stable
**Target branch**: `rebase/onto-v1.0.9`
**PR title**: `[Phase 1] Rebase cognee/ onto upstream v1.0.9`
**Reviewer**: vincentspereira

---

## Pre-Rebase (Non-Destructive)

- [x] Phase 0 pre-flight complete (PHASE-0-REPORT.md)
- [x] .upstream-sync/last_seen_release.txt = v0.5.1
- [x] 461/461 unit tests passing on main branch
- [ ] Write scripts/check_ascii_output.py
- [ ] Write scripts/check_no_hardcoded_categories.py
- [ ] Add upstream remote (topoteretes/cognee)
- [ ] Fetch v1.0.9 tag from upstream
- [ ] Create branch rebase/onto-v1.0.9 from main

## Rebase Execution

- [ ] Download/checkout upstream cognee/ at v1.0.9 tag
- [ ] Identify Enhanced-specific patches inside cognee/ (diff vs upstream baseline)
- [ ] Replace cognee/ with upstream v1.0.9 content
- [ ] Merge pyproject.toml (upstream version bumps + Enhanced extras preserved)
- [ ] Keep all Enhanced-unique directories unchanged:
      - src/ (all 46 Enhanced modules)
      - bin/ (enhanced_cognee_mcp_server.py)
      - tests/unit/, tests/integration/, tests/system/, tests/e2e/
      - scripts/ (backup/restore scripts + new CI scripts)
      - docker/
      - docs/
      - cognee-frontend/ (deferred to Phase 4 per plan)
      - evals/ (deferred to Phase 4 per plan)

## Post-Rebase Validation

- [ ] Run scripts/check_ascii_output.py on cognee/ (new files)
- [ ] Run scripts/check_no_hardcoded_categories.py on cognee/
- [ ] Run 461 unit tests: target 461/461 pass
- [ ] Run integration tests against Docker stack
- [ ] Run MCP smoke test (bin/enhanced_cognee_mcp_server.py --help)
- [ ] Import check: python -c "import cognee; print(cognee.__version__)"

## Conflict Resolution Log

Record any conflicts or import errors found and how they were resolved:

| File | Issue | Resolution |
| ---- | ----- | ---------- |
| (filled during rebase) | | |

## pyproject.toml Merge Strategy

Take from upstream v1.0.9:
- All version bumps to existing dependencies
- New core dependencies added in v0.5.2 -> v1.0.9
- New optional dependency groups added upstream

Keep from Enhanced:
- All Enhanced-unique optional groups that don't conflict with upstream

Bump version in pyproject.toml:
- FROM: "0.5.1"
- TO: "1.0.9-enhanced" (marks this as a local Enhanced build based on v1.0.9)

## Acceptance Criteria

1. `python -c "import cognee; print(cognee.__version__)"` prints version without error
2. `python -m pytest tests/unit/ -q` passes 461/461 (or more, if new upstream tests ported)
3. `python scripts/check_ascii_output.py cognee/` exits 0
4. `python scripts/check_no_hardcoded_categories.py cognee/` exits 0
5. Docker stack + integration tests: no regressions
6. `python bin/enhanced_cognee_mcp_server.py` starts without import errors

## Known Risks

| Risk | Mitigation |
| ---- | ---------- |
| API changes in cognee/ that break src/ Enhanced modules | Fix imports in src/ to match new API |
| New mandatory deps in v1.0.9 not in pyproject.toml | Add them during pyproject.toml merge |
| Upstream removed features Enhanced-modules reference | Keep removed features in a `_compat/` shim |
| Test suite count changes (fewer if upstream removed tests) | Accept, document in PR |

---

**Status**: In Progress
**Last updated**: 2026-05-13
