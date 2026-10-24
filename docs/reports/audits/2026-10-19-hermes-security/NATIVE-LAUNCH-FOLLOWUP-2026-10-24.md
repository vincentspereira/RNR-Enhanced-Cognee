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
