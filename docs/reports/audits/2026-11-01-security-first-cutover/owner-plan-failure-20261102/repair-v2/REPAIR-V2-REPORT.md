# Second/final bounded repair: V2 candidate ready for independent review

## Result and acceptance boundary

Implemented the requested NEW standalone V2 helper and NEW canonical tests.
The offline V2 inventory passes. This is an implementer verification report,
NOT independent source acceptance, protected staging or runtime acceptance.
Parent must obtain fresh independent review of the exact manifest, including
OWNER-V2-PLAN.md. If that review fails, freeze/escalate: this remains the
SECOND/FINAL repair cycle. The interrupted provider attempt wrote nothing and
was not a third cycle.

Checkout: /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101
Branch: codex/enhanced-cognee-security-first-cutover-20261101
HEAD: 72d2d90c3383cc9a83b7dfed7e3060c6ab27a8cf
Execution identity: ordinary uid/gid 1000, WSL Linux; no root or sudo execution.
No existing tracked file changed; git diff and cached diff were empty at final
inspection. No commit, staging or publication was performed. Existing dirty,
untracked, protected and live state was preserved.

## Confirmed cause and minimal change

The owner-provided read-only diagnostic confirmed V1 refused the protected
launch override because it lacked repeated User/Group lines. The four-line
metadata-equivalent invented override was reproduced offline. The first RED
attempt had a test-only substring error (User= matched DynamicUser=); its full
failure and original test bytes remain. After correcting only that assertion,
V1 failed at the actual parse_unit Refusal unit_syntax_or_directive_refused.
Only then was V2 created; the same regression passed against V2.

V2 permits absent User and/or Group declarations in the launch drop-in while
retaining exact OLD WorkingDirectory and empty-reset-plus-exact OLD ExecStart.
Whole-source validation requires an explicit DynamicUser=yes in the known
fragments, refuses any conflicting/disabled declaration, derives an omitted
user from a valid unit name, derives an omitted group from the selected user,
and compares the effective identity with the exact expected manager state.
Every explicit User/Group must match enhanced-cognee-api, including values
that a later fragment could otherwise override. No numeric UID is pinned.

Only parse_unit and plan_from_snapshot changed, plus these version constants:
- Installed path: /opt/enhanced-cognee-memory/security-first-helper-v2/prepare_security_first_cutover_v2.py
- Future bundle: /opt/enhanced-cognee-memory/cutover/security-first-c14f595c-20261101-v2

All other 14 function bodies are byte-identical to V1. Base source pins,
8 exact installed site-packages module pins, expected loaded state, lexical
interpreter alias protection, proposed api/index-only credential policy,
strict path trust, plan digest, exclusive writer, readback, partial evidence,
nonprinting exceptions and CLI safety constraints remain unchanged. No app
or V1 import exists in V2. The fixed output bundle is not created by --plan.
The minimal diff is minimal-v1-to-v2.diff.

The public local systemd.exec manpage supports the DynamicUser name/default
rules and 31-character portable name syntax. Its identity excerpt is retained
as systemd-exec-identity-reference.roff.txt. The initial read-only lookup used
an unescaped heading and failed; it was a lookup error, not a helper test.
No protected runtime-unit bytes or hash were inferred from owner metadata.

## Exact deliverable hashes

SHA-256:
- integrations/hermes/deployment/prepare_security_first_cutover_v2.py
  a8b333c156f03aa32ac3c69d8475f5978f9651bb3547b9ececca61be18e97365
- tests/unit/test_security_first_cutover_v2.py
  197edec152175a3171f7379dffea28ce4b87a000412e74f913fe699e3ad12e0e
- tests/unit/test_security_first_cutover_v2_review_regressions.py
  fb4dbdd20431b57c1130bd6e0ed1e18d556cd477c5456f4be7fdd456efe11ae7
- OWNER-V2-PLAN.md (this repair evidence directory)
  cbebb9eb0ae50451e5df431312ce9c7776dc90cabad1c5ec39ab2d3955bbeba0

V1 remains d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63.
Original tests and original owner bootstrap hashes remain unchanged, as
recorded in baseline-manifest.json and artifact-verification.json.
review-input-manifest.json also binds the shared independent challenge,
payload metadata, pytest config and the accepted eight public source modules.

## Actual execution inventory

Every pytest run used the deployment virtualenv Python, -B, plugin autoload,
--confcutdir=tests/unit and -p no:cacheprovider. Each has a separately created,
previously nonexistent --basetemp under its run directory. Full stdout,
stderr, JUnit, start binding and terminal process return code remain outside
that sandbox. No previous sandbox was reused or cleaned.

