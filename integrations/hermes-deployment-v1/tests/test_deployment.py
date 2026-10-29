"""Native host loading checks; only synthetic data and disposable homes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

CANDIDATE = Path(os.environ.get('DEPLOYMENT_CANDIDATE', Path(__file__).resolve().parents[1]))
HOST = Path('/home/vincentspereira/agent-workspace/hermes-agent')
MODEL = Path('/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/.data/hermes-models/bge-small-en-v1.5')


def run_host(tmp_path, source):
    home = tmp_path / 'home'
    destination = home / 'plugins/enhanced-cognee'
    shutil.copytree(CANDIDATE, destination, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'tests', 'dist'))
    hostile_src = tmp_path / 'src'
    hostile_src.mkdir()
    (hostile_src / '__init__.py').write_text("raise RuntimeError('ambient src must never be imported')\n")
    env = {'PATH': os.environ['PATH'], 'HOME': str(tmp_path), 'HERMES_HOME': str(home),
           'PYTHONDONTWRITEBYTECODE': '1', 'HF_HUB_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false'}
    code = 'import sys\nsys.path.insert(0, ' + repr(str(HOST)) + ')\n' + source
    result = subprocess.run(['unshare', '--user', '--map-root-user', '--net', sys.executable,
                             '-B', '-c', code], cwd=tmp_path, env=env, text=True, capture_output=True)
    (tmp_path / 'host-probe.py').write_text(code)
    (tmp_path / 'host-stdout.jsonl').write_text(result.stdout)
    (tmp_path / 'host-stderr.log').write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.splitlines()[-1])


def test_directory_discovery_and_registration(tmp_path):
    result = run_host(tmp_path, '''
import json
from plugins.memory import list_memory_provider_names, load_memory_provider, find_provider_dir
assert 'enhanced-cognee' in list_memory_provider_names(), 'directory provider not discovered'
p = load_memory_provider('enhanced-cognee', register_skills=False)
assert p is not None, 'native register did not yield provider'
assert p.name == 'enhanced-cognee'
assert p.get_tool_schemas() == []
from agent.memory_manager import MemoryManager
manager = MemoryManager()
manager.add_provider(p)
assert manager.get_provider('enhanced-cognee') is p
assert not p.is_available()
assert 'src' not in sys.modules
manager.shutdown_all()
print(json.dumps({'name': p.name, 'module': type(p).__module__, 'directory': str(find_provider_dir(p.name)), 'schemas': p.get_tool_schemas()}))
''')
    assert result['name'] == 'enhanced-cognee'


def test_default_factory_real_model_storage_isolation(tmp_path):
    home = tmp_path / 'home'
    root = home / 'enhanced-cognee'
    shutil.copytree(MODEL, root / 'models/bge-small-en-v1.5')
    (home / 'enhanced-cognee.json').write_text('{"auto_capture": false}\n')
    result = run_host(tmp_path, '''
import json, os
from pathlib import Path
from plugins.memory import load_memory_provider
home = Path(os.environ['HERMES_HOME'])
p = load_memory_provider('enhanced-cognee', register_skills=False)
assert p is not None
assert p.get_tool_schemas() == []
assert p.is_available(), p.unavailable_reason()
from agent.memory_manager import MemoryManager
manager = MemoryManager()
manager.add_provider(p)
manager.initialize_all('synthetic-first', hermes_home=home, platform='cli')
assert p.diagnostics()['state'] == 'ready', p.diagnostics()
assert p._backend.embedder._session.get_providers() == ['CPUExecutionProvider']
assert not p.diagnostics()['auto_capture']
p.sync_turn('Do not capture synthetic text automatically.', '')
assert p._backend.stats(p._sessions['synthetic-first']['scope'])['sources'] == 0
scope = p._sessions['synthetic-first']['scope']
receipt = p._backend.upsert('synthetic-turn-one', 'The synthetic cobalt project uses a turquoise launch marker.', scope,
                           {'session_id': 'synthetic-first', 'platform': 'cli', 'author_id': 'synthetic-user',
                            'author_name': 'Synthetic User', 'evidence_type': 'direct_user_statement'})
assert receipt['indexed'] is True
manager.shutdown_all()
p = load_memory_provider('enhanced-cognee', register_skills=False)
manager = MemoryManager()
manager.add_provider(p)
manager.initialize_all('synthetic-fresh', hermes_home=home, platform='cli')
recall = manager.prefetch_all('What launch marker does the synthetic cobalt project use?', session_id='synthetic-fresh')
assert 'synthetic-turn-one' in recall, p.diagnostics()
assert 'synthetic-first' in recall and 'synthetic-user' in recall
p.on_session_switch('chat-negative', platform='telegram', gateway_session_key='synthetic-other-chat')
assert p.prefetch('What launch marker does the synthetic cobalt project use?', session_id='chat-negative') == ''
other = home.parent / 'other-home'
other.mkdir()
(other / 'enhanced-cognee.json').write_text('{"auto_capture": false}')
import shutil
shutil.copytree(home / 'enhanced-cognee/models', other / 'enhanced-cognee/models')
q = type(p)(hermes_home=other)
q.initialize('synthetic-other-profile', hermes_home=other, platform='cli')
assert q.diagnostics()['state'] == 'ready', q.diagnostics()
assert q.prefetch('What launch marker does the synthetic cobalt project use?') == ''
assert q._backend.stats(q._sessions['synthetic-other-profile']['scope'])['sources'] == 0
print(json.dumps({'cpu_provider': p._backend.embedder._session.get_providers(), 'module': type(p).__module__,
                  'backend_module': type(p._backend).__module__, 'receipt': receipt, 'recall': recall,
                  'provider_file': sys.modules[type(p).__module__].__file__,
                  'backend_file': sys.modules[type(p._backend).__module__].__file__,
                  'dimension': p._backend.embedder.dimension,
                  'capture': p.diagnostics()['auto_capture'], 'other_chat_empty': True, 'other_profile_empty': True}))
assert 'src' not in sys.modules
manager.shutdown_all(); q.shutdown()
''')
    assert result['capture'] is False
    assert result['other_chat_empty'] and result['other_profile_empty']
