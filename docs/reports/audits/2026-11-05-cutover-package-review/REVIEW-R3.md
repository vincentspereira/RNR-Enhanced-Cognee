# Cutover package review - ROUND 3 (delta re-review of the live-run repair)

Package: docs/reports/audits/2026-11-05-cutover-package/ at commit
c9d8a0da2632bfafe49694a5baa56890c5e9df93 on branch
codex/enhanced-cognee-cutover-package-20261105 (round 2 reviewed
18509ec4db7f0d1c874c839fe49c1580f39c173e; this repair commit changes
exactly 3 files). Reviewer: fresh non-builder context, read-only,
unprivileged, offline only. No live state was touched; no credential
values or root-only bytes were printed; the reviewed worktree stayed
clean throughout.

## VERDICT: PASS

Both live-run defects ([L1] missing drop-in directory creation, [L2]
E4 install positioned before the Block G ledger-initialising restart)
are repaired correctly and completely. The commit is documentation-only
and scoped exactly as claimed. Every hash pin in MANIFEST.json and
DELIVERY.json re-verifies against the new file bytes. The offline suite
re-ran 34/34 at this commit. Two minor, non-blocking documentation
observations were found (defects 1-2 below); neither affects any
executable step, gate, or expected receipt.

## Scope check (task 1)

git diff --name-status 18509ec4..c9d8a0da lists exactly:

- M docs/reports/audits/2026-11-05-cutover-package/CUTOVER-COMMANDS.md
- M docs/reports/audits/2026-11-05-cutover-package/DELIVERY.json
- M docs/reports/audits/2026-11-05-cutover-package/MANIFEST.json

Nothing else changed (127 lines changed in the doc, 6 in DELIVERY, 2 in
MANIFEST; 83 insertions / 52 deletions total). Worktree clean at
c9d8a0da; remote branch ref equals c9d8a0da.

## L1 verification - install -d for the drop-in directory (task 2)

The relocated E4 script in Block G now contains, after the REFUSE guard
and before the file install, the exact line:

  sudo /usr/bin/install -d -o root -g root -m 0755 /etc/systemd/system/enhanced-cognee-backup.service.d

- Path is exactly the parent of dest
  (/etc/systemd/system/enhanced-cognee-backup.service.d/40-ledger.conf),
  matching the live failure ("No such file or directory" observed
  2026-11-05 because the directory did not exist on this host).
- Owner root:root, mode 0755 - the standard systemd drop-in directory
  mode (same form as the Block A evidence-dir creation pattern
  elsewhere in the doc, adapted to a world-readable /etc path).
- Ordering inside the script is correct: source-hash gate, REFUSE guard
  on dest, install -d, install file, dest-hash gate, daemon-reload,
  NeedDaemonReload=no check, oneshot run, status, backup listing.
- The surrounding prose explicitly documents the live-run finding and
  why the directory is created first. RESOLVED.

## L2 verification - E4 relocated into Block G (task 3)

- Block E no longer contains the E4 procedure. Its purpose statement
  now says E4 "is NOT run from this block any more", and a relocation
  note at the end of Block E explains the live-run finding (owner ran
  E4 pre-G; every scheduled enhanced-cognee-backup.service run failed
  because the drop-in's ledger-backup ExecStart is a hard dependency of
  the Type=oneshot unit and the ledger only exists after the G
  enablement restart initialises it in-namespace).
- The complete E4 procedure (unit bytes, install commands including the
  install -d line, expected receipt, on-failure remediation) now lives
  inside Block G, positioned after the enablement restart receipt and
  after E2/E3.
- An explicit "WARNING - ORDERING (live-run finding, 2026-11-05)"
  paragraph states that installing the drop-in before the Block G
  restart makes EVERY scheduled run of the backup service fail, records
  that this was observed live, and instructs running E4 only after the
  restart receipt is green AND E2/E3 have passed.
- The old G receipt sentence "(and install the E4 backup drop-in)"
  became "then run E4 below"; the checklist item now reads "E4 drop-in
  installed IN BLOCK G (only after the enablement restart and E2/E3 -
  never before G)". The old, ineffective trailing ordering note in
  Block E was removed rather than left duplicated.
- E2/E3/E4 acceptance sequence is coherent: G gates checked -> one
  enablement restart (ledger initialised in-namespace) -> E2 root
  readback -> E3 encrypted backup + restore proof -> E4 drop-in install
  + oneshot run producing both backups -> final summarize exercise.
  The Block E LEDGER INITIALIZATION note (run E2/E3/E4 only AFTER the
  G restart) and Block G gate item 2 (references the Block E ordering
  note) both still resolve correctly. RESOLVED.

