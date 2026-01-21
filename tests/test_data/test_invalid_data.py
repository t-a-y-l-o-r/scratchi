"""Tests for invalid data handling and security concerns.

This module tests how the system handles:
- Invalid enum values
- Non-numeric values in numeric fields
- Extremely long strings
- Special characters and security concerns (SQL injection, XSS)
"""

import csv
import tempfile
from pathlib import Path

import pytest

from scratchi.data_loader import load_plans_from_csv
from scratchi.models.constants import (
    CSVColumn,
    CoverageStatus,
    EHBStatus,
    NOT_APPLICABLE,
    YesNoStatus,
)


def create_test_csv(content: list[list[str]]) -> Path:
    """Create a temporary CSV file with given content."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
    ) as temp_file:
        writer = csv.writer(temp_file)
        writer.writerows(content)
        return Path(temp_file.name)


CSV_HEADER_ROW = [
    CSVColumn.BUSINESS_YEAR.value,
    CSVColumn.STATE_CODE.value,
    CSVColumn.ISSUER_ID.value,
    CSVColumn.SOURCE_NAME.value,
    CSVColumn.IMPORT_DATE.value,
    CSVColumn.STANDARD_COMPONENT_ID.value,
    CSVColumn.PLAN_ID.value,
    CSVColumn.BENEFIT_NAME.value,
    CSVColumn.COPAY_INN_TIER1.value,
    CSVColumn.COPAY_INN_TIER2.value,
    CSVColumn.COPAY_OUTOF_NET.value,
    CSVColumn.COINS_INN_TIER1.value,
    CSVColumn.COINS_INN_TIER2.value,
    CSVColumn.COINS_OUTOF_NET.value,
    CSVColumn.IS_EHB.value,
    CSVColumn.IS_COVERED.value,
    CSVColumn.QUANT_LIMIT_ON_SVC.value,
    CSVColumn.LIMIT_QTY.value,
    CSVColumn.LIMIT_UNIT.value,
    CSVColumn.EXCLUSIONS.value,
    CSVColumn.EXPLANATION.value,
    CSVColumn.EHB_VAR_REASON.value,
    CSVColumn.IS_EXCL_FROM_INN_MOOP.value,
    CSVColumn.IS_EXCL_FROM_OON_MOOP.value,
]


def create_csv_data_row(
    business_year: str = "2026",
    state_code: str = "AK",
    issuer_id: str = "21989",
    source_name: str = "HIOS",
    import_date: str = "2025-10-15",
    standard_component_id: str = "21989AK0030001",
    plan_id: str = "21989AK0030001-00",
    benefit_name: str = "Basic Dental Care - Adult",
    copay_inn_tier1: str = NOT_APPLICABLE,
    copay_inn_tier2: str = "",
    copay_outof_net: str = NOT_APPLICABLE,
    coins_inn_tier1: str = "",
    coins_inn_tier2: str = "",
    coins_outof_net: str = "",
    is_ehb: str = "",
    is_covered: str = CoverageStatus.COVERED,
    quant_limit_on_svc: str = "",
    limit_qty: str = "",
    limit_unit: str = "",
    exclusions: str = "",
    explanation: str = "",
    ehb_var_reason: str = "",
    is_excl_from_inn_moop: str = "",
    is_excl_from_oon_moop: str = "",
) -> list[str]:
    """Create a CSV data row list matching the header order."""
    return [
        business_year,
        state_code,
        issuer_id,
        source_name,
        import_date,
        standard_component_id,
        plan_id,
        benefit_name,
        copay_inn_tier1,
        copay_inn_tier2,
        copay_outof_net,
        coins_inn_tier1,
        coins_inn_tier2,
        coins_outof_net,
        is_ehb,
        is_covered,
        quant_limit_on_svc,
        limit_qty,
        limit_unit,
        exclusions,
        explanation,
        ehb_var_reason,
        is_excl_from_inn_moop,
        is_excl_from_oon_moop,
    ]


def create_valid_row() -> list[str]:
    """Create a valid CSV data row."""
    return create_csv_data_row(
        coins_inn_tier1="35.00%",
        coins_outof_net="35.00%",
        is_covered=CoverageStatus.COVERED,
        ehb_var_reason=EHBStatus.NOT_EHB,
        is_excl_from_inn_moop=YesNoStatus.YES,
        is_excl_from_oon_moop=YesNoStatus.YES,
    )


class TestInvalidEnumValues:
    """Test handling of invalid enum values in CSV."""

    def test_invalid_coverage_status(self) -> None:
        """Test invalid value for IsCovered field (e.g., 'Maybe')."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                is_covered="Maybe",  # Invalid
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            # Should skip invalid row or raise appropriate error
            benefits = load_plans_from_csv(csv_path)
            # If it doesn't crash, that's good - invalid row should be skipped
            assert isinstance(benefits, list)
        finally:
            csv_path.unlink()

    def test_invalid_yes_no_status(self) -> None:
        """Test invalid value for Yes/No field (e.g., 'Maybe')."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                is_excl_from_inn_moop="Maybe",  # Invalid
                is_excl_from_oon_moop="Maybe",  # Invalid
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should handle gracefully
            assert isinstance(benefits, list)
        finally:
            csv_path.unlink()

    def test_invalid_ehb_status(self) -> None:
        """Test invalid value for EHB field."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                ehb_var_reason="InvalidEHB",  # Invalid
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
        finally:
            csv_path.unlink()


