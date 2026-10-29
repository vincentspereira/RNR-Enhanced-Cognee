# Enhanced Cognee: staged feature use and current acceptance gates

Evidence date: 2026-10-12. Owner-facing interim report, not live activation approval.

## Recommendation

Keep Hermes operational memory, sessions and skills in place. Evaluate Enhanced Cognee as an optional meaning-based search layer first, then add only features with a demonstrated need. Preserve the existing Brain until its replacement passes editing, navigation, source-integrity, complete-export, recovery and owner-usability checks.

A reduced initial runtime means a bounded starting point, not permanent removal of Enhanced Cognee's other features. A successful first stage does not automatically enable the full feature catalogue.

Names: **Enhanced Cognee** is Vincent's application. **Upstream Cognee** is its distinct foundation. Neither name is a substitute for the other.

## Current status

| Workstream | Evidence now available | Still required |
| --- | --- | --- |
| Source fixes | Original 16 dedicated tests passed; independent real-engine probes found unsupported scalar filter clauses and `min_should` being ignored | Current safety acceptance is BLOCKED. Parent replay confirmed 5 failures and 1 positive-control pass. First scoped safety repair is underway; fresh independent review must follow |
| Native bridge | Six changed-file hashes independently matched the repair manifest; implementer reports real model/backend construction and same-profile fresh-session recall tests passing | Independent bridge review is underway. Candidate test success is not full plugin installation, managed-runtime compatibility, bot rollout or operational acceptance |
| Real retrieval comparison | Actual local model/LanceDB search placed expected source first in 18/18 positive questions, versus Hermes 5/18 natural questions or 11/18 OR searches | Neither raw search abstained on four unsupported questions. Full agent usefulness, scale, cost and maintainability remain unproven |
| Human-readable library | Independent review accepted the bounded local command-line source-library candidate; source/export round trips and crash probes ran | No write GUI, real-browser acceptance, full Brain compatibility or Obsidian replacement acceptance. Interrupted export can be a valid-looking incomplete prefix; reopening alone is not complete-backup proof |
| Live operation | No live activation, private conversation capture or Brain migration is accepted | Exact data/profile scope and owner approval after technical evidence passes |

The filter defect predates the current patches but still blocks the promised safety contract. It cannot be dismissed because older tests pass. All deletion probes used synthetic records, not the owner's notes or sessions.

## Optional stages

| Stage | Feature and purpose | Avoided duplication | Required gate before use |
| --- | --- | --- | --- |
| 0 - preserved baseline | Hermes built-in notebooks, saved sessions and skills; current Brain | No new runtime introduced | Keep existing behaviour and source ownership unchanged |
| 1 - approved document recall | Enhanced Cognee finds relevant passages by meaning and provides source references | Source notes remain authoritative; derived search index is not another editable truth store | Exact approved source allowlist; safe filters; fresh-process recall; no foreign scope returns; denied-egress tests; stale/corrected/withdrawn evidence; bounded latency/context |
| 2 - native read-only bridge | Hermes automatically asks the approved index for bounded relevant context | No second conversation writer; no mirror of built-in memory or skills; no second model answer pipeline | Actual plugin discovery/admission, isolated dependency compatibility, outage handling, safe disable, complete backup/restore and independent exact-source review |
| 3 - opt-in conversation evidence | Capture only explicitly approved direct user evidence for cross-session lookup | Original Hermes session archive remains canonical conversation history; no assistant guesses promoted to owner facts | Per-profile/current-speaker scope; exact consent; idempotent writes; durable failure handling; correction/withdrawal semantics; shared-room policy; no capture from subagents or scheduled runs by default |
| 4 - owner-editable knowledge library | Use Enhanced Cognee's own library rather than requiring Obsidian as the owner interface | One canonical editable library, not two automatically synchronised competing copies | Usable editing interface; links/backlinks, navigation and attachments where required; existing Brain schema/provenance preservation; complete export and interruption recovery; authorised reversible migration; owner acceptance |
| 5 - additional graph/extraction/service features | Add specific Enhanced Cognee capabilities only when simpler search cannot meet a measured need | No duplicate Hermes task scheduling, approvals, bot orchestration, memory notebooks or skill management | A separate feature-specific benefit, local/remote processing destination, cost/licence/maintenance assessment, real integration tests and explicit activation scope |

Stages 1 and 2 are related but separately accepted: a good search engine is not automatically a reliable Hermes connector. Stage 4 can be developed without enabling automatic capture at stage 3. These are selectable modules, not a mandatory all-features sequence.

## Important limits

- Raw conversation capture is not automatic reliable fact extraction or conflict resolution. Recording both an old statement and a correction does not prove that recall always chooses the current fact.
- A chat namespace is a retrieval label, not protection from another process with filesystem access. Shared-chat speaker rules need their own policy and tests.
- A returned source is evidence, not permission to spend, run commands, publish, activate bots or override present instructions.
- The current bridge keeps capture off by default and does not mirror Hermes built-in memory. Busy-write rejection is reported; it is not a durable queue guarantee.
- The basic library is usable from the command line, but a read-only HTML page is not an editable application. Its current export is not safe to advertise as a complete transactional backup.
- The existing artificial positive facts fit within Hermes's default built-in memory allowance. Better first-hit search ordering alone does not prove that the complete workflow is better enough to justify more upkeep.

## Owner decisions

No new live approval is requested while safety repair and reviews remain open. Existing isolated setup and synthetic-test approval remains sufficient for that work.

Before a live pilot, the owner must approve the exact selected profile, source/data allowlist, capture mode, any permitted processing destination and rollback/backup scope. The recommended first live choice, if its gates pass, is approved document recall with conversation capture off. This offers a narrower reversible test with less duplicate writing.

Alternative: remain entirely with Hermes and the existing Brain. This has the least upkeep but does not add the demonstrated meaning-based first-result ordering.

Alternative: opt into conversation capture after its additional gates. This may reduce repeated explanations but adds storage, correction, privacy and failure-handling responsibilities.

Alternative: prioritise the editable Enhanced Cognee library before memory integration. This aligns with using the owner's project, but requires substantially more interface and migration work than the current command-line candidate.

## Exact evidence locations

Root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/`

- `independent-source-library-review/verdict.json`: separate library acceptance and source safety failure.
- `independent-source-library-review/test_fail_closed_regressions.py`: immutable real-engine safety probes.
- `parent-filter-red-replay.json`: parent replay, 5 failures and 1 positive-control pass; six bridge file hashes matched.
- `bridge-integration-fix1/changed-files-manifest.json`: exact original/final bridge and legacy-fixture hashes.
- `comparison/parent-comparison-summary.json`: bounded measured retrieval results and limitations.

This report does not supersede preserved failed candidates, grant activation or close unrelated operational gates.
