"""Boundary checks for inactive candidate preparation; no services or keys."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'integrations/hermes/deployment/prepare_launch_candidate_provider.py'
spec = importlib.util.spec_from_file_location('candidate_preparation', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def proposal():
    return dict(existing_binding=None, enabled=False, proposed_binding=dict(
        sub='subject_example', agent_id='agent_example', tenant='hermes_private',
        project_id='profile_example', roles=['api_client'], capture_policy='selected'))


def test_private_proposal_accepted():
    assert module.scope_binding(proposal())['roles'] == ['api_client']


@pytest.mark.parametrize('change', ['existing', 'enabled', 'admin', 'wide', 'invalid'])
def test_scope_widening_refused(change):
    plan = proposal()
    if change == 'existing':
        plan['existing_binding'] = {'sub': 'retained'}
    elif change == 'enabled':
        plan['enabled'] = True
    elif change == 'admin':
        plan['proposed_binding']['roles'] = ['operator']
    elif change == 'wide':
        plan['proposed_binding']['capture_policy'] = 'all'
    else:
        plan['proposed_binding']['project_id'] = '../outside'
    with pytest.raises(ValueError):
        module.scope_binding(plan)


def test_yaml_aliases_do_not_modify_model_route_or_input():
    shared = {'provider': 'existing', 'model': 'keep_this'}
    original = {'memory': shared, 'gateway': shared, 'model': shared}
    result = module.provider_settings(original)
    assert result['model'] == shared
    assert shared == {'provider': 'existing', 'model': 'keep_this'}
    assert result['memory']['provider'] == 'enhanced_cognee'
    assert result['gateway']['multiplex_profiles'] is True
    assert 'multiplex_profiles' not in result['memory']


def test_rename_never_replaces_even_empty_directory(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.mkdir()
    target.mkdir()
    (source / 'retained').write_text('original')
    with pytest.raises(OSError):
        module.rename_new(source, target)
    assert (source / 'retained').read_text() == 'original'
    assert target.is_dir()
    destination = tmp_path / 'fresh'
    module.rename_new(source, destination)
    assert (destination / 'retained').read_text() == 'original'


def test_exclusive_private_write_preserves_original(tmp_path):
    path = tmp_path / 'receipt'
    module.write_new(path, b'original')
    with pytest.raises(FileExistsError):
        module.write_new(path, b'replacement')
    assert path.read_bytes() == b'original'
    assert path.stat().st_mode & 0o777 == 0o600


def test_public_owner_protocol_suppresses_library_output():
    helper_path = SOURCE.with_name('qualify_launch_isolated_accounts.py')
    helper = module.definitions(helper_path.read_bytes(),
        'd0425ae9f2598e79a732e41f23ebbc09bcfd77993b91c8cddb4e45fa192e2a94')
    code, line = helper['owner_program'](b'def child(packet):\n print("library chatter")\n return {"complete":packet["ok"]}\n')
    # Exercise the same framed protocol with an invented, nonprivileged child.
    code = module.owner_launcher(code)
    completed = subprocess.run([sys.executable, '-I', '-B', '-c', code],
        input=line + b'{"ok":true}\n', capture_output=True, timeout=10)
    assert completed.returncode == 0
    assert completed.stdout == b'{"complete": true}\n'
    assert completed.stderr == b''
    # The real public payload also fits both fixed framing bounds.
    helper['owner_program'](SOURCE.read_bytes())
