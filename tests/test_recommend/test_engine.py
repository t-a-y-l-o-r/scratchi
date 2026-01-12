"""Tests for RecommendationEngine."""

from datetime import date

import pytest

from scratchi.models.constants import CoverageStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)
from scratchi.recommend.engine import RecommendationEngine


def create_test_plan(plan_id: str, coinsurance: float = 30.0) -> Plan:
    """Create a test plan with specified coinsurance."""
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
        coins_inn_tier1=f"{coinsurance}%",
    )
    return Plan.from_benefits([benefit])


class TestRecommendationEngine:
    """Test cases for RecommendationEngine."""

    def test_recommend_ranks_by_score(self) -> None:
        """Test that recommendations are ranked by overall score."""
        engine = RecommendationEngine()
        # Create plans with different characteristics
        plan_high = create_test_plan("PLAN-HIGH", coinsurance=20.0)  # Lower cost
        plan_low = create_test_plan("PLAN-LOW", coinsurance=50.0)  # Higher cost

        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        recommendations = engine.recommend([plan_low, plan_high], user_profile)

        assert len(recommendations) == 2
        # Plan with lower coinsurance should rank higher
        assert recommendations[0].overall_score >= recommendations[1].overall_score
        assert recommendations[0].rank == 1
        assert recommendations[1].rank == 2

    def test_recommend_top_n(self) -> None:
        """Test that top_n limits the number of recommendations."""
        engine = RecommendationEngine()
        plans = [
            create_test_plan("PLAN-001", coinsurance=20.0),
            create_test_plan("PLAN-002", coinsurance=30.0),
            create_test_plan("PLAN-003", coinsurance=40.0),
        ]

        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        recommendations = engine.recommend(plans, user_profile, top_n=2)

        assert len(recommendations) == 2
        assert recommendations[0].rank == 1
        assert recommendations[1].rank == 2

    def test_recommend_empty_list(self) -> None:
        """Test that empty plan list returns empty recommendations."""
        engine = RecommendationEngine()
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

        recommendations = engine.recommend([], user_profile)

        assert len(recommendations) == 0

    def test_recommend_includes_reasoning(self) -> None:
        """Test that recommendations include reasoning chains."""
        engine = RecommendationEngine()
        plan = create_test_plan("PLAN-001")

        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        recommendations = engine.recommend([plan], user_profile)

        assert len(recommendations) == 1
        assert recommendations[0].reasoning_chain is not None
        assert len(recommendations[0].reasoning_chain.explanations) == 4
        assert "coverage" in recommendations[0].user_fit_scores
        assert "cost" in recommendations[0].user_fit_scores

    def test_recommend_with_plans(self) -> None:
        """Test recommend_with_plans includes plan objects."""
        engine = RecommendationEngine()
        plan = create_test_plan("PLAN-001")

        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        results = engine.recommend_with_plans([plan], user_profile)

        assert len(results) == 1
        assert "plan" in results[0]
        assert "recommendation" in results[0]
        assert results[0]["plan"].plan_id == "PLAN-001"
        assert results[0]["recommendation"].plan_id == "PLAN-001"
