"""Join atomic Module B feature frames into the LP-friendly allocation table.

This is the bridge between Phase 6's atomic feature builders
(``features/reach_caps.py``, ``features/district_tiers.py``,
``features/diminishing_returns.py``) and the Phase 7 LP/MILP
allocation model — the latter needs a single denormalized 198-row frame
(``department × channel``) carrying every coefficient the solver references.

Schema produced (must round-trip into ``schema_contracts/reachability_caps_dept_channel.yaml``):

* ``department``, ``channel``, ``region``, ``channel_type``,
  ``department_tier``, ``tier_eligibility``
* ``reach_cap_share``, ``reachable_audience``
* ``salience_multiplier``, ``attention_multiplier``, ``network_hostility``
* ``unit_cost_pyg``, ``fx_tier_default``
* ``diminishing_returns_k``, ``diminishing_returns_inflection_pct``
* ``dept_mean_propensity`` (Module A participation propensity weight)
* ``provenance``

When Module A's ``media_reachability_by_segment_department.csv`` artifact is
present, measured channel penetration replaces the YAML reach-cap priors for
TV / radio / WhatsApp / internet channels (provenance ``MODULE_A``) and the
department participation propensity feeds the MILP persuasion weight. Without
the artifact, the frame falls back to YAML priors and a uniform weight.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd
import yaml

from module_b_resource_allocation.constants import CHANNEL_TYPES
from module_b_resource_allocation.features.diminishing_returns import build_dr_params
from module_b_resource_allocation.features.district_tiers import build_district_tiers
from module_b_resource_allocation.features.module_a_ingestion import (
    CHANNEL_PENETRATION_SOURCE,
    UNCERTAINTY_FLAG,
    department_media_profile,
    load_segment_department_reachability,
)
from module_b_resource_allocation.features.reach_caps import build_reach_caps

logger = logging.getLogger(__name__)

_CONFIG_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "config"


_TIER_ELIGIBILITY: Final[dict[str, str]] = {
    "whatsapp_chatbot": "mobile_first",
    "messenger_chatbot": "mobile_first",
    "facebook_ads": "mobile_first",
    "sms": "mobile_first",
    "email": "mobile_first",
    "tv_spots": "mass",
    "radio_spots": "mass",
    "billboards": "mass",
    "rallies_events": "in_person_only",
    "canvassing": "in_person_only",
    "sound_cars": "in_person_only",
}


def _load_yaml(name: str) -> dict:
    with open(_CONFIG_DIR / name) as f:
        return yaml.safe_load(f)


def _channel_unit_costs_pyg() -> dict[str, tuple[float, str]]:
    cfg = _load_yaml("channel_unit_costs_pyg.yaml")["channels"]
    return {ch: (float(spec["unit_cost_pyg"]), spec["fx_tier_default"]) for ch, spec in cfg.items()}


def _department_population() -> dict[str, int]:
    pop = _load_yaml("department_population_prior.yaml")["population"]
    return {k: int(v) for k, v in pop.items()}


def build_allocation_features(
    *,
    module_a_reachability: Path | None = None,
    use_module_a: bool = True,
) -> pd.DataFrame:
    """Return the denormalized LP-facing ``(department, channel)`` feature frame.

    Args:
        module_a_reachability: Optional explicit path to Module A's
            ``media_reachability_by_segment_department.csv`` export; defaults
            to the canonical ``data/processed`` location.
        use_module_a: When ``True`` (default), measured Module A penetration
            replaces YAML reach-cap priors for the channels Module A measures
            and the department propensity weight is populated. When ``False``
            (or the artifact is absent), pure YAML priors are used.

    Returns:
        DataFrame joining reach caps, district tiers, diminishing-return
        knobs, and (when available) Module A measured reachability/propensity.

    Raises:
        OSError: If required YAML configuration files cannot be read.
        KeyError: If upstream builders omit expected join keys.
        ValueError: If the Module A artifact exists but is malformed.

    Example:
        ``build_allocation_features()`` feeds :func:`build_problem` when reach caps are omitted.
    """
    caps = build_reach_caps().copy()
    tiers = build_district_tiers().rename(columns={"provenance": "tier_provenance"})
    dr = build_dr_params().rename(
        columns={
            "k_shape": "diminishing_returns_k",
            "inflection_pct": "diminishing_returns_inflection_pct",
        }
    )[
        [
            "department",
            "channel",
            "diminishing_returns_k",
            "diminishing_returns_inflection_pct",
        ]
    ]

    df = caps.merge(
        tiers[["department", "department_tier"]],
        on="department",
        how="left",
    )
    df = df.merge(dr, on=["department", "channel"], how="left")

    unit_costs = _channel_unit_costs_pyg()
    population = _department_population()

    df["channel_type"] = df["channel"].map(lambda c: CHANNEL_TYPES[str(c)])
    df["tier_eligibility"] = df["channel"].map(lambda c: _TIER_ELIGIBILITY[str(c)])
    df["unit_cost_pyg"] = df["channel"].map(lambda c: unit_costs[c][0])
    df["fx_tier_default"] = df["channel"].map(lambda c: unit_costs[c][1])

    # Module A ingestion: measured penetration overrides YAML priors for the
    # channels Module A measures; department propensity becomes the MILP
    # persuasion weight. Falls back gracefully when the artifact is absent.
    profile: pd.DataFrame | None = None
    if use_module_a:
        seg_dept = load_segment_department_reachability(module_a_reachability)
        if seg_dept is not None:
            profile = department_media_profile(seg_dept)

    if profile is not None:
        dept_series = cast(pd.Series, df["department"])
        for channel, source_col in CHANNEL_PENETRATION_SOURCE.items():
            penetration_by_dept = cast(pd.Series, profile[source_col]).to_dict()
            measured = dept_series.map(penetration_by_dept)
            replace = (df["channel"] == channel) & measured.notna()
            df.loc[replace, "reach_cap_share"] = measured[replace]
            df.loc[replace, "provenance"] = "MODULE_A"
        propensity_by_dept = cast(pd.Series, profile["mean_participation_propensity"]).to_dict()
        mapped = dept_series.map(propensity_by_dept)
        # Disclosed fallback (IMP-B02 / issue #58): departments Module A did
        # not cover keep the neutral 1.0 weight, but the substitution is now
        # recorded per row and counted — never silent. Rows sourced from an
        # artifact predating the v1.1.0 uncertainty columns are flagged
        # MODULE_A_NO_UNCERTAINTY, never unqualified MODULE_A.
        df["dept_mean_propensity"] = mapped.fillna(1.0)
        uncertainty_ok = bool(profile[UNCERTAINTY_FLAG].iloc[0])
        measured_source = "MODULE_A" if uncertainty_ok else "MODULE_A_NO_UNCERTAINTY"
        df["dept_mean_propensity_source"] = np.where(
            mapped.notna(), measured_source, "NEUTRAL_FALLBACK"
        )
        df["dept_propensity_ci_low"] = dept_series.map(
            cast(pd.Series, profile["propensity_ci_low"]).to_dict()
        )
        df["dept_propensity_ci_high"] = dept_series.map(
            cast(pd.Series, profile["propensity_ci_high"]).to_dict()
        )
        n_fallback = int((df["dept_mean_propensity_source"] == "NEUTRAL_FALLBACK").sum())
        if n_fallback:
            logger.warning(
                "dept_mean_propensity NEUTRAL_FALLBACK applied to %d row(s) — "
                "departments missing from the Module A profile",
                n_fallback,
            )
    else:
        df["dept_mean_propensity"] = 1.0
        df["dept_mean_propensity_source"] = "NEUTRAL_FALLBACK"
        df["dept_propensity_ci_low"] = np.nan
        df["dept_propensity_ci_high"] = np.nan

    def _reachable(row: pd.Series) -> int:
        cap = float(row["reach_cap_share"])
        dept = str(row["department"])
        pop = float(population[dept])
        return int(round(cap * pop))

    df["reachable_audience"] = df.apply(_reachable, axis=1)

    column_order = [
        "department",
        "channel",
        "region",
        "channel_type",
        "department_tier",
        "tier_eligibility",
        "reach_cap_share",
        "reachable_audience",
        "salience_multiplier",
        "attention_multiplier",
        "network_hostility",
        "unit_cost_pyg",
        "fx_tier_default",
        "diminishing_returns_k",
        "diminishing_returns_inflection_pct",
        "dept_mean_propensity",
        "dept_mean_propensity_source",
        "dept_propensity_ci_low",
        "dept_propensity_ci_high",
        "provenance",
    ]
    return cast(pd.DataFrame, df[column_order])
