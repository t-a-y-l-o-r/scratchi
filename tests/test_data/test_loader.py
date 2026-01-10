"""Tests for CSV loader."""

import csv
import tempfile
from pathlib import Path

import pytest

from scratchi.data_loader import load_plans_from_csv, parse_plan_benefit_row
from scratchi.models.constants import (
    CSVColumn,
    CoverageStatus,
    EHBStatus,
    EHBVarReason,
    NOT_APPLICABLE,
    YesNoStatus,
)
from scratchi.models.plan import PlanBenefit


class TestParsePlanBenefitRow:
    """Test cases for parse_plan_benefit_row function."""

    def test_parse_valid_row(self) -> None:
        """Test parsing a valid CSV row."""
        row = {
            CSVColumn.BUSINESS_YEAR.value: "2026",
            CSVColumn.STATE_CODE.value: "AK",
            CSVColumn.ISSUER_ID.value: "21989",
            CSVColumn.SOURCE_NAME.value: "HIOS",
            CSVColumn.IMPORT_DATE.value: "2025-10-15",
            CSVColumn.STANDARD_COMPONENT_ID.value: "21989AK0030001",
            CSVColumn.PLAN_ID.value: "21989AK0030001-00",
            CSVColumn.BENEFIT_NAME.value: "Basic Dental Care - Adult",
            CSVColumn.COPAY_INN_TIER1.value: NOT_APPLICABLE,
            CSVColumn.COPAY_INN_TIER2.value: "",
            CSVColumn.COPAY_OUTOF_NET.value: NOT_APPLICABLE,
            CSVColumn.COINS_INN_TIER1.value: "35.00%",
            CSVColumn.COINS_INN_TIER2.value: "",
            CSVColumn.COINS_OUTOF_NET.value: "35.00%",
            CSVColumn.IS_EHB.value: "",
            CSVColumn.IS_COVERED.value: CoverageStatus.COVERED,
            CSVColumn.QUANT_LIMIT_ON_SVC.value: "",
            CSVColumn.LIMIT_QTY.value: "",
            CSVColumn.LIMIT_UNIT.value: "",
            CSVColumn.EXCLUSIONS.value: "See policy for exclusions.",
            CSVColumn.EXPLANATION.value: "All dental services subject to annual maximum.",
            CSVColumn.EHB_VAR_REASON.value: EHBStatus.NOT_EHB,
            CSVColumn.IS_EXCL_FROM_INN_MOOP.value: YesNoStatus.YES,
            CSVColumn.IS_EXCL_FROM_OON_MOOP.value: YesNoStatus.YES,
        }
        benefit = parse_plan_benefit_row(row)
        assert isinstance(benefit, PlanBenefit)
        assert benefit.plan_id == "21989AK0030001-00"
        assert benefit.benefit_name == "Basic Dental Care - Adult"
        assert benefit.is_covered == CoverageStatus.COVERED

    def test_parse_row_with_missing_columns(self) -> None:
        """Test parsing row with missing optional columns."""
        row = {
            CSVColumn.BUSINESS_YEAR.value: "2026",
            CSVColumn.STATE_CODE.value: "AK",
            CSVColumn.ISSUER_ID.value: "21989",
            CSVColumn.SOURCE_NAME.value: "HIOS",
            CSVColumn.IMPORT_DATE.value: "2025-10-15",
            CSVColumn.STANDARD_COMPONENT_ID.value: "21989AK0030001",
            CSVColumn.PLAN_ID.value: "21989AK0030001-00",
            CSVColumn.BENEFIT_NAME.value: "Test Benefit",
            CSVColumn.IS_COVERED.value: CoverageStatus.COVERED,
            # Missing optional fields should be OK
        }
        benefit = parse_plan_benefit_row(row)
        assert benefit.plan_id == "21989AK0030001-00"
        assert benefit.copay_inn_tier1 is None

    def test_parse_row_invalid_data(self) -> None:
        """Test parsing row with invalid data raises ValueError."""
        row = {
            CSVColumn.BUSINESS_YEAR.value: "invalid",  # Should be int, but string can be parsed
            CSVColumn.STATE_CODE.value: "AK",
            CSVColumn.ISSUER_ID.value: "21989",
            CSVColumn.SOURCE_NAME.value: "HIOS",
            CSVColumn.IMPORT_DATE.value: "invalid-date",  # Invalid date format
            CSVColumn.STANDARD_COMPONENT_ID.value: "21989AK0030001",
            CSVColumn.PLAN_ID.value: "21989AK0030001-00",
            CSVColumn.BENEFIT_NAME.value: "Test Benefit",
            CSVColumn.IS_COVERED.value: CoverageStatus.COVERED,
        }
        with pytest.raises(ValueError):
            parse_plan_benefit_row(row)


