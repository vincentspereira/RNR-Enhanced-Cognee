# Two-batch Hermes launch qualification

Latest source checkpoint: the restricted text-only service now has a clean
locked dependency audit, matching real BGE vectors and disposable encrypted
recovery evidence. The full legacy lock retains three filelock findings.
See [the source report](../reports/audits/2026-10-19-hermes-security/TEXT-EMBEDDING-SECURITY-2026-10-24.md)
and [the consolidated host continuation](HERMES-SYSTEM-WIDE-LAUNCH-CONTINUATION.md).
Installed renewal/recovery, native completion and real fleet admission remain
open. Do not replay the completed version-4 record. Older checkpoints below
retain their dates and do not override this update.

Prepared 24 October 2026 in Ubuntu-Workspace. This is a continuation of the
restricted pilot, not permission to activate everyday profiles or the fleet.
Use two work batches, with individual checks and retained failure evidence.
Two batches are not a promise that implementation gaps disappear in two calls.

Current security blocker: the restricted FastEmbed dependency caps Pillow below
the patched major version. [The 24 October dependency report](../reports/audits/2026-10-19-hermes-security/DEPENDENCY-LAUNCH-BLOCKER-2026-10-24.md)
records the failed enforced audit, compatible full-runtime update and unresolved
restricted-service gate. Do not force an incompatible install to proceed.

Native follow-up: the owner's first candidate attempt staged the artifact but
stopped in the native-question phase. The original receipt did not identify its
substep. A confirmed helper error expected encryption="enabled"; the actual
schema-3 service reports encryption="AES-256-GCM". The helper now validates that
actual contract, including the qualification tenant and signed project scope.
This repairs the test; it does not establish why the earlier host attempt stopped.
See [the native follow-up report](../reports/audits/2026-10-19-hermes-security/NATIVE-LAUNCH-FOLLOWUP-2026-10-24.md).

Latest native checkpoint: the owner-run read-only check on d275ab5e passed.
The corrected native run then reached question_preservation and stopped. The
native conversation helper closes its provider before returning; both launch
stages now reinitialize that provider under the same scoped binding before
authoritative post-turn reads. The pending question must reload from its
durable journal, and the record and complete queried history must still match.
Six local lifecycle cases exercise the actual provider and conversation helper,
with simulated host/model/transport. They include refusal on damaged current
record, history, pending state and final history. A new installed pass is still
required. Reuse the successful inspection evidence; the next native command is
one `qualify` invocation with the corrected published revision. Retain both
earlier incomplete attempts without replay or deletion.

Latest terminal checkpoint: on 1fa28665 the owner-run native question and
reviewed-sharing phases passed, including post-question record/history checks.
The run stopped at human_answer before receiving an answer. Buffered text r+
cannot open a Linux terminal because it requires seeking. The helper now uses
separate read/write streams, checks terminal availability before issuing keys
or calling a model, and reports fixed input-failure categories without input
content. Real pseudo-terminal tests cover piped-bundle stdin, a visible prompt,
accepted/mismatched/EOF/non-ASCII replies and no controlling terminal. Operator
flow fixtures also test the full question/sharing/human/follow-up sequence.
No typed fixture is counted as real human confirmation. The previous attempt
has no trusted resumable operator receipt identifying its scope, so it cannot
be safely selected for automatic continuation. Preserve it; one corrected fresh
qualification is required to exercise the terminal answer and native follow-up.

Explicit-scope continuation: the next owner output includes test ID
5d0e9a49bdf544359ae6deff in the displayed terminal sentence, paired with native
question/sharing passes and answer_mismatch_or_truncated. The owner confirmed
entering a different or blank answer. That refusal is expected. The newly
available explicit ID permits a narrow continuation without guessing profiles.
Use `resume-answer EXPLICIT_TEST_ID` as the launcher's mode and fourth argument.
Only the identified invented qualification scope is eligible. The helper verifies
the protected candidate, issues fresh ordinary credentials for that exact scope
and its existing peer, and runs a non-root no-model/no-write check of the pending
journal, exact version-2 invented content and complete versions 1-2. Existing
peer read access must still be valid. It creates no profile, memory or share.
No reviewer credential is issued. Root does not traverse the agent profile.

