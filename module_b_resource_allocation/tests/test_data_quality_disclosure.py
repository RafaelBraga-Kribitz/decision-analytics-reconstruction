"""No silent substitution in the Module B data layer (F-086 / IMP-B04)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import pytest
from module_b_resource_allocation.data.cleaner import (
    REJECTION_RATE_GATE,
    clean_budget_lines,
    clean_directory_with_report,
    rejection_summary,
)
from module_b_resource_allocation.data.dirty_generator import DirtyGenConfig, generate_all
from module_b_resource_allocation.fx.spread_model import (
    DEFAULT_SPREAD_PYG_PER_USD,
    apply_retail_spread,
    fx_fallback_gate,
    fx_fallback_report,
    load_spread_config,
)
from module_b_resource_allocation.fx.tc_ref_loader import build_daily_series

_CLEAN_KEY = {
    "budget_lines_raw.csv": "budget_lines_clean",
    "volunteer_logs_raw.csv": "volunteer_logs_clean",
    "media_buy_sheet_raw.csv": "media_buy_sheet_clean",
}


@pytest.fixture(scope="module")
def cleaned_with_report(tmp_path_factory: pytest.TempPathFactory):
    out = tmp_path_factory.mktemp("dirty")
    generate_all(DirtyGenConfig(), out)
    return clean_directory_with_report(out)


def test_every_drop_has_a_reason(cleaned_with_report) -> None:
    frames, rejections, summary = cleaned_with_report
    assert rejections["reason"].notna().all()
    for row in summary.itertuples():
        assert row.n_raw - len(frames[_CLEAN_KEY[row.source_file]]) == row.n_rejected


def test_volunteer_logs_survive_cleaning(cleaned_with_report) -> None:
    """Regression: dtype inference once turned contacts_text into floats and
    the locale parser silently rejected all 3,500 volunteer rows."""
    frames, _, summary = cleaned_with_report
    assert len(frames["volunteer_logs_clean"]) > 3_000
    vol = summary.set_index("source_file").loc["volunteer_logs_raw.csv"]
    assert vol.rejection_rate < 0.05


def test_rejection_reasons_and_gate() -> None:
    raw = pd.DataFrame(
        {
            "row_id": ["B1", "B2", "B3", "B4", "B4"],
            "vendor": ["v"] * 5,
            "channel_text": ["Radio", "Radio", "Radio", "Radio", "Radio"],
            "department_text": ["Itapúa"] * 5,
            "week_label": ["2018-W01"] * 5,
            "currency": ["USD", "XYZ", "USD", "USD", "USD"],
            "amount_text": ["100", "100", "abc", "50", "50"],
            "fx_tier_hint": ["REF"] * 5,
        }
    )
    frame = clean_budget_lines(raw)
    reasons = sorted(frame.rejections["reason"])
    assert reasons == ["duplicate_row_id", "unparsable_amount", "unrecognized_currency"]
    assert len(frame.df) == 2
    summary = rejection_summary(frame.rejections, {"budget_lines_raw.csv": len(raw)})
    assert summary.loc[0, "n_rejected"] == 3
    assert summary.loc[0, "gate_status"] == "FAIL"  # 3/5 > REJECTION_RATE_GATE
    assert (
        rejection_summary(frame.rejections.iloc[0:0], {"x.csv": 100}).loc[0, "rejection_rate"]
        <= REJECTION_RATE_GATE
    )


def test_complete_fx_config_has_no_fallback() -> None:
    report = fx_fallback_report(build_daily_series(), load_spread_config())
    assert report.empty
    assert fx_fallback_gate(report) == "PASS"


def test_missing_week_is_disclosed_and_fails(caplog: pytest.LogCaptureFixture) -> None:
    daily = build_daily_series()
    cfg = load_spread_config()
    cfg = {
        **cfg,
        "series_b_weekly": {k: v for k, v in cfg["series_b_weekly"].items() if k != "2018-W07"},
    }
    report = fx_fallback_report(daily, cfg)
    assert list(report["iso_week"]) == ["2018-W07"]
    tc_ref = float(report.loc[0, "tc_ref"])
    assert report.loc[0, "fallback_pct_applied"] == pytest.approx(
        DEFAULT_SPREAD_PYG_PER_USD / tc_ref
    )
    assert fx_fallback_gate(report) == "FAIL"
    with caplog.at_level(logging.WARNING):
        out = apply_retail_spread(daily, cfg)
    assert "2018-W07" in caplog.text
    w07 = out.loc[out["iso_week"] == "2018-W07"]
    assert (w07["tc_retail"] == w07["tc_ref"] + DEFAULT_SPREAD_PYG_PER_USD).all()


def test_committed_reports_reconcile() -> None:
    root = Path(__file__).resolve().parents[2] / "reports" / "module_b"
    agg = pd.read_csv(root / "data_rejection_report.csv")

    summary = json.loads((root / "data_quality_summary.json").read_text(encoding="utf-8"))
    for src in summary["sources"]:
        assert agg.loc[agg["source_file"] == src["source_file"], "count"].sum() == src["n_rejected"]
