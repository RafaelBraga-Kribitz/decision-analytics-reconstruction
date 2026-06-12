"""Adversary core — re-run every closed finding's verification_script.

Run by `make verify` and by the `adversary` CI job on every PR. For each finding
with status `closed`, execute its verification_script and require exit 0. A
non-zero result is a regression: the finding was declared fixed but its contract
no longer holds. This is the mechanism that makes closure durable rather than a
narrative claim.

`closed_historical` findings are archival records and may carry a null script;
they are skipped.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FINDINGS = REPO_ROOT / "governance" / "findings"


def _run(script: str) -> tuple[int, str]:
    path = REPO_ROOT / script
    if not path.exists():
        return 1, f"verification_script '{script}' not found"
    if script.startswith("tests/"):
        cmd = [sys.executable, "-m", "pytest", str(path), "-q", "-o", "addopts="]
    else:
        cmd = [sys.executable, str(path)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _load_closed_findings() -> list[tuple[str | None, str | None]]:
    if not FINDINGS.exists():
        return []
    closed: list[tuple[str | None, str | None]] = []
    for path in sorted(FINDINGS.glob("F-*.yaml")):
        if path.name == "F-TEMPLATE.yaml":
            continue
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("status") == "closed":
            closed.append((data.get("id"), data.get("verification_script")))
    return closed


def _verify_closed_finding(fid: str | None, script: str | None) -> str | None:
    if not script:
        print(f"[WARN] {fid}: closed but has no verification_script")
        return None
    rc, output = _run(script)
    if rc == 0:
        print(f"[PASS] {fid}: {script}")
        return None
    print(f"[FAIL] {fid}: {script} regressed (rc={rc})")
    for line in output.splitlines()[-10:]:
        print(f"       {line}")
    return f"{fid} ({script}) -> rc={rc}"


def main() -> int:
    closed = _load_closed_findings()
    if not FINDINGS.exists():
        print("[PASS] check_closed_findings.py: no findings directory yet")
        return 0

    regressions: list[str] = []
    for fid, script in closed:
        failure = _verify_closed_finding(fid, script)
        if failure:
            regressions.append(failure)

    if regressions:
        print(f"\n[FAIL] check_closed_findings.py: {len(regressions)} closed finding(s) regressed")
        return 1
    print(f"[PASS] check_closed_findings.py: {len(closed)} closed finding(s) re-verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
