
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
directory(helper)