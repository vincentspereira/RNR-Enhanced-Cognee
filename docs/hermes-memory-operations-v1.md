# Enhanced Cognee minimal memory: offline operations and value gate v1

## Decision

**GO for the bounded offline runtime/source-library controls; NO-GO for claiming a
reliable automatic external memory deployment or replacing native memory.**
No production helper or durable queue was added. Existing runtime operations
already cover revision replacement, withdrawal and verified indexed writes.
Adding a second writer/service would not fix the missing host-facing guarantees.
Keep native notebooks/sessions and canonical owner records authoritative. A
manual, approved-document derived index remains a possible bounded feature, not
an automatic conversational fact resolver.

Evidence directory:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-deployment-2026-10-12/operations-value/`

This assessment used only synthetic sources, the already approved local
BGE-small-en-v1.5 CPU ONNX model and existing LanceDB. Tests and both benchmark
processes ran with networking denied by `unshare --user --map-root-user --net`.
No installs, model/API calls, live configuration, private ingestion, core/provider
edits, Git operations or fleet activation occurred.

## Operational acceptance, exact scope

Final execution: **22 passed** (7 new operational cases, 15 unchanged runtime
cases). Receipts: `final-tests/pytest.receipt.json`, XML and stdout. The earlier
20-case pass and 22-case run with one incorrect exception expectation remain
preserved. The corrected probe keeps the same case ID and checks the actual
visible `ValueError`; no production code was changed to make it pass.

| Scenario | Executed control | Result / limit |
|---|---|---|
| Complete selected-memory snapshot | Close engine, stop all publishers, copy source library/all revisions, entire SQLite ledger, entire Lance directory and all approved model files; SHA-256 every file | Exact-byte copy verified |
| Same-home restore | Retain original, restore complete copy to original pathname | Source history, stats, active hits, withdrawn exclusion and idempotent receipt match |
| Portable-path restore | Restore to another directory, load copied model, open copied runtime/library | Same checks pass on this Ubuntu interpreter/dependency set; not cross-platform portability |
| Corrupt snapshot | Alter ledger after snapshot | Full-file manifest mismatch detected before restore; test harness comparison, not a deployed restore command |
| Correction | Explicit same-source ID upsert after owner-source update | Only newest indexed revision searchable; previous history retained |
| Withdrawal | Repeated withdrawal, close/reopen | Excluded on recall; ledger still contains original text, NOT physical deletion |
| CPU embedding outage | Inject exception during correction | Prior head unchanged, no indexed success; explicit retry succeeds once |
| Vector outage | Move complete vector store aside | Upsert and search fail visibly with Lance `ValueError` for limit zero; no success claim; restore vector store and retry returns original receipt |
| Model unavailable | Construct using missing model directory | Explicit failure, no network/fallback |
| Crash after real vector write | Child exits 23 after Lance write, before ledger commit, using real ONNX embeddings | Old head remains; orphan vector not returned; explicit retry commits revision 2, repeated retry idempotent |
| Disable/re-enable engine | Close twice, reject search, preserve all bytes, reopen | Reversible engine-level disable verified, not full host config rollback |

### Backup procedure and completeness boundary

The tests are an inspectable operational drill, **not a new production backup
API**. For a selected runtime use this procedure only after stopping every
writer, including library publishers and provider callbacks:

1. Record source/library/index/model roots, trusted scopes, approved source code
   hashes, model manifest hash and the actual interpreter/dependency versions.
2. Stop callbacks and close runtime clients. Do not copy a running SQLite ledger
   separately from changing Lance files. Library and index publication are not
   a joint transaction: quiescence must cover both.
3. Copy the whole owned source library (all revisions/provenance), complete
   runtime root (`control.sqlite3`, `vectors`, lock and any remaining journals),
   and approved model assets. Hash every copied file and verify exact coverage.
4. Keep the original. Restore into a new private root, verify coverage/hashes
   BEFORE opening it, then check model fingerprint, source histories, head
   counts, corrections, withdrawals, recall and repeat-upsert receipt.
5. For same-home cutover, retain/rename the original while stopped; restore the
   exact copy. Do not rewrite SQLite heads or Lance metadata by hand.

These tests establish **complete selected-memory-data restore**, not complete
installed Hermes-profile recovery. Native `MEMORY.md`, `USER.md`, `state.db`,
transcripts, selected provider configuration, approved plugin/package and
interpreter environment also belong in a deployment backup. Their joint
installed-plugin/host restoration is still a parent integration gate. Secrets
need their own secure owner-controlled backup; never ingest them into the index.
A copied model plus existing environment was tested; an offline rebuild from a
package lock/wheelhouse and a different OS/CPU/library version was NOT tested.
The manifest protects against accidental corruption, not malicious replacement
of both manifest and data. No concurrent snapshot, encryption, remote backup,
power-loss filesystem guarantee or automatic schedule is claimed.

### Correction, outage and retry policy

Only canonical approved records can determine the current fact. Map an owner
correction to the same stable source ID, re-index its exact new revision, inspect
`indexed=True` receipt, and verify current recall. A library linked correction
alone does not reconcile separate index records. Withdrawal hides a record from
retrieval but backups/history retain it; erasure requires separately authorised
retention work.

On unavailable/busy/error/invalid receipt, say **not memorised/indexed**, retain
the authoritative source, and retry explicitly after recovery with the same
source ID, text and provenance. Do not report a successful memory write merely
because a callback returned. The provider can reject `busy` and has no durable
queue; its capture hooks are off by default. Its additive turn key includes the
whole raw turn: a later correction is another record, not automatic fact
replacement. Automatic capture therefore cannot currently guarantee no lost
memorised facts or resolved contradictions. A user-visible explicit-remember
transaction/retry integration is missing. This is not fixed by a backup helper.

Engine shutdown is reversible and keeps state. Full live disable should switch
back to native through approved Hermes configuration, stop old callback workers,
retain data, and verify a fresh native session before re-enable. This assessment
did not change live settings and does not claim that host-level sequence passed.
The accepted bridge's publication lock is not a full host prompt-dispatch
transaction; that existing boundary is untouched.

## Predeclared value and no-answer evaluation

New workload: 48 synthetic registers; 24 positive retrieval cases and 12
no-requested-affirmative-fact cases. Four exact recovery reference values per
positive total **3,072 characters before entity labels**, exceeding the default
2,200-character operational notebook. Actual native `MemoryStore` compacted
facts (entity + four values, no prose) retained 15/24; session archive held all
48. The 1,375-character USER budget is for stable user facts, not another
project-record database. This workload is deliberately register-heavy and not
a representative sample of private conversations.

Separate calibration: 8 other-domain registers, 8 positive and 8 no-answer
queries. Before model execution the declared rule was
`min(1.0, max(calibration negative top1 score) + 0.01)`. The resulting threshold
**0.7395172810554504** was frozen before held-out indexing/evaluation. No retuning
occurred. Runtime head/hash/revision checks remain in place. Scores certify
similarity, not entailment. This threshold was NOT installed in the provider;
the accepted provider still uses 0.25 (all 36 new queries have candidates at that
level).

| Source-retrieval method | Positive top1 / top5 (24) | No-answer candidate returns (12) | Median lookup |
|---|---:|---:|---:|
| Native SessionDB, natural wording | 0 / 0 | 6 | 0.198 ms |
| Native SessionDB, predeclared entity-key assistance | 24 / 24 | 6 | 0.217 ms |
| Enhanced Cognee, raw ranking | 23 / 24 | 12 | 41.601 ms |
| Enhanced Cognee, separately calibrated | 23 / 24 | 1 | 41.601 ms |

Calibration retained 8/8 positives and returned 0/8 negative candidates. Holdout
retained 24/24 top5 positives but returned one above-threshold candidate for
`absent-field-1` (Kestrel fuel specification, score 0.7486951351165771). The
predeclared zero-no-answer-candidate gate therefore **fails**; it was not relaxed.
Six negative cases name absent entities, six request an unrecorded field. The
registers explicitly say no fuel specification is recorded: returning such a
source may help an agent abstain. Neither this one return nor the six native
returns establish a fabricated AI answer. Labels concern retrieval candidates
without the requested affirmative fact, not end-to-end answer correctness.

The natural SessionDB queries were actual full questions and returned no
positive source; entity-key reformulation was specified in advance and recovered
all of them. That assisted native baseline is essential: comparing only natural
queries would overstate the optional index's value. A full agent could formulate
more queries or refuse on absent fields; no model answers were evaluated here.
Native baseline context-character fields are zero because the default search
projection omits full content; do not interpret them as zero prompt overhead.

Cost observations, not fleet envelopes: CPU model initialisation 0.727 s,
48-record ingest 5.019 s, 20-repeat warm median lookup 43.503 ms. Enhanced process
peak RSS 412.305 MiB versus native benchmark 62.715 MiB. Approved model assets
133,903,215 bytes; both calibration/holdout runtime roots together 469,139 bytes.
Median raw/selected source text returned: 1,604 / 1,602 characters, before JSON
and provenance wrappers. These are single-machine process measurements, not
sustained load or whole-agent response latency.

## Preserve negative evidence and avoid duplicate authority

Original frozen comparison remains unchanged: 22 cases, 139 records, 18 positive
facts totalling 1,624 characters (fits native notebook); both unthresholded
methods returned candidates for all four no-answer queries. That experiment
never justified a universal benefit claim.

This experiment intentionally stores 48 quotes in native sessions and in a
separate derived SQLite/Lance index for identical-source comparison. That is
physical duplication, not two authoritative owners. The runtime ledger retains
texts and historical/withdrawn revisions, plus derived vector files. Do not
promise zero duplication, automatic source synchronisation or physical erasure.
Keep canonical owner records, native essential facts and archived sessions;
index only explicitly approved sources, with provenance and no competing writer.

Protected hash checks: 23 assessment-before files unchanged; accepted manifest
11/11 and immutable evidence/source manifest 277/277 match. Provider source is
still `2adc216f13d68b8fee06795429101e39d5f0fbd1d66df51daa7f85b237b30cc8`.

## Missing gates and recommendation

- Independent parent review of these new test/doc/evidence artifacts.
- Installed-plugin/full-host backup, disable/re-enable and fresh-session tests.
- Explicit remember + visible failure/retry semantics; no capture-loss promise
  until the native host-facing path is integrated and exercised.
- Canonical correction/withdrawal publication into derived index; raw turn
  capture is not a fact-resolution system.
- An owner-approved realistic workload showing benefit beyond assisted native
  session search, with source-specific abstention and provenance checks. The
  separately calibrated scalar threshold did not meet its held-out refusal gate.
- Separate owner scope for any private source/automatic capture activation.

**Recommendation:** keep automatic capture off and native authority intact. Do
not add a service/queue or replace native memory on this evidence. The index can
reduce natural-query reformulation for larger approved records, but the measured
cost and absence of superiority over assisted native retrieval do not establish
a deployment win. No component outside this assessment was repaired/promoted.
