"""User profile models for plan recommendation engine."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpectedUsage(StrEnum):
    """Expected healthcare usage level."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class CostSharingPreference(StrEnum):
    """Preferred cost-sharing method."""

    COPAY = "Copay"
    COINSURANCE = "Coinsurance"
    EITHER = "Either"


class PriorityWeights(BaseModel):
    """Weights for different scoring dimensions.

    Weights should sum to 1.0 for normalized scoring.
    """

    coverage_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for coverage score (0.0-1.0)",
    )
    cost_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for cost score (0.0-1.0)",
    )
    limit_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for limit score (0.0-1.0)",
    )

    @field_validator("coverage_weight", "cost_weight", "limit_weight")
    @classmethod
    def validate_weights_range(cls, v: float) -> float:
        """Validate that weights are in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v

    @classmethod
    def default(cls) -> "PriorityWeights":
        """Create default priority weights (coverage-focused)."""
        return cls(coverage_weight=0.4, cost_weight=0.4, limit_weight=0.2)

    @classmethod
    def coverage_focused(cls) -> "PriorityWeights":
        """Create coverage-focused priority weights."""
        return cls(coverage_weight=0.6, cost_weight=0.3, limit_weight=0.1)

    @classmethod
    def cost_focused(cls) -> "PriorityWeights":
        """Create cost-focused priority weights."""
        return cls(coverage_weight=0.2, cost_weight=0.7, limit_weight=0.1)

    @classmethod
    def balanced(cls) -> "PriorityWeights":
        """Create balanced priority weights."""
        return cls(coverage_weight=0.33, cost_weight=0.33, limit_weight=0.34)

    model_config = ConfigDict(frozen=True)


class BudgetConstraints(BaseModel):
    """Budget constraints for plan selection."""

    max_monthly_premium: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum monthly premium in dollars",
    )
    max_annual_out_of_pocket: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum annual out-of-pocket cost in dollars",
    )
    max_copay_per_visit: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum copay per visit in dollars",
    )

    model_config = ConfigDict(frozen=True)


@dataclass
class UserProfile:
    """User profile containing preferences and requirements for plan matching.

    This model represents a user's healthcare needs, preferences, and constraints
    for matching against insurance plans.
    """

    family_size: int
    children_count: int
    adults_count: int
    expected_usage: ExpectedUsage
    priorities: PriorityWeights
    required_benefits: list[str]
    excluded_benefits_ok: list[str]
    preferred_cost_sharing: CostSharingPreference
    budget_constraints: BudgetConstraints | None = None

    def __post_init__(self) -> None:
        """Validate family composition."""
        if self.family_size != self.children_count + self.adults_count:
            raise ValueError(
                f"family_size ({self.family_size}) must equal "
                f"children_count ({self.children_count}) + adults_count ({self.adults_count})",
            )
        if self.family_size < 1:
            raise ValueError(f"family_size must be at least 1, got {self.family_size}")
        if self.children_count < 0:
            raise ValueError(
                f"children_count must be non-negative, got {self.children_count}",
            )
        if self.adults_count < 1:
            raise ValueError(f"adults_count must be at least 1, got {self.adults_count}")
