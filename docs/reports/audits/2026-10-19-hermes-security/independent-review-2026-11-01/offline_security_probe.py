"""Offline audit: AST-extracted endpoint functions and stdlib-only modules.
No project package imports, real sockets, route/environment loading, or services.
All payloads are invented. No credential values are printed or saved.
"""
import ast
import asyncio
import hashlib
import json
from pathlib import Path
import socket
import sys
import threading
import types
from unittest.mock import patch

ROOT = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024')
OUT = Path(__file__).parent
sys.dont_write_bytecode = True

def load_pure(name):
    path = ROOT / 'src' / (name + '.py')
    module = types.ModuleType('audit_' + name)
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    return module

llm = load_pure('llm_summarize')
ing = load_pure('ingestion')
results = {}

# Exercise the actual stdlib connection path; socket operations are invented doubles.
dns_calls = []
connected = []
def fake_resolver(host, port, *args, **kwargs):
    dns_calls.append((host, port))
    address = '93.184.216.34' if len(dns_calls) == 1 else '127.0.0.1'
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, port or 0))]
class FakeSocket:
    def __init__(self, *a, **kw): pass
    def settimeout(self, timeout): pass
    def setsockopt(self, *args): pass
    def connect(self, address): connected.append(address)
    def sendall(self, data): pass
    def close(self): pass
class Response:
    status = 200
    def getheader(self, name): return 'text/plain'
    def read(self, n): return b'invented document'
class FakeResponseConnection(ing.HTTPConnection):
    def getresponse(self): return Response()
with patch.object(socket, 'getaddrinfo', fake_resolver), patch.object(socket, 'socket', FakeSocket), patch.object(ing, 'HTTPConnection', FakeResponseConnection):
    doc, _ = ing.fetch_public_text('http://rebind.audit.test/document', resolver=fake_resolver)
results['ssrf_dns_rebinding'] = {'dns_calls': len(dns_calls), 'connected_to': connected, 'document_returned': doc == 'invented document'}

# Parse only the named nested endpoints, without importing the app or dependencies.
api_path = ROOT / 'src/memory_api.py'
api_tree = ast.parse(api_path.read_text())
create = next(n for n in api_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'create_app')
names = {'summarize', 'consolidation', 'translate', 'ingest'}
funcs = [n for n in create.body if isinstance(n, ast.AsyncFunctionDef) and n.name in names]
for node in funcs: node.decorator_list = []
fragment = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + funcs, type_ignores=[])
ast.fix_missing_locations(fragment)

def endpoints(store, budget, route):
    ns = {'_llm': lambda: (llm, route, budget), 'store': lambda: store,
          'scope': lambda request: types.SimpleNamespace(project='consumer'),
          '_project': lambda request: 'consumer'}
    exec(compile(fragment, str(api_path), 'exec'), ns)
    return ns

class Store:
    def __init__(self):
        self.saved = []
        self.list_args = []
        self.rows = [{'id': 'invented-source', 'project_id': 'publisher', 'shared': True,
                      'version': 7, 'expires_at': '2030-01-01T00:00:00Z',
                      'content': 'Invented confidential project detail.'}]
    async def list_records(self, scope, **kwargs):
        self.list_args.append(kwargs)
        return {'results': self.rows}
    async def remember(self, scope, **kwargs):
        self.saved.append(kwargs)
        return {'id': 'invented-local-summary'}

