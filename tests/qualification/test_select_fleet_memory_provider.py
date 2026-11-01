"""Tests for the fleet provider selection line editor."""
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


sel = load('select_fleet_memory_provider')

FULL = """model:
  id: gpt
# memory settings
memory:
  memory_enabled: true
  provider: builtin
  memory_char_limit: 2200

session_reset:
  mode: none
"""


def test_select_replaces_existing_provider_in_place():
    updated = sel.select_provider(FULL)
    assert "  provider: enhanced_cognee\n" in updated
    assert "builtin" not in updated
    assert updated.count("provider:") == 1
    assert "# memory settings" in updated and "memory_char_limit: 2200" in updated
    import yaml
    assert yaml.safe_load(updated)["memory"]["provider"] == "enhanced_cognee"


def test_select_appends_when_memory_missing():
    config = "model:\n  id: gpt\ntools:\n  x: 1\n"
    updated = sel.select_provider(config)
    import yaml
    parsed = yaml.safe_load(updated)
    assert parsed["memory"]["provider"] == "enhanced_cognee"
    assert parsed["model"]["id"] == "gpt" and parsed["tools"]["x"] == 1


def test_select_returns_none_when_already_selected():
    config = FULL.replace("provider: builtin", "provider: enhanced_cognee")
    assert sel.select_provider(config) is None


def test_select_handles_no_trailing_newline():
    updated = sel.select_provider("model:\n  id: g")
    import yaml
    assert yaml.safe_load(updated)["memory"]["provider"] == "enhanced_cognee"
