# Enhanced Cognee: frozen bridge candidate and owner decision

Evidence date: 2026-10-12.
Status: **Native bridge rejected and frozen. No third automatic repair.**
This checkpoint supersedes earlier interim status reports for the bridge, without replacing their historical evidence.

## Recommendation

Do not activate this bridge in Hermes or any bot. Keep Hermes built-in memory, sessions, skills and the existing Brain unchanged.

If continuing the integration project, approve one new, tightly scoped phase to repair and independently review how the bridge handles a chat switch while a lookup is running. This is a specific reproducible defect, not a reason to rebuild all of Enhanced Cognee. Existing setup does not need to be repeated. No private-data ingestion, live activation, installation, spending or migration is included in this proposed repair phase.

## What failed

The final independent review found a timing defect: the bridge reads the old chat identity, then a valid chat switch can occur before it reads the change counter. It can therefore pair old-chat data with the new counter and return the old chat's evidence after the switch. It also displays a successful-recall indicator.

The reviewer reproduced this twice using the real Hermes memory manager, local CPU embedding model and LanceDB database. I independently replayed the unchanged test: **1 failed, 1 passed, 5 deselected**. The passing control switches slightly later and correctly discards the old result. The failing control has correct original-chat and current-chat lookups before and after the switch; it is not a test that rejects everything.

Only thread scheduling was controlled. The engine, model and provider were not replaced by pretend implementations. The host configuration loader remains explicitly stubbed in this fixture; actual installed-plugin admission and a live gateway exploit have not been established.

All 150 candidate manifest entries matched my latest check. No source repair was made after the rejection. The freeze is a recorded work/acceptance boundary, not a claim that filesystem permissions make the checkout immutable.

## What has been achieved

| Requirement | Current evidence | Acceptance |
| --- | --- | --- |
| Relevant source defects | Five inactive global bindings corrected; diagnostics moved to stderr; unsupported vector constraints reject; LanceDB structural identity matching and native result conversion tested | Accepted only for the reviewed source/normaliser/Lance scope. Initializer/protocol diagnostics are source fixtures, not a full server handshake |
| Real search comparison | Enhanced Cognee ranked the expected source first in 18/18 positive questions; Hermes ranked it first in 5/18 natural queries or 11/18 explicit keyword queries | Bounded artificial source-retrieval comparison complete, not full workflow superiority |
| Native local bridge capability | Actual model/backend construction, fresh same-home CLI recall, conflicting rebinding rejection and original speaker/session attribution work in tested controls | Candidate remains REJECTED because the new concurrent-switch defect contradicts its safety contract |
| Recovery | Complete, stopped-writer synthetic backup restored to the same absolute profile path with genuine recall | Narrow same-home fixture only. Portable relocation, live backup, general crash recovery and deployment rollback not accepted |
| Own readable/editable library | Enhanced Cognee has a reviewed local command-line Markdown library and escaped read-only reading view | Basic candidate accepted; not an Obsidian replacement. Interrupted export can be incomplete while looking valid |
| Fuller Enhanced Cognee features | Optional stages and separate activation gates documented | No permanent feature ban; no automatic enable-all rollout |
| Hermes/bot live use | Nothing accepted for activation | Not installed/activated as an accepted native provider; no private conversation ingestion or Brain migration accepted |

**Names:** Enhanced Cognee is Vincent's project (`RNR-Enhanced-Cognee`). Upstream Cognee is the separate foundation it builds on.

## Benefit and complexity verdict

Meaning-based search produced better first-result ordering in the artificial comparison. However:

- Hermes's explicit keyword search and Enhanced Cognee both found the expected source among the first five in all 18 positive cases.
- Both unthresholded methods returned records on all four unsupported questions. A returned source is not itself a false model answer, but automatic recall needs its own tested no-answer policy.
- The positive facts total 1,624 characters and could fit within the default 2,200-character built-in memory budget before notebook overhead and other memories. This is not evidence that built-in memory is inadequate.
- Enhanced Cognee lookup was slower in that run: median approximately 74 ms versus approximately 1 ms for Hermes search. Its recall process peaked around 491 MiB. These are one-run observations, not universal resource guarantees.
- Full agent-answer quality, larger-scale retrieval, everyday usefulness, dependency upkeep and corrected-fact resolution remain unproven.

