# Enhanced Cognee: chat-switch safety phase final result

Evidence date: 2026-10-12.
Status: **Review complete. Versioned candidate rejected and frozen.**
This report supersedes the interim recovery checkpoint for this phase; historical evidence is preserved.

## Recommendation

Do not install or activate this candidate. If continuing the native bridge, approve one new, tightly scoped request-validation repair phase. It should make an invalid lookup leave the active chat's pending result and indicator untouched, then repeat the preserved checks and obtain fresh independent review.

The prior chat-switch safety approval covered one implementation and review with a stop condition on a new blocker. That phase has ended with rejection. No further repair has started under that approval.

## Verified result

| Check | Passed | Failed | Setup errors |
| --- | --- | --- | --- |
| Corrected independent timing tests | 8 | 4 | 0 |
| Original unchanged chat-switch tests | 2 | 0 | 0 |

The four failed cases reproduce **one reliability defect**, not four separate bugs. An old or unknown-session lookup returns no result, as intended, but first changes the active request counter and clears the successful-recall indicator. This either erases an already-published indicator or causes a valid current lookup still running to return empty.

The current chat's correct-source lookup passes before the rejected request. The tests use the actual CPU model, LanceDB store and Hermes memory manager; only the existing fixture configuration loader is stubbed. The run is network-denied and uses synthetic data only. There is **no cross-chat disclosure claim** from these four failures and no claim that database work is physically cancelled.

The original chat-switch timing defect is fixed in the two preserved checks. Other new checks passed for superseded completion handling, atomic result/status publication and real backend close during search/write. A result already accepted by the provider cannot be retracted from the caller after a later switch; complete host prompt-dispatch safety remains an explicitly unaccepted separate boundary.

## Interrupted-review reconciliation

The earlier owner exit left no terminal verdict. I recovered its files, verified the four product failures and dispatched a read-only completion review. The completed corrected harness ran all 12 timing cases without setup errors or timeouts. The original three missing-thread-name failures remain classified as test-harness setup errors, not source defects. Incomplete v2 outputs remain preserved and are not labelled passing.

I independently verified all 32 entries in the final review evidence manifest, mechanically reconciled its JUnit counts, and rechecked all 10 candidate files plus 152 protected existing files. All hashes and sizes matched. Parent replay had already independently reproduced the same four failures.

No repair, installation, activation, private-data ingestion, Brain change, promotion, commit or push occurred during review recovery/completion.

## Next owner decision

### Recommended: approve a scoped request-validation repair

Reply: **Approve the scoped request-validation repair phase.**

Proposed scope, not yet authorised:

1. Preserve this rejected candidate and exact failing tests unchanged.
2. Create a separate versioned candidate in the authorised Enhanced Cognee checkout.
3. Validate that a lookup belongs to the active known session before changing request ownership, clearing indicators or altering recall diagnostics.
4. Test old-session and unknown-session rejection with both already-published and pending current results. Preserve valid current lookup, session-switch invalidation, superseding request, shutdown, delayed-write, scope and provenance controls.
5. Keep originals immutable. If a copied legacy test expects rejected calls to clear indicators, explicitly reconcile that expectation with the new contract rather than silently skipping or weakening it.
6. Run the exact previous failure and passing controls against the new candidate, then obtain fresh independent review. Stop and escalate again on a remaining blocking finding.
7. Limit source changes to the versioned bridge and necessary tests/documentation. No Hermes core, runtime/backend, dependencies, live profiles, private data, Brain, services, installation, promotion, commit or push.

**Pros:** Addresses the exact remaining request-ownership defect while retaining the now-passing original timing fix and the user's own project.
**Cons:** Another implementation/review effort is required. Success would not prove overall benefit or close installation, recovery, bot rollout or library-replacement gates.

### Alternative: pause native integration

Reply: **Keep the candidate frozen and pause native integration.**

**Pros:** No further repair effort or added live risk. Hermes and the current Brain continue unchanged; code, evidence and accepted narrow source fixes remain preserved.
**Cons:** Automatic Enhanced Cognee recall remains unavailable as an accepted live provider.

Activation of the rejected candidate is not recommended.

## Exact locations

Candidate:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/integrations/hermes-chat-switch-safety-v1/`

Provider SHA-256:
`3e3fe9282af38fabde5b86aab3d1af4a318bce77d99d78480433d514c4f6d6d7`

Evidence root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/chat-switch-safety-phase-v1/`

- `independent-review-resumed-v1/final-verdict.json`: final independent rejection, fresh counts and limits.
- `independent-review-resumed-v1/evidence-manifest.json`: complete review artifact hashes.
- `independent-review-resumed-v1/fresh-candidate-v2/receipt.json`: all 12 corrected timing cases.
- `independent-review-resumed-v1/original-concurrency/receipt.json`: two unchanged original cases.
- `parent-recovered-review-replay-v1/receipt.json`: parent reproduction of all four failures.
- `parent-resumed-final-verification.json`: parent artifact/source checks and mechanically parsed case counts.

Remaining broader gates are unchanged: real packaging/plugin admission, managed dependency paths, reliable no-answer and correction handling, operational recovery, exact private/shared scope, overall benefit and owner-editable library replacement. This review does not establish production or fleet readiness.
