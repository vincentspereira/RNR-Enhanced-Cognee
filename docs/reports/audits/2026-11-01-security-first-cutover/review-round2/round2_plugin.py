"""Persist full pytest identities/outcomes before reducing output."""
import json
import os
from pathlib import Path

OUT = Path(os.environ['ROUND2_RUN_OUTPUT'])
rows = []


def pytest_collection_finish(session):
    (OUT / 'collected-case-ids.json').open('x').write(json.dumps([item.nodeid for item in session.items], indent=2) + '\n')


def pytest_runtest_logreport(report):
    rows.append(dict(nodeid=report.nodeid, when=report.when, outcome=report.outcome))


def pytest_sessionfinish(session, exitstatus):
    (OUT / 'case-phase-outcomes.json').open('x').write(json.dumps(dict(exitstatus=int(exitstatus), reports=rows), indent=2) + '\n')
