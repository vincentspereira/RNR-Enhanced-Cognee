"""Pinned provider descriptor recovery and arbitrary-link refusal."""
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import sqlite3
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
CORE = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/capture_candidate_profile.py'), run_name='candidate_capture_test')


def fixture_profile(path):
    (path / 'plugins').mkdir()
    (path / CORE['PROVIDER_LINK']).symlink_to(CORE['PROVIDER_TARGET'])
    (path / '.env').write_bytes(b'INVENTED_CREDENTIAL=preserved\n')
    return path


def test_exact_provider_descriptor_and_committed_sqlite_recovery(tmp_path):
    profile = fixture_profile(tmp_path)
    writer = sqlite3.connect(profile / 'state.db')
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE history(version integer)')
    writer.execute('INSERT INTO history VALUES (1)')
    writer.commit()
    writer.execute('INSERT INTO history VALUES (2)')
    payload, captured = CORE['capture'](profile)
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        member = archive.getmember(CORE['PROVIDER_LINK'])
        assert member.isfile() and not member.issym()
        assert archive.extractfile(member).read() == CORE['PROVIDER_DESCRIPTOR']
    destination, restored = CORE['restore'](payload)
    destination = Path(destination)
    assert os.readlink(destination / CORE['PROVIDER_LINK']) == CORE['PROVIDER_TARGET']
    assert (destination / '.env').read_bytes() == (profile / '.env').read_bytes()
    with sqlite3.connect(destination / 'state.db') as database:
        assert database.execute('SELECT version FROM history').fetchall() == [(1,)]
    assert captured['sqlite_databases'] == restored['sqlite_databases_verified'] == 1
    assert restored['pinned_provider_binding_reconstructed'] is True
    assert restored['restored_profile_executed'] is False
    writer.rollback()
    writer.close()


@pytest.mark.parametrize('kind', ['other_link', 'wrong_target', 'missing_binding', 'hardlink'])
def test_unsupported_bindings_refused(tmp_path, kind):
    if kind == 'wrong_target':
        (tmp_path / 'plugins').mkdir()
        (tmp_path / CORE['PROVIDER_LINK']).symlink_to('/unreviewed/provider')
    elif kind == 'missing_binding':
        (tmp_path / '.env').write_text('invented')
    else:
        fixture_profile(tmp_path)
        if kind == 'other_link':
            (tmp_path / 'other').symlink_to('/unreviewed')
        else:
            os.link(tmp_path / '.env', tmp_path / 'alias')
    with pytest.raises(CORE['CaptureError']):
        CORE['capture'](tmp_path)


def test_even_self_consistent_forged_descriptor_is_refused(tmp_path):
    payload, _ = CORE['capture'](fixture_profile(tmp_path))
    members = []
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        for item in archive:
            members.append((item, archive.extractfile(item).read() if item.isfile() else None))
    forged = b'{"kind":"pinned_provider_binding","target":"/unreviewed"}'
    for item, raw in members:
        if item.name == 'profile-manifest.json':
            manifest = json.loads(raw)
            for entry in manifest['entries']:
                if entry['path'] == CORE['PROVIDER_LINK']:
                    entry.update(size=len(forged), sha256=hashlib.sha256(forged).hexdigest())
            manifest_raw = json.dumps(manifest).encode()
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w') as archive:
        for item, raw in members:
            if item.name == CORE['PROVIDER_LINK']:
                raw = forged
            elif item.name == 'profile-manifest.json':
                raw = manifest_raw
            if raw is not None:
                item.size = len(raw)
            archive.addfile(item, io.BytesIO(raw) if raw is not None else None)
    with pytest.raises(CORE['CaptureError']):
        CORE['restore'](output.getvalue())


def test_operator_component_pin_and_public_payload_bounds():
    backup_path = ROOT / 'integrations/hermes/deployment/backup_launch_candidate_profile.py'
    backup = runpy.run_path(str(backup_path), run_name='candidate_backup_test')
    source = ROOT / 'integrations/hermes/deployment/capture_candidate_profile.py'
    backup['definitions'](source.read_bytes(), backup['CORE_SHA'])
    helper = runpy.run_path(str(ROOT / 'integrations/hermes/deployment/qualify_launch_isolated_accounts.py'), run_name='owner_frame_test')
    helper['owner_program'](backup_path.read_bytes())
