"""Unit tests for the cross-provider benchmark runner.

The runner itself shells out to Locust, but the parsing + reporting
layers are pure-Python and worth testing so we catch regressions in
the report format used in PR descriptions.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.benchmarks import run_provider_comparison as bench


# ---------------------------------------------------------------------------
# Permutation matrix
# ---------------------------------------------------------------------------


class TestPermutations:
    def test_has_at_least_three_permutations(self):
        assert len(bench.PROVIDER_PERMUTATIONS) >= 3

    def test_each_permutation_has_required_keys(self):
        required = {
            "name",
            "ENHANCED_GRAPH_PROVIDER",
            "ENHANCED_VECTOR_PROVIDER",
            "ENHANCED_CACHE_PROVIDER",
            "ENHANCED_RELATIONAL_PROVIDER",
        }
        for perm in bench.PROVIDER_PERMUTATIONS:
            missing = required - perm.keys()
            assert not missing, f"Permutation {perm.get('name')!r}: missing {missing}"

    def test_permutation_names_are_unique(self):
        names = [p["name"] for p in bench.PROVIDER_PERMUTATIONS]
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# CSV parser
# ---------------------------------------------------------------------------


def _write_stats_csv(path: Path, rows):
    fieldnames = [
        "Type",
        "Name",
        "Request Count",
        "Failure Count",
        "Median Response Time",
        "Average Response Time",
        "50%",
        "95%",
        "99%",
        "Requests/s",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


class TestParseLocustCSV:
    def test_aggregates_and_per_endpoint_split(self, tmp_path: Path):
        prefix = tmp_path / "perm_x"
        stats = prefix.with_name(prefix.name + "_stats.csv")
        _write_stats_csv(
            stats,
            [
                {
                    "Type": "GET",
                    "Name": "/search",
                    "Request Count": "100",
                    "Failure Count": "1",
                    "Median Response Time": "10",
                    "Average Response Time": "12",
                    "50%": "10",
                    "95%": "30",
                    "99%": "50",
                    "Requests/s": "20",
                },
                {
                    "Type": "POST",
                    "Name": "/add",
                    "Request Count": "50",
                    "Failure Count": "0",
                    "Median Response Time": "8",
                    "Average Response Time": "9",
                    "50%": "8",
                    "95%": "20",
                    "99%": "40",
                    "Requests/s": "10",
                },
                {
                    "Type": "",
                    "Name": "Aggregated",
                    "Request Count": "150",
                    "Failure Count": "1",
                    "Median Response Time": "9",
                    "Average Response Time": "11",
                    "50%": "9",
                    "95%": "27",
                    "99%": "47",
                    "Requests/s": "30",
                },
            ],
        )

        perm = {
            "name": "perm_x",
            "ENHANCED_GRAPH_PROVIDER": "arcadedb",
            "ENHANCED_VECTOR_PROVIDER": "qdrant",
            "ENHANCED_CACHE_PROVIDER": "valkey",
            "ENHANCED_RELATIONAL_PROVIDER": "postgres",
        }
        result = bench._parse_locust_csv("perm_x", perm, prefix)

        assert result.total_requests == 150
        assert result.total_failures == 1
        assert result.rps == 30.0
        assert result.p50_ms == 9.0
        assert result.p95_ms == 27.0
        assert result.p99_ms == 47.0
        assert result.error_pct == pytest.approx(100.0 / 150.0)
        assert len(result.per_endpoint) == 2

    def test_missing_csv_returns_empty_result(self, tmp_path: Path):
        # File doesn't exist on disk
        result = bench._parse_locust_csv(
            "perm_missing",
            {"name": "perm_missing", "ENHANCED_GRAPH_PROVIDER": "x"},
            tmp_path / "perm_missing",
        )
        assert result.total_requests == 0
        assert result.rps == 0.0

    def test_missing_aggregated_row(self, tmp_path: Path):
        prefix = tmp_path / "perm_y"
        stats = prefix.with_name(prefix.name + "_stats.csv")
        _write_stats_csv(
            stats,
            [
                {
                    "Type": "GET",
                    "Name": "/search",
                    "Request Count": "5",
                    "Failure Count": "0",
                    "Median Response Time": "10",
                    "Average Response Time": "12",
                    "50%": "10",
                    "95%": "30",
                    "99%": "50",
                    "Requests/s": "5",
                }
            ],
        )

        result = bench._parse_locust_csv("perm_y", {"name": "perm_y"}, prefix)
        # No "Aggregated" row -> falls back to zeroed result
        assert result.total_requests == 0
        assert result.rps == 0.0


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


class TestWriteReports:
    def test_writes_json_and_markdown(self, tmp_path: Path):
        result = bench.RunResult(
            name="demo",
            providers={
                "ENHANCED_GRAPH_PROVIDER": "arcadedb",
                "ENHANCED_VECTOR_PROVIDER": "qdrant",
                "ENHANCED_CACHE_PROVIDER": "valkey",
                "ENHANCED_RELATIONAL_PROVIDER": "postgres",
            },
            total_requests=100,
            total_failures=2,
            rps=10.0,
            p50_ms=5,
            p95_ms=15,
            p99_ms=30,
            error_pct=2.0,
            per_endpoint=[
                {
                    "Name": "/x",
                    "Request Count": "100",
                    "Failure Count": "2",
                    "50%": "5",
                    "95%": "15",
                    "99%": "30",
                    "Requests/s": "10",
                }
            ],
        )
        bench.write_reports([result], tmp_path)

        json_path = tmp_path / "provider_comparison.json"
        md_path = tmp_path / "provider_comparison.md"

        assert json_path.exists()
        assert md_path.exists()

        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(loaded) == 1
        assert loaded[0]["name"] == "demo"
        assert loaded[0]["rps"] == 10.0

        md = md_path.read_text(encoding="utf-8")
        assert "Cross-provider benchmark comparison" in md
        assert "demo" in md
        assert "arcadedb" in md
        # Per-endpoint section should be present
        assert "Per-endpoint detail" in md
        assert "/x" in md


# ---------------------------------------------------------------------------
# Build env
# ---------------------------------------------------------------------------


class TestBuildEnv:
    def test_run_env_overrides_provider_vars(self):
        perm = {
            "name": "perm",
            "ENHANCED_GRAPH_PROVIDER": "apache_age",
            "ENHANCED_VECTOR_PROVIDER": "pgvector",
        }
        env = bench._build_run_env(perm)
        assert env["ENHANCED_GRAPH_PROVIDER"] == "apache_age"
        assert env["ENHANCED_VECTOR_PROVIDER"] == "pgvector"
        assert "name" not in env or env.get("name") != "perm"


# ---------------------------------------------------------------------------
# CLI main()
# ---------------------------------------------------------------------------


class TestMainCLI:
    def test_main_fails_when_locust_missing(self):
        with patch("tests.benchmarks.run_provider_comparison.shutil.which", return_value=None):
            rc = bench.main(["--output-dir", "tests/benchmarks/_unused"])
        assert rc == 2
