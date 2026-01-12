"""Models for recommendations and reasoning chains."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CoverageAnalysis(BaseModel):
    """Analysis of plan coverage against user requirements."""

    required_benefits_covered: int
    required_benefits_total: int
    ehb_benefits_count: int
    total_benefits_count: int
    missing_benefits: list[str]
    covered_benefits: list[str]

    model_config = ConfigDict(frozen=True)


class CostAnalysis(BaseModel):
    """Analysis of plan cost-sharing."""

    avg_coinsurance_rate: float | None
    copay_available: bool
    annual_maximum: float | None
    out_of_network_rate: float | None
    cost_sharing_method: str  # "copay", "coinsurance", or "mixed"

    model_config = ConfigDict(frozen=True)


class LimitAnalysis(BaseModel):
    """Analysis of plan limits and restrictions."""

    benefits_with_quantity_limits: int
    benefits_with_time_limits: int
    total_covered_benefits: int
    restrictive_limits: list[str]  # Benefit names with restrictive limits

    model_config = ConfigDict(frozen=True)


class ExclusionAnalysis(BaseModel):
    """Analysis of plan exclusions and restrictions."""

    benefits_with_exclusions: int
    complex_exclusions: int
    prior_coverage_required: bool

    model_config = ConfigDict(frozen=True)


class TradeOff(BaseModel):
    """Represents a trade-off in a plan."""

    aspect: str
    pro: str
    con: str

    model_config = ConfigDict(frozen=True)


class ReasoningChain(BaseModel):
    """Complete reasoning chain for a plan recommendation.

    Contains detailed analysis and human-readable explanations.
    """

    coverage_analysis: CoverageAnalysis
    cost_analysis: CostAnalysis
    limit_analysis: LimitAnalysis
    exclusion_analysis: ExclusionAnalysis
    explanations: list[str] = Field(
        default_factory=list,
        description="Human-readable explanations",
    )
    trade_offs: list[TradeOff] = Field(
        default_factory=list,
        description="Identified trade-offs",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Plan strengths",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Plan weaknesses",
    )

    model_config = ConfigDict(frozen=True)


class Recommendation(BaseModel):
    """Complete recommendation for a plan."""

    plan_id: str
    overall_score: float
    rank: int
    reasoning_chain: ReasoningChain
    user_fit_scores: dict[str, float] = Field(
        description="Individual dimension scores (coverage, cost, limit, exclusion)",
    )

    model_config = ConfigDict(frozen=True)
