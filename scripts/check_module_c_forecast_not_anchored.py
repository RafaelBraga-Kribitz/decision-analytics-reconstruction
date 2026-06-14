#!/usr/bin/env python3
"""Verification script for F-069: the public track is an honest retrodiction.

AUD forecast-vs-retrodiction: the tracking model adds a soft outcome anchor in the
likelihood (Normal("outcome_anchor", mu=mu[-1], observed=m_star_pp)). The published
"Daily Posterior Forecast Track" is that anchored series — it conditions on the very
outcome it appears to predict, so it is a retrospective reconciliation, not a
forecast. The genuinely out-of-sample series is walk-forward validation, which must
never see m_star.

Closure invariant (static source checks):
  validation/walk_forward.py  — the fit call explicitly passes ``m_star_pp=None``.
  reports/eda/generate_eda.py — the C1 panel is labelled a retrospective
        reconciliation that conditions on the outcome anchor and is NOT an
        out-of-sample forecast.
  tests/test_walk_forward.py  — a ``never_anchors`` test guards the guarantee.

The runtime proof (walk-forward never passes m_star to the fit) is the spy test
test_walk_forward_never_anchors_on_outcome.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MOD = REPO_ROOT / "module_c_forecasting_scenarios" / "src" / "module_c_forecasting_scenarios"
WALK = MOD / "validation" / "walk_forward.py"
GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
TEST = REPO_ROOT / "module_c_forecasting_scenarios" / "tests" / "test_walk_forward.py"


def _walk_gaps(src: str) -> list[str]:
    # The walk-forward fit must explicitly opt out of the anchor.
    if not re.search(r"fit_tracking_hierarchical\(.*?m_star_pp\s*=\s*None", src, re.S):
        return ["walk_forward.py does not explicitly pass m_star_pp=None to the fit"]
    return []


def _c1_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    low = src.lower()
    if "retrospective reconciliation" not in low:
        gaps.append("C1 is not labelled a 'retrospective reconciliation'")
    if "conditions on the verified outcome anchor" not in low:
        gaps.append("C1 does not disclose it conditions on the verified outcome anchor")
    if "not an out-of-sample forecast" not in low:
        gaps.append("C1 does not state it is not an out-of-sample forecast")
    return gaps


def main() -> int:
    for path in (WALK, GENERATOR, TEST):
        if not path.is_file():
            return gate("F-069", Path(__file__).name, False, f"missing {path.name}")
    gaps = _walk_gaps(WALK.read_text(encoding="utf-8"))
    gaps += _c1_gaps(GENERATOR.read_text(encoding="utf-8"))
    if "never_anchors" not in TEST.read_text(encoding="utf-8"):
        gaps.append("test_walk_forward.py has no never_anchors guard test")
    detail = (
        "; ".join(gaps)
        if gaps
        else "walk-forward is anchor-free; C1 is an honest retrodiction with the guarantee tested"
    )
    return gate("F-069", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
