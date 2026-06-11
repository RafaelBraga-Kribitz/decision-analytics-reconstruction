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
from typing import Final

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


def department_media_profile(seg_dept: pd.DataFrame) -> pd.DataFrame:
    """Reduce segment×department rows to one measured profile row per department.

    All means are weighted by ``segment_size``; empty (size-0) cells are
    excluded so dense-grid NaN placeholders never poison the averages.

    Args:
        seg_dept: Frame from :func:`load_segment_department_reachability`.

    Returns:
        DataFrame indexed by ``department`` with columns ``tv_penetration``,
        ``radio_penetration``, ``whatsapp_penetration``, ``internet_access``,
        ``mean_participation_propensity`` — all in [0, 1].

    Raises:
        ValueError: If no department has any populated segment cell.

    Example:
        ``department_media_profile(seg_df).loc["Central", "tv_penetration"]``.
    """
    populated = seg_dept[seg_dept["segment_size"] > 0]
    if populated.empty:
        raise ValueError("Module A reachability artifact has no populated segment cells")

    def _weighted(group: pd.DataFrame) -> pd.Series:
        w = group["segment_size"].to_numpy(dtype=float)
        return pd.Series(
            {
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
        )

    profile = populated.groupby("department")[list(_REQUIRED_COLUMNS)].apply(_weighted)
    return profile.clip(lower=0.0, upper=1.0)
