"""Cost scoring agent for evaluating plan cost-sharing."""

import logging
import re

from scratchi.agents.base import ScoringAgent
from scratchi.models.constants import NOT_APPLICABLE, NOT_COVERED, NO_CHARGE
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.user import CostSharingPreference, UserProfile

logger = logging.getLogger(__name__)


class CostAgent:
    """Agent that scores plans based on cost-sharing preferences.

    Evaluates:
    - Copay preference alignment
    - Coinsurance rate score
    - Annual maximum score (from explanations)
    - Out-of-network cost score
    """

    def score(self, plan: Plan, user_profile: UserProfile) -> float:
        """Score a plan based on cost-sharing against user preferences.

        Args:
            plan: Plan to score
            user_profile: User profile with cost preferences

        Returns:
            Score between 0.0 and 1.0 (higher is better)
        """
        # Copay preference alignment (0.3 weight)
        copay_alignment = self._calculate_copay_preference_alignment(plan, user_profile)

        # Coinsurance rate score (0.3 weight)
        coinsurance_score = self._calculate_coinsurance_rate_score(plan, user_profile)

        # Annual maximum score (0.2 weight)
        annual_max_score = self._calculate_annual_maximum_score(plan)

        # Out-of-network cost score (0.2 weight)
        oon_score = self._calculate_out_of_network_score(plan, user_profile)

        # Weighted combination
        cost_score = (
            copay_alignment * 0.3
            + coinsurance_score * 0.3
            + annual_max_score * 0.2
            + oon_score * 0.2
        )

        # Ensure score is in [0, 1] range
        original_score = cost_score
        clamped_score = max(0.0, min(1.0, cost_score))
        if original_score != clamped_score:
            logger.warning(
                f"CostAgent score clamped from {original_score:.4f} to {clamped_score:.4f} "
                f"for plan {plan.plan_id} (indicates potential algorithm issue)",
            )
        return clamped_score

    def _calculate_copay_preference_alignment(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate alignment with copay preference.

        Args:
            plan: Plan to evaluate
            user_profile: User profile with cost-sharing preference

        Returns:
            Score between 0.0 and 1.0
        """
        if user_profile.preferred_cost_sharing == CostSharingPreference.EITHER:
            return 1.0  # No preference, so full score

        # Sample a few key benefits to determine cost-sharing method
        sample_benefits = list(plan.benefits.values())[:5]  # Sample first 5
        if not sample_benefits:
            return 0.5  # Neutral if no benefits

        copay_count = 0
        coinsurance_count = 0

        for benefit in sample_benefits:
            if not benefit.is_covered_bool():
                continue

            # Check if copay exists
            if (
                benefit.copay_inn_tier1
                and benefit.copay_inn_tier1 not in [NOT_APPLICABLE, NOT_COVERED]
            ):
                copay_count += 1

            # Check if coinsurance exists
            if benefit.coins_inn_tier1:
                rate = benefit.get_coinsurance_rate("coins_inn_tier1")
                if rate is not None:
                    coinsurance_count += 1

        total = copay_count + coinsurance_count
        if total == 0:
            return 0.5  # Neutral if unclear

        copay_ratio = copay_count / total

        # Score based on preference
        if user_profile.preferred_cost_sharing == CostSharingPreference.COPAY:
            return copay_ratio
        else:  # COINSURANCE
            return 1.0 - copay_ratio

    def _calculate_coinsurance_rate_score(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate score based on coinsurance rates (lower is better).

        Args:
            plan: Plan to evaluate
            user_profile: User profile

        Returns:
            Score between 0.0 and 1.0 (lower coinsurance = higher score)
        """
        # Sample benefits to get average coinsurance rate
        rates: list[float] = []
        for benefit in plan.benefits.values():
            if not benefit.is_covered_bool():
                continue

            rate = benefit.get_coinsurance_rate("coins_inn_tier1")
            if rate is not None:
                rates.append(rate)

        if not rates:
            return 0.5  # Neutral if no coinsurance data

        avg_rate = sum(rates) / len(rates)

        # Score: lower coinsurance = higher score
        # 0% = 1.0, 50% = 0.0, 100% = 0.0
        if avg_rate <= 0:
            return 1.0
        if avg_rate >= 50:
            return 0.0

        # Linear interpolation: 0% -> 1.0, 50% -> 0.0
        score = 1.0 - (avg_rate / 50.0)
        return max(0.0, min(1.0, score))

    def _calculate_annual_maximum_score(self, plan: Plan) -> float:
        """Calculate score based on annual maximums mentioned in explanations.

        Args:
            plan: Plan to evaluate

        Returns:
            Score between 0.0 and 1.0 (higher maximum = higher score)
        """
        max_amounts: list[float] = []

        # Extract annual maximum amounts from explanations
        for benefit in plan.benefits.values():
            if benefit.explanation:
                # Look for dollar amounts in explanations
                # Pattern: $1,000 or $1000 or 1000 dollars
                patterns = [
                    r"\$([\d,]+)",
                    r"([\d,]+)\s*dollars?",
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, benefit.explanation, re.IGNORECASE)
                    for match in matches:
                        try:
                            amount = float(match.replace(",", ""))
                            if amount > 0:
                                max_amounts.append(amount)
                        except ValueError:
                            continue

        if not max_amounts:
            return 0.5  # Neutral if no maximum data found

        # Use highest maximum found
        max_amount = max(max_amounts)

        # Score: higher maximum = higher score
        # Normalize: $5000+ = 1.0, $0 = 0.0
        if max_amount >= 5000:
            return 1.0
        if max_amount <= 0:
            return 0.0

        # Linear interpolation
        score = min(1.0, max_amount / 5000.0)
        return score

    def _calculate_out_of_network_score(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> float:
        """Calculate score based on out-of-network cost-sharing.

        Args:
            plan: Plan to evaluate
            user_profile: User profile

        Returns:
            Score between 0.0 and 1.0 (lower OON cost = higher score)
        """
        oon_rates: list[float] = []

        for benefit in plan.benefits.values():
            if not benefit.is_covered_bool():
                continue

            rate = benefit.get_coinsurance_rate("coins_outof_net")
            if rate is not None:
                oon_rates.append(rate)

        if not oon_rates:
            return 0.5  # Neutral if no OON data

        avg_oon_rate = sum(oon_rates) / len(oon_rates)

        # Score: lower OON coinsurance = higher score
        # Similar to in-network scoring
        if avg_oon_rate <= 0:
            return 1.0
        if avg_oon_rate >= 50:
            return 0.0

        score = 1.0 - (avg_oon_rate / 50.0)
        return max(0.0, min(1.0, score))