Therefore the evidence supports continuing a bounded evaluation, not live adoption or replacing Hermes memory. Automatic conversation capture remains off by default; built-in memory is not mirrored into a second writer.

## Decision needed

### Recommended: approve a new scoped bridge-safety phase

Reply: **Approve the scoped chat-switch safety phase.**

Authorised scope would be:

1. Preserve the rejected candidate and the exact failing test.
2. Change only the Enhanced Cognee bridge's chat-state handling and necessary tests/documentation in a new versioned candidate.
3. Make reading the chat identity/change state and validating a returned result consistent even when another thread switches chats; do not hold up all chat activity during model/database work.
4. Re-run the unchanged failure and passing controls, then obtain fresh independent review with additional timing tests.
5. Leave Hermes core, live profiles, private data, Brain, services, dependencies and other Enhanced Cognee features unchanged. No live activation or remote push is authorised by this decision alone.
6. Stop and escalate again if a remaining defect exceeds the specifically approved phase; do not disguise repeated repairs as new filenames.

**Pros:** Addresses the exact remaining local bridge blocker while keeping the user's own project and prior work.
**Cons:** Requires more engineering/review; success still does not close deployment, usefulness, library-replacement or live-operation gates.

### Alternative: leave the bridge frozen and unconnected

Reply: **Keep the bridge frozen and pause integration.**

**Pros:** No added operational risk or upkeep; Hermes and the current Brain continue unchanged; all source fixes, tests and comparison evidence remain preserved.
**Cons:** Enhanced Cognee's automatic native recall will not be available. The local search/library work remains a separate candidate, not an accepted live replacement.

There is no recommendation to activate the rejected bridge or to enable all Enhanced Cognee features.

## Other open gates, not silently closed

- Package build, dependency/source-path handling and actual plugin discovery/admission. Build tooling is currently missing in the isolated environment; no installation success is claimed.
- Reliable no-answer handling, corrections/withdrawals, durable delivery or retry, hard cancellation and complete operational recovery.
- Exact private/shared-profile and speaker policy before bots or shared conversations are included.
- Full Enhanced Cognee MCP server handshake/backend activation if that alternative is pursued; source checks do not prove that connection.
- Broader backend safety: untouched Lance selector wrappers ignore shard routing, other database delete paths bypass the normaliser, and typed identity evidence is not transferable to every adapter.
- Full editable library interface, links/backlinks/attachments/navigation, Brain schema/provenance compatibility, complete export, recovery and owner usability acceptance before migration.
- Exact live source/profile/capture scope, authorised backup coverage and reversible cutover approval.
- Reviewed branch commit/push delivery remains pending; no commit or push has been claimed for this build.

## Locations and evidence

Authorised implementation checkout:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes`

Task branch:
`hermes/enhanced-cognee-native-memory-20261012`

Rejected provider SHA-256:
`0b4778e7530dee07f531195917cfbc679e20178b424a50d6414c80dd95a6546f`

Exact final test/source manifest:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/bridge-integration-fix2/06-final-bridge-independent/manifest.json`

Manifest SHA-256:
`1135f3fa9db9d6fb35d362c5e09e9e656a7d42fd71b4075d5f069e1faea40c90`

Final independent rejection:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/independent-bridge-final-review/review-verdict.json`

Parent unchanged-test replay and exact candidate checks:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/parent-final-concurrency-replay/receipt.json`

Independent narrow source acceptance:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/independent-source-filter-recheck/verdict.json`

Independent basic library acceptance and limits:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/independent-source-library-review/verdict.json`

Comparison report:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/docs/hermes-retrieval-comparison-2026-10-12.md`

The comparison's exact executed scripts are now also preserved under the durable project evidence directory `comparison/executed-harnesses/`, not solely in temporary scratch.
