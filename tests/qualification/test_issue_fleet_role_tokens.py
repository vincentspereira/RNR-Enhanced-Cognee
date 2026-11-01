"""Tests for the fleet role token batch issuer (read-only parts)."""
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


batch = load('issue_fleet_role_tokens')


def test_role_names_exclude_default_and_canaries():
    names = batch.role_names()
    assert 40 <= len(names) <= 42
    assert 'enhanced-cognee-test' not in names
    assert 'enhanced-cognee-test-two' not in names
    assert 'default' not in names
    assert all((batch.PROFILES / name / '.env').is_file() for name in names)


def test_provisioner_and_support_files_exist():
    assert batch.PROVISIONER.is_file()
    assert batch.HOME.is_dir()
