# Enhanced Cognee: interrupted safety review recovered

Evidence date: 2026-10-12. Status: candidate frozen; read-only review completion resumed.

## Recommendation

Keep the candidate uninstalled and inactive. Resume the interrupted review, not source repair. The previous approval permits one scoped implementation and review; it requires freezing and reporting a new blocker rather than starting another automatic repair.

## What was recovered

The previous delegated review did not record a terminal result before the owner session exited. Its final outcome is unknown. Saved files are evidence of particular completed runs, not proof that the entire review finished.

The saved `independent-review/freeze-receipt.json` records a reproduced blocker: a lookup for an old or unknown physical session is rejected, but first increments the current request counter and clears its recall indicator. That can suppress a valid current-chat lookup that is still running, or erase its already-published recall indicator.

I replayed the four checks using the unchanged corrected reviewer test bytes, the actual versioned provider, real Hermes memory manager, CPU ONNX embedding model and LanceDB. Only the host configuration loader is stubbed as in the existing fixture. The run was kernel network-denied and used synthetic data only.

**Parent replay: 4 failed, 8 deselected, no test errors.** The controls first verified that the current chat recalled only its own source. The rejected call returned an empty result, but changed the current request ID. In the running-lookup controls, the valid current lookup subsequently returned empty. This is a request-ownership/reliability defect, not a newly demonstrated cross-chat disclosure or a claim of hard cancellation of database work.

The original chat-switch failure had previously passed both unchanged controls against this candidate. That specific improvement does not override the newly reproduced defect.

## Source preservation

Latest parent hash checks matched all **10 candidate files** and **152 protected existing files**. No source, test expectation, package, live configuration, Hermes core, private profile or Brain file was repaired or promoted during recovery.

Candidate:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/integrations/hermes-chat-switch-safety-v1/`

Provider SHA-256:
`3e3fe9282af38fabde5b86aab3d1af4a318bce77d99d78480433d514c4f6d6d7`

Candidate manifest SHA-256:
`88344fbad334179d56324534e3a3d12f90610d675225e0848c4eef17ec450bbd`

The rejected earlier bridge at `integrations/hermes/` remains unchanged as well.

## Interrupted review limits

The first saved fresh run contained four substantive failures and three test-harness setup failures caused by missing required thread names. Those setup failures are not additional source defects. A separate corrected v2 test preserves the original expectations and supplies the names. Its old partial run has empty captured output and no terminal receipt; it must not be labelled passed or failed.

A fresh read-only reviewer has been dispatched to execute that corrected harness in a new evidence directory and issue a terminal verdict. Existing incomplete outputs will be preserved. No new repair, installation, activation, migration, commit or push has been dispatched.

## Exact evidence

Evidence root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/chat-switch-safety-phase-v1/`

- `independent-review/freeze-receipt.json`: recovered freeze notice.
- `independent-review/fresh-candidate/receipt.json`: completed initial independent run with separately classified setup failures.
- `independent-review/test_independent_interleavings_v2.py`: corrected independent scheduling harness.
- `parent-recovered-review-replay-v1/receipt.json`: new parent run, exact import binding, source checks, all four failure cases and literal output.
- `independent-review-resumed-v1/`: new review output boundary; completion remains pending at the time of this checkpoint.

Full native installation, host prompt-dispatch safety, workflow benefit, fleet operation and Brain replacement remain separate unaccepted gates.
