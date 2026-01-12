"""Tests for Cost Agent."""

from datetime import date

import pytest

from scratchi.agents.cost import CostAgent
from scratchi.models.constants import CoverageStatus
from scratchi.models.user import CostSharingPreference
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import ExpectedUsage, PriorityWeights, UserProfile


def create_test_plan_with_coinsurance(
    plan_id: str,
    coinsurance_rate: float | None,
) -> Plan:
    """Create a test plan with specified coinsurance rate."""
    coinsurance_str = f"{coinsurance_rate}%" if coinsurance_rate is not None else None
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
        coins_inn_tier1=coinsurance_str,
    )
    return Plan.from_benefits([benefit])


class TestCostAgent:
    """Test cases for CostAgent."""

    def test_score_low_coinsurance(self) -> None:
        """Test that lower coinsurance rates score higher."""
        agent = CostAgent()
        plan_low = create_test_plan_with_coinsurance("PLAN-LOW", 20.0)
        plan_high = create_test_plan_with_coinsurance("PLAN-HIGH", 50.0)

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

        score_low = agent.score(plan_low, user_profile)
        score_high = agent.score(plan_high, user_profile)
        assert score_low > score_high  # Lower coinsurance should score higher

    def test_score_copay_preference(self) -> None:
        """Test that copay preference affects scoring."""
        agent = CostAgent()
        # Create plan with copay
        benefit_copay = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-COPAY",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
            copay_inn_tier1="$25",
        )
        plan_copay = Plan.from_benefits([benefit_copay])

        # Create plan with coinsurance
        plan_coins = create_test_plan_with_coinsurance("PLAN-COINS", 30.0)

        user_profile_copay = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.COPAY,
        )

        score_copay_plan = agent.score(plan_copay, user_profile_copay)
        score_coins_plan = agent.score(plan_coins, user_profile_copay)
        # Copay plan should score higher when user prefers copays
        assert score_copay_plan >= score_coins_plan

    def test_score_annual_maximum(self) -> None:
        """Test that annual maximums in explanations affect scoring."""
        agent = CostAgent()
        # Plan with high annual maximum
        benefit_high_max = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-HIGH-MAX",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
            explanation="Annual maximum of $5,000 applies",
        )
        plan_high_max = Plan.from_benefits([benefit_high_max])

        # Plan with low annual maximum
        benefit_low_max = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-LOW-MAX",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
            explanation="Annual maximum of $1,000 applies",
        )
        plan_low_max = Plan.from_benefits([benefit_low_max])

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

        score_high = agent.score(plan_high_max, user_profile)
        score_low = agent.score(plan_low_max, user_profile)
        assert score_high > score_low  # Higher maximum should score higher
