"""Tests for tests/coverage_audit.py and SigNoz smoke test scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.coverage_audit import (
    ModuleStat,
    filter_below,
    parse_coverage_xml,
    render_report,
)


# ---------------------------------------------------------------------------
# Coverage parser
# ---------------------------------------------------------------------------


SAMPLE_COVERAGE_XML = """<?xml version="1.0" ?>
<coverage version="7.0" timestamp="0" lines-valid="0" lines-covered="0" line-rate="0.0">
  <sources/>
  <packages>
    <package name="src" line-rate="0.85">
      <classes>
        <class name="good_mod.py" filename="src/good_mod.py"
               lines-valid="100" lines-covered="95" line-rate="0.95">
          <lines/>
        </class>
        <class name="needs_work.py" filename="src/needs_work.py"
               lines-valid="200" lines-covered="100" line-rate="0.50">
          <lines/>
        </class>
        <class name="medium.py" filename="src/medium.py"
               lines-valid="50" lines-covered="40" line-rate="0.80">
          <lines/>
        </class>
        <class name="empty.py" filename="src/empty.py"
               lines-valid="0" lines-covered="0" line-rate="0.0">
          <lines/>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


class TestParseCoverageXML:
    def test_parses_module_stats(self, tmp_path: Path):
        path = tmp_path / "coverage.xml"
        path.write_text(SAMPLE_COVERAGE_XML, encoding="utf-8")

        stats = parse_coverage_xml(path)
        # Empty file skipped
        assert len(stats) == 3
        names = sorted(s.filename for s in stats)
        assert names == [
            "src/good_mod.py",
            "src/medium.py",
            "src/needs_work.py",
        ]

    def test_coverage_pct_computed(self, tmp_path: Path):
        path = tmp_path / "coverage.xml"
        path.write_text(SAMPLE_COVERAGE_XML, encoding="utf-8")

        stats = parse_coverage_xml(path)
        good = next(s for s in stats if "good_mod" in s.filename)
        assert good.coverage_pct == pytest.approx(95.0)
        assert good.uncovered == 5

    def test_falls_back_to_line_counting(self, tmp_path: Path):
        # XML without lines-valid attribute -- parser should count <line> elems
        xml = """<?xml version="1.0" ?>
<coverage>
  <packages><package>
    <classes>
      <class name="a.py" filename="src/a.py">
        <lines>
          <line number="1" hits="1"/>
          <line number="2" hits="0"/>
          <line number="3" hits="1"/>
        </lines>
      </class>
    </classes>
  </package></packages>
</coverage>
"""
        path = tmp_path / "coverage.xml"
        path.write_text(xml, encoding="utf-8")
        stats = parse_coverage_xml(path)
        assert len(stats) == 1
        assert stats[0].lines_valid == 3
        assert stats[0].lines_covered == 2


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestFilterBelow:
    def test_filters_below_threshold(self):
        stats = [
            ModuleStat("a.py", line_rate=0.95, lines_valid=100, lines_covered=95),
            ModuleStat("b.py", line_rate=0.70, lines_valid=100, lines_covered=70),
            ModuleStat("c.py", line_rate=0.85, lines_valid=100, lines_covered=85),
        ]
        below = filter_below(stats, threshold_pct=85.0)
        assert [s.filename for s in below] == ["b.py"]


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


class TestRenderReport:
    def test_empty_below_says_clear(self):
        report = render_report([], threshold=85.0)
        assert "Nothing to do" in report

    def test_sorted_by_uncovered_descending(self):
        below = [
            ModuleStat("small.py", line_rate=0.5, lines_valid=20, lines_covered=10),
            ModuleStat("big.py", line_rate=0.5, lines_valid=300, lines_covered=150),
            ModuleStat("med.py", line_rate=0.5, lines_valid=100, lines_covered=50),
        ]
        report = render_report(below, threshold=85.0)
        big_idx = report.index("big.py")
        med_idx = report.index("med.py")
        small_idx = report.index("small.py")
        assert big_idx < med_idx < small_idx

    def test_priority_buckets(self):
        below = [
            ModuleStat("small.py", line_rate=0.5, lines_valid=20, lines_covered=10),
            ModuleStat("big.py", line_rate=0.5, lines_valid=300, lines_covered=150),
            ModuleStat("med.py", line_rate=0.5, lines_valid=100, lines_covered=50),
        ]
        report = render_report(below, threshold=85.0)
        # big has 150 uncovered -> HIGH
        # med has 50 uncovered -> LOW (boundary: > 50 = MED)
        # small has 10 uncovered -> LOW
        assert "| HIGH |" in report
        assert "LOW" in report

    def test_total_uncovered_line_present(self):
        below = [
            ModuleStat("a.py", line_rate=0.5, lines_valid=20, lines_covered=10),
            ModuleStat("b.py", line_rate=0.5, lines_valid=30, lines_covered=15),
        ]
        report = render_report(below, threshold=85.0)
        # Total uncovered: 10 + 15 = 25
        assert "25" in report


# ---------------------------------------------------------------------------
# SigNoz smoke test gating
# ---------------------------------------------------------------------------


class TestSigNozSmokeGating:
    def test_smoke_test_collects(self):
        # The smoke test module should import cleanly + collect even
        # without SigNoz running (it skips at runtime).
        from tests.integration import test_signoz_smoke

        assert hasattr(test_signoz_smoke, "TestSigNozTracePipeline")
        assert hasattr(test_signoz_smoke, "_signoz_enabled")
        assert hasattr(test_signoz_smoke, "_signoz_ui_reachable")
