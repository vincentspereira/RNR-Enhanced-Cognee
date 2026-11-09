# Candidate service-user check passed - cutover decision

Date: 2026-11-01. Ubuntu-Hermes only. Proposal, not activation instructions.

## Verified completed check

The owner ran the reviewed diagnostic as enhanced-cognee-api and supplied:
complete=true, uid=63764, modules_imported=8, correct_module_paths=true,
source_writable=false, api_started=false, credentials_passed=false. The candidate
prefix was /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime.
Independent read-only account lookup confirms that UID belongs to the API user.
The successful service-user execution is owner-provided evidence, not a claim
that the assistant independently reran it under that account.

This closes candidate import/path/read-only permission acceptance. It does not
prove full service startup, credential loading, data-plane behaviour, physical
OS isolation or backup recovery. No diagnostic needs rerunning just for a badge.

The live API unit remains active on the old 21abf4857ca8dce8e0a3aafc725266c8d3754529
candidate. StateDirectory is still unset. DynamicUser=yes: its numeric account ID
is managed temporarily by systemd, not a fixed UID to hard-code into ownership
commands. Persistent state must be provisioned through the manager and checked
inside the actual service namespace, including the ledger's strict path/symlink
rules. Current StateDirectoryMode is only the unused default 0755, not proof of
a private ledger; the proposed state must be private. No activation or restart
was performed.

## Recommendation: prepare a security-first phased cutover

Prepare and independently review an owner-run package which switches ordinary
memory service to the fixed candidate, but initially withholds the OPTIONAL
backend model-analysis route. Keep ordinary remember/recall/correction and the
main assistant's own chat model separate from those backend analysis endpoints.

Reason: a new empty budget ledger would otherwise forget any usage already
charged by the old process's in-memory counter during the current UTC day.
That reset must not silently create extra model allowance. Suppressing backend
model calls until accounting and recovery are proven avoids additional spend
while allowing core security fixes to be deployed sooner.

Withholding this optional route is a proposal, not an action already approved
or applied. It would temporarily make backend summarisation/consolidation/
translation unavailable. Do not confuse this with disabling all memory or the
main assistant's own configured model. Verify the exact selected credential
names/unit wiring before preparing any unit override; systemctl's generic
LoadCredential display was opaque, not evidence of the full credential layout.
Do not edit, print, rotate, copy or remove the root-only LLM key file.

## Required package and owner gates

1. Preserve old runtime, selected unit/drop-in bytes, source identities and MCP
   script with rollback evidence. Do not copy credentials into source reports.
2. Prepare the smallest exact API override: new runtime/working directory,
   service-private persistent state, and a reviewed optional-analysis gate.
   Preserve the ordinary API credential and all unrelated hardening. Match the
   MCP server contract to the reviewed API changes; do not blindly change other
   profile settings or restart the whole gateway/fleet.
3. Obtain owner approval for the exact change and a brief API interruption.
   Source preparation approval is not a live restart approval. No activation
   command is supplied until the operator helper and rollback are reviewed.
4. Run only targeted installed checks agreed for the change; do not repeat the
   completed historical native/memory qualification suite, rotate credential
   families, activate bots or run unfiltered model operations.
5. Provision and verify the persistent budget ledger under the API identity,
   and its consistent encrypted backup/restore. Until those gates pass, keep
   optional backend model calls unavailable rather than pretending they are
   accounted for. An empty directory or successful module import is not proof.
6. Define usage cutover explicitly. If prior usage cannot be transferred safely,
   do not admit model calls during the partially accounted UTC day. Enabling at
   a later clean UTC-day boundary is an option only if no unaccounted model calls
   occurred in that day. No arbitrary allowance reset is acceptable.
7. Read back live command, state protections, source hashes and targeted results.
   Emergency rollback must not discard the ledger or claim reverting binaries
   reverses spend; old code has known security defects and is not the default
   long-term fallback.

## Alternative

Keep the existing API unchanged until full accounting handover and recovery are
ready, then do one full cutover. Advantage: avoids temporary loss of the optional
analysis endpoints. Disadvantage: leaves the old backend security findings live
for longer. Neither option permits a blind restart or claiming full readiness
from the staged/imported candidate.

## Unchanged parallel work

The 40-role execution-tool proposal and four-specialist tool review remain saved
in Projects/Hermes-Bot-Fleet/docs/. No role tool settings were modified and no
fleet execution was started. They do not replace this backend workstream.
