# Cutover package review - ROUND 2 (post-repair re-review)

Package: docs/reports/audits/2026-11-05-cutover-package/ at commit
18509ec4db7f0d1c874c839fe49c1580f39c173e on branch
codex/enhanced-cognee-cutover-package-20261105 (round 1 reviewed
66d1744e6bdd891ff570cc06ab48be469ad77aba; the repair commit changes
exactly 8 files). Reviewer: fresh non-builder context, read-only,
unprivileged, offline invented fixtures only. No live state was modified
by anyone during this review; no credential values or root-only bytes
were printed.

## VERDICT: PASS

All three round-1 blocking/major defects are repaired and verified
against commit bytes and the live read-only system. The offline suite
re-ran 34/34 from a clean environment. Two new minor documentation
defects were found in the repair itself (defects 1-2 below); neither
affects any executable step, gate, or expected receipt. The package is
operable as written; the two wording fixes belong in a docs-only
follow-up.

## Repair verification (per claim)

D1 (blocking, pin): re-hashed the live staged candidate myself, all NINE
Block B1 pins: 9/9 match (round 1 found 8/9). enterprise_auth.py is
78cf82b8d052c74438dc85b9b24393128e837dbb8bfee78eda8146dbef66ae1e on
disk and in the doc. The 85e9 typo pin appears nowhere in the package
and in NO preserved pre-package artifact (repo-wide search). RESOLVED.

D2 (major, readbacks): all six LoadCredential readbacks (A, C, D1, F1,
F2, G) now use
`sudo busctl introspect org.freedesktop.systemd1 /org/freedesktop/systemd1/unit/enhanced_2dcognee_2dapi_2eservice | grep .LoadCredential`;
no `-p LoadCredential` remains (also test-enforced). I executed the
command live, unprivileged: exit 0, correct object-path escaping, output
`.LoadCredential property a(ss) 3 "index.json" ... "llm.json" ... "api.json" ...`
- exactly the three-pair pre-switch set Block A's new
busctl-loadcredential-before.txt capture expects. systemctl show still
prints `LoadCredential=[unprintable]` on this systemd 255 host, so the
replacement rationale is correct. The `grep .LoadCredential` pattern
also matches the adjacent empty `.LoadCredentialEncrypted a(ss) 0`
line - harmless (zero pairs; expected pair counts stay unambiguous).
RESOLVED.

