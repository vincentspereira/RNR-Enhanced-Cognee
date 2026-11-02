"""Create new review-only replay bindings; never edit historical inputs."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
AUDIT = OUT.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((AUDIT / 'parent/round2-review-manifest.json').read_text())
assert all(sha(ROOT / p) == pin for p, pin in manifest['files'].items())
for name in ('copied-original-cases.py', 'copied-review-cases.py', 'test_current_original_cases.py', 'test_current_review_cases.py'):
    data = (AUDIT / 'repair-round1' / name).read_bytes()
    if name == 'test_current_review_cases.py':
        data = data.replace(b'current-review-diagnostics', b'round2-review-diagnostics')
    with (OUT / name).open('xb') as f:
        f.write(data)
owner = (AUDIT / 'OWNER-NEXT-PLAN.md').read_text('ascii')
blocks = re.findall(r'```bash\n(.*?)```', owner, re.S)
assert len(blocks) == 2
pyblocks = re.findall(r"/usr/bin/python3 -I -S -B -c '\n(.*?)'(?=\s)", blocks[0], re.S)
assert len(pyblocks) == 3
records = []
for i, text in enumerate(blocks, 1):
    path = OUT / ('owner-block-%d.sh' % i)
    path.open('x').write(text)
    result = subprocess.run(['/usr/bin/bash', '-n', str(path)], capture_output=True)
    records.append({'kind': 'bash_syntax_only', 'block': i, 'returncode': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode(), 'sha256': sha(path)})
    assert result.returncode == 0
for i, text in enumerate(pyblocks, 1):
    path = OUT / ('owner-python-%d.py' % i)
    path.open('x').write(text + '\n')
    ast.parse(text)
    records.append({'kind': 'python_ast_only', 'block': i, 'sha256': sha(path)})
(OUT / 'command-extraction.json').open('x').write(json.dumps(records, indent=2) + '\n')
print(json.dumps(records, indent=2))