At the displayed `>` prompt, paste the full displayed fictional sentence and
press Enter. Do not paste the `>` symbol, and do not paste the answer into a
normal shell after the command has ended. Only the real typed answer permits
the separate native follow-up process. A wrong/blank answer still stops safely.
The continuation does not replay the question or sharing sequence, and its
receipt explicitly treats earlier question evidence as the separate owner
report, not a newly verified machine receipt. It reports only its current model
request count and follow-up scope. Changed, resolved, missing or ambiguous state
is refused; there is no automatic repair, profile selection or retry.

Post-answer checkpoint: the owner entered the displayed sentence successfully
on 9ee85b05. Existing pending record/history and peer access passed, but the
native follow-up stopped with a broad native_followup condition. The old receipt
does not establish whether zero, one or both mutations reached the service.
Do not replay the answer or assume preservation. Use the explicit mode
`inspect-attempt EXPLICIT_TEST_ID` first. It verifies the candidate and issues
fresh ordinary credentials for the same invented/peer scopes, then inspects only
the private validated journal and canonical history/current row through the
restricted child. Root does not read the agent-owned profile. No OAuth store,
model, human prompt, sharing change or memory mutation is used. API request
accounting can advance; the short-lived ordinary credentials stay in memory.

The observation labels unchanged_pending, corrected_not_retracted,
retracted_with_history or state_needs_review. It reports only verified version
counts, pending/state flags and peer HTTP status, never record content. A
completed inspection is not a completed model qualification and does not prove
the old model failure cause. Changed/nonmatching/ambiguous evidence is refused.
Future follow-up failure receipts now expose only fixed bounded fields: model
request count/status, completion/error/rate-limit flags, called mutation-tool
flags, service-acknowledged correction/retraction, peer withdrawal and the last
fixed checkpoint. Raw error text, answers, prompts and tool arguments remain
excluded. Determine the next action from the read-only installed state instead
of automatically retrying.

Installed state closure: the owner-run f63cdd52 observation returned canonical
version 4, retracted=true, four history versions, pending=false and peer 404
for 5d0e9a49bdf544359ae6deff. These canonical effects passed; preserve them and
do not run resume-answer again on that completed record. The inspection itself
used no OAuth/model/memory write and kept the checked pilot files unchanged.
The earlier overall native-turn failure cause/completion gate remains open.
Further work moves to the separate dependency and operational gates, preserving
this state as evidence. [The current checkpoint](../reports/audits/2026-10-19-hermes-security/CANONICAL-EFFECTS-AND-SECURITY-2026-10-24.md)
also records the compatible source repair reducing full-runtime findings from
17 to 11; the restricted index-lock Pillow findings remain at 37.

## Batch 1: automated source and disposable integration checks

Run with the native Linux test interpreter and the repository-pinned optional
unit dependencies available. Keep credentials out of arguments and reports:

```bash
python scripts/qualification/run_launch_batches.py source \
  --artifacts /var/tmp/cognee-source-qualification-UNIQUE
```

The command runs the complete unit lane, all Hermes/provider/operator helpers,
encrypted collection fixtures and portable Python backup tests. It rejects
every failure, error and skip, retaining private logs and short-path fixtures.
It disables dotenv loading, telemetry and outbound TCP in the unit lane. The
helper lane has real temporary files, age/restic subprocesses and mocked host
boundaries; it is not an installed OS/model test. Separate real PostgreSQL tests
exercise canonical access, history, sharing, key rotation, synthetic fleet
spaces and encrypted dump/disposable restoration. These do not establish
restoration of the current Ubuntu-Hermes database or full-fleet capacity.

The new provider journal retains only bounded private record-ID/turn metadata,
never human messages, confirmation quotes, memory content or credentials. It
preserves pending clarification across sessions/processes and refuses same-turn
confirmation. Unsafe links/permissions, conflicting locks, incomplete metadata
and size overflow fail closed; old entries are not deleted. This is cooperating
provider state, not protection against a malicious process with the same OS
identity and write access to the profile. Server access policy and actual
profile/process separation remain independent requirements.

Original provider/installer sources were preserved under the ignored local
.archive directory before source changes. The candidate installer has a new
immutable artifact name and content hash. Existing installed helpers retain
their original artifact pins. Do not use initial pilot installation/configuration
commands to overwrite or recreate the populated pilot.

## Batch 2: installed acceptance and operational closure

Run in the normal Ubuntu-Hermes operator terminal, not Hermes chat. Use the
published revision recorded in the launch report and the existing source
checkout. Fetch the delivery branch without switching a running checkout.

