"""Actual offline CPU ONNX + Enhanced Cognee LanceDB integration, synthetic sources."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
MODEL = Path(os.environ.get('ENHANCED_TEST_MODEL_DIR', REPO / '.data/hermes-models/bge-small-en-v1.5'))
READY = (MODEL / 'manifest.json').is_file() and all(importlib.util.find_spec(m) for m in ('onnxruntime', 'tokenizers', 'lancedb'))


@unittest.skipUnless(READY, 'Optional actual local model/dependencies unavailable; no download attempted')
class ActualLocalTests(unittest.TestCase):
    def test_real_cls_embeddings_and_semantic_vector_recall_offline(self):
        from hermes_memory import LocalOnnxEmbedder
        from hermes_memory.runtime import EnhancedMemoryEngine
        import numpy as np
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            embedder = LocalOnnxEmbedder(MODEL)
            vectors = embedder.embed(['The kitten enjoys milk.', 'Database backup rotation.'])
            self.assertEqual(embedder.dimension, 384)
            self.assertEqual(embedder.embed_query('kitten'), embedder.embed([
                'Represent this sentence for searching relevant passages: kitten'])[0])
            self.assertEqual(len(vectors), 2)
            for v in vectors:
                self.assertEqual(len(v), 384)
                self.assertTrue(all(math.isfinite(x) for x in v))
                self.assertAlmostEqual(sum(x*x for x in v), 1.0, places=5)
                self.assertGreater(sum(abs(x) for x in v), 0.0)
            # Independent raw ONNX output establishes CLS, not invented mean pooling.
            encoded = embedder._tokenizer.encode_batch(['The kitten enjoys milk.'])
            feeds = {'input_ids': np.array([e.ids for e in encoded], dtype=np.int64),
                     'attention_mask': np.array([e.attention_mask for e in encoded], dtype=np.int64),
                     'token_type_ids': np.array([e.type_ids for e in encoded], dtype=np.int64)}
            raw = embedder._session.run(['last_hidden_state'], feeds)[0][:, 0, :]
            raw = raw / np.linalg.norm(raw, axis=1, keepdims=True)
            np.testing.assert_allclose(vectors[0], raw[0], atol=2e-6)
            with tempfile.TemporaryDirectory(prefix='enhanced-real-local-') as tmp:
                root = Path(tmp) / 'memory'
                engine = EnhancedMemoryEngine(root, embedder)
                fixtures = [('feline', 'A young feline drinks milk and naps on the sofa.'),
                            ('database', 'Rotate encrypted SQL backups every Sunday.'),
                            ('garden', 'The tomato plants need sunlight and fertilizer.')]
                for sid, text in fixtures:
                    engine.upsert(sid, text, 'synthetic:a', {'synthetic': True})
                query = 'What does the kitten drink?'
                hits = engine.search(query, 'synthetic:a')
                self.assertEqual(hits[0]['source_id'], 'feline')
                self.assertEqual(engine.search(query, 'synthetic:b'), [])
                engine.close()
                engine = EnhancedMemoryEngine(root, embedder)
                self.assertEqual(engine.search(query, 'synthetic:a')[0]['source_id'], 'feline')
                engine.withdraw('feline', 'synthetic:a')
                self.assertNotIn('feline', [h['source_id'] for h in engine.search(query, 'synthetic:a')])
                engine.close()
            print('REAL_SEMANTIC_EVIDENCE=' + json.dumps({
                'manifest_sha256': hashlib.sha256((MODEL/'manifest.json').read_bytes()).hexdigest(),
                'dimension': embedder.dimension, 'norms': [math.sqrt(sum(x*x for x in v)) for v in vectors],
                'nonzero_coordinates': [sum(x != 0 for x in v) for v in vectors],
                'query': query, 'hits': hits, 'providers': embedder._session.get_providers(),
                'pooling': 'CLS + L2', 'adapter': 'src.db_adapters.vector_lancedb'}))


if __name__ == '__main__':
    unittest.main()
