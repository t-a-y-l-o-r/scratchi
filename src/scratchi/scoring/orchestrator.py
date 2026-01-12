"""Scoring orchestrator that combines agent scores."""

import logging
from typing import Any

from scratchi.agents.coverage import CoverageAgent
from scratchi.agents.cost import CostAgent
from scratchi.agents.exclusion import ExclusionAgent
from scratchi.agents.limit import LimitAgent
from scratchi.models.plan import Plan
from scratchi.models.user import UserProfile

logger = logging.getLogger(__name__)


class ScoringOrchestrator:
    """Orchestrates scoring across multiple agents and combines results.

    Combines scores from Coverage, Cost, and Limit agents using user-defined
    priority weights. Exclusion agent score is incorporated into the overall
    evaluation but doesn't have a separate weight.
    """

    def __init__(self) -> None:
        """Initialize scoring orchestrator with agents."""
        self.coverage_agent = CoverageAgent()
        self.cost_agent = CostAgent()
        self.limit_agent = LimitAgent()
        self.exclusion_agent = ExclusionAgent()

    def score_plan(self, plan: Plan, user_profile: UserProfile) -> dict[str, float]:
        """Score a plan across all dimensions.

        Args:
            plan: Plan to score
            user_profile: User profile with preferences and priorities

        Returns:
            Dictionary with scores:
            - coverage: Coverage score (0-1)
            - cost: Cost score (0-1)
            - limit: Limit score (0-1)
            - exclusion: Exclusion score (0-1)
            - overall: Weighted overall score (0-1)
        """
        # Get individual agent scores
        coverage_score = self.coverage_agent.score(plan, user_profile)
        cost_score = self.cost_agent.score(plan, user_profile)
        limit_score = self.limit_agent.score(plan, user_profile)
        exclusion_score = self.exclusion_agent.score(plan, user_profile)

        # Calculate weighted overall score
        priorities = user_profile.priorities
        overall_score = (
            coverage_score * priorities.coverage_weight
            + cost_score * priorities.cost_weight
            + limit_score * priorities.limit_weight
        )

        # Apply exclusion score as a modifier (penalty for poor exclusions)
        # Exclusion score acts as a multiplier: 0.5 exclusion = 0.5x overall score
        # This ensures plans with very restrictive exclusions are penalized
        exclusion_modifier = 0.5 + (exclusion_score * 0.5)  # Maps [0,1] to [0.5, 1.0]
        overall_score *= exclusion_modifier

        # Ensure overall score is in [0, 1] range
        original_overall = overall_score
        overall_score = max(0.0, min(1.0, overall_score))
        if original_overall != overall_score:
            logger.warning(
                f"Overall score clamped from {original_overall:.4f} to {overall_score:.4f} "
                f"for plan {plan.plan_id} (indicates potential algorithm issue)",
            )

        logger.debug(
            f"Plan {plan.plan_id} scores: "
            f"coverage={coverage_score:.2f}, cost={cost_score:.2f}, "
            f"limit={limit_score:.2f}, exclusion={exclusion_score:.2f}, "
            f"overall={overall_score:.2f}",
        )

        return {
            "coverage": coverage_score,
            "cost": cost_score,
            "limit": limit_score,
            "exclusion": exclusion_score,
            "overall": overall_score,
        }

    def score_plans(
        self,
        plans: list[Plan],
        user_profile: UserProfile,
    ) -> list[dict[str, Any]]:
        """Score multiple plans and return results with plan info.

        Args:
            plans: List of plans to score
            user_profile: User profile with preferences and priorities

        Returns:
            List of dictionaries with plan_id and scores for each plan
        """
        results: list[dict[str, Any]] = []

        for plan in plans:
            scores = self.score_plan(plan, user_profile)
            results.append(
                {
                    "plan_id": plan.plan_id,
                    "scores": scores,
                },
            )

        return results
