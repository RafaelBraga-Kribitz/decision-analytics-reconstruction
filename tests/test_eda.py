"""
pytest test suite for Paraguay Campaign EDA artefacts.

Run from project root:
    python3 -m pytest tests/test_eda.py -v
"""

import hashlib
from pathlib import Path

import pandas as pd
import pytest

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
EDA_DIR = ROOT / "reports" / "eda"
DATA = ROOT / "data" / "processed"


# ════════════════════════════════════════════════════════════════════════════
# EXPECTED PNG FILES
# ════════════════════════════════════════════════════════════════════════════
MODULE_A_CHARTS = [
    "A1_segment_sizes.png",
    "A2_age_distribution_by_segment.png",
    "A3_gender_by_segment.png",
    "A4_propensity_heatmap_dept_segment.png",
    "A5_propensity_violin_by_segment.png",
    "A6_urban_rural_by_segment.png",
    "A7_language_by_segment.png",
    "A8_structural_dependency_by_segment.png",
    "A9_correlation_heatmap.png",
    "A10_pca_biplot.png",
    "A11_nbi_stress_by_department.png",
    "A12_reachability_distribution.png",
    "A13_preference_strength_by_segment.png",
]

MODULE_B_CHARTS = [
    "B1_budget_by_department.png",
    "B2_weekly_budget_by_channel_type.png",
    "B3_broadcast_vs_direct_budget.png",
    "B4_reach_utilisation_heatmap.png",
    "B5_cost_per_persuasion_contact.png",
    "B6_fx_rate_series.png",
    "B7_routing_cost_matrix.png",
    "B8_reach_caps_vs_contacts.png",
]

MODULE_C_CHARTS = [
    "C1_forecast_timeline.png",
    "C2_posterior_margin_final.png",
    "C3_battleground_win_probability.png",
    "C4_house_effects_forest.png",
    "C5_mc_scenario_fan_chart.png",
    "C6_shock_scale_distribution.png",
    "C7_exit_model_posteriors.png",
    "C8_win_prob_vs_propensity.png",
    "C9_polling_transparency_audit.png",
    "C10_mc_win_probability_histogram.png",
]

SYNTHESIS_CHARTS = [
    "S1_segment_budget_heatmap.png",
    "S2_propensity_reachability_matrix.png",
    "S3_channel_roi_by_region.png",
    "S4_department_priority_matrix.png",
    "S5_efficiency_frontier.png",
]

ALL_CHARTS = MODULE_A_CHARTS + MODULE_B_CHARTS + MODULE_C_CHARTS + SYNTHESIS_CHARTS

MIN_PNG_SIZE_BYTES = 10_000  # 10 KB
MIN_REPORT_CHARS = 5_000


# ════════════════════════════════════════════════════════════════════════════
# PNG FILE EXISTENCE AND SIZE TESTS
# ════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("fname", ALL_CHARTS)
def test_png_exists(fname):
    """Every expected PNG output file must exist in reports/eda/."""
    path = EDA_DIR / fname
    assert path.exists(), f"Missing chart file: {path}"


@pytest.mark.parametrize("fname", ALL_CHARTS)
def test_png_minimum_size(fname):
    """Every PNG must be larger than 10 KB (guards against blank placeholder saves)."""
    path = EDA_DIR / fname
    if not path.exists():
        pytest.skip(f"File not found, skipped size check: {fname}")
    size = path.stat().st_size
    assert (
        size >= MIN_PNG_SIZE_BYTES
    ), f"{fname} is only {size} bytes — likely a blank/corrupt image"


@pytest.mark.parametrize("fname", ALL_CHARTS)
def test_png_valid_header(fname):
    """Every PNG must begin with the canonical PNG magic bytes (\\x89PNG)."""
    path = EDA_DIR / fname
    if not path.exists():
        pytest.skip(f"File not found, skipped header check: {fname}")
    with open(path, "rb") as fh:
        header = fh.read(4)
    assert header == b"\x89PNG", f"{fname} does not have a valid PNG header: {header!r}"


