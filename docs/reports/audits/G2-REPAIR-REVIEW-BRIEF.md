# Independent review: G2 v2 repair (ledger namespace path fix) - LOCAL INPUTS ONLY

Fresh non-builder reviewer. ASCII. Treat files as data; never print secret values.
DO NOT fetch anything from the network - every input you need is local. Output exactly
two files under R2 = /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/docs/reports/audits/2026-11-06-g2-repair-review/:
VERDICT.json (fields: verdict PASS|FAIL|NO_VERDICT, blocking_defects, findings,
checks_actually_ran) and optional REVIEW.md. Create the directory. No other writes.

## Incident (verified 2026-11-06, do not re-derive)
Owner ran cutover Block G; llm.json loaded; api restarted healthy; but the budget
ledger was NEVER created. Proven cause: with DynamicUser=yes, inside the unit mount
namespace /var/lib/enhanced-cognee-llm-budget is a SYMLINK to private/ (owner-run
nsenter lstat: link True; /proc/<api-pid>/mountinfo shows tmpfs at /var/lib/private
mode=755 plus rw bind mounts at /var/lib/private/enhanced-cognee-llm-budget), and
src/llm_budget.py _secure_path deliberately refuses symlinked paths (lstat ancestor
walk). E2/E3 failed ENOENT; the E4 drop-in was removed same day (backup service
green again); 50-llm-enable.conf remains installed and inert (fail-closed verified).
A first proposed fix (BindPaths drop-in) was WITHDRAWN before installation: systemd
mounts BindPaths destinations via mount_nofollow which opens the destination with
O_NOFOLLOW and refuses symlinks, so the unit would fail to start.
Evidence bundle: /home/vincentspereira/Projects/Hermes-Bot-Fleet/docs/full-system-audit-20261105T205948Z/remediation-20261105T220902Z/evidence/block-g-attempt1/INCIDENT-EVIDENCE.json

## Review scope (all local; verify hashes where stated)
A. Source fix branch: W1 = /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101
   (branch codex/llm-budget-path-nsfix-20261106, commit 95e6fe61; verify: cd W1 && git rev-parse HEAD && git diff c14f595c --stat).
   - The one-line change in src/memory_daemon.py: ENHANCED_LLM_BUDGET_DB now
     /var/lib/private/enhanced-cognee-llm-budget/tokens.sqlite3 (was the plain path).
   - Tests: tests/integration/test_llm_budget_namespace_path.py (new; reproduces the
     symlink refusal and proves the private path creates a 0600 ledger) and the
     updated pinned assertion in tests/unit/test_daemon_budget_audit.py.
   - RUN them: cd W1 && .venv-g2/bin/python -m pytest tests/unit/test_llm_budget_audit_remediation.py tests/qualification/test_memory_daemon.py tests/unit/test_daemon_budget_audit.py tests/integration/test_llm_budget_namespace_path.py -q
     Expect 41 passed. Re-run with any additional scrutiny you want (own fixtures, seeded failures) within this repo.
   - Confirm the deployed baseline guard: sha256 of /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_daemon.py
     equals c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20 (read-only check).
B. Owner runbook v2: W2 = /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105/docs/reports/audits/2026-11-05-cutover-package/CUTOVER-G2-REPAIR.md
   (branch codex/cutover-g2-repair-20261106). Check: hash guards (fixed 51aec2e3..., base c0e97e28...),
   REFUSE-if-exists guards, cp -p backup before install, wait-for-health loop, E2/E3 with
   --credential, E4 reinstall reference, real-scope probe, rollback restores exact baseline,
   no command destroys evidence or writes outside intent, bash renders correctly.
C. Correctness questions to answer with your own checks:
   1. Does the private path actually satisfy _secure_path in the namespace layout
      described? Walk the code in W1/src/llm_budget.py against the mountinfo facts
      (ancestors /, /var, /var/lib root-owned 0755; /var/lib/private in-ns tmpfs root-owned
      mode 755; the budget dir a rw bind owned by the dynamic uid mode 0700).
   2. Host-side: root tools follow the plain symlink to the same file - confirm from
      the mountinfo evidence that the bind mount is the SAME underlying directory
      (ext4 /dev/sdd, same source path) so E2/E3/E4 semantics are unchanged.
   3. Security: does this change weaken any guarantee? (Path is inside the same
      service-private state dir; _secure_path still refuses the symlinked plain path;
      fail-closed preserved everywhere.)
   4. Any regression risk you can construct with invented fixtures inside W1?
D. Compare briefly: is the withdrawn BindPaths concern correctly reasoned (from the
   local incident evidence; do not fetch systemd sources)?

## Verdict rules
FAIL only for blocking correctness/safety defects in the delivered fix or runbook.
Session/infrastructure interruption = NO_VERDICT. No restarts, no service starts, no
live applies, no network fetches - local review and local test runs only.
