"""Recommendation engine for ranking and recommending plans."""

import logging
from typing import Any

from scratchi.models.plan import Plan
from scratchi.models.recommendation import Recommendation
from scratchi.models.user import UserProfile
from scratchi.reasoning.builder import ReasoningBuilder
from scratchi.scoring.orchestrator import ScoringOrchestrator

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Main engine for generating plan recommendations.

    Combines scoring, reasoning, and ranking to produce complete recommendations.
    """

    def __init__(self) -> None:
        """Initialize recommendation engine with orchestrator and builder."""
        self.orchestrator = ScoringOrchestrator()
        self.builder = ReasoningBuilder()

    def recommend(
        self,
        plans: list[Plan],
        user_profile: UserProfile,
        top_n: int | None = None,
    ) -> list[Recommendation]:
        """Generate ranked recommendations for a user profile.

        Args:
            plans: List of plans to evaluate
            user_profile: User profile with preferences and requirements
            top_n: Optional limit on number of recommendations (None = all)

        Returns:
            List of Recommendation objects, sorted by overall_score (descending)
        """
        if not plans:
            logger.warning("No plans provided for recommendation")
            return []

        recommendations: list[Recommendation] = []

        for plan in plans:
            # Score the plan
            scores = self.orchestrator.score_plan(plan, user_profile)

            # Build reasoning chain
            reasoning_chain = self.builder.build_reasoning_chain(plan, user_profile)

            # Create recommendation
            recommendation = Recommendation(
                plan_id=plan.plan_id,
                overall_score=scores["overall"],
                rank=0,  # Will be set after sorting
                reasoning_chain=reasoning_chain,
                user_fit_scores={
                    "coverage": scores["coverage"],
                    "cost": scores["cost"],
                    "limit": scores["limit"],
                    "exclusion": scores["exclusion"],
                },
            )
            recommendations.append(recommendation)

        # Sort by overall score (descending), then by coverage score for ties
        recommendations.sort(
            key=lambda r: (r.overall_score, r.user_fit_scores.get("coverage", 0.0)),
            reverse=True,
        )

        # Assign ranks and rebuild recommendations (since model is frozen)
        ranked_recommendations: list[Recommendation] = []
        for rank, recommendation in enumerate(recommendations, start=1):
            ranked_recommendations.append(
                Recommendation(
                    plan_id=recommendation.plan_id,
                    overall_score=recommendation.overall_score,
                    rank=rank,
                    reasoning_chain=recommendation.reasoning_chain,
                    user_fit_scores=recommendation.user_fit_scores,
                ),
            )
        recommendations = ranked_recommendations

        # Limit to top N if specified
        if top_n is not None:
            recommendations = recommendations[:top_n]

        if recommendations:
            logger.info(
                f"Generated {len(recommendations)} recommendations "
                f"(top score: {recommendations[0].overall_score:.2f})",
            )
        else:
            logger.info("No recommendations generated")

        return recommendations

    def recommend_with_plans(
        self,
        plans: list[Plan],
        user_profile: UserProfile,
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate recommendations with full plan objects included.

        Args:
            plans: List of plans to evaluate
            user_profile: User profile with preferences and requirements
            top_n: Optional limit on number of recommendations

        Returns:
            List of dictionaries with plan, recommendation, and scores
        """
        recommendations = self.recommend(plans, user_profile, top_n)

        # Create plan lookup
        plan_dict = {plan.plan_id: plan for plan in plans}

        # Combine recommendations with plans
        results: list[dict[str, Any]] = []
        for recommendation in recommendations:
            plan = plan_dict.get(recommendation.plan_id)
            results.append(
                {
                    "plan": plan,
                    "recommendation": recommendation,
                },
            )

        return results
