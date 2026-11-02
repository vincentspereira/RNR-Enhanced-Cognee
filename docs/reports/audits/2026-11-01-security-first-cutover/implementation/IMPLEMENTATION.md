# Security-first stage-only cutover helper implementation

## Outcome

Implemented a standalone 405-line, stdlib-only helper. No service was activated,
reloaded, restarted or installed. No root command was executed. No credential
file contents or raw profiles were read. Application modules are hashed as bytes,
never imported by the helper. No API, authentication or model call was made. Existing tracked files
are unchanged; all deliverables are new files in the authorized scope.

Repository:
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101

Accepted base: 41e4de7a5db99970a7629ef3f274138eef3031e8
Branch: codex/enhanced-cognee-security-first-cutover-20261101

## New source and hashes

- integrations/hermes/deployment/prepare_security_first_cutover.py
  SHA256 cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813
- tests/unit/test_security_first_cutover.py
  SHA256 4c75858260829750aacb4e659b98a6fac698af88b99dbecb01c8e79683b61777
- This implementation directory contains the evidence runners, sanitized receipts,
  separate RED/GREEN logs and JUnit, this report, and preserved invented sandboxes.
  artifact_hashes.json records source sizes/hashes; created_paths.json enumerates
  exact absolute artifact paths, types and hashes without following symlinks/FIFOs.

## Helper contract (not an installation authorization)

The only CLI forms are --plan and
--prepare --expected-plan-sha256 <the exact lowercase 64-hex plan digest>.
There is no installer, activation command, path override or safety bypass flag.

The intended separately protected helper path is:
/opt/enhanced-cognee-memory/security-first-helper/prepare_security_first_cutover.py

It requires root UID/GID, /usr/bin/python3 with -I -S -B, a fixed protected
installation path, root-owned interpreter/helper/ancestor chains, no writable
ancestors, regular single-link input files, and trusted interpreter leaf aliases.
The candidate interpreter must resolve to its fixed regular binary or a protected
/usr/bin/python3[.N] target and have execute permission. Arbitrary alias targets
are rejected before reading any file, including credential paths.

The output parent /opt/enhanced-cognee-memory/cutover must already exist as a
root:root 0700 directory; the helper does not provision it. The fixed new bundle
is /opt/enhanced-cognee-memory/cutover/security-first-c14f595c-20261101.
Only these new files are created, 0600 inside a new 0700 bundle:

- 40-audit-security-first.conf
- manifest.json (canonical, sanitized approved plan)
- receipt.json (last; complete artifact receipt, not deployment proof)

The writer uses exclusive/no-follow creation, fsync, and exact byte readback.
Existing targets and partial targets are never overwritten or removed. Failures
retain partial artifacts. A final fsync error may leave a complete-looking receipt;
treat the process exit status and successful receipt output as required evidence,
not the mere presence of receipt.json.

--plan creates nothing. Preparation rederives the plan twice, compares the exact
approved hash, and repeats runtime/output preflight before the first write. All
errors cross the CLI as one fixed ASCII message, never exception text or arguments.
This is not an atomic freeze against a concurrently acting privileged operator.

## Bindings and fail-closed inputs

The plan binds all four static unit source hashes (including the unknown
20-launch-runtime.conf hash learned only by an eventual owner-root plan), selected
loaded properties, helper bytes, startup interpreter identity/hash, eight embedded
accepted candidate payload hashes, and proposed drop-in bytes. Embedded payload
hashes exactly match integrations/hermes/deployment/audit_backend_payload.json;
no writable sibling input is read by the CLI.

Only systemctl show is called, using a fixed binary, no shell, a fixed minimal
environment, no pager, selected properties and a timeout. Environment and
credential-value properties are never requested. Exact unit-manager search paths,
static sources, loaded fragment/drop-ins/names and NeedDaemonReload are checked.
Runtime, generic type-wide and prefix drop-ins are refused. The parser rejects
continuations, escapes, resets/duplicates except the specifically required old
ExecStart reset, conflicting credential mechanisms, unknown directives and unsafe
Environment inputs without copying their values into a plan or error.

The unreadable runtime drop-in is NOT guessed or pinned to invented bytes. Its
supported subset is one [Service] section with the known old User/Group,
WorkingDirectory, reset/ExecStart and at most one Environment line consisting only
of the helper's explicit nonsecret SAFE_ENV assignments. A legitimate different
shape will fail closed and needs separate review, not a bypass. No new credential
binding in that source is permitted. The combined static inventory must be exactly
api.json, index.json and llm.json, with the three exact known source bindings.

