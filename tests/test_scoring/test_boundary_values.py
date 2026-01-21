"""Tests for boundary values and extreme inputs.

These tests ensure the system handles extreme inputs gracefully without
crashing or producing invalid results.
"""

from datetime import date

import pytest

from scratchi.models.constants import CoverageStatus, EHBStatus, YesNoStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)
from scratchi.recommend.engine import RecommendationEngine
from scratchi.scoring.orchestrator import ScoringOrchestrator


def create_test_plan(
    plan_id: str,
    benefit_count: int = 1,
    coinsurance: float = 30.0,
    benefit_prefix: str = "Benefit",
) -> Plan:
    """Create a test plan with specified number of benefits."""
    benefits: list[PlanBenefit] = []
    for i in range(benefit_count):
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id=plan_id,
            benefit_name=f"{benefit_prefix} {i+1}",
            is_covered=CoverageStatus.COVERED,
            coins_inn_tier1=f"{coinsurance}%",
            ehb_var_reason=EHBStatus.NOT_EHB,
            is_excl_from_inn_moop=YesNoStatus.YES,
            is_excl_from_oon_moop=YesNoStatus.YES,
        )
        benefits.append(benefit)
    return Plan.from_benefits(benefits)


class TestFamilySizeBoundaries:
    """Test boundary values for family size."""

    def test_family_size_one(self) -> None:
        """Test single person family (family_size = 1)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
        user_profile = UserProfile(
            family_size=1,
            children_count=0,
            adults_count=1,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        assert "coverage" in scores
        assert "cost" in scores
        assert "limit" in scores

    def test_family_size_very_large(self) -> None:
        """Test very large family size (20+)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
        user_profile = UserProfile(
            family_size=25,
            children_count=15,
            adults_count=10,
            expected_usage=ExpectedUsage.HIGH,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        # System should handle large families without crashing
        assert isinstance(scores["overall"], float)

    def test_family_size_extreme(self) -> None:
        """Test extreme family size (50+)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
        user_profile = UserProfile(
            family_size=50,
            children_count=30,
            adults_count=20,
            expected_usage=ExpectedUsage.HIGH,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0


class TestRequiredBenefitsBoundaries:
    """Test boundary values for required benefits."""

    def test_many_required_benefits(self) -> None:
        """Test very large number of required benefits (100+)."""
        orchestrator = ScoringOrchestrator()
        # Create plan with many benefits
        plan = create_test_plan("PLAN-001", benefit_count=150)
        # Create user profile with many required benefits
        required_benefits = [f"Benefit {i+1}" for i in range(100)]
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=required_benefits,
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        assert "coverage" in scores

    def test_extreme_required_benefits(self) -> None:
        """Test extreme number of required benefits (500+)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", benefit_count=600)
        required_benefits = [f"Benefit {i+1}" for i in range(500)]
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=required_benefits,
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0


class TestPlanBenefitsBoundaries:
    """Test boundary values for plan benefits."""

    def test_plan_with_many_benefits(self) -> None:
        """Test plan with very large number of benefits (1000+)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", benefit_count=1000)
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        # System should handle large benefit lists without crashing
        assert len(plan.benefits) == 1000

    def test_plan_with_extreme_benefits(self) -> None:
        """Test plan with extreme number of benefits (5000+)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", benefit_count=5000)
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0


class TestPriorityWeightsBoundaries:
    """Test boundary values for priority weights."""

    def test_extreme_coverage_weight(self) -> None:
        """Test extreme priority weights (coverage_weight = 0.99)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
        priorities = PriorityWeights(
            coverage_weight=0.99,
            cost_weight=0.005,
            limit_weight=0.005,
        )
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=priorities,
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        # Coverage should dominate the score
        assert scores["overall"] is not None

    def test_extreme_cost_weight(self) -> None:
        """Test extreme cost weight (cost_weight = 0.99)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", coinsurance=10.0)
        priorities = PriorityWeights(
            coverage_weight=0.005,
            cost_weight=0.99,
            limit_weight=0.005,
        )
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=priorities,
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0

    def test_extreme_limit_weight(self) -> None:
        """Test extreme limit weight (limit_weight = 0.99)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
        priorities = PriorityWeights(
            coverage_weight=0.005,
            cost_weight=0.005,
            limit_weight=0.99,
        )
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=priorities,
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0


class TestCoinsuranceBoundaries:
    """Test boundary values for coinsurance rates."""

    def test_zero_coinsurance(self) -> None:
        """Test 0% coinsurance rate."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", coinsurance=0.0)
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        # 0% coinsurance should be very favorable
        assert scores["cost"] is not None

    def test_hundred_percent_coinsurance(self) -> None:
        """Test 100% coinsurance rate."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", coinsurance=100.0)
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0
        # 100% coinsurance should be less favorable
        assert scores["cost"] is not None

    def test_very_low_coinsurance(self) -> None:
        """Test very low coinsurance rate (0.1%)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", coinsurance=0.1)
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0

    def test_very_high_coinsurance(self) -> None:
        """Test very high coinsurance rate (99.9%)."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001", coinsurance=99.9)
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores = orchestrator.score_plan(plan, user_profile)

        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0


class TestRecommendationEngineBoundaries:
    """Test boundary values in recommendation engine."""

    def test_recommend_with_many_plans(self) -> None:
        """Test recommendation engine with many plans."""
        engine = RecommendationEngine()
        plans = [create_test_plan(f"PLAN-{i:03d}") for i in range(100)]
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Benefit 1"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        recommendations = engine.recommend(plans, user_profile)

        assert len(recommendations) == 100
        # All should be ranked
        ranks = [r.rank for r in recommendations]
        assert sorted(ranks) == list(range(1, 101))

    def test_recommend_with_extreme_inputs(self) -> None:
        """Test recommendation engine with extreme inputs."""
        engine = RecommendationEngine()
        # Large plan with many benefits
        plan = create_test_plan("PLAN-001", benefit_count=1000)
        # User with many required benefits
        required_benefits = [f"Benefit {i+1}" for i in range(200)]
        user_profile = UserProfile(
            family_size=50,
            children_count=30,
            adults_count=20,
            expected_usage=ExpectedUsage.HIGH,
            priorities=PriorityWeights(
                coverage_weight=0.99,
                cost_weight=0.005,
                limit_weight=0.005,
            ),
            required_benefits=required_benefits,
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        recommendations = engine.recommend([plan], user_profile)

        assert len(recommendations) == 1
        assert recommendations[0].overall_score is not None
        assert 0.0 <= recommendations[0].overall_score <= 1.0
