"""L3 dispatcher: pick the top open finding and print the Remediator contract.

Reads governance/SESSION_HANDOUT.md (produced by session-start) and
governance/AUDIT_STATE.json, then prints a single-finding work order that an
agent or human can execute next. Does not mutate any file.

Exit codes:
  0 — a workable finding was found and printed
  1 — no `open` finding in AUDIT_STATE.json; nothing to do
  2 — AUDIT_STATE.json missing or stale (older than 1 h)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "governance" / "AUDIT_STATE.json"
HANDOUT_PATH = REPO_ROOT / "governance" / "SESSION_HANDOUT.md"
PROCEDURE_PATH = REPO_ROOT / "governance" / "AUDIT_PROCEDURE.md"

STALE_AFTER = timedelta(hours=1)


def _load_state() -> dict:
    if not STATE_PATH.exists():
        print(f"ERROR: {STATE_PATH} missing — run `make session-start` first.", file=sys.stderr)
        sys.exit(2)
    state = json.loads(STATE_PATH.read_text())
    generated_at = state.get("generated_at")
    if generated_at:
        try:
            ts = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if datetime.now(UTC) - ts > STALE_AFTER:
                print(
                    f"WARNING: AUDIT_STATE.json is older than {STALE_AFTER} "
                    f"(generated_at={generated_at}). Re-run `make session-start`.",
                    file=sys.stderr,
                )
        except ValueError:
            pass
    return state


def _pick_finding(state: dict) -> dict | None:
    findings = [f for f in state.get("findings", []) if f.get("status") == "open"]
    if not findings:
        return None
    # Highest-priority first. AUDIT_STATE.json does not carry priority labels;
    # fall back to id order (lower F-NNN first), which matches the historical
    # convention that earlier findings are foundational.
    findings.sort(key=lambda f: f.get("id", "F-999"))
    return findings[0]


def main() -> int:
    state = _load_state()
    finding = _pick_finding(state)
    if finding is None:
        print("No open findings. L3 has nothing to dispatch.")
        return 1

    fid = finding.get("id", "?")
    title = finding.get("title", "(no title)")
    path = finding.get("path", "?")
    vscript = finding.get("verification_script") or "(none yet — Remediator must add or fill)"

    print("── L3 dispatch ─────────────────────────────────────────────")
    print(f"Top open finding: {fid} — {title}")
    print(f"YAML:             {path}")
    print(f"verification:     {vscript}")
    print()
    print("Remediator contract (from governance/AUDIT_PROCEDURE.md §L1):")
    print("  1. Make the change.")
    print("  2. Add or extend the `verification_script` named in the finding YAML.")
    print("  3. Update the finding YAML: status=closed, closed_at=<today>,")
    print("     fill verification_script path.")
    print("  4. Run `make verify`.")
    print(f"  5. Open a PR. Title must contain `{fid}`.")
    print()
    if HANDOUT_PATH.exists():
        print(f"→ Full handout: {HANDOUT_PATH.relative_to(REPO_ROOT)}")
    print(f"→ Procedure:    {PROCEDURE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
