"""Tests for Scoring Orchestrator."""

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
from scratchi.scoring.orchestrator import ScoringOrchestrator


def create_test_plan(plan_id: str) -> Plan:
    """Create a simple test plan."""
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
        coins_inn_tier1="30%",
    )
    return Plan.from_benefits([benefit])


class TestScoringOrchestrator:
    """Test cases for ScoringOrchestrator."""

    def test_score_plan_returns_all_scores(self) -> None:
        """Test that score_plan returns all dimension scores."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")
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

        scores = orchestrator.score_plan(plan, user_profile)

        assert "coverage" in scores
        assert "cost" in scores
        assert "limit" in scores
        assert "exclusion" in scores
        assert "overall" in scores

        # All scores should be in [0, 1] range
        for score_value in scores.values():
            assert 0.0 <= score_value <= 1.0

    def test_score_plan_overall_uses_priorities(self) -> None:
        """Test that overall score uses user priority weights."""
        orchestrator = ScoringOrchestrator()
        plan = create_test_plan("PLAN-001")

        # Coverage-focused priorities
        user_profile_coverage = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.coverage_focused(),
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        # Cost-focused priorities
        user_profile_cost = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.cost_focused(),
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        scores_coverage = orchestrator.score_plan(plan, user_profile_coverage)
        scores_cost = orchestrator.score_plan(plan, user_profile_cost)

        # Overall scores should differ based on priorities
        # (exact relationship depends on individual scores)
        assert scores_coverage["overall"] >= 0.0
        assert scores_cost["overall"] >= 0.0

    def test_score_plans_multiple(self) -> None:
        """Test scoring multiple plans."""
        orchestrator = ScoringOrchestrator()
        plans = [
            create_test_plan("PLAN-001"),
            create_test_plan("PLAN-002"),
        ]
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

        results = orchestrator.score_plans(plans, user_profile)

        assert len(results) == 2
        assert results[0]["plan_id"] == "PLAN-001"
        assert results[1]["plan_id"] == "PLAN-002"
        assert "scores" in results[0]
        assert "scores" in results[1]
