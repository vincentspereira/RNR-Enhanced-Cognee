"""Invented-fixture tests for the native MCP binding qualification cores."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = load('probe_native_mcp_binding')
helper = load('qualify_native_mcp_binding')

CONFIG = """
gateway:
  multiplex_profiles: true
memory:
  provider: enhanced_cognee
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem@2026.8.31", "/home/vincentspereira/agent-workspace"]
  fetch:
    command: uvx
    args: ["mcp-server-fetch"]
"""


def stdio_case(name, count=1):
    return {'complete': True, 'binding': 'stdio', 'resolved_via': 'managed',
            'initialize_passed': True, 'tools_list_passed': True, 'tools_count': count,
            'private_denials': 0, 'env_key_count': 0}


def catalogue_receipt(complete=True):
    return {'stage': 'catalogue', 'complete': complete, 'invocation_id': 'a' * 32,
            'config_path': '/var/lib/enhanced-cognee-profiles/5592956882ea9a13/.hermes/config.yaml',
            'config_sha256': 'b' * 64, 'fetch_server': 'fetch', 'definition_count': 2,
            'remote_definitions_deferred': [],
            'servers': {'fetch': dict(stdio_case('fetch'), private_denials=2, tools_count=1),
                        'rea': stdio_case('rea', 207)}}


def test_definitions_extracts_and_detects_fetch():
    servers, fetch, remotes = driver.definitions(CONFIG.encode())
    assert fetch == 'fetch'
    assert remotes == []
    assert set(servers) == {'filesystem', 'fetch'}
    assert servers['filesystem']['command'] == 'npx'
    assert servers['fetch']['kind'] == 'stdio'
    assert servers['fetch']['env'] == {}


def test_definitions_classifies_remote_definitions_without_exposing_them():
    config = CONFIG + """
  context7:
    url: https://mcp.context7.example/?key=invented-value
    headers:
      CONTEXT7_API_KEY: invented-value
"""
    servers, fetch, remotes = driver.definitions(config.encode())
    assert remotes == ['context7']
    assert servers['context7']['kind'] == 'remote'
    assert set(servers['context7']) == {'name', 'kind'}
    assert servers['context7'] != dict(servers['context7'], url='anything')


def test_definitions_refuses_duplicate_keys_and_bad_shapes():
    duplicate = CONFIG + "  fetch:\n    command: uvx\n"
    with pytest.raises(ValueError):
        driver.definitions(duplicate.encode())
    oversized = "mcp_servers:\n  x:\n    command: '" + 'a' * 300 + "'\n"
    with pytest.raises(ValueError):
        driver.definitions(oversized.encode())
    with pytest.raises(ValueError):
        driver.definitions(b'')
    with pytest.raises(ValueError):
        driver.safe_config(b'key: \x00nul')


def test_definitions_accepts_date_scalars_and_reports_count_bounds():
    config = CONFIG + "created: 2026-10-29\n"
    servers, fetch, remotes = driver.definitions(config.encode())
    assert fetch == 'fetch'
    many = CONFIG + ''.join("  extra%d:\n    command: node\n" % i for i in range(17))
    with pytest.raises(ValueError) as caught:
        driver.definitions(many.encode())
    assert 'mcp_servers_count' in str(caught.value)


def test_definitions_refuses_multiple_fetch_definitions():
    config = CONFIG + "  fetch2:\n    command: uvx\n    args: [\"mcp-server-fetch\"]\n"
    with pytest.raises(ValueError):
        driver.definitions(config.encode())


def test_validate_catalogue_accepts_and_rejects_receipts():
    receipt = catalogue_receipt()
    assert helper.validate_catalogue(receipt, 'a' * 32)['complete'] is True
    remote = catalogue_receipt()
    remote['servers']['context7'] = {'complete': True, 'binding': 'remote',
                                     'remote_binding_qualified': False,
                                     'deferred_reason': 'external_endpoint_requires_owner_gate'}
    remote['definition_count'] = 3
    remote['remote_definitions_deferred'] = ['context7']
    assert helper.validate_catalogue(remote, 'a' * 32)['complete'] is True
    for broken in ({**receipt, 'invocation_id': 'zz'},
                   {**receipt, 'definition_count': 3},
                   {**receipt, 'servers': {**receipt['servers'],
                                           'rea': {**receipt['servers']['rea'], 'tools_count': 0}}},
                   {**receipt, 'config_sha256': 'short'},
                   {**receipt, 'remote_definitions_deferred': ['ghost']}):
        with pytest.raises(ValueError):
            helper.validate_catalogue(broken, 'a' * 32)


def test_validate_catalogue_rejects_remote_entries_carrying_endpoint_data():
    receipt = catalogue_receipt()
    receipt['servers']['context7'] = {'complete': True, 'binding': 'remote',
                                      'remote_binding_qualified': False,
                                      'deferred_reason': 'external_endpoint_requires_owner_gate',
                                      'url': 'https://mcp.context7.example/'}
    receipt['definition_count'] = 3
    receipt['remote_definitions_deferred'] = ['context7']
    with pytest.raises(ValueError):
        helper.validate_catalogue(receipt, 'a' * 32)


def test_validate_fetch_accepts_and_rejects_receipts():
    good = {'stage': 'fetch-public', 'server': 'fetch', 'complete': True, 'invocation_id': 'c' * 32,
            'raw_passed': True, 'default_extraction_qualified': True, 'private_denials': 2}
    assert helper.validate_fetch(good, 'c' * 32)['complete'] is True
    for broken in ({**good, 'private_denials': 1},
                   {**good, 'raw_passed': False},
                   {**good, 'invocation_id': 'd' * 32}):
        with pytest.raises(ValueError):
            helper.validate_fetch(broken, 'c' * 32)


def test_journal_receipt_binds_invocation_pid_and_uid():
    invocation = 'e' * 32
    state = {'InvocationID': invocation, 'ExecMainPID': '4242', 'Result': 'success',
             'ExecMainStatus': '0'}
    receipt = catalogue_receipt()
    receipt['invocation_id'] = invocation
    rows = [{'_SYSTEMD_INVOCATION_ID': invocation, '_PID': '4242', '_UID': '992',
             '_TRANSPORT': 'stdout', 'MESSAGE': json.dumps(receipt)}]
    bound = helper.journal_receipt(rows, state, 992, helper.validate_catalogue, invocation)
    assert bound['complete'] is True
    failed_rows = [dict(rows[0], MESSAGE=json.dumps({**receipt, 'complete': False}))]
    with pytest.raises(ValueError):
        helper.journal_receipt(failed_rows, state, 992, helper.validate_catalogue, invocation)
    with pytest.raises(ValueError):
        helper.journal_receipt([dict(rows[0], _UID='1000')], state, 992,
                               helper.validate_catalogue, invocation)


def test_helper_sources_are_pinned_constants():
    assert helper.PROTOCOL_SHA == '415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07'
    assert helper.SUPPORT_SHA == 'fc389e21e8f13dd9feb54e35a760ccf482fc0bcf6d79c76ffa13bf3e47bd1d51'
    assert driver.PROTOCOL_SHA == helper.PROTOCOL_SHA
