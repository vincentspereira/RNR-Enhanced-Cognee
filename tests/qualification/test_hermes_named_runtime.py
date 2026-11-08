"""Configured-route, evidence binding and no-replay boundaries of batch three."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/qualify_launch_named_runtime.py'), run_name='runtime_tests')


def configured():
    return ({'model': {'provider': 'zai', 'default': 'glm-5.3-flash', 'base_url': 'https://open.bigmodel.cn/api/paas/v4/'}},
            {'provider': 'zai', 'base_url': 'https://open.bigmodel.cn/api/paas/v4',
             'api_mode': 'chat_completions', 'api_key': 'invented-not-a-real-credential'})


def test_route_binding_returns_only_public_metadata():
    config, runtime = configured()
    value = MODULE['route_metadata'](config, runtime)
    assert value == dict(provider='zai', model='glm-5.3-flash', host='open.bigmodel.cn', api_mode='chat_completions')
    assert runtime['api_key'] not in json.dumps(value)


def test_dispatcher_accepts_only_the_exact_reviewed_runtime_source():
    control = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/launch_control.py'), run_name='control_runtime_test')
    raw = (ROOT / 'integrations/hermes/deployment/qualify_launch_named_runtime.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == control['RUNTIME_SHA']
    assert control['definitions'](ROOT / 'integrations/hermes/deployment/qualify_launch_named_runtime.py', control['RUNTIME_SHA'])['_verified_source_bytes'] == raw


@pytest.mark.parametrize('change', ['other_host', 'http', 'userinfo', 'query', 'fragment', 'port', 'path',
                                     'provider', 'mode', 'missing_key', 'callable_key', 'model'])
def test_wrong_or_ambiguous_route_fails_closed(change):
    config, runtime = configured()
    if change == 'other_host': runtime['base_url'] = 'https://invented.example/api/paas/v4'
    elif change == 'http': runtime['base_url'] = 'http://open.bigmodel.cn/api/paas/v4'
    elif change == 'userinfo': runtime['base_url'] = 'https://user:invented@open.bigmodel.cn/api/paas/v4'
    elif change == 'query': runtime['base_url'] += '?credential=invented'
    elif change == 'fragment': runtime['base_url'] += '#invented'
    elif change == 'port': runtime['base_url'] = 'https://open.bigmodel.cn:8443/api/paas/v4'
    elif change == 'path': runtime['base_url'] = 'https://open.bigmodel.cn/other'
    elif change == 'provider': runtime['provider'] = 'other'
    elif change == 'mode': runtime['api_mode'] = 'responses'
    elif change == 'missing_key': runtime['api_key'] = ''
    elif change == 'callable_key': runtime['api_key'] = lambda: 'invented'
    elif change == 'model': config['model']['default'] = 'other'
    with pytest.raises(ValueError): MODULE['route_metadata'](config, runtime)


def inventory():
    plans, manifest = [], []
    for i in range(45):
        ident = f'{i:016x}'
        plans.append(dict(profile_id=ident, existing_binding=None, enabled=False,
            source_profile='/home/vincentspereira/.hermes/profiles/profile'+str(i), proposed_user='ecbot_'+ident,
            proposed_home='/var/lib/enhanced-cognee-profiles/'+ident, proposed_binding={'project_id':'profile_'+ident}))
        if i < 39:
            manifest.append(dict(profile_id=ident, evidence=str(MODULE['RESUMED']/ident)))
    return plans, manifest


def test_selection_uses_completed_manifest_without_qualification_bindings():
    rows = MODULE['validate_rows'](*inventory())
    assert len(rows) == 39


@pytest.mark.parametrize('change', ['duplicate', 'existing', 'enabled', 'main', 'redirect', 'identity'])
def test_selection_refuses_replays_and_wrong_evidence_lineage(change):
    plans, manifest = inventory()
    if change == 'duplicate': manifest[-1] = deepcopy(manifest[0])
    elif change == 'existing': plans[0]['existing_binding'] = {'tenant':'qualification'}
    elif change == 'enabled': plans[0]['enabled'] = True
    elif change == 'main': plans[0]['source_profile'] = '/home/vincentspereira/.hermes'
    elif change == 'redirect': manifest[0]['evidence'] = '/tmp/'+manifest[0]['profile_id']
    elif change == 'identity': plans[0]['proposed_user'] = 'root'
    with pytest.raises(ValueError): MODULE['validate_rows'](plans, manifest)


def receipt():
    return dict(dict.fromkeys(MODULE['TRUE_FLAGS'], True), **dict.fromkeys(MODULE['FALSE_FLAGS'], False),
                invocation_id='a'*32, uid=1234, source_sha256='b'*64,
                route=dict(provider='zai', model='glm-5.3-flash', host='open.bigmodel.cn', api_mode='chat_completions'))


@pytest.mark.parametrize('change', [None, 'uid', 'invocation', 'source', 'chat', 'extra'])
def test_receipt_requires_actual_systemd_identity_and_invocation(change):
    value = receipt()
    if change == 'uid': value['uid'] = 0
    elif change == 'invocation': value['invocation_id'] = 'c'*32
    elif change == 'source': value['source_sha256'] = 'd'*64
    elif change == 'chat': value['chat_model_called'] = True
    elif change == 'extra': value['invented_secret'] = 'must-not-be-accepted'
    call = lambda: MODULE['verify_receipt'](value, {'InvocationID':'a'*32}, {'uid':1234}, 'b'*64)
    if change is None: assert call() == value
    else:
        with pytest.raises(ValueError): call()


def test_failed_unit_is_stopped_and_cannot_become_a_pass(tmp_path, monkeypatch):
    probe = MODULE['native_probe']
    observed, stopped = [], []
    monkeypatch.setattr(MODULE['subprocess'], 'run', lambda args, **kw: observed.append(args) or SimpleNamespace(stdout=b'', returncode=0))
    monkeypatch.setitem(probe.__globals__, 'finish_unit', lambda unit: stopped.append(unit) or True)
    monkeypatch.setitem(probe.__globals__, 'sync_directory', lambda path: None)
    monkeypatch.setattr(MODULE['pwd'], 'getpwnam', lambda name:SimpleNamespace(pw_name=name))
    native = {'properties':lambda unit:dict(ActiveState='failed', SubState='failed', InvocationID='a'*32),
              'verified_metadata':lambda *args: (_ for _ in ()).throw(ValueError('failed unit'))}
    row = dict(user='ecbot_'+'a'*16, uid=1234, home='/var/lib/enhanced-cognee-profiles/'+'a'*16,
               scope=dict(project_id='invented', tenant='hermes_private', sub='invented'))
    writes = {}
    with pytest.raises(ValueError): probe(row, tmp_path, native, lambda p,raw: writes.setdefault(p.name,raw))
    assert len(stopped) == 1 and 'unit.started.json' in writes and 'native.receipt.json' not in writes
    command = observed[0]
    assert '--property=User='+row['user'] in command
    assert '--property=CapabilityBoundingSet=' in command
    assert '--property=NoNewPrivileges=yes' in command
    assert '--property=ReadWritePaths='+row['home'] in command
    assert not any('TOKEN=' in arg or 'PASSWORD=' in arg for arg in command)


def test_existing_job_only_reattaches_without_selection_or_new_probe(monkeypatch):
    launch = MODULE['launch']
    monkeypatch.setattr(MODULE['os'], 'geteuid', lambda:0)
    monkeypatch.setattr(MODULE['os'].path, 'lexists', lambda path:True)
    monkeypatch.setitem(launch.__globals__, 'definitions', lambda *args: {'read_file':object(), 'private_write':object()})
    monkeypatch.setitem(launch.__globals__, 'selected', lambda *args: (_ for _ in ()).throw(AssertionError('must not select again')))
    monkeypatch.setitem(launch.__globals__, 'watch', lambda *args:42)
    assert launch() == 42


def test_ctrl_c_detaches_without_service_stop(tmp_path, monkeypatch, capsys):
    watch = MODULE['watch']
    evidence = tmp_path/'operator-evidence/named-runtime-invented'
    evidence.mkdir(parents=True)
    monkeypatch.setitem(watch.__globals__, 'BASE', tmp_path)
    def interrupt(*args): raise KeyboardInterrupt()
    monkeypatch.setitem(watch.__globals__, 'properties', interrupt)
    monkeypatch.setitem(watch.__globals__, 'finish_unit', lambda *a: (_ for _ in ()).throw(AssertionError('must not stop')))
    assert watch(lambda *a:json.dumps(dict(unit=MODULE['UNIT'], evidence=str(evidence))).encode()) == 0
    assert json.loads(capsys.readouterr().out)['job_continues'] is True
