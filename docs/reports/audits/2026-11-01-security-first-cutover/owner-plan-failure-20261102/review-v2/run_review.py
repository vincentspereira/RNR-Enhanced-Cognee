"""Bounded offline runner. Never removes or reuses a pytest basetemp."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

# Parse only JUnit emitted by our own offline pytest subprocess, not external XML.
ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
PYTHON = '/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python'
assert ROOT.name == 'security-first-cutover-worktree-20261101'
assert os.geteuid() != 0
name = sys.argv[1]
tests = sys.argv[2:]
assert tests
run = OUT / (name + '-' + uuid.uuid4().hex)
run.mkdir(mode=0o700)
base = run / 'sandbox'
assert not os.path.lexists(base)
env = dict(os.environ)
for key in ('ENHANCED_CUTOVER_BASELINE_V1', 'PYTEST_ADDOPTS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD'):
    env.pop(key, None)
env.update(PYTHONDONTWRITEBYTECODE='1', REVIEW_RUN_OUTPUT=str(run), PYTHONPATH=str(OUT))
argv = [PYTHON, '-B', '-m', 'pytest', '--confcutdir=tests/unit', '-p', 'no:cacheprovider',
        '-p', 'review_bindings', '--basetemp=' + str(base), '--junitxml=' + str(run / 'junit.xml'), *tests]
with (run / 'stdout.txt').open('xb') as stdout, (run / 'stderr.txt').open('xb') as stderr:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=180)
receipt = {'argv': argv, 'cwd': str(ROOT), 'euid': os.geteuid(), 'exit_code': result.returncode,
           'plugin_autoload': True, 'baseline_switch_unset': True, 'basetemp_previously_absent': True,
           'test_inputs': {p: hashlib.sha256((ROOT / p.split('::', 1)[0]).read_bytes()).hexdigest() for p in tests}}
if (run / 'junit.xml').is_file():
    tree = ET.parse(run / 'junit.xml')
    receipt['junit_suites'] = [dict(s.attrib) for s in tree.iter('testsuite')]
    receipt['cases'] = [{'classname': c.get('classname'), 'name': c.get('name'),
                         'outcome': 'failed' if c.find('failure') is not None else
                         'error' if c.find('error') is not None else
                         'skipped' if c.find('skipped') is not None else 'passed'}
                        for c in tree.iter('testcase')]
receipt['artifacts'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
(run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'run': str(run), 'exit_code': result.returncode, 'junit_suites': receipt.get('junit_suites')}))
sys.exit(result.returncode)
