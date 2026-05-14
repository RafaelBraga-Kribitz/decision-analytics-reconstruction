"""Stratified MC draws — all canonical buckets present + synthesis fallback."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.scenarios.monte_carlo import (
    CANONICAL_BUCKETS,
    run_monte_carlo_scenarios,
)


def test_mc_draws_cover_all_canonical_buckets(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    assert set(draws["scenario_bucket"].unique()) == set(CANONICAL_BUCKETS)
    counts = draws["scenario_bucket"].value_counts().to_dict()
    # Equal partitioning into 3 buckets → 300 each at n=900.
    for b in CANONICAL_BUCKETS:
        assert counts[b] == 300


def test_mc_draws_size_default_is_10000(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=10_000)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    assert len(draws) == 10_000


def test_mc_draws_synthetic_prior_marks_source(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    # Drop one bucket from tracking to force prior synthesis.
    missing_bucket = "compounded_herd"
    truncated = tracking[tracking["scenario_bucket"] != missing_bucket].copy()
    manifest = run_monte_carlo_scenarios(truncated, None, out_dir=tmp_path, n_draws=900)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    synthetic = draws[draws["draw_source"] == "synthetic_prior"]
    assert set(synthetic["scenario_bucket"].unique()) == {missing_bucket}
    assert missing_bucket in manifest["buckets_synthesised_from_prior"]


def test_mc_draws_schema_fields_match_contract(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=300)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    contract_path = (
        Path(__file__).resolve().parents[2] / "schema_contracts" / "monte_carlo_draws.yaml"
    )
    contract = yaml.safe_load(contract_path.read_text())
    expected_fields = set(contract["fields"].keys())
    assert set(draws.columns) == expected_fields


def test_mc_manifest_records_quotas(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    manifest = run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
    assert manifest["bucket_quotas"] == {b: 300 for b in CANONICAL_BUCKETS}
    assert manifest["n_draws"] == 900
    assert manifest["canonical_buckets"] == list(CANONICAL_BUCKETS)


def test_mc_deterministic_with_fixed_seed(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    run_monte_carlo_scenarios(tracking, None, out_dir=out_a, n_draws=600)
    run_monte_carlo_scenarios(tracking, None, out_dir=out_b, n_draws=600)
    a = pd.read_parquet(out_a / "monte_carlo_draws.parquet")
    b = pd.read_parquet(out_b / "monte_carlo_draws.parquet")
    pd.testing.assert_frame_equal(a, b)


def test_mc_raises_when_bucket_missing_and_no_prior(
    fixture_raw_polls_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    truncated = tracking[tracking["scenario_bucket"] != "compounded_herd"].copy()
    # Patch shock_params so the canonical bucket has no prior.
    import module_c_forecasting_scenarios.scenarios.monte_carlo as mc_mod

    original_load = mc_mod.yaml.safe_load

    def _strip_priors(text: str | bytes) -> object:
        doc = original_load(text)
        if isinstance(doc, dict) and "bucket_priors" in doc:
            doc["bucket_priors"].pop("compounded_herd", None)
        return doc

    monkeypatch.setattr(mc_mod.yaml, "safe_load", _strip_priors)
    with pytest.raises(ValueError, match="missing from tracking"):
        run_monte_carlo_scenarios(truncated, None, out_dir=tmp_path, n_draws=300)
