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
