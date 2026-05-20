# Contributing to Enhanced Cognee

Welcome! This is the quick-start guide for contributors. The full
contributor guide -- coding standards, DCO, dev setup, test conventions
-- lives at [`docs/development/CONTRIBUTING.md`](docs/development/CONTRIBUTING.md).

## Project rules at a glance

A handful of project-specific rules that every PR must honour. These
are enforced in code review and (where possible) by CI:

- **ASCII-only output** in all source code, tests, logs, and scripts.
  Windows cp1252 consoles cannot print Unicode; use `OK` / `WARN` /
  `ERR` / `[OK]` / `[ERROR]` rather than `✓` / `✗` / `→` / emojis.
- **No hard-coded provider names** in new code. All four DB tiers go
  through `src/db_factory.py` and accept env-var-driven providers
  (`ENHANCED_RELATIONAL_PROVIDER` / `ENHANCED_VECTOR_PROVIDER` /
  `ENHANCED_GRAPH_PROVIDER` / `ENHANCED_CACHE_PROVIDER`). See
  [`docs/PROFILES.md`](docs/PROFILES.md) for the current matrix.
- **No hard-coded memory categories** (`ATS` / `OMA` / `SMC` etc.).
  Load category prefixes from `.enhanced-cognee-config.json`.
- **No emojis in new files** unless the user explicitly asks for them.
- **No new Markdown files in the repo root** unless explicitly asked --
  put new docs in `docs/`.

## PR workflow

`main` is protected. Four required status checks must pass before
merge: `Lint and Code Quality`, `Unit Tests`, `Security Audit`,
`Integration Tests`.

```bash
# 1. Branch
git checkout -b feat/<topic>-YYYY-MM-DD     # or fix/, docs/, chore/, etc.

# 2. Work + test
python -m pytest tests/unit/ tests/system/  # full suite expected to pass
python -m pytest --cov=src                  # coverage stays above 85%

# 3. Commit -- Conventional Commits prefix required
git commit -m "feat(scope): brief description

Details about the change.

Co-Authored-By: Your Name <your@email>"

# 4. PR -- use the template at .github/pull_request_template.md
gh pr create --base main --head feat/<topic>-YYYY-MM-DD

# 5. Wait for the 4 required checks. Then squash-merge:
gh pr merge --squash --delete-branch
```

## Conventional Commits prefixes

| Prefix | When to use |
|---|---|
| `feat(scope):` | new feature or capability |
| `fix(scope):` | bug fix |
| `chore(scope):` | infrastructure, CI, deps, tooling |
| `docs:` | documentation only |
| `refactor:` | code change with no behaviour change |
| `test:` | tests only |
| `perf:` | performance improvement |

## Coding standards

- **Tests for every behaviour change** -- unit tests under
  `tests/unit/` and (where they exercise live infra) integration
  tests under `tests/integration/`.
- **Lazy-import optional dependencies** in adapter modules so installs
  that don't opt into that provider don't pay the import cost. See
  the existing adapters in `src/db_adapters/` for the pattern.
- **No silent failures.** Surface errors with clear `ValueError` /
  `NotImplementedError` messages that point at the relevant doc
  section.
- **Don't add abstractions before the second concrete need.** Three
  similar lines is fine; premature interfaces are not.

## Reporting issues

Use the templates at `.github/ISSUE_TEMPLATE/`:

- 🐛 [Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
- ✨ [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)
- 📚 [Documentation](.github/ISSUE_TEMPLATE/documentation.yml)

For security issues, **do not file a public issue** -- email the
maintainer or open a private security advisory on GitHub.

## License + DCO

Enhanced Cognee is Apache-2.0. Every commit must conform to the
[Developer Certificate of Origin](https://developercertificate.org/);
the PR template includes the DCO affirmation checkbox. Sign-off your
commits with `git commit -s` if you prefer the inline DCO line.

## Full guide

The longer-form contributor handbook lives at
[`docs/development/CONTRIBUTING.md`](docs/development/CONTRIBUTING.md).
It covers dev environment setup, the upstream-sync workflow against
`topoteretes/cognee`, and the community channels.
