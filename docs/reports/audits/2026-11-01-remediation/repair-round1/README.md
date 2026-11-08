# Repair cycle 1 evidence

Scope: independent review R1/R2/R3 and the reported installed-inventory ambiguity.
This is offline source/unit-test evidence, not installation or qualification.
No commits, pushes, installs, live APIs, models, credentials or services were used.
Root checks use synthetic metadata over real sandbox symlinks; subprocess and
systemctl paths in the new tests are no-launch doubles. Profile files and tokens
are invented sandbox fixtures only.

## Changes

- R1: check both OS/provisioner interpreter lexical parent chains, in addition to
  resolved targets and pyvenv.cfg. A writable runtime/bin is refused before any
  subprocess. Existing protected-root positive controls still pass.
- R2: api() accepts JSON objects only; empty/null/array/boolean/number/string
  responses receive fixed sanitized errors and isError through serve(). Malformed
  JSON/encoding never echoes its body; valid objects retain their payloads.
- R3: preserve positive integer expiry policy while rejecting timestamps after
  9999-12-31T23:59:59Z and platform-unrepresentable UTC values. Loading, decoding
  and formatting are inside the per-profile boundary. Invalid/unreadable expiry
  retains the existing renew policy, after trusted-runtime/inventory validation.
  Continuation tests verify later profiles, published state, skipped membership,
  failure receipts, and absence of token/exception-value disclosure.
- Inventory: apply approved_predecessor to an existing roles.json before any
  writes or subprocesses, including systemctl. Unknown bytes fail closed; absent
  and byte-exact inventories pass. roles.json was NOT added to PREDECESSORS.

## Test-first evidence

Each initial-*-tests.py snapshot was copied before that fix, followed by its RED
run, the scoped source change, and its GREEN run. Snapshots preserve test bytes;
run tests at tests/unit/test_review_round1_remediation.py so its portable REPO
locator resolves the checkout. Historical reviewer inputs remain unchanged.

| Slice | Selector | RED | GREEN |
| --- | --- | --- | --- |
| R1 | whole initial file | 3 failed, 2 passed | 5 passed |
| R2 | -k mcp | 9 failed, 4 passed, 5 deselected | 13 passed, 5 deselected |
| R3 | -k 'r3 or unrepresentable' | 10 failed, 7 passed, 18 deselected | 17 passed, 18 deselected |
| Inventory | -k inventory | 1 failed, 2 passed, 35 deselected | 3 passed, 35 deselected |

All slice commands use this prefix from the repository root:

```text
../.venv-deployment/bin/python -B -m pytest --confcutdir=tests/unit -p no:cacheprovider tests/unit/test_review_round1_remediation.py
```

Append the selector above and -q. Each command's complete output is retained in
<slice>-red.txt or <slice>-green.txt. RED exits were 1; GREEN exits were 0.

Final regression run: the unchanged 13-file audit suite (149 cases) plus the new
38-case file: **187 passed in 4.82s**, exit 0, no skips/errors/warnings reported.
See regressions-green.txt/.xml and commands.json for exact arguments.
The preserved independent v2 suite, excluding only its obsolete R3 precondition:
**13 passed, 1 deselected in 0.17s**, exit 0. See independent-unchanged-green.*.

## R3 reviewer mapping

The preserved review-round1/test_independent_challenges_v2.py lines 174-194 are
copied into the new regression under the same function name. Its line 178
asserted the old defect, decode_exp(token) == 10**100. Only that precondition is
replaced by pytest.raises(ValueError); all subsequent continuation assertions
are retained verbatim. The original reviewer file is unchanged. A separate
parameterized main/state test covers huge expiry, invalid Unicode, token-load
failure, UTC-formatting failure, and malformed token, with a later successful
renewal and a later valid skipped profile.

preservation-check.json records a byte-level verification of that exact mapping,
all 29 rejected ZIP entries against the original source manifest, and original
reviewer inputs against their preserved scratch originals. Exactly the three
assigned source paths differ from the rejected ZIP; all 13 existing test files
and all other archived sources match. repair-vs-rejected.patch isolates this
cycle's source changes. The original source-manifest.json and owner hash list
were not changed; the parent owns any new versioned delivery manifest.

## Remaining limits

Independent re-review is still required. This cycle does not establish installed
root ownership, installed runtime dependency availability, service/timer state,
credential renewal, real API/model behavior, or live fleet qualification. No such
checks were attempted. All pre-existing acceptance/owner-host restrictions remain.
