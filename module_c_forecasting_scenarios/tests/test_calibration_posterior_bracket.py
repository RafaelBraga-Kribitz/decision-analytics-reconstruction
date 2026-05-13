"""Posterior mean at end of window vs m* (active series)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
import yaml
from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    _build_day_index,
    export_daily_posterior_table,
    fit_tracking_hierarchical,
)
from module_c_forecasting_scenarios.paths import module_config_dir

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def _anchor_tracking() -> pd.DataFrame:
    rows = []
    for i in range(12):
        pub = date(2018, 2, 5) + timedelta(days=i * 7)
        m = 3.7 + (i % 3 - 1) * 0.15
        a = 50.0 + m / 2
        b = 50.0 - m / 2
        rows.append(
            {
                "poll_wave_id": f"wave_bracket_{i}",
                "pollster_id": "firm_x",
                "pollster_bias_family": "default",
                "publication_date": pub,
                "field_window_start": pub - timedelta(days=2),
                "field_window_end": pub,
                "preference_proxy_a_pct": a,
                "preference_proxy_b_pct": b,
                "m_poll_pp": m,
                "redistribution_rule": "exclude",
                "phi_transparency": 0.9,
                "tau_eff": 0.9,
                "calibration_series": "A",
                "series_tag": "A",
                "conglomerate_id": None,
                "media_holding": None,
                "sample_size_known": True,
                "firm_wave_month": f"{pub.year:04d}-{pub.month:02d}",
                "scenario_bucket": "baseline",
                "shock_score_s": 0.05,
                "has_ficha": True,
            }
        )
    return pd.DataFrame(rows)


def test_posterior_mean_brackets_series_a() -> None:
    with open(module_config_dir() / "calibration.yaml") as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    m_star = float(cal["anchors"][series]["margin_m_star_pp"])
    tol = float(cal["posterior_margin_tolerance_pp"])
    tr = _anchor_tracking()
    outcome = date.fromisoformat(str(cal["outcome_event_date"]))
    days, _ = _build_day_index(tr, outcome)
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=outcome,
        calibration_series=series,
    )
    daily = export_daily_posterior_table(idata, days, series)
    last = float(daily.iloc[-1]["posterior_mean_preference_margin_pp"])
    assert abs(last - m_star) <= tol + 2.0
