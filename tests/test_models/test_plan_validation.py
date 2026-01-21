"""Tests for Plan data validation."""

from datetime import date

import pytest

from scratchi.models.constants import (
    NOT_APPLICABLE,
    CoverageStatus,
    EHBStatus,
    YesNoStatus,
)
from scratchi.models.plan import Plan, PlanBenefit


def create_test_benefit(
    plan_id: str = "21989AK0030001-00",
    standard_component_id: str = "21989AK0030001",
    benefit_name: str = "Basic Dental Care - Adult",
    is_covered: CoverageStatus = CoverageStatus.COVERED,
    copay_inn_tier1: str | None = None,
    coins_inn_tier1: str | None = "30%",
    **overrides: str,
) -> PlanBenefit:
    """Create a test PlanBenefit with common defaults."""
    data = {
        "business_year": 2026,
        "state_code": "AK",
        "issuer_id": "21989",
        "source_name": "HIOS",
        "import_date": date(2025, 10, 15),
        "standard_component_id": standard_component_id,
        "plan_id": plan_id,
        "benefit_name": benefit_name,
        "is_covered": is_covered,
        "copay_inn_tier1": copay_inn_tier1 or NOT_APPLICABLE,
        "copay_inn_tier2": None,
        "copay_outof_net": NOT_APPLICABLE,
        "coins_inn_tier1": coins_inn_tier1 or NOT_APPLICABLE,
        "coins_inn_tier2": None,
        "coins_outof_net": NOT_APPLICABLE,
        "is_ehb": None,
        "quant_limit_on_svc": None,
        "limit_qty": None,
        "limit_unit": None,
        "exclusions": None,
        "explanation": None,
        "ehb_var_reason": EHBStatus.NOT_EHB,
        "is_excl_from_inn_moop": YesNoStatus.YES,
        "is_excl_from_oon_moop": YesNoStatus.YES,
    }
    data.update(overrides)
    return PlanBenefit(**data)


class TestPlanValidation:
    """Test cases for Plan data validation."""

    def test_validate_valid_plan(self) -> None:
        """Test that a valid plan has no validation issues."""
        benefit = create_test_benefit()
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        assert len(issues) == 0, f"Valid plan should have no issues, got: {issues}"

    def test_validate_standard_component_id_mismatch(self) -> None:
        """Test validation detects standard_component_id not matching plan_id prefix."""
        benefit = create_test_benefit(
            plan_id="21989AK0030001-00",
            standard_component_id="21989AK9999999",  # Doesn't match plan_id prefix
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        assert len(issues) > 0
        assert any("standard_component_id" in issue.lower() for issue in issues)
        assert any("does not match" in issue.lower() for issue in issues)

    def test_validate_standard_component_id_matches_prefix(self) -> None:
        """Test validation passes when standard_component_id matches plan_id prefix."""
        benefit = create_test_benefit(
            plan_id="21989AK0030001-00",
            standard_component_id="21989AK0030001",  # Matches prefix
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        # Should not have standard_component_id issues
        assert not any("standard_component_id" in issue.lower() for issue in issues)

    def test_validate_all_benefits_not_covered(self) -> None:
        """Test validation detects plans with all benefits marked Not Covered."""
        benefit1 = create_test_benefit(
            benefit_name="Benefit 1",
            is_covered=CoverageStatus.NOT_COVERED,
        )
        benefit2 = create_test_benefit(
            benefit_name="Benefit 2",
            is_covered=CoverageStatus.NOT_COVERED,
        )
        plan = Plan.from_benefits([benefit1, benefit2])

        issues = plan.validate()

        assert len(issues) > 0
        assert any("no covered benefits" in issue.lower() for issue in issues)
        assert any("not covered" in issue.lower() for issue in issues)

    def test_validate_some_benefits_covered(self) -> None:
        """Test validation passes when at least one benefit is covered."""
        benefit1 = create_test_benefit(
            benefit_name="Benefit 1",
            is_covered=CoverageStatus.NOT_COVERED,
        )
        benefit2 = create_test_benefit(
            benefit_name="Benefit 2",
            is_covered=CoverageStatus.COVERED,  # At least one covered
        )
        plan = Plan.from_benefits([benefit1, benefit2])

        issues = plan.validate()

        # Should not have "all not covered" issue
        assert not any("no covered benefits" in issue.lower() for issue in issues)

    def test_validate_cost_sharing_both_copay_and_coinsurance_tier1(self) -> None:
        """Test validation detects both copay and coinsurance for tier 1."""
        benefit = create_test_benefit(
            copay_inn_tier1="$20",
            coins_inn_tier1="30%",  # Both specified
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        assert len(issues) > 0
        assert any("tier 1" in issue.lower() for issue in issues)
        assert any("both copay and coinsurance" in issue.lower() for issue in issues)

    def test_validate_cost_sharing_both_copay_and_coinsurance_tier2(self) -> None:
        """Test validation detects both copay and coinsurance for tier 2."""
        benefit = create_test_benefit(
            copay_inn_tier2="$30",
            coins_inn_tier2="40%",  # Both specified
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        assert len(issues) > 0
        assert any("tier 2" in issue.lower() for issue in issues)
        assert any("both copay and coinsurance" in issue.lower() for issue in issues)

    def test_validate_cost_sharing_both_copay_and_coinsurance_oon(self) -> None:
        """Test validation detects both copay and coinsurance for out-of-network."""
        benefit = create_test_benefit(
            copay_outof_net="$50",
            coins_outof_net="50%",  # Both specified
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        assert len(issues) > 0
        assert any("out-of-network" in issue.lower() for issue in issues)
        assert any("both copay and coinsurance" in issue.lower() for issue in issues)

    def test_validate_cost_sharing_copay_only(self) -> None:
        """Test validation passes when only copay is specified."""
        benefit = create_test_benefit(
            copay_inn_tier1="$20",
            coins_inn_tier1=NOT_APPLICABLE,
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        # Should not have cost-sharing consistency issues
        assert not any("both copay and coinsurance" in issue.lower() for issue in issues)

    def test_validate_cost_sharing_coinsurance_only(self) -> None:
        """Test validation passes when only coinsurance is specified."""
        benefit = create_test_benefit(
            copay_inn_tier1=NOT_APPLICABLE,
            coins_inn_tier1="30%",
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        # Should not have cost-sharing consistency issues
        assert not any("both copay and coinsurance" in issue.lower() for issue in issues)

    def test_validate_multiple_issues(self) -> None:
        """Test validation detects multiple issues in a single plan."""
        benefit = create_test_benefit(
            plan_id="21989AK0030001-00",
            standard_component_id="WRONG-ID",  # Mismatch
            is_covered=CoverageStatus.NOT_COVERED,  # Not covered
            copay_inn_tier1="$20",
            coins_inn_tier1="30%",  # Both copay and coinsurance
        )
        plan = Plan.from_benefits([benefit])

        issues = plan.validate()

        assert len(issues) >= 3, f"Expected at least 3 issues, got {len(issues)}: {issues}"
