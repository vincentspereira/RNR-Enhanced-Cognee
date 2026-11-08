# Hosted release checks and main protection

Prepared 20 October 2026. These controls close the gap between the owner's
conditional merge approval and the repository's former unit-only protection.
They do not certify private Hermes installation or owner recovery custody.

## Current required hosted checks

The reviewed policy is `.github/release-checks.json`. Main protection now requires:

| Check context | Maintained workflow | Scope |
|---|---|---|
| Required CI (unit tests) | ci-required.yml | Full unit lane, legacy schema and canonical checks |
| default-stack | canonical-memory-stack.yml | Actual four-store behavior, restricted package/image, restart recovery and unsuppressed image scan |
| canonical-browser | canonical-dashboard.yml | Actual browser/PostgreSQL memory flow |
| frontend (cognee-frontend) | canonical-dashboard.yml | Lint, build, mitigation regression, image build and complete dependency audits |
| frontend (dashboard/nextjs-dashboard) | canonical-dashboard.yml | Dashboard lint/build/behavior, mitigation regression, image build and complete dependency audits |

All five contexts are bound to the verified GitHub Actions application identity,
app ID 15368. Main must be up to date; protection applies to administrators.
Existing unrelated protection settings were preserved. Configuration originals
are privately archived. Repository administrators can still deliberately edit
their protection configuration; this is not an immutable external policy.

Both canonical workflows run on pull requests targeting main, including changes
that their narrower delivery-branch push filters would omit. Required CI also
runs on such pull requests. Use a PR or explicit workflow dispatch to obtain all
checks for the chosen candidate. A passing workflow from an earlier commit does
not qualify a newer documentation-only commit automatically.

GitHub treats some skipped/neutral checks as successful for branch protection.
The additional review tool below deliberately requires completed success. Unit
and browser workflows also retain their existing zero-skip report assertions.

## Read-only exact-revision review

From a checkout containing this tool, with the existing authenticated GitHub CLI:

```bash
python3 scripts/check_release_readiness.py --ref codex/hermes-memory-hardening
```

For the final reviewed candidate, prefer its full 40-character commit ID instead
of a branch that is still receiving changes. No secret value is a command argument.

The tool resolves the candidate and main, reads all check-result pages and accepts
only the newest exact-revision result for each configured GitHub Actions context.
An older success cannot replace a failed/in-progress rerun. Missing, skipped,
neutral, cancelled, untrusted and incomplete evidence refuses clearance. It also
checks pinned protection, the current main ancestry, moving references and check
results changing during review. Other/new protection requirements need explicit
policy review rather than being silently ignored. Unexpected data/API failures
produce a generic refusal without exposing provider diagnostics or credentials.

Exit codes:

- 0: the selected hosted checks and protection snapshot satisfy this policy.
- 1: valid evidence shows the hosted conditions are not all satisfied.
- 2: configuration or evidence is unavailable/invalid; no clearance is given.

This is a read-only snapshot and can become stale after observation. It never
changes protection, dispatches jobs, merges or authorizes release. Its report
always says installed host/owner acceptance is not assessed. Review actual Hermes
boundaries/model/backup/timer evidence and owner custody/revocation separately.
The larger legacy image and unselected optional providers retain their separate
qualification scope; the five checks do not admit all historical features.

## Outstanding dependency finding

The installed Next ESLint plugin brings fast-glob -> micromatch -> braces.
The current official advisory still has no listed fixed version, and the npm
registry reports braces 3.0.3 as latest. The tested depth backport remains in
place. Both full audit gates remain enforced, so those frontend checks still
fail while the version-matched findings remain. No advisory exception, fake
version, lint-rule removal or unsafe downgrade has been introduced.

The actual runtime/browser functionality and the complete dependency audit are
different evidence. Retain both. Do not bypass main protection to hide this
remaining release condition or interrupt the separately pinned Hermes deployment.

## Sources

- [GitHub branch protection API](https://docs.github.com/en/rest/branches/branch-protection)
- [GitHub check-run API](https://docs.github.com/en/rest/checks/runs)
- [GitHub required-check behavior](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Unresolved dependency advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
