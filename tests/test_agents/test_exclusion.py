"""Tests for Exclusion Agent."""

from datetime import date

import pytest

from scratchi.agents.exclusion import ExclusionAgent
from scratchi.models.constants import CoverageStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)


def create_test_plan_with_exclusions(
    plan_id: str,
    exclusions: str | None = None,
) -> Plan:
    """Create a test plan with specified exclusions."""
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
        exclusions=exclusions,
    )
    return Plan.from_benefits([benefit])


class TestExclusionAgent:
    """Test cases for ExclusionAgent."""

    def test_score_no_exclusions(self) -> None:
        """Test that plans without exclusions score higher."""
        agent = ExclusionAgent()
        plan_no_exclusions = create_test_plan_with_exclusions("PLAN-NO-EXCL", exclusions=None)
        plan_with_exclusions = create_test_plan_with_exclusions(
            "PLAN-EXCL",
            exclusions="See policy for exclusions",
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

        score_no_excl = agent.score(plan_no_exclusions, user_profile)
        score_with_excl = agent.score(plan_with_exclusions, user_profile)
        assert score_no_excl > score_with_excl

    def test_score_complex_exclusions_penalty(self) -> None:
        """Test that complex exclusions are penalized more."""
        agent = ExclusionAgent()
        plan_simple = create_test_plan_with_exclusions(
            "PLAN-SIMPLE",
            exclusions="Not covered for cosmetic procedures",
        )
        plan_complex = create_test_plan_with_exclusions(
            "PLAN-COMPLEX",
            exclusions="See policy for exclusions. Subject to contract terms.",
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

        score_simple = agent.score(plan_simple, user_profile)
        score_complex = agent.score(plan_complex, user_profile)
        # Complex exclusions should score lower
        assert score_simple > score_complex

    def test_score_prior_coverage_penalty(self) -> None:
        """Test that prior coverage requirements are penalized."""
        agent = ExclusionAgent()
        plan_no_prior = create_test_plan_with_exclusions("PLAN-NO-PRIOR", exclusions=None)
        plan_prior = create_test_plan_with_exclusions(
            "PLAN-PRIOR",
            exclusions="Requires prior coverage for 12 months",
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

        score_no_prior = agent.score(plan_no_prior, user_profile)
        score_prior = agent.score(plan_prior, user_profile)
        assert score_no_prior > score_prior
