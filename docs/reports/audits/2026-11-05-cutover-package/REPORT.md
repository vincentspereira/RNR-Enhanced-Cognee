# Cutover package report - 2026-11-05

Status: package PREPARED AND COMMITTED; nothing executed against any live
service, unit, credential or profile. No root was used by the preparing
agent. All system facts below are read-only discoveries or owner-supplied
receipts cited from the repository's accepted audit evidence.

## What was built

Branch codex/enhanced-cognee-cutover-package-20261105, one commit on top of
accepted backend-stage commit 41e4de7a5db99970a7629ef3f274138eef3031e8.

1. docs/reports/audits/2026-11-05-cutover-package/CUTOVER-COMMANDS.md -
   sequenced owner blocks 0, A-G with purpose, exact paste-and-run commands,
   expected receipts and stop-on-mismatch instructions:
   - A: rollback-evidence capture (unit + three drop-ins copied byte-for-byte
     into a root-only 0700 evidence dir with sha256; systemctl show facts;
     pinned expected hashes; secret values never printed).
   - B: candidate hash re-verify (8 modules + interpreter; every pin
     re-derived from the live candidate bytes, not from earlier receipts -
     repairs review defect 1, the enterprise_auth.py one-character pin
     error propagated from the 2026-11-03 step-2 receipt), verbatim
     service-user import re-check, current-day usage read from the old API
     summarization status, and the exact honest-abort rule (usage findings
     never abort the switch; they keep optional analysis withheld until the
     first clean UTC-day boundary).
   - C: the switch - one new drop-in 40-cutover-candidate.conf (V3-reviewed
     base bytes + three StateDirectory lines), daemon-reload, ONE restart of
     enhanced-cognee-api only; explicit 30-llm.conf handling (file untouched;
     its llm.json LoadCredential is neutralized by the drop-in's list reset,
     so no LLM credential reaches the new daemon).
   - D: post-switch readbacks (manager properties, state dirs 0700 inside
     the namespace via /proc/PID/root, /health/ready, plugin-path
     remember+recall round trip, analysis 422 + configured=false, proof no
     other unit restarted against the Block A timestamps - the before/
     after capture now covers every enhanced-cognee-* timer on this host:
     backup, profile-backup and qualified-fleet-backup-v2).
   - E: root-side ledger verification, one-shot encrypted backup +
     decrypt/restore verification, and the exact owner edit aligning the
     EXISTING enhanced-cognee-backup service (drop-in adds a second oneshot
     ExecStart; original preserved). Ledger initialization is deliberately
     DEFERRED: the daemon creates the ledger inside the service mount
     namespace at Block G enablement time, because a host-side
     service-identity init cannot traverse the DynamicUser private state
     directory (review defect 3); until enablement the empty private state
     directory is honestly recorded as NOT ledger proof.
   - F: rollback - recommended variant keeps analysis withheld on the old
     runtime; full-restore variant documented with explicit warning that
     reverting binaries does not revert spend.
   - G: later optional-analysis enablement (clean UTC-day rule, ledger +
     backup acceptance now sequenced right after the enablement restart,
     owner-deferred credential decision; the 50- drop-in is byte-identical
     to the deployed 30-llm.conf loader).
