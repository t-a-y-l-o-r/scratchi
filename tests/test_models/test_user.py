"""Tests for user profile models."""

import pytest

from scratchi.models.user import (
    BudgetConstraints,
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)




class TestPriorityWeights:
    """Test cases for PriorityWeights model."""

    @pytest.mark.parametrize(
        "method,expected_coverage,expected_cost,expected_limit",
        [
            ("default", 0.4, 0.4, 0.2),
            ("coverage_focused", 0.6, 0.3, 0.1),
            ("cost_focused", 0.2, 0.7, 0.1),
            ("balanced", 0.33, 0.33, 0.34),
        ],
    )
    def test_create_preset_weights(
        self,
        method: str,
        expected_coverage: float,
        expected_cost: float,
        expected_limit: float,
    ) -> None:
        """Test creating preset priority weights."""
        weights = getattr(PriorityWeights, method)()
        assert weights.coverage_weight == expected_coverage
        assert weights.cost_weight == expected_cost
        assert abs(weights.limit_weight - expected_limit) < 0.01

    def test_create_custom_weights(self) -> None:
        """Test creating custom priority weights."""
        weights = PriorityWeights(
            coverage_weight=0.5,
            cost_weight=0.3,
            limit_weight=0.2,
        )
        assert weights.coverage_weight == 0.5
        assert weights.cost_weight == 0.3
        assert weights.limit_weight == 0.2

    def test_validate_weight_range(self) -> None:
        """Test weight validation."""
        # Valid weights
        weights = PriorityWeights(coverage_weight=0.5, cost_weight=0.3, limit_weight=0.2)
        assert weights.coverage_weight == 0.5

        # Invalid weight (too high)
        with pytest.raises(Exception):  # Pydantic ValidationError
            PriorityWeights(coverage_weight=1.5, cost_weight=0.3, limit_weight=0.2)

        # Invalid weight (negative)
        with pytest.raises(Exception):  # Pydantic ValidationError
            PriorityWeights(coverage_weight=-0.1, cost_weight=0.3, limit_weight=0.2)



class TestBudgetConstraints:
    """Test cases for BudgetConstraints model."""

    def test_create_budget_constraints(self) -> None:
        """Test creating budget constraints."""
        budget = BudgetConstraints(
            max_monthly_premium=500.0,
            max_annual_out_of_pocket=5000.0,
            max_copay_per_visit=50.0,
        )
        assert budget.max_monthly_premium == 500.0
        assert budget.max_annual_out_of_pocket == 5000.0
        assert budget.max_copay_per_visit == 50.0


    def test_validate_negative_budget(self) -> None:
        """Test that negative budget values are rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            BudgetConstraints(max_monthly_premium=-100.0)


class TestUserProfile:
    """Test cases for UserProfile model."""

    def test_create_valid_profile(self) -> None:
        """Test creating a valid user profile."""
        profile = UserProfile(
            family_size=4,
            children_count=2,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=["Orthodontia - Child"],
            excluded_benefits_ok=["Adult Orthodontia"],
            preferred_cost_sharing=CostSharingPreference.COPAY,
        )
        assert profile.family_size == 4
        assert profile.children_count == 2
        assert profile.adults_count == 2
        assert profile.expected_usage == ExpectedUsage.MEDIUM
        assert len(profile.required_benefits) == 1

    def test_create_profile_with_budget(self) -> None:
        """Test creating profile with budget constraints."""
        budget = BudgetConstraints(max_monthly_premium=500.0)
        profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.LOW,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
            budget_constraints=budget,
        )
        assert profile.budget_constraints is not None
        assert profile.budget_constraints.max_monthly_premium == 500.0

    def test_validate_family_size_mismatch(self) -> None:
        """Test that family size must match children + adults."""
        with pytest.raises(ValueError, match="family_size"):
            UserProfile(
                family_size=4,
                children_count=1,
                adults_count=1,  # Doesn't sum to 4
                expected_usage=ExpectedUsage.MEDIUM,
                priorities=PriorityWeights.default(),
                required_benefits=[],
                excluded_benefits_ok=[],
                preferred_cost_sharing=CostSharingPreference.EITHER,
            )

    def test_validate_minimum_family_size(self) -> None:
        """Test that family size must be at least 1."""
        with pytest.raises(ValueError, match="family_size"):
            UserProfile(
                family_size=0,
                children_count=0,
                adults_count=0,
                expected_usage=ExpectedUsage.LOW,
                priorities=PriorityWeights.default(),
                required_benefits=[],
                excluded_benefits_ok=[],
                preferred_cost_sharing=CostSharingPreference.EITHER,
            )

    def test_validate_minimum_adults(self) -> None:
        """Test that adults_count must be at least 1."""
        with pytest.raises(ValueError, match="adults_count"):
            UserProfile(
                family_size=2,
                children_count=2,
                adults_count=0,  # Must have at least 1 adult
                expected_usage=ExpectedUsage.MEDIUM,
                priorities=PriorityWeights.default(),
                required_benefits=[],
                excluded_benefits_ok=[],
                preferred_cost_sharing=CostSharingPreference.EITHER,
            )

    def test_validate_negative_children(self) -> None:
        """Test that children_count cannot be negative."""
        with pytest.raises(ValueError, match="children_count"):
            UserProfile(
                family_size=2,
                children_count=-1,
                adults_count=2,
                expected_usage=ExpectedUsage.MEDIUM,
                priorities=PriorityWeights.default(),
                required_benefits=[],
                excluded_benefits_ok=[],
                preferred_cost_sharing=CostSharingPreference.EITHER,
            )
