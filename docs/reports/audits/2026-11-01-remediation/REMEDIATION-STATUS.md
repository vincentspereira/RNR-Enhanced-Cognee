# Enhanced Cognee remediation - source versus installed status

Date: 2026-11-01. Ubuntu-Hermes only.
Branch: codex/enhanced-cognee-audit-remediation-20261101
Base: 89d1be78bbe9571b9152396c5483eabbb8360b95
Checkout: /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101

## Source review gate: accepted repaired candidate, NOT installed

The independent review rejected the 149-test candidate. Its exact 29-file source
snapshot, hashes, verdict, challenge sources and outputs are preserved in
`review-round1/`; `rejected-source.zip` is the immutable pre-repair candidate.
The parent replay reproduced the failures before any repair.

Three blockers require repair: R1 interpreter lexical-directory trust (high),
R2 malformed successful API response acceptance (medium), and R3 expiry overflow
aborting the renewal sweep (medium). One non-blocking ambiguity also requires a
fail-closed policy for an unknown existing role inventory. These are source
acceptance defects, not reasons to weaken or waive the owner deployment gates.

Repair cycle 1 was implemented in a third agent context. The parent rerun passes
187 targeted offline cases (149 original plus 38 repair cases), with no failures,
skips or warnings. Static checks also pass. Only the three reported production
files changed; the original 13 test files and rejected evidence are preserved.
The repaired candidate in `source-manifest-round2.json` passed a fresh independent
review: 187 regressions, 15 mapped prior challenges and 12 fresh challenges passed
(214 accepted case executions, not 214 distinct new tests). Ten deprecation
warnings came from the unchanged historical SQLite grant-test adapter; none came
from the 187-case suite or fresh challenges. Failed harness attempts and exact
mapping explanations are preserved and not double-counted.

The parent verified all 30 current source/test hashes, the review archive CRC,
every archived payload hash and the machine-readable verdict. Evidence is retained
in `review-round2/` and `parent-acceptance-round2.json`. Source publication on the
separate remediation branch is now allowed. No installed security sign-off is
implied; owner deployment gates below remain open. The original rejected review
and source archive remain unchanged.

## Recommendation

Review the accepted source changes, then install the narrowly scoped root renewal
upgrade first using OWNER-NEXT-STEPS.md. Do not treat this source work as an installed
security fix or production sign-off. The live backend and all profile files have
been preserved. Main has not been merged; no bot was activated, no credential
family rotated, and no service restarted.

The original independent audit and raw outputs remain untouched in the delivery
checkout under docs/reports/audits/2026-10-19-hermes-security/
independent-review-2026-11-01/.

## Current source changes

| Finding | Candidate source action | Installed/acceptance status |
|---|---|---|
| F01 root runtime | OS Python for root renewal; protected-runtime child for python-dotenv provisioner; root ownership/mode/ancestor checks; root-staged installer | NOT INSTALLED; owner sudo required |
| F02 DNS rebinding | Numeric-IP socket connection after validating every DNS answer, actual-peer check, original TLS/Host identity retained | Offline source tests pass; protected backend not updated |
| F03 summary lifecycle | Explicit owned source IDs; summary returned only, stored=false, no detached saved derivative | Intentional API contract change; not deployed |
| F04 model cap | Persistent service-private SQLite ledger; tenant/project/day reservations before dispatch; conservative charges survive failures, process death and cancellation | Offline concurrency/reopen tests pass; service directory and installed accounting pending |
| F05 model privacy | No unfiltered recent-memory selection; reject foreign/shared/unverifiable sources; credential screening before truncation and dispatch | Pattern detection is not universal privacy classification; no private data used |
| F06 MCP errors | API failures set MCP isError while retaining bounded fixed service details | Offline transport tests pass; installed MCP untouched |
| F07 timeout | Analysis client timeout raised above backend model deadline; summaries no longer auto-write on a lost reply | Candidate only; real provider/deployment acceptance pending |
| F08 renewal failures | Per-profile timeouts/invalid receipts fail safely; strict booleans, exit status, profile and expiry; atomic state publication | Offline tests pass; no renewal run performed |
| F09 renewal drift | Root-owned data-only roles.json, 45 identities; reviewed predecessor upgrade with preserved backups | Original installed script still differs until owner upgrades |
| F10 running child handoff | No claim that .env replacement reloads an existing MCP child; targeted acceptance protocol below | OPEN runtime acceptance gate |
| F11 verifier truthfulness | Explicit failure/skip summaries and nonzero exit; maintained fixture-only functional runner replaces ignored historical diagnostic | New offline tests pass; full corrected live runner deliberately not run before deployment |
| F12 catalogue overclaim | Full selected provider/MCP config, exact configured launch and scoped status; independent tool-name sets; no capture claim | 44/44 corrected live catalogue/status checks pass; native capture qualification not repeated |
| F13 current recovery | Distinguish canonical data, restricted inactive candidates, and CURRENT 44 gateway profiles | OPEN owner evidence; no new backup/restore/retention deletion performed |
| F14 fetch deadline | Isolated killable worker bounds whole DNS/connect/header/body fetch; parent waits/reaps its child on timeout | Offline tests pass; real network/installed sandbox checks pending |
| F15 partial ingestion | Explicit non-success receipt listing acknowledged IDs and stable retry base key; no false rollback claim | Source/API fake-store tests pass; not a transactional batch guarantee |
| F16 malformed RPC | Validate params/argument shape and required fields; do not echo malformed input | Offline tests pass; no gateway child restarted |
| F17 documentation drift | This status supersedes blanket completion wording, while retaining original historical engagement text | No historical evidence erased |
| F18 broken read tools | Correct entity payload; scoped shared/library GET handlers; exact read-only permission exemptions; mutations remain admin-only | Source route/query tests pass; installed endpoints still old |

