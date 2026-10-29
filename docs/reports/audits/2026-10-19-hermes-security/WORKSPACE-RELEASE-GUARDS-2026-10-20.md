# Independent Workspace release safeguards

Prepared 20 October 2026 while the owner and isolated Ubuntu-Hermes session
handle credential custody and installed deployment. This update supersedes the
earlier ledger's unit-only main-protection finding. It does not change the live
Hermes service/model/profile, revoke provider keys or qualify private activation.

## Implemented and verified

- Main now requires five existing maintained contexts: Required CI (unit tests),
  default-stack, canonical-browser, frontend (cognee-frontend), and
  frontend (dashboard/nextjs-dashboard).
- All five are bound to the verified GitHub Actions application, ID 15368.
  The branch must be up to date and protection applies to administrators. The
  previous complete configuration is privately archived; unrelated settings and
  main's source revision were verified unchanged. Administrators can still
  deliberately edit their own protection configuration.
- `.github/release-checks.json` records the reviewed expected configuration.
  `scripts/check_release_readiness.py` checks live read-only evidence for a chosen
  immutable revision, including complete pagination, newest trusted app results,
  strict protection, current main ancestry and moving refs/results. It does not
  merge, dispatch work, change settings or certify owner/installed-host acceptance.
- Missing, failed, skipped, neutral, cancelled, wrong-revision, untrusted and
  incomplete evidence cannot clear this review. Raw GitHub errors, annotations,
  URLs and credentials are not echoed. The client supports the installed gh 2.45
  pagination format without requiring a CLI upgrade.
- Thirty-seven focused local security regression tests pass with zero failures
  or skips. Syntax compilation and whitespace checks pass. This is separate from
  the previously recorded full application suite and any later hosted run.
- Live API review verified the strengthened protection and exercised the tool's
  refusal on historical hosted results with failed frontend audit checks. A
  newer documentation-only revision with missing checks is correctly refused;
  the prior passing unit/image evidence is not silently reused for that revision.

See [the release-check runbook](../../../runbooks/RELEASE-CHECKS.md) for commands,
exit codes, scope and required workflows. All three relevant workflows run on
pull requests targeting main, so their narrower delivery-branch push filters do
not skip the required PR workflow as a whole.

## Reviewed dependency alternatives

The dependency chain was traced again: @next/eslint-plugin-next 16.4.2 depends
on fast-glob 3.3.1, which reaches micromatch/braces. The installed TypeScript
resolver already uses tinyglobby; upgrading that resolver would not remove the
affected Next plugin chain. The latest available Next configuration still brings
the affected plugin. The official braces advisory still has no fixed release and
the npm registry still reports 3.0.3.

Keep the existing tested bounded-depth backport and complete audit gates. Do not
remove lint rules, substitute an unqualified glob implementation, mislabel a
version, suppress findings or downgrade just to report a green release. This
external dependency condition remains open despite the completed safeguards.

## Remaining boundaries

- Owner credential classification/revocation and independently accessible
  recovery material remain owner evidence, not code-generated confirmation.
- Installed Hermes OS/service/model/provider/schema/index/backup/restore/timer
  qualification remains with the already running isolated session.
- Actual v11 Windows PowerShell/DPAPI/Task Scheduler and off-machine archive
  recovery need native Windows evidence; Workspace cannot execute that control
  route and has not enabled interop or mounts.
- The broader legacy image and additional providers/features retain their
  separate admission/qualification scope. The restricted-service checks do not
  imply full legacy release support.
- After Hermes results are available, reconcile its branch/report with current
  source, run the required checks on the final candidate and review remaining
  acceptance conditions before the already conditionally authorized main merge.

These are operational, owner, upstream or deliberately separate qualification
items. They must not be described as completed just because the independent
Workspace release-safeguard implementation is finished.
