"""Reasoning chain builder for generating plan explanations."""

import logging
import re
from typing import Any

from scratchi.agents.coverage import CoverageAgent
from scratchi.agents.cost import CostAgent
from scratchi.agents.exclusion import ExclusionAgent
from scratchi.agents.limit import LimitAgent
from scratchi.models.constants import YesNoStatus
from scratchi.models.plan import Plan, PlanBenefit
from scratchi.models.recommendation import (
    CostAnalysis,
    CoverageAnalysis,
    ExclusionAnalysis,
    LimitAnalysis,
    ReasoningChain,
    TradeOff,
)
from scratchi.models.user import UserProfile
from scratchi.reasoning.templates import (
    ExplanationStyle,
    format_cost_explanation,
    format_coverage_explanation,
    format_exclusion_explanation,
    format_limit_explanation,
)
from scratchi.scoring.orchestrator import ScoringOrchestrator

logger = logging.getLogger(__name__)


class ReasoningBuilder:
    """Builds reasoning chains for plan recommendations."""

    def __init__(self) -> None:
        """Initialize reasoning builder with agents."""
        self.orchestrator = ScoringOrchestrator()

    def build_reasoning_chain(
        self,
        plan: Plan,
        user_profile: UserProfile,
        style: str = ExplanationStyle.DETAILED,
    ) -> ReasoningChain:
        """Build a complete reasoning chain for a plan.

        Args:
            plan: Plan to analyze
            user_profile: User profile with preferences
            style: Explanation style (detailed or concise)

        Returns:
            ReasoningChain with analysis and explanations
        """
        # Perform analyses
        coverage_analysis = self._analyze_coverage(plan, user_profile)
        cost_analysis = self._analyze_cost(plan)
        limit_analysis = self._analyze_limits(plan)
        exclusion_analysis = self._analyze_exclusions(plan)

        # Generate explanations
        explanations = [
            format_coverage_explanation(coverage_analysis, style),
            format_cost_explanation(cost_analysis, style),
            format_limit_explanation(limit_analysis, style),
            format_exclusion_explanation(exclusion_analysis, style),
        ]

        # Identify trade-offs
        trade_offs = self._identify_trade_offs(
            plan,
            user_profile,
            coverage_analysis,
            cost_analysis,
        )

        # Identify strengths and weaknesses
        strengths = self._identify_strengths(
            plan,
            user_profile,
            coverage_analysis,
            cost_analysis,
        )
        weaknesses = self._identify_weaknesses(
            plan,
            user_profile,
            coverage_analysis,
            cost_analysis,
            limit_analysis,
        )

        return ReasoningChain(
            coverage_analysis=coverage_analysis,
            cost_analysis=cost_analysis,
            limit_analysis=limit_analysis,
            exclusion_analysis=exclusion_analysis,
            explanations=explanations,
            trade_offs=trade_offs,
            strengths=strengths,
            weaknesses=weaknesses,
        )

    def _analyze_coverage(
        self,
        plan: Plan,
        user_profile: UserProfile,
    ) -> CoverageAnalysis:
        """Analyze plan coverage against user requirements.

        Args:
            plan: Plan to analyze
            user_profile: User profile with required benefits

        Returns:
            CoverageAnalysis object
        """
        required_benefits_covered = 0
        missing_benefits: list[str] = []
        covered_benefits: list[str] = []

        for benefit_name in user_profile.required_benefits:
            benefit = plan.get_benefit(benefit_name)
            if benefit and benefit.is_covered_bool():
                required_benefits_covered += 1
                covered_benefits.append(benefit_name)
            else:
                missing_benefits.append(benefit_name)

        ehb_benefits = plan.get_ehb_benefits()
        total_benefits = len(plan.benefits)

        return CoverageAnalysis(
            required_benefits_covered=required_benefits_covered,
            required_benefits_total=len(user_profile.required_benefits),
            ehb_benefits_count=len(ehb_benefits),
            total_benefits_count=total_benefits,
            missing_benefits=missing_benefits,
            covered_benefits=covered_benefits,
        )

    def _analyze_cost(self, plan: Plan) -> CostAnalysis:
        """Analyze plan cost-sharing.

        Args:
            plan: Plan to analyze

        Returns:
            CostAnalysis object
        """
        coinsurance_rates: list[float] = []
        oon_rates: list[float] = []
        copay_count = 0
        coinsurance_count = 0
        annual_maximums: list[float] = []

        for benefit in plan.benefits.values():
            if not benefit.is_covered_bool():
                continue

            # Check for copays
            if benefit.copay_inn_tier1 and benefit.copay_inn_tier1 not in [
                "Not Applicable",
                "Not Covered",
            ]:
                copay_count += 1

            # Check for coinsurance
            rate = benefit.get_coinsurance_rate("coins_inn_tier1")
            if rate is not None:
                coinsurance_rates.append(rate)
                coinsurance_count += 1

            # Check OON coinsurance
            oon_rate = benefit.get_coinsurance_rate("coins_outof_net")
            if oon_rate is not None:
                oon_rates.append(oon_rate)

            # Extract annual maximum from explanation
            if benefit.explanation:
                patterns = [r"\$([\d,]+)", r"([\d,]+)\s*dollars?"]
                for pattern in patterns:
                    matches = re.findall(pattern, benefit.explanation, re.IGNORECASE)
                    for match in matches:
                        try:
                            amount = float(match.replace(",", ""))
                            if amount > 0:
                                annual_maximums.append(amount)
                        except ValueError:
                            continue

        # Determine cost-sharing method
        if copay_count > coinsurance_count:
            cost_sharing_method = "copay"
        elif coinsurance_count > copay_count:
            cost_sharing_method = "coinsurance"
        else:
            cost_sharing_method = "mixed"

        avg_coinsurance = (
            sum(coinsurance_rates) / len(coinsurance_rates) if coinsurance_rates else None
        )
        avg_oon_rate = sum(oon_rates) / len(oon_rates) if oon_rates else None
        annual_max = max(annual_maximums) if annual_maximums else None

        return CostAnalysis(
            avg_coinsurance_rate=avg_coinsurance,
            copay_available=copay_count > 0,
            annual_maximum=annual_max,
            out_of_network_rate=avg_oon_rate,
            cost_sharing_method=cost_sharing_method,
        )

    def _analyze_limits(self, plan: Plan) -> LimitAnalysis:
        """Analyze plan limits and restrictions.

        Args:
            plan: Plan to analyze

        Returns:
            LimitAnalysis object
        """
        benefits_with_quantity_limits = 0
        benefits_with_time_limits = 0
        restrictive_limits: list[str] = []
        total_covered = 0

        for benefit in plan.benefits.values():
            if not benefit.is_covered_bool():
                continue

            total_covered += 1

            if benefit.has_quantity_limit():
                benefits_with_quantity_limits += 1
                # Consider limits restrictive if quantity is low
                if benefit.limit_qty is not None and benefit.limit_qty <= 2:
                    restrictive_limits.append(benefit.benefit_name)

            if benefit.limit_unit:
                unit_lower = benefit.limit_unit.lower()
                if any(
                    time_word in unit_lower
                    for time_word in ["year", "month", "day", "visit", "occurrence"]
                ):
                    benefits_with_time_limits += 1
                    if benefit.limit_qty is not None and benefit.limit_qty <= 2:
                        restrictive_limits.append(benefit.benefit_name)

        return LimitAnalysis(
            benefits_with_quantity_limits=benefits_with_quantity_limits,
            benefits_with_time_limits=benefits_with_time_limits,
            total_covered_benefits=total_covered,
            restrictive_limits=restrictive_limits,
        )

    def _analyze_exclusions(self, plan: Plan) -> ExclusionAnalysis:
        """Analyze plan exclusions and restrictions.

        Args:
            plan: Plan to analyze

        Returns:
            ExclusionAnalysis object
        """
        benefits_with_exclusions = 0
        complex_exclusions = 0
        prior_coverage_required = False

        exclusion_keywords = ["see policy", "see contract", "subject to", "may be excluded"]
        prior_coverage_keywords = [
            "prior coverage",
            "previous coverage",
            "must have had",
            "continuous coverage",
        ]

        for benefit in plan.benefits.values():
            if benefit.exclusions:
                benefits_with_exclusions += 1
                exclusions_lower = benefit.exclusions.lower()

                if any(keyword in exclusions_lower for keyword in exclusion_keywords):
                    complex_exclusions += 1

                if any(keyword in exclusions_lower for keyword in prior_coverage_keywords):
                    prior_coverage_required = True

        return ExclusionAnalysis(
            benefits_with_exclusions=benefits_with_exclusions,
            complex_exclusions=complex_exclusions,
            prior_coverage_required=prior_coverage_required,
        )

    def _identify_trade_offs(
        self,
        plan: Plan,
        user_profile: UserProfile,
        coverage_analysis: CoverageAnalysis,
        cost_analysis: CostAnalysis,
    ) -> list[TradeOff]:
        """Identify trade-offs in the plan.

        Args:
            plan: Plan to analyze
            user_profile: User profile
            coverage_analysis: Coverage analysis
            cost_analysis: Cost analysis

        Returns:
            List of TradeOff objects
        """
        trade_offs: list[TradeOff] = []

        # Trade-off: Good coverage but high cost
        if (
            coverage_analysis.required_benefits_covered == coverage_analysis.required_benefits_total
            and cost_analysis.avg_coinsurance_rate is not None
            and cost_analysis.avg_coinsurance_rate > 40
        ):
            trade_offs.append(
                TradeOff(
                    aspect="Coverage vs Cost",
                    pro="Covers all required benefits",
                    con=f"Higher coinsurance rate ({cost_analysis.avg_coinsurance_rate:.0f}%)",
                ),
            )

        # Trade-off: Lower cost but missing benefits
        if (
            coverage_analysis.missing_benefits
            and cost_analysis.avg_coinsurance_rate is not None
            and cost_analysis.avg_coinsurance_rate < 30
        ):
            trade_offs.append(
                TradeOff(
                    aspect="Cost vs Coverage",
                    pro=f"Lower coinsurance rate ({cost_analysis.avg_coinsurance_rate:.0f}%)",
                    con=f"Missing {len(coverage_analysis.missing_benefits)} required benefit(s)",
                ),
            )

        return trade_offs

    def _identify_strengths(
        self,
        plan: Plan,
        user_profile: UserProfile,
        coverage_analysis: CoverageAnalysis,
        cost_analysis: CostAnalysis,
    ) -> list[str]:
        """Identify plan strengths.

        Args:
            plan: Plan to analyze
            user_profile: User profile
            coverage_analysis: Coverage analysis
            cost_analysis: Cost analysis

        Returns:
            List of strength descriptions
        """
        strengths: list[str] = []

        if coverage_analysis.required_benefits_total > 0:
            if (
                coverage_analysis.required_benefits_covered
                == coverage_analysis.required_benefits_total
            ):
                strengths.append(
                    f"Covers all {coverage_analysis.required_benefits_total} required benefits",
                )

        if cost_analysis.annual_maximum is not None and cost_analysis.annual_maximum >= 3000:
            strengths.append(f"Generous annual maximum (${cost_analysis.annual_maximum:,.0f})")

        if cost_analysis.copay_available and user_profile.preferred_cost_sharing.value == "Copay":
            strengths.append("Uses copay-based cost-sharing (matches preference)")

        if coverage_analysis.ehb_benefits_count > 0:
            strengths.append(
                f"Includes {coverage_analysis.ehb_benefits_count} Essential Health Benefits",
            )

        return strengths

    def _identify_weaknesses(
        self,
        plan: Plan,
        user_profile: UserProfile,
        coverage_analysis: CoverageAnalysis,
        cost_analysis: CostAnalysis,
        limit_analysis: LimitAnalysis,
    ) -> list[str]:
        """Identify plan weaknesses.

        Args:
            plan: Plan to analyze
            user_profile: User profile
            coverage_analysis: Coverage analysis
            cost_analysis: Cost analysis
            limit_analysis: Limit analysis

        Returns:
            List of weakness descriptions
        """
        weaknesses: list[str] = []

        if coverage_analysis.missing_benefits:
            missing_count = len(coverage_analysis.missing_benefits)
            if missing_count == 1:
                weaknesses.append(f"Missing required benefit: {coverage_analysis.missing_benefits[0]}")
            else:
                weaknesses.append(f"Missing {missing_count} required benefits")

        if (
            cost_analysis.avg_coinsurance_rate is not None
            and cost_analysis.avg_coinsurance_rate > 40
        ):
            weaknesses.append(
                f"High coinsurance rate ({cost_analysis.avg_coinsurance_rate:.0f}%)",
            )

        if limit_analysis.restrictive_limits:
            weaknesses.append(
                f"Restrictive limits on {len(limit_analysis.restrictive_limits)} benefit(s)",
            )

        if cost_analysis.annual_maximum is not None and cost_analysis.annual_maximum < 1000:
            weaknesses.append(f"Low annual maximum (${cost_analysis.annual_maximum:,.0f})")

        return weaknesses
