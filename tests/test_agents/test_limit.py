"""Tests for Limit Agent."""

from datetime import date

import pytest

from scratchi.agents.limit import LimitAgent
from scratchi.models.constants import CoverageStatus, YesNoStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)


def create_test_plan_with_limits(
    plan_id: str,
    has_quantity_limit: bool = False,
    limit_unit: str | None = None,
) -> Plan:
    """Create a test plan with specified limits."""
    benefit = PlanBenefit(
        business_year=2026,
        state_code="AK",
        issuer_id="21989",
        source_name="HIOS",
        import_date=date(2025, 10, 15),
        standard_component_id="TEST001",
        plan_id=plan_id,
        benefit_name="Basic Dental Care - Adult",
        is_covered=CoverageStatus.COVERED,
        quant_limit_on_svc=YesNoStatus.YES if has_quantity_limit else YesNoStatus.NO,
        limit_qty=2.0 if has_quantity_limit else None,
        limit_unit=limit_unit,
    )
    return Plan.from_benefits([benefit])


class TestLimitAgent:
    """Test cases for LimitAgent."""

    def test_score_no_limits(self) -> None:
        """Test that plans without limits score higher."""
        agent = LimitAgent()
        plan_no_limits = create_test_plan_with_limits("PLAN-NO-LIMITS", has_quantity_limit=False)
        plan_with_limits = create_test_plan_with_limits(
            "PLAN-LIMITS",
            has_quantity_limit=True,
            limit_unit="Exam(s) per Year",
        )

        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        score_no_limits = agent.score(plan_no_limits, user_profile)
        score_with_limits = agent.score(plan_with_limits, user_profile)
        assert score_no_limits > score_with_limits

    def test_score_high_usage_penalty(self) -> None:
        """Test that high usage users are more penalized by limits."""
        agent = LimitAgent()
        plan_with_limits = create_test_plan_with_limits(
            "PLAN-LIMITS",
            has_quantity_limit=True,
        )

        user_profile_low = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.LOW,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        user_profile_high = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.HIGH,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        score_low = agent.score(plan_with_limits, user_profile_low)
        score_high = agent.score(plan_with_limits, user_profile_high)
        # High usage user should score lower (more penalized)
        assert score_low > score_high
