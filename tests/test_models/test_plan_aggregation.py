"""Tests for Plan aggregation model."""

from datetime import date

import pytest

from scratchi.data_loader import aggregate_plans_from_benefits, create_plan_index
from scratchi.models.constants import CoverageStatus, EHBStatus, YesNoStatus
from scratchi.models.plan import Plan, PlanBenefit


def create_test_benefit(
    plan_id: str = "21989AK0030001-00",
    benefit_name: str = "Basic Dental Care - Adult",
    is_covered: str = CoverageStatus.COVERED,
    is_ehb: str | None = None,
    **overrides: str | int | float | date | None,
) -> PlanBenefit:
    """Create a test PlanBenefit with default values."""
    defaults = {
        "business_year": 2026,
        "state_code": "AK",
        "issuer_id": "21989",
        "source_name": "HIOS",
        "import_date": date(2025, 10, 15),
        "standard_component_id": "21989AK0030001",
        "plan_id": plan_id,
        "benefit_name": benefit_name,
        "is_covered": is_covered,
        "is_ehb": is_ehb,
    }
    defaults.update(overrides)
    return PlanBenefit(**defaults)


class TestPlan:
    """Test cases for Plan model."""

    def test_create_plan_from_benefits(self) -> None:
        """Test creating a Plan from a list of PlanBenefit objects."""
        benefits = [
            create_test_benefit(benefit_name="Basic Dental Care - Adult"),
            create_test_benefit(benefit_name="Basic Dental Care - Child"),
            create_test_benefit(benefit_name="Orthodontia - Child"),
        ]
        plan = Plan.from_benefits(benefits)

        assert plan.plan_id == "21989AK0030001-00"
        assert plan.standard_component_id == "21989AK0030001"
        assert plan.state_code == "AK"
        assert plan.issuer_id == "21989"
        assert plan.business_year == 2026
        assert len(plan.benefits) == 3
        assert "Basic Dental Care - Adult" in plan.benefits
        assert "Basic Dental Care - Child" in plan.benefits
        assert "Orthodontia - Child" in plan.benefits

    def test_create_plan_from_empty_list(self) -> None:
        """Test creating a Plan from empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            Plan.from_benefits([])

    def test_create_plan_with_inconsistent_plan_id(self) -> None:
        """Test creating a Plan with inconsistent plan_ids raises ValueError."""
        benefits = [
            create_test_benefit(plan_id="PLAN-001", benefit_name="Benefit 1"),
            create_test_benefit(plan_id="PLAN-002", benefit_name="Benefit 2"),
        ]
        with pytest.raises(ValueError, match="plan_id"):
            Plan.from_benefits(benefits)

    def test_create_plan_with_inconsistent_state_code(self) -> None:
        """Test creating a Plan with inconsistent state_code raises ValueError."""
        benefits = [
            create_test_benefit(state_code="AK", benefit_name="Benefit 1"),
            create_test_benefit(state_code="CA", benefit_name="Benefit 2"),
        ]
        with pytest.raises(ValueError, match="state_code"):
            Plan.from_benefits(benefits)

    def test_create_plan_with_duplicate_benefit_names(self) -> None:
        """Test creating a Plan with duplicate benefit names keeps first."""
        benefits = [
            create_test_benefit(benefit_name="Basic Dental Care - Adult"),
            create_test_benefit(benefit_name="Basic Dental Care - Adult"),  # Duplicate
        ]
        plan = Plan.from_benefits(benefits)
        # Should keep first occurrence
        assert len(plan.benefits) == 1
        assert "Basic Dental Care - Adult" in plan.benefits

    def test_benefit_lookup_methods(self) -> None:
        """Test getting and checking benefits by name."""
        benefits = [
            create_test_benefit(benefit_name="Basic Dental Care - Adult"),
            create_test_benefit(benefit_name="Basic Dental Care - Child"),
        ]
        plan = Plan.from_benefits(benefits)

        # Test get_benefit
        benefit = plan.get_benefit("Basic Dental Care - Adult")
        assert benefit is not None
        assert benefit.benefit_name == "Basic Dental Care - Adult"
        assert plan.get_benefit("Non-existent Benefit") is None

        # Test has_benefit
        assert plan.has_benefit("Basic Dental Care - Adult") is True
        assert plan.has_benefit("Non-existent Benefit") is False

    def test_get_covered_benefits(self) -> None:
        """Test getting all covered benefits."""
        benefits = [
            create_test_benefit(
                benefit_name="Covered Benefit",
                is_covered=CoverageStatus.COVERED,
            ),
            create_test_benefit(
                benefit_name="Not Covered Benefit",
                is_covered=CoverageStatus.NOT_COVERED,
            ),
            create_test_benefit(
                benefit_name="Another Covered Benefit",
                is_covered=CoverageStatus.COVERED,
            ),
        ]
        plan = Plan.from_benefits(benefits)

        covered = plan.get_covered_benefits()
        assert len(covered) == 2
        assert "Covered Benefit" in covered
        assert "Another Covered Benefit" in covered
        assert "Not Covered Benefit" not in covered

    def test_get_ehb_benefits(self) -> None:
        """Test getting all EHB benefits."""
        benefits = [
            create_test_benefit(
                benefit_name="EHB Benefit",
                is_ehb=EHBStatus.YES,
            ),
            create_test_benefit(
                benefit_name="Not EHB Benefit",
                is_ehb=EHBStatus.NOT_EHB,
            ),
            create_test_benefit(
                benefit_name="Unknown EHB Benefit",
                is_ehb=None,
            ),
        ]
        plan = Plan.from_benefits(benefits)

        ehb_benefits = plan.get_ehb_benefits()
        assert len(ehb_benefits) == 1
        assert "EHB Benefit" in ehb_benefits
        assert "Not EHB Benefit" not in ehb_benefits
        assert "Unknown EHB Benefit" not in ehb_benefits



class TestAggregatePlansFromBenefits:
    """Test cases for aggregate_plans_from_benefits function."""

    def test_aggregate_single_plan(self) -> None:
        """Test aggregating benefits for a single plan."""
        benefits = [
            create_test_benefit(plan_id="PLAN-001", benefit_name="Benefit 1"),
            create_test_benefit(plan_id="PLAN-001", benefit_name="Benefit 2"),
        ]
        plans = aggregate_plans_from_benefits(benefits)

        assert len(plans) == 1
        assert plans[0].plan_id == "PLAN-001"
        assert len(plans[0].benefits) == 2

    def test_aggregate_multiple_plans(self) -> None:
        """Test aggregating benefits for multiple plans."""
        benefits = [
            create_test_benefit(plan_id="PLAN-001", benefit_name="Benefit 1"),
            create_test_benefit(plan_id="PLAN-001", benefit_name="Benefit 2"),
            create_test_benefit(plan_id="PLAN-002", benefit_name="Benefit 3"),
            create_test_benefit(plan_id="PLAN-002", benefit_name="Benefit 4"),
            create_test_benefit(plan_id="PLAN-003", benefit_name="Benefit 5"),
        ]
        plans = aggregate_plans_from_benefits(benefits)

        assert len(plans) == 3
        plan_ids = {plan.plan_id for plan in plans}
        assert plan_ids == {"PLAN-001", "PLAN-002", "PLAN-003"}
        assert len([p for p in plans if p.plan_id == "PLAN-001"][0].benefits) == 2
        assert len([p for p in plans if p.plan_id == "PLAN-002"][0].benefits) == 2
        assert len([p for p in plans if p.plan_id == "PLAN-003"][0].benefits) == 1

    def test_aggregate_empty_list(self) -> None:
        """Test aggregating empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            aggregate_plans_from_benefits([])

    def test_aggregate_with_invalid_benefits(self) -> None:
        """Test aggregating with invalid benefits skips them."""
        benefits = [
            create_test_benefit(plan_id="PLAN-001", benefit_name="Valid Benefit"),
            create_test_benefit(
                plan_id="PLAN-002",
                benefit_name="Invalid Benefit",
                state_code="AK",
            ),
            create_test_benefit(
                plan_id="PLAN-002",
                benefit_name="Another Invalid Benefit",
                state_code="CA",  # Inconsistent state_code
            ),
        ]
        # Should create PLAN-001 successfully, skip PLAN-002 due to inconsistency
        plans = aggregate_plans_from_benefits(benefits)
        assert len(plans) == 1
        assert plans[0].plan_id == "PLAN-001"


