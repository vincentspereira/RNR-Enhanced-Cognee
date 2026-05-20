"""Coverage gap auditor.

Reads ``coverage.xml`` (produced by ``pytest --cov --cov-report=xml``)
and reports modules below a configurable per-module threshold (default
85%). Designed as the first step of the "bring every module to >=85%"
workstream: this script generates the prioritised hit-list; humans
then write tests against each module.

Usage:

    # 1. Generate coverage.xml
    pytest --cov=src --cov-report=xml

    # 2. Audit
    python -m tests.coverage_audit --threshold 85

The output is sorted by absolute number of uncovered lines (biggest
gaps first) so reviewers can pick the highest-impact targets.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ModuleStat:
    filename: str
    line_rate: float          # 0.0-1.0
    lines_valid: int
    lines_covered: int

    @property
    def uncovered(self) -> int:
        return self.lines_valid - self.lines_covered

    @property
    def coverage_pct(self) -> float:
        return self.line_rate * 100.0


def parse_coverage_xml(path: Path) -> List[ModuleStat]:
    """Parse a coverage.xml (Cobertura format) into per-file stats."""
    tree = ET.parse(path)
    root = tree.getroot()

    stats: List[ModuleStat] = []
    for cls in root.iter("class"):
        filename = cls.get("filename", "")
        # `lines-valid` and `lines-covered` aren't always present; fall
        # back to counting hits on the <lines>/<line> elements.
        lines_valid = int(cls.get("lines-valid", 0))
        lines_covered = int(cls.get("lines-covered", 0))
        line_rate = float(cls.get("line-rate", 0.0))

        if lines_valid == 0:
            lines = list(cls.iter("line"))
            lines_valid = len(lines)
            lines_covered = sum(1 for ln in lines if int(ln.get("hits", 0)) > 0)
            line_rate = (
                lines_covered / lines_valid if lines_valid > 0 else 0.0
            )

        if lines_valid == 0:
            continue   # empty file -- skip

        stats.append(
            ModuleStat(
                filename=filename,
                line_rate=line_rate,
                lines_valid=lines_valid,
                lines_covered=lines_covered,
            )
        )

    return stats


def filter_below(stats: List[ModuleStat], threshold_pct: float) -> List[ModuleStat]:
    return [s for s in stats if s.coverage_pct < threshold_pct]


def render_report(below: List[ModuleStat], threshold: float) -> str:
    """Render a markdown report sorted by absolute uncovered-line count."""
    below_sorted = sorted(below, key=lambda s: -s.uncovered)

    lines: List[str] = []
    lines.append(f"# Coverage Gap Report (threshold: {threshold:.0f}%)")
    lines.append("")
    lines.append(f"**{len(below_sorted)} modules below {threshold:.0f}%.**")
    lines.append("Sorted by absolute uncovered-line count (biggest gaps first).")
    lines.append("")
    if not below_sorted:
        lines.append("All modules clear the threshold. Nothing to do.")
        return "\n".join(lines)

    lines.append("| File | Coverage | Uncovered / Valid | Priority |")
    lines.append("| --- | ---: | ---: | --- |")
    for s in below_sorted:
        # Priority: > 100 uncovered = HIGH; 50-100 = MED; < 50 = LOW
        if s.uncovered > 100:
            prio = "HIGH"
        elif s.uncovered > 50:
            prio = "MED"
        else:
            prio = "LOW"
        lines.append(
            f"| `{s.filename}` | {s.coverage_pct:.1f}% | "
            f"{s.uncovered} / {s.lines_valid} | {prio} |"
        )

    lines.append("")
    total_uncovered = sum(s.uncovered for s in below_sorted)
    lines.append(
        f"**Total uncovered lines in below-threshold modules: {total_uncovered}.**"
    )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Coverage gap auditor.")
    parser.add_argument(
        "--coverage-xml",
        default="coverage.xml",
        type=Path,
        help="Path to coverage.xml (Cobertura format)",
    )
    parser.add_argument(
        "--threshold",
        default=85.0,
        type=float,
        help="Per-module coverage threshold in percent",
    )
    parser.add_argument(
        "--fail-on-gap",
        action="store_true",
        help="Exit non-zero if any module is below the threshold",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write report to this file (default: stdout)",
    )
    args = parser.parse_args(argv)

    if not args.coverage_xml.exists():
        print(
            f"ERR coverage.xml not found at {args.coverage_xml}. "
            "Run pytest with `--cov=src --cov-report=xml` first.",
            file=sys.stderr,
        )
        return 2

    stats = parse_coverage_xml(args.coverage_xml)
    below = filter_below(stats, args.threshold)

    report = render_report(below, args.threshold)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(report)

    if args.fail_on_gap and below:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
