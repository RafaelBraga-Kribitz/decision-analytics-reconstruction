"""Golden-metric CI gates (F-040).

Asserts that the regenerated pipeline reproduces the canonical numbers
recorded in ``reports/golden_metrics.json`` and that the A->B->C data
handshakes carry real (non-zero, correctly-provenanced) values.

Skips cleanly when pipeline artifacts are absent (e.g. fresh clone before
``make pipeline-full``); once artifacts exist the gates are strict.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
GOLDEN_PATH = ROOT / "reports" / "golden_metrics.json"

REL_TOL = 0.005  # 0.5% — covers float accumulation across re-runs, not model drift

B_MANIFEST = DATA / "module_b" / "run_manifest_baseline.json"
MC_DRAWS = DATA / "module_c" / "run_all" / "mc" / "monte_carlo_draws.parquet"
MC_MANIFEST = DATA / "module_c" / "run_all" / "mc" / "scenario_run_manifest.json"
TRACKING_MANIFEST = DATA / "module_c" / "run_all" / "tracking" / "run_tracking_manifest.json"


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"pipeline artifact not present (run `make pipeline-full`): {path}")
    return path


@pytest.fixture(scope="module")
def golden() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.skip("reports/golden_metrics.json missing — run scripts/generate_golden_metrics.py")
    return json.loads(GOLDEN_PATH.read_text())


@pytest.fixture(scope="module")
def b_manifest() -> dict:
    return json.loads(_require(B_MANIFEST).read_text())


def _close(actual: float, expected: float, rel: float = REL_TOL) -> bool:
    if expected == 0:
        return abs(actual) < 1e-9
    return abs(actual - expected) / abs(expected) <= rel


# ── Module B gates ───────────────────────────────────────────────────────────


def test_b_solver_optimal(b_manifest):
    assert b_manifest["solver_status"] == "OPTIMAL"


def test_b_provenance_includes_module_a(b_manifest):
    """A->B handshake: features must carry MODULE_A provenance, not pure priors."""
    assert "MODULE_A" in b_manifest["provenance"], (
        f"Module B ran without Module A artifacts (provenance={b_manifest['provenance']!r}); "
        "the A->B ingestion link is broken"
    )


def test_b_objective_identity(b_manifest):
    """Optimizer objective must match reported persuasion contacts (F-037)."""
    objective = b_manifest["lp_diagnostics"]["objective_value"]
    reported = b_manifest["total_persuasion_contacts"]
    assert _close(objective, reported), (
        f"objective={objective:.1f} vs reported={reported:.1f} diverge by "
        f"{abs(objective - reported) / reported:.2%} (> {REL_TOL:.1%})"
    )


def test_b_golden_reproduction(golden, b_manifest):
    g = golden["module_b"]
    assert b_manifest["row_count"] == g["row_count"]
    assert _close(b_manifest["total_budget_usd"], g["total_budget_usd"])
    assert _close(b_manifest["total_persuasion_contacts"], g["total_persuasion_contacts"])
    lift = b_manifest["baseline_comparison"]["efficiency_vs_department_uniform_naive"][
        "linearized_lift_pct_milp_vs_naive"
    ]
    assert _close(lift, g["linearized_lift_pct_milp_vs_naive"], rel=0.02)


# ── B -> C handshake gates ───────────────────────────────────────────────────


def test_mc_allocation_input_wired():
    """scenario_run_manifest must record a real allocation parquet, not null."""
    manifest = json.loads(_require(MC_MANIFEST).read_text())
    alloc = manifest.get("allocation_input")
    assert alloc, (
        "Monte Carlo ran with allocation_input=null — the B->C handshake is "
        "not wired (run module_c with --allocation-parquet)"
    )


def test_mc_alloc_contacts_positive():
    """The silent-zero failure mode: contacts must be strictly positive."""
    mc = pd.read_parquet(_require(MC_DRAWS))
    assert (mc["alloc_mean_persuasion_contacts"] > 0).all(), (
        "alloc_mean_persuasion_contacts contains zeros — Module B allocation "
        "did not reach the Monte Carlo engine"
    )


def test_mc_golden_reproduction(golden):
    mc = pd.read_parquet(_require(MC_DRAWS))
    g = golden["module_c"]
    assert len(mc) == g["mc_n_draws"]
    assert _close(
        float(mc["alloc_mean_persuasion_contacts"].mean()),
        g["mc_alloc_mean_persuasion_contacts"],
    )


# ── Module C tracking gates ──────────────────────────────────────────────────


def test_c_tracking_golden_reproduction(golden):
    tracking = json.loads(_require(TRACKING_MANIFEST).read_text())
    g = golden["module_c"]
    assert tracking["calibration_series"] == g["calibration_series"]
    assert tracking["m_star_pp"] == pytest.approx(g["m_star_pp"])
    assert tracking["outcome_event_date"] == g["outcome_event_date"]
    assert tracking["n_tracking_waves"] == g["n_tracking_waves"]


# ── SSOT: no two published artifacts may disagree on the same quantity (F-072) ──

HOUSE_EFFECTS = DATA / "module_c" / "run_all" / "tracking" / "posterior_house_effects.parquet"
EDA_REPORT = ROOT / "reports" / "eda" / "eda_report.md"
_GEN = ROOT / "reports" / "eda" / "generate_eda.py"
_NB = ROOT / "reports" / "eda" / "build_notebook.py"
# Stale hardcoded house-effect literals that previously diverged between artifacts.
_BANNED_HE = re.compile(
    r"(ATI/Snead has a [+\-−]?5\.1|~\+1\.5 pp|\(-2\.1 pp\)|\+3\.8 pp\)\. CAPLI)"
)


def test_house_effect_prose_single_sourced() -> None:
    """Static SSOT gate: both generators must DERIVE house-effect prose from the
    parquet (reference _he_* variables) and hardcode no contradictory pp literal."""
    gen, nb = _GEN.read_text(encoding="utf-8"), _NB.read_text(encoding="utf-8")
    assert (
        "_he_neg_name" in gen and "_he_pos_name" in gen
    ), "generate_eda.py hardcodes house effects"
    assert "_he_hi_name" in nb and "_he_lo_name" in nb, "build_notebook.py hardcodes house effects"
    assert not _BANNED_HE.search(gen), "generate_eda.py still has a stale house-effect literal"
    assert not _BANNED_HE.search(nb), "build_notebook.py still has a stale house-effect literal"


def test_house_effect_report_matches_parquet() -> None:
    """Runtime SSOT gate: the EDA report's house-effect number must equal the
    canonical parquet — two artifacts cannot report the same quantity differently."""
    he = pd.read_parquet(_require(HOUSE_EFFECTS))
    if not EDA_REPORT.exists():
        pytest.skip("eda_report.md not generated yet (run reports/eda/generate_eda.py)")
    canonical_min = float(he["house_effect_posterior_mean"].min())
    text = EDA_REPORT.read_text(encoding="utf-8").replace("−", "-")
    m = re.search(r"largest negative house effect \((-?\d+\.\d+) pp\)", text)
    assert m, "could not find the derived house-effect sentence in eda_report.md"
    reported = float(m.group(1))
    # prose is rounded to 1 dp; allow the rounding plus a hair of float noise.
    assert abs(reported - canonical_min) <= 0.06, (
        f"eda_report.md house effect {reported} pp disagrees with parquet "
        f"{canonical_min:.1f} pp — published artifacts diverge"
    )
