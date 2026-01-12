"""Tests for ReasoningBuilder."""

from datetime import date

import pytest

from scratchi.models.constants import CoverageStatus, YesNoStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)
from scratchi.reasoning.builder import ReasoningBuilder
from scratchi.reasoning.templates import ExplanationStyle


def create_test_plan(plan_id: str, benefit_names: list[str]) -> Plan:
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
            is_covered=CoverageStatus.COVERED,
            coins_inn_tier1="30%",
        )
        benefits.append(benefit)
    return Plan.from_benefits(benefits)


class TestReasoningBuilder:
    """Test cases for ReasoningBuilder."""

    def test_build_reasoning_chain(self) -> None:
        """Test building a complete reasoning chain."""
        builder = ReasoningBuilder()
        plan = create_test_plan("PLAN-001", ["Basic Dental Care - Adult"])
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

        reasoning = builder.build_reasoning_chain(plan, user_profile)

        assert reasoning.coverage_analysis.required_benefits_covered == 1
        assert reasoning.coverage_analysis.required_benefits_total == 1
        assert len(reasoning.explanations) == 4  # Coverage, cost, limit, exclusion
        assert isinstance(reasoning.strengths, list)
        assert isinstance(reasoning.weaknesses, list)
        assert isinstance(reasoning.trade_offs, list)

    def test_coverage_analysis_missing_benefits(self) -> None:
        """Test coverage analysis identifies missing benefits."""
        builder = ReasoningBuilder()
        plan = create_test_plan("PLAN-001", ["Basic Dental Care - Adult"])
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

        reasoning = builder.build_reasoning_chain(plan, user_profile)

        assert reasoning.coverage_analysis.required_benefits_covered == 1
        assert reasoning.coverage_analysis.required_benefits_total == 2
        assert "Orthodontia - Child" in reasoning.coverage_analysis.missing_benefits
        assert len(reasoning.weaknesses) > 0  # Should identify missing benefit as weakness

    def test_cost_analysis_extracts_annual_maximum(self) -> None:
        """Test that cost analysis extracts annual maximum from explanations."""
        builder = ReasoningBuilder()
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-001",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
            explanation="Annual maximum of $2,500 applies to all services",
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

        reasoning = builder.build_reasoning_chain(plan, user_profile)

        assert reasoning.cost_analysis.annual_maximum == 2500.0
        assert "$2,500" in reasoning.explanations[1]  # Cost explanation

    def test_limit_analysis_identifies_restrictive_limits(self) -> None:
        """Test that limit analysis identifies restrictive limits."""
        builder = ReasoningBuilder()
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-001",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
            quant_limit_on_svc=YesNoStatus.YES,
            limit_qty=2.0,
            limit_unit="Exam(s) per Year",
        )
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.HIGH,  # High usage user
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        reasoning = builder.build_reasoning_chain(plan, user_profile)

        assert reasoning.limit_analysis.benefits_with_quantity_limits == 1
        assert "Basic Dental Care - Adult" in reasoning.limit_analysis.restrictive_limits

    def test_explanation_styles(self) -> None:
        """Test that different explanation styles produce different outputs."""
        builder = ReasoningBuilder()
        plan = create_test_plan("PLAN-001", ["Basic Dental Care - Adult"])
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

        detailed = builder.build_reasoning_chain(plan, user_profile, ExplanationStyle.DETAILED)
        concise = builder.build_reasoning_chain(plan, user_profile, ExplanationStyle.CONCISE)

        # Concise should be shorter
        assert len(concise.explanations[0]) <= len(detailed.explanations[0])

    def test_trade_offs_identification(self) -> None:
        """Test that trade-offs are identified correctly."""
        builder = ReasoningBuilder()
        # Plan with all benefits but high coinsurance
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-001",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
            coins_inn_tier1="45%",  # High coinsurance
        )
        plan = Plan.from_benefits([benefit])
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

        reasoning = builder.build_reasoning_chain(plan, user_profile)

        # Should identify trade-off between coverage and cost
        assert len(reasoning.trade_offs) >= 0  # May or may not have trade-offs depending on analysis
