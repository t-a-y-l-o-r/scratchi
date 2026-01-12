"""Coverage scoring agent for evaluating plan benefit coverage."""

import logging

from scratchi.agents.base import ScoringAgent
from scratchi.models.constants import CoverageStatus, EHBStatus
from scratchi.models.plan import Plan
from scratchi.models.user import UserProfile

logger = logging.getLogger(__name__)


class CoverageAgent:
    """Agent that scores plans based on benefit coverage.

    Evaluates:
    - Required benefits coverage ratio
    - EHB coverage bonus
    - Benefit breadth score
    - Exclusion penalty
    """

    def score(self, plan: Plan, user_profile: UserProfile) -> float:
        """Score a plan based on coverage against user requirements.

        Args:
            plan: Plan to score
            user_profile: User profile with required benefits

        Returns:
            Score between 0.0 and 1.0 (higher is better)
        """
        # Required benefits coverage ratio (0.4 weight)
        required_ratio = self._calculate_required_benefits_ratio(plan, user_profile)

        # EHB coverage bonus (0.2 weight)
        ehb_bonus = self._calculate_ehb_coverage_bonus(plan)

        # Benefit breadth score (0.2 weight)
        breadth_score = self._calculate_benefit_breadth_score(plan)

        # Exclusion penalty (0.2 weight)
        exclusion_penalty = self._calculate_exclusion_penalty(plan, user_profile)

        # Weighted combination
        coverage_score = (
            required_ratio * 0.4
            + ehb_bonus * 0.2
            + breadth_score * 0.2
            + exclusion_penalty * 0.2
        )

        # Ensure score is in [0, 1] range
        return max(0.0, min(1.0, coverage_score))

    def _calculate_required_benefits_ratio(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate ratio of required benefits that are covered.

        Args:
            plan: Plan to evaluate
            user_profile: User profile with required benefits

        Returns:
            Ratio between 0.0 and 1.0
        """
        if not user_profile.required_benefits:
            # If no required benefits, give full score
            return 1.0

        covered_count = 0
        for benefit_name in user_profile.required_benefits:
            benefit = plan.get_benefit(benefit_name)
            if benefit and benefit.is_covered_bool():
                covered_count += 1

        ratio = covered_count / len(user_profile.required_benefits)
        logger.debug(
            f"Plan {plan.plan_id}: {covered_count}/{len(user_profile.required_benefits)} "
            f"required benefits covered (ratio: {ratio:.2f})",
        )
        return ratio

    def _calculate_ehb_coverage_bonus(self, plan: Plan) -> float:
        """Calculate bonus for EHB coverage.

        Args:
            plan: Plan to evaluate

        Returns:
            Bonus score between 0.0 and 1.0
        """
        ehb_benefits = plan.get_ehb_benefits()
        total_benefits = len(plan.benefits)

        if total_benefits == 0:
            return 0.0

        # Bonus based on percentage of benefits that are EHB
        ehb_ratio = len(ehb_benefits) / total_benefits
        return ehb_ratio

    def _calculate_benefit_breadth_score(self, plan: Plan) -> float:
        """Calculate score based on benefit breadth (number of unique benefits).

        Args:
            plan: Plan to evaluate

        Returns:
            Score between 0.0 and 1.0 (normalized, higher is better)
        """
        # Count covered benefits
        covered_benefits = plan.get_covered_benefits()
        covered_count = len(covered_benefits)

        # Normalize: assume 20+ benefits is excellent (score = 1.0)
        # This is a heuristic - adjust based on actual data distribution
        max_expected_benefits = 20.0
        breadth_score = min(1.0, covered_count / max_expected_benefits)

        return breadth_score

    def _calculate_exclusion_penalty(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate penalty for excluding benefits user needs.

        Args:
            plan: Plan to evaluate
            user_profile: User profile with excluded benefits OK list

        Returns:
            Penalty score between 0.0 and 1.0 (higher = less penalty)
        """
        if not user_profile.excluded_benefits_ok:
            # If user doesn't specify excluded benefits, no penalty
            return 1.0

        # Check if plan excludes benefits that user actually needs
        # (i.e., benefits in required_benefits but not in excluded_benefits_ok)
        penalty_count = 0
        for benefit_name in user_profile.required_benefits:
            if benefit_name not in user_profile.excluded_benefits_ok:
                benefit = plan.get_benefit(benefit_name)
                if benefit and not benefit.is_covered_bool():
                    penalty_count += 1

        if not user_profile.required_benefits:
            return 1.0

        # Penalty: lose points for each excluded required benefit
        penalty_ratio = 1.0 - (penalty_count / len(user_profile.required_benefits))
        return max(0.0, penalty_ratio)
