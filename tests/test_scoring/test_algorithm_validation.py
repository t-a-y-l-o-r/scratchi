"""Tests for scoring algorithm validation (Section 1 recommendations).

This module implements tests for:
1.1 Score range validation (property-based tests)
1.2 Score consistency (determinism, transitivity, monotonicity)
1.3 Weighted score calculation validation (edge cases)
1.4 Cross-agent score independence
"""

from datetime import date
from typing import Any

import pytest
from hypothesis import given, strategies as st

from scratchi.agents.coverage import CoverageAgent
from scratchi.agents.cost import CostAgent
from scratchi.agents.exclusion import ExclusionAgent
from scratchi.agents.limit import LimitAgent
from scratchi.models.constants import CoverageStatus, EHBStatus, YesNoStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)
from scratchi.scoring.orchestrator import ScoringOrchestrator


def create_test_plan(
    plan_id: str,
    coinsurance: float | None = 30.0,
    benefit_names: list[str] | None = None,
    is_covered: bool = True,
    has_exclusions: bool = False,
    has_limits: bool = False,
    explanation: str | None = None,
) -> Plan:
    """Create a test plan with configurable properties."""
    if benefit_names is None:
        benefit_names = ["Basic Dental Care - Adult"]

    benefits: list[PlanBenefit] = []
    for benefit_name in benefit_names:
        coinsurance_str = f"{coinsurance}%" if coinsurance is not None else None
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id=plan_id,
            benefit_name=benefit_name,
            is_covered=CoverageStatus.COVERED if is_covered else CoverageStatus.NOT_COVERED,
            coins_inn_tier1=coinsurance_str,
            is_ehb=EHBStatus.YES if is_covered else None,
            exclusions="See policy for exclusions" if has_exclusions else None,
            quant_limit_on_svc=YesNoStatus.YES if has_limits else YesNoStatus.NO,
            limit_qty=2.0 if has_limits else None,
            limit_unit="Exam(s) per Year" if has_limits else None,
            explanation=explanation,
        )
        benefits.append(benefit)
    return Plan.from_benefits(benefits)


def create_test_user_profile(
    required_benefits: list[str] | None = None,
    expected_usage: ExpectedUsage = ExpectedUsage.MEDIUM,
    priorities: PriorityWeights | None = None,
    preferred_cost_sharing: CostSharingPreference = CostSharingPreference.EITHER,
) -> UserProfile:
    """Create a test user profile with configurable properties."""
    if required_benefits is None:
        required_benefits = []
    if priorities is None:
        priorities = PriorityWeights.default()

    return UserProfile(
        family_size=2,
        children_count=0,
        adults_count=2,
        expected_usage=expected_usage,
        priorities=priorities,
        required_benefits=required_benefits,
        excluded_benefits_ok=[],
        preferred_cost_sharing=preferred_cost_sharing,
    )


