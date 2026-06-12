#!/usr/bin/env python3
"""Verification script for F-044 (Module A model_params wiring honesty)."""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MODEL_PARAMS = REPO_ROOT / "module_a_population_segmentation" / "config" / "model_params.yaml"
REACHABILITY = (
    REPO_ROOT
    / "module_a_population_segmentation"
    / "src"
    / "population_segmentation"
    / "features"
    / "reachability.py"
)

# Documented in model_params header as not yet wired — must stay declared until wired.
UNWIRED_MARKERS = (
    "NOT yet wired",
    "hardcoded",
    "Planned: a config-loading adapter",
)


def main() -> int:
    gaps: list[str] = []
    if not MODEL_PARAMS.is_file():
        gaps.append("missing model_params.yaml")
    else:
        text = MODEL_PARAMS.read_text(encoding="utf-8")
        if not any(m in text for m in UNWIRED_MARKERS):
            gaps.append("model_params.yaml must document unwired keys until loader exists")

    if REACHABILITY.is_file():
        code = REACHABILITY.read_text(encoding="utf-8")
        yaml_path = REPO_ROOT / "module_a_population_segmentation" / "config" / "model_params.yaml"
        if yaml_path.is_file():
            yaml_text = yaml_path.read_text(encoding="utf-8")
            if "0.40" in yaml_text and "0.25" in code and "0.40" not in code:
                gaps.append("reachability weights drift: YAML vs reachability.py")
    else:
        gaps.append("missing reachability.py")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "config wiring documented; no reachability drift"
    return gate("F-044", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
