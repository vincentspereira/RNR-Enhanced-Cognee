# Runbook RB-007: Upstream Sync Conflict Resolution

**Applies to:** RNR Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Maintainers responsible for upstream parity

---

## Overview

RNR Enhanced Cognee is a fork of topoteretes/cognee. A scheduled GitHub Actions
workflow runs weekly to detect changes in the upstream repository. When the
workflow fires a "new upstream version" alert, this runbook guides the maintainer
through classifying and incorporating the upstream changes without breaking the
RNR Enhanced Cognee extensions.

---

## Symptoms

- A GitHub Actions workflow named "Upstream Sync Check" has status [FAILED] or
  has posted a comment to a tracking issue.
- The tracking issue title matches the pattern:
  "Upstream sync required: cognee vX.Y.Z released".
- A maintainer has run scripts/upstream_diff.py manually and found a non-empty
  diff report.

---

## Diagnosis Steps

### Step 1: Generate the diff report

From the repository root, with the virtual environment active:

    python scripts/upstream_diff.py --upstream-tag vX.Y.Z --output diff_report.txt

Replace vX.Y.Z with the upstream tag from the tracking issue. The script compares
the upstream tag against the cognee/ subdirectory in this repository.

The report is structured in three sections:

    SECTION A: API-Breaking Changes
    SECTION B: Additive Changes (new files, new functions)
    SECTION C: Internal Changes (implementation details, no public API change)

Read each section before taking action. A single upstream release may contain
items in all three sections.

---

### Step 2: Classify the changes

For each item in the diff report, classify it using this table:

    Classification         Description
    -------------------    -------------------------------------------------
    API-breaking           A public function or class was renamed, removed,
                           or its parameters changed in an incompatible way.
    Additive               A new file, function, or class was added. Existing
                           callers are unaffected.
    Internal               Implementation changed but the public interface is
                           stable (refactor, performance fix, docstring update).

Record your classifications alongside each diff item in diff_report.txt before
proceeding. Items you cannot classify should be escalated to a second maintainer.

---

### Step 3: Check whether RNR Enhanced Cognee overrides the changed files

For each changed file identified in Step 2, check whether RNR Enhanced Cognee has
modified that file:

    git log --oneline cognee/<changed_file_path>

If the log is empty, RNR Enhanced Cognee has not touched the file; the upstream change
can be applied directly. If the log has entries, RNR Enhanced Cognee has extended or
overridden the file; the upstream change must be merged carefully.

---

## Fix Steps

### Fix A: Additive changes (new files, new functions)

Additive changes are the safest category. For each additive item:

1. Run the auto-port script to generate a stub MCP tool entry:

       python scripts/auto_port.py --diff-item "<item_id_from_report>"

   The script creates a new tool stub in src/mcp_tools/ and adds the tool to the
   MCP server's tool registry. The stub returns a "[INFO] Not yet implemented"
   response.

2. Review the generated stub:

       cat src/mcp_tools/<generated_tool_name>.py

3. If the new upstream function is straightforward, implement the tool body
   instead of leaving the stub. If it requires significant work, leave the stub
   and open a GitHub issue for full implementation.

4. Run the fast test suite to confirm no regressions:

       pytest -m fast

---

### Fix B: Internal changes (no public API change)

For internal changes in files that RNR Enhanced Cognee has not modified:

    git checkout upstream/<tag> -- cognee/<changed_file_path>

For internal changes in files that RNR Enhanced Cognee has modified:

1. View the upstream diff for the file:

       python scripts/upstream_diff.py --file cognee/<changed_file_path> --upstream-tag vX.Y.Z

2. Apply the relevant lines manually using a text editor. Preserve any Enhanced
   Cognee additions (lines introduced by commits in git log for that file).

3. Run the full test suite:

       pytest

---

### Fix C: API-breaking changes

API-breaking changes require the most care.

1. Identify which RNR Enhanced Cognee MCP tools call the changed upstream function
   or class:

       python -m scripts.find_upstream_callers --symbol <changed_symbol>

   The script outputs a list of RNR Enhanced Cognee files and line numbers.

2. Update each caller to use the new upstream API. Test each tool after updating:

       pytest tests/mcp_tools/test_<tool_name>.py

3. Update the cognee/ infrastructure file itself:

       git checkout upstream/<tag> -- cognee/<changed_file_path>

   Then re-apply any RNR Enhanced Cognee extensions that existed in the file (visible
   in git log for that file).

4. Run the full test suite:

       pytest

5. If the breaking change affects the external MCP tool interface (a tool's
   parameters change), update the Python SDK (ADR-008) and bump the SDK's minor
   version. Document the parameter change in docs/mcp/tool-reference.md.

---

### Fix D: Update the implementation plan

After all changes are applied and tests pass:

1. Open docs/plans/MASTER_IMPLEMENTATION_PLAN.md.
2. Find the "Upstream Parity" section.
3. Update the "Last synced upstream version" line to the new tag.
4. Record any stub tools (Fix A) that were not fully implemented, with the
   GitHub issue number.

---

### Fix E: Run the full verification

    pytest
    pre-commit run --all-files
    RNR-Enhanced-Cognee health

All three must pass before committing the sync changes.

Commit with a message of the form:

    chore: upstream sync cognee vX.Y.Z

    Additive: <count> new tool stubs added
    Internal: <count> files updated
    Breaking: <count> API changes resolved

---

## Verification

1. The test suite passes with no failures.
2. pre-commit run --all-files reports no violations.
3. RNR-Enhanced-Cognee health shows all components [OK].
4. The tracking issue is closed or updated with the sync summary.

---

## Postmortem Template

    Incident: Upstream Sync Conflict
    Upstream version: cognee vX.Y.Z
    Date sync completed: YYYY-MM-DD
    Maintainer: <name>

    Change summary:
    - API-breaking:  N items
    - Additive:      N items (N stubs, N fully implemented)
    - Internal:      N items

    Files modified in RNR Enhanced Cognee: <list>

    Test results: pytest <pass/fail>  pre-commit <pass/fail>

    Complications:
    <Describe any item that was harder to resolve than expected.>

    Follow-up Actions:
    - [ ] Implement stub tool: <tool_name> (GitHub issue #NNN)
    - [ ] Review breaking change impact on Python SDK (due: YYYY-MM-DD)
