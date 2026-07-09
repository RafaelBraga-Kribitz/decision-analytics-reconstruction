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


# NOTE ON MC_FAST: setting ``MC_FAST=0`` does NOT select full NUTS — the model
# reads ``if os.environ.get("MC_FAST")`` and the string "0" is truthy, so it would
# pick the fast (50-draw) path. To exercise the full sampler these tests DELETE the
# variable. The disclosure script (scripts/check_mcmc_diagnostics_disclosure.py,
# finding F-042) now verifies these gates are enforced rather than xfail'd.
def test_rhat_acceptable_under_full_nuts(monkeypatch: pytest.MonkeyPatch) -> None:
    """R-hat must be <= 1.01 for every parameter on the 8-wave fixture (full NUTS)."""
    import arviz as az

    monkeypatch.delenv("MC_FAST", raising=False)
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
    assert rhat <= 1.01, f"R-hat {rhat:.4f} indicates non-convergence"


def test_ess_acceptable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bulk and tail ESS must both be >= 400 on the 8-wave fixture (full NUTS)."""
    import arviz as az

    monkeypatch.delenv("MC_FAST", raising=False)
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )

    tr = _tiny_tracking()
    idata = fit_tracking_hierarchical(
        tr,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    ess_bulk = az.ess(idata, method="bulk").min().to_array().min().item()
    ess_tail = az.ess(idata, method="tail").min().to_array().min().item()
    assert ess_bulk >= 400, f"bulk ESS {ess_bulk:.0f} too low — increase tuning"
    assert ess_tail >= 400, f"tail ESS {ess_tail:.0f} too low — increase tuning"


def test_no_divergences_under_full_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full NUTS (not MC_FAST) must report zero divergences."""

    monkeypatch.delenv("MC_FAST", raising=False)
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


def test_posterior_stability_across_independent_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two independent full-NUTS fits on identical (seed-42) input must agree.

    The non-centered model is fully seeded (``random_seed=42`` in
    ``config/pymc_sampler.yaml``), so two fresh fits of the same fixture must
    reproduce the daily posterior. We assert per-day agreement within 0.05 pp on
    the posterior mean and 0.10 pp on each 94% HDI bound — a tolerance that would
    fail loudly if the reparameterization reintroduced sampler nondeterminism.
    """
    monkeypatch.delenv("MC_FAST", raising=False)
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        _build_day_index,
        export_daily_posterior_table,
        fit_tracking_hierarchical,
    )

    tr = _tiny_tracking()
    outcome = date(2018, 4, 22)
    days, _ = _build_day_index(tr, outcome)

    def _fit_table() -> pd.DataFrame:
        idata = fit_tracking_hierarchical(tr, outcome_event_date=outcome, calibration_series="A")
        return export_daily_posterior_table(idata, days, "A")

    a = _fit_table()
    b = _fit_table()

    assert list(a["date"]) == list(b["date"])
    mean_gap = (
        a["posterior_mean_preference_margin_pp"] - b["posterior_mean_preference_margin_pp"]
    ).abs()
    low_gap = (a["posterior_hdi_low_pp"] - b["posterior_hdi_low_pp"]).abs()
    high_gap = (a["posterior_hdi_high_pp"] - b["posterior_hdi_high_pp"]).abs()

    assert mean_gap.max() <= 0.05, f"posterior mean drift {mean_gap.max():.4f} pp > 0.05"
    assert low_gap.max() <= 0.10, f"HDI-low drift {low_gap.max():.4f} pp > 0.10"
    assert high_gap.max() <= 0.10, f"HDI-high drift {high_gap.max():.4f} pp > 0.10"
