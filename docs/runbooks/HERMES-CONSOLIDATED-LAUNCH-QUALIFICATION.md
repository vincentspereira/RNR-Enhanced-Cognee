# Two-batch Hermes launch qualification

Prepared 24 October 2026 in Ubuntu-Workspace. This is a continuation of the
restricted pilot, not permission to activate everyday profiles or the fleet.
Use two work batches, with individual checks and retained failure evidence.
Two batches are not a promise that implementation gaps disappear in two calls.

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

The pinned scripts/qualification/run_hermes_launch_native.sh accepts exactly
the existing checkout path and full published revision. It verifies the seven
public archived sources before any root definitions execute, stages a separate
protected candidate, and uses two non-root native Hermes processes. It requires
the already enrolled secondary pilot model account; no automatic fallback or
account rotation is allowed. A model refusal/429 stops the run. Up to six model
requests per process are allowed, with a 100-second native agent budget each.
No model defaults are changed.

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
