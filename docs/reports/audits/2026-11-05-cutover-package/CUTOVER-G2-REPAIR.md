# CUTOVER-G2-REPAIR - Block G2 owner runbook (after failed G attempt 1, 2026-11-06)

Incident: G attempt 1 loaded llm.json and restarted the api cleanly, but the budget
ledger was never created: in the unit mount namespace /var/lib/enhanced-cognee-llm-budget
is a SYMLINK (systemd DynamicUser layout; real dir at /var/lib/private/...), and
src/llm_budget.py _secure_path refuses symlinked paths by design. Evidence:
nsenter lstat (link: True), /proc/<pid>/mountinfo lines 1051-1053, empty private dir.
E2/E3 failed ENOENT; the E4 drop-in was removed the same day and the backup service
restored to green. 50-llm-enable.conf remains installed and inert (fail-closed verified:
_llm() and budgeted_chat() both refuse without a working ledger).

Fix: bind-mount the real private directory over the symlink path. Unit file
units/45-llm-budget-bind.conf sha256 7c5cfb687071858ea469e77def6ea65b6bb48ad6ea5eeda0dd11e261a36a79cd

This block also corrects three CUTOVER-COMMANDS.md defects found in attempt 1:
(1) wait for health before dependent checks; (2) verify-backup needs --credential;
(3) the usage probe must use the real scope hermes_gateway/backend_developer.

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"
expected="7c5cfb687071858ea469e77def6ea65b6bb48ad6ea5eeda0dd11e261a36a79cd"
src="$repo/docs/reports/audits/2026-11-05-cutover-package/units/45-llm-budget-bind.conf"
[ "$(sha256sum "$src" | cut -d' ' -f1)" = "$expected" ]
dest="/etc/systemd/system/enhanced-cognee-api.service.d/45-llm-budget-bind.conf"
[ ! -e "$dest" ] || { echo "REFUSE: $dest already exists; stop"; exit 1; }
sudo /usr/bin/install -o root -g root -m 0644 "$src" "$dest"
sudo systemctl daemon-reload
sudo systemctl restart enhanced-cognee-api.service
for i in $(seq 1 30); do
  [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:28080/health)" = "200" ] && break
  sleep 1
done
systemctl is-active enhanced-cognee-api.service
sudo ls -la /var/lib/private/enhanced-cognee-llm-budget/
)
```

Expected: active; the directory now contains tokens.sqlite3 created by the app at
startup (owner enhanced-cognee-api, mode 0600). If tokens.sqlite3 is still absent,
STOP and report; do not continue to E2.

Then run E2, E3 (from CUTOVER-COMMANDS.md; E3 verify-backup now takes --credential):
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py verify --owner-name enhanced-cognee-api
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py backup --credential /etc/enhanced-cognee/backup.json
# substitute the stamped ledger path printed above and your age identity:
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py verify-backup \
  --backup /var/backups/enhanced-cognee/ledger-CHANGEME.sqlite3.age \
  --credential /etc/enhanced-cognee/backup.json --identity /PATH/TO/AGE-IDENTITY
```

Then reinstall E4 exactly as in CUTOVER-COMMANDS.md Block G (its guard now passes
because $dest was removed during incident recovery), then the usage probe with the
REAL scope:
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/cutover_probe_20261105.py usage \
  --api-credential /etc/enhanced-cognee/api.json --origin http://127.0.0.1:28080 \
  --scope hermes_gateway/backend_developer
```
Expected: configured=true, used_today=0, any_charged_today=false. Then one real
summarize call and the status check, completing Block G.

Rollback of G2: sudo rm /etc/systemd/system/enhanced-cognee-api.service.d/45-llm-budget-bind.conf
&& sudo systemctl daemon-reload && sudo systemctl restart enhanced-cognee-api.service
(plus the Block G reversal if analysis must be disabled again).
