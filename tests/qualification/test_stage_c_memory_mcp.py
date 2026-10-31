"""Stage C server and enablement tests (pure cores, invented fixtures)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / 'integrations/hermes/deployment'
SERVER = Path(__file__).resolve().parents[2] / 'integrations/hermes/enhanced_cognee_mcp'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = load(SERVER / 'server.py', 'ec_stage_c_server')


def test_registry_matches_stage_c_inventory():
    table = server.handlers("invented-token")
    expected = {"recall", "get_memories", "get_memory", "get_memory_history",
                "get_related", "list_agents", "get_shared_memories",
                "library_membership", "get_stats", "health", "remember",
                "update_memory", "forget_memory", "set_memory_sharing",
                "ingest_url", "ingest_text", "summarize_memories",
                "find_consolidation_candidates", "get_summarization_status",
                "translate_text", "detect_language"}
    assert set(table) == expected
    for schema, fn in table.values():
        assert schema["inputSchema"]["additionalProperties"] is False


def test_ingest_tools_build_correct_bodies(monkeypatch):
    captured = {}

    def fake_api(method, path, token, body=None):
        captured.update(method=method, path=path, body=body)
        return 200, {"ingested": 1, "chunks": 1}

    monkeypatch.setattr(server, "api", fake_api)
    table = server.handlers("scoped-token")
    result = table["ingest_text"][1]({"text": "invented document",
                                      "title": "Fixture"})
    assert result["ingested"] == 1
    assert captured["method"] == "POST" and captured["path"] == "/v1/memories/ingest"
    assert captured["body"]["text"] == "invented document"
    assert captured["body"]["title"] == "Fixture"
    assert captured["body"]["base_key"].startswith("mcp-")
    selection = server.apply_groups(dict(table), "memory_read,ingest")
    assert {"ingest_url", "ingest_text"} <= set(selection)
    read_only = server.apply_groups(dict(table), "memory_read")
    assert "ingest_url" not in read_only


def test_groups_keep_write_tools_out_of_read_selection():
    table = server.handlers("invented-token")
    read_only = server.apply_groups(dict(table), "memory_read")
    assert set(read_only) == set(server.GROUPS["memory_read"])
    assert "remember" not in read_only and "set_memory_sharing" not in read_only
    write = server.apply_groups(dict(table), "memory_write")
    assert "recall" not in write and "remember" in write
    with pytest.raises(SystemExit):
        server.apply_groups(dict(table), "bogus")
    with pytest.raises(SystemExit):
        server.apply_groups(dict(table), "")


def test_input_guards():
    with pytest.raises(ValueError):
        server.handlers("t")["recall"][1]({})
    with pytest.raises(ValueError):
        server.handlers("t")["recall"][1]({"query": ""})
    with pytest.raises(ValueError):
        server.handlers("t")["get_memory"][1]({"record_id": "../escape"})
    with pytest.raises(ValueError):
        server.handlers("t")["recall"][1]({"query": "ok", "limit": 999})


def test_api_call_shapes(monkeypatch):
    captured = {}

    def fake_api(method, path, token, body=None):
        captured.update(method=method, path=path, body=body, token=token)
        return 200, {"ready": True}

    monkeypatch.setattr(server, "api", fake_api)
    table = server.handlers("scoped-token")
    result = table["recall"][1]({"query": "invented question"})
    assert captured == {"method": "POST", "path": "/v1/memories/recall",
                        "body": {"query": "invented question", "limit": 5,
                                 "include_shared": True},
                        "token": "scoped-token"}
    assert result == {"ready": True}
    table["get_memories"][1]({"limit": 10, "offset": 0})
    assert captured["path"].startswith("/v1/memories?") and "limit=10" in captured["path"]
    table["get_memory"][1]({"record_id": "abc-123"})
    assert captured["path"] == "/v1/memories/abc-123" and captured["method"] == "GET"
    table["update_memory"][1]({"record_id": "abc-123", "expected_version": 2,
                               "content": "fixed"})
    assert captured["method"] == "PATCH" and captured["body"] == {
        "expected_version": 2, "content": "fixed"}
    table["forget_memory"][1]({"record_id": "abc-123"})
    assert captured["path"] == "/v1/memories/abc-123/retract"


def test_api_error_maps_to_honest_tool_error(monkeypatch):
    monkeypatch.setattr(server, "api",
                        lambda m, p, t, b=None: (403, {"detail": "x"}))
    table = server.handlers("t")
    payload = table["get_stats"][1]({})
    assert payload["status_code"] == 403 and "refused" in payload["error"]

    monkeypatch.setattr(server, "api",
                        lambda m, p, t, b=None: (422, {"detail":
                                                  "Refused: not a public address"}))
    payload = server.handlers("t")["ingest_url"][1]({"url": "http://127.0.0.1/"})
    assert payload["status_code"] == 422
    assert payload.get("detail") == "Refused: not a public address"


def test_enablement_helper_constants():
    helper = load(DEPLOY / 'enable_fleet_memory_mcp.py', 'stage_c_enable')
    assert helper.SERVER_NAME == "enhanced_cognee"
    assert helper.SOURCE.is_file()
    assert helper.DEFAULT_GROUPS == "memory_read"
