"""Unit tests for private helpers in ``population_segmentation.data.raw_injector``."""

from __future__ import annotations

import pandas as pd
from population_segmentation.data.raw_injector import (
    _ENCODING_GARBLES,
    _add_raw_fields,
    _garble_encoding,
    _randomize_phone_format,
)
from population_segmentation.utils.schema import (
    AGE_ON_EVENT_DATE,
    CEDULA,
    DEPARTMENT,
    DOB,
    FIRST_NAME,
    LAST_NAME,
    PHONE,
    QUALITATIVE_DISTRICT,
    QUALITATIVE_SENTIMENT,
)
from population_segmentation.utils.seeds import make_rng


def test_garble_encoding_replaces_first_accent_match() -> None:
    char = next(iter(_ENCODING_GARBLES))
    garbled = _ENCODING_GARBLES[char]
    name = f"X{char}Y"
    out = _garble_encoding(name)
    assert out == f"X{garbled}Y"


def test_garble_encoding_ascii_unchanged() -> None:
    assert _garble_encoding("Smith") == "Smith"


def test_garble_encoding_non_string_passthrough() -> None:
    assert _garble_encoding(123) == 123  # type: ignore[arg-type]


def test_randomize_phone_format_deterministic_with_seed() -> None:
    rng = make_rng(7)
    base = "+595981123456"
    a = _randomize_phone_format(base, rng)
    rng = make_rng(7)
    b = _randomize_phone_format(base, rng)
    assert a == b
    digits = "".join(c for c in a if c.isdigit())
    assert len(digits) >= 9


def test_add_raw_fields_populates_raw_layer_columns() -> None:
    n = 5
    df = pd.DataFrame({AGE_ON_EVENT_DATE: [35] * n, DEPARTMENT: ["Central"] * n})
    rng = make_rng(1)
    out = _add_raw_fields(df.copy(), n, rng)
    assert CEDULA in out.columns and DOB in out.columns
    assert FIRST_NAME in out.columns and LAST_NAME in out.columns
    assert PHONE in out.columns
    assert QUALITATIVE_SENTIMENT in out.columns
    assert QUALITATIVE_DISTRICT in out.columns
    assert len(out) == n