## MANIFEST / DELIVERY hash verification (task 4)

Re-hashed every entry against the worktree bytes at c9d8a0da:

- MANIFEST.json: 12/12 files match, file_count field 12 consistent;
  CUTOVER-COMMANDS.md re-pinned to b114353d180f52da440b0b50f45ba39a
  eb3f0707f6d456f16d89684bf57e4b81 (actual bytes match).
- DELIVERY.json: 13/13 artifact_sha256 match (including the MANIFEST
  self-hash 784bc824f4bd15c5699de5c840158f0d0d44b84e706c7c8761324e406
  3969ce, re-computed and matching) and 5/5 primary_sha256 match;
  DELIVERY does not pin itself (correctly impossible).
- The E4 unit pin inside the doc (3eaa518890356207b33cc3bb5742772b3
  9e6bc2b9eb6bcfdb6888714807f9e22) still equals the tracked
  units/enhanced-cognee-backup-40-ledger.conf bytes (file unchanged).
- The old doc hash 77d36772142f755d... appears nowhere in the tree.

## Breakage hunt (task 5)

- Cross-references to E4: all nine occurrences in CUTOVER-COMMANDS.md
  (lines 399-652) are consistent with the relocation; none instructs a
  pre-G install; Block F contains no E4 reference; REPORT.md has one
  historical mention (see defect 1).
- Stale text in Blocks F/G: Block F is byte-unchanged and needs no
  change; Block G reads coherently end-to-end after the insertion.
- Hash pins of the doc inside tests: the offline suite pins no document
  hash; its four doc-consistency tests assert content strings
  (enterprise-auth pin, busctl form count 6, no -p LoadCredential,
  ledger-init deferral markers, timer-name counts) - none is affected
  by the moved text (the E4 block contains neither busctl readbacks
  nor timer names), confirmed by the passing re-run below.
- Doc-content tests, timer counts, busctl counts: all re-verified
  green at this commit.

## Offline test suite re-run (task 6)

Re-ran the exact receipt command form (venv python 3.12.13, pytest
9.1.1, --confcutdir=tests/unit, no cache providers), with the junit
artifact redirected outside the reviewed worktree to keep it clean:

34 passed, 0 failed, 0 errors, 0 skipped in 4.70s, exit 0. Worktree
still clean (git status empty) after the run.

## Defects

1. MINOR - REPORT.md repair log not extended for this repair. Item 3
   of the "Review repairs applied 2026-11-05" log still describes
   "Block E rewritten to the viable form - root-side E2/E3/E4
   verification only", and no entry documents the c9d8a0da live-run
   repair. As a historical record of the 18509ec4 revision the
   sentence was true when written, but a reader of REPORT.md alone
   would believe E4 still runs from Block E. Non-blocking:
   CUTOVER-COMMANDS.md is the authoritative procedure and carries the
   current truth, and the repair commit deliberately minimised its
   footprint to the three files it re-pinned. Recommend a docs-only
   follow-up appending a live-run repair entry.
2. MINOR - offline-tests artifacts not refreshed at c9d8a0da.
   receipt.json/junit.xml/output.txt still record the 15:50:37Z run
   against the 18509ec4 tree (commit time 15:50:46Z); the repair
   commit (17:27:44Z) did not re-run the suite. The test file itself
   is unchanged and this re-review independently re-ran it 34/34 at
   c9d8a0da, so the recorded results remain accurate for the code
   under test; the timestamps simply predate the doc-only repair.
   Non-blocking staleness of run metadata only.

## Verified sound (summary)

- Repair commit is documentation-only: 3 files, no unit bytes, no
  code, no test changes; all changed files pure ASCII.
- L1 and L2 fully resolved with correct commands, ordering, warnings,
  and checklist updates; E2/E3/E4 sequence coherent end-to-end.
- All 32 hash pins across MANIFEST/DELIVERY re-verified against
  actual bytes; no stale hash anywhere in the tree.
- No hash pin of the doc inside tests; all doc-consistency tests
  unaffected and green.
- Offline suite: 34/34 re-passed at this commit, exit 0, worktree
  clean before and after.
- Package branch remote ref equals c9d8a0da (pushed by preparer);
  worktree clean at c9d8a0da.

## Could not verify

- Post-install runtime behaviour of the relocated E4 (drop-in install,
  oneshot run, scheduled-timer health) - these exist only at owner
  execution time; per the owner's live report the emergency removal
  already restored scheduled backups to status=0/SUCCESS, and this
  review made no live changes to re-confirm that state.
- Root-only paths and credential contents - never read by policy.
