"""Module A → Module B ingestion bridge.

Reads Module A's exported ``media_reachability_by_segment_department.csv``
(contract: ``schema_contracts/media_reachability_by_segment_department.yaml``)
and reduces it to the department-level quantities Module B's allocator
consumes:

* **Measured channel penetration** — segment-size-weighted means of TV /
  radio / WhatsApp penetration and internet access per department. These
  replace the corresponding YAML reach-cap priors in
  :func:`~module_b_resource_allocation.models.feature_join.build_allocation_features`
  (provenance ``MODULE_A``).
* **Participation propensity weight** — the segment-size-weighted mean
  participation propensity per department, used as a persuasion weight in
  the MILP objective (contacts in high-propensity departments count more).

The bridge degrades gracefully: if the artifact is absent (fresh clone
before ``dvc repro module_a``), Module B falls back to its YAML priors and a
uniform propensity weight, and the feature frame says so via ``provenance``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: Default location of the Module A export (DVC stage ``module_a``).
DEFAULT_REACHABILITY_CSV: Final[Path] = (
    _REPO_ROOT / "data" / "processed" / "media_reachability_by_segment_department.csv"
)

#: Module B channel → Module A measured penetration column family.
#: Channels absent here (sms, billboards, ground channels) keep YAML priors:
#: Module A does not measure them.
CHANNEL_PENETRATION_SOURCE: Final[dict[str, str]] = {
    "tv_spots": "tv_penetration",
    "radio_spots": "radio_penetration",
    "whatsapp_chatbot": "whatsapp_penetration",
    "messenger_chatbot": "whatsapp_penetration",
    "facebook_ads": "internet_access",
    "email": "internet_access",
}

_REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "segment_label",
    "department",
    "segment_size",
    "mean_participation_propensity",
    "pct_internet_access",
    "mean_tv_penetration",
    "mean_radio_penetration",
    "mean_whatsapp_penetration",
)


def load_segment_department_reachability(path: Path | None = None) -> pd.DataFrame | None:
    """Load Module A's segment×department reachability artifact, if present.

    Args:
        path: Optional explicit artifact path; defaults to
            :data:`DEFAULT_REACHABILITY_CSV`.

    Returns:
        Validated DataFrame, or ``None`` when the artifact does not exist
        (callers fall back to YAML priors).

    Raises:
        ValueError: If the artifact exists but is missing required columns.

    Example:
        ``load_segment_department_reachability()`` inside
        ``build_allocation_features``.
    """
    target = path if path is not None else DEFAULT_REACHABILITY_CSV
    if not target.exists():
        logger.warning(
            "Module A reachability artifact missing at %s — Module B will use YAML priors",
            target,
        )
        return None
    df = pd.read_csv(target)
    missing = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Module A reachability artifact {target} is missing columns {missing}; "
            "regenerate it with `dvc repro module_a`."
        )
    return df


#: z multiplier for the propagated ~95% propensity interval.
_CI_Z: Final[float] = 1.959963984540054

#: Column flagging whether the loaded artifact carried uncertainty columns.
UNCERTAINTY_FLAG: Final[str] = "uncertainty_available"


def validate_department_profile(profile: pd.DataFrame) -> None:
    """Abort on a degenerate/inverted propensity interval (IMP-B02 NFR).

    Args:
        profile: Output of :func:`department_media_profile`.

    Returns:
        None.

    Raises:
        ValueError: If any department's interval fails
            ``propensity_ci_low <= mean_participation_propensity <=
            propensity_ci_high`` (NaN intervals — the degraded no-uncertainty
            path — are exempt; they are flagged, not bounded).

    Example:
        Called by :func:`department_media_profile` before returning.
    """
    if "propensity_ci_low" not in profile.columns:
        return
    has_ci = profile["propensity_ci_low"].notna() & profile["propensity_ci_high"].notna()
    sub = cast(pd.DataFrame, profile[has_ci])
    bad = cast(
        pd.DataFrame,
        sub[
            (sub["propensity_ci_low"] > sub["mean_participation_propensity"])
            | (sub["mean_participation_propensity"] > sub["propensity_ci_high"])
        ],
    )
    if not bad.empty:
        raise ValueError(
            "inverted propensity interval (ci_low <= mean <= ci_high violated) for "
            f"department(s): {sorted(bad.index.tolist())} — contract violation, not a warning"
        )


def department_media_profile(seg_dept: pd.DataFrame) -> pd.DataFrame:
    """Reduce segment×department rows to one measured profile row per department.

    All means are weighted by ``segment_size``; empty (size-0) cells are
    excluded so dense-grid NaN placeholders never poison the averages.

    Uncertainty propagation (IMP-B02 / issue #58): when the artifact carries
    ``participation_propensity_se`` (handshake contract v1.1.0), the
    department standard error is propagated from the segment-cell SEs under
    the weighted mean — ``se_dept = sqrt(sum(w_i^2 se_i^2)) / sum(w_i)`` —
    and returned as a ~95% interval (``propensity_ci_low``/``_high``,
    clipped to [0, 1]). Cells with undefined SE (n<=1) contribute zero to the
    propagation. When the artifact predates the contract change,
    ``uncertainty_available`` is False and the interval columns are NaN — the
    consumer must flag degraded confidence, never treat missing uncertainty
    as zero uncertainty.

    Args:
        seg_dept: Frame from :func:`load_segment_department_reachability`.

    Returns:
        DataFrame indexed by ``department`` with columns ``tv_penetration``,
        ``radio_penetration``, ``whatsapp_penetration``, ``internet_access``,
        ``mean_participation_propensity`` (all in [0, 1]), plus
        ``propensity_ci_low``, ``propensity_ci_high`` and the boolean
        ``uncertainty_available``.

    Raises:
        ValueError: If no department has any populated segment cell, or a
            propagated interval is inverted.

    Example:
        ``department_media_profile(seg_df).loc["Central", "tv_penetration"]``.
    """
    populated = seg_dept[seg_dept["segment_size"] > 0]
    if populated.empty:
        raise ValueError("Module A reachability artifact has no populated segment cells")

    has_uncertainty = "participation_propensity_se" in populated.columns

    def _weighted(group: pd.DataFrame) -> pd.Series:
        w = group["segment_size"].to_numpy(dtype=float)
        row = {
            "tv_penetration": float(np.average(group["mean_tv_penetration"], weights=w)),
            "radio_penetration": float(np.average(group["mean_radio_penetration"], weights=w)),
            "whatsapp_penetration": float(
                np.average(group["mean_whatsapp_penetration"], weights=w)
            ),
            "internet_access": float(np.average(group["pct_internet_access"], weights=w)),
            "mean_participation_propensity": float(
                np.average(group["mean_participation_propensity"], weights=w)
            ),
        }
        if has_uncertainty:
            se = group["participation_propensity_se"].to_numpy(dtype=float)
            se = np.nan_to_num(se, nan=0.0)  # n<=1 cells: undefined SE contributes zero
            se_dept = float(np.sqrt(np.sum((w * se) ** 2)) / max(1e-9, float(w.sum())))
            mean = row["mean_participation_propensity"]
            row["propensity_ci_low"] = max(0.0, mean - _CI_Z * se_dept)
            row["propensity_ci_high"] = min(1.0, mean + _CI_Z * se_dept)
        else:
            row["propensity_ci_low"] = float("nan")
            row["propensity_ci_high"] = float("nan")
        return pd.Series(row)

    cols = [c for c in populated.columns if c != "department"]
    profile = populated.groupby("department")[cols].apply(_weighted)
    value_cols = [
        "tv_penetration",
        "radio_penetration",
        "whatsapp_penetration",
        "internet_access",
        "mean_participation_propensity",
    ]
    profile[value_cols] = cast(pd.DataFrame, profile[value_cols]).clip(lower=0.0, upper=1.0)
    profile[UNCERTAINTY_FLAG] = has_uncertainty
    validate_department_profile(cast(pd.DataFrame, profile))
    return cast(pd.DataFrame, profile)