class TestScoreRangeValidation:
    """1.1 Score Range Validation - Property-based tests."""

    @given(
        coinsurance=st.one_of(
            st.none(),
            st.floats(min_value=0.0, max_value=100.0),
            st.just(0.0),
            st.just(100.0),
        ),
        benefit_count=st.integers(min_value=1, max_value=50),
        has_exclusions=st.booleans(),
        has_limits=st.booleans(),
    )
    def test_cost_agent_score_in_range(
        self,
        coinsurance: float | None,
        benefit_count: int,
        has_exclusions: bool,
        has_limits: bool,
    ) -> None:
        """Property test: CostAgent scores are always in [0, 1] range."""
        agent = CostAgent()
        benefit_names = [f"Benefit {i}" for i in range(benefit_count)]
        plan = create_test_plan(
            "TEST-PLAN",
            coinsurance=coinsurance,
            benefit_names=benefit_names,
            has_exclusions=has_exclusions,
            has_limits=has_limits,
        )
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)

        assert 0.0 <= score <= 1.0, f"Cost score {score} is outside [0, 1] range"

    @given(
        required_benefit_count=st.integers(min_value=0, max_value=20),
        plan_benefit_count=st.integers(min_value=1, max_value=20),
        coverage_ratio=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_coverage_agent_score_in_range(
        self,
        required_benefit_count: int,
        plan_benefit_count: int,
        coverage_ratio: float,
    ) -> None:
        """Property test: CoverageAgent scores are always in [0, 1] range."""
        agent = CoverageAgent()
        required_benefits = [f"Required {i}" for i in range(required_benefit_count)]
        plan_benefits = [f"Plan {i}" for i in range(plan_benefit_count)]

        # Create plan with some required benefits covered
        covered_count = int(required_benefit_count * coverage_ratio)
        covered_benefits = required_benefits[:covered_count] if required_benefits else []
        all_benefits = list(set(required_benefits + plan_benefits))

        # Ensure at least one benefit (plan_benefit_count >= 1 guarantees this)
        plan = create_test_plan("TEST-PLAN", benefit_names=all_benefits)
        user_profile = create_test_user_profile(required_benefits=required_benefits)

        score = agent.score(plan, user_profile)

        assert 0.0 <= score <= 1.0, f"Coverage score {score} is outside [0, 1] range"

    @given(
        benefit_count=st.integers(min_value=1, max_value=50),
        has_limits=st.booleans(),
        expected_usage=st.sampled_from(list(ExpectedUsage)),
    )
    def test_limit_agent_score_in_range(
        self,
        benefit_count: int,
        has_limits: bool,
        expected_usage: ExpectedUsage,
    ) -> None:
        """Property test: LimitAgent scores are always in [0, 1] range."""
        agent = LimitAgent()
        benefit_names = [f"Benefit {i}" for i in range(benefit_count)]
        plan = create_test_plan("TEST-PLAN", benefit_names=benefit_names, has_limits=has_limits)
        user_profile = create_test_user_profile(expected_usage=expected_usage)

        score = agent.score(plan, user_profile)

        assert 0.0 <= score <= 1.0, f"Limit score {score} is outside [0, 1] range"

    @given(
        benefit_count=st.integers(min_value=1, max_value=50),
        has_exclusions=st.booleans(),
    )
    def test_exclusion_agent_score_in_range(
        self,
        benefit_count: int,
        has_exclusions: bool,
    ) -> None:
        """Property test: ExclusionAgent scores are always in [0, 1] range."""
        agent = ExclusionAgent()
        benefit_names = [f"Benefit {i}" for i in range(benefit_count)]
        plan = create_test_plan("TEST-PLAN", benefit_names=benefit_names, has_exclusions=has_exclusions)
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)

        assert 0.0 <= score <= 1.0, f"Exclusion score {score} is outside [0, 1] range"

    @given(
        coverage_weight=st.floats(min_value=0.0, max_value=1.0),
        cost_weight=st.floats(min_value=0.0, max_value=1.0),
        limit_weight=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_orchestrator_overall_score_in_range(
        self,
        coverage_weight: float,
        cost_weight: float,
        limit_weight: float,
    ) -> None:
        """Property test: Orchestrator overall scores are always in [0, 1] range."""
        # Normalize weights to sum to 1.0 (or close to it)
        total = coverage_weight + cost_weight + limit_weight
        if total > 0:
            coverage_weight /= total
            cost_weight /= total
            limit_weight /= total

        try:
            priorities = PriorityWeights(
                coverage_weight=coverage_weight,
                cost_weight=cost_weight,
                limit_weight=limit_weight,
            )
        except ValueError:
            # Skip invalid weight combinations
            pytest.skip("Invalid weight combination")

        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("TEST-PLAN")
        user_profile = create_test_user_profile(priorities=priorities)

        scores = orchestrator.score_plan(plan, user_profile)

        assert 0.0 <= scores["overall"] <= 1.0, f"Overall score {scores['overall']} is outside [0, 1] range"
        for dimension in ["coverage", "cost", "limit", "exclusion"]:
            assert 0.0 <= scores[dimension] <= 1.0, f"{dimension} score {scores[dimension]} is outside [0, 1] range"


class TestScoreConsistency:
    """1.2 Score Consistency Tests - Determinism, transitivity, monotonicity."""

    def test_score_determinism_identical_inputs(self) -> None:
        """Test that identical inputs produce identical scores (determinism)."""
        agent = CostAgent()
        plan1 = create_test_plan("PLAN-001", coinsurance=30.0)
        plan2 = create_test_plan("PLAN-001", coinsurance=30.0)  # Identical plan
        user_profile = create_test_user_profile()

        score1 = agent.score(plan1, user_profile)
        score2 = agent.score(plan2, user_profile)

        assert score1 == score2, f"Scores differ for identical inputs: {score1} vs {score2}"

    def test_score_determinism_multiple_runs(self) -> None:
        """Test that scoring is consistent across multiple runs."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
        user_profile = create_test_user_profile()

        scores_run1 = orchestrator.score_plan(plan, user_profile)
        scores_run2 = orchestrator.score_plan(plan, user_profile)
        scores_run3 = orchestrator.score_plan(plan, user_profile)

        assert scores_run1 == scores_run2 == scores_run3, "Scores differ across runs"

    def test_score_transitivity(self) -> None:
        """Test that score ordering is transitive (if A > B and B > C, then A > C)."""
        agent = CostAgent()
        user_profile = create_test_user_profile()

        # Create plans with different coinsurance rates
        plan_a = create_test_plan("PLAN-A", coinsurance=10.0)  # Lowest cost
        plan_b = create_test_plan("PLAN-B", coinsurance=30.0)  # Medium cost
        plan_c = create_test_plan("PLAN-C", coinsurance=50.0)  # Highest cost

        score_a = agent.score(plan_a, user_profile)
        score_b = agent.score(plan_b, user_profile)
        score_c = agent.score(plan_c, user_profile)

        # Lower coinsurance should score higher
        assert score_a > score_b, f"Transitivity violated: A ({score_a}) should be > B ({score_b})"
        assert score_b > score_c, f"Transitivity violated: B ({score_b}) should be > C ({score_c})"
        assert score_a > score_c, f"Transitivity violated: A ({score_a}) should be > C ({score_c})"

    def test_score_monotonicity_coverage(self) -> None:
        """Test that increasing coverage always increases coverage score (monotonicity)."""
        agent = CoverageAgent()
        required_benefits = ["Benefit A", "Benefit B", "Benefit C"]

        # Plan with 0% coverage
        plan_0 = create_test_plan("PLAN-0", benefit_names=["Other Benefit"])
        # Plan with 33% coverage (1 of 3)
        plan_33 = create_test_plan("PLAN-33", benefit_names=[required_benefits[0]])
        # Plan with 67% coverage (2 of 3)
        plan_67 = create_test_plan("PLAN-67", benefit_names=required_benefits[:2])
        # Plan with 100% coverage (3 of 3)
        plan_100 = create_test_plan("PLAN-100", benefit_names=required_benefits)

        user_profile = create_test_user_profile(required_benefits=required_benefits)

        score_0 = agent.score(plan_0, user_profile)
        score_33 = agent.score(plan_33, user_profile)
        score_67 = agent.score(plan_67, user_profile)
        score_100 = agent.score(plan_100, user_profile)

        assert score_0 <= score_33, f"Monotonicity violated: 0% ({score_0}) should be <= 33% ({score_33})"
        assert score_33 <= score_67, f"Monotonicity violated: 33% ({score_33}) should be <= 67% ({score_67})"
        assert score_67 <= score_100, f"Monotonicity violated: 67% ({score_67}) should be <= 100% ({score_100})"

    def test_score_monotonicity_cost(self) -> None:
        """Test that decreasing cost (lower coinsurance) always increases cost score (monotonicity)."""
        agent = CostAgent()
        user_profile = create_test_user_profile()

        # Plans with decreasing coinsurance (lower = better)
        plan_50 = create_test_plan("PLAN-50", coinsurance=50.0)
        plan_30 = create_test_plan("PLAN-30", coinsurance=30.0)
        plan_10 = create_test_plan("PLAN-10", coinsurance=10.0)
        plan_0 = create_test_plan("PLAN-0", coinsurance=0.0)

        score_50 = agent.score(plan_50, user_profile)
        score_30 = agent.score(plan_30, user_profile)
        score_10 = agent.score(plan_10, user_profile)
        score_0 = agent.score(plan_0, user_profile)

        # Lower coinsurance should score higher
        assert score_0 >= score_10, f"Monotonicity violated: 0% ({score_0}) should be >= 10% ({score_10})"
        assert score_10 >= score_30, f"Monotonicity violated: 10% ({score_10}) should be >= 30% ({score_30})"
        assert score_30 >= score_50, f"Monotonicity violated: 30% ({score_30}) should be >= 50% ({score_50})"


class TestWeightedScoreCalculation:
    """1.3 Weighted Score Calculation Validation - Edge cases."""

    def test_exclusion_modifier_logic(self) -> None:
        """Test that exclusion modifier (0.5 + exclusion_score * 0.5) produces expected results."""
        orchestrator = ScoringOrchestrator()
        user_profile = create_test_user_profile()

        # Plan with no exclusions (should have high exclusion score)
        plan_no_excl = create_test_plan("PLAN-NO-EXCL", has_exclusions=False)
        # Plan with exclusions (should have lower exclusion score)
        plan_with_excl = create_test_plan("PLAN-EXCL", has_exclusions=True)

        scores_no_excl = orchestrator.score_plan(plan_no_excl, user_profile)
        scores_with_excl = orchestrator.score_plan(plan_with_excl, user_profile)

        # Exclusion modifier: 0.5 + (exclusion_score * 0.5)
        # Maps [0, 1] exclusion score to [0.5, 1.0] modifier
        # So overall score should be: base_score * modifier

        # Plan with no exclusions should have higher exclusion score
        assert scores_no_excl["exclusion"] > scores_with_excl["exclusion"]

        # Overall score should reflect the exclusion modifier
        # The plan with no exclusions should have higher overall score
        # (assuming other scores are similar)
        assert scores_no_excl["overall"] > scores_with_excl["overall"]

    def test_weighted_score_bounds(self) -> None:
        """Test that overall score is bounded by individual scores when weights are balanced."""
        orchestrator = ScoringOrchestrator()
        # Use balanced weights
        priorities = PriorityWeights.balanced()
        user_profile = create_test_user_profile(priorities=priorities)
        plan = create_test_plan("PLAN-001")

        scores = orchestrator.score_plan(plan, user_profile)

        individual_scores = [
            scores["coverage"],
            scores["cost"],
            scores["limit"],
        ]
        min_score = min(individual_scores)
        max_score = max(individual_scores)

        # Overall score should be between min and max (before exclusion modifier)
        # But exclusion modifier can push it lower, so we check it's >= min * 0.5
        # (since exclusion modifier is at least 0.5)
        assert scores["overall"] >= min_score * 0.5, "Overall score below minimum individual score"
        assert scores["overall"] <= max_score, "Overall score above maximum individual score"

    def test_extreme_priority_weights(self) -> None:
        """Test scoring with extreme priority weights."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")

        # Coverage-focused (coverage_weight = 0.99, others = 0.01)
        # Note: Pydantic validation prevents weights > 1.0, so we use valid extreme weights
        priorities_coverage = PriorityWeights(
            coverage_weight=0.98,
            cost_weight=0.01,
            limit_weight=0.01,
        )
        user_coverage = create_test_user_profile(priorities=priorities_coverage)

        # Cost-focused
        priorities_cost = PriorityWeights(
            coverage_weight=0.01,
            cost_weight=0.98,
            limit_weight=0.01,
        )
        user_cost = create_test_user_profile(priorities=priorities_cost)

        scores_coverage = orchestrator.score_plan(plan, user_coverage)
        scores_cost = orchestrator.score_plan(plan, user_cost)

        # Scores should still be in [0, 1] range
        assert 0.0 <= scores_coverage["overall"] <= 1.0
        assert 0.0 <= scores_cost["overall"] <= 1.0

        # Overall scores may differ based on priorities
        # (exact relationship depends on individual scores)


