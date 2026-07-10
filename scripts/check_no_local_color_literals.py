#!/usr/bin/env python3
"""IMP-V01 static check: no local segment-color literals outside the shared module.

The shared visual system (``shared/src/visual_system/palette.py``) is the only
sanctioned home for segment colors. This check parses every first-party Python
file and fails if it finds a *local* segment palette — either shape:

* a ``dict`` literal whose keys include two or more canonical segment labels
  and at least one value is a hex color string (the ``SEG_COLORS = {...}``
  shape that ``reports/eda/generate_eda.py`` used to carry), or
* a list/tuple literal of three or more hex color strings assigned to a name
  containing ``COLOR`` (the positional ``SEG_COLORS = [...]`` shape that
  ``reports/eda/build_notebook.py`` used to carry).

Either shape is a palette that can drift from the canonical one — the exact
defect IMP-V01 exists to retire. Import from ``visual_system`` instead.

Pure AST inspection — no imports of the scanned files, no data load.

Run standalone:
    poetry run python scripts/check_no_local_color_literals.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))

from visual_system.palette import SEGMENT_LABELS  # noqa: E402 -- after sys.path insert

_CANONICAL = frozenset(SEGMENT_LABELS)
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Directories whose first-party Python this check governs.
_SCAN_DIRS = (
    "reports",
    "scripts",
    "module_a_population_segmentation/src",
    "module_a_population_segmentation/app",
    "module_b_resource_allocation/src",
    "module_c_forecasting_scenarios/src",
)

# The shared module (the one sanctioned home) and this check's sibling, whose
# ``_MOTIVATING_OLD_PALETTE`` is a deliberately-retained segment->hex dict used
# as the recurrence guard's negative fixture, are exempt.
_EXEMPT = (
    "shared/src/visual_system/palette.py",
    "scripts/check_palette_cvd_contrast.py",
    "scripts/check_no_local_color_literals.py",
)


def _is_hex(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(_HEX_RE.match(node.value))
    )


def _segment_color_dict(node: ast.AST) -> bool:
    """True if ``node`` is a dict literal mapping >=2 segment labels, with a hex value."""
    if not isinstance(node, ast.Dict):
        return False
    seg_keys = [k for k in node.keys if isinstance(k, ast.Constant) and k.value in _CANONICAL]
    if len(seg_keys) < 2:
        return False
    return any(_is_hex(v) for v in node.values)


def _hex_sequence(node: ast.AST) -> bool:
    """True if ``node`` is a list/tuple of >=3 hex color string literals."""
    if not isinstance(node, (ast.List, ast.Tuple)):
        return False
    hexes = [e for e in node.elts if _is_hex(e)]
    return len(hexes) >= 3


def _violations_in(tree: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        # dict form: SEG_COLORS = {"rural_committed": "#...", ...}
        if _segment_color_dict(node):
            found.append((getattr(node, "lineno", 0), "segment-label-keyed color dict"))
        # positional form: SEG_COLORS = ["#...", "#...", "#..."]
        if isinstance(node, ast.Assign):
            names = "".join(t.id for t in node.targets if isinstance(t, ast.Name)).upper()
            if "COLOR" in names and _hex_sequence(node.value):
                found.append((node.lineno, f"local hex color sequence assigned to {names}"))
    return found


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for rel in _SCAN_DIRS:
        base = REPO_ROOT / rel
        if base.is_dir():
            files.extend(sorted(base.rglob("*.py")))
    return files


def main() -> int:
    exempt = {(REPO_ROOT / e).resolve() for e in _EXEMPT}
    violations: list[str] = []
    scanned = 0
    for path in _iter_python_files():
        if path.resolve() in exempt:
            continue
        scanned += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - defensive
            violations.append(f"{path.relative_to(REPO_ROOT)}: unparseable ({exc})")
            continue
        for lineno, kind in _violations_in(tree):
            violations.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {kind}")

    print(f"check_no_local_color_literals: scanned {scanned} Python files")
    if violations:
        print(
            f"[FAIL] check_no_local_color_literals.py: {len(violations)} local "
            "segment-color literal(s) found — import from visual_system instead:"
        )
        for v in violations:
            print(f"       {v}")
        return 1
    print("[PASS] check_no_local_color_literals.py: no local segment-color literals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
