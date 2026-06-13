#!/usr/bin/env python3
"""Verification script for F-053: win-probability charts must not amplify noise.

Chart-audit batch 1 (governance/ISSUE_TRIAGE_MASTER.yaml, AUD-C8) flagged the
department win-probability charts for zooming the probability axis into a
~0.48–0.52 band, turning sub-1pp deterministic jitter into an apparent
department ranking (a Class-D "correct data, misleading chart" problem).

Closure invariant: no `set_ylim`/`set_xlim` on a win-probability axis in
reports/eda/generate_eda.py may span a band narrower than MIN_AXIS_SPAN around
0.5. Charts must either show the full [0,1] range or a band wide enough that
the spread reads honestly as noise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
# A probability axis tighter than this around 0.5 visually amplifies noise.
MIN_AXIS_SPAN = 0.20
# Numeric-literal set_ylim/set_xlim calls, e.g. set_ylim(0.48, 0.52).
_AXIS_RE = re.compile(r"set_[xy]lim\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)")


def main() -> int:
    if not GENERATOR.is_file():
        return gate("F-053", Path(__file__).name, False, "missing reports/eda/generate_eda.py")

    src = GENERATOR.read_text(encoding="utf-8")
    gaps: list[str] = []
    for m in _AXIS_RE.finditer(src):
        lo, hi = float(m.group(1)), float(m.group(2))
        span = hi - lo
        # Only flag bands that sit around the 0.5 win-probability threshold.
        straddles_half = lo <= 0.5 <= hi
        if straddles_half and span < MIN_AXIS_SPAN:
            line = src.count("\n", 0, m.start()) + 1
            gaps.append(
                f"generate_eda.py:{line}: probability axis {lo}-{hi} "
                f"(span {span:.3f} < {MIN_AXIS_SPAN}) amplifies win-prob noise"
            )

    ok = not gaps
    detail = (
        "; ".join(gaps)
        if gaps
        else "no win-probability chart zooms into a sub-0.20 noise band around 0.5"
    )
    return gate("F-053", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
