"""Run only explicit authorized inventories, preserving full process evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
PYTHON = '/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python'
assert os.geteuid() != 0
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
mode = sys.argv[1]
if mode == 'historical':
    tests = [OUT / 'test_current_original_cases.py', OUT / 'test_current_review_cases.py', ROOT / 'tests/unit/test_security_first_cutover_review_regressions.py']
elif mode == 'fresh':
    tests = [OUT / 'test_fresh_challenges.py']
else:
    raise SystemExit('unknown inventory')
run = OUT / (mode + '-run')
run.mkdir(mode=0o700)
base = OUT / (mode + '-sandbox')
assert not base.exists()
env = dict(os.environ)
assert env.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '') not in ('1', 'true')
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTHONPATH'] = str(OUT) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
env['ROUND2_RUN_OUTPUT'] = str(run)
assert env.get('CUTOVER_REPAIR_OBSOLETE_FIXTURE', '') != '1'
argv = [PYTHON, '-B', '-m', 'pytest', '--confcutdir=tests/unit', '-p', 'no:cacheprovider', '-p', 'round2_plugin',
        '--basetemp=' + str(base), '--junitxml=' + str(run / 'junit.xml'), *[str(p.relative_to(ROOT)) for p in tests]]
bindings = {str(p.relative_to(ROOT)): sha(p) for p in tests + [ROOT / 'integrations/hermes/deployment/prepare_security_first_cutover.py', ROOT / 'docs/reports/audits/2026-11-01-security-first-cutover/OWNER-NEXT-PLAN.md']}
(run / 'pre-run-bindings.json').open('x').write(json.dumps(bindings, indent=2) + '\n')
with (run / 'process.log').open('xb') as log:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
assert bindings == {p: sha(ROOT / p) for p in bindings}
cases = []
if (run / 'junit.xml').exists():
    for case in ET.parse(run / 'junit.xml').iter('testcase'):
        cases.append(dict(classname=case.attrib.get('classname'), name=case.attrib['name'],
                          state='failed' if case.find('failure') is not None else 'error' if case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'))
receipt = dict(argv=argv, cwd=str(ROOT), euid=os.geteuid(), returncode=result.returncode,
               source_and_test_bindings=bindings, case_count=len(cases), counts={state: sum(c['state'] == state for c in cases) for state in ['passed', 'failed', 'error', 'skipped']}, cases=cases,
               log_sha256=sha(run / 'process.log'), junit_sha256=sha(run / 'junit.xml') if (run / 'junit.xml').exists() else None)
(run / 'process-receipt.json').open('x').write(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k not in ['cases', 'source_and_test_bindings']}, indent=2))
sys.exit(result.returncode)
