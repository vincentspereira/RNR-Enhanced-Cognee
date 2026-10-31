"""Fixed isolation selection and pipe contract, never real account creation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment/qualify_launch_isolated_accounts.py'
spec = importlib.util.spec_from_file_location('isolated_accounts', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def plan():
    rows = []
    for char in ('a', 'b'):
        ident = char * 16
        rows.append(dict(profile_id=ident, source_user='vincentspereira', proposed_user='ecbot_' + ident,
            proposed_home=str(helper.PARENT / ident), proposed_uid=None, enabled=False, gates={'backup': False}))
    return dict(schema=1, qualification_scope='inert_isolation_drafts_only', fleet_launch_approved=False, profiles=rows)


def test_only_two_fixed_planned_identities_selected():
    rows = helper.selection(plan())
    assert len(rows) == 2 and rows[0]['proposed_user'] != rows[1]['proposed_user']


@pytest.mark.parametrize('field,value', [('proposed_user', 'root'), ('proposed_home', '/root'),
    ('proposed_uid', 0), ('enabled', True), ('gates', {'backup': True}), ('gates', {})])
def test_widened_or_admitted_account_plan_refused(field, value):
    document = plan()
    document['profiles'][0][field] = value
    with pytest.raises(ValueError):
        helper.selection(document)


@pytest.mark.parametrize('field', sorted(helper.FLAGS))
def test_every_os_boundary_must_pass(field):
    value = dict.fromkeys(helper.FLAGS, True)
    value[field] = False
    with pytest.raises(ValueError):
        helper.receipt(value)


def test_no_extra_receipt_fields_or_truthy_strings_admitted():
    for value in (dict(dict.fromkeys(helper.FLAGS, True), raw_environment='invented'),
                  dict.fromkeys(helper.FLAGS, 'true')):
        with pytest.raises(ValueError):
            helper.receipt(value)


def test_public_source_and_two_phase_pipe_protocol_in_real_python():
    source = b'''import sys,json
def child():
    value=json.loads(sys.stdin.buffer.readline(8193))
    print(json.dumps({'ordinary_packet':value=={'invented':True}}),flush=True)
    assert sys.stdin.buffer.read(1)==b'!'
'''
    code, line = helper.owner_program(source)
    result = subprocess.run([sys.executable, '-I', '-B', '-c', code],
        input=line + b'{"invented":true}\n!', capture_output=True, timeout=5, check=True)
    assert json.loads(result.stdout) == {'ordinary_packet': True}


def test_root_preflight_refuses_unprivileged_parent_before_any_reads(monkeypatch):
    monkeypatch.setattr(helper.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError):
        helper.main()


def test_denied_file_must_be_permission_denied_not_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        helper.denied(tmp_path / 'missing')
    marker = tmp_path / 'invented'
    marker.write_bytes(b'invented')
    assert helper.denied(marker) is False
