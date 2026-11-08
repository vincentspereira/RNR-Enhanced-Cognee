"""Offline stage-only tests. Never invoke a protected interpreter or service."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'integrations/hermes/deployment/stage_audit_backend.py'
MANIFEST = HELPER.with_name('audit_backend_payload.json')


@pytest.fixture
def stage():
    if not HELPER.is_file():
        return None
    spec = importlib.util.spec_from_file_location('stage_backend_under_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_c14_payload(stage):
    assert stage is not None, 'stage-only helper is not implemented'
    manifest = stage.load_manifest(MANIFEST.read_bytes())
    assert manifest['source_commit'] == 'c14f595ccd53f432b455b16f116765d9aa6c9a14'
    assert len(manifest['files']) == 8
    for row in manifest['files']:
        assert hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['new_sha256']
    added = [r['path'] for r in manifest['files'] if r['old_sha256'] is None]
    assert added == ['src/llm_budget.py']


@pytest.mark.parametrize('attack', [
    'unknown', 'missing', 'duplicate', 'nested-duplicate', 'extra-row',
    'missing-row', 'row-field', 'traversal', 'wrong-commit', 'wrong-hash',
    'malformed-hash', 'bool-schema', 'float-schema', 'nan', 'not-object',
])
def test_manifest_is_closed_schema(stage, attack):
    stage.load_manifest(MANIFEST.read_bytes())  # genuine positive control first
    obj = json.loads(MANIFEST.read_bytes())
    if attack == 'unknown':
        obj['environment'] = '/private/config'
    elif attack == 'missing':
        del obj['source_commit']
    elif attack == 'extra-row':
        obj['files'].append(obj['files'][0])
    elif attack == 'missing-row':
        obj['files'].pop()
    elif attack == 'row-field':
        obj['files'][0]['extra'] = True
    elif attack == 'traversal':
        obj['files'][0]['path'] = 'src/../../etc/shadow'
    elif attack == 'wrong-commit':
        obj['source_commit'] = '0' * 40
    elif attack == 'wrong-hash':
        obj['files'][0]['new_sha256'] = '0' * 64
    elif attack == 'malformed-hash':
        obj['files'][0]['old_sha256'] += 'x'
    elif attack == 'bool-schema':
        obj['schema'] = True
    elif attack == 'float-schema':
        obj['schema'] = 1.0
    elif attack == 'not-object':
        obj = []
    data = json.dumps(obj)
    if attack == 'duplicate':
        data = data.replace('"schema": 1', '"schema": 1, "schema": 1')
    elif attack == 'nested-duplicate':
        data = data.replace('"path": "src/ingestion.py"',
                            '"path": "src/ingestion.py", "path": "src/ingestion.py"')
    elif attack == 'nan':
        data = data.replace('"schema": 1', '"schema": NaN')
    with pytest.raises(stage.Rejected):
        stage.load_manifest(data)
