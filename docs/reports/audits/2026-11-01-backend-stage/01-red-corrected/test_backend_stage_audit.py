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
    assert HELPER.is_file(), 'stage-only helper is not implemented'
    spec = importlib.util.spec_from_file_location('stage_backend_under_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_c14_payload(stage):
    manifest = stage.load_manifest(MANIFEST.read_bytes())
    assert manifest['source_commit'] == 'c14f595ccd53f432b455b16f116765d9aa6c9a14'
    assert len(manifest['files']) == 8
    for row in manifest['files']:
        assert hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['new_sha256']
    added = [r['path'] for r in manifest['files'] if r['old_sha256'] is None]
    assert added == ['src/llm_budget.py']
