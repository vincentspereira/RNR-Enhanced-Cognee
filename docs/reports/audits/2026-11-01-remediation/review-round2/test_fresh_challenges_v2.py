"""Fresh offline challenges bound to the frozen round-2 candidate."""
import asyncio
import base64
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

REPO = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101')
sys.path.insert(0, str(REPO))
DEPLOY = REPO / 'integrations/hermes/deployment'


def load(path):
    spec = importlib.util.spec_from_file_location('fresh_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def token_payload(raw):
    return 'a' * 16 + '.' + base64.urlsafe_b64encode(raw.encode()).rstrip(b'=').decode() + '.' + 'a' * 16


@pytest.mark.parametrize('payload', [
    '{"exp":1800000000,"extra":' + '[' * 1100 + '0' + ']' * 1100 + '}',
    '{"exp":' + '[' * 1100 + '0' + ']' * 1100 + '}',
    '{"exp":' + str(10**100) + '}',
    'not-json',
], ids=['deep-unused-claim', 'deep-expiry', 'unsupported-integer', 'malformed-json'])
def test_any_invalid_profile_token_does_not_abort_remaining_profiles(tmp_path, monkeypatch, payload):
    renewal = load(DEPLOY / 'renew_fleet_memory_tokens.py')
    token = token_payload(payload)
    assert 32 <= len(token) < 4096
    monkeypatch.setattr(renewal.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(renewal.os, 'uname', lambda: SimpleNamespace(nodename='Ubuntu-Hermes'))
    monkeypatch.setattr(renewal, 'validate_runtime', lambda: None)
    provisioner = tmp_path / 'provisioner.py'
    provisioner.write_text('# no executable content\n')
    monkeypatch.setattr(renewal, 'PROVISIONER', provisioner)
    monkeypatch.setattr(renewal, 'profiles', lambda: ['default', 'web-researcher'])
    monkeypatch.setattr(renewal, 'load_profile_token', lambda path: token)
    monkeypatch.setattr(renewal, 'STATE', tmp_path / 'state.json')
    attempted = []
    def no_launch(profile):
        attempted.append(profile)
        return {'profile':profile, 'complete':False, 'expires_utc':None, 'error':'invalid_receipt'}
    monkeypatch.setattr(renewal, 'renew', no_launch)
    supported_unused_claim = payload.startswith('{"exp":1800000000,"extra":')
    assert renewal.main() == (0 if supported_unused_claim else 1)
    assert attempted == ([] if supported_unused_claim else ['default', 'web-researcher'])
    state = json.loads(renewal.STATE.read_text())
    assert [r['profile'] for r in state['failed']] == attempted
    assert state['skipped'] == (['default', 'web-researcher'] if supported_unused_claim else [])
    assert token not in renewal.STATE.read_text()


@pytest.mark.parametrize('field', ['bin', 'runtime', 'fixture-parent'])
def test_root_runtime_rejects_writable_lexical_ancestor(tmp_path, monkeypatch, field):
    renewal = load(DEPLOY / 'renew_fleet_memory_tokens.py')
    runtime = tmp_path / 'runtime'
    binary = runtime / 'bin'
    binary.mkdir(parents=True)
    alias = binary / 'python'
    alias.symlink_to(Path('/usr/bin/python3').resolve())
    (runtime / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    provisioner = tmp_path / 'provisioner.py'
    provisioner.write_text('# no executable content\n')
    inventory = tmp_path / 'roles.json'
    inventory.write_bytes((DEPLOY / 'roles.json').read_bytes())
    unsafe = {'bin':binary, 'runtime':runtime, 'fixture-parent':tmp_path}[field]
    unsafe.chmod(0o777)
    real_lstat = Path.lstat
    def ownership_fixture(path):
        values = list(real_lstat(path))
        values[4] = 0
        if path != unsafe:
            values[0] &= ~0o022
        return __import__('os').stat_result(values)
    monkeypatch.setattr(Path, 'lstat', ownership_fixture)
    monkeypatch.setattr(renewal, 'PROVISIONER_PYTHON', alias)
    monkeypatch.setattr(renewal, 'PROVISIONER', provisioner)
    monkeypatch.setattr(renewal, 'INVENTORY', inventory)
    with pytest.raises(ValueError, match='untrusted_runtime_path'):
        renewal.validate_runtime()


@pytest.mark.parametrize('first_reply', [(200, b'null'), (200, b'[]'), (200, b''), (200, b'"private-invented-marker"')])
def test_mcp_invalid_reply_does_not_poison_next_success(monkeypatch, first_reply):
    import io
    from unittest.mock import patch
    mcp = load(REPO / 'integrations/hermes/enhanced_cognee_mcp/server.py')
    replies = iter([first_reply, (200, b'{"ready":true}')])
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args, **kwargs): pass
        def getresponse(self):
            status, raw = next(replies)
            return SimpleNamespace(status=status, read=lambda n: raw)
        def close(self): pass
    monkeypatch.setattr(mcp, 'HTTPConnection', Connection)
    messages = [dict(jsonrpc='2.0', id=n, method='tools/call', params={'name':'get_stats','arguments':{}}) for n in (1,2)]
    output = io.StringIO()
    with patch('sys.stdin', io.StringIO(''.join(json.dumps(m)+'\n' for m in messages))), patch('sys.stdout',output):
        mcp.serve(mcp.handlers('invented-review-placeholder'))
    results = [json.loads(line)['result'] for line in output.getvalue().splitlines()]
    assert results[0]['isError'] is True
    assert not results[1].get('isError', False)
    assert json.loads(results[1]['content'][0]['text']) == {'ready':True}
    assert 'private-invented-marker' not in output.getvalue()


def test_budget_reservation_persists_after_provider_error_without_content(tmp_path, monkeypatch):
    from src import llm_summarize as llm
    budget = llm.TokenBudget(tmp_path / 'tokens.sqlite3')
    text = 'invented-only-payload-marker'
    messages = [{'role':'user', 'content':text}]
    estimate = len(json.dumps(messages, ensure_ascii=False).encode()) + 1024 + 900
    calls = []
    def refuse(*args, **kwargs):
        calls.append(True)
        raise OSError('invented-only-provider-error')
    monkeypatch.setattr(llm, 'chat', refuse)
    with pytest.raises(OSError):
        asyncio.run(llm.budgeted_chat({'daily_token_cap':estimate},budget,'tenant','project',messages))
    reopened = llm.TokenBudget(budget.path)
    assert reopened.used('tenant','project') == estimate
    with pytest.raises(llm.LlmUnavailable):
        asyncio.run(llm.budgeted_chat({'daily_token_cap':estimate},reopened,'tenant','project',messages))
    assert calls == [True]
    assert text.encode() not in budget.path.read_bytes()
