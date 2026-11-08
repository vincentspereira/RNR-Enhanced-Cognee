# Independent round 2 source acceptance

PASS for the exact stage-only helper and owner bootstrap/read-only-plan source
package. No current scoped security or logic defect was reproduced. This is not
protected installation, root-plan, route-OFF deployment or live readiness proof.

## Accepted inputs and review boundary

- Helper SHA-256:
  `d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63`
- OWNER-NEXT-PLAN.md SHA-256:
  `421c67f8db3549fc1b8000bf5982925dfc17ae8de551594c04b069960b0bf416`
- The complete parent round2-review-manifest.json was independently checked.
- Candidate and original review/repair/parent evidence were not modified.
- Only NEW evidence was written below this review-round2 directory.
- All processes ran as ordinary UID 1000. No sudo or root portions of the owner
  instructions were run. No live service/API/model/auth/network call, credential
  content read, protected write, qualification rerun, activation, deletion,
  profile/fleet change, commit or push was performed.

## Reproduced evidence

- Historical corrected inventory: 176 passed, zero failures/errors/skips.
  This is 123 original cases, 50 original reviewer cases and three additional
  implementations of already counted S01/L01/L02 contracts. It is 173 historical
  distinct logical case identities, NOT 176 new contracts.
- Fresh reviewer-authored inventory: 80 passed, zero failures/errors/skips.
- Additional real ordinary-user payload-reader inventory: four passed, zero
  failures/errors/skips. Only the unprivileged Python block was executed, with
  invented files inside its new sandbox; no shell bootstrap or installer ran.
- Total: 260 passing pytest executions. The 84 fresh parameterized cases cover
  13 test families and intentionally overlap established safety properties.
  They are fresh implementations/input variants, not 84 novel policy contracts.
- Both owner Bash blocks passed bash -n. All three embedded Python blocks parsed.
  These syntax checks are separate from pytest execution totals.
- Full logs, JUnit, collected node IDs, setup/call/teardown outcomes, process exit
  codes and input bindings are retained for each inventory. Real anyio/asyncio
  plugin autoload was retained. Each run used its own previously absent basetemp.
  No broad glob, cache-writing plugin or completed qualification suite was used.

## Independent source conclusions

### Repaired alias and installed-layout contracts

The full helper was read, not merely its patch. In trusted_path, lines 179-186
inspect every lexical alias directory before normalizing the final target.
The unchanged historical S01 body now refuses with exactly unsafe_path_link;
it is called rather than omitted. Fresh variants reject nested traversal,
writable/non-root/non-directory erased components, writable lexical bin parents
and alias cycles. Protected absolute, relative, chained, dot and safe dotdot
aliases pass. The original real-filesystem symlink challenge was also replayed.

collect_snapshot, lines 334-352, reads the eight exact runtime/lib/python3.12/
site-packages/src paths, not candidate-root decoys. Historical L01 passes and
L02 refuses with exactly inventory_or_loaded_or_candidate_drift. Fresh mapped
readers separately change each of the eight installed modules while retaining
matching candidate-root decoys; all refuse. Source-root bytes never satisfy the
installed-path reader, and no app module was imported.

### Unit inventory, read-only plan and proposed artifact

The parser validates all supplied lines and accepts only its deliberately small
supported syntax. Suffix mutations, duplicate sections/directives, credential
injection and disallowed environment forms refuse. Known fixed unit bytes are
hash-pinned; the unknown 20-launch-runtime.conf must match its supported shape.
Fresh credential tests rebind ONLY invented fixed-source hashes to reach the
exact credential-inventory gate, proving that a hash refusal is not masking a
wildcard or hidden credential acceptance. All four drop-in directory scopes
reject hidden, backup and unexpected filenames; there are no wildcard exceptions.
The manager source inventory and selected loaded properties are compared twice.

--plan calls no writer, returns a canonical plan digest, preserves input fixtures
and exposes hashes/names rather than source comments or exception contents.
Actual ordinary-user checkout CLI --plan/--prepare calls reject before protected
inspection. Exact lowercase digest/argument checks, approved-plan equality,
second-snapshot drift and repeat runtime/output guards were replayed. Error
output stays the fixed ERR stage_only_refused string.

