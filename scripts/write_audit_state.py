"""Write governance/AUDIT_STATE.json from the canonical governance/ inputs.

Reads:
  governance/findings/F-*.yaml
  governance/migrations/*.yaml

Writes:
  governance/AUDIT_STATE.json — single machine-readable snapshot consumed by
  `make session-start` to produce the session handout, and by CI for the
  Adversary job.

This script is the *only* writer of AUDIT_STATE.json. Hand-editing is forbidden.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GOV = REPO_ROOT / "governance"
FINDINGS_DIR = GOV / "findings"
MIGRATIONS_DIR = GOV / "migrations"
STATE_PATH = GOV / "AUDIT_STATE.json"

VALID_FINDING_STATUSES = {
    "open",
    "in_progress",
    "closed",
    "closed_historical",
    "wont_fix",
}
VALID_MIGRATION_STATUSES = {
    "not_started",
    "in_progress",
    "complete",
    "abandoned",
}


def _load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],  # noqa: S607
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def collect_findings() -> tuple[list[dict], list[str]]:
    findings: list[dict] = []
    errors: list[str] = []
    if not FINDINGS_DIR.exists():
        return findings, errors
    for path in sorted(FINDINGS_DIR.glob("F-*.yaml")):
        if path.name == "F-TEMPLATE.yaml":
            continue
        try:
            data = _load_yaml(path)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse error: {exc}")
            continue
        for required in ("id", "title", "category", "kind", "status", "opened_at"):
            if required not in data:
                errors.append(f"{path}: missing required field '{required}'")
        status = data.get("status")
        if status not in VALID_FINDING_STATUSES:
            errors.append(f"{path}: invalid status '{status}'")
        if status == "wont_fix" and not data.get("wont_fix_reason"):
            errors.append(f"{path}: status=wont_fix requires wont_fix_reason")
        findings.append(
            {
                "id": data.get("id"),
                "title": data.get("title"),
                "category": data.get("category"),
                "kind": data.get("kind"),
                "status": data.get("status"),
                "opened_at": str(data.get("opened_at")),
                "closed_at": (
                    str(data["closed_at"]) if data.get("closed_at") is not None else None
                ),
                "verification_script": data.get("verification_script"),
                "path": str(path.relative_to(REPO_ROOT)),
            }
        )
    return findings, errors


def collect_migrations() -> tuple[list[dict], list[str]]:
    migrations: list[dict] = []
    errors: list[str] = []
    if not MIGRATIONS_DIR.exists():
        return migrations, errors
    for path in sorted(MIGRATIONS_DIR.glob("*.yaml")):
        if path.name == "MIGRATION_TEMPLATE.yaml":
            continue
        try:
            data = _load_yaml(path)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML parse error: {exc}")
            continue
        status = data.get("status")
        if status not in VALID_MIGRATION_STATUSES:
            errors.append(f"{path}: invalid status '{status}'")
        migrations.append(
            {
                "name": data.get("name"),
                "status": data.get("status"),
                "started_at": str(data.get("started_at", "unknown")),
                "max_days_in_progress": data.get("max_days_in_progress"),
                "linked_finding": data.get("linked_finding"),
                "path": str(path.relative_to(REPO_ROOT)),
            }
        )
    return migrations, errors


def summarize(findings: list[dict], migrations: list[dict]) -> dict:
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for f in findings:
        by_status[f["status"]] = by_status.get(f["status"], 0) + 1
        if f["status"] in {"open", "in_progress"}:
            by_category[f["category"]] = by_category.get(f["category"], 0) + 1
    return {
        "findings_total": len(findings),
        "findings_open": by_status.get("open", 0),
        "findings_in_progress": by_status.get("in_progress", 0),
        "findings_closed": by_status.get("closed", 0),
        "findings_closed_historical": by_status.get("closed_historical", 0),
        "findings_wont_fix": by_status.get("wont_fix", 0),
        "open_by_category": by_category,
        "migrations_total": len(migrations),
        "migrations_in_progress": sum(1 for m in migrations if m["status"] == "in_progress"),
    }


def main() -> int:
    findings, ferrors = collect_findings()
    migrations, merrors = collect_migrations()
    summary = summarize(findings, migrations)
    state = {
        "writer": "scripts/write_audit_state.py",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_head_sha": _git("rev-parse", "HEAD"),
        "summary": summary,
        "findings": findings,
        "migrations": migrations,
        "validation_errors": ferrors + merrors,
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    print(f"[write_audit_state] wrote {STATE_PATH.relative_to(REPO_ROOT)}")
    print(
        f"[write_audit_state]   findings: total={summary['findings_total']} "
        f"open={summary['findings_open']} in_progress={summary['findings_in_progress']} "
        f"closed={summary['findings_closed']} historical={summary['findings_closed_historical']}"
    )
    print(
        f"[write_audit_state]   migrations: total={summary['migrations_total']} "
        f"in_progress={summary['migrations_in_progress']}"
    )
    if state["validation_errors"]:
        print("[write_audit_state] validation errors:", file=sys.stderr)
        for err in state["validation_errors"]:
            print(f"  - {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
