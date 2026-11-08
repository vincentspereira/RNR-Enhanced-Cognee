# Restricted Hermes pilot: operational readiness

Reviewed in Workspace on 23 October 2026. This is a source/evidence review,
not a new inspection of Ubuntu-Hermes. Preserve the existing service, profiles,
keys, backup generations and all qualification receipts. V12 remains paused.

## What is already established

The owner supplied native results for the protected runtime/provider and
restricted account. The pilot passes automatic selected capture, separate-process
recall and clear correction with preserved version history, using invented data
and temporary GPT-6.1-Sol subscription model arguments. Exact results are in
[the restricted-profile report](../reports/audits/2026-10-19-hermes-security/HERMES-RESTRICTED-PROFILE-2026-10-22.md).

Correction reached Cedar version 2, preserving version 1 and the Larch record.
The owner ran recall_corrected at helper revision
086e61e698e46b3bddec48befe35829ea46fe900. The model service returned 429 for
all three observed requests, classified as rate_limit; no memory tool ran.
That first-account attempt did not qualify corrected recall. The owner then
passed recall_corrected at 2117ba01ae473dfd0ff4698c212eec01c8c013cf using the
explicit secondary pilot credential: native completed turn, enhanced_get, two
model requests, version 2 and two active records. The current answer/citation,
prior version and all receipts were validated; checked settings/credentials
were unchanged and no memory write occurred. This establishes the narrow
corrected fresh-recall gate. It does not establish that the first account's
limit reset; do not replay completed write stages.

Older service backup/restore and 42-space tests retain their own revisions and
identities. They do not establish recovery of this later restricted profile or
installed admission of the current fleet. The owner already tested recovery-key
custody separately; do not ask for those completed steps again. Outstanding real
credential-review coverage must be reconciled against its existing private record.

## Credential operation

Latest owner-run update: manual renewal passed at
8fb6fca95cf5480830d748134da93b785645820a. The ordinary pilot token expires at
2026-10-24T09:15:06+00:00. New-token acceptance, missing/expired/altered refusal,
retained old environment and unchanged settings/OAuth passed with no model or
memory write. No interrupted attempt was reconciled in that run. Installed
interruption recovery, unattended lifecycle and fleet rollout remain separate.
The original issue/inspection history below retains its earlier time and scope.


The initial ordinary memory token was issued for 24 hours and its recorded
expiry was 2026-10-23T18:23:15+00:00. This is the initial receipt's expiry, not
a fresh observation of the installed token or the current clock. Successful
past calls do not establish future validity. Do not extend lifetime, assume a
renewal occurred or re-run initial provisioning against a populated scope.

The existing provision_pilot_access.py deliberately refuses an existing token
and requires an empty namespace. It is an initial issuer, not a renewal tool.
The untracked renew_protected_test_tokens.py in Workspace is preserved unrelated
work; this continuation neither admits nor publishes it as the pilot renewer.

check_pilot_codex.py now provides main_operations(approved_test=True), a prepared
read-only restricted-account check. It reads the ordinary memory token from the
pilot .env through the native scoped loader and reports only bounded expiry
metadata. Claims are decoded locally without a signing key and explicitly marked
unverified. Separate authenticated API status tests current server acceptance;
neither decoding nor a successful API response proves a future renewal path.

The check reads no auth.json, human credential store, operator key, test receipt
or memory content, constructs no chat agent and calls no cloud model. It compares
checked profile/settings/.env bytes after status. It does not renew tokens,
alter configuration or test backups. profile_backup_coverage_verified=false is
an explicit unverified gate, not a filesystem scan result. Use the next reviewed,
pinned/hash-verified operator command to check the local memory credential/API
while cloud model testing is deferred. This does not call the rate-limited model
or claim its limit has cleared. If the API refuses access, decoded expiry metadata
is still explicitly unverified; reconcile renewal rather than repeat model calls.

Before unattended operation, prepare and qualify a fixed-scope operator renewal
path with protected code and locking, a private no-replace old-file backup,
signature/identity/lifetime verification, fresh/expired/altered negative controls,
atomic environment publication and preservation of all other settings. Signing
authority stays out of the runtime account. Prove agent denial and recovery
after interrupted renewal; do not inject privileged renewal callbacks into a
profile controlled by the agent. Existing JWTs remain usable until expiry unless
an independently supported revocation path invalidates them. Do not rotate the
global signing key to stop one profile.

## Recovery coverage: keep the layers distinct

