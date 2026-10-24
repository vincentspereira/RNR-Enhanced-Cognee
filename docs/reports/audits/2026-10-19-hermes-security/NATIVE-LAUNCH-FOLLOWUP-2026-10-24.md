# Native launch qualification follow-up - 24 October 2026

The owner's Ubuntu-Hermes result from published revision
2b2d5bc897d63a1bd83299954d01264c8c0d5fec reports complete=false,
candidate_staged=true and failure_stage=native_question. Native question,
reviewed sharing, human answer and native follow-up flags are false. Fleet
launch remains unapproved. That receipt identifies a phase, not its failed
subcheck; it does not prove that a model was contacted or a fixture was written.

Workspace source inspection found a deterministic qualification-helper error.
It expected encryption="enabled" from GET /v1/memories/status. The canonical
MemoryService.status implementation and the reviewed original pilot admission
both use encryption="AES-256-GCM". The helper now accepts that actual contract
while enforcing the qualification tenant, expected signed project, ready=true
and integer schema version 3. The service and its encryption were not changed.
An earlier credential, import or discovery error could still have stopped the
owner's attempt before this assertion. No exact native cause is claimed yet.

A regression obtains the status response directly from the real service method,
with a minimal disposable database-interface fixture, and passes it to the launch
validator. It does not duplicate a status dictionary as its only positive test.
Negative cases reject the wrong cipher, tenant, project, readiness and version
type. Fixed-stage diagnostics now distinguish restricted identity, pilot files,
secondary credentials, candidate profile/discovery/initialization, authenticated
status, fixture creation, native clarification, preservation, restart admission,
native follow-up and final history. Parent receipts reject unexpected/private
fields, phases, categories and HTTP status types. Raw exception messages, OAuth
data, memory content, prompts and model output are never serialized.

The launcher also accepts an explicit inspect mode. Root verifies the existing
candidate's protected public files without staging or reading an agent profile.
The restricted child reads the old pilot's reviewed configuration and API token,
verifies its original provider admission, makes one authenticated status GET,
and checks those files remain identical. It does not load a provider, create a
profile, read the OAuth store, call a model, sign/renew credentials or write memory
records. Server request accounting can advance. The check reports sanitized
HTTP failure status when available. It cannot qualify model behavior or prove
the exact failure point of the original attempt.

After inspection passes, one corrected native qualification uses a fresh scope
and profile. No earlier attempt is replayed, deleted, reset or repaired. Public
provider bytes and their immutable artifact name are unchanged by this helper
repair. The original helper and launcher were preserved under the ignored
.archive/2026-10-24_launch_native_diagnostics directory before editing.

Workspace verification: 1253 Hermes/operator/encrypted-collection/portable-backup
regressions passed, with zero failures, errors, skips or reported pytest warnings.
This includes 50 launch-harness tests. The redacted public-diff secret scan found
zero leaks. Python syntax, ASCII and shell syntax checks passed. Coverage was
not measured. Sanitized counts and source hashes are recorded in
remediation-evidence/2026-10-24-native-launch-followup.json; private logs and
fixtures remain in /tmp/ec-native-launch-fix-20261024 and /tmp/ecq-afghceia.
No Ubuntu-Hermes execution occurred from Workspace. The dependency audit blocker,
unattended renewal, current database recovery and actual fleet admission remain
separate open requirements. Passing this corrected test cannot by itself approve
system-wide activation.

## Second owner result and provider lifecycle correction

On d275ab5e0309bde2bef13a7a76d2c8e94808397d, the owner's read-only installed
diagnostic passed the authenticated status contract, candidate artifact and
checked-pilot preservation. It reports no model call, memory write or OAuth
store read. The subsequent native run stopped at question_preservation, with
the native clarification routine having returned. Sharing, human-answer and
native follow-up acceptance remain false. Record/history preservation is not
inferred from reaching this stage.

