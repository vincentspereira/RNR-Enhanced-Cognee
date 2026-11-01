"""Disabled admission and the generated issuer's real directory protections."""
import hashlib
import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / 'integrations/hermes/deployment'
STAGE = runpy.run_path(str(DEPLOYMENT / 'stage_launch_candidate_issuer.py'), run_name='stage_test')


def sources():
    return [(DEPLOYMENT / name).read_bytes() for name in
        ('provision_pilot_access.py','renew_fleet_credentials.py','prepare_launch_candidate_provider_v2.py')]


def test_exact_generated_core_pin_and_separate_policy_and_ledger():
    core, driver = STAGE['build_sources'](*sources())
    driver_namespace = STAGE['definitions'](driver)
    assert driver_namespace['SOURCES']['provision_pilot_access.py'] == hashlib.sha256(core).hexdigest()
    assert driver_namespace['POLICY'] == STAGE['PACKAGE'] / 'candidate-policy.json'
    assert driver_namespace['LEDGER'] == STAGE['PACKAGE'] / 'root-ledger'
    assert core.isascii() and driver.isascii()


@pytest.mark.parametrize('index',[0,1,2])
def test_unreviewed_source_cannot_build(index):
    values = sources()
    values[index] += b'\n# unreviewed\n'
    with pytest.raises(ValueError):
        STAGE['build_sources'](*values)


def test_candidate_policy_disabled_and_not_admissible_before_remaining_gates():
    policy = STAGE['definitions']((DEPLOYMENT / 'fleet_credential_policy.py').read_bytes())
    account = SimpleNamespace(pw_name='ecbot_'+'a'*16,pw_uid=900,pw_dir='/var/lib/enhanced-cognee-profiles/'+'a'*16)
    binding = dict(user=account.pw_name,uid=account.pw_uid,profile=account.pw_dir+'/.hermes',profile_id='a'*16,
        scope=dict(tenant='hermes_private',project_id='profile_a',sub='subject_a',agent_id='agent_a',roles=['api_client'],capture_policy='selected'))
    entry = STAGE['policy_entry'](binding,account,policy)
    result = policy['validate'](dict(schema=1,profiles=[entry]))
    assert result['profiles'][0]['enabled'] is False
    assert entry['backup_qualified'] and entry['os_boundary_qualified']
    assert not entry['reload_qualified'] and not entry['launch_binding_qualified']
    with pytest.raises(ValueError):
        policy['validate'](dict(schema=1,profiles=[dict(entry,enabled=True)]))
    with pytest.raises(ValueError):
        STAGE['policy_entry'](dict(binding,uid=901),account,policy)


def test_generated_core_traverses_without_read_permission_but_refuses_writeable_ancestor():
    core,_ = STAGE['build_sources'](*sources())
    namespace = STAGE['definitions'](core)
    archive = ROOT / '.archive/isolated-issuer-tests'
    archive.mkdir(parents=True,exist_ok=True,mode=0o700)
    base = Path(tempfile.mkdtemp(dir=archive))
    parent = base / 'traverse'
    parent.mkdir(mode=0o700)
    candidate = parent / 'candidate'
    candidate.mkdir(mode=0o700)
    parent.chmod(0o111)
    fd = namespace['open_directory'](candidate,{0,os.geteuid()})
    os.close(fd)
    base.chmod(0o722)
    with pytest.raises(namespace['ProvisionError']):
        namespace['open_directory'](candidate,{0,os.geteuid()})
