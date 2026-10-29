"""Real offline bridge tests: actual host ABC, engine, LanceDB and pinned ONNX.

Only disposable synthetic homes are provisioned. No injected backend/model,
network, credentials, live configuration, Brain or native memory ingestion.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, os.environ.get('HERMES_SOURCE', '/home/vincentspereira/agent-workspace/hermes-agent'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enhanced_cognee_hermes import EnhancedCogneeProvider
from src.hermes_memory.embeddings import LocalOnnxEmbedder
from src.hermes_memory.runtime import EnhancedMemoryEngine

MODEL = REPO / '.data/hermes-models/bge-small-en-v1.5'


class RealBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='real-bridge-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'synthetic-single-owner-cli'

    def provision(self, home=None, *, capture=False):
        home = home or self.home
        p = EnhancedCogneeProvider(hermes_home=home)
        p.save_config({'auto_capture': capture}, str(home))
        model = home / 'enhanced-cognee/models/bge-small-en-v1.5'
        if not model.exists():
            shutil.copytree(MODEL, model)
        self.addCleanup(p.shutdown)
        return p

    def initialize(self, p, session='session-one', **kwargs) -> EnhancedMemoryEngine:
        p.initialize(session, hermes_home=p._home, **kwargs)
        self.assertEqual(p.diagnostics()['state'], 'ready', p.diagnostics())
        self.assertIsInstance(p._backend, EnhancedMemoryEngine)
        assert isinstance(p._backend, EnhancedMemoryEngine)
        self.assertIsInstance(p._backend.embedder, LocalOnnxEmbedder)
        return p._backend

    def test_default_factory_opens_actual_engine_with_actual_384_dimension_model(self):
        p = self.provision()
        self.assertTrue(p.is_available(), p.unavailable_reason())
        self.assertIsNone(p._backend, 'cheap readiness must not open the model/store')
        self.assertFalse((self.home / 'enhanced-cognee/control.sqlite3').exists())
        engine = self.initialize(p, platform='cli')
        vector = engine.embedder.embed(['Synthetic owner prefers indigo notebooks.'])[0]
        self.assertEqual(len(vector), 384)
        self.assertAlmostEqual(sum(x*x for x in vector), 1.0, places=5)
        self.assertEqual(engine.embedder._session.get_providers(), ['CPUExecutionProvider'])
        self.assertEqual(engine.stats(p._sessions['session-one']['scope'])['dimension'], 384)
        self.assertFalse(p.diagnostics()['auto_capture'])
        p.sync_turn('Must not capture by default.', '')
        self.assertEqual(engine.stats(p._sessions['session-one']['scope'])['sources'], 0)
        p.shutdown()
        self.assertEqual(p.diagnostics()['state'], 'closed')
        self.assertTrue((self.home / 'enhanced-cognee/control.sqlite3').is_file())

    def test_missing_manifest_fails_closed_in_cheap_probe_without_loading_backend(self):
        from unittest.mock import patch
        import enhanced_cognee_hermes.provider as provider_module
        p = self.provision()
        model = self.home / 'enhanced-cognee/models/bge-small-en-v1.5'
        (model / 'manifest.json').rename(model / 'manifest-withheld.json')
        with patch.object(provider_module.importlib, 'import_module',
                          side_effect=AssertionError('cheap probe must not import runtime/model')):
            self.assertFalse(p.is_available(), 'model integrity manifest is a required local asset')
            self.assertIn('model', p.unavailable_reason())
            p.initialize('missing-manifest', hermes_home=self.home)
        self.assertEqual(p.diagnostics()['state'], 'unavailable')
        self.assertIsNone(p._backend)
        self.assertFalse((self.home / 'enhanced-cognee/control.sqlite3').exists())

    def test_keyed_gateway_continuity_keeps_delayed_job_provenance_and_chat_privacy(self):
        p = self.provision(capture=True)
        engine = self.initialize(p, 'old-chat-a', platform='telegram', gateway_session_key='chat-a')
        fact = 'Synthetic chat Alice chooses lavender folders for the Orion project.'
        p.sync_turn(fact, '', session_id='old-chat-a', turn_author={'id': 'alice'})
        self.assertEqual(p.diagnostics()['last_write'], 'backend_returned')
        old_session = p._sessions['old-chat-a']
        p.on_session_switch('new-chat-b', gateway_session_key='chat-b')
        self.assertEqual(p.prefetch('What folder color was chosen for Orion?', session_id='new-chat-b'), '')
        late = 'Synthetic chat Alice also prefers violet labels for Orion.'
        p.sync_turn(late, '', session_id='old-chat-a', turn_author={'id': 'alice'})
        self.assertIs(p._sessions['old-chat-a'], old_session)
        with self.assertRaises(TypeError):
            old_session['scope'] = 'forged'
        rows = engine.search('Orion folder colors and labels', old_session['scope'], min_score=.25)
        self.assertEqual({r['text'] for r in rows}, {fact, late})
        self.assertTrue(all(r['metadata']['session_id'] == 'old-chat-a' and
                            r['metadata']['author_id'] == 'alice' for r in rows))
        self.assertEqual(engine.stats(p._sessions['new-chat-b']['scope'])['sources'], 0)
        p.shutdown()

        resumed = self.provision()
        self.initialize(resumed, 'fresh-chat-a', platform='telegram', gateway_session_key='chat-a')
        self.assertIn(fact, resumed.prefetch('What folder color was chosen for Orion?'))
        self.assertEqual(resumed._sessions['fresh-chat-a']['scope'], old_session['scope'])
        resumed.shutdown()
        isolated = self.provision()
        self.initialize(isolated, 'fresh-chat-b', platform='telegram', gateway_session_key='chat-b')
        self.assertEqual(isolated.prefetch('What folder color was chosen for Orion?'), '')
        # Unknown/unkeyed non-CLI sessions are NOT implicitly a profile owner.
        isolated.on_session_switch('unkeyed-one', gateway_session_key='')
        scope_one = isolated._sessions['unkeyed-one']['scope']
        isolated.on_session_switch('unkeyed-two', gateway_session_key='')
        self.assertNotEqual(isolated._sessions['unkeyed-two']['scope'], scope_one)
        self.assertEqual(isolated.prefetch('What folder color was chosen for Orion?'), '')

    def test_invalid_manifest_remains_honest_not_ready_without_fallback(self):
        p = self.provision()
        manifest_path = self.home / 'enhanced-cognee/models/bge-small-en-v1.5/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['revision'] = 'synthetic-unapproved-revision'
        manifest_path.write_text(json.dumps(manifest))
        # Cheap readiness verifies required paths only; actual construction verifies integrity.
        self.assertTrue(p.is_available())
        p.initialize('invalid-model', hermes_home=self.home)
        self.assertEqual(p.diagnostics()['state'], 'error')
        self.assertIsNone(p._backend)
        self.assertEqual(p.prefetch('Recall synthetic model evidence'), '')
        self.assertFalse((self.home / 'enhanced-cognee/control.sqlite3').exists())

    def test_fresh_cli_provider_recalls_learned_fact_only_in_same_profile(self):
        import types
        from unittest.mock import patch
        # Load the real native module before patch.dict(sys.modules) snapshots it.
        # Restoring that snapshot after a first import would unload its Python wrapper
        # but leave the Rust logger initialized, making the next real import panic.
        import lancedb
        self.assertTrue(callable(lancedb.connect))
        from hermes_constants import set_hermes_home_override, reset_hermes_home_override
        # Stub only config loading: importing host config can re-exec managed Python.
        # The manager, worker, provider, engine and ONNX model remain real.
        config = types.ModuleType('hermes_cli.config')
        setattr(config, 'load_config', lambda: {})
        token = set_hermes_home_override(self.home)
        self.addCleanup(reset_hermes_home_override, token)
        with patch.dict(sys.modules, {'hermes_cli.config': config}):
            from agent.memory_manager import MemoryManager
            writer = self.provision(capture=True)
            old = MemoryManager()
            self.addCleanup(old.shutdown_all)
            old.add_provider(writer)
            old.initialize_all('physical-old', hermes_home=self.home, platform='cli')
            self.assertEqual(writer.diagnostics()['state'], 'ready', writer.diagnostics())
            assert isinstance(writer._backend, EnhancedMemoryEngine)
            fact = 'For the synthetic Aurora project, I prefer indigo notebooks.'
            old.sync_all(fact, 'Invented assistant fact: red notebooks.',
                         session_id='physical-old', turn_author={'id': 'synthetic-owner', 'name': 'Fixture Owner'})
            self.assertTrue(old.flush_pending(timeout=5))
            self.assertEqual(writer.diagnostics()['last_write'], 'backend_returned')
            scope = writer._sessions['physical-old']['scope']
            records = writer._backend.search('What notebook color do I prefer for Aurora?', scope, min_score=.25)
            self.assertEqual([r['text'] for r in records], [fact])
            self.assertEqual(records[0]['metadata']['session_id'], 'physical-old')
            self.assertEqual(records[0]['metadata']['author_id'], 'synthetic-owner')
            self.assertFalse(records[0]['metadata']['verified_owner_fact'])
            old.shutdown_all()

            # Distinct instance and physical ID: this is a new CLI conversation.
            reader = self.provision()
            fresh = MemoryManager()
            self.addCleanup(fresh.shutdown_all)
            fresh.add_provider(reader)
            fresh.initialize_all('physical-fresh', hermes_home=self.home, platform='cli')
            recalled = fresh.prefetch_all('What notebook color do I prefer for Aurora?', session_id='physical-fresh')
            self.assertIn(fact, recalled, reader.diagnostics())
            self.assertIn('UNTRUSTED', recalled)
            self.assertEqual(reader.recall_status().count, 1)
            assert isinstance(reader._backend, EnhancedMemoryEngine)
            self.assertNotIn('Invented assistant fact', recalled)
            self.assertEqual(reader._sessions['physical-fresh']['scope'], scope)
            # Built-in mirror remains a no-op even with a real store.
            reader.on_memory_write('add', 'user', 'Do not ingest native memory')
            self.assertEqual(reader._backend.stats(scope)['sources'], 1)
            fresh.shutdown_all()

        sibling = self.provision(self.home.parent / 'synthetic-other-profile')
        self.initialize(sibling, 'physical-fresh', platform='cli')
        self.assertEqual(sibling.prefetch('What notebook color do I prefer for Aurora?'), '')
        self.assertEqual(sibling.diagnostics()['last_recall'], 'no_answer')
        self.assertNotEqual(sibling._sessions['physical-fresh']['scope'], scope)

        # Same store/home but a keyed chat must not acquire the CLI owner's scope.
        keyed = self.provision()
        self.initialize(keyed, 'physical-fresh', platform='cli', gateway_session_key='synthetic-keyed-chat')
        self.assertEqual(keyed.prefetch('What notebook color do I prefer for Aurora?'), '')
        self.assertEqual(keyed.diagnostics()['last_recall'], 'no_answer')
        self.assertNotEqual(keyed._sessions['physical-fresh']['scope'], scope)


if __name__ == '__main__':
    unittest.main()