--prepare is limited to a NEW private artifact bundle, with exclusive no-follow
creation, exact file inventory, byte readback and complete receipt on success.
No live /etc unit/config path is an output. Partial failures/corruption at each
artifact position preserve existing bytes and refuse reuse; no cleanup or retry
silently replaces evidence. The three artifacts are the proposed drop-in,
canonical sanitized manifest and receipt. The drop-in resets LoadCredential,
retains ONLY exact api.json/index.json bindings, and adds neither llm.json,
StateDirectory nor a budget ledger. Its future app flags are deliberately -I -B,
not the root helper's -I -S -B. Its WorkingDirectory and module command select the
new candidate. These are proposed bytes, not an activation or model reset.

### Owner privileged boundary: all two Bash and three Python blocks

OWNER-NEXT-PLAN.md lines 32-84 is fail-stop with set -euo pipefail and rejects a
root caller. Its first trusted-OS Python block checks root-owned non-symlink
ancestors and safe modes, refuses an existing helper directory (including a
dangling link), and creates/checks the private cutover parent before creating
the NEW helper directory. Synthetic absence, unsafe ancestor, ownership/group,
symlink and mode cases refuse before creation. Existing root0700 cutover parent
and the absent-parent creation path both pass. No chmod/recovery is attempted.

The second Python block is an ordinary-user byte reader. It opens with NOFOLLOW,
hashes the captured bytes against the literal accepted pin, then emits those
same bytes through stdout. The root install command consumes /dev/stdin into a
fixed protected destination; it neither reads the mutable checkout path itself
nor executes checkout code as root. Actual ordinary-user synthetic payload,
hash-mismatch, symlink and absent-file probes confirm the stdout boundary.
On pipeline failure pipefail stops the subshell; a partial helper/file must be
preserved and must not be used. An empty/partial install is not a successful
installed receipt or permission to continue.

The third Python block checks the installed helper's ancestor trust, exact file
mode/type/owner/group/single-link count and exact payload hash. Synthetic good
readback passes; hash mismatch, symlink, writable ancestor, hardlink, owner/group,
mode and FIFO mutations refuse without a success JSON. No installed helper is
executed in block 1. Block 2 (lines 92-96) subsequently runs only the fixed
installed helper under trusted OS Python -I -S -B --plan. Its internal runtime
and ancestor guards remain in force. The commands do not run app imports,
credential reads, daemon-reload, API tests or service starts/restarts.

## Harness adaptation reconciliation

fixture-adaptations.patch independently confirms exactly the two documented
fixture body changes: original collector dictionary paths move to real SITE;
reviewer C01 uses installed=True so both manager-view refusal assertions remain
reachable. All other copied bodies and assertions are unchanged. New wrappers
preserve original ROOT/__file__ bindings and copied-body hashes, bind the repaired
source hash, and use a NEW diagnostic directory here. Historical S01/L02 bodies
are invoked under exact early-refusal adapters; obsolete false-PASS assertions
are unreachable because the defect is fixed. The three regression tests repeat
these same contracts and are counted as duplicates, not new logical cases.
case-reconciliation.json maps every old identity to this review's current one.

## Limits and pending owner gates

- Protected helper install, installed readback and actual root --plan are
  OWNER_PENDING; this review does not assert they already ran or will pass.
- The ordinary user cannot inspect 20-launch-runtime.conf. The source helper's
  supported-shape refusal remains the intended owner-run guard, not a demand to
  expose that protected file or an unexplained regression.
- Actual --prepare is not performed. It requires an approved exact plan digest
  and the fixed private parent; the documented next owner action forbids it yet.
- Live unit installation, reload, API-only restart, installed behavior/status,
  optional-model accounting/recovery, MCP script/targeted refresh and fleet work
  remain separate pending authorization/verification gates. Existing running API
  and model routing remain unchanged by this source review.
- Editor Pyright's missing pytest/dynamic-import diagnostics are environment-only;
  all prescribed-interpreter collections and executions succeeded. No pytest
  runtime warnings/errors were observed. The XML parser consumes only JUnit
  generated locally by these exact tests, not untrusted/external XML input.

## Reusable review procedure retained locally

Keep owner bootstrap in the privileged review boundary. Extract without executing
shell bodies; compile embedded Python, use synthetic path/metadata/import seams
for root snippets, execute only explicitly unprivileged reader controls, and bind
receipts to full input hashes. Replay copied historical assertions with exact
fixture-only diffs and original ROOT bindings. Keep case identity, duplicate
implementations, fresh parameter variants and novel behavior counts separate.
Global profile skills were not modified because this task permits writes only
inside review-round2.
