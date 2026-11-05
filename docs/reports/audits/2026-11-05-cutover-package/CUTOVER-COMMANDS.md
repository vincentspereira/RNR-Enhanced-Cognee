# Enhanced Cognee backend cutover - sequenced owner commands (2026-11-05)

Status: PREPARED, NOT EXECUTED. No privileged command in this document has
been run by the preparing agent. Everything below is owner-run, paste-and-run,
after independent review of this package (bind acceptance to DELIVERY.json
hashes, not to this prose).

Source lineage: branch codex/enhanced-cognee-cutover-package-20261105, one
commit on top of accepted backend-stage commit 41e4de7a5db99970a7629ef3f274138eef3031e8
(source lineage c14f595ccd53f432b455b16f116765d9aa6c9a14). Candidate under
switch: /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101
(byte-verified at staging; all eight module hashes re-pinned in Block B).

Worktree holding the reviewed files (read-only source for installs):
  repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"

## Scope and hard boundaries

- Only enhanced-cognee-api.service is restarted (exactly once in Block C, and
  once more only in rollback F or enablement G). No other unit, timer, the
  Hermes gateway, profiles, credentials or fleet roles are touched.
- No credential VALUE is ever printed, copied or stored by these commands.
  Root-only files are captured byte-for-byte into root-only 0700 evidence
  storage; terminals and this repository only ever see hashes, sizes and
  systemd property NAMES.
- /etc/enhanced-cognee/llm.json is never opened, read, rotated, moved or
  modified by this procedure. Withholding is achieved purely by not loading
  it into the new daemon (see Block C).
- The old runtime /opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529
  is preserved untouched as rollback evidence.
- Stop-on-mismatch: every block states its expected receipt. If reality
  differs, STOP. Do not retry, repair permissions, edit units or delete
  evidence; preserve the full output and report it.

## MCP / plugin contract (must keep working unchanged) - verified read-only

The Hermes profiles reach this API exclusively through the installed plugin:

