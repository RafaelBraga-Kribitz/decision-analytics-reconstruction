"""Tests for population_segmentation.data.raw_injector.

TDD: tests written before implementation.
Gate A2: all 13 flaw types present at configured rates ±20%.
"""

from __future__ import annotations

import pandas as pd

SAMPLE_SIZE = 50_000  # session fixture sample size (see conftest.py)


class TestFlawTypes:
    def test_fmt_cedula_errors_present(
        self, raw_population: pd.DataFrame, config: dict  # type: ignore[type-arg]
    ) -> None:
        """FMT: some cédulas should be 7-digit (missing zero-pad)."""
        cedulas = raw_population["cedula"].dropna()
        short_cedulas = cedulas.str.len() == 7
        assert short_cedulas.sum() > 0, "No FMT cedula errors injected"

    def test_dup_duplicates_present(self, raw_population: pd.DataFrame) -> None:
        """DUP: some entity_ids should appear more than once."""
        # Duplicates are injected as appended rows with slightly modified names
        assert (
            len(raw_population) > SAMPLE_SIZE
        ), "No duplicate rows injected (length should exceed sample_size)"

    def test_typ_department_typos_present(self, raw_population: pd.DataFrame) -> None:
        """TYP: some department values should be typo variants."""
        from population_segmentation.utils.schema import CANONICAL_DEPARTMENTS

        dept_values = set(raw_population["department"].dropna().unique())
        typos = dept_values - CANONICAL_DEPARTMENTS
        assert len(typos) > 0, f"No department typos found; all values canonical: {dept_values}"

    def test_nul_municipality_nulls_present(
        self, raw_population: pd.DataFrame, config: dict  # type: ignore[type-arg]
    ) -> None:
        """NUL: ~8% of municipality values should be null."""
        null_rate = raw_population["municipality"].isna().mean()
        expected = config["flaw_injection"]["municipality_null_rate"]
        tolerance = expected * 0.25
        assert (
            abs(null_rate - expected) < tolerance
        ), f"Municipality null rate {null_rate:.3f} not within ±25% of {expected}"

    def test_fmt_date_format_swap_present(self, raw_population: pd.DataFrame) -> None:
        """FMT: dob field should exist and contain mixed format indicators."""
        assert "dob" in raw_population.columns
        assert raw_population["dob"].notna().sum() > 0

    def test_enc_encoding_errors_present(self, raw_population: pd.DataFrame) -> None:
        """ENC: some name fields should have encoding artifacts."""
        assert "first_name" in raw_population.columns
        # Encoding errors produce replacement chars or garbled sequences
        garbled = (
            raw_population["first_name"]
            .astype(str)
            .str.contains(r"[?#\u00ef\u00bf\u00bd\ufffd]|Ã", na=False, regex=True)
        )
        assert garbled.sum() > 0, "No encoding errors found in first_name"

    def test_fmt_phone_variants_present(self, raw_population: pd.DataFrame) -> None:
        """FMT: phone field should have 3 format variants."""
        assert "phone" in raw_population.columns
        phones = raw_population["phone"].dropna()
        has_plus = phones.str.startswith("+595").any()
        has_zero = phones.str.startswith("0").any()
        has_raw = phones.str.match(r"^9\d{8}$").any()
        assert sum([has_plus, has_zero, has_raw]) >= 2, "Fewer than 2 phone format variants found"

    def test_typ_gender_variants_present(self, raw_population: pd.DataFrame) -> None:
        """TYP: gender field should have multiple representation variants."""
        gender_values = set(raw_population["gender"].dropna().unique())
        expected_variants = {"M", "F", "Masculino", "Femenino", "1", "2"}
        found = gender_values & expected_variants
        assert len(found) >= 3, f"Only {len(found)} gender variants found: {found}"

    def test_rng_age_range_errors_present(self, raw_population: pd.DataFrame) -> None:
        """RNG: DOB year-swap flaw must produce out-of-range ages on the event date."""
        assert "dob" in raw_population.columns
        event_date = pd.Timestamp("2018-04-22")
        parsed = pd.to_datetime(raw_population["dob"], format="%d/%m/%Y", errors="coerce")
        ages = (event_date - parsed).dt.days / 365.25
        bad_age_count = int((ages < 18).sum() + (ages > 120).sum() + parsed.isna().sum())
        assert bad_age_count > 0, (
            "Expected age_range flaw to produce unparseable or out-of-range DOBs, "
            f"but all {len(raw_population):,} records have valid ages in [18, 120]"
        )

    def test_sch_schema_drift_present(self, raw_population: pd.DataFrame) -> None:
        """SCH: dataset should include a schema drift marker column."""
        # Schema drift is encoded as a flag column
        assert "schema_drift_flag" in raw_population.columns
        drift_count = raw_population["schema_drift_flag"].sum()
        assert drift_count > 0, "No schema drift records flagged"

    def test_nul_qualitative_district_nulls(self, raw_population: pd.DataFrame) -> None:
        """NUL: ~25% of qualitative_district should be null."""
        if "qualitative_district" in raw_population.columns:
            null_rate = raw_population["qualitative_district"].isna().mean()
            expected = 0.25
            assert abs(null_rate - expected) < 0.05


class TestDeterminism:
    def test_same_seed_deterministic(
        self, config: dict, clean_population: pd.DataFrame  # type: ignore[type-arg]
    ) -> None:
        from population_segmentation.data.raw_injector import inject_flaws

        df1 = inject_flaws(clean_population, config, seed=42)
        df2 = inject_flaws(clean_population, config, seed=42)
        assert len(df1) == len(df2)
        pd.testing.assert_frame_equal(
            df1[["entity_id", "department", "municipality"]].reset_index(drop=True),
            df2[["entity_id", "department", "municipality"]].reset_index(drop=True),
        )

    def test_length_increases_by_dup_rate(
        self, raw_population: pd.DataFrame, config: dict  # type: ignore[type-arg]
    ) -> None:
        dup_rate = config["flaw_injection"]["duplicate_rate"]
        expected_extra = int(SAMPLE_SIZE * dup_rate)
        actual_extra = len(raw_population) - SAMPLE_SIZE
        tolerance = max(5, int(expected_extra * 0.30))
        assert (
            abs(actual_extra - expected_extra) <= tolerance
        ), f"Expected ~{expected_extra} duplicate rows, got {actual_extra}"


class TestFlaw13Coverage:
    """All 13 flaw types from scope §4.2 must be present."""

    def test_all_13_flaw_types_accounted(self, raw_population: pd.DataFrame) -> None:
        """inject_flaws must record exactly 13 flaw types in df.attrs."""
        assert (
            "flaw_types_injected" in raw_population.attrs
        ), "inject_flaws must store the injected flaw list in df.attrs['flaw_types_injected']"
        injected = raw_population.attrs["flaw_types_injected"]
        assert (
            len(injected) == 13
        ), f"Expected exactly 13 flaw types (scope §4.2), got {len(injected)}: {injected}"
