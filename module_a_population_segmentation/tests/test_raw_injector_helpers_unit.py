"""Unit tests for private helpers in ``population_segmentation.data.raw_injector``."""

from __future__ import annotations

from population_segmentation.data.raw_injector import (
    _ENCODING_GARBLES,
    _garble_encoding,
    _randomize_phone_format,
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
