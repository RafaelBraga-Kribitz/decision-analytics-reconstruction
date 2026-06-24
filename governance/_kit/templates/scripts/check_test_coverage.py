"""Verify test line coverage stays above the project-defined threshold.

Reads coverage data from:
  1. .coverage database (coverage.py) — preferred
  2. coverage.xml — fallback if .coverage is absent

Gate: F-COVERAGE-GAP (coverage_regression category)

Run with --baseline to print the current coverage without gating.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate


def _load_threshold() -> float:
    try:
        import yaml
        cfg_path = REPO_ROOT / "config" / "quality_gates.yaml"
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            return float(data.get("coverage", {}).get("min_lines", 80))
    except Exception:
        pass
    return 80.0


def _coverage_from_db() -> float | None:
    try:
        import coverage as cov_lib
        import io
        cov = cov_lib.Coverage(data_file=str(REPO_ROOT / ".coverage"))
        cov.load()
        buf = io.StringIO()
        total = cov.report(file=buf)
        return float(total)
    except Exception:
        return None


def _coverage_from_xml() -> float | None:
    xml_path = REPO_ROOT / "coverage.xml"
    if not xml_path.exists():
        return None
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        rate = tree.getroot().attrib.get("line-rate")
        return float(rate) * 100 if rate else None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()

    try:
        import coverage as _  # noqa: F401
    except ImportError:
        print("[SKIP] check_test_coverage.py: coverage not installed (pip install coverage)")
        return 0

    pct = _coverage_from_db() or _coverage_from_xml()

    if args.baseline:
        if pct is None:
            print("[BASELINE] check_test_coverage.py: no coverage data found — run pytest --cov first")
        else:
            print(f"[BASELINE] check_test_coverage.py: current line coverage = {pct:.1f}%")
            print(f"           Suggested quality_gates.coverage.min_lines: {max(0, pct - 5):.0f}")
        return 0

    if pct is None:
        return gate(
            "F-COVERAGE-GAP", "check_test_coverage.py", False,
            "no coverage data found (.coverage or coverage.xml) — run pytest --cov first",
        )

    threshold = _load_threshold()
    fixed = pct >= threshold
    return gate(
        "F-COVERAGE-GAP", "check_test_coverage.py", fixed,
        f"line coverage {pct:.1f}% is below threshold {threshold:.0f}%",
    )


if __name__ == "__main__":
    sys.exit(main())
