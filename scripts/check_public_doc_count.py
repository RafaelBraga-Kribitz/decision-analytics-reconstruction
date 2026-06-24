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
    "maintainer/",
)

OPERATOR_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "docs/INDEX.md",
    "governance/SESSION_END.md",
    "governance/SESSION_HANDOUT.md",
    "governance/Truth_and_rebuild_sprint.md",
    "governance/chart_audit_completion_sprint.md",
    # Gate-evidence trail consumed by test_architecture_module_c_surface, not
    # reviewer-facing narrative.
    "module_c_forecasting_scenarios/reports/C_research_proof_table.md",
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