## Verification actually performed

- Final repaired candidate: 187 targeted offline regression cases passed in one
  parent run: targeted-regressions-round2.txt/.xml and targeted-command-round2.json.
  The initial 149-case passing run is preserved as rejected-candidate evidence;
  passing that run alone did not establish correctness.
- Model slice includes real SQLite concurrency, reopen, abrupt exit, lock
  contention, cancellation and file-protection tests, with fake model/store data.
- Scoped API tests call the actual route functions using invented in-memory
  stores; they are not live PostgreSQL, service-UID or hosted-model acceptance.
- Revised non-root consolidated verifier returns a normal 69-check summary:
  three failures (candidate MCP not installed; unsafe live renewal entry point;
  last renewal state not a full 45-identity sweep), five owner-only receipt skips.
  It exits 1 honestly. The other checks pass in their declared limited scope.
- Revised per-role verifier passes all 44 exact configured catalogue/status
  checks. No profile config, token or fleet-admission setting was changed.
- A broad filename glob also selected old unrelated audit tests: 229 cases,
  211 passed, 1 failed and 17 setup errors, all failing cases blocked at the
  missing optional qdrant_client import. The same representative failure was
  reproduced against the untouched delivery checkout. No dependency was
  installed and the broad run is NOT reported as a clean full suite.
- Whitespace checks on the 30 reviewed source/test files and maintained runbooks
  pass, as does independent pre-commit source review. The full staged evidence
  tree reports original trailing whitespace in five raw log/XML/patch files;
  those evidence bytes are intentionally preserved, not silently cleaned. See
  review-round2/verdict.json and parent-acceptance-round2.json for exact scope
  and source hash binding. Hosted CI is not verified green.

No completed native/memory qualification, credential-family test, live model
call or live write/retract loop was repeated during this remediation phase.

### Preserved test-harness correction

The first revised verifier compared a display-masked runtime path literally and
incorrectly rejected the configured commands. It also over-interpreted the main
profile's catalog plugin allowlist. Those failed outputs remain preserved.
The corrected verifier reads the exact approved runtime identifier as static AST
data and checks main local-provider selection separately; a new positive-control
test prevents the false rejection. Do not count the first run as live failures
of 44 profiles or discard its evidence.

### Functional runner testing discipline

The original audit preserved the failing real archived-suite output (including
exit zero after failure). The maintained replacement has unit checks for exit
status and cleanup acknowledgement. It was written before those helper-unit
checks, so it must not be described as an entirely test-first rewrite. Existing
RED/GREEN logs for the other remediation slices are retained individually.

## Important intentional changes

1. POST /v1/memories/summarize now requires record_ids and returns the summary
   without storing it. Persisting an output is a separate reviewed remember
   operation, not an automatic side effect. This avoids retaining a copy after
   source access/expiry changes.
2. Consolidation also requires selected owned record_ids; it does not scrape
   recent memories or merge anything.
3. Model calls require a private persistent budget ledger. The daemon exports
   the fixed path /var/lib/enhanced-cognee-llm-budget/tokens.sqlite3. The owner
   must provision the API unit's StateDirectory before deployment. Missing or
   unsafe accounting disables optional model calls, not normal memory.
4. The renewal installer requires root-staged sources and a stopped timer. It
   never runs renewal or starts the timer. It preserves source/unit backups and
   leaves re-enabling the timer to the owner after receipt review.
5. The provisioner needs python-dotenv, absent from the OS Python. Renewal itself
   uses /usr/bin/python3, while the child provisioner uses the existing protected
   /opt runtime only after its resolved executable, environment and ancestors
   pass root-trust checks. No user-writable deployment venv is permitted.

## Remaining host acceptance: not silently closed

- F01 root renewal upgrade installation, loaded-unit readback and timer resume.
- Exact protected backend code/package binding and a versioned owner deployment
  preserving old source, keys, data, store permissions and rollback evidence.
- API StateDirectory provisioning and ledger persistence under its service UID.
- Corrected MCP installation with original copy retained, and new-session tool
  calls for all ten read tools. Existing long-lived children may need a supported
  reconnect after the approved installation.
- F10 renewal/credential handoff: demonstrate fresh credentials reach the native
  provider and MCP children, and a restart between atomic publication and sweep
  completion does not strand later profiles. Use a separately approved narrow
  protocol, never repeat backend-family rotations to simulate this.
- F13 existing backup membership/receipt evidence for the CURRENT gateway home
  and all 44 profiles, plus a dated restore proof. The inactive 41-candidate job
  and canonical database backup do not by themselves establish this coverage.
- The historical qualification fixture tests/qualification/test_llm_family.py
  still uses retired in-memory TokenBudget semantics. Migrate that fixture to a
  private temporary ledger before any separately approved qualification phase;
  it was not changed or rerun here. This is an intentional source API change,
  not a claim that the historical qualification suite is currently green.
- Owner-only rotation receipts and exact LLM credential file protection, without
  values. The original OWNER-CHECKS.md remains applicable.
- Test a bounded owner alert route for failed/stale renewal, backups and disk
  pressure. No notification, cron job, off-host upload or service was added.

These host gates cannot be completed by pretending that source tests are live
proof. Non-interactive sudo was unavailable in this session; do not share a
password in chat or put it in an agent environment file.
