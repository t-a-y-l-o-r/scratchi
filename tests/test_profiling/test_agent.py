"""Tests for user profiling agent."""

import pytest

from scratchi.models.user import (
    BudgetConstraints,
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
)
from scratchi.profiling.agent import (
    calculate_default_priorities,
    create_profile_from_dict,
    create_profile_from_natural_language,
    extract_family_composition,
    infer_expected_usage,
)


class TestExtractFamilyComposition:
    """Test cases for extract_family_composition function."""

    def test_extract_explicit_fields(self) -> None:
        """Test extracting family composition from explicit fields."""
        data = {"family_size": 4, "children_count": 2, "adults_count": 2}
        family_size, children_count, adults_count = extract_family_composition(data)
        assert family_size == 4
        assert children_count == 2
        assert adults_count == 2

    def test_extract_from_children_and_adults(self) -> None:
        """Test extracting from children_count and adults_count only."""
        data = {"children_count": 1, "adults_count": 2}
        family_size, children_count, adults_count = extract_family_composition(data)
        assert family_size == 3
        assert children_count == 1
        assert adults_count == 2

    @pytest.mark.parametrize(
        "family_size_input,expected_family,expected_children,expected_adults",
        [
            (1, 1, 0, 1),
            (4, 4, 2, 2),  # Inferred: 2 adults, 2 children
        ],
    )
    def test_extract_from_family_size_only(
        self,
        family_size_input: int,
        expected_family: int,
        expected_children: int,
        expected_adults: int,
    ) -> None:
        """Test extracting from family_size only (infers composition)."""
        data = {"family_size": family_size_input}
        family_size, children_count, adults_count = extract_family_composition(data)
        assert family_size == expected_family
        assert children_count == expected_children
        assert adults_count == expected_adults

    def test_extract_missing_fields(self) -> None:
        """Test that missing fields raise ValueError."""
        data = {}
        with pytest.raises(ValueError, match="Cannot determine"):
            extract_family_composition(data)


class TestInferExpectedUsage:
    """Test cases for infer_expected_usage function."""

    def test_low_usage(self) -> None:
        """Test inferring low usage."""
        usage = infer_expected_usage(
            required_benefits=[],
            excluded_benefits_ok=[],
            family_size=1,
            children_count=0,
        )
        assert usage == ExpectedUsage.LOW

    def test_medium_usage(self) -> None:
        """Test inferring medium usage."""
        usage = infer_expected_usage(
            required_benefits=["Basic Dental Care - Adult", "Basic Dental Care - Child"],
            excluded_benefits_ok=[],
            family_size=3,
            children_count=1,
        )
        assert usage == ExpectedUsage.MEDIUM

    def test_high_usage(self) -> None:
        """Test inferring high usage."""
        usage = infer_expected_usage(
            required_benefits=["Orthodontia - Child", "Major Dental Care - Adult"],
            excluded_benefits_ok=[],
            family_size=4,
            children_count=2,
        )
        assert usage == ExpectedUsage.HIGH


class TestCalculateDefaultPriorities:
    """Test cases for calculate_default_priorities function."""

    def test_cost_focused_with_budget(self) -> None:
        """Test that budget constraints lead to cost-focused priorities."""
        budget = BudgetConstraints(max_monthly_premium=500.0)
        priorities = calculate_default_priorities(
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
            budget_constraints=budget,
        )
        assert priorities.cost_weight > priorities.coverage_weight

    def test_coverage_focused_with_many_benefits(self) -> None:
        """Test that many required benefits lead to coverage-focused priorities."""
        priorities = calculate_default_priorities(
            required_benefits=[
                "Benefit 1",
                "Benefit 2",
                "Benefit 3",
                "Benefit 4",
                "Benefit 5",
            ],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
            budget_constraints=None,
        )
        assert priorities.coverage_weight > priorities.cost_weight

    def test_balanced_default(self) -> None:
        """Test balanced priorities for default case."""
        priorities = calculate_default_priorities(
            required_benefits=["Basic Dental Care - Adult"],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
            budget_constraints=None,
        )
        # Should be relatively balanced
        assert abs(priorities.coverage_weight - priorities.cost_weight) < 0.2


