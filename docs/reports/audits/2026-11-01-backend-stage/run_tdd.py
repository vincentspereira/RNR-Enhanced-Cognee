"""Run only the new offline suite; retain exact commands, source and receipts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
label = sys.argv[1]
if not label.replace('-', '').isalnum():
    raise SystemExit('invalid evidence label')
folder = OUT / label
folder.mkdir(exist_ok=False)
paths = ['integrations/hermes/deployment/stage_audit_backend.py',
         'integrations/hermes/deployment/audit_backend_payload.json',
         'tests/unit/test_backend_stage_audit.py']
bindings = {}
for name in paths:
    path = ROOT / name
    if path.exists():
        data = path.read_bytes()
        (folder / path.name).write_bytes(data)
        bindings[name] = hashlib.sha256(data).hexdigest()
    else:
        bindings[name] = None
command = ['../.venv-deployment/bin/python', '-B', '-m', 'pytest',
           '--confcutdir=tests/unit', 'tests/unit/test_backend_stage_audit.py', '-q',
           '--junitxml=' + str(folder / 'junit.xml')] + sys.argv[2:]
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
(folder / 'output.txt').write_text(result.stdout + result.stderr)
receipt = {'command': command, 'cwd': str(ROOT), 'returncode': result.returncode,
           'bindings': bindings}
(folder / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
print(result.stdout + result.stderr)
raise SystemExit(result.returncode)