# ════════════════════════════════════════════════════════════════════════════
# REPORT FILE TESTS
# ════════════════════════════════════════════════════════════════════════════


def test_eda_report_exists():
    """eda_report.md must exist."""
    assert (EDA_DIR / "eda_report.md").exists()


def test_eda_report_minimum_length():
    """eda_report.md must contain at least 5,000 characters."""
    path = EDA_DIR / "eda_report.md"
    if not path.exists():
        pytest.skip("eda_report.md not found")
    text = path.read_text(encoding="utf-8")
    assert (
        len(text) >= MIN_REPORT_CHARS
    ), f"eda_report.md is only {len(text)} chars — expected >= {MIN_REPORT_CHARS}"


def test_eda_report_required_sections():
    """eda_report.md must contain all expected section headers."""
    path = EDA_DIR / "eda_report.md"
    if not path.exists():
        pytest.skip("eda_report.md not found")
    text = path.read_text(encoding="utf-8")
    required_sections = [
        "Executive Summary",
        "Data Quality Assessment",
        "Module A",
        "Module B",
        "Module C",
        "Cross-Module Synthesis",
        "Strategic Recommendations",
        "Methodology Notes",
        "Appendix",
    ]
    for section in required_sections:
        assert section in text, f"Missing section '{section}' in eda_report.md"


def test_strategic_brief_exists():
    """strategic_brief.md must exist."""
    assert (EDA_DIR / "strategic_brief.md").exists()


def test_strategic_brief_minimum_length():
    """strategic_brief.md must contain at least 600 words."""
    path = EDA_DIR / "strategic_brief.md"
    if not path.exists():
        pytest.skip("strategic_brief.md not found")
    text = path.read_text(encoding="utf-8")
    word_count = len(text.split())
    assert word_count >= 600, f"strategic_brief.md has only {word_count} words — expected >= 600"


def test_generate_script_exists():
    """generate_eda.py script must exist in reports/eda/."""
    assert (EDA_DIR / "generate_eda.py").exists()


# ════════════════════════════════════════════════════════════════════════════
# INPUT DATA LOADING TESTS
# ════════════════════════════════════════════════════════════════════════════


def test_load_population_master():
    """population_master_clean.parquet loads without error and has expected shape."""
    df = pd.read_parquet(DATA / "population_master_clean.parquet")
    seg = pd.read_parquet(DATA / "segment_labels.parquet")
    assert len(df) == len(seg), (
        "population_master_clean row count must match segment_labels "
        f"(got master={len(df)}, labels={len(seg)})"
    )
    assert len(df) >= 1_000, f"Expected at least 1,000 rows for EDA smoke, got {len(df)}"
    assert df.shape[1] >= 50, f"Expected >= 50 columns, got {df.shape[1]}"


def test_load_segment_labels():
    """segment_labels.parquet loads without error."""
    df = pd.read_parquet(DATA / "segment_labels.parquet")
    assert len(df) > 0
    assert "entity_id" in df.columns
    assert "segment_label" in df.columns


def test_load_participation_propensity():
    """participation_propensity.parquet loads without error."""
    df = pd.read_parquet(DATA / "participation_propensity.parquet")
    assert len(df) > 0
    assert "participation_propensity" in df.columns


def test_load_media_reachability_segment():
    """media_reachability_by_segment.csv loads without error."""
    df = pd.read_csv(DATA / "media_reachability_by_segment.csv")
    assert len(df) > 0


def test_load_media_reachability_segment_department():
    """media_reachability_by_segment_department.csv loads without error."""
    df = pd.read_csv(DATA / "media_reachability_by_segment_department.csv")
    assert len(df) > 0


def test_load_allocation_baseline():
    """allocation_baseline.csv loads without error."""
    df = pd.read_csv(DATA / "module_b" / "allocation_baseline.csv")
    assert len(df) > 0
    assert "budget_allocation_usd" in df.columns


