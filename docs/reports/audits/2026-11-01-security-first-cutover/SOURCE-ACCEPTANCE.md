# Security-first cutover preparation: source accepted

Date: 2026-11-02. Ubuntu-Hermes only.

## Recommendation and immediate owner action

Run blocks 1 and 2 in OWNER-NEXT-PLAN.md from the ordinary Ubuntu-Hermes terminal,
then return their JSON output. This installs only the protected helper and obtains
a read-only plan. Do not run --prepare, write a live override or restart the API.
The previous candidate staging and service-user imports already passed; do not
repeat them.

## Verified source and evidence

- Helper: integrations/hermes/deployment/prepare_security_first_cutover.py
  SHA-256 d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63.
- Owner commands: OWNER-NEXT-PLAN.md
  SHA-256 421c67f8db3549fc1b8000bf5982925dfc17ae8de551594c04b069960b0bf416.
- Fresh independent source acceptance: review-round2/verdict.json and REPORT.md.
  No reported security concerns, logic errors or suggestions remain.
- 260 passing offline test executions: 176 historical/replay implementations
  (173 historical logical identities plus three repeated implementations) and
  84 fresh reviewer input variants across 13 families. They are not 260 newly
  discovered contracts. No failures, errors or skips in the accepted inventory.
- Two owner Bash blocks passed syntax checks; three embedded Python blocks parsed.
  Only ordinary-user synthetic probes were executed, not root command blocks.
- Parent checked the review ZIP CRC, all 44 unique member lengths/hashes and
  archive digest 72dea048a7540200e142585dd3e8dfb86148fb766f7a47ed0647863dd735bfe7.

## Repair and canonical unit-test packaging

The rejected helper and original unit-test bytes remain in parent/round1-source.zip
and prior evidence; the rejected archive SHA-256 is
ff21c524ac91e1fdb426de8c7c4c2ec4533c94bc554252282bf0efedd495196b.
Two defects were repaired in one bounded cycle: wrong installed module locations,
and symlink-target normalisation erasing an unchecked ancestor. Original review
inputs and failure receipts remain unchanged.

The corrected physical-path fixture was independently reviewed and executed as
repair-round1/copied-original-cases.py with its original canonical __file__/ROOT
binding. For publication, that exact byte-identical reviewed body was placed at
tests/unit/test_security_first_cutover.py. Its SHA-256 is now
1d32c2528b1f860f5ae495f3606e7496c720fba463f5ae617345b23f65c1f213.
Only the fixture's source-file dictionary location changes from candidate/src to
candidate/runtime/lib/python3.12/site-packages/src; no assertion was removed or
weakened. This avoids shipping the known-obsolete failing fixture as the active
unit suite. The original rejected test bytes are preserved, not discarded.

The helper, owner instructions and every other previously accepted input stayed
unchanged during that canonicalisation. parent/publication-input-manifest.json
records the physical-location projection. Parent directly ran the TWO canonical
unit files with the normal prescribed pytest command: 126 passed, zero failures,
errors or skips (parent/canonical-tests-receipt.json). This is an additional
packaging replay, not 126 more independent contracts or a rerun of live memory
qualification. The 50 historical challenge cases remain in the reviewed replay
inventory, not in the canonical 126-case unit count.

## What has not happened

- No root helper installation or root --plan execution by the assistant.
- No live unit write, daemon-reload, API restart, model call, credential action,
  budget ledger/state provisioning, profile change or fleet activation.
- Live metadata readback still shows the old API candidate active and no
  StateDirectory. Route withholding is the future proposal, not current behaviour.
- The unreadable 20-launch-runtime.conf still needs the owner's protected plan.
  It must pass the helper's strict supported shape; no success is promised.
- Full repository tests and hosted CI are not claimed green; the historical
  optional qdrant_client dependency problem remains separate.

## Remaining gates

1. Protected helper readback and actual owner-root plan; review exact returned
   source hashes, selected unit state and plan digest.
2. Separate exact-digest approval for preparing the new private artifact bundle.
   Even that preparation does not install a live unit or take effect next boot.
3. A separately approved API-only installation/restart window and installed
   identity/readiness/analysis-off checks. Preserve optional-route withholding in
   any emergency rollback; old code has known defects.
4. Shared MCP reviewed-script installation and targeted connection refresh;
   no blanket gateway restart or fleet admission is implied.
5. DynamicUser-safe persistent model accounting, safe usage handover and tested
   encrypted backup/recovery before optional analysis is re-enabled. A midnight
   boundary alone is not evidence that the partially accounted day was unused.
6. The 40-role execution-tool proposal and four-specialist review remain separate,
   saved but unapplied. Renewal schedule and successful renewed-job execution
   remain distinct evidence gates; no manual renewal was run to obtain a badge.

Synthetic sandboxes, symlinks, FIFOs and partial bundles are retained locally,
not promoted as deployed artifacts or blindly added to publication. Selected
source, reports, complete receipts and review archives are the intended handoff.