D3 (major, Block E): the out-of-namespace E1 one-shot is gone from the
doc (LEDGER_INIT_OK / TokenBudget( strings absent - test-enforced) and
Block E is root-side E2/E3/E4 only. The deferral is not just prose: I
verified in the staged candidate bytes that src/memory_api.py's
lifespan eagerly constructs TokenBudget() when an llm route is loaded
(the Block G restart), that llm_budget's _secure_path(create=True)
makes exactly what E2 checks (0600, nlink 1, uid=service,
reservations + budget_scope_day), and that E2's
`--owner-name enhanced-cognee-api` resolves via NSS while the unit is
active - guaranteed immediately after the G restart. A failed init is
fail-soft in the daemon but detectable: the G receipt demands
configured=true and E2 must pass before E3/E4. /var/lib/private
re-verified 0700 root:root. G re-sequencing (E2/E3/E4 immediately
after the enablement restart; E4 drop-in only after E2) and the
completion checklist are consistent; no stale procedural E1
references remain. RESOLVED.

D4 (minor, wording): units/40-cutover-candidate.conf re-read - 10
lines, first SEVEN are the V3-identical prefix; stripping the three
StateDirectory lines reproduces 40ee1d8b...9651 exactly. Wording now
accurate. RESOLVED.

D5 (minor, exit 2): probe re-read - exit 2 is the generic
OSError/ValueError path (missing secret, malformed scope, transport,
unparseable credential/response) printing error_kind (a type name) and
message. Broadened wording matches the code. RESOLVED.

D6 (info, timers): profile-backup and qualified-fleet-backup-v2 timers
added to Blocks A and D5; all named units exist live. PARTIAL - see
defect 2.

D7 (info, Block 0): Block 0 section byte-identical across
66d1744e..18509ec4 (1490 bytes compared). RESOLVED (no change needed).

Manifests: MANIFEST.json 12/12 and DELIVERY.json 13/13 re-verified
against worktree bytes, zero mismatches; the six changed shipped files
re-pinned; junit.xml/output.txt/receipt.json internally consistent
(34 tests; receipt 15:50:37 < commit 15:50:46). All 8 changed files
pure ASCII.

## Whole-package re-judgment

Round-1 case list re-run in full (45 checks, see VERDICT-R2.json
case_list R2-01..R2-45), including: worktree clean at 18509ec4; V3
hash derivation both directions; offline suite 34/34 from a clean
environment (env -i, exit 0, worktree still clean after); no live
changes by builder or repairer (drop-ins exactly 10/20/30 with
pre-package mtimes 2026-10-20/24/31, NeedDaemonReload=no, no 40-/50-
drop-ins, no enhanced-cognee-backup.service.d, cutover dir mtime
2026-11-02); LLM-withholding chain intact (40- reset+two-adds re-read;
live merged value is the expected three pairs; 50-llm-enable.conf pin
equals today's live 30-llm.conf bytes 12f118dd...); Block A pins now
3/4 verified against today's live world-readable bytes (unit
af979af0..., 10- 6ae6c5eb..., 30- 12f118dd...; 20- is 0600 root-only
and stays anchored to the preserved step-2 receipt, which carries all
four pins); dynamic-user account semantics; old-runtime facts for
B3/F1/G; plugin contract 44/44 uniform plugin.yaml, client.py
allowlist, zero enhanced_cognee.json overrides; remote branch ref
equals 18509ec4.

## Defects (numbered, by severity)

1. MINOR - False provenance claim in the repair documentation.
   REPORT.md ("the 2026-11-03 step-2 receipt had a one-character
   transcription error") and the test file comment ("the 2026-11-03
   owner step-2 receipt contained a one-character transcription error
   ... that the package had propagated") assert the owner's step-2
   receipt carried the 85e9 typo. The preserved receipt
   (OWNER-SUPPLIED-STEP2.txt, re-read this session) contains exactly
   one 78cf82b8... hash - the CORRECT 85b9 form - and a repo-wide
   search finds 85e9 in no preserved artifact, only in the package's
   own first commit and in the round-1 review docs that quoted it. The
   typo was born in the package, not the receipt. The misattribution
   originated in the round-1 review's evidence narrative (my
   predecessor's) and was repeated by the repairer. Docs-only impact;
   the pin itself is now correct and live-verified. Correct in a
   docs-only follow-up - an audit package should not accuse a
   preserved owner artifact of an error it does not contain.
2. MINOR - D6 repair overclaims. Blocks A/D5 and REPORT.md say the
   capture covers "every other enhanced-cognee-* timer on this host -
   backup, profile-backup and qualified-fleet-backup-v2", but a fourth
   timer exists: enhanced-cognee-qualified-fleet-backup.timer (v1,
   unit-file state disabled) is still not captured. Operationally
   negligible (disabled timer; nothing touches it), but the wording is
   factually false as written. Scope the claim to the three captured
   timers or add the v1 timer.
3. INFO - `grep .LoadCredential` also matches the empty
   `.LoadCredentialEncrypted` line in every receipt (see D2 above);
   harmless, no change required.
4. INFO - pre-existing (unchanged) property choice: comparing the
   timers' own ActiveEnterTimestamp/NRestarts detects timer restarts
   but not a scheduled firing during the window (the triggered oneshot
   service runs without re-entering the timer's active state).
   Same blind spot round 1 recorded as info; acceptable for the
   package's threat model.

## Could not verify (honest limits)

- 20-launch-runtime.conf bytes (0600 root-only); its pin is anchored
  to the preserved 2026-11-03 step-2 receipt, consistent with the
  three live-verified sibling pins.
- Contents of root-only paths (/opt/enhanced-cognee-memory/cutover,
  credential files) - metadata and preserved hashes only.
- Real TENANT/PROJECT scope values; existence of the owner's private
  age identity (the package gates G on both).
- Post-install runtime states (Block C/D receipts, the post-cutover
  two-pair value, G-time in-namespace ledger creation) exist only at
  owner execution; verified at unit-semantics and source level against
  the hash-pinned candidate bytes.

## Bottom line

Every deterministic STOP introduced by round-1 defects 1-3 is removed
and re-verified against live bytes; no new executable defect was
found. PASS, with two minor documentation corrections recommended
(defects 1-2) before or alongside owner execution.
