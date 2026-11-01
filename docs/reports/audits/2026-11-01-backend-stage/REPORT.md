# Stage-only backend preparation report

## Outcome and scope

Prepared a fixed-target stdlib staging helper, exact eight-file payload manifest,
new offline unit suite and owner guide. No commit, push, root command, protected
write, application import, service operation, API/model call, credential operation
or historical qualification was performed. No ledger or candidate was created.
All existing tracked source, helpers and tests remain unchanged at base
`c14f595ccd53f432b455b16f116765d9aa6c9a14` on branch
`codex/enhanced-cognee-backend-stage-20261101`.

Primary review files:

- `integrations/hermes/deployment/stage_audit_backend.py`
- `integrations/hermes/deployment/audit_backend_payload.json`
- `tests/unit/test_backend_stage_audit.py`
- `docs/reports/audits/2026-11-01-backend-stage/OWNER-GUIDE.md`

The helper copies only the existing protected runtime into the fixed NEW
candidate, overlays the eight bound source files, omits stale bytecode for those
modules, checks copied hashes/modes/AST, and records overlay provenance without
claiming a wheel rebuild. Root execution requires an owner-hashchecked protected
bundle and OS Python with `-I -S -B`. Partial candidates are preserved and never
reused. Success explicitly leaves activation, service restarts, credentials and
ledger creation false/zero. The separate bounded inspection mode is read-only.

## Verified results

- Final offline run: 58 distinct cases passed, zero failures, errors or skips.
  `final-offline/receipt.json` contains the exact interpreter, pytest command,
  working directory, return code and current source/test SHA-256 bindings.
  `final-offline/junit.xml` and `output.txt` contain the complete result.
- Seven old installed-file hashes and the new module's absence match the supplied
  discovery proof. All literal hash formats were checked before the provenance
  file lookups. All eight desired source files equal `git show c14:<path>`, their
  manifest new hashes match, and all eight parse as AST. See
  `source-provenance.json`. No application code was executed.
- Actual ordinary UID 1000, OS-Python read-only inspection succeeded. It validated
  7,235 runtime entries and inventory SHA-256
  `55897401aad689f945b96d0e9e56b17ee2165eb9567d2cce84347f0ac32b2926`.
  Earlier and final inspections have the same runtime digest. See
  `runtime-inspection.json` and `runtime-inspection-final.json` (the latter binds
  the final helper hash). The protected candidate destination remains absent.
- AST/static checks passed: stdlib-only helper imports, no eval/exec/compile,
  subprocess or OS-shell calls, ASCII authored files, no trailing whitespace.
  Observed original overlay modes are all 0644. See `static-checks.json`.
  Ruff was not installed in the OS or test interpreter; no package was installed.
- `git diff --check` passed, index remains empty, and tracked diff is empty.
  Untracked additions are confined to the three new primary source/test files
  and this new report directory. No existing source/helpers/tests were edited.

## TDD evidence

Each feature/fix was preceded by an executed failing test and followed by the
complete new suite. The corresponding directories retain source/test snapshots,
exact commands, full output, JUnit and return-code receipts; old evidence was not
rewritten. Additional adversarial coverage that already passed is not described
as a newly discovered defect. `test-reconciliation.json` programmatically counts
the receipts and does not count replays as extra distinct cases.

| Cycle | Executed RED | Accepted GREEN | Behavior |
| --- | --- | --- | --- |
| 01 | `01-red-final` | `01-green` | Initial c14 payload loading/binding |
| 02 | `02-red` | `02-green` | Closed manifest, duplicate keys, exact paths/fields/hashes |
| 03 | `03-red` | `03-green-corrected` | Protected runtime/payload preflight |
| 04 | `04-red` | `04-green` | Exclusive new clone, immutable original, honest result |
| 05 | `05-red` | `05-green` | Reject .pth, privileged modes and private runtime dirs |
| 06 | `06-red` | `06-green` | Omit stale overlay bytecode without deleting old caches |
| 07 | `07-red` | `07-green` | Bounded read-only CLI and no caller-selected paths |
| 08 | `08-red` | `08-green` | Final completion-marker readback and preserved failed marker |

Coverage also includes wrong old/source hashes; new source already present;
writable runtime/bundle/interpreter parents; wrong owner; real file hardlinks;
source and directory symlink escapes; lexical interpreter aliases even with a
protected resolved target; bad lib64; FIFO; changed pyvenv config; all existing
destination shapes; injected clone I/O failure; real cloned-file and final-marker
tampering; partial preservation/refused reuse; no subprocess/network/services or
private-path opens; and no ledger. The preflight and root-trust attack fixtures
first exercise their positive preflight/trust controls. Root ownership/above-fixture ancestor metadata
and root launch conditions are synthetic; actual file operations use small real
filesystem trees, never the protected destination.

### Preserved harness corrections, not hidden successes

- The initial `01-red` runner attempt used the wrong report-to-repository parent
  depth and failed before pytest started. Its directory is retained. The runner
  was corrected from `parents[5]` to `parents[4]`; no production code existed.
- `01-red-corrected` put the expected missing-helper assertion in fixture setup,
  producing a setup error. The same test ID `test_exact_c14_payload` was changed
  to assert missing behavior in the test body, yielding the genuine failed case
  in `01-red-final` before implementation. Count that case once in the final suite.
- The first `03-green` exposed fixture files inheriting group-writable modes.
  The root-ownership double did not and should not mask those modes. The fixture
  now explicitly creates safe 0644 files, leaving all deliberate unsafe mutations
  intact. `03-green-corrected` passes the unchanged test IDs with no source change.
- Final verification strengthens cloned-file tampering from a read-result double
  to an actual on-disk fixture mutation. The unchanged helper rejects it and the
  final suite remains green. Earlier receipts remain historical, not final hashes.

## Limitations and next gate

This is prepared source awaiting fresh independent parent review. It is not
root staging, runtime boot, live memory/model qualification, install approval,
promotion or operational acceptance. The suite cannot establish real root
isolation from synthetic ownership, full cloned-runtime operation, hostile root
concurrency/mount changes or power-loss durability. Root owns the fixed paths;
only a separate owner operation may stage the protected bundle and candidate.

The original wheel metadata intentionally remains old; copied activation scripts
and entry-point shebangs are not relocation evidence. Preserve the old runtime.
Future service changes, protected StateDirectory/ledger provisioning, cutover
accounting for the current UTC day's legacy volatile budget and backup/new-ledger
recovery remain OPEN. An empty ledger would not migrate prior spending. A future
single API restart would briefly interrupt memory and needs separate approval.
There is deliberately no activation command in the guide.

No reusable skill/profile files were modified because this task's explicit write
scope permits only the new helper/manifest/test/report paths. The retained
`run_tdd.py` and owner guide document the reproducible local workflow instead.