Source review found a second deterministic harness defect. The actual
native_memory_turn calls agent.close in its finally block, which shuts down the
provider and clears its client. The launch child then dereferenced that closed
client to check the record/history. Its answer stage had the same defect. The
original reviewed main_memory checker already reinitializes before these reads.
Both candidate stages now do likewise, retaining the same active secret scope,
profile and settings. The question verification additionally requires the exact
pending record to reload from the real durable journal. Separate fixed substages
identify reinitialization, pending-state, current-record and history checks.
The provider, service, credentials and immutable candidate artifact are unchanged.

A local full-child regression reproduces AttributeError on the unfixed code at
the post-question client read. After correction it runs both stages with the
actual provider, filesystem journal, reviewed native conversation helper and
follow-up transport guard. The host, model and canonical HTTP transport are
simulated. A fresh provider loads the question's pending state, rejects an
unconfirmed correction, accepts the later synthetic human fixture, performs
version-checked correction/retraction, and reloads state after both closures.
Negative cases reject a missing question mark, changed current record, changed
history, lost pending state and invalid final version history. The local fixture
is not installed evidence or a replacement for the real terminal human answer.

The owner's receipt does not expose the original low-level exception. The local
closed-client failure is confirmed and consistent with the reported stage; an
earlier question-format failure in that same stage cannot be ruled out from
the receipt alone. Do not claim a proven host exception or preserved rows yet.
The original helper and launcher are retained under the ignored
.archive/2026-10-24_launch_provider_lifecycle directory. The successful native
inspection need not repeat. One new corrected native qualification should use
a fresh fictional scope and retain all prior attempts.

Final lifecycle follow-up validation: 1259 Hermes/operator/encrypted-collection/
portable-backup checks passed, zero failures/errors/skips and no reported pytest
warnings. This includes 50 existing harness checks and six new full-child cases.
Private final logs and fixtures are at /tmp/ec-native-lifecycle-fix-final-20261024
and /tmp/ecq-1wqyqkq8. Earlier fixture failures remain at
/tmp/ec-native-lifecycle-fix-20261024; those test-only issues required a writable
journal descriptor for the deliberate mutation and restoration of the process
umask after each simulated child. Production admission rules were not relaxed.
Sanitized source hashes/counts are in
remediation-evidence/2026-10-24-native-provider-lifecycle.json. Required CI on the
earlier d275ab5e passed; Security Audit, memory-qualification, full-runtime and
other legacy jobs still failed. No all-green release result is claimed.

## Third owner result and terminal input correction

On 1fa286652d53420b28b0f4f245a89666fe61e1fa, the owner-relayed result reaches
failure_stage=human_answer, with native_question_passed=true and
reviewed_sharing_passed=true. Candidate admission, negative credentials, native
clarification, unchanged current/history rows, restored pending state and the
scoped sharing/revocation checks preceding this stage passed. Human-answer
receipt and native follow-up are false; no follow-up acceptance is claimed.

The helper attempted open('/dev/tty', 'r+', buffering=1) before displaying its
prompt. A real local Linux pseudo-terminal reproduces UnsupportedOperation:
File or stream is not seekable. Buffered text update mode requires seeking;
the terminal cannot provide it. The receipt itself does not disclose that
low-level exception, but this confirmed defect is consistent with the stage.
Separate read and write streams now handle terminal I/O and flush the prompt.
A terminal preflight runs before protected issuer definitions, candidate
staging, credential creation or model execution. Absent terminals stop early.
Rejected/EOF/encoding input reports fixed categories without serializing the
reply. The script still requires the actual operator to supply the displayed
invented-data answer; no automatic answer is supplied.

Ten new regressions cover real controlling-terminal I/O with piped bundle stdin,
acceptance and three refusal cases, missing-terminal refusal before issuer
loading, and complete operator-flow/failure-order fixtures. Model, canonical
store and human input in these tests are simulated. No local test is promoted
to installed human/model acceptance. The sharing-progress flag is now set only
after every sharing/revocation/resharing check completes, so an intermediate
failure cannot mark that whole phase passed.

