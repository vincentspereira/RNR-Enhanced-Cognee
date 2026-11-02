# V2 next owner actions: new helper installation, then read-only plan

Second/final bounded repair candidate for Ubuntu-Hermes. These commands are
PENDING fresh independent review of the exact helper and this document. Do not
run them until the parent confirms that review passed. This is not source or
runtime acceptance. V1 and the running service remain unchanged.

Use an ORDINARY Ubuntu-Hermes terminal. Authenticate locally if sudo requests
it; never paste a password. Run block 1 once, then block 2 only if block 1 passes.
If anything fails, preserve complete output and STOP. Do not retry installation,
remove partial evidence, overwrite V1, change permissions or edit a live unit.

Block 1 installs only the new hash-bound standalone stdlib V2 helper through an
unprivileged byte reader and trusted root installer. Root never follows the
checkout source path. It refuses an existing new helper directory. The existing
cutover parent must already be root:root 0700; it can be created only if absent.
The future output bundle is not created. Neither block imports application code,
reads credential JSON values, starts the API, changes any profile, provisions a
ledger, makes model calls or changes live service configuration.

## 1. Install NEW V2 helper only

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101"
expected="a8b333c156f03aa32ac3c69d8475f5978f9651bb3547b9ececca61be18e97365"
/usr/bin/test "$(/usr/bin/id -u)" -ne 0
/usr/bin/sudo /usr/bin/python3 -I -S -B -c '
import os,stat
from pathlib import Path
base=Path("/opt/enhanced-cognee-memory")
def directory(path,private=False):
 for item in [*reversed(path.parents),path]:
  s=item.lstat()
  if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_mode & 0o7022:
   raise SystemExit("Untrusted protected ancestor; stop without changing permissions")
 if private and stat.S_IMODE(path.lstat().st_mode)!=0o700:
  raise SystemExit("Existing output parent is not private; stop")
directory(base)
helper=base/"security-first-helper-v2"
if os.path.lexists(helper): raise SystemExit("Helper directory exists; preserve it and stop")
parent=base/"cutover"
if os.path.lexists(parent): directory(parent,private=True)
else:
 parent.mkdir(mode=0o700)
 directory(parent,private=True)
helper.mkdir(mode=0o755)
directory(helper)'
/usr/bin/python3 -I -S -B -c '
import hashlib,os,sys
if os.geteuid()==0: raise SystemExit("Payload reader must remain unprivileged")
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd,"rb") as stream: data=stream.read()
if hashlib.sha256(data).hexdigest()!=sys.argv[2]: raise SystemExit("Source hash mismatch; no bytes emitted")
sys.stdout.buffer.write(data)' \
  "$repo/integrations/hermes/deployment/prepare_security_first_cutover_v2.py" "$expected" |
  /usr/bin/sudo /usr/bin/install -o root -g root -m 0644 /dev/stdin \
    /opt/enhanced-cognee-memory/security-first-helper-v2/prepare_security_first_cutover_v2.py
/usr/bin/sudo /usr/bin/python3 -I -S -B -c '
import hashlib,json,stat,sys
from pathlib import Path
p=Path("/opt/enhanced-cognee-memory/security-first-helper-v2/prepare_security_first_cutover_v2.py")
for item in reversed(p.parents):
 s=item.lstat()
 if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_mode & 0o7022:
  raise SystemExit("Installed helper ancestor check failed; stop")
s=p.lstat()
if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_gid!=0 or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o644:
 raise SystemExit("Installed helper file check failed; stop")
actual=hashlib.sha256(p.read_bytes()).hexdigest()
if actual!=sys.argv[1]: raise SystemExit("Installed helper hash mismatch; stop")
print(json.dumps({"helper_sha256":actual,"helper_installed":True,"api_override_installed":False,"services_restarted":False}))' "$expected"
)
```

Expected: helper_sha256 is a8b333c156f03aa32ac3c69d8475f5978f9651bb3547b9ececca61be18e97365,
helper_installed=true, api_override_installed=false, services_restarted=false.
This proves only the helper installation, not API or route status.

## 2. Obtain the protected read-only plan only

```bash
/usr/bin/sudo /usr/bin/python3 -I -S -B \
  /opt/enhanced-cognee-memory/security-first-helper-v2/prepare_security_first_cutover_v2.py \
  --plan
```

Expected: a plan and lowercase 64-character plan_sha256. The bundle field must
be /opt/enhanced-cognee-memory/cutover/security-first-c14f595c-20261101-v2.
The plan must report activated=false, services_restarted=false,
ledger_created=false, credentials_issued=0, installation_pending=true,
model_usage_reset=false, state_directory_proposed=false and
model_analysis_expected_enabled=false. Retained credential NAMES are api.json
and index.json; omitted NAME is llm.json. These are proposed configuration
fields, not statements about the current live model route.

Return both JSON outputs, or the complete error from the first failing block.
Do not edit/invent a digest. Private 20-launch-runtime.conf bytes/hash remain
unknown to the assistant: the owner-supplied four-line structure is not a copy
of those bytes. All unit source, identity, manager, credential inventory, path
and payload checks must still pass on the protected host. A refusal is a stop.

No artifact preparation or live override installation, reload, restart, model
analysis resumption, credential issue, ledger ownership or fleet activation is
authorised here. The service DynamicUser identity is a name, not a permanent
numeric UID. Those later gates remain separate from this read-only plan.