The pinned scripts/qualification/run_hermes_launch_native.sh accepts
the existing checkout path, full published revision and optional mode
(`qualify`, the default, `inspect`, `resume-answer` or `inspect-attempt`, with an
explicit fourth test-ID argument for the last two). It verifies the seven
public archived sources before any root definitions execute, stages a separate
protected candidate, and uses two non-root native Hermes processes. It requires
the already enrolled secondary pilot model account; no automatic fallback or
account rotation is allowed. A model refusal/429 stops the run. Up to six model
requests per process are allowed, with a 100-second native agent budget each.
No model defaults are changed.

After the incomplete attempt, first use the same pinned launcher with `inspect`.
This verifies the already-staged public candidate without changing it and runs
a restricted read-only check of the existing pilot's service status contract.
It does not load a provider, create a profile, read OAuth credentials, call a
model, sign/renew credentials or write memory records. Existing API request
accounting can still advance. Existing pilot API expiry/HTTP errors stop the
check; report the sanitized result rather than changing credentials blindly.
If inspection passes, use `qualify` once with the corrected revision. It creates
a fresh invented-data scope, retaining the earlier attempt and all its evidence.
Each new failure identifies a fixed public native substage and, when available,
an HTTP status; exception messages, credentials and model output are excluded.

The operator issues one-hour credentials for two new qualification scopes.
The signing key stays in the operator process; the reviewer credential also
stays there. Root never traverses the agent-owned profile. The native child
reads only the existing pilot's selected auth/config/env files through the
reviewed private reader and verifies they are preserved. It creates a fresh
mode-0700 /var/tmp/hermes-launch-<id> profile with public candidate settings and
an approved provider link. Ordinary memory tokens stay in process memory.
This profile is outside the runtime home so its candidate link cannot make
the existing whole-home backup refuse an unknown link. Preserve this private
test directory after the run; its backup/recovery is not qualified.

The consolidated native command checks:

1. Missing, expired and signature-altered credential refusal.
2. One model-driven uncertainty question with unchanged current/history rows.
3. Cross-scope denial, reviewer-only sharing, reviewed read, revocation and
   reviewer mutation denial using real API responses and separate credentials.
4. A complete native process restart, with pending clarification still blocking
   an unconfirmed edit.
5. A real terminal answer to the synthetic question, followed by a model-driven
   version-checked correction and requested retraction of that exact record.
6. Withdrawal from the peer view on correction and preservation of versions
   1-4 after retraction, with no active records left in the new test scope.
7. Byte preservation of the original pilot settings, auth and environment.

The terminal asks the operator to type one displayed invented-data answer.
Do not replace that interaction with a generated answer or mark a scripted
fixture as genuine human clarification. The native tests exercise the candidate
in a separate installed profile; they do not switch the existing pilot, bots
or main assistant. Root/public candidate files and private test history remain
preserved on failure; no automatic retry, rollback or deletion occurs.

The native command is one part of batch 2. Its receipt explicitly keeps these
remaining requirements open:

- Installed interrupted-renewal recovery and an operator-owned unattended
  renewal path. The manual renewal pass remains valid for its original scope.
- Current canonical database generation, independent verification/disposable
  restore, required current index replay and relevant recovery checks. Preserve
  prior manual profile restore, key custody and daily-timer passes.
- Real Windows dual-family collection, actual v12 completion and required remote
  recovery. The owner's new native Windows result is 62 passed, zero failures
  and skips, with source/installed hash matches. It closes synthetic native
  Windows qualification; it is not a real backup, upload or task switch.
- Inventory and admission of actual main/bot profiles, their real launch
  identities and peer-secret/admin-socket boundaries. Two signed test scopes
  and the old synthetic 42-space workload are not full-fleet admission.
- Exact candidate runtime/dependency/release checks and remaining private
  exposed-credential disposition. Frontend release findings remain separately
  tracked; do not label them failed Hermes conversations or suppress them.

Continue these independent host checks in the same operator qualification
window where safe. Reuse unchanged exact-scope evidence and batch per-profile
checks; do not repeat completed custody/restoration/model stages by default.
If code or operational mechanisms are missing, implement and qualify them
before claiming that batch 2 or the launch is complete.

After both batches and the actual profile gates pass, record the admitted
revision, scope/credential mapping and disable/recovery path before staged
activation. Do not make a global provider switch on the strength of a source
test count or this document.
