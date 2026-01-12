"""Tests for CSV loader."""

import csv
import tempfile
from pathlib import Path
from typing import Any

import pytest

from scratchi.data_loader import (
    aggregate_plans_from_benefits,
    create_plan_index,
    load_plans_from_csv,
    load_plans_from_csv_aggregated,
    parse_plan_benefit_row,
)
from scratchi.models.constants import (
    CSVColumn,
    CoverageStatus,
    EHBStatus,
    EHBVarReason,
    NOT_APPLICABLE,
    YesNoStatus,
)
from scratchi.models.plan import PlanBenefit

# Constants for test data
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


def create_base_test_row(
    business_year: str = "2026",
    state_code: str = "AK",
    issuer_id: str = "21989",
    source_name: str = "HIOS",
    import_date: str = "2025-10-15",
    standard_component_id: str = "21989AK0030001",
    plan_id: str = "21989AK0030001-00",
    benefit_name: str = "Test Benefit",
    is_covered: str = CoverageStatus.COVERED,
    **overrides: Any,
) -> dict[str, Any]:
    """Create a base test row dictionary with common defaults.

    Args:
        business_year: Business year value
        state_code: State code value
        issuer_id: Issuer ID value
        source_name: Source name value
        import_date: Import date value
        standard_component_id: Standard component ID value
        plan_id: Plan ID value
        benefit_name: Benefit name value
        is_covered: Coverage status value
        **overrides: Additional fields or overrides for default values

    Returns:
        Dictionary with CSV column names as keys
    """
    row = {
        CSVColumn.BUSINESS_YEAR.value: business_year,
        CSVColumn.STATE_CODE.value: state_code,
        CSVColumn.ISSUER_ID.value: issuer_id,
        CSVColumn.SOURCE_NAME.value: source_name,
        CSVColumn.IMPORT_DATE.value: import_date,
        CSVColumn.STANDARD_COMPONENT_ID.value: standard_component_id,
        CSVColumn.PLAN_ID.value: plan_id,
        CSVColumn.BENEFIT_NAME.value: benefit_name,
        CSVColumn.IS_COVERED.value: is_covered,
    }
    row.update(overrides)
    return row


def create_csv_data_row(
    business_year: str = "2026",
    state_code: str = "AK",
    issuer_id: str = "21989",
    source_name: str = "HIOS",
    import_date: str = "2025-10-15",
    standard_component_id: str = "21989AK0030001",
    plan_id: str = "21989AK0030001-00",
    benefit_name: str = "Test Benefit",
    copay_inn_tier1: str = "",
    copay_inn_tier2: str = "",
    copay_outof_net: str = "",
    coins_inn_tier1: str = "",
    coins_inn_tier2: str = "",
    coins_outof_net: str = "",
    is_ehb: str = "",
    is_covered: str = CoverageStatus.COVERED,  # StrEnum value is already a string
    quant_limit_on_svc: str = "",
    limit_qty: str = "",
    limit_unit: str = "",
    exclusions: str = "",
    explanation: str = "",
    ehb_var_reason: str = "",
    is_excl_from_inn_moop: str = "",
    is_excl_from_oon_moop: str = "",
) -> list[str]:
    """Create a CSV data row list matching the header order.

    Args:
        business_year: Business year value
        state_code: State code value
        issuer_id: Issuer ID value
        source_name: Source name value
        import_date: Import date value
        standard_component_id: Standard component ID value
        plan_id: Plan ID value
        benefit_name: Benefit name value
        copay_inn_tier1: Copay in-network tier 1 value
        copay_inn_tier2: Copay in-network tier 2 value
        copay_outof_net: Copay out-of-network value
        coins_inn_tier1: Coinsurance in-network tier 1 value
        coins_inn_tier2: Coinsurance in-network tier 2 value
        coins_outof_net: Coinsurance out-of-network value
        is_ehb: Is EHB value (StrEnum values are strings)
        is_covered: Coverage status value (StrEnum values are strings)
        quant_limit_on_svc: Quantity limit on service value
        limit_qty: Limit quantity value
        limit_unit: Limit unit value
        exclusions: Exclusions value
        explanation: Explanation value
        ehb_var_reason: EHB variation reason value (StrEnum values are strings)
        is_excl_from_inn_moop: Is excluded from in-network MOOP value (StrEnum values are strings)
        is_excl_from_oon_moop: Is excluded from out-of-network MOOP value (StrEnum values are strings)

    Returns:
        List of string values matching CSV_HEADER_ROW order
    """
    # StrEnum values are already strings in Python 3.11+, so no conversion needed
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


