# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Leave-one-wave-out (LOWO) validation for the hierarchical tracking model.

For each of the ``n`` real tracking waves, the tracking model is refit on the
other ``n - 1`` waves and the held-out wave's observed margin is scored against
the model's **posterior predictive** for that wave's field-window midpoint —
``mu_margin[day] + house_offset[pollster] + Normal(0, sigma_obs(phi))``, the same
generative mean and noise the likelihood assigns to a poll observation (shared
with :mod:`walk_forward` via :func:`holdout_predictive_samples`).

Unlike walk-forward — which uses an *expanding* chronological window and so scores
only the later waves — LOWO holds out **every** wave in turn, yielding one
out-of-sample score per wave (``k = n`` folds). On the Paraguay 2018 fixture that
is the eight real tracking waves, so LOWO produces the repository's first genuinely
out-of-sample number on withheld real poll data.

Reported metrics:

* **Predictive log-score** — the Gaussian log predictive density
  ``log N(y_obs | mean, sd)`` where ``mean``/``sd`` are the mean and standard
  deviation of the held-out wave's posterior-predictive draws. Higher is better;
  it is reported per wave and averaged. This is a proper scoring rule for the
  continuous margin (a Gaussian approximation to the predictive density, disclosed
  as such — the predictive samples are close to Gaussian by construction of the
  additive noise model).
* **94% interval coverage** — fraction of held-out margins whose observed value
  falls inside the 94% highest-density interval of the posterior predictive.

**Honesty guarantee.** Every fit is unanchored (``m_star_pp=None``): the verified
TSJE election margin (+3.70 pp Series A) never enters a fit whose wave is being
scored. The model variant scored is therefore
``c_tracking_hierarchical_v0.4`` (unanchored likelihood path). See F-069.

**n = 8 caveat.** Eight waves of a single election is a small sample; LOWO
quantifies out-of-sample predictive performance on this fixture, it is not
"validated forecasting skill." Intervals are structurally wide and the aggregate
log-score / coverage carry the sampling noise of eight folds. The same routine
scales to denser polling without modification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    HDI_PROB,
    MODEL_VERSION,
)
from module_c_forecasting_scenarios.validation.walk_forward import (
    _hdi_bounds,  # pyright: ignore[reportPrivateUsage]
    holdout_predictive_samples,
)

# The scored variant is the unanchored tracking model — the m★ outcome anchor is
# never passed to a LOWO fit (holdout_predictive_samples forces m_star_pp=None).
MODEL_VARIANT = f"{MODEL_VERSION} (unanchored; m_star_pp=None)"
_EPS = 1e-6


@dataclass(frozen=True)
class LeaveOneWaveOutResult:
    """Per-wave predictions plus aggregate LOWO metrics.

    Attributes:
        per_wave: One row per held-out wave with ``poll_wave_id``,
            ``publication_date``, ``n_train``, ``observed_margin_pp``,
            ``predictive_mean_pp``, ``predictive_sd_pp``, ``hdi94_low_pp``,
            ``hdi94_high_pp``, ``log_score``, ``covered_94pct``, plus per-fit
            sampler diagnostics ``rhat_max``, ``ess_bulk_min``, ``n_divergences``.
        metrics: Dict with ``mean_log_score``, ``coverage_94pct``,
            ``n_covered``, ``n_waves``, ``hdi_prob``.
        calibration_series: Series tag forwarded from input.
        model_variant: The scored model variant string (unanchored).
    """

    per_wave: pd.DataFrame
    metrics: dict[str, float] = field(default_factory=dict)
    calibration_series: str = "A"
    model_variant: str = MODEL_VARIANT


def _gaussian_log_score(samples: np.ndarray, observed: float) -> float:
    """Gaussian log predictive density of ``observed`` under the predictive draws.

    ``log N(observed | mean, sd)`` with ``mean``/``sd`` the sample moments of the
    posterior-predictive draws. ``sd`` is floored at ``_EPS`` so a degenerate
    predictive does not produce ``-inf`` / ``nan``.
    """
    mean = float(samples.mean())
    sd = max(float(samples.std(ddof=1)), _EPS)
    var = sd * sd
    return float(-0.5 * math.log(2.0 * math.pi * var) - (observed - mean) ** 2 / (2.0 * var))


