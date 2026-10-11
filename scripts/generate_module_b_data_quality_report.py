#!/usr/bin/env python3
"""Publish Module B's data-quality disclosure artifacts (F-086 / IMP-B04).

Regenerates the deterministic dirty input batch (``DirtyGenConfig`` defaults),
cleans it, and writes under ``reports/module_b/``:

* ``data_rejection_report.csv`` — rejected-row counts by source, reason,
  department and channel (no row is dropped without a reason).
* ``fx_fallback_report.csv`` — weeks that used the default FX spread add-on.
* ``data_quality_summary.json`` — per-source rejection rates and gates, and
  the FX fallback gate.

Outputs are byte-identical across runs (sorted, no timestamps).

Usage: ``poetry run python scripts/generate_module_b_data_quality_report.py``
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
from module_b_resource_allocation.data.cleaner import (
    REJECTION_RATE_GATE,
    clean_directory_with_report,
)
from module_b_resource_allocation.data.dirty_generator import DirtyGenConfig, generate_all
from module_b_resource_allocation.fx.spread_model import (
    fx_fallback_gate,
    fx_fallback_report,
    load_spread_config,
)
from module_b_resource_allocation.fx.tc_ref_loader import build_daily_series

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "reports" / "module_b"
REJECTION_CSV = OUT_DIR / "data_rejection_report.csv"
FX_FALLBACK_CSV = OUT_DIR / "fx_fallback_report.csv"
SUMMARY_JSON = OUT_DIR / "data_quality_summary.json"
GROUP_KEYS = ["source_file", "reason", "department", "channel"]


def build_reports() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (aggregated rejections, FX fallback weeks, summary dict)."""
    cfg = DirtyGenConfig()
    with tempfile.TemporaryDirectory() as tmp:
        generate_all(cfg, Path(tmp))
        frames, rejections, summary = clean_directory_with_report(Path(tmp))
    aggregated = (
        rejections.fillna({"department": "(unresolved)", "channel": "(unresolved)"})
        .groupby(GROUP_KEYS, as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(GROUP_KEYS)
        .reset_index(drop=True)
    )
    fx = fx_fallback_report(build_daily_series(), load_spread_config())
    payload = {
        "input_batch": {"generator": "DirtyGenConfig defaults", "seed": cfg.seed},
        "rejection_gate_threshold": REJECTION_RATE_GATE,
        "sources": summary.to_dict(orient="records"),
        "clean_row_counts": {k: len(v) for k, v in sorted(frames.items())},
        "fx_fallback_weeks": len(fx),
        "fx_fallback_gate": fx_fallback_gate(fx),
        "note": (
            "The demo batch injects nulls and duplicates on purpose "
            "(DirtyGenConfig.null_rate / duplicate_rate), so its rejection gates "
            "report FAIL by design; the point is that every drop is counted."
        ),
    }
    return aggregated, fx, payload


def main() -> int:
    aggregated, fx, payload = build_reports()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    aggregated.to_csv(REJECTION_CSV, index=False, lineterminator="\n")
    fx.to_csv(FX_FALLBACK_CSV, index=False, lineterminator="\n")
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in (REJECTION_CSV, FX_FALLBACK_CSV, SUMMARY_JSON):
        print(f"[PASS] wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
