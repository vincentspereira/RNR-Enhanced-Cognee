# Enhanced Cognee release status - 21 October 2026

The protected Hermes test deployment is qualified. The full remediation release,
main merge, everyday-bot rollout and other-project onboarding are not complete.
This table reconciles the plan's six phases; earlier reports remain historical
evidence, not six separately completed phases.

| Plan phase | Current disposition | Remaining work |
|---|---|---|
| 0 - Preserve/baseline | Originals, older stores/history and instruction/source evidence preserved | Owner disposition of real exposed credentials and independent service-key recovery custody |
| 1 - Access control | Restricted service/API/worker/operator identities, scoped credentials, actual non-admin denial tests and cross-scope fleet tests qualified | Verify/admit each intended everyday-bot operating boundary; broader retained legacy/provider paths are separate |
| 2 - Storage/memory | Canonical schema/history, private spaces, reviewed sharing, index worker/rebuild, restart consistency and encrypted service restore qualified | Migrate old/private data only when explicitly selected and qualified; no blanket migration or unrestricted cross-project access |
| 3 - Packaging/release | Core source/stack/image checks and real browser/SDK evidence passed on recorded source revisions | Resolve enforced frontend development-dependency findings; validate all required checks on the final candidate; then conditional main merge |
| 4 - Hermes integration | Eight-tool provider, real non-admin qualification and five local-model scenarios passed | Review/admit an everyday profile, credential renewal and resource behavior, then stage the bot fleet; actual profiles are not enabled by synthetic tests |
| 5 - Operations/private use | Protected daily encrypted backup, disposable restore, restart/timer catch-up and temporary-account cleanup passed | Owner recovery/revocation, complete Windows/provider recovery, actual scheduled run and final private-use review |

## Confirmed evidence and its dates

The installed qualification evidence is dated 20 October. It records 93 complete
qualification tests, 41 focused real-store regressions, 11 native provider checks,
11 actual OS denial checks, three real SDKs, Chromium and five local-model
scenarios. The lanes overlap and must not be added as distinct tests. The later
synthetic service-fleet test admitted 41 bot scopes and a controller, with
cross-scope denials and reviewed sharing/revocation verified. It did not activate
the real bots or run 42 simultaneous model conversations. The temporary Linux
test account was removed; the real Windows rnr-worker account is a separate
Spatial isolation component and must remain in place.

The latest recorded hosted core runs, rechecked through GitHub on 21 October,
are on dac7826f56d876d5282f7210581f114e061ec06d:

- Required CI 39501940961 passed: 4,344 unit, 3 schema, 10 upstream settings/
  security and 80 canonical checks; zero failures/errors/skips.
- Default-stack 39501944103 passed 35 checks with zero skips.
- Dashboard 39501947497 passed the real browser and frontend build/check steps,
  but both frontend jobs failed the enforced dependency audit: five HIGH
  development-dependency matches each, zero production findings in that run.

These are dated exact-revision results, not hosted approval of subsequent
documentation/backup commits. No new successful full release run is inferred
from publishing the backup work.

Live recheck on 21 October: braces latest remains 3.0.3; the official advisory
GHSA-vfj7-8cjw-p6xm covers <=3.0.3, has no first patched version and is not
withdrawn. Existing source mitigation does not clear the enforced npm findings.
Do not fake a version, remove lint coverage, suppress the audit or merge around
this gate. Dependency-chain remediation and final release validation remain
repository work, not items the owner must solve through credential confirmation.

Live main-branch review still shows five strict required checks with administrator
enforcement: unit CI, default-stack, canonical-browser and both frontend checks.
Main remains at e25bd6356e38970c525e0258bdac983cd4079d29. Conditional merge approval
is retained, but its prerequisites have not all passed.

## Windows/backup progress

Current result: [v12 native qualification passed](WINDOWS-V12-NATIVE-PASS-2026-10-22.md):
45 passed, zero failures/skips, exit 0; all 15 receipt hashes match installed
files. Earlier native-pending/failure observations below are historical. First
real v12 backup, provider/recovery review and task transition remain pending;
v11 remains scheduled. Documentation updates leave qualified code unchanged.