The proposed new drop-in sets the new WorkingDirectory and an ExecStart reset
followed by the new candidate's runtime/bin/python -I -B -m src.memory_daemon api.
It resets LoadCredential and restores ONLY the exact api.json and index.json
bindings. It omits llm.json and StateDirectory. Original credentials and the LLM
key file remain untouched. There is no ledger creation or model-usage reset.

Every plan/prepare result explicitly reports activated=false,
services_restarted=false, ledger_created=false, credentials_issued=0,
model_analysis_expected_enabled=false, installation_pending=true and
model_usage_reset=false. These are stage-only facts/proposed expectations, not
claims about deployed service behavior.

## Verification and retained failures

Exact required pytest prefix:
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B -m pytest --confcutdir=tests/unit -p no:cacheprovider tests/unit/test_security_first_cutover.py

run_tdd.py adds verbose collected identities, short tracebacks, a unique JUnit
path and a new sandbox under this directory for each run. No broad suite ran.
Final latest complete receipt: 08-green.json, 08-green.log and 08-green.xml:
123 passed, 0 failures, 0 errors, 0 skipped; no warnings in the run output.
The earlier final-verification.* is preserved at 121 passed and predates the final
interpreter-target safeguards. Use 08-green.* as the final helper test receipt.

Vertical cycles, each with separate failing evidence before production changes:

1. Proposed Phase A bytes/canonical hashing: 01b-red -> 01-green.
2. Restricted unit parsing: 02-red -> 02-green.
3. Full source/candidate/loaded plan bindings: 03-red -> 03-green.
4. Path/alias trust and exclusive partial-preserving writes:
   04-red -> 04-green (one fixture failure) -> 04b-green.
5. Protected reads, source inventory and read-only process seam:
   05-red -> 05-green.
6. Root CLI guards, full plan/prepare, exact approval and TOCTOU refusal:
   06-red -> 06-green.
7. Artifact corruption readback and exact output inventory:
   07-red -> 07-green.
8. No arbitrary interpreter-target reads and executable permission:
   08-red -> 08-green.

Additional audit tests independently exercise every selected loaded property,
every required Python flag, literal source pins, imported-module allowlist,
non-root real CLI refusal, malformed hashes/arguments, and no ledger path.
Positive preparation is exercised only with invented inputs and ordinary-user
sandbox writes plus injected root-metadata/process seams. It is NOT protected
root staging or actual deployment acceptance.

Two unsuccessful harness/fixture attempts are retained, not relabeled successes:

- 01-red had an evidence-runner parent-index error, selected the parent checkout,
  collected no actual tests, emitted the known missing-qdrant_client warning and
  a plugin/config error. The runner path/plugin environment was corrected before
  production code was written; 01b-red is the genuine initial missing-feature RED.
- 04-green caught an invented interpreter fixture inheriting group-write mode.
  The fixture was explicitly made 0644; production trust was not weakened.

Sandboxes are intentionally retained, including synthetic symlinks, hardlinks,
FIFOs and incomplete bundles. They contain invented data only. Do not treat or
publish these fixtures as deployed artifacts. No cleanup or deletion was done.

## Ordinary-user live evidence and remaining gates

readable_live_metadata.json records that the three readable unit hashes still
match the owner-supplied pins and parse in the supported subset. The safe loaded
metadata still identifies the OLD active candidate, NeedDaemonReload=no,
DynamicUser=yes, StateDirectory empty and UMask0077. No temporary numeric service
UID is hardcoded. The actual manager UnitPath matches the fixed supported list.
No candidate inventory/import/qualification was rerun.

src/memory_daemon.py and src/llm_summarize.py were read, not imported/changed.
The daemon reconstructs a whitelisted environment; without llm.json it does not
populate the model route variables. The summarizer supports environment and
credential-file route lookup. This supports the proposed expected-off plan but
is not installed runtime evidence; the independently requested assumption review
and future actual service checks remain open.

Still pending: owner review and any separately authorized safe installation of the
helper, protected-root plan of unreadable source 20 and trust/output prerequisites,
exact digest approval, protected-root bundle preparation, independent review,
later /etc installation, reload/restart authorization, live health/MCP script
updates, and accounting/legacy-usage/recovery acceptance before optional model
analysis. This report intentionally gives no immediate activation command block.
No commits, pushes, profile/fleet edits, root staging or live state edits occurred.
