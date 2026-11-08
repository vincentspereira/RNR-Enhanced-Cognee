# Enhanced Cognee automatic memory: current deployment decision

Evidence date: 2026-10-12.

## Recommendation and decision

**Do not activate the current Enhanced Cognee connector as automatic memory.** Keep Hermes's existing memory, saved sessions and skills operating as they are.

This decision applies the owner's explicit condition: deploy only if it improves the workflow without unjustified effort, complexity or duplication. The current build does not meet that condition. It is a working search/connector prototype, not dependable automatic conversational memory. Bringing it to that standard requires more than installing a package; overall everyday benefit has not yet been demonstrated to justify that additional development.

This is not a permanent rejection of Enhanced Cognee or of the earlier accepted source repairs. All source, artifacts, model assets, tests and historical evidence remain preserved. No further automatic repair, installation, feature rollout or private ingestion is being started by this decision. No action, credentials or repeated repair approval is required from the owner to retain the current Hermes setup.

## The two concrete deployment faults

Fresh independent tests used artificial data and the actual packaged connector, native Hermes loading and local model/storage:

1. **Desktop memory does not follow the owner into a fresh chat.** The same store reopens successfully, but Desktop records use the old chat's identity and are not recalled in a new session. The CLI control works. CLI means the terminal interface; it is not evidence that the Desktop works.
2. **Shared-room capture is not blocked.** Four tests, covering group/channel conversations through CLI/Desktop, stored artificial user text despite the required one-to-one-only rule. No real shared-room conversations were ingested.

These faults are repairable. Fixing them alone would not resolve the saving, correction, recovery and usefulness limits below. The candidate is therefore not approved for automatic deployment.

## Other limits preventing dependable automatic memory

- A background capture can fail or be skipped when the store is busy; no verified saved/not-saved receipt and reliable retry are integrated into the conversation workflow.
- A later correction is another raw quote. The automatic path does not reliably publish a replacement for the old current fact. Low-level explicit correction controls exist and passed tests, but that is not proof that automatic capture uses them.
- Complete selected-data backup/restore passed. Installed Hermes profile, plugin configuration, dependency environment and full-host disable/recovery have not passed an equivalent drill.
- The actual managed core-plus-plugin install transaction is unrun. Built artifacts, declared dependencies and test-environment loading are not the completed installation in the running main profile.
- Complete host prompt dispatch remains unverified. Direct manager concurrency tests do not certify the whole conversation lifecycle; no real host cross-session exploit is claimed.
- Six additional real-Qdrant filter replay cases were unrun in the package review because its test interpreter lacked qdrant_client. This is a missing test prerequisite, not a reason to add Qdrant as a live service or a claim that those tests passed.

## What independently passed

| Work | Verified result | Boundary |
| --- | --- | --- |
| Package build and loading | Directory artifact and wheel hashes verified; genuine discovery, registration, configuration and memory manager loading with actual local CPU model/storage | Does not establish live managed installation or data-policy acceptance |
| Package behaviour review | 76 passing cases, 5 failed cases; 81 distinct completed cases reconciled against their JUnit executions | Five failed cases demonstrate two deployment faults; six filter cases remain unrun |
| Operational source/runtime tests | 22 passed: 7 operational cases and 15 unchanged runtime cases | Explicit correction/withdrawal, selected-data restore, outage/retry and crash controls; not automatic capture guarantees or installed-profile recovery |
| Benefit comparison | Independent replay reproduced every source identity in the frozen comparison | Source retrieval only; final AI answer quality and whole-workflow benefit remain unmeasured |
| Preservation | Package reviewer recorded 89 protected files unchanged; parent verified all 89 current hashes | No source/configuration changes from this review |

The parent also verified 34 operations-review evidence files, all 22 successful JUnit cases, 12 package-review harnesses (11 original/copy pairs plus one fresh harness), and the package's 81 reconciled final case outcomes. A parent verifier initially assumed every harness had an original counterpart; the fresh harness has none. That verification setup error was corrected without changing source, harness assertions or review evidence.

## What the larger comparison means

| Search approach | Correct source first | Correct source in first five | Unsupported questions that returned a candidate |
| --- | --- | --- | --- |
| Hermes natural-language keyword lookup | 0/24 | 0/24 | 6/12 |
| Hermes lookup assisted by the named project | 24/24 | 24/24 | 6/12 |
| Enhanced Cognee, current low threshold | 23/24 | 24/24 | 12/12 |
| Enhanced Cognee, separately calibrated threshold | 23/24 | 24/24 | 1/12 |

