# ADR-007: Pre-Commit Hooks for Automated Quality Gates

**Status:** Accepted
**Date:** 2026-05-14
**Deciders:** RNR Enhanced Cognee maintainers

---

## Context

RNR Enhanced Cognee has two project-wide rules that every code change must respect:

1. ASCII-only output: no Unicode symbols, no emoji, no arrows (ADR-002).
2. Dynamic categories: no hardcoded ATS, OMA, or SMC strings in code (ADR-003,
   Phase 6).

In practice, these rules were enforced only by code review. Reviewers occasionally
missed violations, and violations were discovered during CI runs that run minutes to
hours after the commit. Fixing them required an amended commit or a follow-up
commit, polluting the history and interrupting the contributor's flow.

Additionally, the project has accumulated lint debt (ruff) and a small set of known
security anti-patterns (bandit). CI catches these but not until after push, which
means the feedback loop is too slow for contributors working offline or on branches
that must pass CI before merging.

A faster quality gate at the moment of commit would prevent most rule violations
from ever reaching the repository.

---

## Decision

Adopt the pre-commit framework (https://pre-commit.com) as the standard mechanism
for all commit-time quality checks. The .pre-commit-config.yaml in the repository
root defines the following hooks, run in order:

1. ruff
   Source: pre-commit/mirrors-ruff
   Purpose: Lint and auto-fix Python files. Enforces the project's ruff.toml
   configuration. Blocks the commit if unfixable lint errors remain after auto-fix.

2. bandit
   Source: PyCQA/bandit
   Purpose: Static analysis for common security issues (hard-coded secrets,
   shell injection, use of eval). Runs with --skip B101 (assert statements are
   acceptable in tests). Blocks the commit if any medium or high severity issue is
   found.

3. check-no-hardcoded-categories
   Source: local hook (scripts/hooks/check_no_hardcoded_categories.py)
   Purpose: Scans staged Python files for the strings "ats", "oma", and "smc" as
   standalone words in string literals or enum values. Passes if no matches are
   found. Provides a clear error message with file and line number on failure.

4. check-ascii-output
   Source: local hook (scripts/hooks/check_ascii_output.py)
   Purpose: Scans staged Python files for Unicode codepoints above U+007F in
   string literals and print/return statements. Permits Unicode in comments and
   docstrings (where it is acceptable for explanatory text). Blocks the commit and
   reports the offending codepoint and line number on failure.

5. pytest-fast
   Source: local hook (scripts/hooks/run_fast_tests.sh)
   Purpose: Runs the test suite subset marked with @pytest.mark.fast. This subset
   covers unit tests that complete in under 30 seconds total without requiring
   database containers. Blocks the commit if any fast test fails.

Installation for a new contributor:

    pip install pre-commit
    pre-commit install

After install, hooks run automatically on every git commit. To run manually against
all staged files:

    pre-commit run

To run against all files in the repository (for one-time audit):

    pre-commit run --all-files

To bypass hooks in exceptional cases (document the reason in the commit message):

    git commit --no-verify -m "emergency: revert broken migration"

Bypassing hooks is logged in the commit message convention and is subject to review
in the PR. It must never be used to skip the ASCII or category checks on production
code.

---

## Consequences

**Positive**
- ASCII and dynamic-category violations are caught at commit time, before push
  and before CI, giving the contributor immediate feedback.
- Lint and security issues are caught offline, without waiting for a CI run.
- The fast test suite gives a quick sanity check that basic functionality was not
  broken by the change.
- The pre-commit framework handles hook version pinning, isolation, and updates
  independently of the project's own virtual environment.

**Negative**
- Every contributor must run pip install pre-commit && pre-commit install once
  after cloning. Contributors who skip this step receive no pre-commit protection.
  The CI pipeline must also run pre-commit run --all-files to catch violations from
  contributors who did not install hooks.
- The first pre-commit run after a framework update downloads hook environments,
  which requires a network connection and can take 30-60 seconds.
- Commits are blocked if any hook fails. Contributors who do not understand why
  a hook failed may feel frustrated. Hook error messages must be kept clear and
  actionable.
- The pytest-fast hook adds up to 30 seconds to every commit on slow machines.
  Contributors with very slow machines may find this disruptive; they can configure
  SKIP=pytest-fast in their shell environment temporarily.

---

## Alternatives Considered

**CI-only quality checks**
Run ruff, bandit, and the category/ASCII checks only in GitHub Actions. Rejected
because the feedback loop is 3-10 minutes (push, wait for CI, read results, fix,
push again). Violations that would take 10 seconds to fix locally take 10 minutes
when caught in CI.

**Manual discipline with documented rules**
Document the ASCII and category rules (as in ADR-002 and ADR-003) and rely on
contributors to remember them. Rejected because Phase 6 demonstrated that even
well-documented rules are violated by automated tools and human error. A systematic
gate is more reliable than documentation alone.

**Custom git hooks without the pre-commit framework**
Write shell scripts in .git/hooks/pre-commit directly. Rejected because .git/hooks
is not version-controlled, so each contributor must set up hooks manually with no
shared configuration. The pre-commit framework solves this with .pre-commit-config.yaml
in the repository, which is committed and shared automatically.

**Husky (Node.js-based hook manager)**
Husky is widely used in JavaScript projects. Rejected because it requires Node.js,
which is not a dependency of this Python project. Adding a Node.js toolchain for
hook management would increase the contributor environment complexity significantly.
