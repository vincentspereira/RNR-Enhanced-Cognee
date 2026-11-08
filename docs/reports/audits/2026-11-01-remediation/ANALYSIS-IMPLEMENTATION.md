# F03/F04/F05 analysis remediation - source-only evidence

Environment: existing WSL worktree, branch
`codex/enhanced-cognee-audit-remediation-20261101`, baseline `89d1be78`.
No commits, deployment writes, service restarts, live model calls, real memory
backend connections, qualification tests, or native tests were performed.

## Result

- Summarization and consolidation require explicit, bounded, unique record_ids.
  Every fetched snapshot must match the selected id, active state, project,
  authenticated subject provenance, positive version, usable content and valid
  unexpired timestamp if present. Shared and unverifiable records are refused.
- Summary is return-only: stored=false, record_id=null, source_records carries
  selected ids and versions. There is no summary remember() call or unfiltered
  recent-record selection.
- Every model endpoint uses a persistent SQLite ledger keyed by tenant, project,
  UTC day. BEGIN IMMEDIATE atomically reserves serialized UTF-8 input bytes plus
  a 1024-token framing allowance and the entire output maximum before chat.
  Failed, cancelled, abandoned and missing/malformed-usage calls retain their
  conservative charge. Reliable positive integer usage reconciles once against
  the original reservation/day. Overages are accounted, not clipped.
- Ledger configuration is ENHANCED_LLM_BUDGET_DB. There is no memory fallback.
  Missing/unsafe/unavailable ledger blocks model calls but not canonical memory.
  Status reports configured=false and used_today=null when accounting is absent
  or unreadable. SQLite lock waits are bounded to 250ms per operation; request
  operations run in worker threads.
- Ledger requires an absolute path in a private service-UID-owned directory.
  Files are created exclusively with mode 0600, never truncated; directory/file
  symlinks, hardlinks, unsafe ownership/modes and unsafe journal paths are refused.
- Credential-shaped input is refused before prompt truncation and again before
  dispatch. Original string leaves and serialized field pairs are inspected:
  serializing quoted JSON alone had masked password/api_key assignments.

## Owned repository paths

- src/llm_summarize.py
- src/llm_budget.py (new)
- src/memory_api.py (analysis request classes, analysis endpoints/helpers, LLM lifespan only)
- tests/unit/test_analysis_audit_remediation.py (preserved scaffold extended)
- tests/unit/test_analysis_lifespan_audit_remediation.py (new)
- tests/unit/test_analysis_protocol_audit_remediation.py (new)
- tests/unit/test_llm_budget_audit_remediation.py (new)
- This report and the analysis-*.txt evidence files listed below.

Other concurrent changes were not edited. Ingestion/library endpoint integration
is reserved for the parent. Original source copies were preserved outside Git at
`/home/vincentspereira/.hermes/cache/scratch/analysis-originals-ydzufpl0`.

## Commands

All pytest commands used:

```text
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -m pytest --confcutdir=tests/unit <files> -q
```

Each run's stdout/stderr is saved in its named evidence file below. Final command:

```text
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -m pytest --confcutdir=tests/unit tests/unit/test_analysis_audit_remediation.py tests/unit/test_analysis_lifespan_audit_remediation.py tests/unit/test_analysis_protocol_audit_remediation.py tests/unit/test_llm_budget_audit_remediation.py -q
```

Final: 98 passed in 5.82s; no failures, errors, skips or warnings reported.
Real SQLite tests include independent concurrent connections, reopen, abrupt
subprocess exit, tenant/project isolation, UTC rollover, missing/malformed usage,
transport failure/cancellation retention, lock contention and safe file handling.
HTTP/model/store/lifespan dependencies are synthetic; no live model was sent data.

Additional commands succeeded:

```text
git diff --check -- src/llm_summarize.py src/memory_api.py
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -m py_compile src/llm_summarize.py src/llm_budget.py src/memory_api.py
```

## RED/GREEN evidence

Paths below are relative to this report directory. RED exits were 1; GREEN exits
were 0. The initial preserved scaffold had ten false-positive negative tests:
Pydantic ValidationError is a ValueError. Moving request construction outside the
exception assertion made them exercise the endpoint after implementation.

| Evidence file | Files exercised | Result |
|---|---|---|
| analysis-preserved-RED.txt | analysis | 3 failed, 10 passed |
| analysis-source-RED.txt | analysis | 13 failed |
| analysis-source-GREEN.txt | analysis | 13 passed |
| analysis-screen-RED.txt | analysis | 20 failed, 13 passed |
| analysis-screen-GREEN.txt | analysis | 33 passed |
| analysis-budget-core-RED.txt | budget | 13 failed |
| analysis-budget-core-GREEN.txt | budget | 13 passed |
| analysis-budget-files-RED.txt | budget | 5 failed, 18 passed |
| analysis-budget-paths-RED.txt | budget | 7 failed, 16 passed |
| analysis-budget-files-GREEN.txt | budget | 23 passed |
| analysis-budget-dispatch-RED.txt | analysis | 15 failed, 32 passed |
| analysis-lifespan-RED.txt | lifespan | 2 failed, 1 passed |
| analysis-budget-dispatch-GREEN.txt | analysis, lifespan, budget | 73 passed |
| analysis-protocol-RED.txt | protocol | 3 failed, 8 passed |
| analysis-protocol-GREEN.txt | all four | 84 passed |
| analysis-status-RED.txt | analysis | 3 failed, 47 passed |
| analysis-status-GREEN.txt | all four | 88 passed |
| analysis-escaped-credentials-RED.txt | analysis | 10 failed, 51 passed |
| analysis-final-GREEN.txt | all four | 98 passed |

## Remaining integration/owner concerns

1. No deployment is claimed. An owner must provision a service-private writable
   ledger directory and expose ENHANCED_LLM_BUDGET_DB. The current
   src/memory_daemon.py _API allowlist does not admit that setting and discards
   arbitrary inherited environment values; the parent must arrange a separately
   scoped daemon/config change before model activation. That source was outside
   this assignment and is unchanged. Without it the model route fails closed.
2. Existing tests/qualification/test_llm_family.py uses the retired no-argument
   in-memory TokenBudget()/allows()/charge() API. It was not edited or executed
   under this bounded unit-test assignment. Its dedicated budget case needs an
   explicit temporary ledger path and tenant/project reservation API migration;
   do not reintroduce an implicit in-memory production fallback to satisfy it.
3. Unit coverage does not establish service-UID isolation, durable filesystem
   guarantees on the installed host, end-to-end private-data suitability, or
   installed model token accounting. Credential detection is conservative and
   pattern-based, not a complete secret/privacy classifier. Explicit source
   selection is processing approval, not an automatic persistence approval.
4. Summary output remains untrusted model text. Return-only semantics avoid a
   stale detached stored derivative; any later persistence needs its own reviewed
   admission/provenance/version workflow. No automatic summary deletion is needed
   because no summary is written by this route.