| Run directory | Passed | Failed | Errors | Skipped | Exit | Meaning |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| red-owner-minimal | 0 | 1 | 0 | 0 | 1 | Test-only instrumentation failure; helper not reached |
| red-owner-confirmed | 0 | 1 | 0 | 0 | 1 | Genuine V1 missing-identity launch refusal |
| green-owner-minimal | 1 | 0 | 0 | 0 | 0 | Same corrected regression against V2 |
| historical-v1 | 126 | 0 | 0 | 0 | 0 | Original 123 safety cases plus original 3 reviewer regressions unchanged |
| canonical-v2 | 202 | 0 | 0 | 0 | 0 | 126 mapped historical replays plus 76 additional V2-context cases |

The 76 additional parameterized cases are not 76 distinct newly discovered
logical contracts. They exercise the new identity/default context, positives,
conflicting identities in all four source positions, absent/disabled dynamic
allocation, source-manager conflict, invalid defaults, malformed launch resets,
credential/directive injection and read-only V2 plan output. The preliminary
GREEN is the same logical regression later present in canonical-v2, not extra
unique coverage. The final passing inventories contain 328 test executions
across V1 and V2, including the 126 intentional historical replays.
No pytest warnings, errors, skipped cases, xfails or deselections were reported
in either final passing inventory. No live API/model or qualification suite ran.

NEW canonical test source explicitly copies all original bodies and decorators.
Only its loader selects V2 by default (V1 requires the explicit baseline-only
environment variable), and its synthetic base fixture gains DynamicUser=yes.
The original synthetic base omitted that directive despite loaded=yes. No
original fixture was edited. All 29 original test function bodies remain
byte-identical. Complete old/new node-ID mappings and every new case ID appear
in test-inventory-and-mapping.json. canonical-copy-v1-to-v2.diff shows the exact
loader/fixture projection. Parameters and assertions were not removed.

The NEW reviewer wrapper changes both the hash PIN and the actual imported
challenge HELPER path to V2, retaining original challenge bytes and original
three assertion bodies. Its copied historical synthetic fixture is unchanged:
L01 exercises collection only, L02 rejects candidate drift before identity
validation, and S01 rejects the lexical alias before fingerprinting.
mapped-review-wrapper-v1-to-v2.diff records every wrapper change.

## Owner bootstrap verification

OWNER-V2-PLAN.md contains exactly two next-step shell blocks: install the new
hash-bound helper through an ordinary reader/stdin to /usr/bin/install, then
invoke only the protected helper --plan with OS Python -I -S -B. It explicitly
waits for independent review. It refuses an existing new helper directory,
preserves ancestor root UID/GID and mode checks, installed single-link/hash
checks and cutover-parent root:root 0700 checks. It changes no permissions.
Root never follows the checkout path. No preparation/live activation command
is provided. The old helper and output names are not overwritten or removed.

Both shell blocks pass bash -n. All three embedded Python scripts compile via
AST. The ordinary reader was safely executed unprivileged with exact source
bytes, wrong/short/long/uppercase hash inputs and a mocked root UID rejection:
6 probes met their expected exit/output contract. These probes are separate
from pytest totals. No sudo/root portion was executed. artifact-check-01 has
the validator process receipt, raw output and exact validator snapshot;
artifact-verification.json binds the checks to helper/owner hashes.

Added production lines passed the scoped shell/eval/pickle scan. Authored
source/tests/owner instructions and runner files are ASCII and have no trailing
whitespace. Raw logs/JUnit/diffs are retained untouched, not whitespace-cleaned.
Editor type diagnostics were not a type-check gate; unchanged baseline-style
untyped import/stat/parser diagnostics must not be presented as a clean full
repository static-analysis result.

## Evidence and limits

- run-summary.json: every pytest process outcome, including both failed REDs.
- test-inventory-and-mapping.json: exact executed case IDs and historical mapping.
- failures-and-limitations.json: instrumentation, read-only lookup and tool
  response-decoding errors, distinguished from helper contract failures.
- red-minimal-test.py.txt and red-corrected-test.py.txt: both minimal inputs.
- frozen-invented-owner-launch.conf: invented four-line regression metadata.
- review-input-manifest.json: exact source/test/owner/dependency review bindings.
- baseline-manifest.json: preserved original file bindings.
- artifact-verification.json: source-body preservation, syntax, reader and scans.

Independent review is still pending. Protected V2 installation and owner --plan
are unrun, and the protected launch source bytes/hash remain unknown. There
were no /opt, /etc or /var writes, credential reads, service/profile/bot actions,
live calls or qualification suites. No installation/runtime/source acceptance
is claimed. The parent's independent review must be fresh and read-only; a
new blocker requires escalation, not an unrelated fix or weakened gate.

No global/profile skill was edited because this task permits only the named
NEW repository artifacts. The identity/default lesson already exists in the
loaded system-memory-architecture skill.
