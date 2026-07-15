#!/usr/bin/env python3
"""Verify the reviewer-facing Markdown surface stays compact."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MAX_PUBLIC_MD = 20

OPERATOR_PREFIXES = (
    ".claude/",
    ".cursor/",
    ".github/",
    "docs/registry/",
    "governance/_kit/",
    "governance/adrs/",
    # Improvement-plan specs are agent-facing work-queue artifacts (same class
    # as the sprint docs listed in OPERATOR_FILES), not reviewer narrative.
    "governance/improvement_plan/",
    "maintainer/",
)

OPERATOR_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    # Relocated agent instructions (issue #104); root files are pointer stubs.
    "docs/agents/AGENTS.md",
    "docs/agents/GEMINI.md",
    "docs/INDEX.md",
    "governance/SESSION_END.md",
    "governance/SESSION_HANDOUT.md",
    "governance/Truth_and_rebuild_sprint.md",
    "governance/chart_audit_completion_sprint.md",
    # Gate-evidence trail consumed by test_architecture_module_c_surface, not
    # reviewer-facing narrative.
    "module_c_forecasting_scenarios/reports/C_research_proof_table.md",
    # Gate-evidence trail for the IMP-A03 clustering selection (issue #55) —
    # cited by model_params.yaml and the segmentation model card, not
    # reviewer-facing narrative.
    "reports/module_a/k_sweep_2026-07-09.md",
    # Generated constraint x contract matrix (issue #64); registry lists it as
    # internal/generated, freshness-gated by tests/test_conformance_matrix.py.
    "schema_contracts/CONFORMANCE_MATRIX.md",
    # Generated sensitivity-analysis evidence artifacts (IMP-C04 issue #62,
    # IMP-C02 issue #61) — gate-evidence trails consumed by
    # test_shock_herding_sensitivity_artifact.py / test_phi_sensitivity_artifact.py,
    # not reviewer-facing narrative.
    "module_c_forecasting_scenarios/reports/shock_herding_sensitivity.md",
    "module_c_forecasting_scenarios/reports/phi_sensitivity.md",
    # Reference-data schema for battleground σ estimator — data contract, not narrative.
    "data/reference/battleground/README.md",
    # GeoJSON provenance note for ADM1 boundaries (F-081) — data contract, not narrative.
    "module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/geo/paraguay_departments.SOURCE.md",
    # Committed LOO walk-forward evidence (issue #97) — summarized in VALIDATION.md.
    "reports/module_c/walk_forward_loo_report.md",
    # F-082 battleground ceiling investigation — gate-evidence, not reviewer narrative.
    "reports/module_c/battleground_investigation/INVESTIGATION_REPORT.md",
    "reports/module_c/battleground_investigation/scratch/battleground/anchor_comparison.md",
}


def _tracked_markdown() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def _is_public_markdown(path: str) -> bool:
    if path in OPERATOR_FILES:
        return False
    return not any(path.startswith(prefix) for prefix in OPERATOR_PREFIXES)


def main() -> int:
    public_docs = [path for path in _tracked_markdown() if _is_public_markdown(path)]
    count = len(public_docs)
    if count <= MAX_PUBLIC_MD:
        return gate(
            "F-032",
            Path(__file__).name,
            True,
            f"public_markdown={count}/{MAX_PUBLIC_MD}",
        )
    sample = ", ".join(public_docs[:8])
    return gate(
        "F-032",
        Path(__file__).name,
        False,
        f"public_markdown={count}/{MAX_PUBLIC_MD}; sample={sample}",
    )


if __name__ == "__main__":
    sys.exit(main())
