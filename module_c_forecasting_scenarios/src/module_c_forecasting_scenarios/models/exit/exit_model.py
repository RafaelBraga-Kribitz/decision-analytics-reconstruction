"""Exit / quick-count bias layer — separate from tracking likelihood."""

from __future__ import annotations

import os
from typing import Any, cast

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm

from module_c_forecasting_scenarios.config import load_sampler_config

MODEL_VERSION = "c_exit_bias_v0.1"

# Backward-compat alias used by _exit_sampler_kwargs below.
_load_sampler_config = load_sampler_config

# Minimum-width HDI loaded from pymc_sampler.yaml for sync with tracking model.
HDI_PROB = float(load_sampler_config().get("hdi_prob", 0.94))


def _exit_sampler_kwargs() -> dict:
    cfg = _load_sampler_config()
    if os.environ.get("MC_FAST"):
        return {
            "chains": 2,
            "draws": int(cfg["draws_fast"]),
            "tune": int(cfg["tune_fast"]),
            "target_accept": 0.90,
            "random_seed": int(cfg.get("random_seed", 42)),
        }
    return {
        "chains": int(cfg.get("chains", 4)),
        "draws": int(cfg.get("draws", 1000)),
        "tune": int(cfg.get("tune", 1000)),
        "target_accept": float(cfg.get("target_accept", 0.95)),
        "random_seed": int(cfg.get("random_seed", 42)),
        "nuts_sampler_kwargs": {"max_treedepth": int(cfg.get("max_treedepth", 10))},
    }


def fit_exit_quickcount(
    exit_df: pd.DataFrame, *, calibration_series: str
) -> tuple[pd.DataFrame, object | None]:
    """Bayesian normal model for exit margin with OEA/EU timing flags as linear covariates."""
    if exit_df.shape[0] < 2:
        summary = pd.DataFrame(
            [
                {
                    "calibration_series": calibration_series,
                    "model_version": MODEL_VERSION,
                    "note": "insufficient_exit_rows_for_regression",
                    "m_poll_pp_mean": (
                        float(exit_df["m_poll_pp"].mean()) if len(exit_df) else float("nan")
                    ),
                }
            ]
        )
        return summary, None
    y = exit_df["m_poll_pp"].to_numpy(dtype=np.float64)
    oea = exit_df["oea_timing_compliant"].fillna(False).astype(float).to_numpy()
    eu = exit_df["eu_release_window_flag"].fillna(False).astype(float).to_numpy()
    with pm.Model():
        # Weakly-informative prior on the *margin* scale (pp difference, not a
        # percentage level). A legacy mu=60 prior — percentage-level thinking —
        # pulled posterior margins upward on ~30 pp data.
        intercept = pm.Normal("intercept", mu=0.0, sigma=30.0)
        beta_oea = pm.Normal("beta_oea", mu=0.0, sigma=5.0)
        beta_eu = pm.Normal("beta_eu", mu=0.0, sigma=5.0)
        sigma = pm.HalfNormal("sigma", 8.0)
        mu = intercept + beta_oea * oea + beta_eu * eu
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        idata = pm.sample(**_exit_sampler_kwargs(), progressbar=False)
    post = idata.posterior  # type: ignore[union-attr]  # arviz stubs omit InferenceData.posterior; runtime is xarray.Dataset
    rows = []
    for v in ("intercept", "beta_oea", "beta_eu", "sigma"):
        s = post[v].stack(sample=("chain", "draw"))
        # Use minimum-width HDI (same as tracking model) — NOT 5th/95th quantiles.
        # Prior bug: quantile(0.05/0.95) = 90% ETI stored under hdi_* names (F-074).
        # Pass a flat ndarray: az.hdi on an xarray input requires {chain, draw}
        # core dims, which the stack() above collapses into `sample`. The 1-D
        # array form returns array([lower, higher]) and is version-robust.
        _hdi = cast(Any, az.hdi(s.values, hdi_prob=HDI_PROB))
        rows.append(
            {
                "parameter": v,
                "posterior_mean": float(s.mean().values),
                "hdi_low": float(_hdi[0]),
                "hdi_high": float(_hdi[1]),
                "calibration_series": calibration_series,
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows), idata