- /home/vincentspereira/.hermes/profiles/*/plugins/enhanced_cognee/plugin.yaml
  (all 44 profiles, identical bytes): name enhanced_cognee, version 0.1.0,
  requires_env ENHANCED_COGNEE_ACCESS_TOKEN.
- plugins/enhanced_cognee/client.py permits ONLY paths under /v1/memories
  plus /health/ready, sends Authorization: Bearer <token>,
  Content-Type: application/json, and defaults its origin to
  http://127.0.0.1:28080 (no profile overrides enhanced_cognee.json settings
  were found; the default origin is in effect).
- The new daemon binds exactly that origin: src/memory_daemon.py execs
  uvicorn src.memory_api:app --host 127.0.0.1 --port 28080.
- The new src/memory_api.py still serves every endpoint the plugin calls:
  POST /v1/memories (remember), POST /v1/memories/recall,
  POST /v1/memories/connections, GET /v1/memories/status,
  GET/PATCH /v1/memories/{id}, GET /health/ready.
- The analysis-withholding change affects ONLY endpoints the plugin never
  calls (/v1/memories/summarize, .../consolidation/candidates, .../translate
  return 422 "The model route is not configured for this service";
  /v1/memories/summarization/status returns configured=false).

Therefore no plugin.yaml, client.py, profile setting or gateway change is
needed or permitted by this cutover. Block D4 proves the contract live.

## Block 0 - install the two reviewed helper tools (once, before B)

Purpose: root executions must run installed, hash-verified bytes, not the
writable checkout. No secrets involved.

Preconditions: the worktree checkout matches the pushed branch
(git -C "$repo" log --oneline -1 and git -C "$repo" status --short).

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"
expected_probe="8f523042abffee9192cc230a51b534cc9e988dad2814f7a156465df3d7a66514"
expected_ledger="076a2ff699b67117aace6c4ffe2f84280c13ed95e4810146b0929d4d409b3ff7"
[ "$(sha256sum "$repo/integrations/hermes/deployment/cutover_probe_20261105.py" | cut -d' ' -f1)" = "$expected_probe" ]
[ "$(sha256sum "$repo/integrations/hermes/deployment/ledger_tools_20261105.py" | cut -d' ' -f1)" = "$expected_ledger" ]
for name in cutover_probe_20261105.py ledger_tools_20261105.py; do
  sudo /usr/bin/test ! -e "/opt/enhanced-cognee-memory/cutover/$name" || { echo "REFUSE: $name already installed; stop"; exit 1; }
  sudo /usr/bin/install -o root -g root -m 0644 "$repo/integrations/hermes/deployment/$name" "/opt/enhanced-cognee-memory/cutover/$name"
done
sudo sha256sum /opt/enhanced-cognee-memory/cutover/cutover_probe_20261105.py /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py
)
```

Expected receipt: the final sha256sum prints exactly the two hashes above.
On mismatch: stop; do not overwrite an existing installed copy.

## Block A - rollback evidence capture (BEFORE any change)

Purpose: preserve the exact current unit/drop-in bytes and manager state so
rollback (Block F) can restore byte-identical configuration, and Block D can
prove no other unit restarted. Runs from the ordinary terminal; sudo prompts
locally. Never paste your password into anything but the sudo prompt.

```bash
(
set -euo pipefail
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
ev="/opt/enhanced-cognee-memory/cutover/rollback-evidence-$stamp"
sudo /usr/bin/test ! -e "$ev" || { echo "REFUSE: $ev exists; stop"; exit 1; }
sudo /usr/bin/install -d -o root -g root -m 0700 "$ev"
for f in /etc/systemd/system/enhanced-cognee-api.service \
         /etc/systemd/system/enhanced-cognee-api.service.d/10-protected-stores.conf \
         /etc/systemd/system/enhanced-cognee-api.service.d/20-launch-runtime.conf \
         /etc/systemd/system/enhanced-cognee-api.service.d/30-llm.conf; do
  sudo /usr/bin/install -o root -g root -m 0600 "$f" "$ev/$(basename "$f")"
done
systemctl show enhanced-cognee-api.service -p Id -p ActiveState -p SubState -p MainPID \
  -p ExecStart -p WorkingDirectory -p StateDirectory -p StateDirectoryMode -p LoadCredential \
  -p DynamicUser -p User -p Group -p UMask -p ProtectSystem -p DropInPaths -p NeedDaemonReload \
  | sudo /usr/bin/tee "$ev/systemctl-api-before.txt" >/dev/null
systemctl show enhanced-cognee-postgres.service enhanced-cognee-qdrant.service \
  enhanced-cognee-graph.service enhanced-cognee-cache.service enhanced-cognee-index.service \
  enhanced-cognee-backup.timer -p Id -p ActiveState -p ActiveEnterTimestamp -p NRestarts \
  | sudo /usr/bin/tee "$ev/systemctl-related-units-before.txt" >/dev/null
sudo /usr/bin/bash -c "cd '$ev' && sha256sum enhanced-cognee-api.service 10-protected-stores.conf 20-launch-runtime.conf 30-llm.conf | tee SHA256SUMS.txt"
sudo /usr/bin/bash -c "stat -c '%n %s bytes %U:%G %a' '$ev'/*"
echo "EVIDENCE_DIR=$ev"
)
```

Expected receipt: SHA256SUMS lines equal to these pinned values (they match
the owner's verified 2026-11-03 V3 plan readback):

  af979af033e64fee0dde16a1484ac5eb00ca75282c3478f382599027ec35dba2  enhanced-cognee-api.service
  6ae6c5ebf3ac141c5bd03c8ac6970c308eee4fe5220606b800c2e11f698cee06  10-protected-stores.conf
  bc687eadf7a8da3c3193165df2ea11d222c38b8c9a23b564c9e999eb2109846e  20-launch-runtime.conf
  12f118dd78e34477736a3e4a9db2d5d29bcafb199a77386f58b8cc45b5e60f33  30-llm.conf

plus EVIDENCE_DIR=/opt/enhanced-cognee-memory/cutover/rollback-evidence-<stamp>.
On mismatch of any hash: the live unit drifted since 2026-11-03 - STOP and
re-assess; the captured evidence stays as the new baseline, do not delete it.
Do not cat 20-launch-runtime.conf (or any captured file) to the terminal;
its bytes are root-only evidence. Record EVIDENCE_DIR for Blocks D and F.

## Block B - pre-switch checks (no service changes)

Purpose: prove the candidate is still byte-identical, still importable under
the service identity, and record today's model usage honestly.

### B1 - re-verify candidate bytes

```bash
sudo sha256sum \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/ingestion.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/llm_summarize.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/llm_budget.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_api.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_daemon.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_library.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/memory_queries.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/lib/python3.12/site-packages/src/security/enterprise_auth.py \
 /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/bin/python
```

Expected receipt (any mismatch = STOP):

  b814d10674a13ac6e7ed8f1be7de5eec5ae215109dafd85bf524d6f6ba94c32b  .../src/ingestion.py
  e78c3c7fae47afe6c6228d6cab7b45387fb375f8c07ca37261a606e79a4010ae  .../src/llm_summarize.py
  81a4ddc2ef5aee073b814a428a112cabe3536f4e83cbd7a0e15c83522b8d10a7  .../src/llm_budget.py
  4f125fb6d01719440a0b6c614a7767bbe386c73756b19e232e1fd481a7b64dda  .../src/memory_api.py
  c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20  .../src/memory_daemon.py
  9ca8bec14760ca2793b175bf69d088ed1a78eb9a5a06a94a744929ec3aa4ef2f  .../src/memory_library.py
  be051d645535239d57677a8a9d05bf47929d9c80f5e49d3e3884ea47e9c275a3  .../src/memory_queries.py
  78cf82b8d052c74438dc85e9b24393128e837dbb8bfee78eda8146dbef66ae1e  .../src/security/enterprise_auth.py
  1e4461092175d186c4bcdb19ee2849a45d6e4d8d1f6a871e45f63418d52a4e35  .../runtime/bin/python

### B2 - service-user import re-check (verbatim accepted check)

The historically accepted file
docs/reports/audits/2026-11-01-backend-stage/NEXT-READONLY-SERVICE-USER-CHECK.md
was an untracked evidence document; its exact check block is reproduced
verbatim here so this worktree is self-contained:

```bash
sudo -u enhanced-cognee-api /usr/bin/env -i \
  HOME=/nonexistent PATH=/usr/bin:/bin LANG=C.UTF-8 \
  ENHANCED_LOAD_DOTENV=0 COGNEE_LOG_FILE=false \
  COGNEE_TELEMETRY_ENABLED=0 HF_HUB_OFFLINE=1 \
  /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/bin/python \
  -I -B -c '
import importlib,json,os,pwd,sys
from pathlib import Path
os.chdir("/")
expected=Path("/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime")
uid=os.geteuid()
if uid==0 or uid!=pwd.getpwnam("enhanced-cognee-api").pw_uid or sys.prefix!=str(expected):
 raise SystemExit("Identity or candidate prefix check failed; stop")
names=["src.ingestion","src.llm_summarize","src.llm_budget","src.memory_api","src.memory_daemon","src.memory_library","src.memory_queries","src.security.enterprise_auth"]
for name in names:
 try:
  module=importlib.import_module(name)
  path=expected/"lib/python3.12/site-packages"/Path(*name.split("."))
  path=path.with_suffix(".py")
  if module.__file__!=str(path) or os.access(path,os.W_OK):
   raise RuntimeError("Module path or source permission check failed")
 except Exception as exc:
  print(json.dumps({"complete":False,"failed_module":name,"error_kind":type(exc).__name__}))
  raise SystemExit(1)
print(json.dumps({"complete":True,"uid":uid,"prefix":sys.prefix,"modules_imported":len(names),"correct_module_paths":True,"source_writable":False,"api_started":False,"credentials_passed":False}))'
```

Expected receipt: one JSON line with "complete":true, "modules_imported":8,
"correct_module_paths":true, "source_writable":false, "api_started":false,
"credentials_passed":false. Anything else: STOP with the output; do not
change permissions or retry.

### B3 - current-day usage read from the OLD API status

Purpose: record whether the old daemon's volatile per-day accounting already
charged any model usage today. The probe mints a 10-minute scoped token
in-process from /etc/enhanced-cognee/api.json; the secret and the token are
never printed or stored. Replace TENANT/PROJECT with each real scope that
used optional analysis (repeat --scope per scope).

```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/cutover_probe_20261105.py usage \
  --api-credential /etc/enhanced-cognee/api.json --origin http://127.0.0.1:28080 \
  --scope TENANT/PROJECT
```

Expected receipt: JSON with per-scope configured/used_today and the flags
any_charged_today / any_unknown_scope. Exit code 0. If exit code is 2 the
api.json has no ENHANCED_JWT_SECRET (unexpected) - STOP and report.

HONEST-ABORT RULE (exact): the switch in Block C is NEVER aborted by usage
findings - ordinary memory service is independent of the optional route, and
the switch itself loads no model credential. The rule governs optional
analysis only: if any_charged_today is true, or any_unknown_scope is true
(including scopes you cannot enumerate), then the current UTC day is NOT
clean and optional analysis STAYS WITHHELD past the switch until the first
00:00 UTC boundary that begins a day in which analysis was withheld from the
very start (which Block C guarantees by unloading llm.json). Block G may
only enable analysis at/after such a clean boundary. No arbitrary allowance
reset: the new persistent ledger legitimately starts a clean day at zero
because no model call was possible while withheld. Keep the B3 JSON output
with the cutover evidence.

## Block C - THE SWITCH (one new drop-in, one daemon-reload, ONE api restart)

Purpose: point enhanced-cognee-api.service at the audited candidate
runtime, provision the private persistent state directories, and withhold
the optional model route - all with the smallest exact change: one new
drop-in file. APPROVAL NOTE: this block briefly interrupts memory service
for one restart; run it in the approved window.

The exact bytes installed are the tracked file
docs/reports/audits/2026-11-05-cutover-package/units/40-cutover-candidate.conf
(sha256 f85e6fc63c58aa6275549fb36e4e1bc6ab31808d0af11f5498feac8b31ffd4c7):

  [Service]
  WorkingDirectory=/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101
  ExecStart=
  ExecStart=/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/bin/python -I -B -m src.memory_daemon api
  LoadCredential=
  LoadCredential=api.json:/etc/enhanced-cognee/api.json
  LoadCredential=index.json:/etc/enhanced-cognee/index.json
  StateDirectory=enhanced-cognee-api
  StateDirectory=enhanced-cognee-llm-budget
  StateDirectoryMode=0700

Design notes for reviewers: lines 1-6 are byte-identical to the
independently reviewed V3 proposal (dropin_sha256
40ee1d8b61322c49676666257531953ee7957db086269bbb25a0373ad4619651 in the
owner's 2026-11-03 step-2 plan receipt; removing the three StateDirectory
lines from the file above reproduces that hash exactly). The only addition
is the private state provisioning: StateDirectory=enhanced-cognee-api is the
service-private state root requested for this cutover, and
StateDirectory=enhanced-cognee-llm-budget exists because src/memory_daemon.py
hardcodes ENHANCED_LLM_BUDGET_DB=/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3
whenever an llm credential is loaded - without that directory the ledger can
never initialize when analysis is later enabled. Both directories are
created 0700 by systemd under the DynamicUser identity.

30-llm.conf HANDLING (explicit): /etc/systemd/system/enhanced-cognee-api.service.d/30-llm.conf
is NOT modified, moved, masked or deleted. It remains on disk and still
assigns LoadCredential=llm.json:... - but the later-lexically 40- drop-in
resets the LoadCredential list (the bare "LoadCredential=" line) and re-adds
only api.json and index.json, so NO llm credential reaches the new daemon.
systemctl's merged LoadCredential readback in this block proves it. The file
/etc/enhanced-cognee/llm.json itself is never opened by anyone in this
procedure.

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"
expected="f85e6fc63c58aa6275549fb36e4e1bc6ab31808d0af11f5498feac8b31ffd4c7"
src="$repo/docs/reports/audits/2026-11-05-cutover-package/units/40-cutover-candidate.conf"
[ "$(sha256sum "$src" | cut -d' ' -f1)" = "$expected" ]
dest="/etc/systemd/system/enhanced-cognee-api.service.d/40-cutover-candidate.conf"
[ ! -e "$dest" ] || { echo "REFUSE: $dest already exists; stop"; exit 1; }
sudo /usr/bin/install -o root -g root -m 0644 "$src" "$dest"
[ "$(sudo sha256sum "$dest" | cut -d' ' -f1)" = "$expected" ]
sudo systemctl daemon-reload
[ "$(systemctl show enhanced-cognee-api.service -p NeedDaemonReload --value)" = "no" ]
sudo systemctl restart enhanced-cognee-api.service
systemctl is-active enhanced-cognee-api.service
systemctl show enhanced-cognee-api.service -p ExecStart -p WorkingDirectory \
  -p StateDirectory -p StateDirectoryMode -p LoadCredential -p ActiveState -p SubState -p MainPID
)
```

Expected receipt:
- is-active prints active.
- ExecStart= line contains "/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/bin/python" and "-I -B -m src.memory_daemon api".
- WorkingDirectory=/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101
- StateDirectory=enhanced-cognee-api enhanced-cognee-llm-budget
- StateDirectoryMode=0700
- LoadCredential= shows api.json:/etc/enhanced-cognee/api.json and
  index.json:/etc/enhanced-cognee/index.json and NO llm.json entry.
On ANY mismatch (including the service failing to start): run
  systemctl status enhanced-cognee-api.service --no-pager; sudo journalctl -u enhanced-cognee-api.service -n 80 --no-pager
capture the output, then go to Block F (rollback). Never re-run Block C to
"retry"; a second restart doubles the interruption window.

## Block D - post-switch targeted readbacks (read-only)

Purpose: prove the switch took effect exactly, the plugin contract works,
analysis is withheld, and nothing else moved.

D1 manager state:
```bash
systemctl show enhanced-cognee-api.service -p ActiveState -p SubState -p MainPID \
  -p ExecStart -p WorkingDirectory -p StateDirectory -p StateDirectoryMode -p LoadCredential -p NRestarts
```
Expected: active / running; same ExecStart/WorkingDirectory/StateDirectory
values as Block C; NRestarts=0 (the manual restart is not an auto-restart).

D2 state directories inside the service namespace (root:path 0700):
```bash
pid="$(systemctl show -p MainPID --value enhanced-cognee-api.service)"
sudo /usr/bin/stat -c '%n %U:%G %a' "/proc/$pid/root/var/lib/enhanced-cognee-api" "/proc/$pid/root/var/lib/enhanced-cognee-llm-budget"
```
Expected: both lines end "enhanced-cognee-api:enhanced-cognee-api 700".

D3 health endpoint:
```bash
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:28080/health/ready
```
Expected: HTTP 200 and JSON containing "ready": true.

D4 plugin-path round trip + analysis withholding (token minted in-process,
never printed):
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/cutover_probe_20261105.py verify \
  --api-credential /etc/enhanced-cognee/api.json --origin http://127.0.0.1:28080 \
  --scope TENANT/PROJECT
```
Expected receipt: JSON "overall": "pass" with all five checks true:
health_ready, remember_roundtrip, recall_roundtrip, analysis_withheld_422
(HTTP 422, detail "The model route is not configured for this service"),
analysis_status_configured_false (configured=false). Exit code 0.
The scope should be a real fleet scope so the round trip exercises the same
tenant/project the plugin uses. On fail: capture JSON, go to Block F.

D5 no other units restarted:
```bash
systemctl show enhanced-cognee-postgres.service enhanced-cognee-qdrant.service \
  enhanced-cognee-graph.service enhanced-cognee-cache.service enhanced-cognee-index.service \
  enhanced-cognee-backup.timer -p Id -p ActiveState -p ActiveEnterTimestamp -p NRestarts
```
Expected: identical ActiveEnterTimestamp values to the before-capture in
$ev/systemctl-related-units-before.txt (Block A). Any change = unintended
restart - STOP and investigate before continuing.

## Block E - budget ledger + encrypted backup gate (no api restart)

Purpose: provision and verify the persistent budget ledger under the API
identity and extend the EXISTING encrypted backup service to cover it, plus
prove restore. These are gates for Block G, not for the switch itself.

E1 - one-shot ledger initialization as the service identity (requires the
api service active so the managed account exists):
```bash
sudo -u enhanced-cognee-api /usr/bin/env -i HOME=/nonexistent PATH=/usr/bin:/bin LANG=C.UTF-8 \
  ENHANCED_LLM_BUDGET_DB=/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3 \
  /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101/runtime/bin/python -I -B -c \
  'from src.llm_budget import TokenBudget; b = TokenBudget(); print("LEDGER_INIT_OK", b.path)'
```
Expected: "LEDGER_INIT_OK /var/lib/enhanced-cognee-llm-budget/tokens.sqlite3".
A "model budget ledger path is not service-private" refusal means the state
directory is wrong - STOP; never chmod or chown it manually.

E2 - root readback of the ledger:
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py verify --owner-name enhanced-cognee-api
```
Expected: JSON overall=pass, mode 0600, nlink 1, uid = the API account uid,
table reservations, rows 0.

E3 - encrypted backup + restore verification test (one-shot, manual):
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py backup \
  --credential /etc/enhanced-cognee/backup.json
```
Expected: JSON overall=pass with path=/var/backups/enhanced-cognee/ledger-<stamp>-<id>.sqlite3.age
and a signed manifest. Then, substituting that path and the root-only age
IDENTITY file that pairs with the backup recipient (owner-held; never
printed):
```bash
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py verify-backup \
  --backup /var/backups/enhanced-cognee/ledger-CHANGEME.sqlite3.age --identity /PATH/TO/AGE-IDENTITY
```
Expected: JSON overall=pass, integrity ok, rows 0, ciphertext_sha256 present.
If no private age identity is available to the owner, this gate CANNOT pass:
leave analysis withheld (skip G) and report - do not fabricate verification.

E4 - align the EXISTING backup service (exact owner edit). The current
enhanced-cognee-backup.service is Type=oneshot; a drop-in resets ExecStart,
re-adds the ORIGINAL database backup line unchanged, and appends one ledger
backup step. Install the tracked file
docs/reports/audits/2026-11-05-cutover-package/units/enhanced-cognee-backup-40-ledger.conf
(sha256 3eaa518890356207b33cc3bb5742772b39e6bc2b9eb6bcfdb6888714807f9e22):

  [Service]
  ExecStart=
  ExecStart=/opt/enhanced-cognee-memory/runtime/bin/python -m src.memory_daemon backup
  ExecStart=/usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/ledger_tools_20261105.py backup --ledger /var/lib/enhanced-cognee-llm-budget/tokens.sqlite3 --output-dir /var/backups/enhanced-cognee

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"
expected="3eaa518890356207b33cc3bb5742772b39e6bc2b9eb6bcfdb6888714807f9e22"
src="$repo/docs/reports/audits/2026-11-05-cutover-package/units/enhanced-cognee-backup-40-ledger.conf"
[ "$(sha256sum "$src" | cut -d' ' -f1)" = "$expected" ]
dest="/etc/systemd/system/enhanced-cognee-backup.service.d/40-ledger.conf"
[ ! -e "$dest" ] || { echo "REFUSE: $dest already exists; stop"; exit 1; }
sudo /usr/bin/install -o root -g root -m 0644 "$src" "$dest"
[ "$(sudo sha256sum "$dest" | cut -d' ' -f1)" = "$expected" ]
sudo systemctl daemon-reload
[ "$(systemctl show enhanced-cognee-backup.service -p NeedDaemonReload --value)" = "no" ]
sudo systemctl start enhanced-cognee-backup.service
systemctl status enhanced-cognee-backup.service --no-pager | head -12
sudo ls -la /var/backups/enhanced-cognee | tail -8
)
```

Expected: oneshot run exits 0 (both ExecStart steps), fresh encrypted DB
backup and a new ledger-*.sqlite3.age (+ .json manifest) appear. This runs
the existing daily-backup unit once out of schedule - it only ADDS encrypted
artifacts; it deletes nothing. On failure: remove the drop-in
(sudo rm /etc/systemd/system/enhanced-cognee-backup.service.d/40-ledger.conf
&& sudo systemctl daemon-reload), capture journalctl -u enhanced-cognee-backup.service,
and keep analysis withheld. Install this drop-in only AFTER E1 succeeds -
otherwise the ledger step fails the whole backup unit by design.

## Block F - rollback (emergency only)

WARNING (read first): reverting the binaries does NOT revert spend. Usage
already charged today by either daemon stays charged; ledger rows in
/var/lib/enhanced-cognee-llm-budget stay on disk (do NOT delete them - they
are the accounting record); the old daemon's volatile counter does NOT know
about them. The old runtime has known security defects - rollback is an
emergency measure, not a long-term fallback. Preserve all evidence; removing
the cutover drop-in never touches the old runtime or the evidence directory.

Precondition: $ev = the Block A EVIDENCE_DIR. Verify the four original files
are still byte-identical before trusting the unit files themselves:
```bash
sudo /usr/bin/bash -c "cd '$ev' && sha256sum -c SHA256SUMS.txt"
```
Expected: four OK lines. If any FAILED: restore that file first with
  sudo /usr/bin/install -o root -g root -m 0644 "$ev/<name>" "/etc/systemd/system/enhanced-cognee-api.service.d/<name>"
(or "$ev/enhanced-cognee-api.service" to /etc/systemd/system/enhanced-cognee-api.service
for the fragment) - these restore the exact captured bytes.

Variant F1 - RECOMMENDED rollback (old runtime, analysis STAYS withheld).
Removing 40-cutover-candidate.conf lets 20-launch-runtime.conf re-emerge
(old ExecStart/WorkingDirectory); a minimal replacement drop-in keeps the
credential reset so no LLM credential reaches the OLD daemon either
(preserves the withholding policy; the old code has the same loader):

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"
expected="5495876073e6ff1056e22f9c4597f718fa459e72119f031a200ccb39f511e3d0"
src="$repo/docs/reports/audits/2026-11-05-cutover-package/units/40-llm-withhold.conf"
[ "$(sha256sum "$src" | cut -d' ' -f1)" = "$expected" ]
sudo rm /etc/systemd/system/enhanced-cognee-api.service.d/40-cutover-candidate.conf
sudo /usr/bin/install -o root -g root -m 0644 "$src" /etc/systemd/system/enhanced-cognee-api.service.d/40-llm-withhold.conf
sudo systemctl daemon-reload
sudo systemctl restart enhanced-cognee-api.service
systemctl is-active enhanced-cognee-api.service
systemctl show enhanced-cognee-api.service -p ExecStart -p WorkingDirectory -p LoadCredential
)
```
Expected: active; ExecStart/WorkingDirectory show the OLD candidate
21abf4857ca8dce8e0a3aafc725266c8d3754529; LoadCredential lists api.json and
index.json only (no llm.json).

Variant F2 - FULL restore (old behaviour INCLUDING the optional model
route; only with explicit owner acceptance of old-code risk):
```bash
(
set -euo pipefail
sudo rm -f /etc/systemd/system/enhanced-cognee-api.service.d/40-cutover-candidate.conf \
           /etc/systemd/system/enhanced-cognee-api.service.d/40-llm-withhold.conf \
           /etc/systemd/system/enhanced-cognee-api.service.d/50-llm-enable.conf \
           /etc/systemd/system/enhanced-cognee-backup.service.d/40-ledger.conf
sudo systemctl daemon-reload
sudo systemctl restart enhanced-cognee-api.service
systemctl is-active enhanced-cognee-api.service
systemctl show enhanced-cognee-api.service -p ExecStart -p WorkingDirectory -p LoadCredential
)
```
Expected: active; old ExecStart/WorkingDirectory; LoadCredential including
llm.json (old code re-enables the model route with its VOLATILE in-memory
accounting and known defects - this is why F1 is recommended). One restart
only, api unit only. Optionally re-run Block A to capture a fresh evidence
set reflecting the restored state.

## Block G - later optional-analysis enablement (owner decision, separate window)

NOT part of this cutover. All of the following gates must hold first:

1. Clean UTC-day boundary: the first 00:00 UTC after Block C has passed,
   with analysis withheld the entire time (Block D4 receipt configured=false
   and no 50- drop-in ever installed before this block). If Block B3
   recorded any_charged_today or any_unknown_scope, this rule is what
   protects against an allowance reset - no exceptions, no manual waivers.
2. Block E1-E3 all green: ledger provisioned, verified, and an encrypted
   backup whose restore was proven.
3. Explicit owner approval to resume optional backend model calls. This is a
   deferred credential-wiring DECISION: alternatives include keeping
   analysis withheld indefinitely, or issuing a fresh llm credential before
   enabling. Nothing in this package decides it.

Mechanism (smallest exact change): one drop-in that re-adds the LLM
credential AFTER the 40- reset (lexical order 50 > 40). Its bytes are
  [Service]
  LoadCredential=llm.json:/etc/enhanced-cognee/llm.json
which is byte-identical to the already-deployed 30-llm.conf loader
(sha256 12f118dd78e34477736a3e4a9db2d5d29bcafb199a77386f58b8cc45b5e60f33),
re-applied after the reset. llm.json itself is never opened by this
procedure. When it loads, src/memory_daemon.py automatically sets
ENHANCED_LLM_BUDGET_DB=/var/lib/enhanced-cognee-llm-budget/tokens.sqlite3
(the directory provisioned in Block C), so every model call is ledger-gated.

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105"
expected="12f118dd78e34477736a3e4a9db2d5d29bcafb199a77386f58b8cc45b5e60f33"
src="$repo/docs/reports/audits/2026-11-05-cutover-package/units/50-llm-enable.conf"
[ "$(sha256sum "$src" | cut -d' ' -f1)" = "$expected" ]
dest="/etc/systemd/system/enhanced-cognee-api.service.d/50-llm-enable.conf"
[ ! -e "$dest" ] || { echo "REFUSE: $dest already exists; stop"; exit 1; }
sudo /usr/bin/install -o root -g root -m 0644 "$src" "$dest"
sudo systemctl daemon-reload
sudo systemctl restart enhanced-cognee-api.service
systemctl show enhanced-cognee-api.service -p LoadCredential -p ActiveState
sudo /usr/bin/python3 -I -S -B /opt/enhanced-cognee-memory/cutover/cutover_probe_20261105.py usage \
  --api-credential /etc/enhanced-cognee/api.json --origin http://127.0.0.1:28080 --scope TENANT/PROJECT
)
```

Expected: LoadCredential lists api.json, index.json AND llm.json; active;
the usage probe reports configured=true with used_today=0 for the clean day
(exit 0, any_charged_today=false). Then exercise one real summarize call
from a normal client and confirm /v1/memories/summarization/status reports
the expected cap/usage. ONE restart, api unit only. To reverse enablement:
remove the 50- drop-in, daemon-reload, one restart - analysis returns to
422/configured=false with the ledger rows retained.

## Completion checklist

- [ ] Block 0 helpers installed, hashes matched
- [ ] Block A evidence dir + SHA256SUMS matched pinned values; EVIDENCE_DIR recorded
- [ ] Block B1/B2/B3 receipts green; B3 JSON filed with evidence
- [ ] Block C installed drop-in hash matched; ONE restart; merged properties matched
- [ ] Block D1-D5 all matched (incl. plugin-path round trip, 422 withholding, no other unit restarted)
- [ ] Block E1/E2/E3 green; E4 drop-in installed and oneshot run produced both backups
- [ ] Cutover complete - ordinary memory on the audited candidate, analysis withheld
- [ ] (Later, only if approved) Block G gates checked, enablement receipt filed

Nothing in this package authorizes touching the Hermes gateway, profiles,
the four store units, the fleet, or any credential file's CONTENT.
