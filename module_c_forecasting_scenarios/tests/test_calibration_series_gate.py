"""CI gate: calibration.series must be exactly A or B (no hybrid)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CALIB_PATH = _REPO_ROOT / "module_c_forecasting_scenarios/config/calibration.yaml"


def test_calibration_series_is_singleton_letter() -> None:
    with open(_CALIB_PATH) as f:
        cfg = yaml.safe_load(f)
    series = str(cfg.get("series", "")).strip().upper()
    assert series in {"A", "B"}, f"calibration.series must be A or B, got {series!r}"


def test_calibration_yaml_forbids_hybrid_keys() -> None:
    """Guardrail: do not declare parallel active series as sibling YAML keys."""
    with open(_CALIB_PATH) as f:
        cfg = yaml.safe_load(f)
    keys = {str(k).lower() for k in cfg if isinstance(k, str)}
    assert not (
        "series_a" in keys and "series_b" in keys
    ), "Use a single ``series`` key; do not add parallel series_a / series_b objects."


def test_calibration_anchors_have_margin_m_star() -> None:
    with open(_CALIB_PATH) as f:
        cfg = yaml.safe_load(f)
    anchors = cfg.get("anchors") or {}
    assert "A" in anchors and "B" in anchors
    assert float(anchors["A"]["margin_m_star_pp"]) == pytest.approx(3.70)
    assert float(anchors["B"]["margin_m_star_pp"]) == pytest.approx(3.88)
