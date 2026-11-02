"""Read-only pytest observation; output only inside this review directory."""
import hashlib
import json
import os
from pathlib import Path

OUT = Path(os.environ['REVIEW_RUN_OUTPUT'])
RECORDS = []

def binding(path):
    p = Path(path).resolve()
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def pytest_collection_finish(session):
    rows = []
    for item in session.items:
        row = {'nodeid': item.nodeid, 'test_source': binding(item.path)}
        mod = item.module
        if hasattr(mod, 'HELPER'):
            row['declared_helper'] = binding(mod.HELPER)
        if hasattr(mod, 'h'):
            row['actual_import'] = binding(mod.h.__file__)
        rows.append(row)
    (OUT / 'collection-bindings.json').write_text(json.dumps(rows, indent=2) + '\n')

def pytest_runtest_logreport(report):
    RECORDS.append({'nodeid': report.nodeid, 'when': report.when, 'outcome': report.outcome})

def pytest_sessionfinish(session, exitstatus):
    (OUT / 'execution-records.json').write_text(json.dumps({'exitstatus': int(exitstatus), 'records': RECORDS}, indent=2) + '\n')
