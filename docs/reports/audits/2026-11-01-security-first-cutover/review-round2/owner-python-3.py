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
print(json.dumps({"helper_sha256":actual,"helper_installed":True,"api_override_installed":False,"services_restarted":False}))
