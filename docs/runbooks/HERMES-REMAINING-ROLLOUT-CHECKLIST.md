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

The owner then returned complete=false/native_agent_turn with category
ambiguous_change_not_preserved_for_clarification at helper revision
ef39013eab7aba9df2c1413e39f53943ddaaa0f8. Checked settings/credentials were
unchanged and memory_writes_may_have_occurred=false. That report does not say
which condition failed: missing clarification, no preceding read, an editing
tool attempt, a blocked write or unexpected pending state. It did not complete
the post-turn canonical/receipt comparison. Keep this gate failed/pending.

Subsequent owner-run diagnostics at 5b2538ad verified post-turn preservation,
correct pending target, a completed native turn/question, no editing tool and
zero write attempts. Only the explicit-read-tool predicate failed. Pinned native
Hermes also recalls automatically before tools. The updated qualification helper
requires actual matching current-record retrieval and successful model-request
delivery before accepting this alternative, preserving all other guards. The
historical report alone does not establish delivery; one confirmation remains.

## How much remains

There are five shared readiness groups, followed by the actual fleet rollout.
These are six work groups, not six tests or a promise of six commands. Some
mechanisms still need implementation, and a failed installed check may need a
repair and a bounded repeat. Unit-test counts measure source checks; they are
not a countdown to deployment. Group independent checks into safe operator runs
when they use the same trust boundary; do not ask the owner to replay passes.

| Group | Required result | Current status |
|---|---|---|
| 1. Conversation safeguards | Uncertainty asks a question without editing; a later genuine human answer permits only the confirmed change; sensitive details/credentials are rejected; correction/retraction retain appropriate history without claiming sensitive history was erased | Capture/clear correction/corrected recall pass; ambiguity just failed, other current-runtime privacy/follow-up evidence remains open |
| 2. Access and reviewed sharing | The intended runtime cannot reach privileged/peer secrets; private spaces deny other callers; only approved shared summaries are visible and revocation/current-version rules hold | Selected runtime denial and earlier synthetic multi-space tests exist; actual peer/fleet boundaries and installed sharing need reconciliation |
| 3. Credential operation | Protected fixed-scope renewal, expiry/refusal controls, safe atomic publication and interrupted-renewal recovery work without giving agents signing authority | Current 24-hour credential works at last check; renewal mechanism/qualification remains open |
| 4. Recoverable state | Explicit encrypted restricted-profile/workspace/receipt coverage, consistent database generation and disposable restoration prove recovery without overwriting live state | Owner key-package custody passed; earlier service restore exists; later /var/lib/hermes-runtime coverage and current recovery evidence remain open |
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
