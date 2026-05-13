"""Coverage tests for Module C pipeline runners and small uncovered branches.

All tests are fast (no PyMC NUTS). Heavy model calls are either skipped via
branch conditions (insufficient rows, empty frames) or patched with synthetic
DataFrames.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# mlflow_tracking
# ---------------------------------------------------------------------------


def test_log_run_params_noop_without_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    """log_run_params returns immediately when MLFLOW_TRACKING_URI is absent."""
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    from module_c_forecasting_scenarios.mlflow_tracking import log_run_params

    log_run_params({"key": "val"})  # must not raise


def test_log_run_params_with_uri(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """log_run_params calls mlflow when URI is present (mlflow mocked)."""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path}/ml.db")
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "test_c_pipeline")
    from module_c_forecasting_scenarios.mlflow_tracking import log_run_params

    mock_mlflow = MagicMock()
    with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
        log_run_params({"n_waves": 4, "series": "A"})
    mock_mlflow.set_tracking_uri.assert_called_once()
    mock_mlflow.log_params.assert_called_once()


# ---------------------------------------------------------------------------
# viz.plotly_explorer
# ---------------------------------------------------------------------------


def test_write_scenario_explorer_html(tmp_path: Path) -> None:
    """write_scenario_explorer_html writes an HTML file from synthetic frames."""
    from module_c_forecasting_scenarios.viz.plotly_explorer import write_scenario_explorer_html

    daily = pd.DataFrame(
        {
            "date": pd.date_range("2018-02-01", periods=5, freq="W"),
            "posterior_mean_preference_margin_pp": [3.1, 3.3, 3.5, 3.7, 3.9],
            "posterior_hdi_low_pp": [1.0, 1.1, 1.2, 1.3, 1.4],
            "posterior_hdi_high_pp": [5.0, 5.1, 5.2, 5.3, 5.4],
        }
    )
    tracking = pd.DataFrame(
        {
            "publication_date": pd.to_datetime(["2018-02-15", "2018-03-15"]),
            "m_poll_pp": [3.5, 4.0],
        }
    )
    out = tmp_path / "scenario_explorer.html"
    write_scenario_explorer_html(daily, tracking, out)
    assert out.exists()
    assert out.stat().st_size > 100


def test_write_scenario_explorer_html_empty_tracking(tmp_path: Path) -> None:
    """Handles empty tracking frame (no survey markers added to plot)."""
    from module_c_forecasting_scenarios.viz.plotly_explorer import write_scenario_explorer_html

    daily = pd.DataFrame(
        {
            "date": pd.date_range("2018-02-01", periods=3, freq="W"),
            "posterior_mean_preference_margin_pp": [3.0, 3.2, 3.4],
            "posterior_hdi_low_pp": [1.0, 1.1, 1.2],
            "posterior_hdi_high_pp": [5.0, 5.1, 5.2],
        }
    )
    out = tmp_path / "explorer_empty.html"
    write_scenario_explorer_html(daily, pd.DataFrame(), out)
    assert out.exists()


# ---------------------------------------------------------------------------
# contract_validate — error branches
# ---------------------------------------------------------------------------


def test_load_contract_unknown_schema_raises() -> None:
    """load_contract raises QAGateFailure for unknown schema names."""
    from module_c_forecasting_scenarios.data.contract_validate import load_contract
    from module_c_forecasting_scenarios.data.exceptions import QAGateFailure

    with pytest.raises(QAGateFailure, match="nonexistent_schema_xyz"):
        load_contract("nonexistent_schema_xyz")


def test_validate_contract_duplicate_key_raises() -> None:
    """validate_dataframe_contract raises QAGateFailure on duplicate unique key."""
    from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
    from module_c_forecasting_scenarios.data.exceptions import QAGateFailure

    df = pd.DataFrame(
        {
            "date": [date(2018, 2, 1), date(2018, 2, 1)],
            "calibration_series": ["A", "A"],
            "series_tag": ["A", "A"],
            "posterior_mean_preference_margin_pp": [3.0, 3.0],
            "posterior_hdi_low_pp": [1.0, 1.0],
            "posterior_hdi_high_pp": [5.0, 5.0],
            "model_version": ["v0.1", "v0.1"],
        }
    )
    with pytest.raises(QAGateFailure, match="duplicate keys"):
        validate_dataframe_contract(df, "daily_posterior_forecast")


# ---------------------------------------------------------------------------
# herding_weights — April band branch
# ---------------------------------------------------------------------------


def test_rho_herd_april_band() -> None:
    """rho_herd_for_row returns 0.25 for April 1–15 publication dates."""
    from module_c_forecasting_scenarios.features.herding_weights import rho_herd_for_row

    rho = rho_herd_for_row(date(2018, 4, 10), None)
    assert rho == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# shock_scores — compounded_herd branch
# ---------------------------------------------------------------------------


def test_scenario_bucket_compounded_herd() -> None:
    """scenario_bucket_for_margin returns 'compounded_herd' for extreme+opaque+herd."""
    from module_c_forecasting_scenarios.features.shock_scores import scenario_bucket_for_margin

    bucket = scenario_bucket_for_margin(m_poll_pp=20.0, m_star_pp=3.7, phi=0.2, rho=0.55)
    assert bucket == "compounded_herd"


# ---------------------------------------------------------------------------
# taxonomy_tables — additional pollster branches
# ---------------------------------------------------------------------------


def test_normalize_pollster_grau() -> None:
    from module_c_forecasting_scenarios.features.taxonomy_tables import normalize_pollster_id

    pid, fam = normalize_pollster_id("Grau Research")
    assert pid == "grau"


def test_normalize_pollster_ecodat() -> None:
    from module_c_forecasting_scenarios.features.taxonomy_tables import normalize_pollster_id

    pid, fam = normalize_pollster_id("ECODAT Consultoría")
    assert pid == "ecodat"


def test_normalize_pollster_market() -> None:
    from module_c_forecasting_scenarios.features.taxonomy_tables import normalize_pollster_id

    pid, fam = normalize_pollster_id("Market Research Inc.")
    assert pid == "market"


def test_normalize_pollster_prologo() -> None:
    from module_c_forecasting_scenarios.features.taxonomy_tables import normalize_pollster_id

    pid, fam = normalize_pollster_id("Prologo Consultora")
    assert pid == "prologo"


# ---------------------------------------------------------------------------
# exit_model — insufficient rows branch (no PyMC)
# ---------------------------------------------------------------------------


def test_fit_exit_quickcount_insufficient_rows() -> None:
    """fit_exit_quickcount returns summary without PyMC when rows < 2."""
    from module_c_forecasting_scenarios.models.exit.exit_model import fit_exit_quickcount

    exit_df = pd.DataFrame(
        {
            "poll_wave_id": ["wave_exit_01"],
            "pollster_id": ["exit_consortium"],
            "publication_date": [date(2018, 4, 22)],
            "field_window_start": [date(2018, 4, 22)],
            "field_window_end": [date(2018, 4, 22)],
            "preference_proxy_a_pct": [54.1],
            "preference_proxy_b_pct": [45.9],
            "m_poll_pp": [8.2],
            "oea_timing_compliant": [True],
            "eu_release_window_flag": [True],
            "calibration_series": ["A"],
        }
    )
    summary, idata = fit_exit_quickcount(exit_df, calibration_series="A")
    assert idata is None
    assert "note" in summary.columns
    assert summary["note"].iloc[0] == "insufficient_exit_rows_for_regression"


# ---------------------------------------------------------------------------
# run_monte_carlo.main() — fast, no PyMC
# ---------------------------------------------------------------------------


def test_run_monte_carlo_main(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    """run_monte_carlo.main() runs end-to-end with fixture data (no PyMC)."""
    from module_c_forecasting_scenarios.pipeline.run_monte_carlo import main

    out = tmp_path / "mc_out"
    main(["--raw-csv", str(fixture_raw_polls_csv), "--out-dir", str(out)])
    assert out.exists()


# ---------------------------------------------------------------------------
# run_exit.main() — empty exit path (no PyMC)
# ---------------------------------------------------------------------------


def test_run_exit_main_no_exit_rows(tmp_path: Path) -> None:
    """run_exit.main() takes the empty-exit-df early-return when no exit waves."""
    import csv

    from module_c_forecasting_scenarios.pipeline.run_exit import main

    tracking_only_csv = tmp_path / "tracking_only.csv"
    with open(tracking_only_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "poll_raw_id",
                "publication_date",
                "pollster_display_name",
                "outlet_display_name",
                "preference_proxy_a_pct",
                "preference_proxy_b_pct",
                "undecided_pct",
                "sample_size",
                "has_ficha",
                "conglomerate_carrier",
                "wave_type",
                "field_window_candidate_text",
                "sample_size_known",
                "field_window_known",
                "mode_known",
                "oea_timing_compliant",
                "eu_release_window_flag",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "poll_raw_id": "raw_only_tracking_01",
                "publication_date": "2018-02-01",
                "pollster_display_name": "Capli First Análisis",
                "outlet_display_name": "ABC Color",
                "preference_proxy_a_pct": "50.4",
                "preference_proxy_b_pct": "37.2",
                "undecided_pct": "12.4",
                "sample_size": "",
                "has_ficha": "true",
                "conglomerate_carrier": "ABC",
                "wave_type": "tracking",
                "field_window_candidate_text": "",
                "sample_size_known": "false",
                "field_window_known": "true",
                "mode_known": "false",
                "oea_timing_compliant": "",
                "eu_release_window_flag": "",
            }
        )

    out = tmp_path / "exit_out"
    main(["--raw-csv", str(tracking_only_csv), "--out-dir", str(out)])
    assert (out / "exit_model_summary.parquet").exists()


# ---------------------------------------------------------------------------
# run_exit.main() — full path with fit_exit_quickcount mocked
# ---------------------------------------------------------------------------


def _mock_daily_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [date(2018, 2, d) for d in range(1, 6)],
            "calibration_series": ["A"] * 5,
            "series_tag": ["A"] * 5,
            "posterior_mean_preference_margin_pp": [3.0, 3.1, 3.2, 3.3, 3.4],
            "posterior_hdi_low_pp": [1.0] * 5,
            "posterior_hdi_high_pp": [5.0] * 5,
            "model_version": ["c_track_v0.1"] * 5,
        }
    )


def _mock_houses_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pollster_id": ["pollster_a"],
            "calibration_series": ["A"],
            "house_effect_posterior_mean": [0.1],
            "house_effect_hdi_low": [-0.5],
            "house_effect_hdi_high": [0.7],
            "pollster_bias_family": ["default"],
            "model_version": ["c_track_v0.1"],
        }
    )


def test_run_exit_main_with_fixture_mocked(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    """run_exit.main() covers the PyMC branch with fit_exit_quickcount mocked."""
    mock_summary = pd.DataFrame(
        [
            {
                "parameter": "intercept",
                "posterior_mean": 5.0,
                "hdi_low": 2.0,
                "hdi_high": 8.0,
                "calibration_series": "A",
                "model_version": "c_exit_bias_v0.1",
            }
        ]
    )

    with patch(
        "module_c_forecasting_scenarios.pipeline.run_exit.fit_exit_quickcount",
        return_value=(mock_summary, None),
    ):
        from module_c_forecasting_scenarios.pipeline.run_exit import main

        out = tmp_path / "exit_mocked"
        main(["--raw-csv", str(fixture_raw_polls_csv), "--out-dir", str(out)])

    assert (out / "exit_model_summary.parquet").exists()
    assert (out / "run_exit_manifest.json").exists()


# ---------------------------------------------------------------------------
# run_tracking.main() — run_tracking_fit_and_export mocked
# ---------------------------------------------------------------------------


def test_run_tracking_main_mocked(
    fixture_raw_polls_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_tracking.main() covers full flow with run_tracking_fit_and_export mocked."""
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    daily = _mock_daily_df()
    houses = _mock_houses_df()

    with patch(
        "module_c_forecasting_scenarios.pipeline.run_tracking.run_tracking_fit_and_export",
        return_value=(MagicMock(), daily, houses),
    ):
        from module_c_forecasting_scenarios.pipeline.run_tracking import main

        out = tmp_path / "tracking_mocked"
        main(["--raw-csv", str(fixture_raw_polls_csv), "--out-dir", str(out)])

    assert (out / "run_tracking_manifest.json").exists()
    assert (out / "house_effect_seed_matrix.csv").exists()
    assert (out / "polling_transparency_audit.csv").exists()
    assert (out / "scenario_explorer.html").exists()
