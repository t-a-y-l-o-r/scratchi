"""Tests for Coverage Agent."""

from datetime import date

import pytest

from scratchi.agents.coverage import CoverageAgent
from scratchi.models.constants import CoverageStatus, EHBStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)


def create_test_plan_with_benefits(
    plan_id: str,
    benefit_names: list[str],
    covered: bool = True,
    is_ehb: bool | None = None,
) -> Plan:
    """Create a test plan with specified benefits."""
    benefits: list[PlanBenefit] = []
    for benefit_name in benefit_names:
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id=plan_id,
            benefit_name=benefit_name,
            is_covered=CoverageStatus.COVERED if covered else CoverageStatus.NOT_COVERED,
            is_ehb=EHBStatus.YES if is_ehb is True else (EHBStatus.NOT_EHB if is_ehb is False else None),
        )
        benefits.append(benefit)
    return Plan.from_benefits(benefits)


class TestCoverageAgent:
    """Test cases for CoverageAgent."""

    def test_score_all_required_benefits_covered(self) -> None:
        """Test scoring when all required benefits are covered."""
        agent = CoverageAgent()
        plan = create_test_plan_with_benefits(
            "PLAN-001",
            ["Basic Dental Care - Adult", "Orthodontia - Child"],
        )
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Basic Dental Care - Adult", "Orthodontia - Child"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high when all required benefits covered

    def test_score_partial_required_benefits_covered(self) -> None:
        """Test scoring when only some required benefits are covered."""
        agent = CoverageAgent()
        plan = create_test_plan_with_benefits(
            "PLAN-001",
            ["Basic Dental Care - Adult"],  # Only one benefit
        )
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Basic Dental Care - Adult", "Orthodontia - Child"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        assert score < 0.8  # Should be lower when only 50% covered

    def test_score_no_required_benefits(self) -> None:
        """Test scoring when user has no required benefits."""
        agent = CoverageAgent()
        plan = create_test_plan_with_benefits("PLAN-001", ["Basic Dental Care - Adult"])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.LOW,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_score_ehb_bonus(self) -> None:
        """Test that EHB benefits contribute to score."""
        agent = CoverageAgent()
        plan_ehb = create_test_plan_with_benefits(
            "PLAN-EHB",
            ["Basic Dental Care - Adult"],
            is_ehb=True,
        )
        plan_no_ehb = create_test_plan_with_benefits(
            "PLAN-NO-EHB",
            ["Basic Dental Care - Adult"],
            is_ehb=False,
        )
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.LOW,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        score_ehb = agent.score(plan_ehb, user_profile)
        score_no_ehb = agent.score(plan_no_ehb, user_profile)
        # EHB plan should score higher (or equal if other factors dominate)
        assert score_ehb >= score_no_ehb
