# Next owner action: protect the helper, then obtain a read-only plan

Prepared 2026-11-02 for Ubuntu-Hermes. The branch/bundle names retain their
20261101 identity. Do not repeat the completed backend staging or import check.

## Purpose and boundary

Run these blocks only after the matching helper and these instructions have
passed independent source review. Run from your ORDINARY Ubuntu-Hermes terminal;
sudo will ask locally for your password if necessary. Never paste the password.

Block 1 installs only the exact hash-bound, stdlib helper into a NEW protected
helper directory and creates/checks its private future-artifact parent. It does
not install a live unit file. Block 2 reads selected systemd metadata, all four
unit source files and the admitted candidate code as bytes, including the unit
source that the ordinary account cannot read. It does NOT read credential JSON
contents, import application code or start the API.

Neither block installs the proposed API override, runs daemon-reload, restarts
anything, changes profiles, issues credentials, creates a budget ledger or makes
model calls. The running API and its existing model route are unchanged. The
route-OFF fields in the returned plan describe a PROPOSAL, not current service
behaviour. Preparation of the output bundle is a later step after this plan is
checked; live installation/restart is later still and needs its own approval.

If a block fails, preserve its complete output and STOP. Do not retry the
installation, change permissions, edit units or bypass the check. A partial
helper directory is evidence, not permission to remove or overwrite it.

## 1. Install the exact helper only

```bash
(
set -euo pipefail
repo="/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101"
expected="d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"
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
helper=base/"security-first-helper"
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
  "$repo/integrations/hermes/deployment/prepare_security_first_cutover.py" "$expected" |
  /usr/bin/sudo /usr/bin/install -o root -g root -m 0644 /dev/stdin \
    /opt/enhanced-cognee-memory/security-first-helper/prepare_security_first_cutover.py
/usr/bin/sudo /usr/bin/python3 -I -S -B -c '
import hashlib,json,stat,sys
from pathlib import Path
p=Path("/opt/enhanced-cognee-memory/security-first-helper/prepare_security_first_cutover.py")
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

Expected: helper_sha256 matches the exact value above, helper_installed=true,
api_override_installed=false, services_restarted=false. This proves helper
installation only, not an API switch or disabled live model route.

## 2. Obtain the read-only plan

```bash
sudo /usr/bin/python3 -I -S -B \
  /opt/enhanced-cognee-memory/security-first-helper/prepare_security_first_cutover.py \
  --plan
```

Paste the JSON from both blocks, or the complete error if either fails.

Expected: a plan object and a 64-character lowercase plan_sha256. Within the
plan: activated=false, services_restarted=false, ledger_created=false,
credentials_issued=0, installation_pending=true, model_usage_reset=false,
state_directory_proposed=false and model_analysis_expected_enabled=false.
Retained credential NAMES should be api.json and index.json; the omitted NAME
should be llm.json. These names and public source-code/unit hashes are safe to
return; credential values are not requested. Do not invent or edit the digest.

The unknown 20-launch-runtime.conf bytes must pass the supported syntax and
all other preflight checks. A refusal is an explicit stop, not a reason to
weaken the helper or assume the candidate is broken. Do not run --prepare yet.

## Still not authorised or complete

- Live unit installation, daemon-reload and the exact API-only restart window.
- Installed health, preserved canonical/local-embedding/index behaviour and
  actual configured=false analysis status after that eventual restart.
- Shared MCP exact reviewed script installation and targeted connection refresh.
- Persistent DynamicUser-safe budget provisioning, usage handover and tested
  encrypted recovery before optional model analysis can resume.
- Any rollback must preserve withholding of the optional model credential;
  blindly restoring the old complete credential set could undo that policy.
- Fleet activation and the separate 40-role/four-specialist tool changes.
