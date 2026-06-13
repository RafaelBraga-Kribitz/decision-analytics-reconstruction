#!/usr/bin/env python3
"""Verification script for F-054: severe triage rows must be filed, not hidden.

governance/ISSUE_TRIAGE_MASTER.yaml is the unified inventory of every known
issue. Rows graded `reject` or `critical` while still `open_unfiled` are real
defects that the findings queue (and therefore SESSION_HANDOUT) does not
surface — which is how a session can report "queue empty" while serious chart
and inference problems sit unaddressed.

Closure invariant: no row may be `status: open_unfiled` with
`severity: reject|critical`. Each such row must be promoted to a filed finding
(`open_finding`/`verified_closed`) or resolved (`obsolete`/`superseded`/...).
This finding stays OPEN — and the queue stays honestly non-empty — until that
backlog is cleared.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterator

import yaml
from _governance_check import REPO_ROOT, gate

TRIAGE = REPO_ROOT / "governance" / "ISSUE_TRIAGE_MASTER.yaml"
SEVERE = {"reject", "critical"}


def _rows(obj: Any) -> Iterator[dict]:
    if isinstance(obj, dict):
        if "id" in obj and "status" in obj:
            yield obj
        for v in obj.values():
            yield from _rows(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _rows(v)


def main() -> int:
    if not TRIAGE.is_file():
        return gate("F-054", Path(__file__).name, False, "missing ISSUE_TRIAGE_MASTER.yaml")

    doc = yaml.safe_load(TRIAGE.read_text(encoding="utf-8"))
    unfiled = [
        str(r.get("id"))
        for r in _rows(doc)
        if r.get("status") == "open_unfiled" and str(r.get("severity", "")).lower() in SEVERE
    ]

    ok = not unfiled
    detail = (
        f"{len(unfiled)} reject/critical triage row(s) still open_unfiled: "
        + ", ".join(unfiled[:10])
        if unfiled
        else "no reject/critical triage rows remain unfiled"
    )
    return gate("F-054", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
