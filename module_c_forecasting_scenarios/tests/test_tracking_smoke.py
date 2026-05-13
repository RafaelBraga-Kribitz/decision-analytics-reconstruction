"""PyMC tracking model smoke (MC_FAST)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    _build_day_index,
    export_daily_posterior_table,
    fit_tracking_hierarchical,
)

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def _synthetic_tracking_near_m_star() -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(0)
    for i in range(10):
        pub = date(2018, 2, 10) + timedelta(days=i * 8)
        noise = float(rng.normal(0, 0.8))
        a = 50.0 + (3.7 + noise) / 2
        b = 50.0 - (3.7 + noise) / 2
        rows.append(
            {
                "poll_wave_id": f"wave_synth_{i}",
                "pollster_id": "pollster_a" if i % 2 == 0 else "pollster_b",
                "pollster_bias_family": "default",
                "publication_date": pub,
                "field_window_start": pub - timedelta(days=3),
                "field_window_end": pub,
                "preference_proxy_a_pct": a,
                "preference_proxy_b_pct": b,
                "m_poll_pp": a - b,
                "redistribution_rule": "exclude",
                "phi_transparency": 0.75,
                "tau_eff": 0.75,
                "calibration_series": "A",
                "series_tag": "A",
                "conglomerate_id": None,
                "media_holding": None,
                "sample_size_known": True,
                "firm_wave_month": f"{pub.year:04d}-{pub.month:02d}",
                "scenario_bucket": "baseline",
                "shock_score_s": 0.1,
                "has_ficha": True,
            }
        )
    return pd.DataFrame(rows)


def test_fit_tracking_hierarchical_runs() -> None:
    tr = _synthetic_tracking_near_m_star()
    outcome = date(2018, 4, 22)
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=outcome,
        calibration_series="A",
    )
    assert idata is not None
    assert "mu_margin" in idata.posterior


def test_daily_export_shape() -> None:
    tr = _synthetic_tracking_near_m_star()
    outcome = date(2018, 4, 22)
    days, _ = _build_day_index(tr, outcome)
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=outcome,
        calibration_series="A",
    )
    daily = export_daily_posterior_table(idata, days, "A")
    assert len(daily) == len(days)
    assert "posterior_mean_preference_margin_pp" in daily.columns
