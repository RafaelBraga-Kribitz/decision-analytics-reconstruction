#!/usr/bin/env python3
"""Verification script for F-087 (Module A cleaner & injector integrity).

(a) Every entry in inject_flaws' ``flaw_types_injected`` manifest maps to an
    operation actually performed in the function body (static AST check), and
    the docstrings / config do not claim a 13th, never-injected flaw.
(b) A missing ``rural_flag`` is imputed per department urban share, not by a
    flat national draw (functional, 6k synthetic rows).
(c) Malformed DOBs are flagged ``dob_imputed`` and counted in the QA report,
    with the pre-clamp age rate surfaced alongside.

Spec: governance/improvement_plan/IMP-A04_cleaner-injector-integrity.md
"""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

MODULE_A = REPO_ROOT / "module_a_population_segmentation"
INJECTOR = MODULE_A / "src" / "population_segmentation" / "data" / "raw_injector.py"
CONFIG = MODULE_A / "config" / "generation.yaml"

# Manifest token -> source marker that must appear in inject_flaws' body.
FLAW_OPERATIONS = {
    "FMT_cedula": "_inject_cedula_format_errors",
    "DUP": "_inject_duplicate_rows",
    "TYP_department": "_inject_department_typos",
    "NUL_municipality": "municipality_null_rate",
    "FMT_dob": "_inject_dob_swaps",
    "ENC": "_inject_encoding_errors",
    "FMT_phone": "phone_format_variant_rate",
    "TYP_gender": "_inject_gender_variants",
    "RNG_age": "_inject_age_range_errors",
    "SCH": "schema_drift_rate",
    "TYP_sentiment": "_inject_sentiment_scale_inconsistency",
    "NUL_qualitative_district": "qualitative_district_null_rate",
}


def _inject_flaws_node(source: str) -> ast.FunctionDef:
    fn = next(n for n in ast.walk(ast.parse(source)) if getattr(n, "name", "") == "inject_flaws")
    assert isinstance(fn, ast.FunctionDef)
    return fn


def _manifest_and_operations(source: str) -> tuple[list[str], str]:
    """Return inject_flaws' manifest list and the code that runs before it is set."""
    fn = _inject_flaws_node(source)
    assigns = [n for n in fn.body if isinstance(n, ast.Assign)]
    manifest_node = next(n for n in assigns if "flaw_types_injected" in ast.unparse(n.targets[0]))
    manifest = ast.literal_eval(manifest_node.value)
    statements = [s for s in fn.body[1:] if s.lineno < manifest_node.lineno]  # skip docstring
    operations = "\n".join(ast.unparse(s) for s in statements)
    return manifest, operations


def _injector_gaps() -> list[str]:
    source = INJECTOR.read_text(encoding="utf-8")
    manifest, operations = _manifest_and_operations(source)
    gaps = [
        f"manifest lists {token!r} but inject_flaws performs no such operation"
        for token in manifest
        if FLAW_OPERATIONS.get(token, "\0") not in operations
    ]
    if "13 flaw types" in source:
        gaps.append("raw_injector.py still claims 13 flaw types")
    if "rural_flag_missing_rate" in (yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}).get(
        "flaw_injection", {}
    ):
        gaps.append("generation.yaml documents rural_flag_missing_rate, which nothing injects")
    return gaps


def _cleaner_gaps() -> list[str]:
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw = inject_flaws(generate_population({**config, "sample_size": 6000}, seed=7), config, seed=7)
    gaps = []
    with tempfile.TemporaryDirectory() as tmp:
        no_rural = raw.drop(columns=["rural_flag"])
        out = clean_population(no_rural, config, qa_report_dir=tmp, seed=7)
        by_dept = out.groupby("department")["rural_flag"].mean()
        if by_dept.get("Asuncion", 0.0) > 0.0 or by_dept.max() - by_dept.min() < 0.3:
            gaps.append("rural_flag imputation ignores department urban share")
        bad = raw.copy()
        bad.loc[bad.index[:10], "dob"] = "not-a-date"
        out = clean_population(bad, config, qa_report_dir=tmp, seed=7)
        report = "\n".join(p.read_text(encoding="utf-8") for p in Path(tmp).glob("qa_report_*.md"))
    if "dob_imputed" not in out.columns or int(out["dob_imputed"].sum()) < 10:
        gaps.append("malformed DOBs are not flagged dob_imputed")
    if "DOB imputed with" not in report or "before clamping" not in report:
        gaps.append("QA report omits DOB-imputation or pre-clamp age counts")
    return gaps


def main() -> int:
    sys.path.insert(0, str(MODULE_A / "src"))
    gaps = _injector_gaps()
    try:
        gaps += _cleaner_gaps()
    except (KeyError, ImportError) as exc:
        gaps.append(f"cleaner integrity check could not run ({exc!r})")
    return gate("F-087", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())
