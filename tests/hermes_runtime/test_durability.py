"""Actual LanceDB durability/concurrency with explicitly FAKE embeddings.

These acceptance checks are NOT evidence of semantic retrieval quality.
"""
import importlib.util
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


class FixtureEmbedder:
    dimension = 3
    fingerprint = 'synthetic-concurrency-fixture-v1'
    def embed(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def write_process(root, index, queue):
    from hermes_memory.runtime import EnhancedMemoryEngine
    e = EnhancedMemoryEngine(Path(root), FixtureEmbedder())
    result = e.upsert('shared', f'synthetic revision {index}', 'synthetic:concurrent')
    e.close()
    queue.put(result['revision'])


def crash_after_vector_stage(root):
    from hermes_memory import runtime
    original = runtime.create_client
    def crashing_client(**kwargs):
        client = original(**kwargs)
        original_upsert = client.upsert
        def crash(*args, **kw):
            original_upsert(*args, **kw)
            os._exit(23)
        client.upsert = crash
        return client
    runtime.create_client = crashing_client
    e = runtime.EnhancedMemoryEngine(Path(root), FixtureEmbedder())
    e.upsert('shared', 'synthetic interrupted revision', 'synthetic:concurrent')


@unittest.skipUnless(importlib.util.find_spec('lancedb'), 'Optional LanceDB unavailable')
class DurabilityTests(unittest.TestCase):
    def test_separate_process_writers_have_unique_revisions(self):
        from hermes_memory.runtime import EnhancedMemoryEngine
        context = multiprocessing.get_context('spawn')
        with tempfile.TemporaryDirectory(prefix='enhanced-concurrency-') as tmp:
            root = str(Path(tmp) / 'memory')
            queue = context.Queue()
            processes = [context.Process(target=write_process, args=(root, i, queue)) for i in range(4)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(40)
                self.assertFalse(process.is_alive(), 'Process writer timed out')
                self.assertEqual(process.exitcode, 0)
            revisions = sorted(queue.get(timeout=5) for _ in processes)
            queue.close()
            self.assertEqual(revisions, [1, 2, 3, 4])
            e = EnhancedMemoryEngine(Path(root), FixtureEmbedder())
            self.assertEqual(e.stats('synthetic:concurrent')['revisions'], 4)
            self.assertEqual(len(e.search('synthetic question', 'synthetic:concurrent')), 1)
            e.close()
            print('ACTUAL_LANCE_CONCURRENCY=' + str(revisions) + ' (fake embeddings)')

    def test_process_crash_leaves_uncommitted_vector_unsearchable(self):
        from hermes_memory.runtime import EnhancedMemoryEngine
        context = multiprocessing.get_context('spawn')
        with tempfile.TemporaryDirectory(prefix='enhanced-crash-') as tmp:
            root = Path(tmp) / 'memory'
            e = EnhancedMemoryEngine(root, FixtureEmbedder())
            e.upsert('shared', 'synthetic previous active revision', 'synthetic:concurrent')
            e.close()
            process = context.Process(target=crash_after_vector_stage, args=(str(root),))
            process.start()
            process.join(40)
            self.assertEqual(process.exitcode, 23)
            e = EnhancedMemoryEngine(root, FixtureEmbedder())
            hits = e.search('synthetic question', 'synthetic:concurrent')
            self.assertEqual(hits[0]['text'], 'synthetic previous active revision')
            self.assertEqual(hits[0]['revision'], 1)
            self.assertEqual(e.stats('synthetic:concurrent')['revisions'], 1)
            client = e._client('synthetic:concurrent')
            self.assertEqual(client.count(e._collection('synthetic:concurrent')).count, 2)
            client.close()
            self.assertEqual(e.upsert('shared', 'synthetic subsequent revision', 'synthetic:concurrent')['revision'], 2)
            self.assertEqual(e.search('synthetic question', 'synthetic:concurrent')[0]['revision'], 2)
            e.close()
            print('ACTUAL_LANCE_CRASH_RECOVERY=exit23; orphan excluded; prior revision preserved (fake embeddings)')


if __name__ == '__main__':
    unittest.main()
