"""Tests for PlanBenefit model."""

from datetime import date

import pytest

from scratchi.models.constants import (
    NO_CHARGE,
    NOT_APPLICABLE,
    CoverageStatus,
    EHBStatus,
    YesNoStatus,
)
from scratchi.models.plan import PlanBenefit


class TestPlanBenefit:
    """Test cases for PlanBenefit model."""

    def test_create_valid_plan_benefit(self) -> None:
        """Test creating a valid PlanBenefit from complete data."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Basic Dental Care - Adult",
            "copay_inn_tier1": NOT_APPLICABLE,
            "copay_inn_tier2": None,
            "copay_outof_net": NOT_APPLICABLE,
            "coins_inn_tier1": "35.00%",
            "coins_inn_tier2": None,
            "coins_outof_net": "35.00%",
            "is_ehb": None,
            "is_covered": CoverageStatus.COVERED,
            "quant_limit_on_svc": None,
            "limit_qty": None,
            "limit_unit": None,
            "exclusions": "See policy for exclusions.",
            "explanation": "All dental services subject to annual maximum.",
            "ehb_var_reason": EHBStatus.NOT_EHB,
            "is_excl_from_inn_moop": YesNoStatus.YES,
            "is_excl_from_oon_moop": YesNoStatus.YES,
        }
        benefit = PlanBenefit(**data)
        assert benefit.plan_id == "21989AK0030001-00"
        assert benefit.benefit_name == "Basic Dental Care - Adult"
        assert benefit.is_covered == CoverageStatus.COVERED

    def test_parse_date_string(self) -> None:
        """Test parsing date from ISO format string."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.import_date == date(2025, 10, 15)

    def test_parse_date_object(self) -> None:
        """Test parsing date from date object."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": date(2025, 10, 15),
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.import_date == date(2025, 10, 15)

    def test_normalize_empty_strings_to_none(self) -> None:
        """Test that empty strings are normalized to None."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "copay_inn_tier1": "",
            "copay_inn_tier2": "",
            "coins_inn_tier1": "",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.copay_inn_tier1 is None
        assert benefit.copay_inn_tier2 is None
        assert benefit.coins_inn_tier1 is None

    def test_parse_limit_qty_float(self) -> None:
        """Test parsing limit quantity as float."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "limit_qty": "2.0",
            "limit_unit": "Exam(s) per Year",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.limit_qty == 2.0
        assert benefit.limit_unit == "Exam(s) per Year"

    def test_parse_limit_qty_empty(self) -> None:
        """Test parsing empty limit quantity."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "limit_qty": "",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.limit_qty is None

    def test_get_coinsurance_rate_percentage(self) -> None:
        """Test extracting coinsurance rate from percentage string."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "coins_inn_tier1": "35.00%",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 35.0

    def test_get_coinsurance_rate_not_applicable(self) -> None:
        """Test extracting coinsurance rate from 'Not Applicable' string."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "coins_inn_tier1": NOT_APPLICABLE,
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_get_coinsurance_rate_no_charge(self) -> None:
        """Test extracting coinsurance rate from 'No Charge' string."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "coins_inn_tier1": NO_CHARGE,
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 0.0

    def test_get_coinsurance_rate_none(self) -> None:
        """Test extracting coinsurance rate when field is None."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "coins_inn_tier1": None,
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_is_covered_bool(self) -> None:
        """Test is_covered_bool method."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.is_covered_bool() is True

        data["is_covered"] = CoverageStatus.NOT_COVERED
        benefit_not_covered = PlanBenefit(**data)
        assert benefit_not_covered.is_covered_bool() is False

    def test_is_ehb_bool(self) -> None:
        """Test is_ehb_bool method."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
            "is_ehb": EHBStatus.YES,
        }
        benefit = PlanBenefit(**data)
        assert benefit.is_ehb_bool() is True

        data["is_ehb"] = EHBStatus.NO
        benefit_not_ehb = PlanBenefit(**data)
        assert benefit_not_ehb.is_ehb_bool() is False

        data["is_ehb"] = EHBStatus.NOT_EHB
        benefit_not_ehb2 = PlanBenefit(**data)
        assert benefit_not_ehb2.is_ehb_bool() is False

        data["is_ehb"] = None
        benefit_unknown = PlanBenefit(**data)
        assert benefit_unknown.is_ehb_bool() is None

    def test_has_quantity_limit(self) -> None:
        """Test has_quantity_limit method."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
            "quant_limit_on_svc": YesNoStatus.YES,
        }
        benefit = PlanBenefit(**data)
        assert benefit.has_quantity_limit() is True

        data["quant_limit_on_svc"] = YesNoStatus.NO
        benefit_no_limit = PlanBenefit(**data)
        assert benefit_no_limit.has_quantity_limit() is False

    def test_is_excluded_from_moop_bool(self) -> None:
        """Test is_excluded_from_inn_moop_bool and is_excluded_from_oon_moop_bool."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
            "is_excl_from_inn_moop": YesNoStatus.YES,
            "is_excl_from_oon_moop": YesNoStatus.NO,
        }
        benefit = PlanBenefit(**data)
        assert benefit.is_excluded_from_inn_moop_bool() is True
        assert benefit.is_excluded_from_oon_moop_bool() is False

        data["is_excl_from_inn_moop"] = None
        benefit_unknown = PlanBenefit(**data)
        assert benefit_unknown.is_excluded_from_inn_moop_bool() is None

    def test_immutable_model(self) -> None:
        """Test that model is immutable (frozen)."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Test Benefit",
            "is_covered": CoverageStatus.COVERED,
        }
        benefit = PlanBenefit(**data)

        with pytest.raises(Exception):  # Pydantic ValidationError for frozen models
            benefit.plan_id = "new-id"  # type: ignore[misc]

    def test_not_covered_benefit(self) -> None:
        """Test creating a benefit that is not covered."""
        data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "21989AK0030001",
            "plan_id": "21989AK0030001-00",
            "benefit_name": "Accidental Dental",
            "is_covered": CoverageStatus.NOT_COVERED,
        }
        benefit = PlanBenefit(**data)
        assert benefit.is_covered == CoverageStatus.NOT_COVERED
        assert benefit.is_covered_bool() is False