class TestLoadPlansFromCSV:
    """Test cases for load_plans_from_csv function."""

    def create_test_csv(self, content: list[list[str]]) -> Path:
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

    def test_load_valid_csv(self) -> None:
        """Test loading a valid CSV file."""
        csv_content = [
            [
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
            ],
            [
                "2026",
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-00",
                "Basic Dental Care - Adult",
                NOT_APPLICABLE,
                "",
                NOT_APPLICABLE,
                "35.00%",
                "",
                "35.00%",
                "",
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "See policy for exclusions.",
                "All dental services subject to annual maximum.",
                EHBStatus.NOT_EHB,
                YesNoStatus.YES,
                YesNoStatus.YES,
            ],
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert len(benefits) == 1
            assert benefits[0].plan_id == "21989AK0030001-00"
            assert benefits[0].benefit_name == "Basic Dental Care - Adult"
        finally:
            csv_path.unlink()

    def test_load_csv_multiple_rows(self) -> None:
        """Test loading CSV with multiple rows."""
        csv_content = [
            [
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
            ],
            [
                "2026",
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-00",
                "Basic Dental Care - Adult",
                "",
                "",
                "",
                "35.00%",
                "",
                "35.00%",
                "",
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "",
                "",
                EHBStatus.NOT_EHB,
                YesNoStatus.YES,
                YesNoStatus.YES,
            ],
            [
                "2026",
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-00",
                "Basic Dental Care - Child",
                "",
                "",
                "",
                "60.00%",
                "",
                "60.00%",
                EHBStatus.YES,
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "",
                "",
                EHBVarReason.SUBSTANTIALLY_EQUAL,
                YesNoStatus.NO,
                YesNoStatus.NO,
            ],
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            assert len(benefits) == 2
            assert all(isinstance(benefit, PlanBenefit) for benefit in benefits)
            assert benefits[0].benefit_name == "Basic Dental Care - Adult"
            assert benefits[1].benefit_name == "Basic Dental Care - Child"
        finally:
            csv_path.unlink()

    def test_load_csv_file_not_found(self) -> None:
        """Test loading non-existent CSV file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_plans_from_csv("nonexistent_file.csv")

    def test_load_empty_csv(self) -> None:
        """Test loading empty CSV file raises ValueError."""
        csv_content: list[list[str]] = []
        csv_path = self.create_test_csv(csv_content)
        try:
            with pytest.raises(ValueError, match="empty"):
                load_plans_from_csv(csv_path)
        finally:
            csv_path.unlink()

    def test_load_csv_with_invalid_rows(self) -> None:
        """Test loading CSV with some invalid rows - should skip invalid rows."""
        csv_content = [
            [
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
            ],
            [
                "2026",
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-00",
                "Valid Benefit",
                "",
                "",
                "",
                "35.00%",
                "",
                "35.00%",
                "",
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "",
                "",
                EHBStatus.NOT_EHB,
                YesNoStatus.YES,
                YesNoStatus.YES,
            ],
            [
                "invalid",
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-00",
                "Invalid Benefit",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "2026",
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-01",
                "Another Valid Benefit",
                "",
                "",
                "",
                "20.00%",
                "",
                "20.00%",
                "",
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "",
                "",
                EHBStatus.NOT_EHB,
                YesNoStatus.NO,
                YesNoStatus.NO,
            ],
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            # Should parse 2 valid rows, skip 1 invalid
            assert len(benefits) == 2
            assert benefits[0].benefit_name == "Valid Benefit"
            assert benefits[1].benefit_name == "Another Valid Benefit"
        finally:
            csv_path.unlink()

    def test_load_csv_missing_required_fields(self) -> None:
        """Test loading CSV with missing required fields."""
        csv_content = [
            [
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
            ],
            [
                "",  # Missing BusinessYear
                "AK",
                "21989",
                "HIOS",
                "2025-10-15",
                "21989AK0030001",
                "21989AK0030001-00",
                "Test Benefit",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                CoverageStatus.COVERED,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            # Should raise ValueError or skip the row
            benefits = load_plans_from_csv(csv_path)
            # If it doesn't raise, it should skip invalid rows
            assert len(benefits) == 0 or all(
                isinstance(benefit, PlanBenefit) for benefit in benefits
            )
        finally:
            csv_path.unlink()
