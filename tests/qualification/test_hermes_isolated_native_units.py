"""Hardened unit acceptance and constructor probe contracts; no host starts."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/qualify_launch_isolated_native_units.py'
spec = importlib.util.spec_from_file_location('isolated_native', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
ACCOUNT = SimpleNamespace(pw_name='ecbot_' + 'a' * 16, pw_uid=900, pw_gid=900,
                          pw_dir='/var/lib/enhanced-cognee-profiles/' + 'a' * 16)


def metadata():
    return dict(LoadState='loaded', ActiveState='active', SubState='exited', Result='success', ExecMainStatus='0',
        User=ACCOUNT.pw_name, Group=ACCOUNT.pw_name, NoNewPrivileges='yes', CapabilityBoundingSet='',
        AmbientCapabilities='', ProtectSystem='strict', ProtectHome='yes', PrivateTmp='yes',
        ProtectProc='invisible', RestrictSUIDSGID='yes',
        ReadWritePaths=ACCOUNT.pw_dir, SupplementaryGroups='', InvocationID='b' * 32)


@pytest.mark.parametrize('field,value', [('LoadState', 'not-found'), ('ActiveState', 'failed'),
    ('SubState', 'running'), ('Result', 'exit-code'), ('ExecMainStatus', '1'), ('User', 'root'),
    ('Group', 'sudo'), ('NoNewPrivileges', 'no'), ('CapabilityBoundingSet', 'cap_setuid'),
    ('AmbientCapabilities', 'cap_dac_override'), ('ProtectSystem', 'no'), ('ProtectHome', 'no'),
    ('PrivateTmp', 'no'), ('ProtectProc', 'default'), ('RestrictSUIDSGID', 'no'),
    ('ReadWritePaths', '/'), ('SupplementaryGroups', 'docker'), ('InvocationID', '')])
def test_lost_or_weakened_unit_metadata_cannot_pass(field, value):
    value_set = metadata()
    value_set[field] = value
    with pytest.raises(ValueError):
        helper.verified_metadata(value_set, ACCOUNT)


def test_good_metadata_and_exact_bound_receipt_pass():
    proof = metadata()
    helper.verified_metadata(proof, ACCOUNT)
    value = dict(dict.fromkeys(helper.FLAGS, True), invocation_id='b' * 32, uid=900, source_sha256='c' * 64)
    assert helper.verified_receipt(value, proof, 900, 'c' * 64) == value
    for key, replacement in [('uid', True), ('invocation_id', 'd' * 32), ('complete', 'true'), ('source_sha256', 'd' * 64)]:
        with pytest.raises(ValueError):
            helper.verified_receipt(dict(value, **{key: replacement}), proof, 900, 'c' * 64)


@pytest.mark.parametrize('groups', [[], [900]])
def test_only_primary_group_or_no_groups_allowed(groups):
    helper.restricted_status(ACCOUNT, 900, groups, dict(NoNewPrivs='1', CapEff='0' * 16, CapAmb='0' * 16))


def test_extra_group_and_ambient_privilege_refused():
    fields = dict(NoNewPrivs='1', CapEff='0' * 16, CapAmb='0' * 16)
    with pytest.raises(ValueError):
        helper.restricted_status(ACCOUNT, 900, [900, 27], fields)
    with pytest.raises(ValueError):
        helper.restricted_status(ACCOUNT, 900, [], dict(fields, CapAmb='0000000000000001'))


def test_network_guard_denies_connect_connect_ex_and_dns(monkeypatch):
    monkeypatch.setattr(helper.socket.socket, 'connect', lambda *a: None)
    monkeypatch.setattr(helper.socket.socket, 'connect_ex', lambda *a: None)
    monkeypatch.setattr(helper.socket, 'getaddrinfo', lambda *a: None)
    count = helper.block_network()
    for operation in (lambda: helper.socket.socket.connect(None, ('127.0.0.1', 28080)),
                      lambda: helper.socket.socket.connect_ex(None, ('invented.invalid', 443)),
                      lambda: helper.socket.getaddrinfo('invented.invalid', 443)):
        with pytest.raises(RuntimeError):
            operation()
    assert count == {'blocked': 3}


def test_every_created_unit_stopped_even_after_a_stop_failure(monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append(args[-1])
        return SimpleNamespace(returncode=1 if len(calls) == 1 else 0)
    monkeypatch.setattr(helper.subprocess, 'run', run)
    assert helper.stop_units(['one.service', 'two.service']) is False
    assert calls == ['one.service', 'two.service']


def test_unprivileged_operator_refused_before_access(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()
