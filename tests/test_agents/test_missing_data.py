"""Tests for missing data handling (Section 6.2 recommendations).

This module implements tests for:
6.2 Missing Data Handling - Comprehensive tests for all agents
"""

from datetime import date

import pytest

from scratchi.agents.coverage import CoverageAgent
from scratchi.agents.cost import CostAgent
from scratchi.agents.exclusion import ExclusionAgent
from scratchi.agents.limit import LimitAgent
from scratchi.models.constants import CoverageStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)


def create_test_plan_with_missing_data(
    plan_id: str,
    missing_cost_sharing: bool = False,
    missing_limits: bool = False,
    missing_explanation: bool = False,
    missing_exclusions: bool = False,
) -> Plan:
    """Create a test plan with specified missing data fields."""
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
        # Missing cost-sharing if requested
        copay_inn_tier1=None if missing_cost_sharing else "$25",
        coins_inn_tier1=None if missing_cost_sharing else "30%",
        coins_outof_net=None if missing_cost_sharing else "40%",
        # Missing limits if requested
        quant_limit_on_svc=None if missing_limits else None,  # Keep as None for no limits
        limit_qty=None if missing_limits else None,
        limit_unit=None if missing_limits else None,
        # Missing explanation if requested
        explanation=None if missing_explanation else "Annual maximum of $2,000 applies",
        # Missing exclusions if requested
        exclusions=None if missing_exclusions else None,
    )
    return Plan.from_benefits([benefit])


def create_test_user_profile() -> UserProfile:
    """Create a standard test user profile."""
    return UserProfile(
        family_size=2,
        children_count=0,
        adults_count=2,
        expected_usage=ExpectedUsage.MEDIUM,
        priorities=PriorityWeights.default(),
        required_benefits=["Basic Dental Care - Adult"],
        excluded_benefits_ok=[],
        preferred_cost_sharing=CostSharingPreference.EITHER,
    )


class TestMissingCostSharingData:
    """Tests for missing cost-sharing information."""

    def test_cost_agent_missing_all_cost_sharing(self) -> None:
        """Test CostAgent with plan missing all cost-sharing information."""
        agent = CostAgent()
        plan = create_test_plan_with_missing_data("PLAN-001", missing_cost_sharing=True)
        user_profile = create_test_user_profile()

        # Should not crash, should return a valid score
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        # With no cost data, should return neutral score (0.5) or similar
        # The exact value depends on other factors (copay preference, annual max, etc.)

    def test_cost_agent_missing_coinsurance(self) -> None:
        """Test CostAgent with plan missing coinsurance information."""
        agent = CostAgent()
        # Plan with copay but no coinsurance
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
            copay_inn_tier1="$25",
            coins_inn_tier1=None,  # Missing
            coins_outof_net=None,  # Missing
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_cost_agent_missing_copay(self) -> None:
        """Test CostAgent with plan missing copay information."""
        agent = CostAgent()
        # Plan with coinsurance but no copay
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
            copay_inn_tier1=None,  # Missing
            coins_inn_tier1="30%",
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_cost_agent_missing_out_of_network(self) -> None:
        """Test CostAgent with plan missing out-of-network cost information."""
        agent = CostAgent()
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
            coins_inn_tier1="30%",
            coins_outof_net=None,  # Missing
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_cost_agent_handles_missing_data_gracefully(self) -> None:
        """Test that CostAgent doesn't crash with missing data."""
        agent = CostAgent()
        # Plan with absolutely minimal data
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
            # All cost-sharing fields None
            copay_inn_tier1=None,
            copay_inn_tier2=None,
            copay_outof_net=None,
            coins_inn_tier1=None,
            coins_inn_tier2=None,
            coins_outof_net=None,
            explanation=None,
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        # Should not raise any exceptions
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0


class TestMissingLimitData:
    """Tests for missing limit information."""

    def test_limit_agent_missing_limit_information(self) -> None:
        """Test LimitAgent with plan missing limit information."""
        agent = LimitAgent()
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
            quant_limit_on_svc=None,  # Missing
            limit_qty=None,  # Missing
            limit_unit=None,  # Missing
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        # With no limits, should score higher (no limits = better)

    def test_limit_agent_missing_limit_quantity(self) -> None:
        """Test LimitAgent with plan missing limit quantity."""
        agent = LimitAgent()
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
            quant_limit_on_svc="Yes",  # Has limit indicator
            limit_qty=None,  # But missing quantity
            limit_unit="Exam(s) per Year",
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_limit_agent_handles_missing_data_gracefully(self) -> None:
        """Test that LimitAgent doesn't crash with missing limit data."""
        agent = LimitAgent()
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
            quant_limit_on_svc=None,
            limit_qty=None,
            limit_unit=None,
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        # Should not raise any exceptions
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0


