# Consolidated launch qualification - 24 October 2026

Latest checkpoint: owner-run inspection verifies the candidate's completed
canonical correction/retraction, four preserved versions, cleared pending
clarification and peer 404. The earlier native turn's overall completion gate
remains open; do not replay the completed test record. Compatible source
dependency updates reduce the full-lock findings from 17 to 11, while the
restricted index lock retains 37 Pillow findings. See [the current canonical
effects/security report](CANONICAL-EFFECTS-AND-SECURITY-2026-10-24.md); older
counts and hosted runs below retain their original revision scope.

Hosted follow-up: Required CI passed on 06037eb7b, but the enforced memory audit
found 37 Pillow advisories. A compatible full-runtime Pillow fix passes 4344
unit tests; the restricted FastEmbed/Pillow conflict and broader audit findings
remain open. See [the dependency blocker](DEPENDENCY-LAUNCH-BLOCKER-2026-10-24.md).
The green functional results below are not a green dependency/release result.

Recommendation: continue the restricted candidate qualification. System-wide
Hermes/Enhanced Cognee launch remains unadmitted. The owner authorized proceeding
with pending tests and consolidating them into one or two batches. This authorizes
the qualification work, not an automatic global provider switch or main merge.

Environment: Ubuntu-Workspace, source parent c4552d64f01dc0c5e68be8c7a84d3f3ea10032a3.
No direct Ubuntu-Hermes host/model execution occurred in this session. Public
source delivery uses the existing approved codex/hermes-memory-hardening branch.
Private settings, credentials, failed fixtures and earlier deployments remain
preserved; the unrelated untracked renew_protected_test_tokens.py was not edited,
admitted or published.

## Completed source and disposable-store work

| Lane | Result | Scope |
|---|---|---|
| Complete unit lane | 4344 passed; zero failures/errors/skips | Separate Linux test overlay with pinned missing optional packages; existing runtime preserved; TCP denied |
| Hermes/operator/portable recovery lane | 1236 passed; zero failures/errors/skips | Current provider, launch harness, native-boundary simulations, filesystem locks/guards, actual age/restic/tar fixtures and portable Python backup |
| Real canonical PostgreSQL lane | 46 passed; zero failures/errors/skips | New disposable native PostgreSQL 16.15 instance; canonical access, history, sharing, key rotation, synthetic fleet spaces, outbox behavior and encrypted dump/disposable restore |

These lanes are separate evidence and should not be added to historical test
counts. No pytest warnings were reported in the final lanes. Coverage percentage,
fresh dependency/image audits, installed Hermes OS/model effects, full browser/
SDK/release qualification and full-fleet throughput were not measured by these
commands. Source checks do not establish the current installed host's state.
The native synthetic PostgreSQL instance was stopped after testing; its databases,
keys and fixture logs remain in private temporary storage. Existing services
were not restarted or changed.

The staged public diff passes the redacted gitleaks secret scan with zero
findings. An initial generic-key match was a public source SHA256 paired with
the provision_pilot_access.py filename; representing provenance as explicit
path/hash rows removes that false match without suppressing any scanner rule.

Four new regressions reproduced actual provider gaps before the repair: pending
clarification disappeared on session switch/restart, retraction could bypass a
lost pending gate, and a quote from the original uncertain turn could confirm
itself. The repaired provider uses bounded mode-0600 append-only metadata,
exclusive process locks and durable writes. It saves record IDs/turn markers,
not messages, confirmation quotes, memory content or credentials. A subsequent
human turn must supply the confirmation quote. Invalid state is retained and
refused; there is no automatic journal deletion or repair. Fifteen durability/
refusal cases now pass, including second-provider visibility, transport failure,
unsafe links/permissions, torn/oversized metadata and lock conflicts. This is
cooperating-process state; a malicious same-UID process with profile write access
is still outside its trust guarantee. Actual fleet OS boundaries remain open.

The installer pins a separate immutable candidate artifact. Historical installed
pilot checks retain their original hashes and continue to describe that original
generation. The new qualification launcher stages the candidate and tests it in
a new private /var/tmp profile, preserving the active pilot and its home-backup
policy. Thirty-three harness/admission cases pass, including hostile bundle
rejection before execution, strict receipt shapes, wrong-host/operator refusal,
restricted child execution and denial of unrelated model writes.

Initial failures remain preserved in private logs. The first broad unit run had
97 missing-package failures and 12 skips; the separate pinned overlay resolved
them without modifying the existing runtime. Candidate pin drift and an overly
long AF_UNIX fixture path were corrected. One privacy semantic fixture returned
401 instead of expected 409 during a backwards host-clock observation; its
synthetic token now starts 30 seconds in the past. Production JWT validation and
expiry checks were not relaxed. Native cached PostgreSQL tools needed their
existing libpq path; test-only wrappers supplied it without weakening the backup
module's sanitized environment. The final real encrypted recovery passes.

## Windows result reconciled

The owner's saved native-bc953f26467c43a4bb6c40c5669dba85 summary was read locally:
complete=true, native_windows=true, 62 checks passed, zero failures/skips. The
launcher, native test and task-updater receipt hashes match their installed and
repository copies. This closes the updated native synthetic Windows gate.
actual_homes_and_profiles_qualified, real_cloud_upload_verified and
offline_wsl_restore_verified remain false in that same report. No Windows task,
real backup, cloud copy or upload was started here.

## Two-batch execution and remaining work

The maintained procedure is
[the two-batch runbook](../../../runbooks/HERMES-CONSOLIDATED-LAUNCH-QUALIFICATION.md).
Batch 1 is the automated source/disposable integration group above. Batch 2 is
the installed operational acceptance window, keeping every subcheck explicit.

The next executable part of batch 2 is one pinned native candidate command. It
uses two separate restricted native Hermes processes, the explicitly selected
secondary pilot account and a real terminal answer between them. It checks the
new restart gate, model-driven uncertainty, later correction/retraction/history,
real signed-scope denial/reviewed sharing/revocation and original-pilot byte
preservation. Missing/expired/altered credentials must be denied. Reviewer and
signing authority stay with the operator; ordinary new-scope credentials are
passed only through the private process pipe. The existing pilot/model defaults,
service schedules and everyday bots are not switched. A refusal/429 stops the
run without account rotation or automatic replay. No installed pass is claimed
until the owner returns the resulting report.

That command does not implement or qualify unattended renewal. Installed
interrupted-renewal recovery, operator-owned unattended renewal, current database
generation recovery/index replay, real Windows/remote backup completion, actual
fleet inventory/launch identities/peer-secret boundaries, exact-candidate release
checks and the remaining private credential-review scope are still open. Some
are implementation/operational requirements, not existing tests waiting to be
concatenated. Complete these within the same host work batch where safe; do not
convert a native conversation pass into whole-fleet admission.

Earlier capture/recall/correction/privacy, manual renewal/profile restoration,
key-custody and authenticated daily-profile-timer passes retain their exact
scope and need no routine replay. Main merge and everyday/fleet activation stay
conditional. The final source evidence JSON records hashes without publishing
private fixtures or credential values.
