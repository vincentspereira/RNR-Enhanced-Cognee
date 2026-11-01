"""Read-only candidate challenges. All writable fixtures stay in reviewer scratch.
Run with candidate deployment Python, -B, pytest -c /dev/null --confcutdir=<scratch>.
No service, network, model, credential, or privileged process is launched.
"""
import asyncio
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

import pytest

REPO = Path('/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/audit-remediation-worktree-20261101')
sys.path.insert(0, str(REPO))
DEPLOY = REPO / 'integrations/hermes/deployment'


def load(path):
    spec = importlib.util.spec_from_file_location('review_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Keep real path resolution and symlink/type bits. Simulate a root-owned,
# non-writable staged tree, except specifically marked real 0777 directories.
# The initial harness kept unrelated inherited 0775/0664 modes and therefore
# rejected even its positive control; v2 removes that fixture-only interference.
# No actual ownership or ancestor mode is changed.
REAL_LSTAT = Path.lstat
SYNTHETIC_UNSAFE_PATHS = set()

def synthetic_root_lstat(path):
    info = REAL_LSTAT(path)
    values = list(info)
    values[4] = 0  # st_uid
    if path not in SYNTHETIC_UNSAFE_PATHS:
        values[0] &= ~0o022
    return os.stat_result(values)


def setup_renewal_tree(tmp_path):
    runtime = tmp_path / 'runtime'
    binary_dir = runtime / 'bin'
    binary_dir.mkdir(parents=True, mode=0o755)
    alias = binary_dir / 'python'
    alias.symlink_to(Path('/usr/bin/python3').resolve())
    (runtime / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    provisioner = tmp_path / 'provision_gateway_profile_access.py'
    provisioner.write_bytes((DEPLOY / provisioner.name).read_bytes())
    inventory = tmp_path / 'roles.json'
    inventory.write_bytes((DEPLOY / 'roles.json').read_bytes())
    return alias, provisioner, inventory


def test_root_runtime_positive_control(tmp_path, monkeypatch):
    renewal = load(DEPLOY / 'renew_fleet_memory_tokens.py')
    alias, provisioner, inventory = setup_renewal_tree(tmp_path)
    monkeypatch.setattr(renewal, 'PROVISIONER_PYTHON', alias)
    monkeypatch.setattr(renewal, 'PROVISIONER', provisioner)
    monkeypatch.setattr(renewal, 'INVENTORY', inventory)
    monkeypatch.setattr(Path, 'lstat', synthetic_root_lstat)
    renewal.validate_runtime()


def test_root_runtime_rejects_replaceable_interpreter_alias(tmp_path, monkeypatch):
    renewal = load(DEPLOY / 'renew_fleet_memory_tokens.py')
    alias, provisioner, inventory = setup_renewal_tree(tmp_path)
    alias.parent.chmod(0o777)
    SYNTHETIC_UNSAFE_PATHS.add(alias.parent)
    monkeypatch.setattr(renewal, 'PROVISIONER_PYTHON', alias)
    monkeypatch.setattr(renewal, 'PROVISIONER', provisioner)
    monkeypatch.setattr(renewal, 'INVENTORY', inventory)
    monkeypatch.setattr(Path, 'lstat', synthetic_root_lstat)
    with pytest.raises(ValueError, match='untrusted_runtime_path'):
        renewal.trusted_path(alias.parent)  # closest rejection control
    # The symlink's target is safe, but the actual exec pathname is replaceable.
    with pytest.raises(ValueError, match='untrusted_runtime_path'):
        renewal.validate_runtime()


def installer_fixture(tmp_path, monkeypatch):
    installer = load(DEPLOY / 'install_fleet_token_renewal.py')
    stage = tmp_path / 'stage'
    stage.mkdir()
    for name in ('roles.json', 'provision_gateway_profile_access.py', 'renew_fleet_memory_tokens.py', 'install_fleet_token_renewal.py'):
        (stage / name).write_bytes((DEPLOY / name).read_bytes())
    alias, _, _ = setup_renewal_tree(tmp_path / 'runtime-fixture')
    target = tmp_path / 'installed'
    target.mkdir()
    for name in ('provision_gateway_profile_access.py', 'renew_fleet_memory_tokens.py'):
        (target / name).write_bytes((DEPLOY / name).read_bytes())
    service = tmp_path / 'renewal.service'
    monkeypatch.setattr(installer, 'DEPLOY', stage)
    monkeypatch.setattr(installer, '__file__', str(stage / 'install_fleet_token_renewal.py'))
    monkeypatch.setattr(installer, 'RENEWAL_ROOT', target)
    monkeypatch.setattr(installer, 'SERVICE', service)
    monkeypatch.setattr(installer, 'PROVISIONER_PYTHON', alias)
    service.write_text(installer.unit_text())
    monkeypatch.setattr(installer.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(installer.os, 'uname', lambda: SimpleNamespace(nodename='Ubuntu-Hermes'))
    monkeypatch.setattr(installer.sys, 'argv', ['installer', '--upgrade'])
    monkeypatch.setattr(Path, 'lstat', synthetic_root_lstat)
    def systemctl(*args):
        if args[0] == 'is-active':
            return 3, 'inactive'
        if args[0] == 'show':
            return 0, '/usr/bin/python3 -I -B /opt/enhanced-cognee-memory/fleet-renewal/renew_fleet_memory_tokens.py'
        return 0, ''
    monkeypatch.setattr(installer, 'systemctl', systemctl)
    return installer, alias, target


def test_installer_rejects_replaceable_interpreter_before_launch(tmp_path, monkeypatch):
    installer, alias, target = installer_fixture(tmp_path, monkeypatch)
    alias.parent.chmod(0o777)
    SYNTHETIC_UNSAFE_PATHS.add(alias.parent)
    launches = []
    def no_launch(command, **kwargs):
        launches.append(command)
        # Return failure so installer exits before acquiring any write lock.
        return subprocess.CompletedProcess(command, 1, b'', b'')
    monkeypatch.setattr(installer.subprocess, 'run', no_launch)
    with pytest.raises(ValueError):
        installer.main()
    assert launches == [], 'root preflight reached a replaceable exec path: ' + repr(launches)


def test_installer_rejects_unknown_existing_inventory(tmp_path, monkeypatch):
    installer, alias, target = installer_fixture(tmp_path, monkeypatch)
    old_inventory = b'{"schema":99,"profiles":["owner-custom-inventory"]}\n'
    (target / 'roles.json').write_bytes(old_inventory)
    monkeypatch.setattr(installer.subprocess, 'run', lambda command, **kw: subprocess.CompletedProcess(command, 0, b'', b''))
    with pytest.raises(ValueError, match='unknown_predecessor'):
        installer.main()
    assert (target / 'roles.json').read_bytes() == old_inventory


@pytest.mark.parametrize('body', [b'', b'null', b'[]', b'true', b'17', b'"not-an-object"'])
def test_mcp_rejects_http_200_invalid_response_shapes(body, monkeypatch):
    mcp = load(REPO / 'integrations/hermes/enhanced_cognee_mcp/server.py')
    class Connection:
        def __init__(self, *a, **kw):
            pass
        def request(self, *a, **kw):
            pass
        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda size: body)
        def close(self):
            pass
    monkeypatch.setattr(mcp, 'HTTPConnection', Connection)
    message = {'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_stats','arguments':{}}}
    output = io.StringIO()
    with patch('sys.stdin', io.StringIO(json.dumps(message) + '\n')), patch('sys.stdout', output):
        mcp.serve(mcp.handlers('invented-review-placeholder'))
    reply = json.loads(output.getvalue())
    assert reply['result'].get('isError') is True, reply


def test_mcp_object_reply_positive_control(monkeypatch):
    mcp = load(REPO / 'integrations/hermes/enhanced_cognee_mcp/server.py')
    monkeypatch.setattr(mcp, 'api', lambda *a, **kw: (200, {'ready':True, 'project_id':'invented'}))
    assert mcp.handlers('invented-review-placeholder')['get_stats'][1]({}) == {'ready':True, 'project_id':'invented'}


def test_renewal_unrepresentable_expiry_does_not_abort_remaining_profiles(tmp_path, monkeypatch):
    renewal = load(DEPLOY / 'renew_fleet_memory_tokens.py')
    payload = base64.urlsafe_b64encode(json.dumps({'exp':10**100}).encode()).rstrip(b'=').decode()
    token = 'a' * 16 + '.' + payload + '.' + 'a' * 16
    assert renewal.decode_exp(token) == 10**100
    monkeypatch.setattr(renewal.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(renewal.os, 'uname', lambda: SimpleNamespace(nodename='Ubuntu-Hermes'))
    monkeypatch.setattr(renewal, 'validate_runtime', lambda: None)
    monkeypatch.setattr(renewal, 'PROVISIONER', tmp_path / 'provisioner.py')
    renewal.PROVISIONER.write_text('# no executable content\n')
    monkeypatch.setattr(renewal, 'profiles', lambda: ['default', 'web-researcher'])
    monkeypatch.setattr(renewal, 'load_profile_token', lambda path: token)
    monkeypatch.setattr(renewal, 'STATE', tmp_path / 'state.json')
    attempted = []
    def fake_renew(profile):
        attempted.append(profile)
        return {'profile':profile,'complete':False,'expires_utc':None,'error':'invented-refusal'}
    monkeypatch.setattr(renewal, 'renew', fake_renew)
    # No exception should escape a single malformed profile and abort the fleet.
    assert renewal.main() == 1
    assert 'web-researcher' in attempted


def test_cancellation_during_reservation_never_dispatches_model(tmp_path, monkeypatch):
    from src import llm_summarize as llm
    real_budget = llm.TokenBudget(tmp_path / 'ledger.sqlite3')
    started, release = Event(), Event()
    class Budget:
        def reserve(self, *a):
            started.set()
            assert release.wait(5)
            return real_budget.reserve(*a)
        def reconcile(self, *a):
            return real_budget.reconcile(*a)
    dispatched = []
    monkeypatch.setattr(llm, 'chat', lambda *a, **kw: dispatched.append(True))
    route = {'daily_token_cap':50000}
    async def run():
        task = asyncio.create_task(llm.budgeted_chat(route, Budget(), 'tenant', 'project', [{'role':'user','content':'invented'}]))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
    asyncio.run(run())
    assert dispatched == []
    assert real_budget.used('tenant', 'project') > 0


def test_opaque_non_ascii_payload_retains_uncertain_charge(tmp_path, monkeypatch):
    from src import llm_summarize as llm
    budget = llm.TokenBudget(tmp_path / 'ledger.sqlite3')
    calls = []
    def fake_chat(*args, **kw):
        calls.append(True)
        return 'Invented', None
    monkeypatch.setattr(llm, 'chat', fake_chat)
    messages = [{'role':'user','content':'\u4e2d' * 500}]
    estimate = len(json.dumps(messages, ensure_ascii=False).encode()) + 1024 + 900
    asyncio.run(llm.budgeted_chat({'daily_token_cap':estimate}, budget, 'tenant', 'project', messages))
    assert budget.used('tenant', 'project') == estimate
    with pytest.raises(llm.LlmUnavailable):
        asyncio.run(llm.budgeted_chat({'daily_token_cap':estimate}, budget, 'tenant', 'project', messages))
    assert calls == [True]
    assert b'\xe4\xb8\xad' not in budget.path.read_bytes()
