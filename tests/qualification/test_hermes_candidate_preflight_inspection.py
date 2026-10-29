"""Read-only diagnostic framing and bounded failure receipts."""
from pathlib import Path
import runpy
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / 'integrations/hermes/deployment'


def test_denied_directory_reports_phase_without_private_error_text(tmp_path, monkeypatch):
    inspection = runpy.run_path(str(DEPLOYMENT / 'inspect_launch_candidate_preflight.py'), run_name='test_inspection')
    core = runpy.run_path(str(DEPLOYMENT / 'prepare_launch_candidate_provider.py'), run_name='test_preparation')
    exec(inspection['OWNER_SOURCE'], core)
    uid = core['os'].geteuid()
    home = tmp_path / 'home'
    home.mkdir(mode=0o700)
    placeholder = home / '.hermes'
    placeholder.mkdir(mode=0o700)
    (placeholder / '.isolation-marker').write_bytes(b'invented-isolation-marker-v1')
    candidate = home / 'ec-named-profile-restore-invented'
    candidate.mkdir(mode=0o700)
    account = SimpleNamespace(pw_uid=uid, pw_dir=str(home))
    monkeypatch.setattr(core['pwd'], 'getpwuid', lambda _: account)
    monkeypatch.setattr(core['os'], 'getgroups', lambda: [])

    def denied(*args):
        raise PermissionError(13, 'invented private contents must not appear')

    core['definitions'] = lambda *args: {'open_directory': denied}
    result = core['child'](dict(uid=uid, home=str(home), candidate=str(candidate), issuer_source='public'))
    assert result['phase'] == 'directory_open'
    assert result['error_kind'] == 'PermissionError'
    assert result['errno'] == 13
    assert result['profiles_changed'] is False
    assert result['credentials_issued'] == 0
    assert 'private contents' not in str(result)
    assert sorted(path.name for path in home.iterdir()) == ['.hermes', candidate.name]


def test_public_combined_source_fits_restricted_protocol():
    inspection = runpy.run_path(str(DEPLOYMENT / 'inspect_launch_candidate_preflight.py'), run_name='test_inspection')
    helper = runpy.run_path(str(DEPLOYMENT / 'qualify_launch_isolated_accounts.py'), run_name='test_helper')
    raw = (DEPLOYMENT / 'prepare_launch_candidate_provider.py').read_bytes() + inspection['OWNER_SOURCE'].encode()
    code, line = helper['owner_program'](raw)
    assert len(line) <= 65536
    compile(raw, '<combined-owner-source>', 'exec')
