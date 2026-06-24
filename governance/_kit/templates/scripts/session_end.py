"""Write governance/SESSION_END.md as a handoff for the next session.

Pre-fills structure; the agent fills in free-text answers before committing.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_END_PATH = REPO_ROOT / "governance" / "SESSION_END.md"

TEMPLATE = """# Session End — {date}

## Findings touched

<!-- List F-IDs and before -> after status -->

- F-NNN: open -> closed

## ADRs added

<!-- Path + 1-line summary, or "none" -->

- none

## Invariants installed

<!-- Script/test paths added or modified -->

- scripts/check_xxx.py
- tests/governance/test_fxxx_*.py

## Open questions for next session

<!-- Things you couldn't resolve; surface them so the next session sees them -->

-

## Recommended next-finding priority

<!-- Which F-NNN should the next session tackle first, and why -->

-

## Notes

<!-- Anything else worth preserving in the durable record -->

-
"""


def main() -> int:
    SESSION_END_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SESSION_END_PATH.exists():
        print(
            f"[session_end] {SESSION_END_PATH.relative_to(REPO_ROOT)} already exists — "
            f"edit it directly instead of overwriting.",
            file=sys.stderr,
        )
        return 1
    SESSION_END_PATH.write_text(TEMPLATE.format(date=datetime.now(UTC).strftime("%Y-%m-%d")))
    print(f"[session_end] wrote {SESSION_END_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
