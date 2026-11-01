# Owner next steps - no password sharing

Status: source prepared; NOT installed. Run the upgrade only after the final
independent source-review receipt accepts this exact candidate. The live root
renewal entry point is still the old one until you run and verify the upgrade.

Recommended first action: fix the scheduled root renewal job before its next
Monday 04:00 GMT run. This operation does not rotate a backend credential family,
start a bot, or run renewal. Existing memory tokens remain untouched.

## 1. Review the evidence

In the remediation checkout, read REMEDIATION-STATUS.md and the independent
review result. Inspect the source hashes in owner-renewal-source-hashes-round2.json
(the repaired candidate; do not use the preserved pre-repair hash list). They
must match the staged copies below. The installer refuses an unknown existing
role inventory as well as unknown executable/unit predecessors; absence of the
old inventory or byte-exact desired inventory is permitted.

Do not run the installer from the writable checkout as root. First copy the
reviewed files into a NEW root-owned directory, then verify its hashes. The
installer deliberately refuses writable staging ancestors or unknown installed
predecessors.

## 2. Stage only the reviewed renewal files

Run in Vincent's Ubuntu-Hermes terminal. Do not paste a password into chat.
The stage name must be unused. If it already exists, STOP and inspect it instead
of overwriting it; use a new dated suffix after review.

```bash
(
set -eu
cd /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101
sudo /usr/bin/test ! -e /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101
sudo /usr/bin/install -d -o root -g root -m 0700 /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101
sudo /usr/bin/install -o root -g root -m 0600 \
  integrations/hermes/deployment/install_fleet_token_renewal.py \
  integrations/hermes/deployment/renew_fleet_memory_tokens.py \
  integrations/hermes/deployment/provision_gateway_profile_access.py \
  integrations/hermes/deployment/roles.json \
  /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101/
sudo /usr/bin/sha256sum \
  /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101/install_fleet_token_renewal.py \
  /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101/renew_fleet_memory_tokens.py \
  /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101/provision_gateway_profile_access.py \
  /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101/roles.json
)
```

**STOP unless every hash equals the delivered hash list.** Do not execute an
unmatched staged source or silently accept a changed predecessor.

## 3. Install without running renewal

Only after the hashes match:

```bash
sudo /usr/bin/systemctl stop ec-hermes-memory-token-renew.timer
sudo /usr/bin/python3 -I -B \
  /opt/enhanced-cognee-memory/renewal-audit-upgrade-20261101/install_fleet_token_renewal.py --upgrade
```

Expected: complete=true, installed_not_exercised=true, inventory_profiles=45,
credentials_issued=0, renewal_ran=false, timer_started=false, and a retained backup
path. Actual output must be checked; these are acceptance expectations, not a
claim the command has already run.

If the command refuses or returns complete=false, leave the timer stopped,
preserve its output and all staged/backup files, and send only that sanitised
output. Do not rerun provisioning, delete state or substitute an unreviewed
interpreter. Token expiries were about 28-30 days away at audit time; a stopped
timer still needs a prompt follow-up, not indefinite neglect.

## 4. Verify the exact installed target

These commands reveal paths and status, not credentials:

```bash
sudo /usr/bin/systemctl show ec-hermes-memory-token-renew.service \
  -p ExecStart -p User -p Result -p ExecMainStatus
sudo /usr/bin/sha256sum \
  /opt/enhanced-cognee-memory/fleet-renewal/renew_fleet_memory_tokens.py \
  /opt/enhanced-cognee-memory/fleet-renewal/provision_gateway_profile_access.py \
  /opt/enhanced-cognee-memory/fleet-renewal/roles.json
```

ExecStart must use /usr/bin/python3 -I -B, not a home-directory virtual
environment. Installed hashes must match the reviewed job, provisioner and role
inventory. Result is retained LAST-run metadata; no new renewal was exercised.

After a successful installation and hash/unit readback, resume the existing
approved schedule:

```bash
sudo /usr/bin/systemctl start ec-hermes-memory-token-renew.timer
/usr/bin/systemctl list-timers ec-hermes-memory-token-renew.timer --no-pager
```

Persistent timers can run a missed scheduled slot immediately. Do not manually
start the renewal SERVICE just to obtain a green check. If an immediate catch-up
is not acceptable in that window, leave the timer stopped and tell the reviewer
so a deliberate resume time can be chosen before expiry.

## 5. Rollback/failure handling

The installer stores original scripts/inventory/service unit in its printed
root-owned backup directory. It does not overwrite state.json or any profile.

If readback or runtime preflight fails, stop the renewal timer and preserve the
backup. Do not automatically restore the old unsafe home-directory interpreter.
A rollback that reintroduces F01 is not a safe default. Use the retained source
for diagnosis and a reviewed forward correction; normal memory can continue
with its existing scoped tokens while the scheduled job is held.

## 6. Protected backend discovery before its separate deployment

The analysis/ingestion/API fixes have not been copied into the protected backend.
Do not copy source files blindly into a qualified release or restart it merely
because unit tests passed. First return this bounded, code-only path/hash summary:

```bash
sudo /usr/bin/python3 -I -c 'import hashlib,json,pathlib; root=pathlib.Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529"); rows=[]
for path in root.rglob("memory_api.py"):
 if path.is_file() and not path.is_symlink() and root in path.resolve().parents:
  s=path.stat(); rows.append({"path":str(path),"uid":s.st_uid,"mode":oct(s.st_mode & 511),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
  if len(rows)>=10: break
print(json.dumps(rows,indent=2))'
```

This reads application-code bytes only, not credentials or database records. It
does not execute a project import or contact the API/model. Exact installed
package binding is needed to prepare a versioned, rollback-safe backend upgrade.
No backend promotion command is supplied until that prerequisite is known.

For the new ledger, that upgrade must provision the API unit with:

```ini
[Service]
StateDirectory=enhanced-cognee-llm-budget
StateDirectoryMode=0700
```

The patched daemon supplies the fixed ledger path and model calls fail closed if
it is missing/unsafe. Do not edit root-only llm.json values or rotate its key to
solve a missing ledger. Back up/recover the ledger consistently too; restoring
canonical memory alone does not restore daily usage accounting.

## 7. Still needed after installation

- Original OWNER-CHECKS.md sanitised rotation-receipt and LLM-file protection
  summaries (no values; no family reruns).
- Existing proof of CURRENT gateway/profile backup membership and a dated restore.
- Targeted new-session MCP tests after approved installation; long-lived children
  must not be assumed refreshed by a file replacement.
- The maintained functional_memory_test.py is explicitly opt-in and not run by
  installation. Its --allow-model-fixtures flag allows ONLY its invented inputs.
- A bounded acceptance test of token handoff and restart-mid-renewal, without
  launching fleet bots or reissuing credentials simply for a status badge.

Send the sanitised installation receipt, hash readback and path summary. Do not
send .env files, LLM configuration contents, tokens, recovery keys or passwords.
