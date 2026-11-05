# Independent review - cutover package 2026-11-05

Reviewer: independent, fresh non-builder context. Read-only against the live
system (no root, no systemd/service changes, no package edits, no execution of
Blocks C-G). Machine-readable result: VERDICT.json (same directory).

Package under review: branch `codex/enhanced-cognee-cutover-package-20261105`,
commit `66d1744e6bdd891ff570cc06ab48be469ad77aba`, worktree clean at that
commit (verified). Base 41e4de7a; lineage c14f595c confirmed by git log.

## Verdict: FAIL

One blocking defect and two major defects. All three are procedure/verification
defects that make documented blocks dead-end or their receipts uncheckable as
written; every one of them fails CLOSED (no credential exposure, no spend
exposure, no privacy weakening). The shipped unit bytes, the withholding
mechanism, the rollback-evidence design, all package hashes, and the MCP
contract claims are verified sound.

## Defects

### 1. BLOCKING - Block B1 pins a wrong hash for `src/security/enterprise_auth.py`

Block B1 pins `78cf82b8d052c74438dc85e9b24...` (copied from the 2026-11-03
owner step-2 receipt). The actual staged candidate file - hashed this session,
read-only, unprivileged - is `78cf82b8d052c74438dc85b9b24...` (hex position 21:
`b` vs `e`). Six or more preserved pre-package artifacts
(review-round1/evidence-manifest.json, route-review/offline-route-receipt.json,
owner-reader-repair-v3 MANIFEST.json, audit_backend_payload.json, sandbox
manifests) record `...85b9...` agreeing with the file: the candidate is NOT
drifted; the step-2 receipt contains a one-character transcription error that
the package propagated without re-hashing the readable candidate.

Consequence: B1's "any mismatch = STOP" fires deterministically at the first
pre-switch gate; an owner following the package verbatim aborts the cutover
and is steered toward an unnecessary security re-assessment. The other eight
B1 pins (ingestion.py, llm_summarize.py, llm_budget.py, memory_api.py,
memory_daemon.py, memory_library.py, memory_queries.py, runtime/bin/python)
were re-hashed live and all match.

### 2. MAJOR - every `LoadCredential` readback receipt is uncheckable as written

On this host (systemd 255.4-1ubuntu8.18) `systemctl show -p LoadCredential`
prints `LoadCredential=[unprintable]` - verified live three ways (plain,
`--value`, `--output=json`), while `busctl introspect` of the same unit shows
the merged value as three clean ASCII pairs (index.json, llm.json, api.json).
So Block C's "LoadCredential= shows api.json:... and NO llm.json entry"
(and the same readback in D1, F1, G, and Block A's captured before-state)
cannot be confirmed by the commands shown. Immediately after the single
permitted restart the owner faces a guaranteed apparent mismatch; under the
package's own stop-on-mismatch discipline that routes them to rollback for no
real reason. The package's own preserved evidence
(SERVICE-USER-PASSED-CUTOVER-DECISION.md, 2026-11-01) already stated that
systemctl's generic LoadCredential display "was opaque, not evidence of the
full credential layout" - the claim in Block C that this readback "proves"
withholding contradicts it. The withholding itself IS real (see verified-sound
list); a working readback exists via `sudo busctl introspect org.freedesktop.
systemd1 /org/freedesktop/systemd1/unit/enhanced_2dcognee_2dapi_2eservice |
grep .LoadCredential` or root-side hashed reads of the drop-in files.

### 3. MAJOR - Block E1 cannot succeed outside the service namespace

E1 initializes the ledger with `sudo -u enhanced-cognee-api` and
`ENHANCED_LLM_BUDGET_DB=/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3`,
i.e. a host process, not the daemon's mount namespace. With DynamicUser=yes
(unchanged by the 40- drop-in) systemd provisions that directory at
`/var/lib/private/enhanced-cognee-llm-budget` and exposes only a host-side
symlink at the plain path (systemd.exec(5); `/var/lib/private` verified 0700
root:root). The service account - a systemd-managed dynamic uid 63764 that
exists in NSS only while the unit is active (no /etc/passwd entry; getent
resolves now) - cannot traverse `/var/lib/private`, and `llm_budget`'s own
`_secure_path` lstat's the host path, which is a symlink, not a directory.
E1 therefore deterministically fails with exactly the refusal it documents
("The model budget ledger path is not service-private") and instructs the
owner to STOP. Consequences: E2-E4 and the Block G gate chain are unreachable
via the documented procedure (fail-closed; ordinary memory unaffected). The
root-side steps (E2/E3, and the E4 backup drop-in's ledger step, which runs
as root and traverses the symlink) are viable, and the daemon can initialize
the ledger itself, in-namespace, at enablement time; systemd also recursively
re-chowns state directories when the dynamic uid changes across restarts, so
ledger persistence is not the issue - E1's execution context is.

### 4. MINOR - "lines 1-6" wording (Block C design note)

The V3-identical prefix is the first seven lines, not six. The operative
derivation sentence is correct and was proven by computation: removing the
three StateDirectory/StateDirectoryMode lines reproduces the preserved V3
dropin_sha256 `40ee1d8b...619651` exactly.

### 5. MINOR - Block B3 exit-code-2 attribution

Exit 2 is also returned for transport/parse errors (API down, malformed
response), not only for a missing ENHANCED_JWT_SECRET. Both are stop
conditions; the stated mapping is just incomplete.

### 6. INFO - D5 blind spot

The no-other-restart proof covers the four store units + backup timer only;
other enhanced-cognee-* timers present on the host (profile-backup,
qualified-fleet-backup) are not captured before/after. Nothing in the
procedure touches them.

### 7. INFO - no-live-changes claim

Everything readable corroborates `live_changes_made=false`: worktree clean;
drop-in dir contains only 10/20/30 with pre-package mtimes (Oct 20/24/31); no
40-/50- drop-ins; no backup drop-in dir; NeedDaemonReload=no;
`/opt/enhanced-cognee-memory/cutover` pre-exists (mtime 2026-11-02, from the
11-01/03 owner operations). Its 0700 root-only contents cannot be listed
without root - noted as not directly verifiable; Block 0's REFUSE-if-exists
guard covers it at owner time.

## Verified sound (selected)

- 40-cutover-candidate.conf equals reviewed V3 bytes plus exactly the three
  StateDirectory lines - hash-proven both directions (V3 hash anchored to the
  preserved 2026-11-03 step-2 receipt).
- `ENHANCED_LLM_BUDGET_DB=/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3`
  hardcode confirmed in BOTH the worktree (src/memory_daemon.py:123) and the
  staged candidate bytes; it is set only inside the llm-credential branch, so
  before any llm credential exists the ledger code never runs - the empty,
  manager-provisioned 0700 directory neither proves a ledger nor weakens
  privacy.
- Withholding trace: 40- resets the LoadCredential list and re-adds only
  api.json/index.json; 30-llm.conf untouched; the daemon loads llm.json only
  from $CREDENTIALS_DIRECTORY; C-F deliver no llm credential anywhere; G
  requires a manual, hash-pinned, REFUSE-if-exists owner install of
  50-llm-enable.conf (lexically after the reset). No auto-enable path exists.
- F1's withholding also works on the OLD runtime (its loader uses the same
  CREDENTIALS_DIRECTORY/llm.json mechanism - verified in old source).
