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


def test_definitions_extracts_and_detects_fetch():
    servers, fetch = driver.definitions(CONFIG.encode())
    assert fetch == 'fetch'
    assert set(servers) == {'filesystem', 'fetch'}
    assert servers['filesystem']['command'] == 'npx'
    assert servers['fetch']['env'] == {}


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


def test_definitions_refuses_multiple_fetch_definitions():
    config = CONFIG + "  fetch2:\n    command: uvx\n    args: [\"mcp-server-fetch\"]\n"
    with pytest.raises(ValueError):
        driver.definitions(config.encode())


def test_validate_catalogue_accepts_and_rejects_receipts():
    invocation = 'a' * 32
    receipt = {'stage': 'catalogue', 'complete': True, 'invocation_id': invocation,
               'config_sha256': 'b' * 64, 'fetch_server': 'fetch', 'definition_count': 2,
               'servers': {
                   'fetch': {'complete': True, 'resolved_via': 'managed', 'initialize_passed': True,
                             'tools_list_passed': True, 'tools_count': 1, 'private_denials': 2,
                             'env_key_count': 0},
                   'rea': {'complete': True, 'resolved_via': 'passthrough', 'initialize_passed': True,
                           'tools_list_passed': True, 'tools_count': 207, 'private_denials': 0,
                           'env_key_count': 2}}}
    assert helper.validate_catalogue(receipt, invocation)['complete'] is True
    for broken in ({**receipt, 'invocation_id': 'zz'},
                   {**receipt, 'definition_count': 3},
                   {**receipt, 'servers': {**receipt['servers'],
                                           'rea': {**receipt['servers']['rea'], 'tools_count': 0}}},
                   {**receipt, 'config_sha256': 'short'}):
        with pytest.raises(ValueError):
            helper.validate_catalogue(broken, invocation)


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
    receipt = {'stage': 'catalogue', 'complete': True, 'invocation_id': invocation,
               'config_sha256': 'b' * 64, 'fetch_server': None, 'definition_count': 1,
               'servers': {'rea': {'complete': True, 'resolved_via': 'passthrough',
                                   'initialize_passed': True, 'tools_list_passed': True,
                                   'tools_count': 207, 'private_denials': 0, 'env_key_count': 0}}}
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
