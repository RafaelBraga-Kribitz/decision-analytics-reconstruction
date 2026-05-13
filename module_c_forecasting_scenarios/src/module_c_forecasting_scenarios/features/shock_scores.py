"""Shock score s from poll margin, transparency, and herd proxy."""

from __future__ import annotations

from datetime import date

import yaml

from module_c_forecasting_scenarios.features.herding_weights import rho_herd_for_row
from module_c_forecasting_scenarios.paths import module_config_dir


def load_shock_params() -> dict[str, object]:
    path = module_config_dir() / "shock_params.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def shock_score_s(
    m_poll_pp: float,
    m_star_pp: float,
    phi: float,
    publication_date: date,
    conglomerate_carrier: str | None,
    params: dict[str, object] | None = None,
) -> float:
    p = params or load_shock_params()
    lam1 = float(p.get("lambda1", 0.08))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    lam2 = float(p.get("lambda2", 0.35))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    lam3 = float(p.get("lambda3", 0.12))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    clip_days = int(p.get("clip_days_before_outcome", 45))  # type: ignore[arg-type]  # dict[str, object] value; runtime is int
    outcome = date.fromisoformat(str(p.get("outcome_event_date", "2018-04-22")))
    if (outcome - publication_date).days > clip_days:
        scale = 1.0
    else:
        scale = max(0.0, (outcome - publication_date).days / max(clip_days, 1))
    rho = rho_herd_for_row(publication_date, conglomerate_carrier)
    s = lam1 * abs(m_poll_pp - m_star_pp) + lam2 * (1.0 - phi) + lam3 * rho
    return float(s * scale)


def scenario_bucket_for_margin(m_poll_pp: float, m_star_pp: float, phi: float, rho: float) -> str:
    extreme = abs(m_poll_pp - m_star_pp) >= 12.0
    opaque = phi < 0.35
    if extreme and opaque and rho > 0.4:
        return "compounded_herd"
    if extreme:
        return "extreme_tracker"
    return "baseline"
