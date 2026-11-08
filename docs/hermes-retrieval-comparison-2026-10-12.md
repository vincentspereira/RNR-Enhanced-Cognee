# Enhanced Cognee: first real retrieval comparison

Evidence date: 2026-10-12. Status: bounded comparison complete; integration and overall benefit not accepted.

## Recommendation

Keep Hermes built-in memory, saved sessions and the existing Brain unchanged. Enhanced Cognee has demonstrated better first-result ordering in this small artificial test, but that alone does not justify live activation or replacing the Brain. Finish the bridge review and reliability/usability gates first.

Names: **Enhanced Cognee** is Vincent's project, repository `RNR-Enhanced-Cognee`. **Upstream Cognee** is the separate foundation it builds on. These are not interchangeable names.

## Actual measurements

The same frozen artificial source collection was used. Enhanced Cognee used its existing LanceDB adapter and an actual local CPU ONNX embedding model. Ingest and recall ran in separate fresh processes, with networking denied. Hermes used the actual unmodified `SessionDB.search_messages` implementation in a disposable home, with no search or configuration doubles. Its managed-runtime switch required explicitly supplying already installed dependency paths; this was fixture setup, not a live runtime repair.

| Retrieval method | Correct first source | Correct source among first five | Returned something on unanswered questions | Median lookup |
| --- | --- | --- | --- | --- |
| Hermes, original natural-language question | 5/18 | 17/18 | 4/4 | 1.33 ms |
| Hermes, frozen explicit OR search terms | 11/18 | 18/18 | 4/4 | 0.70 ms |
| Enhanced Cognee, original question, raw ranking | 18/18 | 18/18 | 4/4 | 74.37 ms |

Enhanced Cognee had no observed foreign-scope source returns in these 22 questions. This is a bounded negative check, not proof of an operating-system security boundary or general permission enforcement.

Enhanced Cognee indexed 139 records in approximately 15.94 seconds including initialisation. Recall-process initialisation was approximately 0.80 seconds. Peak process memory was approximately 491.35 MiB. Its slowest measured lookup was approximately 1.66 seconds. These are one-run observations, not service guarantees or idle-memory measurements.

## What the results mean

- Meaning-based search put the expected source first more consistently in this artificial collection.
- Hermes keyword search found every expected source among its first five when given the frozen OR queries; Enhanced Cognee did not improve that measure.
- Both unthresholded search methods returned records on all four questions with no supported answer. Returning a record is not itself a fabricated model answer, but reliable automatic recall needs a separately checked refusal-to-recall policy. No threshold was tuned on these held-out cases.
- The 18 positive fact texts total only 1,624 characters and fit the default 2,200-character built-in memory budget before notebook overhead and other memories. A carefully curated built-in notebook is therefore a credible baseline here. This benchmark does not prove an advantage over built-in memory plus a capable agent using session search.
- No answer-producing AI model was evaluated. Automatic extraction of decisions, correction interpretation, everyday usefulness, fleet operation and maintenance effort remain unproven.

## Separate work still pending

1. Review source fixes and reconcile obsolete mocked test fixtures without weakening real filtering checks.
2. Fix and test the native bridge's real runtime construction and intended same-profile cross-session recall; keep other profiles and explicitly keyed conversations separate.
3. Test denied-egress behaviour, corrected/withdrawn evidence, interruption, backup/restore and disable/rollback at the integrated boundary.
4. Independently review the editable Markdown library. Its command-line editing and reading view do not establish Obsidian replacement, GUI editing, backlinks, attachment handling, Brain compatibility or an authorised migration.
5. Define features as separately optional modules. Starting small is not a permanent ban on fuller Enhanced Cognee features, and success does not automatically enable everything.
6. Seek explicit live profile/data-scope approval only after the relevant evidence passes. No live activation or private conversation ingestion is accepted by this report.

## Evidence locations

Comparison evidence root:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/comparison/`

- `frozen-synthetic-comparison.json` and `frozen-comparison-manifest.json`: inputs and predeclared scoring policy.
- `actual-hermes-session-search-baseline.json`: all 44 baseline query results, both modes retained.
- `actual-enhanced-cognee-ingest.json`: real indexing receipts, source hashes and model identity.
- `actual-enhanced-cognee-recall.json`: all 22 raw-ranking results, scores, timing and scope checks.
- `parent-comparison-summary.json`: mechanically aggregated counts and limits.

Frozen input SHA-256:
`e21366a75380bfb25493f08237f8b37597c82675230685f634fab891045df5ed`

The executable benchmark scripts are preserved under:
`/home/vincentspereira/.hermes/cache/scratch/enhanced-cognee-setup-20261012/`

- `run_isolated_hermes_baseline.py`
- `run_enhanced_retrieval_comparison.py`

Scratch files are temporary retention, not durable backup. The result receipts above are saved in the authorised project evidence directory.
