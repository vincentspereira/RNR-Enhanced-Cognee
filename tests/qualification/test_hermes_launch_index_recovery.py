"""Installed recovery may contact only the selected local store ports."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/qualify_launch_indexes.py"
spec = importlib.util.spec_from_file_location("launch_index_recovery", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.mark.parametrize("url,schemes,port", [
    ("https://example.invalid:28535", {"http", "https"}, 28535),
    ("http://127.0.0.1:6333", {"http", "https"}, 28535),
    ("redis://127.0.0.1:6379", {"redis", "rediss"}, 28537),
    ("file:///private", {"http", "https"}, 28535),
    ("http://127.0.0.1:28536", {"redis", "rediss"}, 28536),
])
def test_external_or_different_service_binding_refused(url, schemes, port):
    with pytest.raises(ValueError, match="local_store_binding_required"):
        helper.local(url, schemes, port)


@pytest.mark.parametrize("url,schemes,port", [
    ("http://127.0.0.1:28535", {"http", "https"}, 28535),
    ("http://localhost:28536", {"http", "https"}, 28536),
    ("redis://invented:synthetic@127.0.0.1:28537/0", {"redis", "rediss"}, 28537),
])
def test_exact_selected_local_binding_admitted(url, schemes, port):
    assert helper.local(url, schemes, port) == url


@pytest.mark.parametrize("path", ["/home/agent/index.json", "/tmp/index.json", "relative.json"])
def test_agent_controlled_settings_location_refused(path):
    with pytest.raises(ValueError, match="protected_index_settings_required"):
        helper.protected_settings(Path(path))