- Block A captures unit + all three drop-ins byte-for-byte (root-only 0600),
  with SHA256SUMS and REFUSE-if-exists; StateDirectory is unset today so
  no state contents exist to capture; all four pinned hashes re-derivable
  from preserved pre-package evidence (43/42/14/100 files).
- Honest-abort rule (B3): precisely defined, never aborts the switch,
  enforceable - the old daemon really serves GET /v1/memories/summarization/
  status with configured/used_today, and the probe's minted JWT claims match
  enterprise_auth/MemoryScope.from_principal in both old and new code.
- Block C: exactly one restart of enhanced-cognee-api only; daemon-reload
  verified via NeedDaemonReload=no; StateDirectoryMode=0700.
- D2's expected `enhanced-cognee-api:enhanced-cognee-api 700` is correct
  (NSS-synthesized dynamic account resolves while active).
- E4's re-added first ExecStart line is byte-exact the current backup unit
  line (read-only systemctl show); age binaries present; E3 states honestly
  that the owner-held age identity is required and the gate cannot otherwise
  pass.
- Block F: restores captured bytes (sha256sum -c + repair-from-evidence), one
  restart, spend-not-reverted warning explicit, ledger rows explicitly
  preserved (not deleted).
- MANIFEST.json 12/12 and DELIVERY.json 13/13 hashes re-verified against
  worktree bytes: zero mismatches.
- Offline suite re-run from a clean environment: 30/30 passed (4.89s);
  worktree clean afterward.
- MCP contract: 44/44 profile plugin.yaml byte-identical (single sha256);
  client.py allows only /v1/memories* + /health/ready with Bearer; default
  origin http://127.0.0.1:28080; zero enhanced_cognee.json overrides; the new
  daemon binds exactly that origin and serves every plugin-called route; the
  withheld endpoints (422 detail exact-match, configured=false) are
  plugin-unused.

## Not verifiable by this review

Root-only bytes (drop-in contents, credentials, /opt cutover dir contents);
real TENANT/PROJECT scope values; existence of the owner's private age
identity; today's live unit-file bytes vs Block A pins (the pins are anchored
to preserved 2026-11-03 evidence by design - that IS the drift detector).

## Bottom line

Do not execute until defect 1 (wrong B1 pin) is fixed and defects 2-3 are
revised (working credential readbacks; in-namespace or deferred ledger
initialization). The security posture of the shipped artifacts themselves is
correct and the rollback design is sound.
