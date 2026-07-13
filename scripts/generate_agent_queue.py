"""Generate .claude/agent_queue.json from live GitHub issue state.

The queue lists every open issue labeled ``status:claude-ready``, sorted by
priority then effort. It is generated state, never committed (issue #94: the
committed copy went stale and listed closed issues as ready). Agents run
this at session start when the governance findings queue is empty; the
queue-sync workflow runs the same script so builder and CI cannot drift.

Requires the ``gh`` CLI authenticated against the repository.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = REPO_ROOT / ".claude" / "agent_queue.json"
DEFAULT_REPO = "RafaelBraga-Kribitz/decision-analytics-reconstruction"

PRIORITY_ORDER = {"p0": 0, "p1": 1, "p2": 2}
EFFORT_ORDER = {"high": 0, "medium": 1, "low": 2}


def _fetch_ready_issues(repo: str) -> list[dict]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--search",
        "is:open label:status:claude-ready",
        "--json",
        "number,title,labels,body",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"gh issue list failed (rc={proc.returncode}): {proc.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(proc.stdout) if proc.stdout.strip() else []


def _label_value(labels: set[str], prefix: str, default: str) -> str:
    for label in labels:
        if label.startswith(prefix):
            return label.split(":", 1)[1]
    return default


def _acceptance_criteria(body: str) -> list[str]:
    criteria: list[str] = []
    in_acceptance = False
    for line in body.split("\n"):
        if "acceptance criteria" in line.lower():
            in_acceptance = True
            continue
        if not in_acceptance:
            continue
        if line.startswith(("- [ ]", "- [x]")):
            text = line.split("]", 1)[1].strip() if "]" in line else ""
            if text:
                criteria.append(text)
        elif line.startswith("##"):
            break
    return criteria


def _build_task(issue: dict, repo: str) -> dict:
    labels = {label["name"] for label in issue.get("labels", [])}
    return {
        "number": issue["number"],
        "title": issue["title"],
        "priority": _label_value(labels, "priority:", "p2"),
        "effort": _label_value(labels, "effort:", "unknown"),
        "skills": sorted(label.split(":", 1)[1] for label in labels if label.startswith("skill:")),
        "status": "ready",
        "acceptance_criteria": _acceptance_criteria(issue.get("body") or ""),
        "url": f"https://github.com/{repo}/issues/{issue['number']}",
    }


def main() -> int:
    repo = os.environ.get("GH_REPO", DEFAULT_REPO)
    tasks = [_build_task(issue, repo) for issue in _fetch_ready_issues(repo)]
    tasks.sort(
        key=lambda t: (
            PRIORITY_ORDER.get(t["priority"], 3),
            EFFORT_ORDER.get(t["effort"], 3),
        )
    )
    queue = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ready_tasks": tasks,
    }
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    print(f"[generate_agent_queue] wrote {QUEUE_PATH.relative_to(REPO_ROOT)}")
    print(f"[generate_agent_queue]   ready_tasks: {len(tasks)}")
    for task in tasks[:5]:
        print(f"  #{task['number']}: {task['title']} ({task['priority']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
