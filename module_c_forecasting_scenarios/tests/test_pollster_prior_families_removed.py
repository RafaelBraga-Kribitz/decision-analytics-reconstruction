"""IMP-C02 resolution (b): pollster_prior_families.yaml is deleted, not wired.

`config/pollster_prior_families.yaml` defined per-pollster-family PyMC
hyperparameters that were never consumed by `fit_tracking_hierarchical` — a
config that looks wired but is a dead passthrough label. Resolution (b) was
chosen: delete the config and document the pooled-prior exchangeability
decision in METHODOLOGY.md, rather than wire per-family priors into the model.
"""

from __future__ import annotations

from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _MODULE_ROOT.parent
# Only code/config is scanned for "no reference" — METHODOLOGY.md is REQUIRED
# to name the deleted file (it documents the deletion decision per IMP-C02's
# acceptance criteria), so markdown is intentionally excluded here.
_SCAN_SUFFIXES = (".py", ".yaml", ".yml")


def test_pollster_prior_families_yaml_does_not_exist() -> None:
    assert not (_MODULE_ROOT / "config" / "pollster_prior_families.yaml").exists()


def test_no_code_or_config_references_pollster_prior_families() -> None:
    """Grep-style: no .py/.yaml/.yml under module_c_forecasting_scenarios references it."""
    this_file = Path(__file__).resolve()
    hits: list[str] = []
    for path in _MODULE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in _SCAN_SUFFIXES:
            continue
        if "__pycache__" in path.parts or path.resolve() == this_file:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "pollster_prior_families" in text:
            hits.append(str(path.relative_to(_REPO_ROOT)))
    assert hits == [], f"pollster_prior_families still referenced in: {hits}"


def test_hierarchical_module_fits_a_single_pooled_house_prior() -> None:
    """The model actually fit uses one pooled sigma_house, not per-family priors."""
    src = (
        _MODULE_ROOT
        / "src"
        / "module_c_forecasting_scenarios"
        / "models"
        / "tracking"
        / "hierarchical.py"
    ).read_text(encoding="utf-8")
    assert 'pm.HalfNormal("sigma_house"' in src
    assert "student_nu" not in src
    assert "house_sigma_pp" not in src
    assert "house_loc_pp" not in src


def test_methodology_documents_exchangeability_as_deliberate_decision() -> None:
    methodology = (_MODULE_ROOT / "METHODOLOGY.md").read_text(encoding="utf-8")
    low = methodology.lower()
    assert "exchangeable" in low
    assert "deliberate modeling decision" in low or "deliberate" in low
    assert "pollster_prior_families.yaml" in methodology
    assert "deleted" in low