Enhanced Cognee genuinely improves differently worded lookup compared with direct keyword search. It did not outperform the stronger assisted native baseline in this source-ranking test. That does not prove it is useless: automatic retrieval might reduce steps in a real conversation, which was not measured here.

The calibrated threshold failed the predefined requirement that unsupported questions return no candidate. The one returned source explicitly says the requested information is not recorded. This may help an AI answer 'I don't know'; it is not evidence that the AI invented an answer. Native search also returned candidates for unsupported questions. Do not turn candidate returns into claims about hallucinations.

The calibrated policy is not installed in the connector; the connector still uses its original lower threshold. No threshold was retuned after seeing the held-out failure.

## Cost and complexity

The minimal package avoids the full service stack and extra answer-model calls. One measured process used roughly 400-430 MiB of memory. The prepared dependency closure occupies about 559 million installed-file bytes, plus the local model. Lookup timings varied between runs; the fresh independent concurrent run observed about 76 ms median for Enhanced Cognee and 0.53 ms for assisted native retrieval. These are observations, not a controlled full-agent or fleet cost estimate.

One main-profile instance is not necessarily excessive for this machine. The recommendation against current automatic activation is primarily about missing workflow reliability/privacy acceptance and insufficient demonstrated overall benefit, not a claim that half a gigabyte is inherently prohibitive. Do not extrapolate a measured single process into an accepted all-bot resource plan.

## What remains unchanged in the running system

Parent read-back of `/home/vincentspereira/.hermes/config.yaml`:

- `memory.provider`: unset.
- `plugins.enabled`: empty list.
- Configuration hash unchanged from the inspected pre-deployment state.
- `/home/vincentspereira/.hermes/enhanced-cognee.json`: absent.

No live automatic capture, old-chat import, Brain migration, shared-room capture, dormant-bot activation, cloud memory or extra service was performed. Existing preparation files under `.hermes/enhanced-cognee` are preserved; the directory is not being adopted as a live memory store by this decision.

## Options

### Recommended: retain current Hermes memory and session search

Pros: no new maintenance, duplication of authority or capture exposure; the stronger assisted native baseline worked on all positive cases.

Cons: differently worded questions may need an explicit session search; essential notebooks remain small.

Owner action: **none**. This is the default outcome of the conditional deployment instruction.

### Optional future evaluation: an explicit derived search collection

Use one separately identified, owner-approved collection with visible indexed/not-indexed receipts and deliberate revisions/withdrawals. Keep original sources authoritative.

Pros: can exploit Enhanced Cognee's meaning-based search without claiming it maintains automatic current facts.

Cons: some deliberate maintenance; its useful-work advantage still needs measurement. No Brain or old-chat collection is authorised by this report, and this alternative is not being activated.

### Further automatic-memory product development

Repair Desktop continuity and capture policy, integrate dependable save outcomes and correction publication, prove installed-profile recovery/full-host behaviour, then measure real conversational benefit against native memory plus assisted session search.

Pros: could eventually meet the originally requested automatic experience.

Cons: additional development and upkeep; no established overall winner yet. This is not a simple installation or a permission to turn on the full feature catalogue.

## Task accounting

The benefit/reliability assessment is complete with a negative current automatic-deployment decision. Deployment-related steps are being stopped under the owner's usefulness/simplicity condition, not marked passed. Full MCP server activation and other database backends are not needed for the selected small native route; they remain untested optional alternatives, not falsely certified features.

The previous chat-switch candidate's rejected phase remains recorded as stopped historical work. Accepted request-validation repairs remain accepted. **All workstreams are accounted for; the requested live deployment has not been delivered.** A stopped task is not a successful installation, and a completed assessment is not a completed rollout.

## Preserved artifacts and exact evidence

Implementation checkout:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes`

- Accepted narrow source: `integrations/hermes-request-validation-v1/`
- Current deployment candidate: `integrations/hermes-deployment-v1/`
- Operational assessment: `docs/hermes-memory-operations-v1.md`

Evidence root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-deployment-2026-10-12/`

- `packaging/REPORT.md`, `packaging/artifacts/`: built directory, wheel and source distribution.
- `independent-packaging-review/VERDICT.json`, `REPORT.md`, `case-reconciliation.json`, JUnit and preservation manifests.
- `independent-operations-value-review/verdict.json`, `manifest.json`, benchmark replays and JUnit.
- `operations-value/sealed-delivery.json`: original operational delivery evidence, preserved.

These locations preserve useful work for a future decision. No cleanup, deletion, reset, commit, push or deployment was performed to obtain this conclusion.