The previous operator kept its run identifier/ordinary tokens only in memory
and emitted no trusted resume checkpoint. Agent-owned pending journals do not
prove which attempt reached the operator's sharing checks. No profile is chosen
by guessed timestamps or a same-user claim. Earlier attempts, profiles and
histories remain intact; one new corrected qualification must gather the real
answer and follow-up. The original helper and launcher were preserved under
the ignored .archive/2026-10-24_launch_terminal_input directory. The provider,
service, immutable artifact, existing pilot and model defaults are unchanged.

Final terminal follow-up validation: 1269 Hermes/operator/encrypted-collection/
portable-backup tests passed, zero failures/errors/skips and no reported pytest
warnings. This includes ten new terminal/operator cases. Python/embedded-source,
shell syntax and ASCII checks passed; the redacted staged-diff secret scan
found zero leaks. Coverage was not measured. Private logs/fixtures remain at
/tmp/ec-native-terminal-fix-20261024 and /tmp/ecq-ofu5gu7v. Sanitized counts and
source hashes are in remediation-evidence/2026-10-24-native-terminal-input.json.
No native follow-up or whole-fleet pass is inferred from these local results.

## Explicit identified attempt and remaining human answer

The owner's next 9917f620 output includes the actual terminal prompt for test
5d0e9a49bdf544359ae6deff, native_question_passed=true,
reviewed_sharing_passed=true, human_answer_received=false and
human_answer_failure=answer_mismatch_or_truncated. The owner confirmed entering
a different or blank answer and asked how to respond. Explain the interaction
plainly: while the command waits at `>`, paste the full displayed sentence and
press Enter. Never supply an answer automatically or treat this explanation as
the actual terminal confirmation. No follow-up conversation was accepted yet.

The explicit test ID changes the earlier continuation limitation: a prior JSON
without its ID could not safely identify the profile. The paired terminal output
now supplies that ID directly from the owner. A new resume-answer mode requires
that explicit 24-character lowercase hex value, verifies the existing protected
artifact without staging it, and signs only two ordinary short-lived credentials
for launch_<ID> and peer_<ID>. No reviewer token, profile creation, fixture write
or sharing change occurs. Operator keys stay in root; agent-owned files are read
only by the restricted child. No private token, settings or raw answer is logged.

The read-only child avoids the OAuth store and verifies the original pilot's
checked files, candidate binding and signed qualification status. Exactly one
pending record and one active record must exist. Its canonical subject, project,
state, version and exact invented content must match. Full returned history must
contain only expected versions 1 and 2 for that same record and invented scope,
with no truncated/paginated remainder. The current peer grant must still return
that version. The checks do not replay the earlier model or establish the old
question/sharing receipt independently; the continuation output says so.

The real terminal answer is then passed, unchanged, to a separate native answer
process using the original provider gate and versioned correction/retraction
guard. Model requests, current history and withdrawal from the peer are verified
as before. Output labels the new result as resumed human follow-up, with the
prior owner report kept separate and no whole-fleet approval. Changed/resolved
records or absent/ambiguous state stop instead of guessing or reconstructing.
Existing incomplete attempts remain untouched except for the specifically
requested, human-confirmed correction/retraction if this follow-up succeeds.

Workspace tests exercise the actual provider/journal/read-only continuation
between the question and answer stages, including unchanged journal bytes and
no OAuth selection during the check. Dedicated negative fixtures reject wrong
subjects/projects/content/states/version types, missing/multiple pending records,
incomplete/altered history and invalid IDs. Operator-flow fixtures enforce peer
access and the live-answer boundary, issue only ordinary roles, and reject
unexpected receipt fields. A real pseudo-terminal fixture exercises the resumed
prompt; synthetic typed input remains local test evidence only. Originals were
preserved under .archive/2026-10-24_launch_answer_continuation before edits.

