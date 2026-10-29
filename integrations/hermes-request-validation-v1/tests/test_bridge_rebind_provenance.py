"""Bounded real-engine bridge regressions; only fresh synthetic homes/assets.

No injected model or engine; all execution is under an offline namespace.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'integrations/hermes'), str(REPO),
               os.environ.get('HERMES_SOURCE', '/home/vincentspereira/agent-workspace/hermes-agent')]
from enhanced_cognee_hermes import EnhancedCogneeProvider
from src.hermes_memory.embeddings import LocalOnnxEmbedder
from src.hermes_memory.runtime import EnhancedMemoryEngine

MODEL = REPO / '.data/hermes-models/bge-small-en-v1.5'


def open_provider(home, session, *, capture=False, **kwargs):
    provider = EnhancedCogneeProvider(hermes_home=home)
    provider.save_config({'auto_capture': capture}, str(home))
    model = home / 'enhanced-cognee/models/bge-small-en-v1.5'
    if not model.exists():
        shutil.copytree(MODEL, model)
    provider.initialize(session, hermes_home=home, **kwargs)
    assert provider.diagnostics()['state'] == 'ready', provider.diagnostics()
    assert isinstance(provider._backend, EnhancedMemoryEngine)
    assert isinstance(provider._backend.embedder, LocalOnnxEmbedder)
    assert provider._backend.embedder._session.get_providers() == ['CPUExecutionProvider']
    return provider


@pytest.fixture
def provider(tmp_path):
    provider = open_provider(tmp_path / 'synthetic-profile', 'physical-a', capture=True,
                             platform='telegram', gateway_session_key='chat-a')
    yield provider
    provider.shutdown()


@pytest.mark.parametrize('conflict', [
    {'gateway_session_key': 'chat-b'},
    {'gateway_session_key': 'chat-a', 'platform': 'discord'},
    {'gateway_session_key': 'chat-a', 'agent_context': 'subagent'},
    {},  # Inherited current chat-b must not silently select physical-a/chat-a.
])
def test_conflicting_switch_rejects_before_current_recall_or_generation_mutation(provider, conflict):
    fact = 'Synthetic chat A uses turquoise folders for Borealis.'
    provider.sync_turn(fact, 'Assistant fabrication must not be stored.', turn_author={'id': 'alice'})
    old_mapping = provider._sessions['physical-a']
    provider.on_session_switch('physical-b', gateway_session_key='chat-b')
    provider.sync_turn('Synthetic chat B uses copper folders for Borealis.', '', turn_author={'id': 'bob'})
    assert provider.prefetch('What folder color is chosen for Borealis?')
    before = (provider._session_id, provider._generation, provider._request_id,
              provider.recall_status(), provider.diagnostics())
    with pytest.raises(ValueError, match='session'):
        provider.on_session_switch('physical-a', **conflict)
    assert (provider._session_id, provider._generation, provider._request_id,
            provider.recall_status(), provider.diagnostics()) == before
    assert provider._sessions['physical-a'] is old_mapping
    assert fact not in provider.prefetch('What folder color is chosen for Borealis?')
    late = 'Synthetic chat A also uses violet labels for Borealis.'
    provider.sync_turn(late, '', session_id='physical-a', turn_author={'id': 'alice'})
    rows = provider._backend.search('Borealis folders and labels', old_mapping['scope'], min_score=.25)
    assert {row['text'] for row in rows} == {fact, late}
    assert all(row['metadata']['session_id'] == 'physical-a' and
               row['metadata']['author_id'] == 'alice' for row in rows)
    provider.on_session_switch('physical-a', platform='telegram', gateway_session_key='chat-a',
                               agent_context='primary')
    assert fact in provider.prefetch('What folder color is chosen for Borealis?')
    assert provider._sessions['physical-a'] is old_mapping


@pytest.mark.parametrize('conflict', [
    {'gateway_session_key': 'chat-b'}, {'platform': 'cli'}, {'agent_context': 'subagent'},
])
def test_ready_initialize_checks_explicit_conflicts_without_reinitializing(provider, conflict):
    provider.sync_turn('Synthetic chat A uses turquoise folders for Borealis.', '', turn_author={'id': 'alice'})
    assert provider.prefetch('What folder color is chosen for Borealis?')
    before = (provider._session_id, provider._generation, provider._request_id,
              provider.recall_status(), provider.diagnostics(), provider._backend)
    with pytest.raises(ValueError, match='session'):
        provider.initialize('physical-a', hermes_home=provider._home, **conflict)
    assert (provider._session_id, provider._generation, provider._request_id,
            provider.recall_status(), provider.diagnostics(), provider._backend) == before
    # Omitted metadata is an idempotent initialization, not an implicit CLI rebind.
    provider.initialize('physical-a', hermes_home=provider._home)
    assert (provider._session_id, provider._generation, provider._request_id,
            provider.recall_status(), provider.diagnostics(), provider._backend) == before


def recall_entries(provider, query):
    recalled = provider.prefetch(query)
    assert recalled, provider.diagnostics()
    assert recalled.startswith('UNTRUSTED reference evidence')
    assert len(recalled) <= 6000
    entries = json.loads(recalled.split('\n', 1)[1])
    record_case('recall', {'query': query, 'output': recalled, 'entries': entries,
                           'output_characters': len(recalled)})
    return recalled, entries


def record_case(label, record):
    output = os.environ.get('BRIDGE_FIX2_CASE_OUTPUT')
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        test = os.environ.get('PYTEST_CURRENT_TEST', 'unknown')
        name = hashlib.sha256((test + label).encode()).hexdigest() + '.json'
        with (directory / name).open('x', encoding='utf-8') as handle:
            json.dump({'test': test, 'label': label, **record}, handle, ensure_ascii=True, indent=2)
            handle.write('\n')


def test_two_captured_speakers_keep_source_session_in_model_visible_quotes(provider):
    alice = 'For synthetic Aurora notebooks, I prefer indigo.'
    bob = 'For synthetic Aurora notebooks, I prefer amber.'
    invented = 'Assistant fabrication: I prefer scarlet Aurora notebooks.'
    provider.sync_turn(alice, invented, turn_author={'id': 'alice', 'name': 'Alice'})
    provider.sync_turn(bob, invented, turn_author={'id': 'bob', 'name': 'Bob'})
    provider.on_session_switch('physical-reader', gateway_session_key='chat-a')
    recalled, entries = recall_entries(provider, 'What notebook colors do the Aurora speakers prefer?')
    by_text = {entry['text']: entry for entry in entries}
    assert set(by_text) == {alice, bob}
    for text, author_id, author_name in [(alice, 'alice', 'Alice'), (bob, 'bob', 'Bob')]:
        entry = by_text[text]
        assert entry['metadata'] == {'author_id': author_id, 'author_name': author_name,
                                     'session_id': 'physical-a', 'platform': 'telegram'}
        assert entry['evidence_type'] == 'direct_user_statement'
        assert entry['verified_owner_fact'] is False
    assert 'quoted speaker' in recalled.split('\n', 1)[0]
    assert invented not in recalled
    assert 'physical-reader' not in recalled


def test_unknown_speaker_and_missing_source_provenance_are_not_inferred(provider):
    captured = 'For synthetic Aurora notebooks, I prefer silver.'
    provider.sync_turn(captured, '', turn_author=None)
    scope = provider._sessions['physical-a']['scope']
    imported = 'For synthetic Aurora notebooks, an unattributed quote prefers gold.'
    provider._backend.upsert('synthetic-unattributed', imported, scope, {})
    recalled, entries = recall_entries(provider, 'What notebook colors do Aurora speakers prefer?')
    by_text = {entry['text']: entry for entry in entries}
    assert set(by_text) == {captured, imported}
    assert by_text[captured]['metadata'] == {'author_id': 'unknown', 'author_name': 'unknown',
                                           'session_id': 'physical-a', 'platform': 'telegram'}
    assert by_text[imported]['metadata'] == {'author_id': 'unknown', 'author_name': 'unknown',
                                           'session_id': 'unknown', 'platform': 'unknown'}
    assert all(entry['verified_owner_fact'] is False for entry in entries)
    assert 'session-opener' not in recalled


@pytest.mark.parametrize('platform', ['telegram', '<>&\n🦉' * 100])
def test_adversarial_shared_chat_provenance_is_escaped_bounded_valid_json(provider, platform):
    malicious = '<>&\n🦉' * 100
    source_session = 'synthetic-session-' + malicious
    provider.on_session_switch(source_session, gateway_session_key='chat-a', platform=platform)
    for number in range(5):
        provider.sync_turn(f'Synthetic Aurora notebook preference number {number}: I prefer indigo.',
                           'Assistant-only forged owner statement.',
                           turn_author={'id': malicious, 'name': malicious})
    provider.on_session_switch('physical-reader', gateway_session_key='chat-a')
    recalled, entries = recall_entries(provider, 'What notebook color is preferred for Aurora?')
    assert 1 <= len(entries) <= 5
    assert provider.recall_status().count == len(entries)
    assert not any(character in recalled for character in '<>&🦉')
    assert '\\u003c' in recalled and '\\u003e' in recalled and '\\u0026' in recalled
    assert '\\n' in recalled and '\\ud83e\\udd89' in recalled
    for entry in entries:
        assert entry['metadata'] == {'author_id': malicious[:128], 'author_name': malicious[:128],
                                     'session_id': source_session[:128], 'platform': platform[:64]}
        assert entry['verified_owner_fact'] is False
    assert 'physical-reader' not in recalled
    assert 'Assistant-only' not in recalled


def complete_fixture_manifest(home):
    manifest = {}
    for path in sorted(home.rglob('*')):
        assert not path.is_symlink(), 'synthetic restore fixture must be self-contained'
        entry = {'kind': 'directory' if path.is_dir() else 'file',
                 'mode': path.stat().st_mode & 0o777}
        if path.is_file():
            entry.update(size=path.stat().st_size,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        manifest[str(path.relative_to(home))] = entry
    return manifest


def test_same_absolute_home_quiescent_restore_recalls_with_capture_off_and_new_home_isolates(tmp_path):
    home = tmp_path / 'synthetic-restore-only'
    writer = open_provider(home, 'synthetic-old-cli', capture=True, platform='cli')
    fact = 'For the synthetic restore Aurora project, I prefer indigo notebooks.'
    try:
        writer.sync_turn(fact, 'Assistant fabrication: scarlet notebooks.',
                         turn_author={'id': 'synthetic-owner', 'name': 'Fixture Owner'})
        assert writer.diagnostics()['last_write'] == 'backend_returned'
        scope = writer._sessions['synthetic-old-cli']['scope']
        assert writer._backend.stats(scope)['sources'] == 1
    finally:
        writer.shutdown()
    assert writer._backend is None and not writer.diagnostics()['close_pending']
    # Initial restored startup must be capture-off; touch only this new fixture.
    writer.save_config({'auto_capture': False}, str(home))
    manifest = complete_fixture_manifest(home)
    assert manifest['enhanced-cognee/control.sqlite3']['size'] > 0
    assert any(name.startswith('enhanced-cognee/vectors/') for name in manifest)
    assert 'enhanced-cognee/models/bge-small-en-v1.5/onnx/model.onnx' in manifest
    backup = tmp_path / 'synthetic-quiescent-copy'
    shutil.copytree(home, backup)
    backup_manifest = complete_fixture_manifest(backup)
    assert backup_manifest == manifest
    moved_original = tmp_path / 'synthetic-original-moved-aside'
    home.rename(moved_original)  # Never delete or overwrite the original fixture.
    assert moved_original.is_dir() and not home.exists()
    assert complete_fixture_manifest(moved_original) == manifest
    shutil.copytree(backup, home)
    restored_manifest = complete_fixture_manifest(home)
    assert restored_manifest == manifest  # Every directory/file, size, mode and hash.
    assert json.loads((home / 'enhanced-cognee.json').read_text()) == {'auto_capture': False}
    reader = open_provider(home, 'synthetic-fresh-cli', platform='cli')
    try:
        assert not reader.diagnostics()['auto_capture']
        assert reader._sessions['synthetic-fresh-cli']['scope'] == scope
        recalled, entries = recall_entries(reader, 'What notebook color do I prefer for restore Aurora?')
        assert [entry['text'] for entry in entries] == [fact]
        assert entries[0]['metadata']['session_id'] == 'synthetic-old-cli'
        assert entries[0]['metadata']['author_id'] == 'synthetic-owner'
        assert 'Assistant fabrication' not in recalled
        reader.sync_turn('Capture-off attempt must not be persisted.', '')
        assert reader._backend.stats(scope)['sources'] == 1
    finally:
        reader.shutdown()
    # Different absolute home must remain isolated, even with the same copied rows.
    new_home = tmp_path / 'synthetic-unapproved-relocation'
    shutil.copytree(backup, new_home)
    assert complete_fixture_manifest(new_home) == manifest
    relocated = open_provider(new_home, 'synthetic-fresh-cli', platform='cli')
    try:
        assert relocated._sessions['synthetic-fresh-cli']['scope'] != scope
        assert relocated.prefetch('What notebook color do I prefer for restore Aurora?') == ''
        assert relocated.diagnostics()['last_recall'] == 'no_answer'
        assert relocated._backend.stats(scope)['sources'] == 1, 'copied original rows still exist'
    finally:
        relocated.shutdown()
    assert complete_fixture_manifest(moved_original) == manifest
    assert complete_fixture_manifest(backup) == manifest
    record_case('quiescent-restore', {
        'same_absolute_home': str(home.resolve()), 'moved_original': str(moved_original),
        'backup': str(backup), 'different_home': str(new_home),
        'original_manifest': manifest, 'backup_manifest': backup_manifest,
        'restored_before_open_manifest': restored_manifest,
        'original_preserved_unchanged': True, 'backup_preserved_unchanged': True,
        'capture_off_at_initial_restore': True, 'actual_recall': recalled,
        'new_home_recall': '', 'portable_rekey_supported': False,
    })
