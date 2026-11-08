"""Independent offline runner. New evidence only; no root/live service calls."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PYTHON = '/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python'
HELPER = 'integrations/hermes/deployment/prepare_security_first_cutover.py'
TEST = 'tests/unit/test_security_first_cutover.py'
PARENT = OUT.parent / 'parent'
PINS = {HELPER: 'cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813', TEST: '4c75858260829750aacb4e659b98a6fac698af88b99dbecb01c8e79683b61777'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(name, value):
    with (OUT / name).open('x', encoding='ascii') as f:
        json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write('\n')

def run(group, test):
    args = [PYTHON, '-B', '-m', 'pytest', '--confcutdir=tests/unit', '-p', 'no:cacheprovider', test,
            '--basetemp=' + str(OUT / (group + '-sandbox')), '--junitxml=' + str(OUT / (group + '.xml')), '-q']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    assert not env.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'), 'required plugin environment must remain enabled'
    p = subprocess.run(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    for suffix, data in [('stdout', p.stdout), ('stderr', p.stderr)]:
        with (OUT / (group + '.' + suffix)).open('xb') as f:
            f.write(data)
    cases = []
    if (OUT / (group + '.xml')).exists():
        for c in ET.parse(OUT / (group + '.xml')).iter('testcase'):
            state = 'passed'
            for result in ('failure', 'error', 'skipped'):
                if c.find(result) is not None:
                    state = result
            cases.append({'classname': c.get('classname'), 'name': c.get('name'), 'state': state})
    receipt = {'command': args, 'cwd': str(ROOT), 'exit_code': p.returncode,
               'stdout_sha256': sha(p.stdout), 'stderr_sha256': sha(p.stderr),
               'source_hashes': {k: sha((ROOT / k).read_bytes()) for k in PINS},
               'test_sha256': sha((ROOT / test).read_bytes()), 'cases': cases,
               'counts': {s: sum(c['state'] == s for c in cases) for s in ('passed', 'failure', 'error', 'skipped')},
               'distinct_cases': len({(c['classname'], c['name']) for c in cases})}
    save(group + '-receipt.json', receipt)
    print(group, json.dumps({k: receipt[k] for k in ('exit_code', 'counts', 'distinct_cases')}))

if __name__ == '__main__':
    assert os.geteuid() != 0
    assert ROOT / HELPER != Path(HELPER)
    for path, expected in PINS.items():
        assert sha((ROOT / path).read_bytes()) == expected, path
    if sys.argv[1:] == ['initial']:
        archive = PARENT / 'round1-source.zip'
        assert sha(archive.read_bytes()) == 'ff21c524ac91e1fdb426de8c7c4c2ec4533c94bc554252282bf0efedd495196b'
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            members = {n: sha(z.read(n)) for n in z.namelist() if not n.endswith('/')}
        save('initial-bindings.json', {'source_hashes': PINS, 'archive_sha256': sha(archive.read_bytes()), 'archive_members': members,
             'parent_manifest_sha256': sha((PARENT / 'round1-review-manifest.json').read_bytes()), 'euid': os.geteuid()})
        # Inspect only exact named public paths, metadata only.
        candidate = '/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101'
        paths = [candidate, candidate + '/src/memory_api.py', candidate + '/runtime/lib/python3.12/site-packages/src/memory_api.py', candidate + '/runtime/bin/python', candidate + '/runtime/pyvenv.cfg', '/opt/enhanced-cognee-memory/python']
        metadata = {}
        for path in paths:
            try:
                s = os.lstat(path)
                metadata[path] = {'present': True, 'mode': oct(stat.S_IMODE(s.st_mode)), 'uid': s.st_uid, 'gid': s.st_gid,
                                  'kind': stat.S_IFMT(s.st_mode), 'readlink': os.readlink(path) if stat.S_ISLNK(s.st_mode) else None}
            except FileNotFoundError:
                metadata[path] = {'present': False}
        save('deployed-layout-metadata.json', metadata)
        scan = {}
        for path in PINS:
            text = (ROOT / path).read_text()
            tree = ast.parse(text)
            calls = []
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append({'line': node.lineno, 'statement': ast.get_source_segment(text, node)})
                if isinstance(node, ast.Call):
                    name = ast.unparse(node.func)
                    if any(s in name for s in ('eval', 'exec', 'pickle', 'system', 'subprocess', 'execute', 'write', 'open', 'mkdir', 'unlink', 'rmtree')):
                        calls.append({'line': node.lineno, 'call': name, 'shell_true': any(k.arg == 'shell' and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords)})
            scan[path] = {'imports': imports, 'sensitive_calls': calls, 'non_ascii': not text.isascii()}
        save('static-scan.json', scan)
        run('regressions', TEST)
    elif sys.argv[1:] == ['challenges']:
        run('challenges', str((OUT / 'test_independent_challenges.py').relative_to(ROOT)))
    else:
        raise SystemExit('use initial or challenges')
