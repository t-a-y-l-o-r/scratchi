"""Exclusion scoring agent for evaluating plan exclusions and restrictions."""

import logging

from scratchi.agents.base import ScoringAgent
from scratchi.models.plan import Plan
from scratchi.models.user import UserProfile

logger = logging.getLogger(__name__)


class ExclusionAgent:
    """Agent that scores plans based on exclusion complexity and restrictions.

    Evaluates:
    - Exclusion complexity (simpler = better)
    - Prior coverage requirements
    - General exclusion patterns
    """

    def score(self, plan: Plan, user_profile: UserProfile) -> float:
        """Score a plan based on exclusion complexity.

        Args:
            plan: Plan to score
            user_profile: User profile

        Returns:
            Score between 0.0 and 1.0 (higher is better)
        """
        # Exclusion complexity score (simpler = better)
        complexity_score = self._calculate_exclusion_complexity_score(plan)

        # Prior coverage requirement penalty
        prior_coverage_penalty = self._calculate_prior_coverage_penalty(plan)

        # Combined score (weighted)
        exclusion_score = complexity_score * 0.7 + prior_coverage_penalty * 0.3

        # Ensure score is in [0, 1] range
        original_score = exclusion_score
        clamped_score = max(0.0, min(1.0, exclusion_score))
        if original_score != clamped_score:
            logger.warning(
                f"ExclusionAgent score clamped from {original_score:.4f} to {clamped_score:.4f} "
                f"for plan {plan.plan_id} (indicates potential algorithm issue)",
            )
        return clamped_score

    def _calculate_exclusion_complexity_score(self, plan: Plan) -> float:
        """Calculate score based on exclusion complexity.

        Args:
            plan: Plan to evaluate

        Returns:
            Score between 0.0 and 1.0 (simpler exclusions = higher score)
        """
        total_exclusions = 0
        complex_exclusions = 0

        for benefit in plan.benefits.values():
            if benefit.exclusions:
                total_exclusions += 1
                exclusion_text = benefit.exclusions.lower()

                # Indicators of complexity
                complexity_indicators = [
                    "see policy",
                    "see contract",
                    "subject to",
                    "may be excluded",
                    "varies by",
                    "consult",
                ]

                if any(indicator in exclusion_text for indicator in complexity_indicators):
                    complex_exclusions += 1

        if total_exclusions == 0:
            return 1.0  # No exclusions = perfect score

        # Score: fewer complex exclusions = higher score
        complexity_ratio = complex_exclusions / total_exclusions
        score = 1.0 - complexity_ratio

        return max(0.0, min(1.0, score))

    def _calculate_prior_coverage_penalty(self, plan: Plan) -> float:
        """Calculate penalty for prior coverage requirements.

        Args:
            plan: Plan to evaluate

        Returns:
            Score between 0.0 and 1.0 (higher = less penalty)
        """
        prior_coverage_keywords = [
            "prior coverage",
            "previous coverage",
            "must have had",
            "continuous coverage",
            "preexisting",
        ]

        benefits_with_prior_req = 0
        total_benefits = len(plan.benefits)

        if total_benefits == 0:
            return 1.0

        for benefit in plan.benefits.values():
            if benefit.exclusions:
                exclusions_lower = benefit.exclusions.lower()
                if any(keyword in exclusions_lower for keyword in prior_coverage_keywords):
                    benefits_with_prior_req += 1

        # Score: fewer prior coverage requirements = higher score
        prior_req_ratio = benefits_with_prior_req / total_benefits
        score = 1.0 - prior_req_ratio

        return max(0.0, min(1.0, score))