| Recovery item | Source/evidence finding | Required proof before private use |
|---|---|---|
| Canonical memory database | src/memory_backup.py streams pg_dump through age and signs a completion manifest | Current encrypted generation, signature/decryption and a disposable database restore with history and scope checks |
| Service/recovery keys | Separate protected files and owner-tested recovery package | Preserve that package/custody; reconcile any later key change without exporting secrets into reports |
| Restricted Hermes profile | /var/lib/hermes-runtime/.hermes/profiles/enhanced-cognee-pilot is outside the original user's home | Explicit encrypted profile backup and disposable recovery of settings, scoped access and native provider binding |
| Runtime qualification receipts/workspace | Files under /var/lib/hermes-runtime are outside the original user's home | Include retained test receipts and any original workspace work in explicit coverage; no automatic cleanup |
| Protected program artifacts | /opt/hermes-runtime releases and provider artifacts are separate from profile state | Record source/payload hashes and a verified rebuild or preserved artifact; restored plugin links must target the trusted artifact |
| Full-distro backup | Can contain /var/lib, if a real distro export includes it | Verify actual export provenance/date and disposable recovery; do not infer coverage from a selected-file backup |

Repository source confirms why home backup alone is insufficient:
scripts/windows/backup-all-wsl-v12.ps1 starts the home producer as
vincentspereira, and backup-v12/capture_home.py defaults --root to Path.home().
It does not select /var/lib/hermes-runtime. The separate capture_cognee.py stream
collects completed database dump/manifest pairs from /var/backups/enhanced-cognee;
it does not collect the Hermes profile. The original user's .hermes bot-profile
coverage therefore does not establish coverage of this new runtime home.

No Windows script, scheduled task or running backup is changed by this review.
Do not resume V12 just to close this gap. Prepare a Hermes-local encrypted profile
snapshot first, using an operator-controlled destination and existing approved
encryption/recovery mechanism. Exclude sockets and disposable caches; preserve
original work, profiles, credential files and receipts only inside encryption.
Use a no-write window on the selected profile and a supported consistent SQLite
snapshot for any live database. Never copy mutable SQLite/WAL files blindly.

Prove recovery in a fresh restricted disposable destination, never over the live
profile. Validate file permissions, checksums, consistent database integrity,
restored configuration/provider links and scope denial without publishing private
data or copying root keys into the agent home. A recovered expiring token can be
expired; qualify operator reissuance rather than weakening expiry or treating
token rejection as archive corruption. Preserve restored evidence unless the
owner explicitly permits its deletion. Any later collection to Windows/cloud
requires encrypted coverage, native checks and the existing pause/owner decisions.

## Remaining sequence

The [remaining rollout checklist](HERMES-REMAINING-ROLLOUT-CHECKLIST.md) groups
the open work into five shared readiness groups followed by actual fleet
admission. This is a work breakdown, not a fixed test/command count. The latest
owner-run clarify_followup failed; its missing condition is not established by
the terse original report. The updated helper adds bounded diagnostics and
post-turn preservation verification without weakening the behavior/write guard.

The subsequent owner diagnostic verified canonical/receipt preservation, zero
editing/write attempts, the correct pending target and a native completed turn
with a question mark. Only explicit read-tool ordering failed. Pinned Hermes
also prefetches before tools; the updated helper requires matching canonical
record retrieval and delivery in a successful observed model request before
accepting this read path. Earlier diagnostics did not capture that proof, so
one confirmation remains. Installed provider/core/settings/defaults are unchanged.

23 October owner-run update at helper revision
2117ba01ae473dfd0ff4698c212eec01c8c013cf: secondary pilot sign-in passed,
preserving original credential fields and checked settings. The non-model
operations check passed current authenticated local API status, reporting two
active records. Decoded token timing reported not expired/not within one hour
at the check, with expiry 2026-10-23T18:23:15+00:00; local signature checking
was false. No token renewal, profile-backup proof, model call, memory write or
runtime qualification occurred. These dated results supersede the pending
enrollment/local-status step, not the remaining gates below.

1. Enrollment, current local API acceptance and second-account corrected recall
   now have owner-run passes. Preserve dated evidence and use the secondary
   credential explicitly for subsequent model tests. Keep first-429 blocking,
   no automatic account rotation/status reset and unchanged main Hermes defaults.
2. Qualify ambiguous clarification, private-detail/credential exclusion and
   cross-scope denial in the current restricted runtime, reusing dated unchanged
   service evidence only where justified.
   clarify_followup is now prepared for one uncertain invented Cedar change,
   requiring a question and native pending clarification for the existing record
   with no canonical edit attempt and all prior evidence preserved. This is a
   single-turn test, not durable pending-state or human follow-up qualification.
   Owner-run 0768a43e confirms this single-turn case passed using verified native
   prefetch before clarification. Owner-run 37cc5d9b also confirms all eleven API
   privacy refusals and preservation checks passed without OAuth/chat-model use.
   Owner-run 79264eeb also confirms the native synthetic privacy turn passed with
   one secondary-account model request, no editing tool/write and preserved
   records/history/receipts/profile. Preserve these passes. Later human-answer,
   pending-state durability and retraction/history checks remain separate.