class TestNonNumericValues:
    """Test handling of non-numeric values in numeric fields."""

    def test_non_numeric_business_year(self) -> None:
        """Test non-numeric value in BusinessYear field."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                business_year="invalid-year",  # Invalid
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            # Should raise ValueError when all rows are invalid
            with pytest.raises(ValueError, match="No valid plan benefits found"):
                load_plans_from_csv(csv_path)
        finally:
            csv_path.unlink()

    def test_non_numeric_limit_qty(self) -> None:
        """Test non-numeric value in LimitQty field."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                limit_qty="not-a-number",  # Invalid
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
        finally:
            csv_path.unlink()


class TestExtremelyLongStrings:
    """Test handling of extremely long strings in text fields."""

    def test_long_benefit_name(self) -> None:
        """Test extremely long benefit name."""
        long_name = "A" * 10000  # 10KB string
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name=long_name,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should handle long strings without crashing
            assert isinstance(benefits, list)
            if benefits:
                # Benefit name should be stored as-is
                assert len(benefits[0].benefit_name) > 0
        finally:
            csv_path.unlink()

    def test_long_explanation(self) -> None:
        """Test extremely long explanation field."""
        long_explanation = "B" * 50000  # 50KB string
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                explanation=long_explanation,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
            if benefits:
                # Explanation should be stored
                assert benefits[0].explanation is not None
                assert len(benefits[0].explanation) > 0
        finally:
            csv_path.unlink()

    def test_long_exclusions(self) -> None:
        """Test extremely long exclusions field."""
        long_exclusions = "C" * 20000  # 20KB string
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                exclusions=long_exclusions,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
        finally:
            csv_path.unlink()


class TestSpecialCharactersAndSecurity:
    """Test handling of special characters and security concerns."""

    def test_sql_injection_attempt_in_benefit_name(self) -> None:
        """Test SQL injection attempt in benefit name field."""
        sql_injection = "'; DROP TABLE plans; --"
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name=sql_injection,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should handle as regular text, not execute SQL
            assert isinstance(benefits, list)
            if benefits:
                assert sql_injection in benefits[0].benefit_name
        finally:
            csv_path.unlink()

    def test_xss_attempt_in_explanation(self) -> None:
        """Test XSS attempt in explanation field."""
        xss_attempt = "<script>alert('XSS')</script>"
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                explanation=xss_attempt,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should store as text, not execute script
            assert isinstance(benefits, list)
            if benefits:
                assert xss_attempt in (benefits[0].explanation or "")
        finally:
            csv_path.unlink()

    def test_special_characters_in_plan_id(self) -> None:
        """Test special characters in plan_id field."""
        special_chars = "PLAN-001'; -- <>&\"'"
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                plan_id=special_chars,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
            if benefits:
                assert special_chars in benefits[0].plan_id
        finally:
            csv_path.unlink()

    def test_newlines_in_text_fields(self) -> None:
        """Test newlines and control characters in text fields."""
        text_with_newlines = "Line 1\nLine 2\r\nLine 3\tTabbed"
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name=text_with_newlines,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
            if benefits:
                # Should preserve or sanitize newlines
                assert len(benefits[0].benefit_name) > 0
        finally:
            csv_path.unlink()

    def test_unicode_characters(self) -> None:
        """Test Unicode characters in text fields."""
        unicode_text = "Plan with émojis 🦷 and 中文 characters"
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name=unicode_text,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert isinstance(benefits, list)
            if benefits:
                assert unicode_text in benefits[0].benefit_name
        finally:
            csv_path.unlink()

    def test_null_bytes(self) -> None:
        """Test null bytes in text fields (should be handled safely)."""
        text_with_null = "Text\x00with\x00null\x00bytes"
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name=text_with_null,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should handle null bytes safely
            assert isinstance(benefits, list)
        finally:
            csv_path.unlink()


class TestMixedValidAndInvalidRows:
    """Test handling when CSV contains both valid and invalid rows."""

    def test_mixed_valid_invalid_rows(self) -> None:
        """Test CSV with mix of valid and invalid rows."""
        csv_content = [
            CSV_HEADER_ROW,
            create_valid_row(),  # Valid row
            create_csv_data_row(
                business_year="invalid-year",  # Invalid
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_valid_row(),  # Valid row
            create_csv_data_row(
                is_covered="Maybe",  # Invalid enum
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_valid_row(),  # Valid row
        ]
        csv_path = create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should parse valid rows and skip invalid ones
            assert len(benefits) >= 3  # At least 3 valid rows
            assert all(
                benefit.plan_id == "21989AK0030001-00" for benefit in benefits
            )
        finally:
            csv_path.unlink()

    def test_all_invalid_rows(self) -> None:
        """Test CSV where all rows are invalid."""
        csv_content = [
            CSV_HEADER_ROW,
            ["invalid"] * 24,  # All invalid
            create_csv_data_row(
                business_year="invalid-year",  # Invalid year
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                is_covered=CoverageStatus.COVERED,
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
        ]
        csv_path = create_test_csv(csv_content)
        try:
            with pytest.raises(ValueError, match="No valid plan benefits found"):
                load_plans_from_csv(csv_path)
        finally:
            csv_path.unlink()
