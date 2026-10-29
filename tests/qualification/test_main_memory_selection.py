"""Invented-fixture tests for the main memory selection inspection cores."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load('probe_main_memory_selection')
helper = load('inspect_main_memory_selection')


def test_memory_selection_detects_enhanced_cognee():
    selection = probe.memory_selection({'memory': {'provider': 'enhanced_cognee', 'backend': 'x'}})
    assert selection == {'provider': 'enhanced_cognee', 'selected': True,
                         'keys': ['backend', 'provider']}


def test_memory_selection_reports_absent_and_default_sections():
    assert probe.memory_selection({})['selected'] is False
    assert probe.memory_selection({'memory': {'provider': None}})['selected'] is False
    assert probe.memory_selection({'memory': {'provider': None}})['provider'] is None
    native = probe.memory_selection({'memory': {'provider': 'native'}})
    assert native['provider'] == 'native' and native['selected'] is False


def test_memory_selection_refuses_bad_shapes():
    with pytest.raises(ValueError):
        probe.memory_selection({'memory': 'enhanced_cognee'})
    with pytest.raises(ValueError):
        probe.memory_selection({'memory': {'provider': ''}})
    with pytest.raises(ValueError):
        probe.memory_selection({'memory': {'provider': 42}})


def test_validator_accepts_and_rejects_receipts():
    good = {'stage': 'inspect', 'complete': True, 'invocation_id': 'a' * 32,
            'config_path': '/var/lib/enhanced-cognee-profiles/5592956882ea9a13/.hermes/config.yaml',
            'config_sha256': 'b' * 64, 'config_bytes': 2419,
            'memory': {'provider': 'enhanced_cognee', 'selected': True, 'keys': ['provider']},
            'mcp_definition_count': 4, 'mcp_definition_names': ['context7', 'deepwiki',
                                                                'fetch', 'filesystem']}
    assert helper.validate(good, 'a' * 32)['complete'] is True
    for broken in ({**good, 'invocation_id': 'zz'},
                   {**good, 'memory': {'provider': 'native', 'selected': True, 'keys': []}},
                   {**good, 'memory': {'provider': 'enhanced_cognee', 'keys': []}},
                   {**good, 'complete': False},
                   {**good, 'mcp_definition_names': 'four'}):
        with pytest.raises(ValueError):
            helper.validate(broken, 'a' * 32)


def test_support_chain_constants_are_pinned():
    assert helper.SUPPORT_SHA == 'fc389e21e8f13dd9feb54e35a760ccf482fc0bcf6d79c76ffa13bf3e47bd1d51'
    assert helper.BINDING_DRIVER_SHA == 'a54f321c30b64924a3b72d0b779f90997ec89674f65e192d6643cd02c3e062d5'
