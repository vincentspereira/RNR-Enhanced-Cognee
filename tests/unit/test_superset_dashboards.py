"""Validate the Superset dashboard scaffolding ships well-formed JSON.

Catches regressions where someone edits a dashboard JSON and breaks the
import contract. We don't run a Superset import here -- that requires a
live Superset -- but we lock down the structural invariants the
importer cares about.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[2]
_DASHBOARD_DIR = _ROOT / "monitoring" / "superset-dashboards"

# Every JSON dashboard file we ship + the structural invariants we
# expect.
_DASHBOARDS = [
    "memory_growth.json",
    "agent_activity.json",
    "llm_cost_trends.json",
    "dedup_effectiveness.json",
    "perf_regression.json",
]

# Datasets every dashboard above references; the YAML must define them
# so the importer doesn't fail with "unknown dataset".
_REQUIRED_DATASETS = {
    "memory_documents",
    "memory_documents_daily",
    "llm_usage",
    "llm_usage_daily_by_agent",
    "memory_dedup_effectiveness",
    "signoz_traces_by_agent",
    "signoz_endpoint_latency",
}


class TestDashboardJSONStructure:
    @pytest.mark.parametrize("filename", _DASHBOARDS)
    def test_dashboard_parses_as_json(self, filename):
        path = _DASHBOARD_DIR / filename
        assert path.exists(), f"Dashboard file missing: {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    @pytest.mark.parametrize("filename", _DASHBOARDS)
    def test_dashboard_has_required_top_level_keys(self, filename):
        data = json.loads((_DASHBOARD_DIR / filename).read_text(encoding="utf-8"))
        for key in ("version", "dashboard_title", "slug", "metadata", "charts", "position_json"):
            assert key in data, f"{filename}: missing top-level key {key!r}"

    @pytest.mark.parametrize("filename", _DASHBOARDS)
    def test_dashboard_has_at_least_one_chart(self, filename):
        data = json.loads((_DASHBOARD_DIR / filename).read_text(encoding="utf-8"))
        assert isinstance(data["charts"], list)
        assert len(data["charts"]) >= 1, f"{filename}: no charts"

    @pytest.mark.parametrize("filename", _DASHBOARDS)
    def test_chart_dataset_references_are_in_dataset_yaml(self, filename):
        data = json.loads((_DASHBOARD_DIR / filename).read_text(encoding="utf-8"))
        referenced = {chart["dataset"] for chart in data["charts"]}
        unknown = referenced - _REQUIRED_DATASETS
        assert not unknown, (
            f"{filename}: references dataset(s) not declared in "
            f"_dataset_definitions.yaml: {unknown}"
        )

    @pytest.mark.parametrize("filename", _DASHBOARDS)
    def test_position_json_root_grid_chart_chain(self, filename):
        data = json.loads((_DASHBOARD_DIR / filename).read_text(encoding="utf-8"))
        pos = data["position_json"]
        assert "ROOT_ID" in pos and pos["ROOT_ID"]["type"] == "ROOT"
        assert "GRID_ID" in pos and pos["GRID_ID"]["type"] == "GRID"
        # Each declared CHART-* slot maps to a real chart entry in the
        # `charts` list (matched by sliceName).
        chart_slot_names = {
            pos[k]["meta"]["sliceName"]
            for k in pos
            if k.startswith("CHART-") and "meta" in pos[k]
        }
        chart_names = {c["slice_name"] for c in data["charts"]}
        missing = chart_slot_names - chart_names
        assert not missing, (
            f"{filename}: position_json references chart sliceName(s) "
            f"missing from `charts`: {missing}"
        )


class TestDatasetDefinitions:
    def test_dataset_definitions_file_exists(self):
        path = _DASHBOARD_DIR / "_dataset_definitions.yaml"
        assert path.exists()

    def test_dataset_definitions_declares_all_required_datasets(self):
        # We avoid pulling in PyYAML for one test; just grep for
        # `dataset_name:` lines.
        text = (_DASHBOARD_DIR / "_dataset_definitions.yaml").read_text(encoding="utf-8")
        declared = {
            line.split(":", 1)[1].strip()
            for line in text.splitlines()
            if line.strip().startswith("- dataset_name:")
        }
        missing = _REQUIRED_DATASETS - declared
        assert not missing, f"Datasets missing from YAML: {missing}"