22 October follow-up: the first native v12 test stopped with one failed empty
snapshot-list check after 16 passes. The shared PowerShell compatibility fix is
installed and passed 38 portable checks; its native Windows rerun is pending.
V11 remains the scheduled version. See
[the native qualification and cleanup follow-up](WINDOWS-V12-NATIVE-FOLLOWUP-2026-10-22.md).
The second native attempt passed run/scope selection and stopped at the restored
file verifier after 21 passes. The actual corrected file matches its source;
the shorter-path/hidden-traversal verifier correction is installed, with native
rerun pending. The owner's selective v11 extraction passed three file hashes,
and both text files opened readably. The blank console-summary projection is
corrected; the saved report was valid. Latest portable qualification passes 44
checks, with zero failures/skips. The retained original archive subsequently
passed a fresh full SHA256 check. Owner-approved temporary-copy cleanup completed:
`D:\Recovery-Test` was removed, preserving the original, provider copies and
small recovery evidence outside the test folder. Native v12 qualification is
still pending; the scheduled backup remains v11.

Latest native attempt stopped at the positive geometry-retention check after 41
passes: its fixtures were inside the qualification subtree excluded by the real
backup policy. The test now uses a separate private fixture root and an
unfiltered control, retaining the full production policy unchanged. The fix is
installed; portable qualification passes 48 checks, zero failures/skips. Native
Windows rerun is still pending.

Superseding result: [v11 completed successfully](WINDOWS-V11-COMPLETED-2026-10-21.md).
The owner supplied the successful 56-check qualification and manual v11 backup
exit code 0. The completed encrypted generation and both sync-folder copies are
confirmed. The owner subsequently reported both cloud clients fully synced and
the OneDrive recovery transfer complete. A full 47,503,603,481-byte recovery-copy
SHA256 pass matches the recorded manifest, with no file change during the read.
The owner's subsequent 7-Zip 26.03 password/integrity test reported `Everything
is Ok` for all 744,108 files. Representative text-file extraction/hash/readability
is now confirmed. Application restoration, independent remote provenance and
actual scheduled execution still require their separate evidence; see the
linked recovery follow-up and the simple
manual at `scripts/windows/BACKUP-AND-RESTORE-SIMPLE-MANUAL.md`.

Owner-completed steps now include KeePassXC vault/passphrase recovery, archive
password setup, Microsoft sign-in entry and correction of the weekly v11 task.
The downloaded vault copy opened successfully; this does not prove independent
custody of the separate Cognee age/signing/encryption/index keys.

The real v11 backup completed encrypted-base creation and both sync-folder
copies; the earlier growing-partial observation is superseded. V12 is separately
prepared with broader approved
coverage, encrypted content reuse, resumable provider copies, explicit OneDrive
original/model-weight gaps and preserved recovery inventories. Its native test,
real source capture and downloaded recovery have not yet run. It does not replace
or change the configured v11 task. See the detailed backup review.

## Work still assigned to the implementation session

Finish and qualify backup/inventory changes; support native Windows results;
execute/reconcile the guarded Hermes folder review when a native route is
available; remediate the frontend dependency chain without weakening checks;
run final exact-candidate release validation and reconcile the plan. Merge only
after the agreed prerequisites pass. Then admit one real Hermes profile before
the wider bot fleet and selected Workspace projects. No percentage or completion
date is asserted while these independent gates remain unresolved.

Owner-only actions remain private credential revocation/replacement and recovery
custody, plus entering passwords locally and confirming downloaded recovery.
No passwords/private keys should be pasted into chat or committed to Git.

References:

- [Protected installed deployment](HERMES-PROTECTED-DEPLOYMENT-2026-10-20.md)
- [Fleet and hosted checks](WINDOWS-AND-FLEET-FOLLOWUP-2026-10-20.md)
- [Current backup/home review](BACKUP-V12-AND-HOME-REVIEW-2026-10-21.md)
- [Required CI](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39501940961)
- [Frontend audit run](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39501947497)
- [Official advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
