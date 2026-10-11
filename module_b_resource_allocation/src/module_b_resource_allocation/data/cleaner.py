"""Ingest and clean Module B's dirty source files.

Produces three canonical, contract-aligned frames the rest of Module B
consumes:

* :class:`BudgetLineFrame` — one row per cleaned vendor invoice line.
* :class:`VolunteerLogFrame` — one row per cleaned canvassing/event entry.
* :class:`MediaBuySheetFrame` — one row per cleaned broadcast media buy.

The cleaner is **idempotent** and **deterministic**: a clean frame fed back
through it returns unchanged, and the same inputs always produce the same
output ordering (sorted by ``row_id``).

No row is dropped silently (F-086 / IMP-B04): every rejected row is recorded on
the frame's ``rejections`` table with the first failing predicate as its
``reason``, and :func:`rejection_summary` gates each source at
``REJECTION_RATE_GATE``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import pandas as pd

from module_b_resource_allocation.constants import (
    CHANNEL_NAMES,
    DEPARTMENTS,
    WEEK_LABELS,
)
from module_b_resource_allocation.data.dirty_generator import (
    CHANNEL_ALIASES,
    DEPARTMENT_ALIASES,
)

# Currency markers must reduce to a small canonical set.
_USD_TOKENS: Final[frozenset[str]] = frozenset({"usd", "us$", "$"})
_PYG_TOKENS: Final[frozenset[str]] = frozenset({"pyg", "gs.", "gs", "₲"})


def _strip_accents(text: str) -> str:
    nkfd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nkfd if not unicodedata.combining(c))


def _canonical_channel(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    key = raw.strip()
    if key in CHANNEL_ALIASES:
        return CHANNEL_ALIASES[key]
    # Case-insensitive fallback.
    folded = key.casefold()
    for alias, canon in CHANNEL_ALIASES.items():
        if alias.casefold() == folded:
            return canon
    if key in CHANNEL_NAMES:
        return key
    return None


def _canonical_department(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    key = raw.strip()
    if key in DEPARTMENT_ALIASES:
        return DEPARTMENT_ALIASES[key]
    folded_key = _strip_accents(key).casefold()
    for alias, canon in DEPARTMENT_ALIASES.items():
        if _strip_accents(alias).casefold() == folded_key:
            return canon
    if key in DEPARTMENTS:
        return key
    return None


def _canonical_currency(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    folded = raw.strip().casefold()
    if folded in _USD_TOKENS:
        return "USD"
    if folded in _PYG_TOKENS:
        return "PYG"
    return None


_NUMBER_RE = re.compile(r"\d[\d.,]*")


def _extract_number_token(raw: str) -> str | None:
    match = _NUMBER_RE.search(raw)
    if match is None:
        return None
    text = match.group(0).strip(".,")
    return text if text else None


def _normalize_mixed_separators(text: str) -> str:
    if text.rfind(",") > text.rfind("."):
        return text.replace(".", "").replace(",", ".")
    return text.replace(",", "")


def _normalize_comma_only(text: str) -> str:
    parts = text.split(",")
    if len(parts[-1]) == 3 and len(parts) > 1:
        return text.replace(",", "")
    return text.replace(",", ".")


def _parse_locale_number(raw: object) -> float | None:
    """Parse '1.234,56' (es) or '1,234.56' (en) or '1234.56' to float.

    Strips currency prefixes/markers ('Gs.', 'US$', '₲') before parsing.
    Single-dot ambiguous values ('1.234') default to the decimal-mark
    interpretation (1.234) — locale heuristic kicks in only when both
    separators or pure-comma-with-leading-3-digit-groups appear.
    """
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    if not cleaned or cleaned.upper() in {"NULL", "NAN"}:
        return None
    text = _extract_number_token(cleaned)
    if text is None:
        return None
    if "," in text and "." in text:
        text = _normalize_mixed_separators(text)
    elif "," in text:
        text = _normalize_comma_only(text)
    try:
        return float(text)
    except ValueError:
        return None


def _valid_week(label: str | None) -> str | None:
    if label is None:
        return None
    if label in WEEK_LABELS:
        return label
    return None


#: A source file whose rejected-row share exceeds this fails its gate.
REJECTION_RATE_GATE: Final[float] = 0.02
REJECTION_COLUMNS: Final[tuple[str, ...]] = (
    "source_file",
    "row_id",
    "reason",
    "department",
    "channel",
)


def _empty_rejections() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in REJECTION_COLUMNS})


def _filter_and_record(
    df: pd.DataFrame, source_file: str, checks: list[tuple[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split ``df`` into kept rows and a rejection table (first failing check wins).

    Rows passing every check are then de-duplicated on ``row_id``; dropped
    duplicates are recorded with reason ``duplicate_row_id``.
    """
    reason = pd.Series(None, index=df.index, dtype="object")
    for name, ok in checks:
        reason = reason.where(reason.notna() | ok.fillna(False).astype(bool), name)
    kept = df.loc[reason.isna()]
    dup = kept["row_id"].duplicated(keep="first")
    reason.loc[dup[dup].index] = "duplicate_row_id"
    rejected = df.loc[reason.notna()].assign(source_file=source_file, reason=reason.dropna())
    rejections = rejected.reindex(columns=list(REJECTION_COLUMNS)).sort_values(
        ["reason", "row_id"], kind="stable"
    )
    return df.loc[reason.isna()], rejections.reset_index(drop=True)


