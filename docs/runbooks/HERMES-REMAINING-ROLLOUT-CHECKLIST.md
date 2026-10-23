# Remaining Hermes memory rollout work

Reviewed in Workspace on 23 October 2026 against repository source and the
owner-relayed installed results. This is not direct access to Ubuntu-Hermes.

## What is already working

The protected backend and restricted pilot are installed. Owner-run native
evidence establishes selected capture, fresh-session recall, clear versioned
correction and fresh-session recall of the corrected version. The second pilot
OpenAI account is independently enrolled, and the local API accepted the ordinary
memory credential at its last check. Settings/defaults and prior evidence were
preserved. These completed gates do not need replaying to reconstruct evidence.

Historical uncertainty diagnostic (superseded by the passes below): the owner
returned complete=false/native_agent_turn with category
ambiguous_change_not_preserved_for_clarification at helper revision
ef39013eab7aba9df2c1413e39f53943ddaaa0f8. Checked settings/credentials were
unchanged and memory_writes_may_have_occurred=false. That report does not say
which condition failed: missing clarification, no preceding read, an editing
tool attempt, a blocked write or unexpected pending state. It did not complete
the post-turn canonical/receipt comparison. That run remained failed/pending
until the later, verified native-prefetch pass.

Subsequent owner-run diagnostics at 5b2538ad verified post-turn preservation,
correct pending target, a completed native turn/question, no editing tool and
zero write attempts. Only the explicit-read-tool predicate failed. Pinned native
Hermes also recalls automatically before tools. The updated qualification helper
requires actual matching current-record retrieval and successful model-request
delivery before accepting this alternative, preserving all other guards. The
historical report alone did not establish delivery; the later 0768a43e pass
established it for the single-turn uncertainty case.

## How much remains

There are five shared readiness groups, followed by the actual fleet rollout.
These are six work groups, not six tests or a promise of six commands. Some
mechanisms still need implementation, and a failed installed check may need a
repair and a bounded repeat. Unit-test counts measure source checks; they are
not a countdown to deployment. Group independent checks into safe operator runs
when they use the same trust boundary; do not ask the owner to replay passes.

| Group | Required result | Current status |
|---|---|---|
| 1. Conversation safeguards | Uncertainty asks a question without editing; a later genuine human answer permits only the confirmed change; sensitive details/credentials are rejected; correction/retraction retain appropriate history without claiming sensitive history was erased | Capture/clear correction/corrected recall, single-turn uncertainty, all eleven local API privacy cases and one real native sensitive-input turn pass; later human follow-up/retraction/history work remains open |
| 2. Access and reviewed sharing | The intended runtime cannot reach privileged/peer secrets; private spaces deny other callers; only approved shared summaries are visible and revocation/current-version rules hold | Selected runtime denial and earlier synthetic multi-space tests exist; actual peer/fleet boundaries and installed sharing need reconciliation |
| 3. Credential operation | Protected fixed-scope renewal, expiry/refusal controls, safe atomic publication and interrupted-renewal recovery work without giving agents signing authority | Owner-run manual pilot renewal and API refusal controls pass; installed interruption recovery and unattended/fleet lifecycle remain open |
| 4. Recoverable state | Explicit encrypted restricted-profile/workspace/receipt coverage, consistent database generation and disposable restoration prove recovery without overwriting live state | Owner key-package custody, inventory and manual encrypted profile restore pass (ca2682c6, 60 files/205571 bytes); daily profile job files installed but first run failed at d7c7880c; timer enable did not complete; retained inspection confirms restricted snapshot launch failure; temporary launch probe, recurring operation, collector coverage and current service generation remain open |
| 5. Runtime and release checks | Relevant backend/provider dependencies and required checks pass, failures/unready indexes are reported honestly, and deployed artifacts match the admitted source | Known dependency/release issues and final candidate checks remain; a unit pass alone does not close these |
| 6. Fleet inventory and staged admission | Enumerate actual main/bot/other profiles, map distinct scopes/credentials and real launch identities, back up configurations, then qualify batches with own-scope/other-scope/shared checks and a preserved disable/recovery path | Everyday main/bot profiles remain unchanged; no whole-fleet activation claimed |

Group 5's relevant runtime/backend checks must be distinguished from the full
repository release: separate frontend issues remain tracked for release/main
merge, not relabeled as failed Hermes conversations. Reuse older finite evidence
only where its exact code, identity and scope still apply. Do not repeat distro
restarts, installation, cloud-vault recovery or all prior model tests routinely.

Group 6 must inventory the actual count and launch mechanisms; the earlier
41-bots-plus-controller example is not an installed inventory. Per-profile
checks can run in batches. Shared component evidence can be reused after
verifying the same protected artifact and behavior, while each profile's actual
credential/scope and launch boundary still need admission. One maintained
backend remains the design; there is no need for one backend per bot.

Private credential-review coverage remains a separate owner checkpoint. Preserve
the already completed KeePassXC/key-package recovery evidence; do not restart
that process or claim unknown historical credentials were revoked.

## Immediate next step