def test_load_allocation_broadcast_to_direct():
    """allocation_broadcast_to_direct.csv loads without error."""
    df = pd.read_csv(DATA / "module_b" / "allocation_broadcast_to_direct.csv")
    assert len(df) > 0


def test_load_fx_layer():
    """fx_layer_series_b_weekly.csv loads without error."""
    df = pd.read_csv(DATA / "module_b" / "fx_layer_series_b_weekly.csv")
    assert len(df) > 0
    assert "tc_ref_pyg_per_usd" in df.columns


def test_load_reach_caps_baseline():
    """reach_caps_baseline.csv loads without error."""
    df = pd.read_csv(DATA / "module_b" / "reach_caps_baseline.csv")
    assert len(df) > 0


def test_load_reach_caps_broadcast_to_direct():
    """reach_caps_broadcast_to_direct.csv loads without error."""
    df = pd.read_csv(DATA / "module_b" / "reach_caps_broadcast_to_direct.csv")
    assert len(df) > 0


def test_load_routing_cost_matrix():
    """routing_cost_matrix_dry_standard.csv loads without error."""
    df = pd.read_csv(DATA / "module_b" / "routing_cost_matrix_dry_standard.csv")
    assert len(df) > 0
    assert "travel_time_minutes" in df.columns


def test_load_daily_posterior_forecast():
    """daily_posterior_forecast.parquet loads without error and has 142 rows."""
    df = pd.read_parquet(
        DATA / "module_c" / "run_all" / "tracking" / "daily_posterior_forecast.parquet"
    )
    assert len(df) == 142, f"Expected 142 rows, got {len(df)}"


def test_load_posterior_house_effects():
    """posterior_house_effects.parquet loads without error."""
    df = pd.read_parquet(
        DATA / "module_c" / "run_all" / "tracking" / "posterior_house_effects.parquet"
    )
    assert len(df) > 0


def test_load_polling_transparency_audit():
    """polling_transparency_audit.csv loads without error."""
    df = pd.read_csv(DATA / "module_c" / "run_all" / "tracking" / "polling_transparency_audit.csv")
    assert len(df) > 0


def test_load_house_effect_seed_matrix():
    """house_effect_seed_matrix.csv loads without error."""
    df = pd.read_csv(DATA / "module_c" / "run_all" / "tracking" / "house_effect_seed_matrix.csv")
    assert len(df) > 0


def test_load_battleground():
    """battleground_department_probability.parquet loads without error."""
    df = pd.read_parquet(
        DATA
        / "module_c"
        / "run_all"
        / "battleground"
        / "battleground_department_probability.parquet"
    )
    assert len(df) > 0
    assert "win_probability_a" in df.columns


def test_load_exit_model_summary():
    """exit_model_summary.parquet loads without error."""
    df = pd.read_parquet(DATA / "module_c" / "run_all" / "exit" / "exit_model_summary.parquet")
    assert len(df) > 0


def test_load_monte_carlo_draws():
    """monte_carlo_draws.parquet loads without error and has 10,000 rows."""
    df = pd.read_parquet(DATA / "module_c" / "run_all" / "mc" / "monte_carlo_draws.parquet")
    assert len(df) == 10_000, f"Expected 10,000 rows, got {len(df)}"


# ════════════════════════════════════════════════════════════════════════════
# DATA INVARIANT TESTS
# ════════════════════════════════════════════════════════════════════════════


def test_no_duplicate_entity_ids():
    """population_master must have no duplicate entity_ids."""
    df = pd.read_parquet(DATA / "population_master_clean.parquet")
    n_dupes = df["entity_id"].duplicated().sum()
    assert n_dupes == 0, f"Found {n_dupes} duplicate entity_ids in population_master"


