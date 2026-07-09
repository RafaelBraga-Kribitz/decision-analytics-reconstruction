#!/usr/bin/env python3
"""Generate the transparency-proxy phi sensitivity artifact (IMP-C02 / audit C4, C6).

`data/transparency.py:compute_phi_transparency`'s constants (`base` for
has_ficha True/False, `step`, `PHI_MIN`, `PHI_MISSING_TWO_OR_MORE`) are a
documented modeling heuristic, not fit against realized poll accuracy. This
script quantifies the exposure two ways:

1. A pure-arithmetic table of `sigma_obs(phi)` at every disclosure-pillar
   count (n_ok in {0,1,2,3}) x has_ficha, under +/-20%/+/-50% perturbation of
   `base`/`step` — no PyMC involved, instant.
2. A posterior-summary comparison: refit the tracking hierarchical model at
   MC_FAST fidelity (seed 42) on the canonical fixture once with the
   production phi values and once with phi recomputed under the +/-50%
   perturbation extremes, and report the delta in the daily posterior mean,
   HDI width, and house-effect scale.

Run: ``MC_FAST=1 poetry run python module_c_forecasting_scenarios/reports/generate_phi_sensitivity.py``
Writes: ``module_c_forecasting_scenarios/reports/phi_sensitivity.md``
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parents[1]
_SRC = _MODULE_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from module_c_forecasting_scenarios.data.cleaning_pipeline import (  # noqa: E402
    _load_m_star,
    clean_raw_polls,
)
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv  # noqa: E402
from module_c_forecasting_scenarios.data.transparency import (  # noqa: E402
    PHI_MAX,
    PHI_MIN,
    PHI_MISSING_TWO_OR_MORE,
)
from module_c_forecasting_scenarios.models.tracking.hierarchical import (  # noqa: E402
    fit_tracking_hierarchical,
    observation_sigma,
)

FIXTURE = _MODULE_ROOT / "tests" / "fixtures" / "polls_raw_fixture.csv"
OUT_MD = Path(__file__).resolve().parent / "phi_sensitivity.md"

# base_no_ficha, base_ficha, step — the constants under test.
BASELINE_CONSTANTS: dict[str, float] = {"base_no_ficha": 0.55, "base_ficha": 0.85, "step": 0.12}
PERTURBATIONS: tuple[float, ...] = (-0.50, -0.20, 0.20, 0.50)


def _phi_formula(n_ok: int, has_ficha: bool, constants: dict[str, float]) -> float:
    """Reimplementation of compute_phi_transparency parameterized by constants.

    Mirrors ``data/transparency.py:compute_phi_transparency`` exactly (same
    special cases at n_ok<=1 and n_ok==0) but takes ``base``/``step`` as
    arguments so they can be perturbed without touching the production
    module's literals (keeping those deterministic, per the module's own
    reproducibility requirement).
    """
    base = constants["base_no_ficha"] if not has_ficha else constants["base_ficha"]
    step = constants["step"]
    phi = base + step * n_ok
    if n_ok <= 1:
        phi = min(phi, PHI_MISSING_TWO_OR_MORE + 0.25)
    if n_ok == 0:
        phi = PHI_MISSING_TWO_OR_MORE
    return float(max(PHI_MIN, min(PHI_MAX, phi)))


def _sigma_obs_table() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for has_ficha in (False, True):
        for n_ok in (0, 1, 2, 3):
            baseline_phi = _phi_formula(n_ok, has_ficha, BASELINE_CONSTANTS)
            baseline_sigma = float(observation_sigma(baseline_phi))
            row: dict[str, object] = {
                "has_ficha": has_ficha,
                "n_ok": n_ok,
                "phi_baseline": baseline_phi,
                "sigma_obs_baseline": baseline_sigma,
            }
            for pct in PERTURBATIONS:
                perturbed_constants = {k: v * (1.0 + pct) for k, v in BASELINE_CONSTANTS.items()}
                phi_p = _phi_formula(n_ok, has_ficha, perturbed_constants)
                sigma_p = float(observation_sigma(phi_p))
                row[f"sigma_obs_{pct:+.0%}"] = sigma_p
                row[f"sigma_obs_delta_{pct:+.0%}"] = sigma_p - baseline_sigma
            rows.append(row)
    return rows


def _raw_pillar_lookup(raw: pd.DataFrame) -> dict[str, tuple[bool, bool, bool, bool]]:
    """poll_wave_id -> (has_ficha, sample_size_known, field_window_known, mode_known)."""
    lookup: dict[str, tuple[bool, bool, bool, bool]] = {}
    for _, r in raw.iterrows():
        wave_id = str(r["poll_raw_id"]).replace("raw_", "wave_")
        lookup[wave_id] = (
            bool(r["has_ficha"]),
            bool(r.get("sample_size_known", False)),
            bool(r.get("field_window_known", False)),
            bool(r.get("mode_known", False)),
        )
    return lookup


def _phi_column_under_constants(
    tracking: pd.DataFrame, pillar_lookup: dict[str, tuple[bool, bool, bool, bool]], constants: dict[str, float]
) -> np.ndarray:
    """Recompute phi_transparency for every tracking row under ``constants``.

    Reproduces cleaning_pipeline.py's exact call-site behavior, including its
    ``field_window_known or True`` pass-through (field_window_known is
    effectively always treated as satisfied at the call site today — an
    existing cleaning-pipeline quirk, out of IMP-C02's scope to change, but
    reproduced here so the sensitivity comparison matches production phi
    exactly at the +/-0% baseline).
    """
    out = np.zeros(len(tracking), dtype=np.float64)
    for i, wave_id in enumerate(tracking["poll_wave_id"]):
        has_ficha, sample_size_known, _field_window_known, mode_known = pillar_lookup[str(wave_id)]
        n_ok = sum([sample_size_known, True, mode_known])  # field_window_known or True
        out[i] = _phi_formula(n_ok, has_ficha, constants)
    return out


def _posterior_summary(idata) -> dict[str, float]:  # type: ignore[no-untyped-def]
    post = idata.posterior["mu_margin"]
    mean_m = np.asarray(post.mean(dim=("chain", "draw")).values).reshape(-1)
    house_scale = float(
        np.asarray(idata.posterior["sigma_house"].mean(dim=("chain", "draw")).values)
    )
    return {
        "last_day_posterior_mean_pp": float(mean_m[-1]),
        "posterior_mean_spread_pp": float(mean_m.max() - mean_m.min()),
        "house_effect_scale_pp": house_scale,
    }


def _posterior_delta_under_perturbation() -> list[dict[str, object]]:
    """Refit at MC_FAST fidelity with baseline vs perturbed phi; report deltas."""
    os.environ["MC_FAST"] = "1"
    raw = load_raw_polls_csv(FIXTURE)
    tracking, _exit = clean_raw_polls(raw, "A")
    pillar_lookup = _raw_pillar_lookup(raw)
    m_star = _load_m_star("A")
    outcome = date(2018, 4, 22)

    baseline_idata = fit_tracking_hierarchical(
        tracking, outcome_event_date=outcome, calibration_series="A", m_star_pp=m_star
    )
    baseline_summary = _posterior_summary(baseline_idata)

    rows: list[dict[str, object]] = []
    for pct in (-0.50, 0.50):
        perturbed_constants = {k: v * (1.0 + pct) for k, v in BASELINE_CONSTANTS.items()}
        perturbed_tracking = tracking.copy()
        perturbed_tracking["phi_transparency"] = _phi_column_under_constants(
            tracking, pillar_lookup, perturbed_constants
        )
        perturbed_idata = fit_tracking_hierarchical(
            perturbed_tracking, outcome_event_date=outcome, calibration_series="A", m_star_pp=m_star
        )
        perturbed_summary = _posterior_summary(perturbed_idata)
        row: dict[str, object] = {"pct_perturbation": pct}
        for key, baseline_value in baseline_summary.items():
            row[f"{key}_baseline"] = baseline_value
            row[f"{key}_perturbed"] = perturbed_summary[key]
            row[f"{key}_delta"] = perturbed_summary[key] - baseline_value
        rows.append(row)
    return rows


def _render_markdown(sigma_rows: list[dict[str, object]], posterior_rows: list[dict[str, object]]) -> str:
    lines: list[str] = []
    lines.append("# Transparency proxy phi sensitivity (IMP-C02 / audit C4, C6)")
    lines.append("")
    lines.append(
        "Generated by `module_c_forecasting_scenarios/reports/generate_phi_sensitivity.py`. "
        "`compute_phi_transparency`'s constants (`base_no_ficha=0.55`, `base_ficha=0.85`, "
        "`step=0.12`) are a documented modeling heuristic, not fit against realized poll "
        "accuracy — this artifact bounds the exposure that heuristic status carries."
    )
    lines.append("")
    lines.append("## sigma_obs(phi) at every disclosure-pillar count (pure arithmetic, no MCMC)")
    lines.append("")
    header = (
        "| has_ficha | n_ok | phi (baseline) | sigma_obs (baseline, pp) | "
        "sigma_obs @ -50% | sigma_obs @ -20% | sigma_obs @ +20% | sigma_obs @ +50% |"
    )
    lines.append(header)
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in sigma_rows:
        lines.append(
            f"| {row['has_ficha']} | {row['n_ok']} | {row['phi_baseline']:.3f} | "
            f"{row['sigma_obs_baseline']:.2f} | {row['sigma_obs_-50%']:.2f} | "
            f"{row['sigma_obs_-20%']:.2f} | {row['sigma_obs_+20%']:.2f} | "
            f"{row['sigma_obs_+50%']:.2f} |"
        )
    lines.append("")
    lines.append(
        "## Posterior-summary delta under +/-50% perturbation (MC_FAST fidelity, seed 42, canonical fixture)"
    )
    lines.append("")
    lines.append(
        "| perturbation | last-day posterior mean (baseline, pp) | last-day posterior mean (perturbed, pp) | "
        "delta (pp) | posterior mean spread delta (pp) | house-effect scale delta (pp) |"
    )
    lines.append("|---|---|---|---|---|---|")
    for row in posterior_rows:
        lines.append(
            f"| {row['pct_perturbation']:+.0%} | "
            f"{row['last_day_posterior_mean_pp_baseline']:.3f} | "
            f"{row['last_day_posterior_mean_pp_perturbed']:.3f} | "
            f"{row['last_day_posterior_mean_pp_delta']:.3f} | "
            f"{row['posterior_mean_spread_pp_delta']:.3f} | "
            f"{row['house_effect_scale_pp_delta']:.3f} |"
        )
    lines.append("")
    lines.append(
        "**Reading this table:** the delta columns are the numeric bound IMP-C02 requires — "
        "how much the *published* posterior summary moves when the uncalibrated phi heuristic "
        "is perturbed by a plausible +/-50%, holding everything else (data, sampler, seed) fixed. "
        "A small delta here means the reported forecast is not sensitive to this particular "
        "heuristic's exact constants; a large delta means the heuristic materially drives the "
        "headline number and its uncalibrated status is a live risk, not a formality."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    sigma_rows = _sigma_obs_table()
    posterior_rows = _posterior_delta_under_perturbation()
    OUT_MD.write_text(_render_markdown(sigma_rows, posterior_rows), encoding="utf-8")
    print(f"[PASS] wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
