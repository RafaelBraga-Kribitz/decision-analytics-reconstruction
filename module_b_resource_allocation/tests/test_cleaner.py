"""TDD tests for the Module B dirty-layer cleaner.

The cleaner must:

* Canonicalize channel / department free-text via known aliases.
* Parse mixed-locale numbers ('1.234,56' / '1,234.56' / 'NULL') deterministically.
* Reject rows missing any LP-critical field.
* Deduplicate by row_id and emit sorted output (idempotent).
* Preserve full coverage of cleaned canonical labels.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from module_b_resource_allocation.constants import (
    CHANNEL_NAMES,
    DEPARTMENTS,
    WEEK_LABELS,
)
from module_b_resource_allocation.data.cleaner import (
    _parse_locale_number,
    clean_budget_lines,
    clean_directory,
)
from module_b_resource_allocation.data.dirty_generator import (
    DirtyGenConfig,
    generate_all,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,234.56", 1234.56),
        ("1.234,56", 1234.56),
        ("1234.56", 1234.56),
        ("1234,56", 1234.56),
        ("1,234", 1234.0),  # comma-thousands without decimals
        ("1.234", 1.234),  # ambiguous; single-dot defaults to decimal
        ("0,1", 0.1),
        ("Gs. 5,600,000.00", 5_600_000.0),
        ("US$ 1.500,00", 1500.0),
        ("", None),
        ("NULL", None),
        ("nan", None),
        (None, None),
    ],
)
def test_parse_locale_number(raw, expected) -> None:
    got = _parse_locale_number(raw)
    if expected is None:
        assert got is None
    else:
        assert abs(got - expected) < 1e-6, f"raw={raw!r} expected={expected} got={got}"


@pytest.fixture(scope="module")
def cleaned_frames(tmp_path_factory: pytest.TempPathFactory) -> dict[str, pd.DataFrame]:
    cfg = DirtyGenConfig(n_budget_rows=600, n_volunteer_rows=800, n_media_rows=350, seed=11)
    out = tmp_path_factory.mktemp("dirty")
    generate_all(cfg, out)
    return clean_directory(out)


def test_budget_lines_columns(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["budget_lines_clean"]
    assert set(df.columns) >= {
        "row_id",
        "vendor",
        "channel",
        "department",
        "iso_week",
        "currency",
        "amount_native",
        "fx_tier",
    }


def test_budget_lines_only_canonical_channels(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["budget_lines_clean"]
    assert set(df["channel"]).issubset(set(CHANNEL_NAMES))


def test_budget_lines_only_canonical_departments(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["budget_lines_clean"]
    assert set(df["department"]).issubset(set(DEPARTMENTS))


def test_budget_lines_currency_normalized(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["budget_lines_clean"]
    assert set(df["currency"]).issubset({"USD", "PYG"})


def test_budget_lines_amount_positive(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["budget_lines_clean"]
    assert (df["amount_native"] > 0).all()
    assert not df["amount_native"].isna().any()


def test_volunteer_logs_int_contacts(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["volunteer_logs_clean"]
    assert str(df["contacts"].dtype) == "int64"
    assert (df["contacts"] > 0).all()
    # Volunteer logs are field-collected canvassing/event work: every cleaned
    # row must map to the in-person / broadcast_to_bilateral classes.
    in_person_set = {"canvassing", "rallies_events", "sound_cars"}
    assert set(df["channel"]).issubset(in_person_set)


def test_media_buy_sheet_impressions(cleaned_frames: dict[str, pd.DataFrame]) -> None:
    df = cleaned_frames["media_buy_sheet_clean"]
    assert str(df["impressions"].dtype) == "int64"
    assert (df["impressions"] > 0).all()


def test_cleaner_is_idempotent() -> None:
    """Feeding a cleaned frame back through the cleaner must not change it."""
    cfg = DirtyGenConfig(n_budget_rows=200, n_volunteer_rows=200, n_media_rows=150, seed=7)
    base = Path("/tmp/module_b_dirty_idempotent_test")
    generate_all(cfg, base)
    first = clean_directory(base)

    # Re-render cleaned budget back into a "raw" shape and re-clean.
    bud = first["budget_lines_clean"].copy()
    bud["channel_text"] = bud["channel"]
    bud["department_text"] = bud["department"]
    bud["week_label"] = bud["iso_week"]
    bud["amount_text"] = bud["amount_native"].map(lambda x: f"{x:.2f}")
    bud["fx_tier_hint"] = bud["fx_tier"]
    cleaned_again = clean_budget_lines(bud).df

    bud_first_sorted = first["budget_lines_clean"].sort_values("row_id").reset_index(drop=True)
    cleaned_again_sorted = cleaned_again.sort_values("row_id").reset_index(drop=True)
    assert list(bud_first_sorted["row_id"]) == list(cleaned_again_sorted["row_id"])
    assert np.allclose(bud_first_sorted["amount_native"], cleaned_again_sorted["amount_native"])


def test_cleaner_rejects_missing_critical_fields() -> None:
    raw = pd.DataFrame(
        [
            {  # valid row
                "row_id": "B-0001",
                "vendor": "V001",
                "channel_text": "WhatsApp Chatbot",
                "department_text": "Central",
                "week_label": WEEK_LABELS[0],
                "currency": "USD",
                "amount_text": "1,234.56",
                "fx_tier_hint": "REF",
            },
            {  # invalid: empty channel
                "row_id": "B-0002",
                "vendor": "V002",
                "channel_text": "",
                "department_text": "Central",
                "week_label": WEEK_LABELS[0],
                "currency": "USD",
                "amount_text": "100.00",
                "fx_tier_hint": "REF",
            },
            {  # invalid: NULL amount
                "row_id": "B-0003",
                "vendor": "V003",
                "channel_text": "tv spots",
                "department_text": "Asunción",
                "week_label": WEEK_LABELS[0],
                "currency": "Gs.",
                "amount_text": "NULL",
                "fx_tier_hint": "REF",
            },
            {  # invalid: bogus week
                "row_id": "B-0004",
                "vendor": "V004",
                "channel_text": "radio_ad",
                "department_text": "Itapua",
                "week_label": "2018-W99",
                "currency": "PYG",
                "amount_text": "100,00",
                "fx_tier_hint": "RETAIL",
            },
        ]
    )
    cleaned = clean_budget_lines(raw).df
    assert list(cleaned["row_id"]) == ["B-0001"]


def test_cleaner_accent_strips_department() -> None:
    raw = pd.DataFrame(
        [
            {
                "row_id": "B-9001",
                "vendor": "V001",
                "channel_text": "WhatsApp Chatbot",
                "department_text": "Asunción",  # accent
                "week_label": WEEK_LABELS[0],
                "currency": "USD",
                "amount_text": "100.00",
                "fx_tier_hint": "REF",
            },
            {
                "row_id": "B-9002",
                "vendor": "V002",
                "channel_text": "Cuña Radio",
                "department_text": "Caaguazú",
                "week_label": WEEK_LABELS[3],
                "currency": "PYG",
                "amount_text": "1.000.000,00",
                "fx_tier_hint": "RETAIL",
            },
        ]
    )
    cleaned = clean_budget_lines(raw).df
    assert set(cleaned["department"]) == {"Asuncion", "Caaguazu"}
    assert set(cleaned["channel"]) == {"whatsapp_chatbot", "radio_spots"}


def test_cleaner_dedup_keeps_first_row() -> None:
    raw = pd.DataFrame(
        [
            {
                "row_id": "B-1001",
                "vendor": "V001",
                "channel_text": "WhatsApp Chatbot",
                "department_text": "Central",
                "week_label": WEEK_LABELS[0],
                "currency": "USD",
                "amount_text": "1000.00",
                "fx_tier_hint": "REF",
            },
        ]
        * 5
    )
    cleaned = clean_budget_lines(raw).df
    assert len(cleaned) == 1
