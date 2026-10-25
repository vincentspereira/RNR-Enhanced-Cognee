"""Candidate mapping, authenticated generation and pre-transport key guards."""
import hashlib
import hmac
import importlib.util
import io
import json
from pathlib import Path
import tarfile

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/stage_launch_named_candidate.py'
spec = importlib.util.spec_from_file_location('named_stage', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def fixture():
    plans, accounts = [], []
    for index, char in enumerate(('a', 'b')):
        ident = char * 16
        row = dict(profile_id=ident, user='ecbot_' + ident, home='/var/lib/enhanced-cognee-profiles/' + ident)
        accounts.append(row)
        plans.append(dict(row, proposed_user=row['user'], proposed_home=row['home'], enabled=False,
            source_user='vincentspereira', source_profile='/home/vincentspereira/.hermes' if index == 0
            else '/home/vincentspereira/.hermes/profiles/invented'))
    return plans, accounts


def test_only_backed_up_named_profile_selected_and_main_deferred():
    plans, accounts = fixture()
    assert helper.select_accounts(plans, accounts) == [accounts[1]]


@pytest.mark.parametrize('field,value', [('proposed_user', 'root'), ('proposed_home', '/root'), ('enabled', True),
    ('source_profile', '/home/vincentspereira/.hermes/profiles/../outside')])
def test_widened_mapping_refused(field, value):
    plans, accounts = fixture()
    plans[1][field] = value
    with pytest.raises(ValueError):
        helper.select_accounts(plans, accounts)


def test_manifest_ciphertext_and_identity_are_authenticated():
    key = b'invented-signing-key'
    ciphertext = b'invented-ciphertext'
    manifest = dict(format='hermes-named-profile-sqlite-tar+age', complete=True,
        source_profile_id='a' * 16, capture_component_sha256=helper.CAPTURE_SHA,
        ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest())
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    manifest['signature'] = hmac.new(key, raw, hashlib.sha256).hexdigest()
    helper.verify_manifest(manifest, key, 'a' * 16, ciphertext)
    with pytest.raises(ValueError):
        helper.verify_manifest(manifest, key, 'b' * 16, ciphertext)
    with pytest.raises(ValueError):
        helper.verify_manifest(manifest, key, 'a' * 16, ciphertext + b'altered')


@pytest.mark.parametrize('line', ['ENHANCED_JWT_SECRET=invented', "export 'ENCRYPTION_MASTER_KEY'=invented"])
def test_known_backend_keys_refused_before_plaintext_transport(line):
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo('.env')
        raw = line.encode()
        member.size = len(raw)
        archive.addfile(member, io.BytesIO(raw))
    with pytest.raises(ValueError):
        helper.privileged_environment_absent(payload.getvalue())


def test_component_source_pin_and_unprivileged_operator_refusal(monkeypatch):
    assert hashlib.sha256(SOURCE.with_name('capture_named_profile.py').read_bytes()).hexdigest() == helper.CORE_SHA
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()
