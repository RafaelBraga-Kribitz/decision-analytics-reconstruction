"""Unit tests for ``population_segmentation.pipeline.export`` private helpers."""

from __future__ import annotations

import pandas as pd
import pytest
from population_segmentation.pipeline.export import _validate_export_contracts
from population_segmentation.pipeline.models.segmentation import SEGMENT_LABEL_MAP


def _minimal_anchors() -> dict:
    return {
        "department_participation_rates": {
            "Presidente Hayes": 0.5,
            "Alto Parana": 0.5,
            "Central": 0.5,
            "Guaira": 0.5,
        }
    }


def _minimal_entity_frames(*, n: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seg = list(SEGMENT_LABEL_MAP.values())[0]
    master = pd.DataFrame(
        {
            "entity_id": range(n),
            "department": ["Asuncion"] * n,
        }
    )
    prop = pd.DataFrame(
        {
            "entity_id": range(n),
            "participation_propensity": [0.42] * n,
        }
    )
    labels_df = pd.DataFrame(
        {
            "entity_id": range(n),
            "segment_label": [seg] * n,
        }
    )
    return master, prop, labels_df


def _valid_reach_by_segment() -> pd.DataFrame:
    labels_sorted = sorted(set(SEGMENT_LABEL_MAP.values()))
    assert len(labels_sorted) == 6
    rows = []
    for i, sl in enumerate(labels_sorted):
        rows.append(
            {
                "segment_label": sl,
                "segment_size": 100 + i,
                "segment_size_pct": 1.0 / 6.0,
                "mean_participation_propensity": 0.4,
                "pct_internet_access": 0.5,
                "mean_tv_penetration": 0.3,
                "mean_radio_penetration": 0.25,
                "mean_whatsapp_penetration": 0.35,
                "pct_rural": 0.2,
                "pct_jopara": 0.3,
                "pct_structural_dependency": 0.1,
                "dominant_department": "Central",
                "primary_reach_channel": "tv",
            }
        )
    return pd.DataFrame(rows)


def test_validate_export_contracts_passes_minimal() -> None:
    m, p, labels_df = _minimal_entity_frames()
    _validate_export_contracts(m, p, labels_df, _minimal_anchors())


def test_validate_export_contracts_passes_with_reach() -> None:
    m, p, labels_df = _minimal_entity_frames()
    _validate_export_contracts(m, p, labels_df, _minimal_anchors(), reach=_valid_reach_by_segment())


def test_validate_export_contracts_row_count_mismatch() -> None:
    m, p, labels_df = _minimal_entity_frames(n=2)
    p2 = p.head(1)
    with pytest.raises(ValueError, match="Row count mismatch"):
        _validate_export_contracts(m, p2, labels_df, _minimal_anchors())


def test_validate_export_contracts_prop_out_of_range() -> None:
    m, p, labels_df = _minimal_entity_frames()
    p = p.copy()
    p.loc[0, "participation_propensity"] = 1.5
    with pytest.raises(ValueError, match="participation_propensity"):
        _validate_export_contracts(m, p, labels_df, _minimal_anchors())


def test_validate_export_contracts_bad_segment_label() -> None:
    m, p, labels_df = _minimal_entity_frames()
    labels_df = labels_df.copy()
    labels_df.loc[0, "segment_label"] = "not_a_real_segment"
    with pytest.raises(ValueError, match="non-canonical"):
        _validate_export_contracts(m, p, labels_df, _minimal_anchors())


def test_validate_export_contracts_reach_wrong_row_count() -> None:
    m, p, labels_df = _minimal_entity_frames()
    bad_reach = _valid_reach_by_segment().head(3)
    with pytest.raises(ValueError, match="expected 6 rows"):
        _validate_export_contracts(m, p, labels_df, _minimal_anchors(), reach=bad_reach)
