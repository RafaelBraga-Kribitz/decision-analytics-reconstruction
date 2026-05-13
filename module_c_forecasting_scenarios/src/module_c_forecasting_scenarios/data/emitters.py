"""Emit house_effect_seed_matrix and polling_transparency audit tables."""

from __future__ import annotations

import pandas as pd


def build_house_effect_seed_matrix(
    tracking: pd.DataFrame, m_star_pp: float, calibration_series: str
) -> pd.DataFrame:
    rows = []
    for _, r in tracking.iterrows():
        rows.append(
            {
                "poll_wave_id": r["poll_wave_id"],
                "pollster_id": r["pollster_id"],
                "m_poll_pp": float(r["m_poll_pp"]),
                "phi_transparency": float(r["phi_transparency"]),
                "pollster_bias_family": str(r.get("pollster_bias_family", "default")),
                "m_star_pp": m_star_pp,
                "calibration_series": calibration_series,
            }
        )
    return pd.DataFrame(rows)


def build_polling_transparency_audit(tracking: pd.DataFrame) -> pd.DataFrame:
    """One row per (pollster_id, ISO week) with mean phi and ficha share."""
    t = tracking.copy()
    t["publication_date"] = pd.to_datetime(t["publication_date"])
    t["iso_week"] = t["publication_date"].dt.isocalendar().week.astype(int)
    t["iso_year"] = t["publication_date"].dt.isocalendar().year.astype(int)
    t["week_key"] = t["iso_year"].astype(str) + "-W" + t["iso_week"].astype(str).str.zfill(2)
    g = t.groupby(["pollster_id", "week_key"], as_index=False).agg(
        mean_phi_transparency=("phi_transparency", "mean"),
        n_waves=("poll_wave_id", "count"),
        ficha_share=("has_ficha", "mean"),
    )
    g = g.rename(columns={"week_key": "iso_week"})  # type: ignore[call-overload]  # pandas stubs overload mismatch for GroupBy.rename; runtime is correct
    return g