class TestParsePlanBenefitRow:
    """Test cases for parse_plan_benefit_row function."""

    def test_parse_valid_row(self) -> None:
        """Test parsing a valid CSV row."""
        row = create_base_test_row(
            benefit_name="Basic Dental Care - Adult",
            **{
                CSVColumn.COPAY_INN_TIER1.value: NOT_APPLICABLE,
                CSVColumn.COPAY_INN_TIER2.value: "",
                CSVColumn.COPAY_OUTOF_NET.value: NOT_APPLICABLE,
                CSVColumn.COINS_INN_TIER1.value: "35.00%",
                CSVColumn.COINS_INN_TIER2.value: "",
                CSVColumn.COINS_OUTOF_NET.value: "35.00%",
                CSVColumn.IS_EHB.value: "",
                CSVColumn.QUANT_LIMIT_ON_SVC.value: "",
                CSVColumn.LIMIT_QTY.value: "",
                CSVColumn.LIMIT_UNIT.value: "",
                CSVColumn.EXCLUSIONS.value: "See policy for exclusions.",
                CSVColumn.EXPLANATION.value: "All dental services subject to annual maximum.",
                CSVColumn.EHB_VAR_REASON.value: EHBStatus.NOT_EHB,
                CSVColumn.IS_EXCL_FROM_INN_MOOP.value: YesNoStatus.YES,
                CSVColumn.IS_EXCL_FROM_OON_MOOP.value: YesNoStatus.YES,
            },
        )
        benefit = parse_plan_benefit_row(row)
        assert isinstance(benefit, PlanBenefit)
        assert benefit.plan_id == "21989AK0030001-00"
        assert benefit.benefit_name == "Basic Dental Care - Adult"
        assert benefit.is_covered == CoverageStatus.COVERED

    def test_parse_row_with_missing_columns(self) -> None:
        """Test parsing row with missing optional columns."""
        row = create_base_test_row()
        # Missing optional fields should be OK
        benefit = parse_plan_benefit_row(row)
        assert benefit.plan_id == "21989AK0030001-00"
        assert benefit.copay_inn_tier1 is None

    def test_parse_row_invalid_data(self) -> None:
        """Test parsing row with invalid data raises ValueError."""
        row = create_base_test_row(
            business_year="invalid",  # Should be int, but string can be parsed
            import_date="invalid-date",  # Invalid date format
        )
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
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name="Basic Dental Care - Adult",
                copay_inn_tier1=NOT_APPLICABLE,
                copay_outof_net=NOT_APPLICABLE,
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                exclusions="See policy for exclusions.",
                explanation="All dental services subject to annual maximum.",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
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
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name="Basic Dental Care - Adult",
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_csv_data_row(
                benefit_name="Basic Dental Care - Child",
                coins_inn_tier1="60.00%",
                coins_outof_net="60.00%",
                is_ehb=EHBStatus.YES,
                ehb_var_reason=EHBVarReason.SUBSTANTIALLY_EQUAL,
                is_excl_from_inn_moop=YesNoStatus.NO,
                is_excl_from_oon_moop=YesNoStatus.NO,
            ),
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
            CSV_HEADER_ROW,
            create_csv_data_row(
                benefit_name="Valid Benefit",
                coins_inn_tier1="35.00%",
                coins_outof_net="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_csv_data_row(
                business_year="invalid",  # Invalid year
                benefit_name="Invalid Benefit",
            ),
            create_csv_data_row(
                plan_id="21989AK0030001-01",
                benefit_name="Another Valid Benefit",
                coins_inn_tier1="20.00%",
                coins_outof_net="20.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.NO,
                is_excl_from_oon_moop=YesNoStatus.NO,
            ),
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
            CSV_HEADER_ROW,
            create_csv_data_row(
                business_year="",  # Missing BusinessYear (required field)
            ),
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            # Should raise ValueError when all rows are invalid
            with pytest.raises(ValueError, match="No valid plan benefits found"):
                load_plans_from_csv(csv_path)
        finally:
            csv_path.unlink()


