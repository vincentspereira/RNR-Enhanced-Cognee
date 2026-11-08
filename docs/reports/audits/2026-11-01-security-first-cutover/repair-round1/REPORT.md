# Security-first stage-only helper repair, cycle 1

Status: repaired source prepared for fresh independent review. Not accepted,
installed, activated or promoted. Route OFF remains settled; no new owner consent
was requested. No owner bootstrap or activation commands were authored.

## Source freeze and scope

Worktree:
`/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101`

Branch: `codex/enhanced-cognee-security-first-cutover-20261101`

HEAD: `41e4de7a5db99970a7629ef3f274138eef3031e8`

Only production edit:
`integrations/hermes/deployment/prepare_security_first_cutover.py`

- Rejected SHA-256:
  `cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813`
- Repaired SHA-256:
  `d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63`

New test:
`tests/unit/test_security_first_cutover_review_regressions.py`

- RED and GREEN use identical test bytes, SHA-256:
  `27fcf6efdab49c8dec979c0804a7568c4010706374ea4343047034d59e8b3bb0`

All other new files and synthetic sandboxes are under this `repair-round1/`
evidence directory. No original reviewer evidence or test inputs were edited.

Original test remains byte-exact:
`tests/unit/test_security_first_cutover.py`

- SHA-256:
  `4c75858260829750aacb4e659b98a6fac698af88b99dbecb01c8e79683b61777`

Original reviewer challenge remains byte-exact:
`../review-round1/test_independent_challenges.py`

- SHA-256:
  `549b332ca4b469ed17101f9e4e1fc4341bd49551ce82ab38fd569d53a78af12f`

The parent immutable `parent/round1-source.zip` hash was rechecked, unchanged:
`ff21c524ac91e1fdb426de8c7c4c2ec4533c94bc554252282bf0efedd495196b`.

## Two fixes, three reproductions

1. S01: the alias target's directory components are now validated in lexical
   order before a following `..` can erase a previously traversed directory.
   Each directory uses the existing no-alias owner/group/mode/type/link guard.
   The real `bridge/../python3.12` challenge now raises exactly
   `Refusal("unsafe_path_link")` before interpreter fingerprinting. Safe simple
   relative leaf aliases still pass the unchanged four-case alias tests. The
   existing alias allowlist, lexical path checks and root trust were not widened.
2. L01/L02: the eight module reads now use exactly
   `CANDIDATE/runtime/lib/python3.12/site-packages/` plus each existing logical
   `src/...` identifier. Logical identifiers and embedded hash pins are unchanged.
   L01's exact mapped reader passes. L02's matching candidate-root decoys cannot
   authorize differing installed modules: plan validation raises exactly
   `Refusal("inventory_or_loaded_or_candidate_drift")`.

`source-repair.patch` contains the entire minimal production diff. AST comparison
in `static-review.json` confirms only `trusted_path` and `collect_snapshot`
changed; imports and every module-level assignment are unchanged. Added source
lines passed the bounded static scan. Authored source is ASCII, parses, and has
no trailing whitespace. The Git diff check also returned 0, but these files are
untracked, so the explicit preserved-baseline diff is the meaningful comparison.

## RED/GREEN process receipts

Each row has complete `process.log`, `junit.xml`, and `process-receipt.json` in
its named directory. Receipts contain actual argv, imported source/test bindings,
process exit code, complete case records, and output hashes. No output truncator
was used. Every pytest run used the deployment Python with `-B`,
`-m pytest --confcutdir=tests/unit -p no:cacheprovider`, a unique nonexistent
`--basetemp`, and actual plugin autoload (anyio and asyncio were loaded).

| Directory | Passed | Failed | Errors | Skips | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| red-regressions | 0 | 3 | 0 | 0 | 1 |
| green-S01 | 5 | 0 | 0 | 0 | 0 |
| green-regressions | 3 | 0 | 0 | 0 | 0 |
| original-current-source | 122 | 1 | 0 | 0 | 1 |
| reviewer-obsolete-fixture | 48 | 2 | 0 | 0 | 1 |
| green-current-inventory | 176 | 0 | 0 | 0 | 0 |

RED was captured before implementation. Its three failures reproduce the actual
S01 wrong-interpreter fingerprint and L01/L02 module-binding defects, not setup
errors. S01 was repaired and tested first (its regression plus four old alias
cases), then the single L01/L02 path correction was applied.

Final inventory: 123 copied original cases + all 50 reviewer logical cases +
three new regression implementations = 176 executions. The three regressions
repeat the three reviewer contracts; do not call these 176 distinct historical
logical cases. All 173 historical logical cases are mapped one-to-one; no reviewer
case was deselected, skipped or silently dropped. This is repair replay, not a
fresh independent review.

