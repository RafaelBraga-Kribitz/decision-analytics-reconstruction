"""Exit / quick-count bias layer — separate from tracking likelihood."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pymc as pm

MODEL_VERSION = "c_exit_bias_v0.1"


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
    chains, draws, tune = (2, 200, 200)
    if os.environ.get("MC_FAST"):
        draws, tune = 80, 80
    with pm.Model():
        intercept = pm.Normal("intercept", mu=60.0, sigma=15.0)
        beta_oea = pm.Normal("beta_oea", mu=0.0, sigma=5.0)
        beta_eu = pm.Normal("beta_eu", mu=0.0, sigma=5.0)
        sigma = pm.HalfNormal("sigma", 8.0)
        mu = intercept + beta_oea * oea + beta_eu * eu
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        idata = pm.sample(
            chains=chains,
            draws=draws,
            tune=tune,
            target_accept=0.85,
            random_seed=42,
            progressbar=False,
        )
    post = idata.posterior  # type: ignore[union-attr]
    rows = []
    for v in ("intercept", "beta_oea", "beta_eu", "sigma"):
        s = post[v].stack(sample=("chain", "draw"))
        rows.append(
            {
                "parameter": v,
                "posterior_mean": float(s.mean().values),
                "hdi_low": float(s.quantile(0.05).values),
                "hdi_high": float(s.quantile(0.95).values),
                "calibration_series": calibration_series,
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows), idata