async def run():
    # Both endpoint requests pass the same budget check before either charge occurs.
    budget = llm.TokenBudget()
    route = {'daily_token_cap': 5000, 'model': 'invented-model'}
    store = Store()
    ep = endpoints(store, budget, route)
    barrier = threading.Barrier(2)
    def held_chat(*a, **kw):
        barrier.wait(timeout=5)
        return ('Invented translated text', 4000)
    body = types.SimpleNamespace(text='invented input', target_language='French')
    with patch.object(llm, 'chat', held_chat):
        replies = await asyncio.gather(ep['translate'](body, object()), ep['translate'](body, object()))
    results['budget_concurrency'] = {'completed_requests': len(replies), 'cap': 5000,
                                     'charged': budget.used('consumer')}

    budget = llm.TokenBudget()
    store = Store()
    ep = endpoints(store, budget, route)
    captured = []
    def summary_chat(route, messages, **kwargs):
        captured.extend(messages)
        return ('Invented confidential project detail.', 100)
    summary_body = types.SimpleNamespace(limit=20, category=None, title=None)
    with patch.object(llm, 'chat', summary_chat):
        await ep['summarize'](summary_body, object())
    store.rows = []  # Simulated source grant revocation, NOT a service operation.
    saved = store.saved[0]
    results['summary_grant_lifecycle'] = {
        'include_shared_requested': store.list_args[0]['include_shared'],
        'foreign_content_in_prompt': any('Invented confidential project detail.' in m['content'] for m in captured),
        'persisted_copy_after_simulated_source_revocation': bool(store.saved),
        'source_ids_or_versions_recorded': any(k in saved['metadata'] for k in ['source_ids', 'source_versions', 'source_records']),
        'expiry_passed_to_remember': 'expires_at' in saved,
        'saved_metadata_keys': sorted(saved['metadata'])}

    # Invented credential-shaped text: no value is printed, saved in a receipt, or transmitted.
    payload = 'password=' + 'invented-placeholder-not-real'
    captured = []
    def translation_chat(route, messages, **kwargs):
        captured.extend(messages)
        return ('Invented translation', 0)
    ep = endpoints(Store(), llm.TokenBudget(), route)
    with patch.object(llm, 'chat', translation_chat):
        await ep['translate'](types.SimpleNamespace(text=payload, target_language='French'), object())
    results['translation_admission'] = {'credential_shaped_input_reached_chat': any(payload in m['content'] for m in captured)}

    # A later chunk can fail after a previous remember succeeds. No real store imported.
    class PartialStore:
        def __init__(self): self.saved = []
        async def remember(self, scope, **kwargs):
            if len(self.saved) == 1: raise ValueError('Invented admission refusal')
            self.saved.append(kwargs)
            return {'id': 'invented-first-chunk'}
    st = PartialStore()
    ep = endpoints(st, None, None)
    fake_src = types.ModuleType('src')
    fake_src.__path__ = []
    with patch.dict(sys.modules, {'src': fake_src, 'src.ingestion': ing}):
        try:
            await ep['ingest'](types.SimpleNamespace(url=None, text='a'*2000+'\n\n'+'b'*2000,
                title=None, category='invented', base_key='audit-key'), object())
        except ValueError:
            results['ingestion_partial_commit'] = {'request_raised': True, 'already_stored': len(st.saved)}

asyncio.run(run())

# Missing usage is accepted and charges zero even though a model call returns text.
class ModelResponse:
    status = 200
    def read(self, n): return json.dumps({'choices': [{'message': {'content': 'invented reply'}}]}).encode()
class ModelConnection:
    def __init__(self, *a, **kw): pass
    def request(self, *a, **kw): pass
    def getresponse(self): return ModelResponse()
    def close(self): pass
with patch.object(llm, 'HTTPSConnection', ModelConnection):
    text, tokens = llm.chat({'base_url':'https://model.audit.test/v1', 'model':'invented', 'api_key':'not-a-real-credential'}, [])
results['budget_missing_usage'] = {'reply_accepted': text == 'invented reply', 'charged_tokens': tokens}

receipt = {'mode':'offline-isolated-invented-data', 'source_sha256': {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [ROOT/'src/ingestion.py', ROOT/'src/llm_summarize.py', api_path]}, 'results': results}
(OUT/'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=True)+'\n')
print(json.dumps(receipt, indent=2, ensure_ascii=True))
