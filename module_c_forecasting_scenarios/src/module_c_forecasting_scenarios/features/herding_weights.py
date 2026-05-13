"""Herd correlation weights rho_herd in [0, 1] for shock score (modeling hypothesis)."""

from __future__ import annotations

from datetime import date

import pandas as pd


def rho_herd_for_row(publication_date: date, conglomerate_carrier: str | None) -> float:
    """Elevate covariance proxy for late-March clustered releases (ICA + ECODAT pattern)."""
    carrier_missing = conglomerate_carrier is None or (
        isinstance(conglomerate_carrier, float) and pd.isna(conglomerate_carrier)
    )
    carrier = "" if carrier_missing else str(conglomerate_carrier).lower()
    march = date(2018, 3, 15) <= publication_date <= date(2018, 3, 31)
    if march and ("vierci" in carrier or "ica" in carrier):
        return 0.55
    if march:
        return 0.35
    if date(2018, 4, 1) <= publication_date <= date(2018, 4, 15):
        return 0.25
    return 0.05