class TestPlanAggregation:
    """Test cases for plan aggregation functionality."""

    def test_aggregate_plans_from_csv_benefits(self) -> None:
        """Test aggregating plans from CSV-loaded benefits."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                plan_id="PLAN-001",
                benefit_name="Basic Dental Care - Adult",
                coins_inn_tier1="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_csv_data_row(
                plan_id="PLAN-001",
                benefit_name="Basic Dental Care - Child",
                coins_inn_tier1="60.00%",
                is_ehb=EHBStatus.YES,
                ehb_var_reason=EHBVarReason.SUBSTANTIALLY_EQUAL,
                is_excl_from_inn_moop=YesNoStatus.NO,
                is_excl_from_oon_moop=YesNoStatus.NO,
            ),
            create_csv_data_row(
                plan_id="PLAN-002",
                benefit_name="Orthodontia - Child",
                coins_inn_tier1="50.00%",
                is_ehb=EHBStatus.YES,
                ehb_var_reason=EHBVarReason.SUBSTANTIALLY_EQUAL,
                is_excl_from_inn_moop=YesNoStatus.NO,
                is_excl_from_oon_moop=YesNoStatus.NO,
            ),
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            benefits = load_plans_from_csv(csv_path)
            plans = aggregate_plans_from_benefits(benefits)

            assert len(plans) == 2
            plan_ids = {plan.plan_id for plan in plans}
            assert plan_ids == {"PLAN-001", "PLAN-002"}

            plan_001 = next(p for p in plans if p.plan_id == "PLAN-001")
            assert len(plan_001.benefits) == 2
            assert "Basic Dental Care - Adult" in plan_001.benefits
            assert "Basic Dental Care - Child" in plan_001.benefits

            plan_002 = next(p for p in plans if p.plan_id == "PLAN-002")
            assert len(plan_002.benefits) == 1
            assert "Orthodontia - Child" in plan_002.benefits
        finally:
            csv_path.unlink()

    def test_load_plans_from_csv_aggregated(self) -> None:
        """Test loading and aggregating plans in one step."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                plan_id="PLAN-001",
                benefit_name="Benefit 1",
                coins_inn_tier1="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_csv_data_row(
                plan_id="PLAN-001",
                benefit_name="Benefit 2",
                coins_inn_tier1="60.00%",
                is_ehb=EHBStatus.YES,
                ehb_var_reason=EHBVarReason.SUBSTANTIALLY_EQUAL,
                is_excl_from_inn_moop=YesNoStatus.NO,
                is_excl_from_oon_moop=YesNoStatus.NO,
            ),
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            plans = load_plans_from_csv_aggregated(csv_path)

            assert len(plans) == 1
            assert plans[0].plan_id == "PLAN-001"
            assert len(plans[0].benefits) == 2
        finally:
            csv_path.unlink()

    def test_create_plan_index(self) -> None:
        """Test creating a plan index for fast lookup."""
        csv_content = [
            CSV_HEADER_ROW,
            create_csv_data_row(
                plan_id="PLAN-001",
                benefit_name="Benefit 1",
                coins_inn_tier1="35.00%",
                ehb_var_reason=EHBStatus.NOT_EHB,
                is_excl_from_inn_moop=YesNoStatus.YES,
                is_excl_from_oon_moop=YesNoStatus.YES,
            ),
            create_csv_data_row(
                plan_id="PLAN-002",
                benefit_name="Benefit 2",
                coins_inn_tier1="60.00%",
                is_ehb=EHBStatus.YES,
                ehb_var_reason=EHBVarReason.SUBSTANTIALLY_EQUAL,
                is_excl_from_inn_moop=YesNoStatus.NO,
                is_excl_from_oon_moop=YesNoStatus.NO,
            ),
        ]
        csv_path = self.create_test_csv(csv_content)
        try:
            plans = load_plans_from_csv_aggregated(csv_path)
            index = create_plan_index(plans)

            assert len(index) == 2
            assert "PLAN-001" in index
            assert "PLAN-002" in index

            plan_001 = index["PLAN-001"]
            assert plan_001.plan_id == "PLAN-001"
            assert "Benefit 1" in plan_001.benefits
        finally:
            csv_path.unlink()
