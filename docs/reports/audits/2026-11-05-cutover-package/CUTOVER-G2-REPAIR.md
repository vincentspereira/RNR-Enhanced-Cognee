# CUTOVER-G2-REPAIR v2 - owner runbook (after failed G attempt 1, 2026-11-06)

v1 of this runbook proposed a BindPaths drop-in; it is WITHDRAWN before any
installation: systemd mounts BindPaths destinations via mount_nofollow
(O_NOFOLLOW on the destination), which refuses symlink destinations, so the
unit would have failed to start. units/45-llm-budget-bind.conf was NEVER
installed on the host and must not be. The fix is a one-line source correction.

## Incident summary (evidence: remediation evidence/block-g-attempt1/)
Block G attempt 1 loaded llm.json and restarted the api cleanly, but the
budget ledger was never created: inside the DynamicUser unit namespace
/var/lib/enhanced-cognee-llm-budget is a SYMLINK to private/ (nsenter lstat
link:True; mountinfo: tmpfs at /var/lib/private + rw binds at the private
paths), and src/llm_budget.py _secure_path deliberately refuses symlinked
ledger paths. E2/E3 failed ENOENT; the E4 drop-in was removed same day and
the backup service is green; 50-llm-enable.conf remains installed and inert
(fail-closed verified in _llm() and budgeted_chat()).

## Fix (branch codex/llm-budget-path-nsfix-20261106, commit 95e6fe61)
src/memory_daemon.py now provisions
ENHANCED_LLM_BUDGET_DB=/var/lib/private/enhanced-cognee-llm-budget/tokens.sqlite3
(the path that is a REAL read-write 0700 directory inside the namespace).
Host-side tools (E2/E3/E4) keep using the plain symlink path as root - same
underlying file. Regressions: 41/41 (new tests reproduce the symlink refusal
and prove the private path creates a 0600 ledger; the pinned daemon test was
updated to the new constant).

Baseline guards:
- deployed original sha256 c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20
  (= c14f595c:src/memory_daemon.py, verified 2026-11-06)
- fixed file sha256      51aec2e30944fc197a2352070e4b111d823ad92ec5c5db64c3b4742b5a03a344

## Owner block G2 (single paste, then the checks)
```bash
(
set -euo pipefail
src="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101/src/memory_daemon.py"
expected_fixed="51aec2e30944fc197a2352070e4b111d823ad92ec5c5db64c3b4742b5a03a344"
expected_base="c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20"
dest="/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_daemon.py"
[ "$(sha256sum "$src" | cut -d' ' -f1)" = "$expected_fixed" ]
[ "$(sudo sha256sum "$dest" | cut -d' ' -f1)" = "$expected_base" ] || { echo "REFUSE: deployed file is not the expected baseline; stop"; exit 1; }
[ ! -e "$dest.pre-g2" ] || { echo "REFUSE: backup already exists; stop"; exit 1; }
sudo /usr/bin/cp -p "$dest" "$dest.pre-g2"
sudo /usr/bin/install -o root -g root -m 0644 "$src" "$dest"
[ "$(sudo sha256sum "$dest" | cut -d' ' -f1)" = "$expected_fixed" ]
sudo systemctl restart enhanced-cognee-api.service
for i in $(seq 1 30); do
  [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:28080/health)" = "200" ] && break
  sleep 1
done
systemctl is-active enhanced-cognee-api.service
sudo ls -la /var/lib/private/enhanced-cognee-llm-budget/
)
```
Expected: active; tokens.sqlite3 now present (owner enhanced-cognee-api,
mode 0600). If absent, STOP and report.

## Then E2, E3 (verify-backup now takes --credential), in order
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py verify --owner-name enhanced-cognee-api
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py backup --credential /etc/enhanced-cognee/backup.json
# substitute the stamped ledger path printed above and your age identity:
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py verify-backup \
  --backup /var/backups/enhanced-cognee/ledger-CHANGEME.sqlite3.age \
  --credential /etc/enhanced-cognee/backup.json --identity /PATH/TO/AGE-IDENTITY
```
Expected: overall=pass on all three (E3b: integrity ok, rows 0). If E2/E3
fail: reverse below and keep analysis withheld.

## Then E4 (drop-in was removed during incident recovery; its guard passes now)
Run the E4 sub-block exactly as in CUTOVER-COMMANDS.md Block G (creates the
drop-in directory, installs 40-ledger.conf sha 3eaa5188..., daemon-reload,
NeedDaemonReload=no, start backup service, expect exit 0 and a new
ledger-*.sqlite3.age + manifest).

## Final acceptance
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/cutover_probe_20261105.py usage \
  --api-credential /etc/enhanced-cognee/api.json --origin http://127.0.0.1:28080 \
  --scope hermes_gateway/backend_developer
```
Expected: configured=true, used_today=0, any_charged_today=false. Then one
real summarize call and the /v1/memories/summarization/status check.

## Rollback (any failure)
sudo /usr/bin/cp -p "/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_daemon.py.pre-g2" "/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_daemon.py" && sudo systemctl restart enhanced-cognee-api.service
(restores the exact baseline bytes; the ledger file, if created, is harmless
to keep). To also disable analysis again: remove 50-llm-enable.conf,
daemon-reload, one restart.

## Known fail-closed caveat
If a future reboot assigns a different dynamic UID and systemd does not
re-chown ledger files inside the state dir, the app will fail-closed
(analysis off) rather than risk an un-metered call. Recovery is documented
here; E3/E4 backups cover the ledger.