@dataclass(frozen=True)
class BudgetLineFrame:
    df: pd.DataFrame  # see clean_budget_lines for canonical schema
    rejections: pd.DataFrame = field(default_factory=_empty_rejections)


@dataclass(frozen=True)
class VolunteerLogFrame:
    df: pd.DataFrame
    rejections: pd.DataFrame = field(default_factory=_empty_rejections)


@dataclass(frozen=True)
class MediaBuySheetFrame:
    df: pd.DataFrame
    rejections: pd.DataFrame = field(default_factory=_empty_rejections)


def clean_budget_lines(raw: pd.DataFrame) -> BudgetLineFrame:
    """Normalize dirty budget line CSV rows to the solver contract schema.

    Args:
        raw: Vendor extract containing ``channel_text``, ``department_text``,
            ``week_label``, ``currency``, ``amount_text``, and ``fx_tier_hint``.

    Returns:
        ``BudgetLineFrame`` wrapping sorted, deduplicated clean rows.

    Raises:
        KeyError: If ``raw`` lacks any required input column.

    Example:
        ``clean_budget_lines(pd.read_csv(in_dir / \"budget_lines_raw.csv\"))`` in QA notebooks.
    """
    required = {
        "row_id",
        "channel_text",
        "department_text",
        "week_label",
        "currency",
        "amount_text",
        "fx_tier_hint",
    }
    missing = required - set(raw.columns)
    if missing:
        raise KeyError(f"budget_lines_raw missing columns: {sorted(missing)}")

    df = raw.copy()
    df["channel"] = df["channel_text"].map(_canonical_channel)
    df["department"] = df["department_text"].map(_canonical_department)
    df["iso_week"] = df["week_label"].map(_valid_week)
    df["currency"] = df["currency"].map(_canonical_currency)
    df["amount_native"] = df["amount_text"].map(_parse_locale_number)
    df["fx_tier"] = df["fx_tier_hint"].where(df["fx_tier_hint"].isin(["REF", "RETAIL"]), "REF")

    # Reject rows missing any of the LP-critical fields, recording why.
    kept, rejections = _filter_and_record(
        df,
        "budget_lines_raw.csv",
        [
            ("non_canonical_channel", df["channel"].notna()),
            ("non_canonical_department", df["department"].notna()),
            ("non_canonical_week", df["iso_week"].notna()),
            ("unrecognized_currency", df["currency"].notna()),
            ("unparsable_amount", df["amount_native"].notna()),
            ("non_positive_amount", df["amount_native"] > 0),
        ],
    )
    cleaned = kept.loc[
        :,
        [
            "row_id",
            "vendor",
            "channel",
            "department",
            "iso_week",
            "currency",
            "amount_native",
            "fx_tier",
        ],
    ].copy()

    cleaned = cleaned.sort_values("row_id").reset_index(drop=True)
    return BudgetLineFrame(df=cleaned, rejections=rejections)