3. Preserve the owner-run manual renewal pass at 8fb6fca9; do not repeat it.
   Installed interruption recovery and unattended/fleet lifecycle remain open.
   The owner-run 61c272a7 recovery inventory also passed: 60 files/205571 bytes,
   no detected databases or problematic entries. Owner-run ca2682c6 also passed
   manual encrypted profile recovery of all 60 files with scoped access and live
   source preserved. Owner-run d7c7880c installed the daily job files, but its
   first run exited 1 and timer enable did not complete. Read-only inspection of
   the retained failure at 3bd4bf8f now confirms restricted_snapshot failure before
   any encrypted backup. Owner-run 058b71da observed launch EPERM; next qualify
   the external identity-launch candidate with a bounded transient probe.
   Owner-run 56c0d439 now identifies a setresuid refusal: the parent lacks
   effective CAP_SETUID while CAP_SETGID/no-new-privileges are present. The next
   candidate explicitly retains ambient CAP_SETUID in the root backup service
   and clears ambient/inheritable sets before the non-root reader. Its existing
   zero-effective/zero-ambient guard remains mandatory. This is a candidate
   policy correction, not an installed service repair; see the recovery runbook.
   Recurring operation
   and collector coverage
   and current canonical database recovery remain separate.
   Read HERMES-PILOT-RECOVERY.md and HERMES-PILOT-CREDENTIAL-RENEWAL.md.
4. Inventory actual profiles/bots and their launch identities. Do not copy the
   pilot token across bots or assume one shared OS account isolates their files.
5. Reconcile current service backup freshness, release/security checks, private
   credential review and the owner's activation review before staged rollout.

These are implementation/qualification tasks already within the requested plan;
this document adds no new activation, restart, deployment or sharing permission.

Latest 23 October owner evidence supersedes the failed snapshot candidate:
47b20e4d passed the corrected RAM-only restricted snapshot with child exit 0 and
both intended parent identity-switch capabilities effective. Installed units and
timer remained unchanged. A pinned exact-old-artifact guarded upgrade is now
prepared; the next owner action qualifies a real encrypted service run, verifies
its signed ciphertext and only then enables/verifies the daily timer. No model
call, key-custody replay or manual restore replay is needed. Actual recurring
operation and Windows collection are not yet claimed; see HERMES-PILOT-RECOVERY.md.

Owner-run ab8c990b follow-up: service replacement completed with original public
files preserved, but real_encrypted_backup_qualification failed before timer
enable completed. The summary groups execution/report/authentication checks,
so neither service failure nor backup absence/success is established yet.
Next run only the upgraded read-only inspector described in the recovery
runbook. It targets exact a1ffd4c258238847 runner bytes and retained invocation
status/report, without service start, credentials, models or writes. Do not
repeat the updater or claim recurring profile coverage until reconciled.

Owner-run 6b4453bf read-only inspection itself stopped in the grouped
service_state phase and returned no retained report. No write/restart/key read
occurred. Next use the detailed read-only inspector: separate status/policy
read/parse stages, bounded exception/errno/exit metadata and preserved partial
state. Missing current invocation metadata triggers only a labeled latest
retained journal diagnostic; it does not prove that the report is from the
upgraded attempt. No root cause or completed backup is inferred yet.

Owner-run 3b456aeb now passes retained inspection: installed bytes/protections
match; current state reports success/0/inactive; one completed encryption-only
60-file/205571-byte report is retained; timer inactive/disabled. The journal
fallback remains diagnostic-only. The next main_resume continuation binds root
journal metadata to the exact runner after publication, independently verifies
ciphertext/HMAC/counts/signed time, rechecks candidate and idle schedule, then
enables/verifies the timer. It does not manually start a backup or replace files.
A persistent timer may perform a scheduled catch-up; keep the pilot idle for
this final step. Actual authenticated continuation/timer success remains pending.

Owner-run df79510b completes retained upgraded-runner binding, independent signed
ciphertext authentication and daily timer enabled/active/next-run verification
for the 60-file/205571-byte pilot profile generation. No repeat of backup/restore
or key custody is required. Future scheduled firing, current database generation,
full-fleet homes and Windows/remote collection remain separate. Source v12 now
requires both encrypted database/profile families with versioned checkpoint
coverage, but it has not been installed or resumed; scheduled v11 is unchanged.
