"""Unit tests for dashboard/dashboard_api.py (no live databases required).

Covers the pure helpers and the degraded-mode behavior (all backends
down -> clear errors / empty payloads instead of crashes). Endpoint
behavior against live databases is covered by the manual smoke suite and
the docker-compose healthchecks.
"""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
MODULE_PATH = REPO_ROOT / "dashboard" / "dashboard_api.py"

spec = importlib.util.spec_from_file_location("dashboard_api", MODULE_PATH)
dashboard_api = importlib.util.module_from_spec(spec)
sys.modules["dashboard_api"] = dashboard_api
spec.loader.exec_module(dashboard_api)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_parse_metadata_handles_all_input_shapes():
    assert dashboard_api._parse_metadata({"a": 1}) == {"a": 1}
    assert dashboard_api._parse_metadata('{"a": 1}') == {"a": 1}
    assert dashboard_api._parse_metadata("not json") == {}
    assert dashboard_api._parse_metadata("[1, 2]") == {}  # non-dict JSON
    assert dashboard_api._parse_metadata(None) == {}
    assert dashboard_api._parse_metadata("") == {}


def test_estimate_tokens():
    assert dashboard_api._estimate_tokens("") == 0
    assert dashboard_api._estimate_tokens("abcd" * 25) == 25
    assert dashboard_api._estimate_tokens("ab") == 1  # floor of 1 for non-empty


def test_iso_formats():
    dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert dashboard_api._iso(dt) == "2026-01-02T03:04:05+00:00"
    naive = datetime(2026, 1, 2, 3, 4, 5)
    assert dashboard_api._iso(naive).endswith("+00:00")
    assert dashboard_api._iso(None) == ""


def test_arcade_node_dict_maps_arcadedb_documents():
    node = dashboard_api._arcade_node_dict(
        {"@rid": "#1:0", "@type": "Entity", "@cat": "v", "name": "Alpha",
         "importance": "0.5"}
    )
    assert node["id"] == "#1:0"
    assert node["label"] == "Alpha"
    assert node["type"] == "entity"
    assert node["importance"] == 0.5
    assert "@rid" not in node["properties"]


def test_arcade_node_dict_falls_back_to_rid_label():
    node = dashboard_api._arcade_node_dict({"@rid": "#2:3", "@type": "Thing"})
    assert node["label"] == "#2:3"


def test_arcade_edge_dict_maps_direction():
    edge = dashboard_api._arcade_edge_dict(
        {"@rid": "#9:0", "@type": "RELATES_TO", "@out": "#1:0", "@in": "#2:0",
         "confidence": 0.7}
    )
    assert edge["source"] == "#1:0"
    assert edge["target"] == "#2:0"
    assert edge["type"] == "relates_to"
    assert edge["strength"] == 0.7


def test_graph_payload_counts_types():
    nodes = {
        "a": {"id": "a", "type": "memory"},
        "b": {"id": "b", "type": "memory"},
        "c": {"id": "c", "type": "concept"},
    }
    edges = [{"id": "e1", "type": "semantic"}]
    payload = dashboard_api._graph_payload(nodes, edges)
    assert payload["metadata"]["total_nodes"] == 3
    assert payload["metadata"]["node_types"] == {"memory": 2, "concept": 1}
    assert payload["metadata"]["edge_types"] == {"semantic": 1}


# ---------------------------------------------------------------------------
# Degraded mode (no backends connected)
# ---------------------------------------------------------------------------


@pytest.fixture
def offline_client(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(dashboard_api.conns, "pg_pool", None)
    monkeypatch.setattr(dashboard_api.conns, "neo4j_driver", None)
    monkeypatch.setattr(dashboard_api.conns, "redis_client", None)
    monkeypatch.setattr(dashboard_api.conns, "graph_http", None)
    # TestClient without lifespan so init() doesn't try to reconnect
    return TestClient(dashboard_api.app)


def test_health_reports_degraded_when_offline(offline_client, monkeypatch):
    async def no_qdrant():
        return False

    monkeypatch.setattr(dashboard_api, "_check_qdrant", no_qdrant)
    resp = offline_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["databases"]["postgresql"] is False


def test_memories_returns_503_when_postgres_down(offline_client):
    resp = offline_client.get("/api/memories")
    assert resp.status_code == 503
    assert "PostgreSQL" in resp.json()["detail"]


def test_graph_returns_empty_payload_when_offline(offline_client):
    resp = offline_client.get("/api/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes"] == []
    assert body["metadata"]["total_nodes"] == 0


def test_security_user_local_mode(offline_client, monkeypatch):
    monkeypatch.delenv("DASHBOARD_JWT_SECRET", raising=False)
    resp = offline_client.get("/api/security/user")
    assert resp.status_code == 200
    assert resp.json()["auth_mode"] == "local"


def test_invalid_memory_id_is_400_not_500(offline_client, monkeypatch):
    # Reaches the id validation only when a pool exists; with pool=None the
    # guard fires first, so simulate a pool object.
    monkeypatch.setattr(dashboard_api.conns, "pg_pool", object())
    resp = offline_client.get("/api/memories/not-a-uuid")
    assert resp.status_code == 400