def clean_volunteer_logs(raw: pd.DataFrame) -> VolunteerLogFrame:
    """Normalize volunteer log extracts to the structured contract schema.

    Args:
        raw: Field-ops extract with contacts, hours, and PYG cost text columns.

    Returns:
        ``VolunteerLogFrame`` wrapping sorted, deduplicated clean rows.

    Raises:
        KeyError: If ``raw`` lacks any required input column.

    Example:
        ``clean_volunteer_logs(pd.read_csv(in_dir / \"volunteer_logs_raw.csv\"))``.
    """
    required = {
        "row_id",
        "channel_text",
        "department_text",
        "week_label",
        "contacts_text",
        "hours_text",
        "cost_pyg_text",
    }
    missing = required - set(raw.columns)
    if missing:
        raise KeyError(f"volunteer_logs_raw missing columns: {sorted(missing)}")

    df = raw.copy()
    df["channel"] = df["channel_text"].map(_canonical_channel)
    df["department"] = df["department_text"].map(_canonical_department)
    df["iso_week"] = df["week_label"].map(_valid_week)
    df["contacts"] = df["contacts_text"].map(_parse_locale_number)
    df["hours"] = df["hours_text"].map(_parse_locale_number)
    df["cost_pyg"] = df["cost_pyg_text"].map(_parse_locale_number)

    kept, rejections = _filter_and_record(
        df,
        "volunteer_logs_raw.csv",
        [
            ("non_canonical_channel", df["channel"].notna()),
            ("non_canonical_department", df["department"].notna()),
            ("non_canonical_week", df["iso_week"].notna()),
            ("unparsable_contacts", df["contacts"].notna()),
            ("non_positive_contacts", df["contacts"] > 0),
            ("unparsable_hours", df["hours"].notna()),
            ("unparsable_cost", df["cost_pyg"].notna()),
            ("non_positive_cost", df["cost_pyg"] > 0),
        ],
    )
    cleaned = kept.loc[
        :,
        [
            "row_id",
            "team_lead",
            "channel",
            "department",
            "iso_week",
            "contacts",
            "hours",
            "cost_pyg",
        ],
    ].copy()
    cleaned["contacts"] = cleaned["contacts"].astype("int64")
    cleaned = cleaned.sort_values("row_id").reset_index(drop=True)
    return VolunteerLogFrame(df=cleaned, rejections=rejections)


def clean_media_buy_sheet(raw: pd.DataFrame) -> MediaBuySheetFrame:
    """Normalize paid media buy rows (impressions + spend) for downstream joins.

    Args:
        raw: Media agency sheet with impressions and mixed-currency amounts.

    Returns:
        ``MediaBuySheetFrame`` wrapping sorted, deduplicated clean rows.

    Raises:
        KeyError: If ``raw`` lacks any required input column.

    Example:
        ``clean_media_buy_sheet(pd.read_csv(in_dir / \"media_buy_sheet_raw.csv\"))``.
    """
    required = {
        "row_id",
        "channel_text",
        "department_text",
        "week_label",
        "impressions_text",
        "currency",
        "amount_text",
        "fx_tier_hint",
    }
    missing = required - set(raw.columns)
    if missing:
        raise KeyError(f"media_buy_sheet_raw missing columns: {sorted(missing)}")

    df = raw.copy()
    df["channel"] = df["channel_text"].map(_canonical_channel)
    df["department"] = df["department_text"].map(_canonical_department)
    df["iso_week"] = df["week_label"].map(_valid_week)
    df["impressions"] = df["impressions_text"].map(_parse_locale_number)
    df["currency"] = df["currency"].map(_canonical_currency)
    df["amount_native"] = df["amount_text"].map(_parse_locale_number)
    df["fx_tier"] = df["fx_tier_hint"].where(df["fx_tier_hint"].isin(["REF", "RETAIL"]), "REF")

    kept, rejections = _filter_and_record(
        df,
        "media_buy_sheet_raw.csv",
        [
            ("non_canonical_channel", df["channel"].notna()),
            ("non_canonical_department", df["department"].notna()),
            ("non_canonical_week", df["iso_week"].notna()),
            ("unparsable_impressions", df["impressions"].notna()),
            ("non_positive_impressions", df["impressions"] > 0),
            ("unrecognized_currency", df["currency"].notna()),
            ("unparsable_amount", df["amount_native"].notna()),
            ("non_positive_amount", df["amount_native"] > 0),
        ],
    )
    cleaned = kept.loc[
        :,
        [
            "row_id",
            "vendor",
            "channel",
            "department",
            "iso_week",
            "impressions",
            "currency",
            "amount_native",
            "fx_tier",
        ],
    ].copy()
    cleaned["impressions"] = cleaned["impressions"].astype("int64")
    cleaned = cleaned.sort_values("row_id").reset_index(drop=True)
    return MediaBuySheetFrame(df=cleaned, rejections=rejections)