def leave_one_wave_out_validation(
    tracking: pd.DataFrame,
    *,
    outcome_event_date: date,
    calibration_series: str,
    hdi_prob: float = HDI_PROB,
    sampler_overrides: dict[str, object] | None = None,
) -> LeaveOneWaveOutResult:
    """Refit the hierarchical tracking model leave-one-wave-out over all waves.

    Args:
        tracking: Cleaned tracking poll frame (output of ``clean_raw_polls``).
            Must include ``publication_date``, ``field_window_*``, ``m_poll_pp``,
            ``poll_wave_id``, ``pollster_id``, ``phi_transparency``.
        outcome_event_date: Election day (April 22, 2018 for Paraguay); the day
            grid ends on its eve. Used only to place the latent-day index — the
            verified margin is never used as an anchor here.
        calibration_series: ``"A"`` or ``"B"`` calibration identifier.
        hdi_prob: Coverage interval probability (default 0.94, matching the model's
            reported HDI).
        sampler_overrides: Optional explicit ``pm.sample`` kwarg overrides (e.g.
            ``{"chains": 4, "draws": 300, "tune": 300}``) forwarded to every
            fold's fit. Must be disclosed in any artifact built from the result.

    Returns:
        LeaveOneWaveOutResult with per-wave predictions and aggregate log-score /
        coverage metrics.

    Raises:
        ValueError: If ``tracking`` has fewer than 3 waves (a 2-wave training fold
            is the practical floor for the random-walk likelihood).

    Example:
        ``leave_one_wave_out_validation(tracking, outcome_event_date=date(2018,4,22),
        calibration_series="A")`` returns a result with 8 folds for the Paraguay
        2018 fixture (8 tracking waves).
    """
    if len(tracking) < 3:
        raise ValueError(
            f"leave-one-wave-out needs at least 3 waves (2-wave training fold floor); "
            f"got {len(tracking)}"
        )

    ordered = tracking.sort_values("publication_date").reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for i in range(len(ordered)):
        holdout = ordered.iloc[i]
        train = ordered.drop(index=ordered.index[i]).copy()
        obs = float(holdout["m_poll_pp"])
        diag: dict[str, float] = {}
        samples = holdout_predictive_samples(
            train,
            holdout,
            outcome_event_date=outcome_event_date,
            calibration_series=calibration_series,
            sampler_overrides=sampler_overrides,
            diagnostics=diag,
        )
        low, high = _hdi_bounds(samples, hdi_prob=hdi_prob)
        covered = bool(low <= obs <= high)
        rows.append(
            {
                "fold": i + 1,
                "poll_wave_id": str(holdout["poll_wave_id"]),
                "publication_date": pd.Timestamp(holdout["publication_date"]).date(),
                "n_train": int(len(train)),
                "observed_margin_pp": obs,
                "predictive_mean_pp": float(samples.mean()),
                "predictive_sd_pp": float(samples.std(ddof=1)),
                "hdi94_low_pp": low,
                "hdi94_high_pp": high,
                "log_score": _gaussian_log_score(samples, obs),
                "covered_94pct": covered,
                "rhat_max": diag.get("rhat_max", float("nan")),
                "ess_bulk_min": diag.get("ess_bulk_min", float("nan")),
                "n_divergences": diag.get("n_divergences", float("nan")),
            }
        )

    per_wave = pd.DataFrame(rows)
    metrics = summarize_lowo(per_wave, hdi_prob=hdi_prob)
    return LeaveOneWaveOutResult(
        per_wave=per_wave,
        metrics=metrics,
        calibration_series=calibration_series,
        model_variant=MODEL_VARIANT,
    )


def summarize_lowo(per_wave: pd.DataFrame, *, hdi_prob: float = HDI_PROB) -> dict[str, float]:
    """Aggregate mean log-score and interval coverage from per-wave predictions.

    Args:
        per_wave: DataFrame produced by :func:`leave_one_wave_out_validation`.
        hdi_prob: Coverage interval probability recorded in the summary.

    Returns:
        Dict with ``mean_log_score``, ``coverage_94pct``, ``n_covered``,
        ``n_waves``, ``hdi_prob``.

    Raises:
        KeyError: If required columns are absent from ``per_wave``.

    Example:
        ``summarize_lowo(result.per_wave)`` returns the same dict attached to
        ``result.metrics``.
    """
    if per_wave.empty:
        return {
            "mean_log_score": float("nan"),
            "coverage_94pct": float("nan"),
            "n_covered": 0.0,
            "n_waves": 0.0,
            "hdi_prob": float(hdi_prob),
        }
    n_covered = int(per_wave["covered_94pct"].sum())
    n_waves = int(len(per_wave))
    return {
        "mean_log_score": float(per_wave["log_score"].mean()),
        "coverage_94pct": float(n_covered / n_waves),
        "n_covered": float(n_covered),
        "n_waves": float(n_waves),
        "hdi_prob": float(hdi_prob),
    }
