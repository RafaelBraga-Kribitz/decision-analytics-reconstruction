"""Verify PROJECT_CHARTER.md stays under 200 lines (scannable budget).

The Charter is the SSOT but only useful if it remains scannable. Once it
grows past 200 lines, contributors stop reading it and parallel docs
(REQUIREMENTS.md, SRS.md, ROADMAP.md) start appearing. This gates that.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

CHARTER = REPO_ROOT / "PROJECT_CHARTER.md"
MAX_LINES = 200


def main() -> int:
    if not CHARTER.exists():
        return gate(
            "F-CHARTER-SIZE", "check_charter_size.py", False,
            "PROJECT_CHARTER.md missing",
        )
    lines = CHARTER.read_text().count("\n") + 1
    if lines > MAX_LINES:
        return gate(
            "F-CHARTER-SIZE", "check_charter_size.py", False,
            f"PROJECT_CHARTER.md is {lines} lines (max {MAX_LINES})",
        )
    return gate(
        "F-CHARTER-SIZE", "check_charter_size.py", True,
        f"PROJECT_CHARTER.md is {lines}/{MAX_LINES} lines",
    )


if __name__ == "__main__":
    sys.exit(main())
