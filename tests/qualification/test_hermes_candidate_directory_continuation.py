"""Real directory permissions and fail-closed continuation admission."""
import os
from pathlib import Path
import runpy
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / 'integrations/hermes/deployment'
V2 = runpy.run_path(str(DEPLOYMENT / 'prepare_launch_candidate_provider_v2.py'), run_name='candidate_v2_test')


def retained_fixture():
    archive = ROOT / '.archive/candidate-directory-tests'
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    return Path(tempfile.mkdtemp(dir=archive))


def test_traverse_without_granting_directory_listing():
    base = retained_fixture()
    parent = base / 'traverse'
    parent.mkdir(mode=0o711)
    final = parent / 'candidate'
    final.mkdir(mode=0o700)
    (final / 'config').write_bytes(b'invented')
    # This unprivileged fixture owns the parent: remove its owner-read bit
    # to reproduce a different UID traversing a root-owned 0711 ancestor.
    parent.chmod(0o111)
    original = runpy.run_path(str(DEPLOYMENT / 'provision_pilot_access.py'), run_name='original_test')
    with pytest.raises(PermissionError):
        original['open_directory'](final, {0, os.geteuid()})
    fd = V2['open_candidate_directory'](final, {0, os.geteuid()})
    try:
        child = os.open('config', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            assert os.read(child, 32) == b'invented'
        finally:
            os.close(child)
    finally:
        os.close(fd)
    assert parent.stat().st_mode & 0o777 == 0o111


@pytest.mark.parametrize('kind', ['writable', 'symlink', 'foreign_owner'])
def test_ancestor_boundaries_remain_enforced(kind):
    base = retained_fixture()
    final = base / 'candidate'
    final.mkdir(mode=0o700)
    owners = {0, os.geteuid()}
    if kind == 'writable':
        base.chmod(0o722)
    elif kind == 'symlink':
        link = base / 'redirect'
        link.symlink_to(final, target_is_directory=True)
        final = link
    else:
        owners = {0}
    with pytest.raises((OSError, ValueError)):
        V2['open_candidate_directory'](final, owners)


def test_continuation_refuses_modified_or_published_candidates():
    prior = dict(complete=False, candidate_modified=False, ordinary_credential_published=False,
        owner_failure_phase='preflight', operator_helper_sha256='a21eec3cef6bd37c71467f0c867aaf392700519de2e24aacf837c8fe07d2a175')
    diagnostic = dict(stage='retained_candidate_preflight_inspection', phase='directory_open',
        error_kind='PermissionError', errno=13, profiles_changed=False, credentials_issued=0, store_connections=False)
    V2['continuation_receipts'](prior, diagnostic)
    for flag in ('candidate_modified', 'ordinary_credential_published', 'complete'):
        with pytest.raises(ValueError):
            V2['continuation_receipts'](dict(prior, **{flag: True}), diagnostic)
    with pytest.raises(ValueError):
        V2['continuation_receipts'](prior, dict(diagnostic, phase='other'))


def test_continuation_public_payload_fits_owner_launcher():
    helper = runpy.run_path(str(DEPLOYMENT / 'qualify_launch_isolated_accounts.py'), run_name='frame_test')
    helper['owner_program']((DEPLOYMENT / 'prepare_launch_candidate_provider_v2.py').read_bytes())
