"""Verify CLAUDE.md exists and references the governance contract.

If CLAUDE.md is missing or has been hollowed out, the next agent will not run
`make session-start` and will re-derive state from prose. This script gates
that drift by requiring the key references stay present.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

REQUIRED_PHRASES = (
    "make session-start",
    "governance/AUDIT_PROCEDURE.md",
    "governance/findings",
    "verification_script",
)


def main() -> int:
    if not CLAUDE_MD.exists():
        return gate("F-CLAUDE-MD", "check_claude_md.py", False, "CLAUDE.md missing")
    text = CLAUDE_MD.read_text()
    missing = [p for p in REQUIRED_PHRASES if p not in text]
    if missing:
        return gate(
            "F-CLAUDE-MD", "check_claude_md.py", False,
            f"CLAUDE.md missing required phrases: {', '.join(missing)}",
        )
    return gate(
        "F-CLAUDE-MD", "check_claude_md.py", True,
        f"CLAUDE.md references all {len(REQUIRED_PHRASES)} required contract phrases",
    )


if __name__ == "__main__":
    sys.exit(main())
