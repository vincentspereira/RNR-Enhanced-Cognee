# Enhanced Cognee: request-validation phase accepted

Evidence date: 2026-10-12.
Status: **Scoped source repair accepted. Full integration is not accepted or activated.**

## Recommendation

Keep the accepted candidate inactive for now. The next useful step is isolated packaging and real Hermes plugin-loading tests, not another repair round and not live activation. These would test whether Hermes can actually discover and load the candidate with its intended dependencies, without touching current profiles or private data.

The approved request-validation implementation and independent review are complete. No further repair approval is needed for this resolved defect. Any installation/dependency preparation or subsequent live use needs its own exact scope; the current approval excluded those actions.

## What changed

Four existing lines that change the current lookup's request counter and indicator were moved after active/known/current-session validation, inside the same short-held state lock. Old or unknown-session lookups now return empty without cancelling a valid current lookup or erasing its indicator.

Only the copied legacy test assertion that contradicted this new contract was reconciled. Its empty rejection, no-extra-backend-call and other privacy checks remain. Both previously rejected versions and historical test expectations were preserved unchanged.

The model/database work remains outside the chat-state lock. The earlier chat-switch timing fix, source-speaker attribution, shutdown handoff, default-off capture and no built-in memory mirroring remain in place.

## Verified result

| Scope | Final passed |
| --- | ---: |
| Preserved independent timing tests, including all four prior failures | 12 |
| Original chat-switch concurrency checks | 2 |
| Native bridge contract and real-engine tests | 32 |
| Candidate timing tests | 10 |
| New request-validation regressions | 9 |
| Earlier independent rebind/filter checks | 8 |
| Fresh independent admission challenges | 11 |
| **Distinct final passing cases** | **84** |

The independent review found **no in-scope blocker**. Its fresh challenges verified 221 rejected typed-string calls without current-state mutation or backend/filesystem entry, alongside real CPU ONNX/LanceDB controls for default, explicit and unusual legitimate current session IDs. Legitimate current lookups and valid superseding requests still work.

The test collection includes both genuine model/database paths and explicitly labelled injected-backend unit tests; the table is not a claim that every case is a complete installed-Hermes run.

One fresh reviewer case initially used a nonexistent indicator field before invoking the rejection probe. Its original failure was preserved. A separate copied harness corrected only the snapshot fields, and that single case passed on replay. This was a test setup error, not a source defect; it is not counted as a second distinct passing case.

## Parent verification and preservation

I independently reconciled the complete test receipts and JUnit case identities: 73 existing cases plus 11 distinct fresh cases, all finally passing. I verified hashes and sizes for 61 resumed-review artifacts, five exact read-only references and 15 completed earlier-run artifacts. I also rechecked all 11 candidate files and 277 preservation targets; none had changed.

My earlier replay of the unchanged full 12-case independent timing harness passed against this exact provider.

The reviewer additionally records 632 prior phase evidence files preserved. The interrupted runs with empty/missing receipts remain classified unknown; the completed replacement receipts, not guessed interrupted outcomes, establish the results.

No installation, source promotion, live activation, private ingestion, Brain migration, dependency change, commit or push occurred in this phase.

## Accepted scope

Acceptance applies to this exact source candidate's request admission and the reviewed provider-local timing/state controls:

- Reject old/unknown typed-string sessions before changing current lookup ownership or indicators.
- Preserve correct current recall, bounded quoted source provenance and per-profile/keyed-chat controls.
- Keep atomic state snapshots and result/status publication, with model/storage waits outside the short state lock.
- Preserve truthful busy/timeout/close-pending behaviour and the tested shutdown handoff.

A result already accepted inside the provider cannot be retracted from a caller after a later chat switch. Complete Hermes prompt/model-dispatch transaction safety is not established. Namespace labels are not authentication or protection against another process with filesystem access. Arbitrary hostile Python objects are outside the reviewed typed-string session contract.

This source acceptance does not promote the candidate over either frozen version. The directory remains a separate reviewed candidate.

## Remaining work

1. **Real installation compatibility:** package build, source/dependency paths and actual Hermes plugin discovery/loading in disposable synthetic homes. Build prerequisites have not been installed or accepted under this phase.
2. **Operational reliability:** complete disable/rollback, authorised backup coverage, crash recovery, durable callback delivery and cancellation. Same-home synthetic stopped-writer restore evidence does not establish general portable/hot recovery.
3. **Useful automatic recall:** predeclared no-answer policy, corrected/withdrawn facts, larger held-out questions, full agent-answer quality and measured resource/maintenance benefit. The earlier ranking comparison remains bounded evidence, not overall superiority to Hermes memory plus agent-assisted session search.
4. **Private/bot scope:** exact approved sources, profiles and speaker/sharing rules before any private conversation capture or fleet rollout. Capture remains off by default.
5. **Owner library replacement:** editable interface, navigation/links/attachments, Brain compatibility, complete export/recovery and owner usability. The basic command-line library is not a full Obsidian replacement.
6. **Wider Enhanced Cognee features:** individually gated optional modules; the full server and other database adapters do not inherit this acceptance.
7. **Delivery:** reviewed branch commit/push remains a separately scoped pending action; no remote delivery has been claimed.

No new action from the owner is required to finish this repair phase. For a next testing phase, the recommended scope is isolated packaging/plugin-loading tests with synthetic data only, no current profile activation, private ingestion, Brain changes, promotion or remote push. Remain with Hermes and the existing Brain if further integration work is not wanted; that has the least upkeep but does not add native Enhanced Cognee recall.

## Exact locations

Accepted candidate:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/integrations/hermes-request-validation-v1/`

Task branch:
`hermes/enhanced-cognee-native-memory-20261012`

Provider SHA-256:
`2adc216f13d68b8fee06795429101e39d5f0fbd1d66df51daa7f85b237b30cc8`

Candidate manifest SHA-256:
`64182dee17e85b9d1fc6443ede34e9abf5bfb3f47972dd8809cf90b6fca31d00`

Evidence root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/request-validation-phase-v1/`

- `implementation/sealed-v2/`: exact candidate, minimal diff, RED/GREEN evidence and copied-test reconciliation.
- `independent-review-resumed-v1/final-verdict.json`: final independent source acceptance and limits.
- `independent-review-resumed-v1/case-reconciliation.json`: distinct cases, setup-error reconciliation and fresh observations.
- `independent-review-resumed-v1/evidence-hash-index.json`: complete artifact hash index.
- `parent-preserved-review-replay-v1/receipt.json`: parent real-engine replay of the unchanged 12 timing cases.
- `parent-final-acceptance-verification.json`: parent final hash/case reconciliation and narrow acceptance receipt.

Names: Enhanced Cognee is Vincent's project; upstream Cognee is its separate foundation.
