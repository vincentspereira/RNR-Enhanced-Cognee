# Independent review: G2 v2 repair (ledger namespace path fix)

Reviewer: fresh non-builder, local inputs only. Date: 2026-11-06.
Verdict: PASS (no blocking defects). Full machine-readable detail in VERDICT.json.

## What was verified

### A. Source fix (W1 @ 95e6fe61, clean tree)

- HEAD is 95e6fe619db94b4d9b212378e170e61f163dad6f; diff vs c14f595c touches
  exactly 3 files: the env constant in src/memory_daemon.py (plus comment),
  the new integration test, and the updated pinned unit assertion.
- Prescribed suite: 41 passed in 1.57s.
- Deployed baseline guard: sha256 of the /opt candidate memory_daemon.py is
  c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20 (matches).
  Deployed perms root:root 0644 match the runbook's install command.
- Reviewer fixtures (scratch dir, W1 venv): symlinked plain path refused with
  no side effects; private path accepted, ledger 0600 owner-uid; reserve/
  reconcile round-trip and cap enforcement work; parent 0755 refused;
  ".." refused; env-var path honoured; bad-perm existing ledger refused;
  no lingering sqlite journal after commit.
- One fixture initially looked like a failure (0777 ancestor NOT refused) -
  investigated and closed as a fixture artifact: the 0700 scratch directory
  acted as a shielding "private ancestor", which is the documented, intended
  exemption in _secure_path. In the real namespace the ancestors above the
  budget dir are root-owned, so no shielding applies and the strict rules hold.

### C. Correctness answers

1. Does the private path satisfy _secure_path? YES. Ancestor walk in-namespace:
   /, /var, /var/lib root-owned 0755 (pass uid-in-{0,uid} and no 0o022 bits);
   /var/lib/private is a REAL directory in-ns (tmpfs, mode=755, root-owned);
   /var/lib/private/enhanced-cognee-llm-budget is a real rw bind dir owned by
   the dynamic uid at 0700 - passes every check and sets the private flag;
   the immediate-parent re-check passes; creation uses O_CREAT|O_EXCL|O_NOFOLLOW
   0600. The old plain path fails because /var/lib/enhanced-cognee-llm-budget
   lstats as a symlink (not S_ISDIR) - refusal is deliberate and is reproduced
   by both the new test and my fixture.
2. Same file host-side? YES. mountinfo line 1053 binds source
   /var/lib/private/enhanced-cognee-llm-budget (device 8:48, ext4) to the same
   path in-namespace; the host symlink /var/lib/enhanced-cognee-llm-budget ->
   private/enhanced-cognee-llm-budget resolves to that same directory on the
   same device. Root-side E2/E3/E4 following the plain path operate on the
   identical directory the daemon writes. Semantics unchanged.
3. Security: no weakening. The diff changes one constant. _secure_path is
   untouched and still refuses the symlinked plain path; the new path is inside
   the same systemd-provisioned private StateDirectory (same trust boundary,
   same re-chown lifecycle); fail-closed refusal in _llm()/budgeted_chat() is
   untouched.
4. Constructed regressions: none found. Failures I could construct
   (root-owned or loose-perm ledger, 0755 parent, dot-dot, missing dir) all
   fail closed exactly as before. Pre-existing observation: a crash-left
   sqlite journal with loose bits makes the next connection refuse (fail
   closed) - unchanged by this fix.

### B. Runbook (CUTOVER-G2-REPAIR.md, W2 @ 74450fdf)

All requested checks pass: both hash guards verified against real files;
REFUSE-if-exists guards present; cp -p backup before install; wait-for-health
loop then is-active; E3b has --credential and --identity; E4 reference points
at the self-contained Block G E4 sub-block whose 40-ledger.conf sha
(3eaa5188...) matches the tracked unit file; rollback restores exact
.pre-g2 bytes and deletes nothing; real-scope probe (hermes_gateway/
backend_developer); bash renders correctly. No command destroys evidence.

Minor notes (non-blocking):
- units/45-llm-budget-bind.conf (the withdrawn BindPaths drop-in) is still
  tracked in units/; the runbook forbids installing it, but it should ideally
  be moved to a withdrawn/ location (owner decision - not deleted here).
- CUTOVER-COMMANDS.md Block G retains stale text (old env path at line 553,
  placeholder TENANT/PROJECT scope at line 571); the repair runbook
  supersedes both, but the stale lines could mislead a future reader.
- The health loop itself does not abort on timeout; covered by is-active
  plus the explicit ledger-presence STOP instruction.

### D. BindPaths withdrawal

Correctly reasoned to the extent local evidence allows. The destination is
verified to be a symlink in-namespace (nsenter lstat link:True), the local
systemd 255 man page documents strict destination requirements but not the
O_NOFOLLOW detail, and systemd sources were (per instructions) not fetched -
so the specific mount_nofollow mechanism stays plausible-but-unverified.
The decision is sound regardless: the drop-in was never installed, the bind
is unnecessary (the private dir is already rw in-ns per mountinfo), and
mounting over a verified symlink destination is at best fragile. Withdrawing
in favour of a one-line source fix was the right call.

## Constraints honoured

No network fetches, no restarts, no service starts, no live applies.
Writes limited to R2 outputs and session scratch (scratch fixtures cleaned up
or auto-pruned). No secret values printed.