class TestCreateProfileFromDict:
    """Test cases for create_profile_from_dict function."""

    def test_create_from_complete_dict(self) -> None:
        """Test creating profile from complete dictionary."""
        data = {
            "family_size": 4,
            "children_count": 2,
            "adults_count": 2,
            "required_benefits": ["Orthodontia - Child"],
            "excluded_benefits_ok": ["Adult Orthodontia"],
            "preferred_cost_sharing": "Copay",
            "expected_usage": "Medium",
            "priorities": {
                "coverage_weight": 0.5,
                "cost_weight": 0.3,
                "limit_weight": 0.2,
            },
        }
        profile = create_profile_from_dict(data)
        assert profile.family_size == 4
        assert profile.children_count == 2
        assert profile.adults_count == 2
        assert profile.expected_usage == ExpectedUsage.MEDIUM
        assert profile.preferred_cost_sharing == CostSharingPreference.COPAY
        assert profile.priorities.coverage_weight == 0.5

    def test_create_from_minimal_dict(self) -> None:
        """Test creating profile from minimal dictionary."""
        data = {
            "family_size": 2,
            "children_count": 0,
            "adults_count": 2,
            "required_benefits": ["Basic Dental Care - Adult"],
        }
        profile = create_profile_from_dict(data)
        assert profile.family_size == 2
        assert profile.required_benefits == ["Basic Dental Care - Adult"]
        assert profile.excluded_benefits_ok == []
        # Should infer expected usage
        assert profile.expected_usage in [ExpectedUsage.LOW, ExpectedUsage.MEDIUM, ExpectedUsage.HIGH]

    def test_create_with_budget_constraints(self) -> None:
        """Test creating profile with budget constraints."""
        data = {
            "family_size": 2,
            "children_count": 0,
            "adults_count": 2,
            "required_benefits": [],
            "budget_constraints": {
                "max_monthly_premium": 500.0,
                "max_annual_out_of_pocket": 5000.0,
            },
        }
        profile = create_profile_from_dict(data)
        assert profile.budget_constraints is not None
        assert profile.budget_constraints.max_monthly_premium == 500.0
        assert profile.budget_constraints.max_annual_out_of_pocket == 5000.0

    def test_create_with_invalid_required_benefits(self) -> None:
        """Test that invalid required_benefits raises ValueError."""
        data = {
            "family_size": 2,
            "children_count": 0,
            "adults_count": 2,
            "required_benefits": "not a list",  # Invalid type
        }
        with pytest.raises(ValueError, match="required_benefits"):
            create_profile_from_dict(data)


class TestCreateProfileFromNaturalLanguage:
    """Test cases for create_profile_from_natural_language function."""

    def test_extract_family_size(self) -> None:
        """Test extracting family size from natural language."""
        text = "I have a family of 4 people"
        profile = create_profile_from_natural_language(text)
        assert profile.family_size == 4

    def test_extract_children(self) -> None:
        """Test extracting children count from natural language."""
        text = "I have 2 children and need orthodontia coverage"
        profile = create_profile_from_natural_language(text)
        assert profile.children_count == 2
        assert "Orthodontia" in str(profile.required_benefits)

    def test_extract_benefits(self) -> None:
        """Test extracting required benefits from natural language."""
        text = "I need orthodontia coverage for my child"
        profile = create_profile_from_natural_language(text)
        assert len(profile.required_benefits) > 0
        assert any("orthodontia" in b.lower() for b in profile.required_benefits)

    def test_extract_cost_preference(self) -> None:
        """Test extracting cost preference from natural language."""
        text = "I prefer copays over coinsurance"
        profile = create_profile_from_natural_language(text)
        assert profile.preferred_cost_sharing == CostSharingPreference.COPAY

    def test_extract_budget(self) -> None:
        """Test extracting budget constraints from natural language."""
        text = "My budget is $500 per month"
        profile = create_profile_from_natural_language(text)
        assert profile.budget_constraints is not None
        assert profile.budget_constraints.max_monthly_premium == 500.0

