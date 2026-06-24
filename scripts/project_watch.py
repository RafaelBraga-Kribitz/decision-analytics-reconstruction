"""L3 trigger surface 3: poll GitHub Project #1 for actionable items.

Lists items carrying `status:claude-ready` that are not already labelled
`agent:queued`, and flags items idle longer than --stale-hours as
`agent:stale`. Used by the cron heartbeat in .github/workflows/governance.yml
and runnable locally via `make project-watch`.

Requires `gh` on PATH and a token with `read:project` (heartbeat) or
`project` (label-mutation mode).

Exit codes:
  0 — ran cleanly (with or without actionable items)
  2 — gh missing, auth failed, or project query failed
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta


def _run_gh(args: list[str]) -> str:
    if shutil.which("gh") is None:
        print("ERROR: gh CLI not on PATH.", file=sys.stderr)
        sys.exit(2)
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: gh {' '.join(args)} failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def _list_items(owner: str, project: int) -> list[dict]:
    raw = _run_gh(
        [
            "project",
            "item-list",
            str(project),
            "--owner",
            owner,
            "--format",
            "json",
            "--limit",
            "200",
        ]
    )
    data = json.loads(raw)
    return data.get("items", [])


def _label_matches(lab: object, label: str) -> bool:
    if isinstance(lab, dict):
        return lab.get("name") == label
    if isinstance(lab, str):
        return lab == label
    return False


def _has_label(item: dict, label: str) -> bool:
    labels = (item.get("labels") or {}).get("nodes") or []
    if isinstance(labels, list) and any(_label_matches(lab, label) for lab in labels):
        return True
    raw = item.get("content") or {}
    if isinstance(raw, dict):
        return any(_label_matches(lab, label) for lab in (raw.get("labels", []) or []))
    return False


def _updated_at(item: dict) -> datetime | None:
    content = item.get("content") or {}
    iso = content.get("updatedAt") or item.get("updatedAt")
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, help="GH owner (user or org)")
    parser.add_argument("--project", required=True, type=int, help="Project number (e.g., 1)")
    parser.add_argument(
        "--stale-hours",
        type=int,
        default=24,
        help="Hours after which an unqueued claude-ready item is flagged stale",
    )
    parser.add_argument(
        "--dispatch",
        action="store_true",
        help="If set, call `gh workflow run governance.yml -f mode=maintainer` for the top item",
    )
    return parser.parse_args()


def _stale_items(ready: list[dict], cutoff: datetime) -> list[dict]:
    out: list[dict] = []
    for item in ready:
        updated = _updated_at(item)
        if updated is not None and updated < cutoff:
            out.append(item)
    return out


def _dispatch_workflow(content: dict) -> None:
    repo = (content.get("repository") or {}).get("nameWithOwner")
    if not repo:
        print("WARNING: could not resolve repository for dispatch; skipping.", file=sys.stderr)
        return
    print(f"→ Dispatching governance.yml in {repo} for mode=maintainer …")
    _run_gh(
        [
            "workflow",
            "run",
            "governance.yml",
            "--repo",
            repo,
            "-f",
            "mode=maintainer",
        ]
    )


def main() -> int:
    args = _parse_args()
    items = _list_items(args.owner, args.project)
    ready = [
        i
        for i in items
        if _has_label(i, "status:claude-ready") and not _has_label(i, "agent:queued")
    ]

    print(f"── project #{args.project} watch ─────────────────────────────")
    print(f"Total items:                {len(items)}")
    print(f"Actionable (claude-ready, not queued): {len(ready)}")

    stale_cutoff = datetime.now(UTC) - timedelta(hours=args.stale_hours)
    stale = _stale_items(ready, stale_cutoff)
    if stale:
        print(f"Stale (> {args.stale_hours} h):           {len(stale)}")
        for item in stale[:5]:
            content = item.get("content") or {}
            print(f"  - #{content.get('number', '?')} {content.get('title', '(no title)')}")

    if not ready:
        print("Nothing to dispatch.")
        return 0

    top = ready[0]
    content = top.get("content") or {}
    print()
    print(f"Top item: #{content.get('number', '?')} {content.get('title', '(no title)')}")
    print(f"URL:      {content.get('url', '?')}")

    if args.dispatch:
        _dispatch_workflow(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
