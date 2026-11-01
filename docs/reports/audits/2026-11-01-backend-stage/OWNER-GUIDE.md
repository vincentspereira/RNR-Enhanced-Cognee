# Backend candidate owner guide - STAGING ONLY

Status: source preparation for independent review, not deployment or activation
approval. Base source: `c14f595ccd53f432b455b16f116765d9aa6c9a14`.
No privileged staging command was executed during preparation.

## Fixed scope

- Original, immutable candidate:
  `/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529`
- New candidate, which MUST NOT already exist:
  `/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101`
- Owner-prepared protected input bundle:
  `/opt/enhanced-cognee-memory/staging/audit-c14f595c-20261101`
- Only the original `runtime/` is cloned. No sibling model-cache, artifacts,
  credential-cycle, operator directories, private configuration or profiles are
  copied. The sole supported runtime link is `lib64 -> lib`.
- Exactly eight reviewed source overlays are permitted, including the new
  `src/llm_budget.py` only when that source file is absent in the original.
  See `audit_backend_payload.json` for exact paths and old/new SHA-256 bindings.
  All eight source files must match the fixed c14 commit without edits.

This helper has no path, profile, environment-file or manifest-location options.
It does not create a budget ledger, write `/etc`, issue credentials, install pip
packages, rebuild dependencies, call a model/API, modify services, reload systemd,
restart anything or promote a candidate. It never imports application modules.
It parses the eight files as AST data only. Existing protected transitive
runtime dependencies are reused byte-for-byte.

## Review before root execution

1. Obtain a fresh independent review of the helper, manifest, unit test and this
   guide. Bind acceptance to the current exact file hashes in `DELIVERY.json`,
   not to a prior helper snapshot in a RED/GREEN evidence folder. Source tests
   are not installed-host acceptance. Do not execute an unreviewed helper as root.
2. The OWNER, in a trusted root terminal, must prepare a NEW protected bundle at
   the exact bundle path above using trusted OS file-copy tools, not this helper
   and not a checkout-supplied installer. Do not reuse or overwrite an existing
   bundle. Independently inspect its lexical ancestor chain: root:root,
   directories 0755 (no writable ACL grants), no alias/symlink directories.
   The original and candidate-parent chains must also meet these conditions.
3. Copy only these ten regular, single-link files, preserving their indicated
   relative names in the new bundle:
   - `stage_audit_backend.py` from `integrations/hermes/deployment/`
   - `audit_backend_payload.json` from `integrations/hermes/deployment/`
   - the eight `src/...` files named in the manifest from the c14 source tree
   Use root:root 0644 files and root:root 0755 directories, including `src/` and
   `src/security/`. No archive extraction, symlink following or recursive checkout
   copy. Do not copy Git hooks, sitecustomize, .pth files, model caches or configs.
4. AFTER copying, independently SHA-256-check the protected helper and manifest
   against the accepted `DELIVERY.json` values. SHA-256-check all eight protected
   source copies against each `new_sha256` in the accepted manifest. Do not trust
   a manifest substituted from the writable checkout as the authority for those
   hashes. Compare the copied manifest byte hash first. Abort on any mismatch.
   A copy from a mutable source is not trusted until this post-copy check passes.
5. Confirm the fixed destination is completely absent, including dangling links,
   and the protected runtime is not being changed by another root operator.
   The helper rejects pre-existing candidates and cannot resume a partial copy.
   It requires root ownership, no group/other writes, no special mode bits,
   no hardlinked regular files, no unsupported links or special files, no .pth
   startup files and the discovered exact Python 3.12.13 venv configuration.
   Do not relax these checks or repair the immutable original to make them pass.

Only AFTER independent review and those OWNER checks, the owner may separately
choose to execute this STAGING command (not run by the preparing agent):

```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/staging/audit-c14f595c-20261101/stage_audit_backend.py --stage
```

Use the OS interpreter exactly as shown, not runtime Python, a shell launcher,
venv activation, user Python, PYTHONPATH or a writable checkout script. `-I -S -B`
prevents caller import-path/site startup and bytecode writes. The helper checks
its own protected location and both lexical and resolved interpreter trust;
these checks do not make it safe to start arbitrary untrusted Python as root.
The owner command itself must be trusted before Python starts.

## Completion and failure interpretation