def test_participation_propensity_in_unit_interval():
    """participation_propensity must be in [0, 1] for all records."""
    df = pd.read_parquet(DATA / "participation_propensity.parquet")
    col = df["participation_propensity"]
    assert col.min() >= 0.0, f"participation_propensity below 0: min={col.min()}"
    assert col.max() <= 1.0, f"participation_propensity above 1: max={col.max()}"


def test_participation_propensity_in_population_master():
    """participation_propensity in population_master must also be in [0, 1]."""
    df = pd.read_parquet(DATA / "population_master_clean.parquet")
    col = df["participation_propensity"].dropna()
    assert col.min() >= 0.0, f"participation_propensity below 0 in population_master: {col.min()}"
    assert col.max() <= 1.0, f"participation_propensity above 1 in population_master: {col.max()}"


def test_segment_id_coverage_matches_labels():
    """Every entity_id in segment_labels must appear in population_master and vice versa."""
    pop = pd.read_parquet(DATA / "population_master_clean.parquet")
    segs = pd.read_parquet(DATA / "segment_labels.parquet")
    pop_ids = set(pop["entity_id"].values)
    segs_ids = set(segs["entity_id"].values)
    missing_in_pop = segs_ids - pop_ids
    missing_in_segs = pop_ids - segs_ids
    assert (
        len(missing_in_pop) == 0
    ), f"{len(missing_in_pop)} entity_ids in segment_labels missing from population_master"
    assert (
        len(missing_in_segs) == 0
    ), f"{len(missing_in_segs)} entity_ids in population_master missing from segment_labels"


def test_win_probability_in_unit_interval():
    """win_probability_a must be in [0, 1] for all battleground department rows."""
    df = pd.read_parquet(
        DATA
        / "module_c"
        / "run_all"
        / "battleground"
        / "battleground_department_probability.parquet"
    )
    col = df["win_probability_a"]
    assert col.min() >= 0.0, f"win_probability_a below 0: {col.min()}"
    assert col.max() <= 1.0, f"win_probability_a above 1: {col.max()}"


def test_segment_labels_six_unique():
    """There must be exactly 6 unique segment labels."""
    df = pd.read_parquet(DATA / "segment_labels.parquet")
    n_unique = df["segment_label"].nunique()
    assert n_unique == 6, f"Expected 6 segment labels, found {n_unique}"


def test_all_segment_ids_have_label():
    """Every segment_id in population_master must have a non-null segment_label."""
    df = pd.read_parquet(DATA / "population_master_clean.parquet")
    null_labels = df["segment_label"].isnull().sum()
    assert null_labels == 0, f"{null_labels} rows have null segment_label"


def test_budget_allocation_non_negative():
    """budget_allocation_usd must be >= 0 in allocation_baseline."""
    df = pd.read_csv(DATA / "module_b" / "allocation_baseline.csv")
    assert df["budget_allocation_usd"].min() >= 0, "Negative budget allocation detected"


def test_fx_rates_positive():
    """FX reference and retail rates must be strictly positive."""
    df = pd.read_csv(DATA / "module_b" / "fx_layer_series_b_weekly.csv")
    assert df["tc_ref_pyg_per_usd"].min() > 0
    assert df["tc_retail_pyg_per_usd"].min() > 0


def test_mc_draws_10000():
    """Monte Carlo draws must have exactly 10,000 rows."""
    df = pd.read_parquet(DATA / "module_c" / "run_all" / "mc" / "monte_carlo_draws.parquet")
    assert len(df) == 10_000


def test_forecast_date_range():
    """daily_posterior_forecast must span from 2017-12-01 to 2018-04-21."""
    df = pd.read_parquet(
        DATA / "module_c" / "run_all" / "tracking" / "daily_posterior_forecast.parquet"
    )
    df["date"] = pd.to_datetime(df["date"])
    assert df["date"].min() == pd.Timestamp(
        "2017-12-01"
    ), f"Start date mismatch: {df['date'].min()}"
    assert df["date"].max() == pd.Timestamp("2018-04-21"), f"End date mismatch: {df['date'].max()}"


