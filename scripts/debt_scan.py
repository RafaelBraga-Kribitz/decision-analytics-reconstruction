"""Technical-debt scanner — language-aware, gracefully degrading.

Writes governance/DEBT_BASELINE.json: a normalized snapshot of debt metrics
(dead code, unused exports, duplication, complexity) measured by whatever
specialized tools are installed. Each metric records the tool that produced it
and whether the tool was available, so the ratchet (check_debt_ratchet.py) only
gates metrics it can actually measure on both sides.

Philosophy: this is the static-analysis analogue of the finding ratchet. The
baseline can only move *down*. `make debt-scan` rewrites it (use after you've
reduced debt, to lock in the gain). `make debt-check` re-scans and fails if any
ratcheted metric grew — that is the "remediate before it grows" gate.

Tool matrix (install what applies; missing tools are skipped, not fatal):

  Python : ruff (unused imports/vars), vulture (dead code),
           radon (cyclomatic complexity), jscpd (duplication, optional)
  TS/JS  : knip (unused files/exports/deps), jscpd (duplication),
           eslint (unused, optional)

Fallow (https://github.com/fallow-rs/fallow), if present, is used directly for
TS/JS and supersedes knip+jscpd for those metrics.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOV = REPO_ROOT / "governance"
BASELINE_PATH = GOV / "DEBT_BASELINE.json"
CONFIG_PATH = GOV / "debt_config.yaml"

# Defaults; override per-project via governance/debt_config.yaml.
DEFAULT_THRESHOLDS = {
    "duplication_pct_max": 5.0,
    "complexity_cc_max": 10,  # radon rank C ≈ CC 11-20; we count blocks worse than this
}

_TIMEOUT = 180


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603
            cmd, cwd=REPO_ROOT, capture_output=True, text=True,
            check=False, timeout=_TIMEOUT,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


def _metric(value, available: bool, tool: str, lower_is_better: bool = True) -> dict:
    return {
        "value": value,
        "available": available,
        "tool": tool,
        "lower_is_better": lower_is_better,
    }


def _load_config() -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if CONFIG_PATH.exists():
        try:
            import yaml

            cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
            thresholds.update(cfg.get("thresholds", {}))
        except Exception:  # noqa: BLE001 — config is best-effort
            pass
    return thresholds


def detect_languages() -> list[str]:
    langs: list[str] = []
    if any(REPO_ROOT.glob("**/*.py")) or (REPO_ROOT / "pyproject.toml").exists():
        langs.append("python")
    if (REPO_ROOT / "package.json").exists() or (REPO_ROOT / "tsconfig.json").exists():
        langs.append("ts-js")
    return langs


# ── Python tools ────────────────────────────────────────────────────────────


def scan_python(thresholds: dict) -> dict[str, dict]:
    m: dict[str, dict] = {}

    # ruff — unused imports (F401), unused vars (F841), redefinition (F811)
    if _have("ruff"):
        rc, out = _run(
            ["ruff", "check", "--select", "F401,F811,F841",
             "--output-format", "json", "."]
        )
        try:
            n = len(json.loads(out)) if out.strip().startswith("[") else 0
        except json.JSONDecodeError:
            n = 0
        m["ruff_unused"] = _metric(n, True, "ruff")
    else:
        m["ruff_unused"] = _metric(None, False, "ruff")

    # vulture — dead code (functions, classes, attrs, vars)
    if _have("vulture"):
        rc, out = _run(["vulture", ".", "--min-confidence", "80"])
        # vulture prints one finding per line; rc=1 when it finds something
        n = sum(1 for line in out.splitlines() if ":" in line and "unused" in line.lower())
        m["vulture_dead_code"] = _metric(n, True, "vulture")
    else:
        m["vulture_dead_code"] = _metric(None, False, "vulture")

    # radon — cyclomatic complexity blocks worse than threshold
    if _have("radon"):
        rc, out = _run(["radon", "cc", "-j", "-n", "C", "."])
        try:
            data = json.loads(out) if out.strip().startswith("{") else {}
            n = sum(
                1
                for blocks in data.values()
                for b in blocks
                if isinstance(b, dict) and b.get("complexity", 0) > thresholds["complexity_cc_max"]
            )
        except json.JSONDecodeError:
            n = 0
        m["radon_complex_blocks"] = _metric(n, True, "radon")
    else:
        m["radon_complex_blocks"] = _metric(None, False, "radon")

    return m


# ── TS/JS tools ─────────────────────────────────────────────────────────────


def scan_ts_js(thresholds: dict) -> dict[str, dict]:
    m: dict[str, dict] = {}

    # Fallow supersedes knip+jscpd for TS/JS if installed.
    if _have("fallow"):
        rc, out = _run(["fallow", "scan", "--json"])
        try:
            data = json.loads(out) if out.strip().startswith("{") else {}
            m["fallow_dead_code"] = _metric(
                int(data.get("dead_code_count", 0)), True, "fallow"
            )
            m["fallow_duplication_pct"] = _metric(
                float(data.get("duplication_pct", 0.0)), True, "fallow"
            )
            return m
        except (json.JSONDecodeError, ValueError):
            pass  # fall through to knip/jscpd

    # knip — unused files, exports, dependencies
    if _have("knip"):
        rc, out = _run(["knip", "--reporter", "json"])
        try:
            data = json.loads(out) if out.strip().startswith("{") else {}
            files = len(data.get("files", []))
            issues = data.get("issues", [])
            exports = sum(len(i.get("exports", [])) for i in issues) if isinstance(issues, list) else 0
            m["knip_unused_files"] = _metric(files, True, "knip")
            m["knip_unused_exports"] = _metric(exports, True, "knip")
        except json.JSONDecodeError:
            m["knip_unused_files"] = _metric(None, False, "knip")
    else:
        m["knip_unused_files"] = _metric(None, False, "knip")

    # jscpd — duplication percentage (language-agnostic)
    if _have("jscpd"):
        rc, out = _run(
            ["jscpd", "--silent", "--reporters", "json", "--output", "/tmp/jscpd", "."]
        )
        report = Path("/tmp/jscpd/jscpd-report.json")
        pct = 0.0
        if report.exists():
            try:
                stats = json.loads(report.read_text()).get("statistics", {})
                pct = float(stats.get("total", {}).get("percentage", 0.0))
            except (json.JSONDecodeError, ValueError):
                pct = 0.0
        m["jscpd_duplication_pct"] = _metric(pct, True, "jscpd")
    else:
        m["jscpd_duplication_pct"] = _metric(None, False, "jscpd")

    return m


def scan() -> dict:
    thresholds = _load_config()
    languages = detect_languages()
    metrics: dict[str, dict] = {}
    if "python" in languages:
        metrics.update(scan_python(thresholds))
    if "ts-js" in languages:
        metrics.update(scan_ts_js(thresholds))
    return {
        "writer": "scripts/debt_scan.py",
        "generated_at": datetime.now(UTC).isoformat(),
        "languages": languages,
        "thresholds": thresholds,
        "metrics": metrics,
    }


def main() -> int:
    snapshot = scan()
    GOV.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    measured = {k: v["value"] for k, v in snapshot["metrics"].items() if v["available"]}
    skipped = [v["tool"] for v in snapshot["metrics"].values() if not v["available"]]
    print(f"[debt_scan] wrote {BASELINE_PATH.relative_to(REPO_ROOT)}")
    print(f"[debt_scan]   languages: {', '.join(snapshot['languages']) or 'none detected'}")
    for name, value in sorted(measured.items()):
        print(f"[debt_scan]   {name}: {value}")
    if skipped:
        print(f"[debt_scan]   skipped (tool not installed): {', '.join(sorted(set(skipped)))}")
        print("[debt_scan]   → see governance/DEBT_TOOLS.md to enable more coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
