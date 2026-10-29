"""Actual-candidate unit gates; no services, private profiles or credentials."""
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/qualify_launch_candidate_native_unit.py'), run_name='candidate_unit_test')
ACCOUNT = SimpleNamespace(pw_name='ecbot_' + 'a' * 16, pw_uid=900, pw_gid=900,
    pw_dir='/var/lib/enhanced-cognee-profiles/' + 'a' * 16)


def metadata():
    return dict(LoadState='loaded', ActiveState='active', SubState='exited', Result='success', ExecMainStatus='0',
        User=ACCOUNT.pw_name, Group=ACCOUNT.pw_name, NoNewPrivileges='yes', CapabilityBoundingSet='',
        AmbientCapabilities='', ProtectSystem='strict', ProtectHome='yes', PrivateTmp='yes', ProtectProc='invisible',
        RestrictSUIDSGID='yes', ReadWritePaths=ACCOUNT.pw_dir, SupplementaryGroups='', InvocationID='b' * 32)


@pytest.mark.parametrize('field,value', [('User','root'), ('Group','sudo'), ('ProtectHome','no'),
    ('ProtectSystem','no'), ('NoNewPrivileges','no'), ('CapabilityBoundingSet','cap_setuid'),
    ('AmbientCapabilities','cap_dac_override'), ('ReadWritePaths','/'), ('SupplementaryGroups','docker'),
    ('Result','exit-code'), ('InvocationID',''), ('SubState','running')])
def test_weakened_or_incomplete_unit_cannot_pass(field, value):
    with pytest.raises(ValueError):
        HELPER['verified_metadata'](dict(metadata(), **{field:value}), ACCOUNT)


def test_receipt_bound_to_native_source_uid_and_systemd_invocation():
    proof = metadata()
    HELPER['verified_metadata'](proof, ACCOUNT)
    receipt = dict(dict.fromkeys(HELPER['FLAGS'], True), uid=900, invocation_id='b' * 32, source_sha256='c' * 64)
    HELPER['verified_receipt'](receipt, proof, 900, 'c' * 64)
    for field, value in [('uid', True), ('invocation_id','d' * 32), ('source_sha256','e' * 64), ('candidate_token_bound',False)]:
        with pytest.raises(ValueError):
            HELPER['verified_receipt'](dict(receipt, **{field:value}), proof, 900, 'c' * 64)


@pytest.mark.parametrize('config', [None, {'memory':None},
    {'memory':{'provider':'other'}, 'gateway':{'multiplex_profiles':True}},
    {'memory':{'provider':'enhanced_cognee'}, 'gateway':{'multiplex_profiles':False}},
    {'memory':{'provider':'enhanced_cognee'}, 'gateway':{'multiplex_profiles':True}, 'secrets':{'external':{'enabled':True}}}])
def test_unreviewed_configuration_refused(config):
    with pytest.raises(ValueError):
        HELPER['candidate_config'](config)


def test_candidate_configuration_preserves_existing_route():
    config = {'memory':{'provider':'enhanced_cognee'}, 'gateway':{'multiplex_profiles':True}, 'model':{'default':'preserved'}}
    assert HELPER['candidate_config'](config) == config


def test_unit_cleanup_continues_after_failure(monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append(args[-1])
        return SimpleNamespace(returncode=1 if len(calls) == 1 else 0)
    monkeypatch.setattr(HELPER['subprocess'], 'run', run)
    assert HELPER['stop_units'](['first.service','second.service']) is False
    assert calls == ['first.service','second.service']
