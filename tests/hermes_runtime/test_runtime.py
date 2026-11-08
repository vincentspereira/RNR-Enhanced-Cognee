"""Synthetic unit tests: fake embeddings AND fake vector IO, not semantic evidence."""
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


class FakeEmbedder:
    dimension = 3
    def embed(self, texts):
        return [[1.0, 0.0, 0.0] if 'cat' in t else [0.0, 1.0, 0.0] for t in texts]


class FakeVectors:
    stores = {}
    def __init__(self, url):
        self.tables = self.stores.setdefault(url, {})
    def create_collection(self, name, vectors_config):
        self.tables.setdefault(name, {})
    def upsert(self, name, points):
        for p in points:
            self.tables[name][p.id] = p
    def count(self, name):
        return SimpleNamespace(count=len(self.tables[name]))
    def search(self, name, query_vector, limit=5, **kwargs):
        hits = [SimpleNamespace(id=p.id, payload=p.payload,
                    score=sum(x*y for x,y in zip(p.vector, query_vector)))
                for p in self.tables[name].values()]
        return sorted(hits, key=lambda h: -h.score)[:limit]
    def close(self):
        pass


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='enhanced-runtime-')
        self.root = Path(self.tmp.name) / 'memory'
        self.addCleanup(self.tmp.cleanup)
    def engine(self):
        from hermes_memory.runtime import EnhancedMemoryEngine
        return EnhancedMemoryEngine(self.root, FakeEmbedder())

    def test_verified_upsert_recalls_source_with_provenance(self):
        from hermes_memory import runtime
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            engine = self.engine()
            result = engine.upsert('source-1', 'cat care', 'profile:a', {'owner': 'a'})
            self.assertTrue(result['indexed'])
            hits = engine.search('cat', 'profile:a')
            self.assertEqual(hits[0]['source_id'], 'source-1')
            self.assertEqual(hits[0]['text'], 'cat care')
            self.assertEqual(hits[0]['metadata'], {'owner': 'a'})
            self.assertEqual(hits[0]['revision'], 1)
            self.assertGreater(hits[0]['score'], 0.9)
            engine.close()

    def test_untrusted_empty_scope_is_rejected_before_io(self):
        from hermes_memory import runtime
        e = self.engine()
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            for scope in ('', '   ', None):
                for action in (lambda: e.upsert('s', 'cat', scope),
                               lambda: e.search('cat', scope),
                               lambda: e.withdraw('s', scope), lambda: e.stats(scope)):
                    with self.assertRaises(ValueError):
                        action()
        e.close()

    def test_failed_staging_preserves_prior_active_revision(self):
        from hermes_memory import runtime
        class FailingVectors(FakeVectors):
            def upsert(self, name, points):
                super().upsert(name, points)  # crash after durable vector stage
                raise OSError('synthetic interrupted vector write')
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            e = self.engine()
            e.upsert('s', 'cat old', 'a')
            with patch.object(runtime, 'create_client', side_effect=lambda **kw: FailingVectors(kw['url'])):
                with self.assertRaises(OSError):
                    e.upsert('s', 'dog new', 'a')
            e.close()
            e = self.engine()
            self.assertEqual(e.search('dog', 'a')[0]['text'], 'cat old')
            self.assertEqual(e.stats('a')['revisions'], 1)
            e.close()

    def test_thread_writers_serialize_on_one_engine(self):
        from concurrent.futures import ThreadPoolExecutor
        from hermes_memory import runtime
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            e = self.engine()
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda i: e.upsert('s', f'cat revision {i}', 'a'), range(12)))
            self.assertEqual(sorted(r['revision'] for r in results), list(range(1, 13)))
            self.assertEqual(e.stats('a')['revisions'], 12)
            self.assertEqual(len(e.search('cat', 'a')), 1)
            e.close()

    def test_private_root_and_control_file_permissions(self):
        import stat
        e = self.engine()
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.root / 'control.sqlite3').stat().st_mode), 0o600)
        e.close()

    def test_engine_search_uses_local_query_instruction_hook(self):
        from hermes_memory import runtime
        class QueryEmbedder(FakeEmbedder):
            called = False
            def embed_query(self, query):
                self.called = True
                return [1.0, 0.0, 0.0]
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            emb = QueryEmbedder()
            e = runtime.EnhancedMemoryEngine(self.root, emb)
            e.upsert('s', 'cat record', 'a')
            e.search('kitten question', 'a')
            self.assertTrue(emb.called)
            e.close()

    def test_malformed_vectors_and_arguments_fail_closed(self):
        from hermes_memory import runtime
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            e = self.engine()
            for sid, text, meta in [('', 'cat', None), ('s', '', None), ('s', 'cat', [])]:
                with self.assertRaises(ValueError):
                    e.upsert(sid, text, 'a', meta)
            for vector in ([0.0]*3, [1.0], [float('nan')]*3):
                with patch.object(e.embedder, 'embed', return_value=[vector]):
                    with self.assertRaises(ValueError):
                        e.upsert('s', 'cat', 'a')
            self.assertEqual(e.stats('a')['revisions'], 0)
            for limit in (-1, True, 1.5):
                with self.assertRaises(ValueError):
                    e.search('cat', 'a', limit=limit)
            with self.assertRaises(ValueError):
                e.search('cat', 'a', min_score=float('nan'))
            e.close()

    def test_embedding_identity_mismatch_is_rejected_on_restart(self):
        from hermes_memory.runtime import EnhancedMemoryEngine
        emb = FakeEmbedder()
        emb.fingerprint = 'fixture-model-1'
        e = EnhancedMemoryEngine(self.root, emb)
        e.close()
        emb.fingerprint = 'fixture-model-2'
        with self.assertRaises(ValueError):
            EnhancedMemoryEngine(self.root, emb)

    def test_mismatched_vector_readback_cannot_claim_indexed(self):
        from hermes_memory import runtime
        class CorruptVectors(FakeVectors):
            def upsert(self, name, points):
                for p in points:
                    p.payload = {'revision': 999, 'content_hash': 'wrong'}
                super().upsert(name, points)
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: CorruptVectors(kw['url'])):
            e = self.engine()
            with self.assertRaises(RuntimeError):
                e.upsert('s', 'cat', 'a')
            self.assertEqual(e.stats('a')['active'], 0)
            e.close()

    def test_permission_failure_still_releases_process_lock(self):
        import fcntl
        import os
        e = self.engine()
        with patch.object(e, '_secure_files', side_effect=PermissionError('synthetic chmod failure')):
            with self.assertRaises(PermissionError):
                e.stats('a')
        fd = os.open(self.root / 'writer.lock', os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
        e.close()

    def test_vector_directory_symlink_cannot_escape_caller_root(self):
        from hermes_memory.runtime import EnhancedMemoryEngine
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        self.root.mkdir(mode=0o700)
        (self.root / 'vectors').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            EnhancedMemoryEngine(self.root, FakeEmbedder())
        self.assertEqual(list(outside.iterdir()), [])

    def test_revision_lifecycle_and_scope_isolation_survive_restart(self):
        from hermes_memory import runtime
        with patch.object(runtime, 'create_client', side_effect=lambda **kw: FakeVectors(kw['url'])):
            e = self.engine()
            first = e.upsert('s', 'cat first', 'a', {'owner': 'a'})
            self.assertEqual(e.upsert('s', 'cat first', 'a', {'owner': 'a'}), first)
            self.assertEqual(e.upsert('s', 'dog revised', 'a')['revision'], 2)
            e.upsert('s', 'cat other profile', 'b')
            self.assertEqual(e.search('cat', 'a')[0]['text'], 'dog revised')
            self.assertEqual(e.withdraw('s', 'a')['withdrawn'], True)
            self.assertEqual(e.search('cat', 'a'), [])
            self.assertEqual(e.stats('a')['active'], 0)
            e.close()
            e = self.engine()
            self.assertEqual(e.search('cat', 'a'), [])
            self.assertEqual(e.search('cat', 'b')[0]['text'], 'cat other profile')
            self.assertEqual(e.upsert('s', 'cat first', 'a')['revision'], 3)
            self.assertEqual(e.stats('a')['revisions'], 3)
            e.close()


if __name__ == '__main__':
    unittest.main()
