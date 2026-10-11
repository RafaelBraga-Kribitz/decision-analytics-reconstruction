#!/usr/bin/env python3
"""Verification script for F-086 (no silent substitution in the Module B data layer).

Functional checks, no network and no solver:
(a) a missing FX week is reported and fails the FX gate, a complete config
    reports nothing;
(b) on the deterministic dirty batch every dropped row carries a reason and
    ``n_raw - n_clean == n_rejected`` per source (and volunteer logs survive);
(c) the committed disclosure artifacts exist and reconcile with (b).

Spec: governance/improvement_plan/IMP-B04_silent-substitution.md
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
from _governance_check import REPO_ROOT, gate

REPORTS = REPO_ROOT / "reports" / "module_b"
CLEAN_KEY = {
    "budget_lines_raw.csv": "budget_lines_clean",
    "volunteer_logs_raw.csv": "volunteer_logs_clean",
    "media_buy_sheet_raw.csv": "media_buy_sheet_clean",
}


def _fx_gaps() -> list[str]:
    from module_b_resource_allocation.fx.spread_model import (
        fx_fallback_gate,
        fx_fallback_report,
        load_spread_config,
    )
    from module_b_resource_allocation.fx.tc_ref_loader import build_daily_series

    daily, cfg = build_daily_series(), load_spread_config()
    gaps = []
    if fx_fallback_gate(fx_fallback_report(daily, cfg)) != "PASS":
        gaps.append("committed FX spread config leaves weeks on the default fallback")
    weekly = {k: v for k, v in cfg["series_b_weekly"].items() if k != "2018-W07"}
    report = fx_fallback_report(daily, {**cfg, "series_b_weekly": weekly})
    if list(report["iso_week"]) != ["2018-W07"] or fx_fallback_gate(report) != "FAIL":
        gaps.append("a missing FX week is not reported or does not fail the gate")
    return gaps


def _cleaning_gaps() -> tuple[list[str], pd.DataFrame | None]:
    from module_b_resource_allocation.data.cleaner import clean_directory_with_report
    from module_b_resource_allocation.data.dirty_generator import DirtyGenConfig, generate_all

    with tempfile.TemporaryDirectory() as tmp:
        generate_all(DirtyGenConfig(), Path(tmp))
        frames, rejections, summary = clean_directory_with_report(Path(tmp))
    gaps = []
    if rejections["reason"].isna().any():
        gaps.append("rejected rows without a reason")
    for row in summary.itertuples():
        if row.n_raw - len(frames[CLEAN_KEY[row.source_file]]) != row.n_rejected:
            gaps.append(f"{row.source_file}: dropped rows do not reconcile with reasons")
    if len(frames["volunteer_logs_clean"]) == 0:
        gaps.append("volunteer_logs_clean is empty (silent total drop)")
    return gaps, summary


def _artifact_gaps(summary: pd.DataFrame | None) -> list[str]:
    paths = [
        REPORTS / n
        for n in (
            "data_rejection_report.csv",
            "fx_fallback_report.csv",
            "data_quality_summary.json",
        )
    ]
    missing = [p.name for p in paths if not p.is_file()]
    if missing:
        return [f"missing disclosure artifact(s) {missing}"]
    agg = pd.read_csv(paths[0])
    committed = json.loads(paths[2].read_text(encoding="utf-8"))
    gaps = []
    for src in committed["sources"]:
        if agg.loc[agg["source_file"] == src["source_file"], "count"].sum() != src["n_rejected"]:
            gaps.append(f"data_rejection_report.csv does not reconcile for {src['source_file']}")
    if summary is not None:
        live = dict(zip(summary["source_file"], summary["n_rejected"], strict=True))
        if {s["source_file"]: s["n_rejected"] for s in committed["sources"]} != live:
            gaps.append("committed data_quality_summary.json is stale; regenerate it")
    return gaps


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT / "module_b_resource_allocation" / "src"))
    try:
        cleaning, summary = _cleaning_gaps()
        gaps = _fx_gaps() + cleaning
    except (ImportError, AttributeError) as exc:
        gaps, summary = [f"disclosure helpers missing ({exc})"], None
    gaps += _artifact_gaps(summary)
    return gate("F-086", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())
