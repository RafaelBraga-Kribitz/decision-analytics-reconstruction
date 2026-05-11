"""Tests that verify _validate_export_contracts raises on every known violation.

Each test constructs a *minimal valid* set of DataFrames and then injects
exactly one fault; the assertion is that ValueError is raised with a message
that identifies the offending artifact or column.  These are unit-level tests
(no full pipeline run required).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def anchors() -> dict[str, Any]:
    path = Path(__file__).parent.parent / "config" / "calibration_anchors.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _valid_master(n: int = 20) -> pd.DataFrame:
    """Minimal population_master_clean frame that passes all checks."""
    from population_segmentation.models.segmentation import SEGMENT_LABEL_MAP

    depts = [
        "Presidente Hayes",
        "Alto Parana",
        "Central",
        "Guaira",
        "Concepcion",
    ]
    return pd.DataFrame(
        {
            "entity_id": range(n),
            "department": [depts[i % len(depts)] for i in range(n)],
            "segment_label": [list(SEGMENT_LABEL_MAP.values())[i % 6] for i in range(n)],
        }
    )


def _valid_prop(master: pd.DataFrame, anchors: dict[str, Any]) -> pd.DataFrame:
    """Participation propensity that passes dept calibration gates."""
    dept_targets = anchors["department_participation_rates"]
    national = float(anchors["national"]["participation_rate"])
    prop_vals = master["department"].map(lambda d: float(dept_targets.get(d, national))).to_numpy()
    return pd.DataFrame(
        {
            "entity_id": master["entity_id"].to_numpy(),
            "participation_propensity": prop_vals,
        }
    )


def _valid_labels(master: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entity_id": master["entity_id"].to_numpy(),
            "segment_label": master["segment_label"].to_numpy(),
            "segment_id": [i % 6 for i in range(len(master))],
            "dbscan_noise_flag": [False] * len(master),
        }
    )


def _valid_reach() -> pd.DataFrame:
    """Minimal media reachability aggregate frame (6 rows, one per segment)."""
    from population_segmentation.models.segmentation import SEGMENT_LABEL_MAP

    labels = list(SEGMENT_LABEL_MAP.values())
    n = len(labels)
    return pd.DataFrame(
        {
            "segment_label": labels,
            "segment_size": [100] * n,
            "segment_size_pct": [1 / n] * n,
            "mean_participation_propensity": [0.5] * n,
            "pct_internet_access": [0.4] * n,
            "mean_tv_penetration": [0.6] * n,
            "mean_radio_penetration": [0.5] * n,
            "mean_whatsapp_penetration": [0.3] * n,
            "pct_rural": [0.4] * n,
            "pct_jopara": [0.3] * n,
            "pct_structural_dependency": [0.2] * n,
            "dominant_department": ["Central"] * n,
            "primary_reach_channel": ["tv"] * n,
        }
    )


# ---------------------------------------------------------------------------
# Entity-level artifact violations
# ---------------------------------------------------------------------------


def test_duplicate_entity_id_master_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    master.loc[1, "entity_id"] = master.loc[0, "entity_id"]  # introduce dup
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    with pytest.raises(ValueError, match="population_master_clean"):
        _validate_export_contracts(master, prop, labels, anchors)


def test_duplicate_entity_id_prop_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    prop.loc[1, "entity_id"] = prop.loc[0, "entity_id"]
    labels = _valid_labels(master)
    with pytest.raises(ValueError, match="participation_propensity"):
        _validate_export_contracts(master, prop, labels, anchors)


def test_duplicate_entity_id_labels_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    labels.loc[1, "entity_id"] = labels.loc[0, "entity_id"]
    with pytest.raises(ValueError, match="segment_labels"):
        _validate_export_contracts(master, prop, labels, anchors)


def test_row_count_mismatch_prop_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors).iloc[:-1].copy()  # one row short
    labels = _valid_labels(master)
    with pytest.raises(ValueError, match="Row count mismatch"):
        _validate_export_contracts(master, prop, labels, anchors)


def test_propensity_out_of_range_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    prop.loc[0, "participation_propensity"] = 1.5  # out of [0, 1]
    labels = _valid_labels(master)
    with pytest.raises(ValueError, match="outside \\[0, 1\\]"):
        _validate_export_contracts(master, prop, labels, anchors)


def test_non_canonical_segment_label_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    labels.loc[0, "segment_label"] = "made_up_segment"
    with pytest.raises(ValueError, match="non-canonical labels"):
        _validate_export_contracts(master, prop, labels, anchors)


# ---------------------------------------------------------------------------
# media_reachability_by_segment violations
# ---------------------------------------------------------------------------


def test_media_wrong_row_count_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    reach = _valid_reach().iloc[:4].copy()  # only 4 rows, need 6
    with pytest.raises(ValueError, match="expected 6 rows"):
        _validate_export_contracts(master, prop, labels, anchors, reach=reach)


def test_media_duplicate_segment_label_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    reach = _valid_reach().copy()
    reach.loc[1, "segment_label"] = reach.loc[0, "segment_label"]  # dup
    with pytest.raises(ValueError, match="duplicate segment_label"):
        _validate_export_contracts(master, prop, labels, anchors, reach=reach)


def test_media_invalid_reach_channel_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    reach = _valid_reach().copy()
    reach.loc[0, "primary_reach_channel"] = "newspaper"  # not in allowed set
    with pytest.raises(ValueError, match="invalid primary_reach_channel"):
        _validate_export_contracts(master, prop, labels, anchors, reach=reach)


def test_media_proportion_out_of_range_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    reach = _valid_reach().copy()
    reach.loc[0, "mean_tv_penetration"] = 1.5  # outside [0, 1]
    with pytest.raises(ValueError, match="mean_tv_penetration"):
        _validate_export_contracts(master, prop, labels, anchors, reach=reach)


def test_media_missing_column_raises(anchors: dict[str, Any]) -> None:
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    reach = _valid_reach().drop(columns=["primary_reach_channel"])
    with pytest.raises(ValueError, match="missing columns"):
        _validate_export_contracts(master, prop, labels, anchors, reach=reach)


def test_valid_frames_do_not_raise(anchors: dict[str, Any]) -> None:
    """Sanity check: completely valid frames must not raise."""
    from population_segmentation.pipeline.export import _validate_export_contracts

    master = _valid_master()
    prop = _valid_prop(master, anchors)
    labels = _valid_labels(master)
    reach = _valid_reach()
    # Must complete without exception
    _validate_export_contracts(master, prop, labels, anchors, reach=reach)
