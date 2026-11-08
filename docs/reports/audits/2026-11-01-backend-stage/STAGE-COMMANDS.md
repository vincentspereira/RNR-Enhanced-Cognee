# Concrete owner commands - stage only, awaiting independent acceptance

Do not run until the independent source-review receipt accepts this exact helper
and command document. These commands prepare a separate candidate only; they do
not activate it, change any service or create a ledger. Keep the existing API
and renewal timer running. Do not repeat the earlier renewal installation.

## 1. Prepare and verify the protected input bundle

Paste this whole block into Vincent's ordinary Ubuntu-Hermes Bash terminal, not
an already-root shell. The payload reader MUST remain unprivileged. It verifies
each exact hash before emitting any bytes, and root install reads only stdin.
This avoids making root follow a mutable checkout symlink to a private file.
A failed reader stops the block; preserve any partial protected bundle and do
not reuse it. Root creates only the fixed staging directories after checking
their existing lexical ancestors. No archive is unpacked.

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/backend-stage-worktree-20261101"
bundle="/opt/enhanced-cognee-memory/staging/audit-c14f595c-20261101"
/usr/bin/test "$(/usr/bin/id -u)" -ne 0
/usr/bin/sudo /usr/bin/python3 -I -S -B -c '
import os,stat
from pathlib import Path
base=Path("/opt/enhanced-cognee-memory")
def check(path):
 for item in [*reversed(path.parents),path]:
  s=item.lstat()
  if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_mode & 0o7022:
   raise SystemExit("Untrusted staging ancestor; stop without weakening permissions")
check(base)
parent=base/"staging"
if not os.path.lexists(parent): parent.mkdir(mode=0o755)
check(parent)
bundle=parent/"audit-c14f595c-20261101"
if os.path.lexists(bundle): raise SystemExit("Bundle exists; preserve it and stop")
bundle.mkdir(mode=0o755)
(bundle/"src").mkdir(mode=0o755)
(bundle/"src/security").mkdir(mode=0o755)
check(bundle/"src/security")'
declare -A expected=(
  ["stage_audit_backend.py"]="3bbe0c2305cc87489cea9c5bd87d68c434414dbf82d5fe484a82ad87699ae0c3"
  ["audit_backend_payload.json"]="801103b2fc3f4a01860ed9cb8d45b7d2d4a45c10e2be0c8c339ea11b415112d7"
  ["src/ingestion.py"]="b814d10674a13ac6e7ed8f1be7de5eec5ae215109dafd85bf524d6f6ba94c32b"
  ["src/llm_summarize.py"]="e78c3c7fae47afe6c6228d6cab7b45387fb375f8c07ca37261a606e79a4010ae"
  ["src/llm_budget.py"]="81a4ddc2ef5aee073b814a428a112cabe3536f4e83cbd7a0e15c83522b8d10a7"
  ["src/memory_api.py"]="4f125fb6d01719440a0b6c614a7767bbe386c73756b19e232e1fd481a7b64dda"
  ["src/memory_daemon.py"]="c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20"
  ["src/memory_library.py"]="9ca8bec14760ca2793b175bf69d088ed1a78eb9a5a06a94a744929ec3aa4ef2f"
  ["src/memory_queries.py"]="be051d645535239d57677a8a9d05bf47929d9c80f5e49d3e3884ea47e9c275a3"
  ["src/security/enterprise_auth.py"]="78cf82b8d052c74438dc85b9b24393128e837dbb8bfee78eda8146dbef66ae1e"
)
for relative in "${!expected[@]}"; do
  case "$relative" in
    stage_audit_backend.py|audit_backend_payload.json)
      source="$repo/integrations/hermes/deployment/$relative" ;;
    src/*) source="$repo/$relative" ;;
    *) exit 1 ;;
  esac
  /usr/bin/python3 -I -S -B -c '
import hashlib,os,sys
if os.geteuid()==0: raise SystemExit("Payload reader must remain unprivileged")
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd,"rb") as stream: data=stream.read()
if hashlib.sha256(data).hexdigest()!=sys.argv[2]: raise SystemExit("Source hash mismatch; no bytes emitted")
sys.stdout.buffer.write(data)' "$source" "${expected[$relative]}" |
    /usr/bin/sudo /usr/bin/install -o root -g root -m 0644 /dev/stdin "$bundle/$relative"
done
/usr/bin/sudo /usr/bin/sha256sum   "$bundle/stage_audit_backend.py"   "$bundle/audit_backend_payload.json"
)
```

Expected final helper and manifest hashes, respectively:

- `3bbe0c2305cc87489cea9c5bd87d68c434414dbf82d5fe484a82ad87699ae0c3`
- `801103b2fc3f4a01860ed9cb8d45b7d2d4a45c10e2be0c8c339ea11b415112d7`

The stdin-install transport was tested as an ordinary user on an invented scratch
file. This does not establish privileged staging or protection on the host.
The root preparation itself has not been run. The helper repeats ownership,
ancestor, manifest and all eight payload-byte checks before cloning.

## 2. Create the candidate, only after step 1 succeeds and hashes match

```bash
sudo /usr/bin/python3 -I -S -B   /opt/enhanced-cognee-memory/staging/audit-c14f595c-20261101/stage_audit_backend.py   --stage
```

Paste its JSON receipt back. Expect complete=true, activated=false,
services_restarted=false, credentials_issued=0 and ledger_created=false. These
are expectations, not a claim that staging has happened. On any error stop,
preserve the partial candidate and send the error; do not delete or rerun into
it. No root privileges or protected-file writes were used to test this recipe.

Do not change ExecStart, restart the API or provision a new empty ledger yet.
Runtime relocation/import checks, legacy current-day usage accounting, private
ledger provisioning and backup/recovery still need a separate reviewed cutover.
