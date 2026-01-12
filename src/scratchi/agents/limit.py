"""Limit scoring agent for evaluating plan quantity and time limits."""

import logging
import re

from scratchi.agents.base import ScoringAgent
from scratchi.models.constants import YesNoStatus
from scratchi.models.plan import Plan
from scratchi.models.user import ExpectedUsage, UserProfile

logger = logging.getLogger(__name__)


class LimitAgent:
    """Agent that scores plans based on quantity and time limits.

    Evaluates:
    - Quantity limit score (more limits = lower score)
    - Time limit score
    - Exclusion period penalty
    """

    def score(self, plan: Plan, user_profile: UserProfile) -> float:
        """Score a plan based on limits against expected usage.

        Args:
            plan: Plan to score
            user_profile: User profile with expected usage

        Returns:
            Score between 0.0 and 1.0 (higher is better)
        """
        # Quantity limit score (0.4 weight)
        quantity_score = self._calculate_quantity_limit_score(plan, user_profile)

        # Time limit score (0.3 weight)
        time_score = self._calculate_time_limit_score(plan, user_profile)

        # Exclusion period penalty (0.3 weight)
        exclusion_penalty = self._calculate_exclusion_period_penalty(plan)

        # Weighted combination
        limit_score = (
            quantity_score * 0.4
            + time_score * 0.3
            + exclusion_penalty * 0.3
        )

        # Ensure score is in [0, 1] range
        original_score = limit_score
        clamped_score = max(0.0, min(1.0, limit_score))
        if original_score != clamped_score:
            logger.warning(
                f"LimitAgent score clamped from {original_score:.4f} to {clamped_score:.4f} "
                f"for plan {plan.plan_id} (indicates potential algorithm issue)",
            )
        return clamped_score

    def _calculate_quantity_limit_score(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate score based on quantity limits (fewer limits = higher score).

        Args:
            plan: Plan to evaluate
            user_profile: User profile with expected usage

        Returns:
            Score between 0.0 and 1.0
        """
        limited_benefits = 0
        total_covered = 0

        for benefit in plan.benefits.values():
            if not benefit.is_covered_bool():
                continue

            total_covered += 1
            if benefit.has_quantity_limit():
                limited_benefits += 1

        if total_covered == 0:
            logger.debug(
                f"Plan {plan.plan_id}: No covered benefits found for quantity limit calculation, "
                "using neutral score (0.5)",
            )
            return 0.5  # Neutral if no covered benefits

        # Score: fewer limits = higher score
        limit_ratio = limited_benefits / total_covered
        score = 1.0 - limit_ratio

        # Adjust based on expected usage
        # High usage users are more penalized by limits
        if user_profile.expected_usage == ExpectedUsage.HIGH:
            score *= 0.8  # More penalty for high usage
        elif user_profile.expected_usage == ExpectedUsage.MEDIUM:
            score *= 0.9  # Moderate penalty

        return max(0.0, min(1.0, score))

    def _calculate_time_limit_score(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate score based on time-based limits (e.g., "per year").

        Args:
            plan: Plan to evaluate
            user_profile: User profile with expected usage

        Returns:
            Score between 0.0 and 1.0
        """
        time_limited_benefits = 0
        total_covered = 0

        for benefit in plan.benefits.values():
            if not benefit.is_covered_bool():
                continue

            total_covered += 1
            if benefit.limit_unit:
                # Check if limit unit indicates time-based limit
                unit_lower = benefit.limit_unit.lower()
                if any(
                    time_word in unit_lower
                    for time_word in ["year", "month", "day", "visit", "occurrence"]
                ):
                    time_limited_benefits += 1

        if total_covered == 0:
            logger.debug(
                f"Plan {plan.plan_id}: No covered benefits found for time limit calculation, "
                "using neutral score (0.5)",
            )
            return 0.5  # Neutral if no covered benefits

        # Score: fewer time limits = higher score
        time_limit_ratio = time_limited_benefits / total_covered
        score = 1.0 - time_limit_ratio

        # Adjust based on expected usage
        if user_profile.expected_usage == ExpectedUsage.HIGH:
            score *= 0.8
        elif user_profile.expected_usage == ExpectedUsage.MEDIUM:
            score *= 0.9

        return max(0.0, min(1.0, score))

    def _calculate_exclusion_period_penalty(self, plan: Plan) -> float:
        """Calculate penalty for exclusion periods (waiting periods).

        Args:
            plan: Plan to evaluate

        Returns:
            Score between 0.0 and 1.0 (higher = less penalty)
        """
        exclusion_keywords = [
            "waiting period",
            "exclusion period",
            "must wait",
            "not covered for",
            "excluded for",
        ]

        benefits_with_exclusions = 0
        total_benefits = len(plan.benefits)

        if total_benefits == 0:
            return 1.0

        for benefit in plan.benefits.values():
            if benefit.exclusions:
                exclusions_lower = benefit.exclusions.lower()
                if any(keyword in exclusions_lower for keyword in exclusion_keywords):
                    benefits_with_exclusions += 1

        # Score: fewer exclusions = higher score
        exclusion_ratio = benefits_with_exclusions / total_benefits
        score = 1.0 - exclusion_ratio

        return max(0.0, min(1.0, score))
