#!/usr/bin/env python3
"""Verification script for F-071: the MC contacts figure plots a varying quantity.

AUD dead-B→C-metric: alloc_mean_persuasion_contacts is a single scalar (mean of
persuasion_adjusted_contacts) broadcast to every Monte Carlo draw, so the published
"Monte Carlo scenario distribution — persuasion-adjusted contacts" figure was a flat
line. The shock never propagated to the allocation outcome, despite the contract
saying it should.

Closure invariant (static source checks):
  scenarios/monte_carlo.py — defines _scenario_adjusted_contacts and emits a
        per-draw ``scenario_adjusted_persuasion_contacts`` column.
  schema_contracts/monte_carlo_draws.yaml — declares that field.
  reports/eda/generate_eda.py — a chart plots scenario_adjusted_persuasion_contacts
        (not the flat raw mean) and documents the mean-vs-total unit difference.
  portfolio/quarto/post_mortem.qmd — the deployed MC figure plots
        scenario_adjusted_persuasion_contacts (not alloc_mean as a distribution).
  tests — a std>0 test guards that the plotted metric varies within buckets.

The runtime proof (groupby(scenario_bucket).std() > 0) is
test_scenario_adjusted_contacts_varies_within_buckets in test_bc_handshake.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MC = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "scenarios"
    / "monte_carlo.py"
)
CONTRACT = REPO_ROOT / "schema_contracts" / "monte_carlo_draws.yaml"
GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
POSTMORTEM = (
    REPO_ROOT / "module_c_forecasting_scenarios" / "portfolio" / "quarto" / "post_mortem.qmd"
)
TEST = REPO_ROOT / "module_c_forecasting_scenarios" / "tests" / "test_bc_handshake.py"

FIELD = "scenario_adjusted_persuasion_contacts"
FIG_LABEL = "fig-mc-scenarios"


def _mc_figure_block(qmd: str) -> str:
    """Return the post_mortem.qmd source between fig-mc-scenarios and the next cell."""
    start = qmd.find(f"#| label: {FIG_LABEL}")
    if start < 0:
        return ""
    end = qmd.find("```{python}", start + 1)
    if end < 0:
        return qmd[start:]
    return qmd[start:end]


def _check_mc_sources() -> list[str]:
    gaps: list[str] = []
    mc = MC.read_text(encoding="utf-8")
    if "_scenario_adjusted_contacts" not in mc or FIELD not in mc:
        gaps.append("monte_carlo.py does not emit scenario_adjusted_persuasion_contacts")
    if FIELD not in CONTRACT.read_text(encoding="utf-8"):
        gaps.append("monte_carlo_draws.yaml does not declare scenario_adjusted_persuasion_contacts")
    return gaps


def _check_generator_and_test() -> list[str]:
    gaps: list[str] = []
    gen = GENERATOR.read_text(encoding="utf-8")
    if FIELD not in gen:
        gaps.append("generate_eda.py never plots scenario_adjusted_persuasion_contacts")
    if "expected_contacts across all cells" not in gen:
        gaps.append("generate_eda.py does not document the mean-vs-total contacts unit difference")
    if "scenario_adjusted_contacts_varies" not in TEST.read_text(encoding="utf-8"):
        gaps.append("no std>0 test that the plotted MC contacts metric varies within buckets")
    return gaps


def _check_postmortem_mc_figure() -> list[str]:
    gaps: list[str] = []
    mc_fig = _mc_figure_block(POSTMORTEM.read_text(encoding="utf-8"))
    if not mc_fig:
        gaps.append(f"post_mortem.qmd missing {FIG_LABEL} MC figure block")
        return gaps
    if FIELD not in mc_fig:
        gaps.append("post_mortem.qmd MC figure does not plot scenario_adjusted_persuasion_contacts")
    if 'y="alloc_mean_persuasion_contacts"' in mc_fig:
        gaps.append("post_mortem.qmd MC figure still plots flat alloc_mean as a distribution")
    return gaps


def main() -> int:
    for path in (MC, CONTRACT, GENERATOR, POSTMORTEM, TEST):
        if not path.is_file():
            return gate("F-071", Path(__file__).name, False, f"missing {path.name}")
    gaps = _check_mc_sources() + _check_generator_and_test() + _check_postmortem_mc_figure()

    detail = (
        "; ".join(gaps)
        if gaps
        else (
            "MC contacts figure plots per-draw varying metric in EDA and post_mortem; "
            "std>0 tested"
        )
    )
    return gate("F-071", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