class TestCrossAgentScoreIndependence:
    """1.4 Cross-Agent Score Independence - Explicit tests."""

    def test_cost_changes_dont_affect_coverage(self) -> None:
        """Test that changing cost doesn't affect coverage score."""
        coverage_agent = CoverageAgent()
        cost_agent = CostAgent()
        user_profile = create_test_user_profile(required_benefits=["Basic Dental Care - Adult"])

        # Plan with low cost
        plan_low_cost = create_test_plan("PLAN-LOW-COST", coinsurance=10.0)
        # Plan with high cost (same coverage)
        plan_high_cost = create_test_plan("PLAN-HIGH-COST", coinsurance=50.0)

        coverage_low = coverage_agent.score(plan_low_cost, user_profile)
        coverage_high = coverage_agent.score(plan_high_cost, user_profile)
        cost_low = cost_agent.score(plan_low_cost, user_profile)
        cost_high = cost_agent.score(plan_high_cost, user_profile)

        # Coverage scores should be identical (same benefits)
        assert coverage_low == coverage_high, "Coverage score changed when cost changed"

        # Cost scores should differ
        assert cost_low != cost_high, "Cost scores should differ for different costs"

    def test_coverage_changes_dont_affect_cost(self) -> None:
        """Test that changing coverage doesn't affect cost score."""
        coverage_agent = CoverageAgent()
        cost_agent = CostAgent()
        user_profile = create_test_user_profile()

        # Plan with full coverage
        plan_full = create_test_plan("PLAN-FULL", benefit_names=["Benefit A", "Benefit B"])
        # Plan with partial coverage (same cost structure)
        plan_partial = create_test_plan("PLAN-PARTIAL", benefit_names=["Benefit A"])

        coverage_full = coverage_agent.score(plan_full, user_profile)
        coverage_partial = coverage_agent.score(plan_partial, user_profile)
        cost_full = cost_agent.score(plan_full, user_profile)
        cost_partial = cost_agent.score(plan_partial, user_profile)

        # Cost scores should be identical (same cost structure)
        assert cost_full == cost_partial, "Cost score changed when coverage changed"

        # Coverage scores may differ (different benefits)
        # (This is expected behavior)

    def test_limit_changes_dont_affect_exclusion(self) -> None:
        """Test that changing limits doesn't affect exclusion score."""
        limit_agent = LimitAgent()
        exclusion_agent = ExclusionAgent()
        user_profile = create_test_user_profile()

        # Plan with limits
        plan_with_limits = create_test_plan("PLAN-LIMITS", has_limits=True)
        # Plan without limits (same exclusions)
        plan_no_limits = create_test_plan("PLAN-NO-LIMITS", has_limits=False)

        limit_with = limit_agent.score(plan_with_limits, user_profile)
        limit_without = limit_agent.score(plan_no_limits, user_profile)
        exclusion_with = exclusion_agent.score(plan_with_limits, user_profile)
        exclusion_without = exclusion_agent.score(plan_no_limits, user_profile)

        # Exclusion scores should be identical (same exclusions)
        assert exclusion_with == exclusion_without, "Exclusion score changed when limits changed"

        # Limit scores should differ
        assert limit_with != limit_without, "Limit scores should differ for different limits"

    def test_all_agents_independent(self) -> None:
        """Test that all agents produce independent scores."""
        orchestrator = ScoringOrchestrator()
        user_profile = create_test_user_profile()

        # Create two plans that differ in only one dimension
        plan_a = create_test_plan("PLAN-A", coinsurance=20.0, has_exclusions=False, has_limits=False)
        plan_b = create_test_plan("PLAN-B", coinsurance=20.0, has_exclusions=True, has_limits=False)

        scores_a = orchestrator.score_plan(plan_a, user_profile)
        scores_b = orchestrator.score_plan(plan_b, user_profile)

        # Cost and limit scores should be identical (same cost structure and limits)
        assert scores_a["cost"] == scores_b["cost"], "Cost score changed when only exclusions changed"
        assert scores_a["limit"] == scores_b["limit"], "Limit score changed when only exclusions changed"

        # Exclusion scores should differ
        assert scores_a["exclusion"] != scores_b["exclusion"], "Exclusion scores should differ"
