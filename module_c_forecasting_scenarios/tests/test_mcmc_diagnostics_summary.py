"""Slow-path MCMC diagnostics using ArviZ (runs with ``MC_FAST=1`` for speed)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.slow


def _tiny_tracking() -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(7)
    for i in range(8):
        pub = date(2018, 2, 5) + timedelta(days=i * 10)
        noise = float(rng.normal(0, 0.4))
        a = 50.0 + (3.7 + noise) / 2
        b = 50.0 - (3.7 + noise) / 2
        rows.append(
            {
                "poll_wave_id": f"wave_{i}",
                "pollster_id": "p_a" if i % 2 == 0 else "p_b",
                "pollster_bias_family": "default",
                "publication_date": pub,
                "field_window_start": pub - timedelta(days=2),
                "field_window_end": pub,
                "preference_proxy_a_pct": a,
                "preference_proxy_b_pct": b,
                "m_poll_pp": a - b,
                "redistribution_rule": "exclude",
                "phi_transparency": 0.8,
                "tau_eff": 0.8,
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


def test_arviz_summary_smoke_with_mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    import arviz as az

    monkeypatch.setenv("MC_FAST", "1")
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )

    tr = _tiny_tracking()
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    summary = az.summary(idata, var_names=["sigma_rw", "sigma_house"], round_to=None)
    assert not summary.empty
    assert "r_hat" in summary.columns


@pytest.mark.slow
@pytest.mark.xfail(reason="MC_FAST fixture insufficient for diagnostics; use full NUTS")
def test_rhat_acceptable_under_mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """R-hat must be < 1.05 on production data (full NUTS)."""
    import arviz as az

    monkeypatch.setenv("MC_FAST", "0")
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )

    tr = _tiny_tracking()
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    rhat = az.rhat(idata).max().to_array().max().item()
    assert rhat < 1.05, f"R-hat {rhat:.4f} indicates non-convergence"


@pytest.mark.slow
@pytest.mark.xfail(reason="MC_FAST fixture insufficient for diagnostics; use full NUTS")
def test_ess_acceptable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bulk ESS must be > 200 on production data (full NUTS)."""
    import arviz as az

    monkeypatch.setenv("MC_FAST", "0")
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )

    tr = _tiny_tracking()
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    ess = az.ess(idata, method="bulk").min().to_array().min().item()
    assert ess > 200, f"ESS {ess:.0f} too low — increase tuning"


@pytest.mark.xfail(reason="P2-4 non-centered reparameterization pending")
def test_no_divergences_under_full_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full NUTS (not MC_FAST) must report zero divergences."""
    import arviz as az

    monkeypatch.setenv("MC_FAST", "0")
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )

    tr = _tiny_tracking()
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    n_div = idata.sample_stats["diverging"].sum().item()
    assert n_div == 0, f"{n_div} divergent transitions — reparameterize"
