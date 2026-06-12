"""Ingest and clean Module B's dirty source files.

Produces three canonical, contract-aligned frames the rest of Module B
consumes:

* :class:`BudgetLineFrame` — one row per cleaned vendor invoice line.
* :class:`VolunteerLogFrame` — one row per cleaned canvassing/event entry.
* :class:`MediaBuySheetFrame` — one row per cleaned broadcast media buy.

The cleaner is **idempotent** and **deterministic**: a clean frame fed back
through it returns unchanged, and the same inputs always produce the same
output ordering (sorted by ``row_id``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

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


@dataclass(frozen=True)
class BudgetLineFrame:
    df: pd.DataFrame  # see clean_budget_lines for canonical schema


@dataclass(frozen=True)
class VolunteerLogFrame:
    df: pd.DataFrame


@dataclass(frozen=True)
class MediaBuySheetFrame:
    df: pd.DataFrame


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

    # Reject rows missing any of the LP-critical fields.
    valid_mask = (
        df["channel"].notna()
        & df["department"].notna()
        & df["iso_week"].notna()
        & df["currency"].notna()
        & df["amount_native"].notna()
        & (df["amount_native"] > 0)
    )
    cleaned = df.loc[
        valid_mask,
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

    cleaned = cleaned.drop_duplicates(subset=["row_id"], keep="first")
    cleaned = cleaned.sort_values("row_id").reset_index(drop=True)
    return BudgetLineFrame(df=cleaned)


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

    valid_mask = (
        df["channel"].notna()
        & df["department"].notna()
        & df["iso_week"].notna()
        & df["contacts"].notna()
        & (df["contacts"] > 0)
        & df["hours"].notna()
        & df["cost_pyg"].notna()
        & (df["cost_pyg"] > 0)
    )
    cleaned = df.loc[
        valid_mask,
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
    cleaned = cleaned.drop_duplicates(subset=["row_id"], keep="first")
    cleaned = cleaned.sort_values("row_id").reset_index(drop=True)
    return VolunteerLogFrame(df=cleaned)


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

    valid_mask = (
        df["channel"].notna()
        & df["department"].notna()
        & df["iso_week"].notna()
        & df["impressions"].notna()
        & (df["impressions"] > 0)
        & df["currency"].notna()
        & df["amount_native"].notna()
        & (df["amount_native"] > 0)
    )
    cleaned = df.loc[
        valid_mask,
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
    cleaned = cleaned.drop_duplicates(subset=["row_id"], keep="first")
    cleaned = cleaned.sort_values("row_id").reset_index(drop=True)
    return MediaBuySheetFrame(df=cleaned)


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
    budget = clean_budget_lines(pd.read_csv(in_dir / "budget_lines_raw.csv"))
    volunteer = clean_volunteer_logs(pd.read_csv(in_dir / "volunteer_logs_raw.csv"))
    media = clean_media_buy_sheet(pd.read_csv(in_dir / "media_buy_sheet_raw.csv"))
    return {
        "budget_lines_clean": budget.df,
        "volunteer_logs_clean": volunteer.df,
        "media_buy_sheet_clean": media.df,
    }