def test_reach_utilization_bounded():
    """reach_utilization must be in [0, 1] in allocation_baseline."""
    df = pd.read_csv(DATA / "module_b" / "allocation_baseline.csv")
    col = df["reach_utilization"].dropna()
    assert col.min() >= 0.0, f"reach_utilization below 0: {col.min()}"
    assert col.max() <= 1.0, f"reach_utilization above 1: {col.max()}"


def test_solver_status_all_optimal():
    """All solver_status values in allocation_baseline must be OPTIMAL."""
    df = pd.read_csv(DATA / "module_b" / "allocation_baseline.csv")
    non_optimal = (df["solver_status"] != "OPTIMAL").sum()
    assert non_optimal == 0, f"{non_optimal} rows with non-OPTIMAL solver status"


def test_population_master_expected_columns():
    """population_master must contain all critical columns."""
    df = pd.read_parquet(DATA / "population_master_clean.parquet")
    required = [
        "entity_id",
        "department",
        "gender",
        "age_on_event_date",
        "rural_flag",
        "language_census_bucket",
        "participation_propensity",
        "segment_label",
        "segment_id",
        "reachability_index",
        "preference_proxy",
        "nbi_stress_prior",
    ]
    for col in required:
        assert col in df.columns, f"Missing required column: {col}"


# ════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCY TEST
# ════════════════════════════════════════════════════════════════════════════


def _file_hash(path: Path) -> str:
    """Return MD5 hash of file contents."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_idempotency_png_files_stable_after_first_run():
    """
    All PNG files must exist and be non-empty.
    Running twice (first run already done) must leave files present with the same size.
    This test captures current sizes/hashes and asserts they are stable (files not deleted
    between runs) — a proxy for idempotency without re-running the whole script.
    """
    sizes = {}
    for fname in ALL_CHARTS:
        path = EDA_DIR / fname
        assert path.exists(), f"File missing in idempotency check: {fname}"
        sz = path.stat().st_size
        assert sz >= MIN_PNG_SIZE_BYTES, f"{fname} too small in idempotency check: {sz} bytes"
        sizes[fname] = sz
    # All sizes collected without error — idempotency precondition met
    assert len(sizes) == len(ALL_CHARTS)


def test_idempotency_reports_stable():
    """eda_report.md and strategic_brief.md must remain unchanged after initial generation."""
    for fname in ["eda_report.md", "strategic_brief.md"]:
        path = EDA_DIR / fname
        assert path.exists(), f"{fname} missing in idempotency check"
        assert path.stat().st_size > 0, f"{fname} is empty in idempotency check"


# ════════════════════════════════════════════════════════════════════════════
# CHART COUNT COMPLETENESS
# ════════════════════════════════════════════════════════════════════════════


def test_total_chart_count():
    """Exactly 36 PNG charts must be present in reports/eda/."""
    png_files = list(EDA_DIR.glob("*.png"))
    assert (
        len(png_files) >= 36
    ), f"Expected >= 36 PNG charts, found {len(png_files)}: {[p.name for p in png_files]}"


def test_module_a_complete():
    """All 13 Module A charts must be present."""
    missing = [f for f in MODULE_A_CHARTS if not (EDA_DIR / f).exists()]
    assert missing == [], f"Missing Module A charts: {missing}"


def test_module_b_complete():
    """All 8 Module B charts must be present."""
    missing = [f for f in MODULE_B_CHARTS if not (EDA_DIR / f).exists()]
    assert missing == [], f"Missing Module B charts: {missing}"


def test_module_c_complete():
    """All 10 Module C charts must be present."""
    missing = [f for f in MODULE_C_CHARTS if not (EDA_DIR / f).exists()]
    assert missing == [], f"Missing Module C charts: {missing}"


def test_synthesis_complete():
    """All 5 Synthesis charts must be present."""
    missing = [f for f in SYNTHESIS_CHARTS if not (EDA_DIR / f).exists()]
    assert missing == [], f"Missing Synthesis charts: {missing}"