Final continuation validation: 1300 Hermes/operator/encrypted-collection/
portable-backup tests passed, zero failures/errors/skips and no reported pytest
warnings. This includes 30 dedicated admission cases and one added resumed
pseudo-terminal case; the existing real-provider lifecycle cases also exercise
the read-only continuation. Syntax/ASCII/shell checks pass. The redacted staged
diff secret scan found zero leaks. Coverage was not measured. Private artifacts
remain at /tmp/ec-native-answer-resume-20261024 and /tmp/ecq-aik605l6. Sanitized
counts/source hashes are in remediation-evidence/2026-10-24-native-answer-continuation.json.
A real installed human answer/native follow-up remains pending.

## Human answer received; current mutation state not yet known

The owner's next 9ee85b05 continuation shows the exact displayed answer entered
for 5d0e9a49bdf544359ae6deff. pending_original_fixture_verified and
existing_peer_access_verified passed. human_answer_received=true. The command
then stopped at native_followup_after_process_restart/native_followup, with
condition_or_native_error and no HTTP status. This establishes that the actual
human-answer gate passed and the restarted provider's unconfirmed-edit check
returned an error as required. It does not prove that the model sent no writes,
that both requested writes completed, or that current state remained unchanged.
No automatic answer replay or fresh test scope is warranted from that receipt.

The follow-up helper's broad result assertion combined model completion,
request-budget/rate-limit handling and observed correction/retraction. It now
retains only bounded fixed evidence on failure: initialization/admission/
conversation/guard checkpoints, model request count and last HTTP status,
completion/error/rate-limit booleans, called correction/retraction flags,
service-acknowledged mutation flags and peer-withdrawal acknowledgement. Root
revalidates the entire diagnostic shape before adding it to a failure receipt.
No exception messages, model output, arguments, record content or confirmation
quotes are serialized. These fields help future failures; they cannot recover
the lost details of the owner's preceding model run.

The pinned public Hermes [_init_memory implementation](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/agent_init.py)
reuses an injected already-initialized memory manager. This does not support a
constructor-reinitialization explanation for this failure. No source fix to
the model/provider behavior is claimed without installed evidence.

The next installed action is the new inspect-attempt mode with that explicit
test ID. It verifies the existing public artifact without staging, issues only
two ordinary short-lived tokens and runs a restricted read-only child. No OAuth
store, model, human prompt or memory/sharing mutation is used. The actual
validated private journal is locked and read through its read-only descriptor;
exactly one record ID must have appeared. Bounded canonical history must have
consecutive integer versions 1 through 2, 3 or 4, the exact original invented
versions 1-2 and the guarded five-day correction if present. Retraction must
preserve the corrected content. Current state/active count are checked, and an
active current row must agree with history. A retracted row is inspected through
owner history, because ordinary current GET hides retracted records by design.

The observation returns only version/count/state/pending flags and current peer
HTTP status. Its complete flag means the inspection completed. It explicitly
keeps model_failure_cause_established, native_followup_qualified, automatic_retry
and fleet_launch_approved false. Changed or inconsistent synthetic evidence is
refused without repair. The safe next action depends on whether the installed
record is still pending, only corrected, or already retracted; do not repeat the
previous resume command until that state is known. API request accounting can
advance; scoped credentials remain in memory and the operator key stays in root.

Local real-journal/fake-transport cases cover all three canonical versions with
both pending-state possibilities, refusal of altered/paginated/inconsistent
history and current state, strict root receipt shapes and ordinary-only
observation orchestration. The provider and service were not changed. Original
helper/launcher copies remain under .archive/2026-10-24_launch_followup_observation.

Final observation validation: 1330 Hermes/operator/encrypted-collection/portable
backup tests passed, zero failures/errors/skips and no reported pytest warnings.
This includes 30 new observation/diagnostic cases. Syntax/ASCII and shell checks
pass; the redacted staged-diff secret scan found zero leaks. Coverage was not
measured. Private final logs/fixtures remain at
/tmp/ec-native-followup-observation-final-20261024 and /tmp/ecq-84q8blgt. Earlier
passing evidence is retained at /tmp/ec-native-followup-observation-20261024.
Sanitized counts/source hashes are recorded in
remediation-evidence/2026-10-24-native-followup-observation.json. The next
installed read-only observation and the native follow-up qualification remain
pending; the original failure cause is not established.
