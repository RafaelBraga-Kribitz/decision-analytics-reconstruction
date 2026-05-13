"""Regression: dbscan.max_noise_rate value and inline comment stay aligned (Gate A4 = 1%)."""

from __future__ import annotations

from pathlib import Path

import yaml

_MODEL_PARAMS = Path(__file__).resolve().parents[1] / "config" / "model_params.yaml"


def test_dbscan_max_noise_rate_is_one_percent_in_yaml() -> None:
    with open(_MODEL_PARAMS, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cap = cfg["dbscan"]["max_noise_rate"]
    assert cap == 0.01, f"expected max_noise_rate 0.01, got {cap!r}"


def test_dbscan_max_noise_rate_line_has_no_point_zero_three_comment() -> None:
    """N1.4 class bug: comment once said >0.03 while value was 0.01 — guard both sides."""
    text = _MODEL_PARAMS.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("max_noise_rate:"):
            assert "0.01" in stripped
            assert "0.03" not in stripped
            if "#" in stripped:
                comment = stripped.split("#", 1)[1]
                assert "0.03" not in comment, "comment must not cite 0.03 when cap is 0.01"
            return
    raise AssertionError("dbscan.max_noise_rate line not found in model_params.yaml")
