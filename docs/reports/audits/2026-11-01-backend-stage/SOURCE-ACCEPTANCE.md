# Backend staging preparation - source accepted, host staging pending

Date: 2026-11-01. Ubuntu-Hermes only.
Branch: codex/enhanced-cognee-backend-stage-20261101
Application payload source: c14f595ccd53f432b455b16f116765d9aa6c9a14.

## Recommendation and next owner action

Use the reviewed STAGE-COMMANDS.md in this directory to prepare the protected
input bundle and then create the separate candidate. This is staging only, not
API activation. Leave the current API and restored renewal timer running.

The conditional 'awaiting independent acceptance' warnings retained in the
reviewed preparation documents are now satisfied by the attached exact-hash
source review. They have not been edited after acceptance. Those warnings still
correctly prohibit substituting a different helper or unreviewed command block.

## Verified source acceptance

- Parent and independent reviewer each ran the selected 58-case offline suite:
  no failures, errors, skips or observed warnings.
- Independent review passed 60 additional distinct offline challenge cases.
- The exact seven-file manifest is review-manifest-v1.json, SHA-256:
  ef823819c3273526a94e69853e0109068e4ec483b18e99ea0dd0d940dec6e033.
- Eight application payload hashes match the previously accepted c14 Git blobs.
- Ordinary-user read-only inspection of the fixed old runtime passed: 7,235
  entries, inventory digest
  55897401aad689f945b96d0e9e56b17ee2165eb9567d2cce84347f0ac32b2926.
- Parent rechecked current source bindings, review archive SHA-256/CRC, all 47
  indexed payload members and the byte-identical self-index member (48 members
  total). Evidence is in independent-review-v1/ and parent-acceptance.json.
- Original reviewer-fixture failures and their corrected replay mapping remain
  preserved. They are not counted twice or hidden as original successful runs.
- The initial parent archive check assumed the self-index was in its own payload
  list. The corrected check explicitly verifies the documented excluded index
  against its separate digest and the archive bytes; no member was skipped.

## Precise boundaries

The helper and owner-command source are accepted under the documented exclusive
owner-operation assumptions. No root bootstrap, protected staging, restart,
service change, provider call, credential action, ledger creation or fleet run
was performed during preparation/review. Synthetic root metadata is not proof
of physical privilege isolation, a full copied-runtime boot or power-loss safety.

The fixed old runtime remains untouched. The candidate must not already exist;
a partial copy is retained and cannot be reused or overwritten automatically.
The copied runtime has source overlays, not a newly rebuilt or requalified wheel.

After the owner returns a successful staging receipt, the following remain open:

1. Candidate Python prefix/import and service-identity checks without borrowing
   live credentials or treating static AST parsing as runtime qualification.
2. A separately reviewed API cutover and explicit brief interruption window.
3. Private persistent model-budget StateDirectory provisioning and current-day
   legacy usage/reservation cutover, not merely an empty new ledger.
4. Ledger backup/recovery and rollback semantics alongside service data.
5. Targeted installed acceptance; completed historical qualification is not to
   be rerun simply to obtain an all-green badge.

## Retained fleet-tool workstreams

The original 40-role tool allocation and four-specialist tool review are saved
under Projects/Hermes-Bot-Fleet/docs/. They remain proposals/review findings;
no profile tool settings or bot sessions were changed by those checks. Their
approval and scoped tool-availability testing are separate from this backend
staging handoff.