def clean_directory(in_dir: Path) -> dict[str, pd.DataFrame]:
    """Read the three raw CSV fixtures from ``in_dir`` and return cleaned frames.

    Args:
        in_dir: Directory containing ``budget_lines_raw.csv``,
            ``volunteer_logs_raw.csv``, and ``media_buy_sheet_raw.csv``.

    Returns:
        Dict mapping logical artifact names to cleaned pandas frames.

    Raises:
        FileNotFoundError: If expected CSVs are absent from ``in_dir``.
        KeyError: Propagated from the cleaners when raw columns are missing.

    Example:
        ``clean_directory(Path(\"data/raw/module_b\"))`` in integration tests.
    """
    frames, _rejections, _summary = clean_directory_with_report(in_dir)
    return frames


def rejection_summary(rejections: pd.DataFrame, raw_counts: dict[str, int]) -> pd.DataFrame:
    """Per-source rejected-row counts and rates gated at ``REJECTION_RATE_GATE``.

    Args:
        rejections: Row-level rejection table (``REJECTION_COLUMNS``).
        raw_counts: Raw row count per ``source_file``.

    Returns:
        One row per source with ``n_raw``, ``n_rejected``, ``rejection_rate``
        and ``gate_status`` (``PASS`` / ``FAIL``), sorted by ``source_file``.

    Raises:
        KeyError: If ``rejections`` lacks a ``source_file`` column.

    Example:
        ``rejection_summary(frame.rejections, {"budget_lines_raw.csv": len(raw)})``.
    """
    rows = []
    for source, n_raw in sorted(raw_counts.items()):
        n_rejected = int((rejections["source_file"] == source).sum())
        rate = n_rejected / n_raw if n_raw else 0.0
        rows.append(
            {
                "source_file": source,
                "n_raw": n_raw,
                "n_rejected": n_rejected,
                "rejection_rate": rate,
                "gate_threshold": REJECTION_RATE_GATE,
                "gate_status": "FAIL" if rate > REJECTION_RATE_GATE else "PASS",
            }
        )
    return pd.DataFrame(rows)


def clean_directory_with_report(
    in_dir: Path,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """Clean the three raw CSVs and return frames plus the rejection record.

    Args:
        in_dir: Directory containing the three raw CSV fixtures.

    Returns:
        ``(frames, rejections, summary)``: the cleaned frames as in
        :func:`clean_directory`, the row-level rejection table, and the
        per-source :func:`rejection_summary`. For every source,
        ``n_raw - len(clean) == n_rejected`` exactly.

    Raises:
        FileNotFoundError: If expected CSVs are absent from ``in_dir``.
        KeyError: Propagated from the cleaners when raw columns are missing.

    Example:
        ``frames, rejections, summary = clean_directory_with_report(raw_dir)``.
    """
    # Raw vendor extracts are text: letting read_csv infer dtypes turned the
    # mostly-numeric contacts_text column into floats, which the locale parser
    # rejects, silently emptying volunteer_logs_clean.
    raws = {
        name: pd.read_csv(in_dir / name, dtype=str)
        for name in ("budget_lines_raw.csv", "volunteer_logs_raw.csv", "media_buy_sheet_raw.csv")
    }
    budget = clean_budget_lines(raws["budget_lines_raw.csv"])
    volunteer = clean_volunteer_logs(raws["volunteer_logs_raw.csv"])
    media = clean_media_buy_sheet(raws["media_buy_sheet_raw.csv"])
    frames = {
        "budget_lines_clean": budget.df,
        "volunteer_logs_clean": volunteer.df,
        "media_buy_sheet_clean": media.df,
    }
    rejections = pd.concat(
        [budget.rejections, volunteer.rejections, media.rejections], ignore_index=True
    )
    summary = rejection_summary(rejections, {k: len(v) for k, v in raws.items()})
    return frames, rejections, summary