class TestCreatePlanIndex:
    """Test cases for create_plan_index function."""

    @pytest.mark.parametrize("plan_count", [1, 3])
    def test_create_index(self, plan_count: int) -> None:
        """Test creating index with single or multiple plans."""
        plan_ids = [f"PLAN-{i:03d}" for i in range(1, plan_count + 1)]
        benefits = [create_test_benefit(plan_id=pid) for pid in plan_ids]
        plans = aggregate_plans_from_benefits(benefits)
        index = create_plan_index(plans)

        assert len(index) == plan_count
        for plan_id in plan_ids:
            assert plan_id in index
            assert index[plan_id].plan_id == plan_id

    def test_create_index_with_duplicates(self) -> None:
        """Test creating index with duplicate plan_ids raises ValueError."""
        benefits1 = [create_test_benefit(plan_id="PLAN-001")]
        benefits2 = [create_test_benefit(plan_id="PLAN-001")]  # Same plan_id
        plans1 = aggregate_plans_from_benefits(benefits1)
        plans2 = aggregate_plans_from_benefits(benefits2)
        plans = plans1 + plans2  # Create duplicate plan_ids

        with pytest.raises(ValueError, match="duplicate"):
            create_plan_index(plans)

    def test_index_lookup(self) -> None:
        """Test using index for fast plan lookup."""
        benefits = [
            create_test_benefit(plan_id="PLAN-001", benefit_name="Benefit 1"),
            create_test_benefit(plan_id="PLAN-002", benefit_name="Benefit 2"),
        ]
        plans = aggregate_plans_from_benefits(benefits)
        index = create_plan_index(plans)

        plan = index.get("PLAN-001")
        assert plan is not None
        assert plan.plan_id == "PLAN-001"
        assert "Benefit 1" in plan.benefits

        plan_none = index.get("NON-EXISTENT")
        assert plan_none is None
