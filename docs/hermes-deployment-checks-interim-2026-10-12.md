# Enhanced Cognee: deployment checks - interim owner update

Evidence date: 2026-10-12. Independent reviews pending. Nothing activated.

## Plain-English result so far

Enhanced Cognee can now be packaged as a small connector that Hermes finds and loads in a test setup. That is progress towards deployment, not a rejection of the project.

However, the current automatic-memory behaviour is not ready to turn on. A background save can be skipped when the store is busy, and a later correction is stored as another quote rather than reliably replacing the old fact. These are different issues from the source faults already repaired.

The new comparison also gives a more balanced result: Enhanced Cognee helps with differently worded questions, but when Hermes searches by the named project, native search found the correct source first in all 24 positive cases, versus 23 for Enhanced Cognee. This compares finding sources, not final AI answers.

## Recommendation at this checkpoint

Keep live capture off while the exact package and new operational evidence are independently checked. Do not add the full Enhanced Cognee services, a second bot manager, extra AI calls or a new writer service to force a deployment.

This is not a permanent rejection of Enhanced Cognee and not a claim that meaning-based retrieval has no value. The decision is whether a small remaining change can make the approved main-profile use genuinely useful and dependable without extra upkeep. If not, the owner's instruction permits recommending against automatic deployment.

## What has been produced

- A self-contained directory plugin, built wheel and source distribution.
- Tests using genuine Hermes discovery, registration, configuration loading and memory manager, plus actual local CPU embeddings and LanceDB.
- A separate fresh process that reopens a synthetic memory store successfully.
- Complete selected-data backup/restore, explicit correction/withdrawal, outage/retry and crash-recovery tests.
- A larger frozen comparison with separate calibration and held-out questions. Negative results remain preserved; thresholds were not adjusted after seeing the held-out failure.

These are worker results read back by the parent, not final independent package/operations acceptance. The previous accepted source provider remains unchanged. No live profile, private messages or Brain records were imported.

## Important comparison limits

The held-out test requires no returned candidate for unsupported questions. Enhanced Cognee's separately calibrated threshold returned one candidate out of 12 unsupported questions, so that declared gate failed. Hermes's assisted search returned six. The Enhanced Cognee candidate explicitly says the requested field is not recorded, so returning it might help the AI say 'I don't know'. It is not evidence that the AI invented an answer. The failed gate must still be reported rather than silently relaxed.

All 24 expected sources appeared among Enhanced Cognee's first five results. Natural-language native searches performed worse than named-project-assisted native searches. A complete conversation-level test is still needed before claiming a winner for everyday work.

Measured costs were approximately 412 MiB peak process memory and 42 ms median lookup for Enhanced Cognee, versus 63 MiB and 0.217 ms for the native assisted benchmark. The prepared dependency environment contains approximately 559 million installed-file bytes plus the existing model. This is a single-machine observation, not a fleet cost measurement. It is not necessarily excessive for one main profile, but should not be multiplied across all dormant bots without separate checks.

## Main-profile deployment checks still required

1. Independent review of the packaged code and replays of its previously accepted behaviour against the packaged modules.
2. Actual Desktop fresh-session recall. The earlier provider's continuity rule was CLI-specific; CLI success alone is insufficient for the user's Desktop workflow.
3. Enforced rejection of shared-room capture and the owner's exact main-profile-only future-message policy.
4. Managed dependency/install transaction. Hermes's supported installer requires a Git source and revision; the uncommitted directory/wheel smoke is not the completed live installation. No ad-hoc pip injection into Hermes's selected environment.
5. Clear save-failure/retry and correction/withdrawal behaviour, no-answer policy, and full installed-profile disable/recovery checks.
6. An honest usefulness/simplicity decision before turning future private-message capture on.

The owner has already authorised deployment subject to usefulness and simplicity, and chosen future one-to-one messages in the main profile only. No repeat approval is being sought for those settled decisions. Old-chat import, Brain migration, shared rooms, dormant-bot activation and unrelated spend remain excluded.

## Next work already dispatched

- Independent package/loading review, including actual Desktop and shared-room policy controls.
- Independent reliability/value review, including the held-out failure and the stronger native baseline.

No automatic source repair has been dispatched during this read-only review. Any necessary subsequent work will be bounded by the expanded deployment instruction and will preserve accepted/rejected originals. Live activation will not be claimed from a prepared artifact or a passing isolated import.

## Evidence locations

Root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-deployment-2026-10-12/`

- `packaging/REPORT.md`: package artifacts, actual tests and installation limits.
- `packaging/directory-artifact-manifest.json`: exact directory artifact manifest.
- `operations-value/sealed-delivery.json`: 40 evidence/source hashes verified by the parent.
- `operations-value/final-summary.json`: new operational test results.
- `operations-value/calibrated-policy.json`, `holdout.json`, `baseline.json`, `enhanced.json`: complete comparison evidence.
- `independent-packaging-review/` and `independent-operations-value-review/`: current read-only review output boundaries.

Implementation package candidate:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/integrations/hermes-deployment-v1/`

Operational assessment:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/docs/hermes-memory-operations-v1.md`
