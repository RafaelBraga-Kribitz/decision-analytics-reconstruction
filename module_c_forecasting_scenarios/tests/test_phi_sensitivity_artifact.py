"""Phi transparency-proxy sensitivity artifact (IMP-C02 / audit C4, C6).

`data/transparency.py:compute_phi_transparency`'s constants are a documented
heuristic, not fit against realized poll accuracy — IMP-C02 requires a
published sensitivity analysis bounding the exposure instead. These tests
lock in: the pure-arithmetic sigma_obs table is deterministic (fast lane),
and (slow lane, real MCMC) the full script — including its MC_FAST posterior
refits — runs end-to-end and produces the committed artifact.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_MODULE_ROOT = Path(__file__).resolve().parents[1]
_REPORTS_DIR = _MODULE_ROOT / "reports"


def _import_generator():  # type: ignore[no-untyped-def]
    if str(_REPORTS_DIR) not in sys.path:
        sys.path.insert(0, str(_REPORTS_DIR))
    return importlib.import_module("generate_phi_sensitivity")


def test_sigma_obs_table_is_deterministic() -> None:
    gen = _import_generator()
    a = gen._sigma_obs_table()
    b = gen._sigma_obs_table()
    assert a == b


def test_sigma_obs_table_covers_every_pillar_count_and_ficha_state() -> None:
    gen = _import_generator()
    rows = gen._sigma_obs_table()
    seen = {(row["has_ficha"], row["n_ok"]) for row in rows}
    expected = {(has_ficha, n_ok) for has_ficha in (False, True) for n_ok in (0, 1, 2, 3)}
    assert seen == expected


def test_sigma_obs_respects_clip_bounds() -> None:
    """sigma_obs must stay within [1.0, 25.0] pp regardless of perturbation."""
    gen = _import_generator()
    rows = gen._sigma_obs_table()
    for row in rows:
        for key, value in row.items():
            if isinstance(key, str) and key.startswith("sigma_obs_") and "delta" not in key:
                assert 1.0 <= value <= 25.0, f"{key}={value} out of [1.0, 25.0] pp bounds"


def test_phi_formula_matches_production_compute_phi_transparency() -> None:
    """The script's parameterized reimplementation must agree with production at baseline."""
    gen = _import_generator()
    from module_c_forecasting_scenarios.data.transparency import compute_phi_transparency

    for has_ficha in (False, True):
        for sample_size_known in (False, True):
            for mode_known in (False, True):
                # field_window_known is passed as True at the cleaning-pipeline call
                # site regardless of its actual value (see docstring in
                # generate_phi_sensitivity._phi_column_under_constants) — reproduce
                # that here rather than the raw field_window_known bit.
                n_ok = sum([sample_size_known, True, mode_known])
                expected = compute_phi_transparency(has_ficha, sample_size_known, True, mode_known)
                actual = gen._phi_formula(n_ok, has_ficha, gen.BASELINE_CONSTANTS)
                assert actual == pytest.approx(expected)


def test_committed_artifact_exists_and_documents_calibration_status() -> None:
    md_path = _REPORTS_DIR / "phi_sensitivity.md"
    assert md_path.exists(), "run generate_phi_sensitivity.py to create the artifact"
    text = md_path.read_text(encoding="utf-8")
    assert "heuristic" in text.lower()
    assert "sigma_obs" in text


@pytest.mark.slow
def test_full_script_runs_and_produces_posterior_deltas(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: refits the model at MC_FAST fidelity under phi perturbation.

    Marked slow (like every other test in this suite that calls pm.sample)
    even though MC_FAST keeps it to a few seconds — consistent with the
    module's convention of gating direct-fit tests behind `-m slow`.
    """
    monkeypatch.setenv("MC_FAST", "1")
    gen = _import_generator()
    out_md = tmp_path / "phi.md"
    monkeypatch.setattr(gen, "OUT_MD", out_md)
    rc = gen.main()
    assert rc == 0
    assert out_md.exists()
    text = out_md.read_text(encoding="utf-8")
    assert "Posterior-summary delta" in text
