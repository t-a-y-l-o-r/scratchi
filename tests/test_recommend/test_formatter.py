"""Tests for recommendation formatters."""

from datetime import date

import pytest

from scratchi.models.constants import CoverageStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.recommendation import Recommendation, ReasoningChain
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)
from scratchi.recommend.formatter import (
    format_recommendations_json,
    format_recommendations_markdown,
    format_recommendations_text,
)
from scratchi.reasoning.builder import ReasoningBuilder
from scratchi.scoring.orchestrator import ScoringOrchestrator


def create_test_recommendation(plan_id: str, overall_score: float, rank: int) -> Recommendation:
    """Create a test recommendation."""
    # Create minimal plan for reasoning
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
    )
    plan = Plan.from_benefits([benefit])

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

    orchestrator = ScoringOrchestrator()
    builder = ReasoningBuilder()

    scores = orchestrator.score_plan(plan, user_profile)
    reasoning = builder.build_reasoning_chain(plan, user_profile)

    return Recommendation(
        plan_id=plan_id,
        overall_score=overall_score,
        rank=rank,
        reasoning_chain=reasoning,
        user_fit_scores=scores,
    )


class TestFormatter:
    """Test cases for recommendation formatters."""

    def test_format_json(self) -> None:
        """Test JSON formatting."""
        rec = create_test_recommendation("PLAN-001", 0.85, 1)
        json_output = format_recommendations_json([rec])

        assert "PLAN-001" in json_output
        assert "0.85" in json_output or "0.85" in json_output
        assert "recommendations" in json_output
        # Should be valid JSON
        import json

        parsed = json.loads(json_output)
        assert len(parsed["recommendations"]) == 1

    def test_format_text(self) -> None:
        """Test text formatting."""
        rec = create_test_recommendation("PLAN-001", 0.85, 1)
        text_output = format_recommendations_text([rec])

        assert "PLAN-001" in text_output
        assert "Rank #1" in text_output
        assert "Overall Score" in text_output
        # Format is 85.00% (from :.2% format)
        assert "85.00%" in text_output

    def test_format_markdown(self) -> None:
        """Test Markdown formatting."""
        rec = create_test_recommendation("PLAN-001", 0.85, 1)
        md_output = format_recommendations_markdown([rec])

        assert "# Plan Recommendations" in md_output
        assert "## Rank #1" in md_output
        assert "PLAN-001" in md_output
        assert "**Overall Score:**" in md_output

    def test_format_empty_list(self) -> None:
        """Test formatting empty recommendation list."""
        json_output = format_recommendations_json([])
        text_output = format_recommendations_text([])
        md_output = format_recommendations_markdown([])

        assert "No recommendations" in json_output
        assert "No recommendations" in text_output
        assert "No recommendations" in md_output

    def test_format_multiple_recommendations(self) -> None:
        """Test formatting multiple recommendations."""
        recs = [
            create_test_recommendation("PLAN-001", 0.85, 1),
            create_test_recommendation("PLAN-002", 0.75, 2),
        ]

        json_output = format_recommendations_json(recs)
        text_output = format_recommendations_text(recs)
        md_output = format_recommendations_markdown(recs)

        assert "PLAN-001" in json_output
        assert "PLAN-002" in json_output
        assert "PLAN-001" in text_output
        assert "PLAN-002" in text_output
        assert "PLAN-001" in md_output
        assert "PLAN-002" in md_output
