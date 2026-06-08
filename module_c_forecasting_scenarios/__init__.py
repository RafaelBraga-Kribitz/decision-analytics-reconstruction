"""Module C project root — extend imports to the src implementation."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_src_root = Path(__file__).resolve().parent / "src" / "module_c_forecasting_scenarios"
if _src_root.is_dir():
    __path__.append(str(_src_root))
