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
