# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Aggregate media reachability by segment for Module A contract output.

Produces:

- ``aggregate_media_reachability_by_segment(df)`` — one row per canonical
  segment_label (k=6) matching ``schema_contracts/media_reachability_by_segment.yaml``.
- ``aggregate_media_reachability_by_segment_department(df)`` — one row per
  ``(segment_label, department)`` pair matching
  ``schema_contracts/media_reachability_by_segment_department.yaml``.

The two functions cover the two contract grains: segment-only (national
diagnostic rollup) and segment-by-department (authoritative cap source for
Module B's LP/MILP).
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd


def _primary_reach_channel(row: pd.Series) -> str:  # type: ignore[type-arg]
    """Return the dominant reach channel for a segment row.

    Argmax of (mean_tv_penetration, mean_radio_penetration, mean_whatsapp_penetration).
    If all three are equal, returns "direct".
    """
    tv = float(row["mean_tv_penetration"])
    radio = float(row["mean_radio_penetration"])
    whatsapp = float(row["mean_whatsapp_penetration"])
    if tv == radio == whatsapp:
        return "direct"
    best = max(tv, radio, whatsapp)
    if best == tv:
        return "tv"
    if best == radio:
        return "radio"
    return "whatsapp"


def aggregate_media_reachability_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-entity feature rows into one row per segment.

    Args:
        df: Entity-level DataFrame. Required columns:
            ``segment_label``, ``participation_propensity``, ``internet_access_flag``,
            ``media_penetration_tv``, ``media_penetration_radio``,
            ``media_penetration_whatsapp``, ``rural_flag``, ``jopara_flag``,
            ``structural_dependency_encoded``, ``department``.

    Returns:
        One row per canonical segment with all 13 contract columns from
        ``schema_contracts/media_reachability_by_segment.yaml``.

    Raises:
        KeyError: If a required column is missing from ``df``.

    Example:
        Called from ``run_export`` after ``segment_label`` and media penetration
        columns exist on the entity-level population dataset.
    """
    total = len(df)

    agg = (
        df.groupby("segment_label", sort=False)
        .agg(
            segment_size=("segment_label", "count"),
            mean_participation_propensity=("participation_propensity", "mean"),
            pct_internet_access=("internet_access_flag", "mean"),
            mean_tv_penetration=("media_penetration_tv", "mean"),
            mean_radio_penetration=("media_penetration_radio", "mean"),
            mean_whatsapp_penetration=("media_penetration_whatsapp", "mean"),
            pct_rural=("rural_flag", "mean"),
            pct_jopara=("jopara_flag", "mean"),
            pct_structural_dependency=("structural_dependency_encoded", "mean"),
            dominant_department=("department", lambda s: s.mode().iloc[0]),
        )
        .reset_index()
    )

    agg["segment_size_pct"] = agg["segment_size"] / total

    float_cols = [
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
        "segment_size_pct",
    ]
    for col in float_cols:
        agg[col] = agg[col].astype("float32")

    agg["primary_reach_channel"] = agg.apply(_primary_reach_channel, axis=1)

    column_order = [
        "segment_label",
        "segment_size",
        "segment_size_pct",
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
        "dominant_department",
        "primary_reach_channel",
    ]
    return cast(pd.DataFrame, agg[column_order])


SEGMENT_LABELS: tuple[str, ...] = (
    "rural_committed",
    "urban_high_volatility",
    "youth_volatile",
    "structurally_dependent_bloc",
    "rural_low_propensity",
    "committed_opposition",
)

DEPARTMENTS: tuple[str, ...] = (
    "Asuncion",
    "Concepcion",
    "San Pedro",
    "Cordillera",
    "Guaira",
    "Caaguazu",
    "Caazapa",
    "Itapua",
    "Misiones",
    "Paraguari",
    "Alto Parana",
    "Central",
    "Neembucu",
    "Amambay",
    "Canindeyu",
    "Presidente Hayes",
    "Boqueron",
    "Alto Paraguay",
)

CHACO_DEPARTMENTS: frozenset[str] = frozenset({"Presidente Hayes", "Boqueron", "Alto Paraguay"})


def _region_for(department: str) -> str:
    return "CHACO" if department in CHACO_DEPARTMENTS else "ORIENTAL"


def _primary_channel_from_means(tv: float, radio: float, whatsapp: float) -> str:
    """Deterministic argmax of the three penetration means; tie → 'direct'."""
    if np.isnan(tv) or np.isnan(radio) or np.isnan(whatsapp):
        return "direct"
    if tv == radio == whatsapp:
        return "direct"
    best = max(tv, radio, whatsapp)
    if best == tv:
        return "tv"
    if best == radio:
        return "radio"
    return "whatsapp"


def aggregate_media_reachability_by_segment_department(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-entity rows into one row per (segment_label, department) pair.

    The output is **dense**: every (segment, department) pair appears even if
    no entity is assigned to it; empty cells have ``segment_size=0`` and the
    mean columns set to ``NaN`` (this matches
    ``schema_contracts/media_reachability_by_segment_department.yaml``).

    Args:
        df: Entity-level DataFrame. Required columns mirror those required by
            :func:`aggregate_media_reachability_by_segment`, plus ``department``.

    Returns:
        Dense ``len(SEGMENT_LABELS) * len(DEPARTMENTS)`` rows with all
        13 columns from the contract.

    Raises:
        KeyError: If ``department`` or ``segment_label`` is missing from ``df``.

    Example:
        Emit ``media_reachability_by_segment_department`` before handing reach
        caps to Module B allocation features.
    """
    if "department" not in df.columns:
        raise KeyError("aggregate_media_reachability_by_segment_department requires 'department'")
    if "segment_label" not in df.columns:
        raise KeyError(
            "aggregate_media_reachability_by_segment_department requires 'segment_label'"
        )

    segment_totals = df.groupby("segment_label", sort=False).size().to_dict()
    dept_totals = df.groupby("department", sort=False).size().to_dict()

    grouped = df.groupby(["segment_label", "department"], sort=False)
    observed = grouped.agg(
        segment_size=("segment_label", "count"),
        mean_participation_propensity=("participation_propensity", "mean"),
        pct_internet_access=("internet_access_flag", "mean"),
        mean_tv_penetration=("media_penetration_tv", "mean"),
        mean_radio_penetration=("media_penetration_radio", "mean"),
        mean_whatsapp_penetration=("media_penetration_whatsapp", "mean"),
        pct_rural=("rural_flag", "mean"),
        pct_jopara=("jopara_flag", "mean"),
        pct_structural_dependency=("structural_dependency_encoded", "mean"),
    ).reset_index()

    # Build the dense (segment, department) frame and left-join observed values.
    dense_index = pd.MultiIndex.from_product(
        [SEGMENT_LABELS, DEPARTMENTS], names=["segment_label", "department"]
    )
    dense = pd.DataFrame(index=dense_index).reset_index()
    out = dense.merge(observed, on=["segment_label", "department"], how="left")
    out["segment_size"] = out["segment_size"].fillna(0).astype("int64")

    out["segment_size_pct_of_segment"] = out.apply(
        lambda row: (
            (row["segment_size"] / segment_totals[row["segment_label"]])
            if segment_totals.get(row["segment_label"], 0)
            else 0.0
        ),
        axis=1,
    ).astype("float32")
    out["segment_size_pct_of_department"] = out.apply(
        lambda row: (
            (row["segment_size"] / dept_totals[row["department"]])
            if dept_totals.get(row["department"], 0)
            else 0.0
        ),
        axis=1,
    ).astype("float32")

    float_cols = [
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
    ]
    for col in float_cols:
        out[col] = out[col].astype("float32")

    out["region"] = out["department"].map(_region_for)

    out["primary_reach_channel"] = [
        _primary_channel_from_means(tv, radio, wa) if size > 0 else None
        for tv, radio, wa, size in zip(
            out["mean_tv_penetration"],
            out["mean_radio_penetration"],
            out["mean_whatsapp_penetration"],
            out["segment_size"],
            strict=False,
        )
    ]

    column_order = [
        "segment_label",
        "department",
        "region",
        "segment_size",
        "segment_size_pct_of_department",
        "segment_size_pct_of_segment",
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
        "pct_structural_dependency",
        "primary_reach_channel",
    ]
    return cast(pd.DataFrame, out[column_order])
