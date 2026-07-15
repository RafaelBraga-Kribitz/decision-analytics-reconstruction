#!/usr/bin/env python3
"""Verification script for the figure-manifest coverage invariant (IMP-V02 / issue #67).

Single-sourcing recurrence guard. Generalizes ``check_eda_notebook_chart_parity.py``
(F-049, which caught one instance of notebook/factory drift point-wise) into a
structural invariant with four closure checks:

  1. Coverage — every tracked figure file under ``reports/`` (png/svg/html) has
     exactly one ``governance/FIGURE_MANIFEST.yaml`` entry. A produced figure
     with no lineage entry fails.
  2. Generator existence — every manifest entry's ``generator`` file exists.
     The manifest may never describe a generator that has been deleted/renamed.
  3. Single writer — no figure ``path`` is claimed by two different generators
     inside the manifest.
  4. No re-implementation — no ``build_notebook.py`` code cell whose title is a
     canonical chart ID (A1-A13, B1-B8, C-series, S-series) contains
     matplotlib/plotly drawing calls. Notebook chart cells must *display* the
     canonical factory's manifest-registered figure, never re-draw it.

Static only: filesystem walk + YAML parse + source scan, no chart rendering.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

_MANIFEST = REPO_ROOT / "governance" / "FIGURE_MANIFEST.yaml"
_NOTEBOOK = REPO_ROOT / "reports" / "eda" / "build_notebook.py"

_FIGURE_SUFFIXES = (".png", ".svg", ".html")

# A code-cell header naming a canonical Johnny-Decimal chart ID.
_CHART_ID = re.compile(r"#\s*([ABCS]\d{1,2})\s+[—-]")

# matplotlib / plotly drawing calls that must not appear in a chart-ID-titled
# cell once the notebook is subordinated to the canonical factory.
_DRAW_CALL = re.compile(
    r"\b(?:plt|ax|axes|fig|ax1|ax2)\d*\.\w"
    r"|\.(?:plot|bar|barh|scatter|hist|pie|imshow|twinx|contourf|"
    r"fill_between|boxplot|violinplot|stackplot|step|errorbar)\("
    r"|savefig|add_subplot|subplots\(|go\.Figure|px\.\w+\("
)

# code("""...""") cell bodies in build_notebook.py
_CODE_CELL = re.compile(r'\bcode\(\s*"""(.*?)"""\s*\)', re.S)


def _tracked_figures() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "reports/**/*.png", "reports/**/*.svg", "reports/**/*.html"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return sorted(
        line.strip() for line in proc.stdout.splitlines() if line.strip().endswith(_FIGURE_SUFFIXES)
    )


def _generator_exists(gen: str) -> bool:
    """True if the generator resolves to a real source file.

    Manifest generators are stable *logical* paths: the EDA factory is a real
    filesystem path (``reports/eda/generate_eda.py``), but the Module A
    generator is a package-style path (``module_a_.../pipeline/export.py``)
    whose file actually lives under ``module_a_.../src/population_segmentation/
    pipeline/export.py``. Resolve either form.

    Args:
        gen: The manifest ``generator`` string.

    Returns:
        Whether a matching source file exists on disk.
    """
    if (REPO_ROOT / gen).is_file():
        return True
    parts = gen.split("/")
    src_root = REPO_ROOT / parts[0] / "src"
    tail = "/".join(parts[1:])
    if src_root.is_dir():
        return any(str(f).replace("\\", "/").endswith(tail) for f in src_root.rglob(Path(gen).name))
    return False


def _norm_path(path: str | None) -> str:
    """Normalize manifest/git paths to forward slashes (#148)."""
    return (path or "").replace("\\", "/")


def _coverage_gaps(manifest: dict) -> list[str]:
    figures = manifest.get("figures", [])
    manifest_paths = [_norm_path(f.get("path")) for f in figures]
    path_set = set(manifest_paths)
    gaps: list[str] = []

    # (1) every tracked figure is registered
    for fig in _tracked_figures():
        if _norm_path(fig) not in path_set:
            gaps.append(f"figure {fig} has no FIGURE_MANIFEST.yaml entry")

    # (2) every generator exists
    for f in figures:
        gen = f.get("generator")
        if gen and not _generator_exists(gen):
            gaps.append(f"manifest entry {f.get('chart_id')} names missing generator {gen}")

    # (3) no path claimed by two different generators
    by_path: dict[str, set[str]] = {}
    for f in figures:
        by_path.setdefault(_norm_path(f.get("path")), set()).add(f.get("generator"))
    for path, gens in by_path.items():
        if len(gens) > 1:
            gaps.append(f"figure {path} claimed by multiple generators: {sorted(gens)}")

    return gaps


def _reimplementation_gaps(notebook_src: str) -> list[str]:
    gaps: list[str] = []
    for body in _CODE_CELL.findall(notebook_src):
        m = _CHART_ID.search(body)
        if not m:
            continue
        if _DRAW_CALL.search(body):
            gaps.append(
                f"build_notebook.py cell titled {m.group(1)} contains chart-drawing "
                "calls — it must display the canonical factory figure, not re-draw it"
            )
    return gaps


def main() -> int:
    if not _MANIFEST.is_file():
        return gate("F-077", Path(__file__).name, False, "FIGURE_MANIFEST.yaml missing")
    if not _NOTEBOOK.is_file():
        return gate("F-077", Path(__file__).name, False, "build_notebook.py missing")

    manifest = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8")) or {}
    gaps = _coverage_gaps(manifest) + _reimplementation_gaps(_NOTEBOOK.read_text(encoding="utf-8"))

    ok = not gaps
    detail = (
        "; ".join(gaps)
        if gaps
        else (
            f"{len(manifest.get('figures', []))} figures registered, one generator each; "
            "no notebook chart cell re-implements a canonical figure"
        )
    )
    return gate("F-077", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
