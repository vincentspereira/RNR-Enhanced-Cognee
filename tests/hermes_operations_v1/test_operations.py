"""Offline operational drills, not a deployed backup API. Synthetic sources only.
Quiesced copy assumes all publishers stopped; it is not a concurrent snapshot.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'src'))
from hermes_memory.embeddings import LocalOnnxEmbedder
from hermes_memory.runtime import EnhancedMemoryEngine
from hermes_memory.library import Library
MODEL = REPO / '.data/hermes-models/bge-small-en-v1.5'
SCOPE = 'synthetic:operations'

@pytest.fixture(scope='module')
def embedder():
    return LocalOnnxEmbedder(MODEL)


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}

@pytest.mark.parametrize('same_home', [False, True])
def test_complete_quiesced_backup_restore(tmp_path, embedder, same_home):
    home = tmp_path / 'synthetic-home'
    home.mkdir(mode=0o700)
    library = Library.initialize(home / 'sources')
    note = library.create('Synthetic pump cutoff is 11 bar.', title='Pump policy', author='fixture')
    library.update(note['id'], 'Synthetic pump cutoff is 13 bar.', expected_revision=1,
                   author='fixture', reason='Explicit correction')
    engine = EnhancedMemoryEngine(home / 'index', embedder)
    engine.upsert(note['id'], library.read(note['id'])['text'], SCOPE, {'source_revision': 2})
    engine.upsert('withdrawn', 'Synthetic superseded temperature is 90 C.', SCOPE)
    engine.withdraw('withdrawn', SCOPE)
    expected_stats = engine.stats(SCOPE)
    expected_hits = engine.search('pump cutoff', SCOPE)
    expected_history = library.history(note['id'])
    engine.close()  # ALL publishers must be stopped, including library writers.
    shutil.copytree(MODEL, home / 'model')
    original = hashes(home)
    snapshot = tmp_path / 'snapshot'
    shutil.copytree(home, snapshot)
    assert hashes(snapshot) == original
    manifest = tmp_path / 'snapshot-manifest.json'
    manifest.write_text(json.dumps(original, sort_keys=True))
    if same_home:
        home.rename(tmp_path / 'retained-original')
        target = home
    else:
        target = tmp_path / 'portable-new-home'
    shutil.copytree(snapshot, target)
    assert hashes(target) == json.loads(manifest.read_text())
    restored_model = LocalOnnxEmbedder(target / 'model')
    restored = EnhancedMemoryEngine(target / 'index', restored_model)
    assert restored.stats(SCOPE) == expected_stats
    assert restored.search('pump cutoff', SCOPE) == expected_hits
    assert Library(target / 'sources').history(note['id']) == expected_history
    assert restored.search('pump cutoff', 'synthetic:other-owner') == []
    assert 'withdrawn' not in [h['source_id'] for h in restored.search('temperature', SCOPE)]
    assert restored.upsert(note['id'], 'Synthetic pump cutoff is 13 bar.', SCOPE,
                           {'source_revision': 2})['revision'] == 1
    restored.close()
    # Corruption is detected before opening a restore, not silently repaired.
    (snapshot / 'index/control.sqlite3').write_bytes(b'corrupt')
    assert hashes(snapshot) != original


def test_correction_withdrawal_embedding_outage_explicit_retry(tmp_path, embedder):
    engine = EnhancedMemoryEngine(tmp_path / 'index', embedder)
    first = engine.upsert('policy', 'Synthetic cutoff is 11 bar.', SCOPE)
    with patch.object(embedder, 'embed', side_effect=RuntimeError('injected CPU embedding outage')):
        with pytest.raises(RuntimeError, match='outage'):
            engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE)
    assert engine.stats(SCOPE)['revisions'] == 1
    assert engine.search('cutoff', SCOPE)[0]['text'] == 'Synthetic cutoff is 11 bar.'
    second = engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE)
    assert second['revision'] == first['revision'] + 1
    assert engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE) == second
    assert engine.search('cutoff', SCOPE)[0]['text'] == 'Synthetic cutoff is 13 bar.'
    assert engine.withdraw('policy', SCOPE)['withdrawn']
    assert engine.withdraw('policy', SCOPE)['withdrawn']
    assert engine.search('cutoff', SCOPE) == []
    engine.close()
    reopened = EnhancedMemoryEngine(tmp_path / 'index', embedder)
    assert reopened.search('cutoff', SCOPE) == []
    assert reopened.stats(SCOPE)['withdrawn'] == 1
    # Withdrawn text still exists in revision ledger: exclusion is NOT erasure.
    assert reopened._db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0] == 2
    reopened.close()


def test_real_embedding_vector_stage_process_crash_retry(tmp_path, embedder):
    root = tmp_path / 'index'
    engine = EnhancedMemoryEngine(root, embedder)
    engine.upsert('policy', 'Synthetic previous cutoff is 11 bar.', SCOPE)
    engine.close()
    program = '''import os,sys
from pathlib import Path
from hermes_memory.embeddings import LocalOnnxEmbedder
from hermes_memory import runtime
original = runtime.create_client
def crash_client(**kw):
    client = original(**kw)
    write = client.upsert
    def crash(*args, **kwargs):
        write(*args, **kwargs)
        os._exit(23)
    client.upsert = crash
    return client
runtime.create_client = crash_client
e = runtime.EnhancedMemoryEngine(Path(sys.argv[1]), LocalOnnxEmbedder(Path(sys.argv[2])))
e.upsert('policy', 'Synthetic corrected cutoff is 13 bar.', 'synthetic:operations')
'''
    env = dict(os.environ, PYTHONPATH=str(REPO / 'src') + ':' + str(REPO))
    result = subprocess.run([sys.executable, '-c', program, str(root), str(MODEL)], env=env,
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 23, result.stderr
    engine = EnhancedMemoryEngine(root, embedder)
    assert engine.search('cutoff', SCOPE)[0]['revision'] == 1
    assert engine.stats(SCOPE)['revisions'] == 1
    retry = engine.upsert('policy', 'Synthetic corrected cutoff is 13 bar.', SCOPE)
    assert retry['revision'] == 2
    assert engine.upsert('policy', 'Synthetic corrected cutoff is 13 bar.', SCOPE) == retry
    assert engine.stats(SCOPE)['revisions'] == 2
    engine.close()


def test_missing_vector_outage_never_claims_indexed_retry(tmp_path, embedder):
    root = tmp_path / 'index'
    engine = EnhancedMemoryEngine(root, embedder)
    receipt = engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE)
    engine.close()
    (root / 'vectors').rename(tmp_path / 'retained-vectors')
    engine = EnhancedMemoryEngine(root, embedder)
    # Empty Lance collection currently raises ValueError from limit=0, not a
    # typed 'missing vector' RuntimeError. Both operations fail visibly.
    with pytest.raises(ValueError, match='Limit is required'):
        engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE)
    assert engine.stats(SCOPE)['revisions'] == 1
    with pytest.raises(ValueError, match='Limit is required'):
        engine.search('cutoff', SCOPE)
    engine.close()
    (root / 'vectors').rename(tmp_path / 'empty-outage-vectors')
    (tmp_path / 'retained-vectors').rename(root / 'vectors')
    engine = EnhancedMemoryEngine(root, embedder)
    assert engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE) == receipt
    assert engine.search('cutoff', SCOPE)[0]['revision'] == 1
    engine.close()


def test_shutdown_disables_engine_without_deleting_state(tmp_path, embedder):
    root = tmp_path / 'index'
    engine = EnhancedMemoryEngine(root, embedder)
    engine.upsert('policy', 'Synthetic cutoff is 13 bar.', SCOPE)
    engine.close()
    before = hashes(root)
    engine.close()
    with pytest.raises(RuntimeError, match='closed'):
        engine.search('cutoff', SCOPE)
    assert hashes(root) == before
    reopened = EnhancedMemoryEngine(root, embedder)
    assert reopened.search('cutoff', SCOPE)[0]['source_id'] == 'policy'
    reopened.close()


def test_missing_model_explicit_failure_no_fallback(tmp_path):
    with pytest.raises(FileNotFoundError):
        LocalOnnxEmbedder(tmp_path / 'absent-model')
