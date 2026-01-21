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

    def test_recommend_top_n_zero(self) -> None:
        """Test that top_n=0 returns empty list."""
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

        recommendations = engine.recommend(plans, user_profile, top_n=0)

        assert len(recommendations) == 0

    def test_recommend_top_n_greater_than_total_plans(self) -> None:
        """Test that top_n > total_plans returns all plans."""
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

        recommendations = engine.recommend(plans, user_profile, top_n=10)

        assert len(recommendations) == 3
        assert recommendations[0].rank == 1
        assert recommendations[1].rank == 2
        assert recommendations[2].rank == 3

    def test_recommend_top_n_none(self) -> None:
        """Test that top_n=None returns all plans."""
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

        recommendations = engine.recommend(plans, user_profile, top_n=None)

        assert len(recommendations) == 3
        assert recommendations[0].rank == 1
        assert recommendations[1].rank == 2
        assert recommendations[2].rank == 3

    def test_ranking_determinism_identical_inputs(self) -> None:
        """Test that identical inputs produce identical rankings (determinism)."""
        engine = RecommendationEngine()
        plans1 = [
            create_test_plan("PLAN-001", coinsurance=20.0),
            create_test_plan("PLAN-002", coinsurance=30.0),
            create_test_plan("PLAN-003", coinsurance=40.0),
        ]
        plans2 = [
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

        recommendations1 = engine.recommend(plans1, user_profile)
        recommendations2 = engine.recommend(plans2, user_profile)

        assert len(recommendations1) == len(recommendations2)
        for rec1, rec2 in zip(recommendations1, recommendations2):
            assert rec1.plan_id == rec2.plan_id, (
                f"Ranking differs for identical inputs: "
                f"rank {rec1.rank}: {rec1.plan_id} vs {rec2.plan_id}"
            )
            assert rec1.rank == rec2.rank, (
                f"Rank differs for identical inputs: "
                f"{rec1.plan_id} has rank {rec1.rank} vs {rec2.rank}"
            )
            assert rec1.overall_score == rec2.overall_score, (
                f"Score differs for identical inputs: "
                f"{rec1.plan_id} has score {rec1.overall_score} vs {rec2.overall_score}"
            )

    def test_ranking_determinism_multiple_runs(self) -> None:
        """Test that rankings are consistent across multiple runs."""
        engine = RecommendationEngine()
        plans = [
            create_test_plan("PLAN-001", coinsurance=20.0),
            create_test_plan("PLAN-002", coinsurance=30.0),
            create_test_plan("PLAN-003", coinsurance=40.0),
            create_test_plan("PLAN-004", coinsurance=25.0),
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

        recommendations_run1 = engine.recommend(plans, user_profile)
        recommendations_run2 = engine.recommend(plans, user_profile)
        recommendations_run3 = engine.recommend(plans, user_profile)

        # Extract plan IDs in rank order for each run
        plan_ids_run1 = [r.plan_id for r in recommendations_run1]
        plan_ids_run2 = [r.plan_id for r in recommendations_run2]
        plan_ids_run3 = [r.plan_id for r in recommendations_run3]

        assert plan_ids_run1 == plan_ids_run2 == plan_ids_run3, (
            f"Rankings differ across runs: "
            f"Run 1: {plan_ids_run1}, Run 2: {plan_ids_run2}, Run 3: {plan_ids_run3}"
        )

        # Verify ranks are consistent
        for rec1, rec2, rec3 in zip(
            recommendations_run1,
            recommendations_run2,
            recommendations_run3,
        ):
            assert rec1.rank == rec2.rank == rec3.rank, (
                f"Rank differs across runs for {rec1.plan_id}: "
                f"{rec1.rank} vs {rec2.rank} vs {rec3.rank}"
            )

    def test_ranking_tie_breaking_logic(self) -> None:
        """Test tie-breaking logic when scores are equal.

        Tie-breaking order (from engine.py):
        1. Higher coverage score
        2. Higher cost score
        3. Higher limit score
        4. Alphabetical by plan_id
        """
        engine = RecommendationEngine()

        # Create plans with identical coinsurance (same cost score)
        # but different plan IDs to test alphabetical tie-breaking
        plan_a = create_test_plan("PLAN-A", coinsurance=30.0)
        plan_b = create_test_plan("PLAN-B", coinsurance=30.0)
        plan_c = create_test_plan("PLAN-C", coinsurance=30.0)

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

        recommendations = engine.recommend([plan_c, plan_a, plan_b], user_profile)

        # Verify all plans are ranked (no crashes)
        assert len(recommendations) == 3

        # Verify ranks are assigned correctly
        ranks = [r.rank for r in recommendations]
        assert sorted(ranks) == [1, 2, 3], f"Ranks should be 1, 2, 3, got {ranks}"

        # Verify each plan has a unique rank
        assert len(set(ranks)) == 3, "All plans should have unique ranks"

        # Verify ranking is deterministic (same order when called again)
        recommendations2 = engine.recommend([plan_c, plan_a, plan_b], user_profile)
        plan_ids1 = [r.plan_id for r in recommendations]
        plan_ids2 = [r.plan_id for r in recommendations2]
        assert plan_ids1 == plan_ids2, (
            f"Tie-breaking should be deterministic: "
            f"Run 1: {plan_ids1}, Run 2: {plan_ids2}"
        )