2. units/*.conf - the four exact byte artifacts (hashes pinned in the doc,
   MANIFEST and tests).
3. integrations/hermes/deployment/cutover_probe_20261105.py - read-only
   probe (usage / verify subcommands) minting a short-lived scoped token
   in-process from api.json; never prints secrets or tokens.
4. integrations/hermes/deployment/ledger_tools_20261105.py - ledger verify,
   age-encrypted snapshot backup with HMAC-signed manifest (mirrors
   src/memory_backup.py semantics), and decrypt/restore verification.
5. tests/unit/test_cutover_package_20261105.py - 34 offline tests, invented
   fixtures only (stub HTTP API, fake credentials, temp sqlite ledgers,
   stub age CLI). All 34 pass under the prescribed venv pytest command; see
   offline-tests/receipt.json, output.txt, junit.xml.
6. MANIFEST.json (sha256 of every shipped file) and this DELIVERY.json.

## MCP/plugin contract confirmation

Confirmed unchanged and compatible: all 44 profile plugin.yaml files are
identical (name enhanced_cognee, requires_env ENHANCED_COGNEE_ACCESS_TOKEN);
client.py only calls /v1/memories* and /health/ready with a Bearer token at
the default origin http://127.0.0.1:28080; the new daemon binds exactly that
origin and serves every plugin-called route; withholding only affects
plugin-unused analysis routes (422 / configured=false). No plugin, profile
or gateway change is needed or permitted.

## Deviations and justifications

- The drop-in sets StateDirectory=enhanced-cognee-api (as instructed) AND
  StateDirectory=enhanced-cognee-llm-budget. The second entry is required by
  code: src/memory_daemon.py hardcodes
  ENHANCED_LLM_BUDGET_DB=/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3
  whenever an llm credential loads; without that private directory the
  ledger (and therefore Block G) can never initialize. A unit test proves
  the drop-in equals the independently reviewed V3 bytes plus exactly these
  three StateDirectory lines.
- Ledger initialization happens at Block G enablement time, not at cutover
  time (revised per review defect 3): the daemon creates the ledger inside
  the service mount namespace when it first loads an llm credential. A
  cutover-time host-side init as the service identity cannot work - with
  DynamicUser=yes the state directory lives under /var/lib/private (0700
  root:root, host-side symlink only at the plain path), which the dynamic
  account cannot traverse and which src/llm_budget.py correctly refuses.
  Block E is therefore root-side verification only and runs after the
  enablement restart; until then the empty private state directory is
  honestly recorded as not being ledger proof.

## Review repairs applied 2026-11-05 (same branch, second commit)

The independent review (docs/reports/audits/
2026-11-05-cutover-package-review/, VERDICT FAIL) found seven defects;
this revision repairs all of them, documents only, no live change:

1. BLOCKING: Block B1 enterprise_auth.py pin corrected to the re-derived
   live candidate hash 78cf82b8d052c74438dc85b9...ef66ae1e (the 2026-11-03
   step-2 receipt had a one-character transcription error); all nine B1
   pins now re-derived from the candidate bytes by the preparer.
2. MAJOR: every LoadCredential readback (Blocks A, C, D1, F1, F2, G)
   replaced with the busctl introspection form verified working during
   review - systemctl show -p LoadCredential prints "[unprintable]" on
   this host's systemd 255 and was never a usable proof. The semantic
   purpose of each check is unchanged (especially the Block C/D
   no-llm-credential proof, now via busctl's merged value).
3. MAJOR: Block E rewritten to the viable form - root-side E2/E3/E4
   verification only; the out-of-namespace E1 one-shot init removed;
   ledger initialization deferred to the daemon inside the service
   namespace at Block G enablement, with the honest statement that an
   empty private directory is not ledger proof.
4. MINOR: Block C design note corrected - the V3-identical prefix is the
   first SEVEN lines (the hash-derivation rule was already correct).
5. MINOR: Block B3 exit-code-2 note broadened to the probe's generic
   configuration/transport error (missing secret, malformed scope,
   unreadable/unparseable credential or response).
6. INFO: the no-other-restart before/after capture (Blocks A and D5) now
   also snapshots enhanced-cognee-profile-backup.timer and
   enhanced-cognee-qualified-fleet-backup-v2.timer.
7. INFO: Block 0's REFUSE-if-exists guard kept exactly as reviewed (no
   change required).

The offline suite grew from 30 to 34 tests (four new doc-consistency
tests guard the corrected pin, the busctl-only readbacks, the deferred
ledger initialization and the full timer coverage).

## Live facts relied upon (read-only, 2026-11-05)

Unit active on the old candidate 21abf485...; drop-ins 10/20/30 as recorded
in the 2026-11-03 owner V3 plan receipt (pinned hashes re-stated in Block A);
20-launch-runtime.conf remains root-only 0600 and was never read;
30-llm.conf is the 64-byte llm.json loader; backup unit runs
/opt/enhanced-cognee-memory/runtime/bin/python -m src.memory_daemon backup
(Type=oneshot, daily timer, /var/backups/enhanced-cognee).

## Open questions for review

1. Confirm the StateDirectory=enhanced-cognee-llm-budget addition (code-
   mandated ledger path) is accepted alongside the instructed
   StateDirectory=enhanced-cognee-api.
2. Block A pins the 2026-11-03 unit/drop-in hashes; if the live unit drifted
   since, the owner's Block A will refuse - the drift itself then needs
   review before any switch.
3. B3/D4 need the real TENANT/PROJECT scope values from the owner (not
   discoverable read-only); unenumerated scopes conservatively count as
   unknown under the honest-abort rule.
4. E3 requires the owner-held private age identity pairing with
   backup.json's recipient; without it the backup gate cannot close and
   Block G must stay shut.
5. The base runtime powering the backup service (pre-overlay modules) is
   deliberately untouched; whether to later move it to the audited candidate
   is a separate decision.