class TestMissingExplanationData:
    """Tests for missing explanation fields."""

    def test_cost_agent_missing_explanation(self) -> None:
        """Test CostAgent with plan missing explanation (affects annual maximum extraction)."""
        agent = CostAgent()
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
            coins_inn_tier1="30%",
            explanation=None,  # Missing - affects annual maximum extraction
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        # Without explanation, annual maximum score should be neutral (0.5)

    def test_cost_agent_explanation_without_amount(self) -> None:
        """Test CostAgent with explanation that doesn't contain annual maximum amount."""
        agent = CostAgent()
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
            coins_inn_tier1="30%",
            explanation="Subject to annual maximum per year",  # No dollar amount
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_reasoning_builder_missing_explanation(self) -> None:
        """Test ReasoningBuilder with plan missing explanation."""
        from scratchi.reasoning.builder import ReasoningBuilder

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
            explanation=None,  # Missing
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        # Should not crash
        reasoning = builder.build_reasoning_chain(plan, user_profile)
        assert reasoning is not None
        # Annual maximum should be None when explanation is missing
        assert reasoning.cost_analysis.annual_maximum is None


class TestMissingExclusionData:
    """Tests for missing exclusion information."""

    def test_exclusion_agent_missing_exclusions(self) -> None:
        """Test ExclusionAgent with plan missing exclusion information."""
        agent = ExclusionAgent()
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
            exclusions=None,  # Missing
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        # No exclusions should score higher (1.0)

    def test_exclusion_agent_handles_missing_data_gracefully(self) -> None:
        """Test that ExclusionAgent doesn't crash with missing exclusion data."""
        agent = ExclusionAgent()
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
            exclusions=None,
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        # Should not raise any exceptions
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0


class TestMissingCoverageData:
    """Tests for missing coverage information."""

    def test_coverage_agent_missing_benefit_in_plan(self) -> None:
        """Test CoverageAgent when required benefit is missing from plan."""
        agent = CoverageAgent()
        # Plan doesn't have the required benefit
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="PLAN-001",
            benefit_name="Other Benefit",  # Not the required one
            is_covered=CoverageStatus.COVERED,
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
        # Should score lower since required benefit is missing

    def test_coverage_agent_missing_ehb_information(self) -> None:
        """Test CoverageAgent with plan missing EHB information."""
        agent = CoverageAgent()
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
            is_ehb=None,  # Missing EHB status
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_coverage_agent_handles_missing_data_gracefully(self) -> None:
        """Test that CoverageAgent doesn't crash with missing coverage data."""
        agent = CoverageAgent()
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
            is_ehb=None,
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        # Should not raise any exceptions
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0


class TestComprehensiveMissingData:
    """Tests for plans with multiple types of missing data."""

    def test_plan_with_all_missing_data(self) -> None:
        """Test scoring a plan with all optional data missing."""
        from scratchi.scoring.orchestrator import ScoringOrchestrator

        orchestrator = ScoringOrchestrator()
        # Plan with minimal data - only required fields
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
            # All optional fields None
            copay_inn_tier1=None,
            coins_inn_tier1=None,
            quant_limit_on_svc=None,
            limit_qty=None,
            limit_unit=None,
            explanation=None,
            exclusions=None,
            is_ehb=None,
        )
        plan = Plan.from_benefits([benefit])
        user_profile = create_test_user_profile()

        # Should not crash
        scores = orchestrator.score_plan(plan, user_profile)
        assert 0.0 <= scores["overall"] <= 1.0
        assert 0.0 <= scores["coverage"] <= 1.0
        assert 0.0 <= scores["cost"] <= 1.0
        assert 0.0 <= scores["limit"] <= 1.0
        assert 0.0 <= scores["exclusion"] <= 1.0

    def test_multiple_plans_with_missing_data(self) -> None:
        """Test scoring multiple plans with various missing data scenarios."""
        from scratchi.scoring.orchestrator import ScoringOrchestrator

        orchestrator = ScoringOrchestrator()
        user_profile = create_test_user_profile()

        plans = [
            # Plan with missing cost data
            create_test_plan_with_missing_data("PLAN-001", missing_cost_sharing=True),
            # Plan with missing limit data
            create_test_plan_with_missing_data("PLAN-002", missing_limits=True),
            # Plan with missing explanation
            create_test_plan_with_missing_data("PLAN-003", missing_explanation=True),
            # Plan with all data present
            create_test_plan_with_missing_data("PLAN-004", missing_cost_sharing=False),
        ]

        # Should not crash
        results = orchestrator.score_plans(plans, user_profile)
        assert len(results) == 4
        for result in results:
            assert 0.0 <= result["scores"]["overall"] <= 1.0
