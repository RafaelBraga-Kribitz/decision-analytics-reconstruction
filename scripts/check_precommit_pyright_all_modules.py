#!/usr/bin/env python3
"""Verify pre-commit pyright covers all module src roots."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"
REQUIRED = (
    "module_a_population_segmentation/src",
    "module_b_resource_allocation/src",
    "module_c_forecasting_scenarios/src",
)


def main() -> int:
    data = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    local = next(r for r in data["repos"] if r.get("repo") == "local")
    pyright = next(h for h in local["hooks"] if h.get("id") == "pyright")
    entry = str(pyright.get("entry", ""))
    missing = [path for path in REQUIRED if path not in entry]
    return gate(
        "F-005",
        Path(__file__).name,
        not missing,
        "pre-commit pyright missing: " + ", ".join(missing),
    )


if __name__ == "__main__":
    sys.exit(main())
