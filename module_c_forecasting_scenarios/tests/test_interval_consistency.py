"""Interval-type / level consistency for the tracking credible bands.

AUD interval-mislabel: the daily-margin and house-effect export functions stored
``post.quantile(0.05)`` / ``quantile(0.95)`` — a 90% *equal-tailed* interval — in
columns named ``*_hdi_*`` and every figure titled the band "94% HDI". This suite
pins the honest behaviour:

1. The exported ``*_hdi_*`` bounds equal a genuine ``az.hdi(..., hdi_prob=0.94)``
   highest-density interval on the same posterior (interval *type* = HDI).
2. They are NOT the old 5/95 equal-tailed quantiles — the 94% HDI is materially
   wider than the 90% ETI (interval *level* = 0.94, the negative-control that
   gives the test power).
3. The fit stamps ``interval_type='HDI'`` / ``interval_prob=0.94`` into the idata
   attrs and a v0.3+ ``model_version`` so two artifacts cannot silently disagree
   on what the band means.
"""

from __future__ import annotations

from datetime import date, timedelta

import arviz as az
import numpy as np
import pandas as pd
import pytest

from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    HDI_PROB,
    export_daily_posterior_table,
    export_house_effects_table,
    fit_tracking_hierarchical,
)

pytestmark = pytest.mark.slow

OUTCOME = date(2018, 4, 22)


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def _tracking(n: int = 4, level_pp: float = 5.0) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows: list[dict[str, object]] = []
    for i in range(n):
        pub = date(2018, 2, 1) + timedelta(days=i * 14)
        m = level_pp + float(rng.normal(0, 0.4))
        rows.append(
            {
                "poll_wave_id": f"wave_{i}",
                "pollster_id": "pollster_a" if i % 2 == 0 else "pollster_b",
                "pollster_bias_family": "default",
                "publication_date": pub,
                "field_window_start": pub - timedelta(days=3),
                "field_window_end": pub,
                "preference_proxy_a_pct": 50.0 + m / 2,
                "preference_proxy_b_pct": 50.0 - m / 2,
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
                "shock_score_s": 0.1,
                "has_ficha": True,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fit_and_tables():
    import os

    os.environ["MC_FAST"] = "1"
    tracking = _tracking()
    from module_c_forecasting_scenarios.models.tracking.hierarchical import _build_day_index

    days, _ = _build_day_index(tracking, OUTCOME)
    idata = fit_tracking_hierarchical(
        tracking, outcome_event_date=OUTCOME, calibration_series="A", m_star_pp=3.70
    )
    pollsters = sorted(tracking["pollster_id"].astype(str).unique())
    daily = export_daily_posterior_table(idata, days, "A")
    houses = export_house_effects_table(idata, pollsters, "A", tracking)
    return idata, daily, houses


def test_daily_hdi_columns_are_true_hdi(fit_and_tables) -> None:
    idata, daily, _ = fit_and_tables
    post = idata.posterior["mu_margin"]
    h = az.hdi(post, hdi_prob=HDI_PROB)
    h = h[next(iter(h.data_vars))] if hasattr(h, "data_vars") else h
    exp_low = np.asarray(h.sel(hdi="lower").values, float).reshape(-1)
    exp_high = np.asarray(h.sel(hdi="higher").values, float).reshape(-1)
    np.testing.assert_allclose(daily["posterior_hdi_low_pp"].to_numpy(), exp_low, atol=1e-9)
    np.testing.assert_allclose(daily["posterior_hdi_high_pp"].to_numpy(), exp_high, atol=1e-9)
    # bands bracket the mean
    assert (daily["posterior_hdi_low_pp"] <= daily["posterior_mean_preference_margin_pp"]).all()
    assert (daily["posterior_hdi_high_pp"] >= daily["posterior_mean_preference_margin_pp"]).all()


def test_hdi_is_not_the_old_5_95_quantile_interval(fit_and_tables) -> None:
    """Negative control: 94% HDI must be materially wider than the old 90% ETI."""
    idata, daily, _ = fit_and_tables
    post = idata.posterior["mu_margin"]
    q05 = np.asarray(post.quantile(0.05, dim=("chain", "draw")).values, float).reshape(-1)
    q95 = np.asarray(post.quantile(0.95, dim=("chain", "draw")).values, float).reshape(-1)
    eti90_width = float(np.mean(q95 - q05))
    hdi94_width = float(np.mean(daily["posterior_hdi_high_pp"] - daily["posterior_hdi_low_pp"]))
    assert hdi94_width > eti90_width + 1e-6, (
        f"94% HDI width {hdi94_width:.3f} not wider than the old 90% ETI "
        f"{eti90_width:.3f} — bands may still be 5/95 quantiles"
    )


def test_interval_metadata_is_stamped(fit_and_tables) -> None:
    idata, _, _ = fit_and_tables
    assert idata.attrs.get("interval_type") == "HDI"
    assert float(idata.attrs.get("interval_prob")) == pytest.approx(0.94)
    assert str(idata.attrs.get("model_version", "")).endswith(("v0.3", "v0.4", "v0.5"))


def test_house_effect_hdi_columns_are_true_hdi(fit_and_tables) -> None:
    idata, _, houses = fit_and_tables
    post = idata.posterior["house_offset"]
    h = az.hdi(post, hdi_prob=HDI_PROB)
    h = h[next(iter(h.data_vars))] if hasattr(h, "data_vars") else h
    exp_low = np.asarray(h.sel(hdi="lower").values, float).reshape(-1)
    exp_high = np.asarray(h.sel(hdi="higher").values, float).reshape(-1)
    np.testing.assert_allclose(houses["house_effect_hdi_low"].to_numpy(), exp_low, atol=1e-9)
    np.testing.assert_allclose(houses["house_effect_hdi_high"].to_numpy(), exp_high, atol=1e-9)