Latest owner-run update: clarify_followup passed at
0768a43e0d3e429327b23e108ab5ad4eafe56e30. Verified native prefetch delivery
preceded enhanced_clarify; the record/history/receipts/profile were preserved,
with no edit/write attempt. This closes the single-turn uncertainty gate and
supersedes the diagnostic retry below. It does not qualify a later human answer
or pending-state durability. The owner subsequently returned all eleven API
privacy cases passed at 37cc5d9bd8a25b233fca7f0754d33f035d40269b, with expected
422/409 refusals, unchanged canonical/history/receipts/profile, no OAuth store
read, no chat-model call and no memory write. Preserve both passes.

Owner-run native privacy also passed at
79264eebd2a3a5d99822b45580f496a56b6bc2b1: one GPT-6.1-Sol request using the
explicit secondary account, no tool/edit/write attempt, no full sensitive canary
in the reply and unchanged canonical/history/receipts/settings/credentials.
This is one finite synthetic case; do not replay it or infer universal detection.

Owner-run manual credential renewal passed at
8fb6fca95cf5480830d748134da93b785645820a. New expiry is
2026-10-24T09:15:06+00:00; API acceptance, refusal controls, retained previous
environment and unchanged settings/OAuth passed without a model or memory write.
interrupted_attempts_reconciled=0 does not establish installed crash recovery.

Owner-run recovery inventory passed at
61c272a767f1383acccd9760d782da8c8e127752: 60 files/205571 bytes, no detected
database/sidecar or problematic entries, all required private files/receipts
and protected provider/tool flags passed. No source data was copied then.

Owner-run manual profile recovery now passes at
ca2682c6af3d0c40855e795a1dca9c778629184e: signed ciphertext/decryption,
60 recovered files/205571 bytes, private permissions/provider binding/scoped API
access, with live source and the failed destination preserved. No repeat of
that restore is needed. Owner-run d7c7880c installed the separate daily job
files, but its first run exited 1 and timer enable did not complete. Owner-run 3bd4bf8f verified public artifacts/protections and found the retained
restricted_snapshot failure with no backup created. Owner-run 058b71da then observed PermissionError/errno 1 before a child
result. Next qualify the scheduled external identity-launch candidate with the
updated transient probe before any installed service replacement.
It performs encryption-only snapshots with no model/API, memory write or
recovery-identity read. Keep the pilot idle for its first run. See
HERMES-PILOT-RECOVERY.md. Windows collection, current canonical database
recovery and fresh-machine program rebuild remain separate; no fleet activation.

Latest owner-run 56c0d439: the temporary launcher returned 127 at setresuid;
the root parent has effective CAP_SETGID but lacks CAP_SETUID. No snapshot or
backup completed and installed files/timer remain untouched. The next candidate
retains CAP_SETUID in the root service's ambient set, with the same bounding
set, then explicitly clears ambient/inheritable capabilities for the non-root
reader. Other selected restrictions and the reader's zero-effective/ambient
guard remain. Qualify this finite RAM-only snapshot first. Then prepare the
guarded update of exact known installed artifacts, run an actual encrypted
backup successfully and verify the timer. Do not repeat the initial installer.

### Historical clarification diagnostic, superseded by the passes above

The clarification helper now returns only bounded diagnostic flags/counts and
known tool names for a completed turn missing a clarification condition. No
record IDs, prompts, replies, arguments or credentials are printed. If that
completed turn fails the behavior check, authoritative post-turn reads still
compare canonical content/history, counts, receipts and checked profile state
before reporting whether preservation verified. A failed comparison never
becomes a preservation pass. The original behavior and write guard stay enforced.

One deliberate new run of clarify_followup is needed to confirm matching native
automatic-recall delivery before clarification, which earlier diagnostics did
not observe. This is not a repeat of capture, correction or corrected recall.
Use the explicit secondary account, existing scopes/receipts and the new pinned
hash-verified helper. It may consume existing subscription quota. Stop on an
observed 429; do not rotate accounts automatically or reset statuses.

This single-turn diagnostic does not establish durable clarification across
restarts or a later human-answer turn. Fix the observed condition first, then
complete the remaining group 1 cases and the other groups above.

Latest backup update, 23 October: owner-run 47b20e4d passes the corrected
restricted snapshot (exit 0, snapshot discarded in RAM, no installed change).
Do not repeat it. The next step is the pinned exact-artifact guarded upgrade:
preserve old runner/units, publish the reviewed protected runner and corrected
service, verify one actual signed encrypted backup and then enable/verify the
daily timer. This step is prepared, not owner-run complete. Failed/partial
updates preserve evidence and require review before any retry. Other readiness
and fleet gates above remain open.

Latest owner update at ab8c990b: corrected service replacement succeeded and
originals were preserved. The combined real backup qualification stage failed;
no timer-enable command completed. Do not infer which subcheck failed or whether
ciphertext exists. Next inspect the exact upgraded runner/service and retained
invocation read-only; preserve old/new artifacts, manual recovery and passing
snapshot evidence. Do not rerun the updater. Installed encrypted-job/timer and
all separate collection/release/fleet gates remain pending.