Success is exit 0, a read-back-verified `COMPLETE.json`, and matching candidate
bytes/modes. The marker records helper and manifest hashes, old/new overlay
provenance, original/candidate runtime inventory digests and an entry count.
It MUST say:

```json
{
  "complete": true,
  "activated": false,
  "services_restarted": false,
  "credentials_issued": 0,
  "ledger_created": false,
  "wheel_metadata_rebuilt": false
}
```

The helper retains `INCOMPLETE.json` as the initial journal even on success;
`COMPLETE.json` plus its matching verified result is the completion proof, not
absence of that initial journal. A partial directory, initial marker,
`COMPLETE.pending`, or `COMPLETE.failed` is NOT a completed candidate. Filesystem
failure before the initial marker can leave only a partial directory. Treat any
such directory without a verified completion receipt as incomplete. Preserve it
for owner review. Do not delete it, retry into it, overwrite it, change the fixed
destination or modify the old candidate to make a retry work. No automatic cleanup
is implemented. If final marker readback fails, its bytes are retained as
`COMPLETE.failed` when the filesystem permits that preservation.

Only stale `.pyc`/`.pyo` caches belonging to the eight overlaid modules are omitted
from the new clone; the original caches remain untouched. Other dependency bytes
and modes are preserved. These are source overlays on an existing runtime, NOT a
newly built wheel. Original wheel metadata/RECORD still describe the old wheel.
Do not advertise a reproducible new wheel, new dependency qualification, or an
installed application test. Copied venv activation scripts and console-script
shebangs can still name the original venv. They are not relocation proof and
must not be used to infer the active candidate.

## Read-only ordinary-agent inspection

No root bundle is needed for this bounded check of the original runtime:

```bash
/usr/bin/python3 -I -S -B integrations/hermes/deployment/stage_audit_backend.py --inspect-runtime
```

It validates the runtime's protected layout, exact old file hashes and absent new
source module, and returns only a runtime entry count and inventory digest.
It reads no profile or private service configs, creates no candidate and executes
no application code. It is NOT a live API/model or memory qualification.
Preparation actually ran this at UID 1000; see `runtime-inspection*.json`.

## Separate future owner phase - NOT approved by this guide

Current service facts are supplied discovery evidence: API identity
`enhanced-cognee-api:enhanced-cognee-api`, old-candidate WorkingDirectory, command
using the old `runtime/bin/python -m src.memory_daemon api`, and drop-ins
`10-protected-stores`, `20-launch-runtime`, `30-llm`. No StateDirectory is configured.
None of those service files were opened or modified by this helper.

A future reviewed plan must provision and protect a persistent budget ledger
under the correct service identity and separately reconcile configuration,
StateDirectory, Python prefix/import behavior and launch paths. There is no
activation command here. An eventual single API restart will briefly interrupt
memory access; schedule and approve that interruption separately. Keep the
immutable old runtime as rollback evidence. Activation and rollback must not
rewrite that runtime or pretend reverting binaries reverts budget accounting.

OPEN: the current UTC day's legacy volatile budget accounting cannot be assumed
migrated. A new empty ledger does NOT establish that spending already incurred
has been carried forward. Define cutover accounting and reservations before any
activation. Also OPEN: encrypted backup and restoration/recovery of the new
ledger together with the relevant service data, including rollback and
failure-recovery behavior. No empty ledger was created here and neither open
issue is solved by candidate staging.

Live service/model checks, credential policy, recovery qualification and promotion
remain separate gates. Do not rerun historical native/memory qualification as a
substitute for those future scoped decisions.

## Offline verification recipe and evidence

Only the new test file was exercised:

```bash
../.venv-deployment/bin/python -B -m pytest --confcutdir=tests/unit tests/unit/test_backend_stage_audit.py -q
```

Use `run_tdd.py <new-label>` to retain a new immutable evidence directory containing
source/test snapshots, the exact command/exit receipt, complete output and JUnit.
Never reuse an evidence label. Tests use small real filesystem fixtures with
explicitly rebound fixture hashes, synthetic root ownership/ancestor stat and
no-launch fault doubles. They prove helper behavior under those conditions, not
real root privilege isolation, a copied full runtime boot, power-loss durability,
service activation or persistent-ledger recovery. Exclusive owner operation is
required; hostile/concurrent root writers and mount-namespace changes are outside
this stage helper's threat model. Directory fsync/power-failure recovery is not a
claimed acceptance criterion. Never run this fixture suite as root.
