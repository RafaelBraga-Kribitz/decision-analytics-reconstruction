# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Posterior predictive check plot for the tracking model."""

from __future__ import annotations

from pathlib import Path

import arviz as az
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_ppc_plot(
    idata: az.InferenceData,
    tracking: pd.DataFrame,
    out_path: Path,
) -> Path:
    """Write a PPC fan-chart PNG overlaying posterior predictive vs. observed polls.

    Args:
        idata: InferenceData with ``posterior_predictive`` group (group name ``obs``).
        tracking: Cleaned tracking frame with ``m_poll_pp``, ``publication_date``,
            ``poll_wave_id``.
        out_path: Destination PNG path (parent directories created if needed).

    Returns:
        Resolved path to the written PNG.
    """
    if not hasattr(idata, "posterior_predictive"):
        raise ValueError("idata has no posterior_predictive group — refit with sample_ppc=True")

    ppc_samples = np.asarray(idata.posterior_predictive["obs"].values).reshape(  # type: ignore[union-attr]
        -1, len(tracking)
    )

    sorted_df = tracking.sort_values("publication_date")
    original_idx = sorted_df.index.to_numpy()
    ordered = sorted_df.reset_index(drop=True)
    obs = ordered["m_poll_pp"].to_numpy(dtype=np.float64)
    dates = pd.to_datetime(ordered["publication_date"]).dt.date.tolist()
    x = np.arange(len(ordered))

    fig, ax = plt.subplots(figsize=(9, 5))

    ppc_ordered = ppc_samples[:, original_idx]
    q025 = np.percentile(ppc_ordered, 2.5, axis=0)
    q10 = np.percentile(ppc_ordered, 10.0, axis=0)
    q25 = np.percentile(ppc_ordered, 25.0, axis=0)
    q50 = np.percentile(ppc_ordered, 50.0, axis=0)
    q75 = np.percentile(ppc_ordered, 75.0, axis=0)
    q90 = np.percentile(ppc_ordered, 90.0, axis=0)
    q975 = np.percentile(ppc_ordered, 97.5, axis=0)

    ax.fill_between(x, q025, q975, alpha=0.15, color="#636EFA", label="95% PPC interval")
    ax.fill_between(x, q10, q90, alpha=0.25, color="#636EFA", label="80% PPC interval")
    ax.fill_between(x, q25, q75, alpha=0.40, color="#636EFA", label="50% PPC interval")
    ax.plot(x, q50, color="#636EFA", linewidth=1.5, linestyle="--", label="PPC median")
    ax.scatter(x, obs, color="#EF553B", zorder=5, s=80, label="Observed polls (pp)")

    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in dates], rotation=20, ha="right", fontsize=9)
    ax.set_xlabel("Poll publication date", fontsize=11)
    ax.set_ylabel("Margin (percentage points, A − B)", fontsize=11)
    ax.set_title(
        "Posterior Predictive Check — tracking model vs. observed polls\n"
        "(Series A · Paraguay 2018 reconstruction · n=4 waves)",
        fontsize=12,
    )
    ax.axhline(0, color="#888", linewidth=0.8, linestyle=":")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path.resolve()
