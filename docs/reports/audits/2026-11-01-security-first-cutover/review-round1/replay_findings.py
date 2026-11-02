"""Replay only the three independent failing cases; preserve every execution.

Run as an ordinary user with the deployment Python -B. Exit 1 means current
contract violations reproduced. This is not a regression-suite run or live test.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import uuid

import pytest

OUT = Path(__file__).resolve().parent
assert os.geteuid() != 0
run_dir = OUT / ('replay-' + uuid.uuid4().hex)
run_dir.mkdir(mode=0o700)
target = OUT / 'test_independent_challenges.py'
spec = importlib.util.spec_from_file_location('frozen_independent_probes', target)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# Redirect new evidence, not source or input policy. The original files remain.
module.OUT = run_dir
results = []
for name in ['test_L01_installed_site_packages_layout_is_readable',
             'test_L02_candidate_root_decoys_must_not_substitute_for_runtime_modules',
             'test_S01_interpreter_alias_dotdot_must_not_hide_symlink_ancestor']:
    out, err = io.StringIO(), io.StringIO()
    sandbox = run_dir / name
    sandbox.mkdir(mode=0o700)
    record = {'case': name, 'state': 'unexpected_pass'}
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), pytest.MonkeyPatch.context() as mp:
        try:
            function = getattr(module, name)
            if name.startswith('test_S01'):
                function(sandbox, mp)
            else:
                function(mp)
        except BaseException as exc:
            record.update(state='contract_violation_reproduced', exception_type=type(exc).__name__, message=str(exc))
    record.update(stdout=out.getvalue(), stderr=err.getvalue())
    results.append(record)
receipt = {'helper_sha256': hashlib.sha256(module.HELPER.read_bytes()).hexdigest(),
           'challenge_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
           'cases': results, 'replayed_cases': len(results),
           'exit_code': 1 if any(r['state'] == 'contract_violation_reproduced' for r in results) else 0,
           'scope': 'offline synthetic replay, not additional distinct challenge cases'}
with (run_dir / 'replay-receipt.json').open('x', encoding='ascii') as f:
    json.dump(receipt, f, indent=2, sort_keys=True, ensure_ascii=True)
    f.write('\n')
print(json.dumps({'receipt': str(run_dir / 'replay-receipt.json'), 'results': results}, ensure_ascii=True))
sys.exit(receipt['exit_code'])