## Exact copied-harness transformations

Copies preserve every original assertion. Their ONLY on-disk body changes are:

1. `copied-original-cases.py`: in
   `test_snapshot_collection_reads_only_units_helper_modules_interpreter`, replace
   `h.CANDIDATE + "/" + p` with
   `h.CANDIDATE + "/runtime/lib/python3.12/site-packages/" + p`
   in the fixture content dictionary. All assertions, including exact read set,
   read count, candidate hashes and interpreter/helper fingerprints, are intact.
   Copy SHA-256:
   `1d32c2528b1f860f5ae495f3606e7496c720fba463f5ae617345b23f65c1f213`.
2. `copied-review-cases.py`: ONLY inside
   `test_C01_snapshot_rechecks_both_manager_views`, replace
   `exact_content(snap, installed=False)` with
   `exact_content(snap, installed=True)`. This supplies the eight admitted bytes
   where the repaired collector reads them. Both `[inventory]` and `[loaded]`
   retain the exact `snapshot_changed` refusal assertion.
   Copy SHA-256:
   `834dcdd7fabe479fceb6909e79dcbe446f6af5347df753cf3b6a2dfb70649f39`.

`copy-transformations.json` and the two `.patch` files record the exact byte
changes. The obsolete fixture receipts above remain preserved: the original
collector fixture fails with a KeyError for the installed `src/ingestion.py`
path, and the two C01 cases fail for the same stale fixture mapping before they
can reach their manager-view assertions. These are fixture bindings, not newly
ignored source defects; L01's independent positive and L02's decoy negative
prove the corrected production behavior separately.

Executable collection wrappers:

- `test_current_original_cases.py` compiles the copied original body with the
  original `__file__` binding, preserving its existing ROOT/HELPER calculation,
  then restores the real wrapper filename. It pins copied bytes and source hash.
- `test_current_review_cases.py` similarly preserves ROOT, rebinds only the old
  source PIN in memory to the exact repaired hash, and redirects new diagnostics
  to this repair directory. For S01 and L02, it calls the unchanged historical
  probe bodies under exact-reason `pytest.raises` assertions. Those probes used
  historical false-PASS assertions after `plan_from_snapshot`; correct early
  refusal now prevents those obsolete final assertions from being reached.
  Neither original input nor copied assertion body is weakened or removed.
- The new three-case unit test likewise verifies the immutable original reviewer
  input hash, rebinds source PIN/output only in memory, and calls its unchanged
  probe bodies. L01 is used without an outcome adapter; S01/L02 require the same
  exact refusal reasons as the 50-case wrapper.

`case-reconciliation.json` gives every original node ID, obsolete replay node ID,
corrected node ID, old/current outcome and transformation, plus the three RED to
GREEN regression mappings. `reconcile_receipts.py` verified all identities,
counts, original hashes and complete process log/JUnit hashes in code.
`final-source-test-hashes.json` contains exact hashes for both wrappers, both
copied bodies, the runner, reconciler, source and original/new test inputs.

## Replay inventory for the parent

Select these three files explicitly against the frozen helper:

- `docs/reports/audits/2026-11-01-security-first-cutover/repair-round1/test_current_original_cases.py`
- `docs/reports/audits/2026-11-01-security-first-cutover/repair-round1/test_current_review_cases.py`
- `tests/unit/test_security_first_cutover_review_regressions.py`

The reviewer wrapper's diagnostic directory is exclusive and already exists from
this run. For a later replay, use a NEW copied wrapper/output binding under the
reviewer's own authorized output boundary; do not delete or overwrite existing
evidence. Preserve its source/input pins and all assertions. The original tests
and copied bodies are inputs, not alternative inventories to glob together.

## Limits and remaining gate

All execution was ordinary-user offline synthetic testing. No root command,
service command, protected write, restart/reload, API/model/network call,
qualification rerun, credential/private JSON/.env read, profile/fleet edit,
installation, deletion, commit or push occurred. Public accepted repository
module bytes were hashed but no application module was imported. Local receipt
parsers consume only the preserved local pytest-generated JUnit files; XML static
scanner warnings do not imply an external XML input interface. Editor Pyright
cannot resolve pytest/dynamically compiled module names in its own environment;
real prescribed-interpreter runs had zero collection/setup errors.

Fresh independent exact-hash review remains required. Owner-root preparation,
activation, route review and runtime readiness remain separate parent/owner gates.
No installed-host or current service-state verification was attempted in this
repair; the prior reported old active API was not touched.
