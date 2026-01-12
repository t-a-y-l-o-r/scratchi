"""Templates for generating human-readable explanations."""

from scratchi.models.recommendation import (
    CostAnalysis,
    CoverageAnalysis,
    ExclusionAnalysis,
    LimitAnalysis,
)


class ExplanationStyle:
    """Explanation style options."""

    DETAILED = "detailed"
    CONCISE = "concise"


def format_coverage_explanation(
    analysis: CoverageAnalysis,
    style: str = ExplanationStyle.DETAILED,
) -> str:
    """Generate coverage explanation from analysis.

    Args:
        analysis: Coverage analysis data
        style: Explanation style (detailed or concise)

    Returns:
        Human-readable explanation string
    """
    if style == ExplanationStyle.CONCISE:
        if analysis.required_benefits_total == 0:
            return "Plan provides comprehensive coverage."
        ratio = analysis.required_benefits_covered / analysis.required_benefits_total
        return f"Plan covers {analysis.required_benefits_covered}/{analysis.required_benefits_total} required benefits ({ratio:.0%})."

    # Detailed style
    parts: list[str] = []
    if analysis.required_benefits_total > 0:
        ratio = analysis.required_benefits_covered / analysis.required_benefits_total
        if ratio == 1.0:
            parts.append(
                f"This plan covers all {analysis.required_benefits_total} of your required benefits: "
                f"{', '.join(analysis.covered_benefits[:5])}"
                f"{' and more' if len(analysis.covered_benefits) > 5 else ''}.",
            )
        else:
            parts.append(
                f"This plan covers {analysis.required_benefits_covered} of "
                f"{analysis.required_benefits_total} required benefits ({ratio:.0%}).",
            )
            if analysis.missing_benefits:
                if len(analysis.missing_benefits) == 1:
                    parts.append(f"Missing: {analysis.missing_benefits[0]}.")
                else:
                    parts.append(
                        f"Missing benefits include: {', '.join(analysis.missing_benefits[:3])}"
                        f"{' and more' if len(analysis.missing_benefits) > 3 else ''}.",
                    )
    else:
        parts.append(
            f"This plan provides comprehensive coverage with {analysis.total_benefits_count} total benefits available.",
        )

    if analysis.ehb_benefits_count > 0:
        ehb_ratio = analysis.ehb_benefits_count / max(analysis.total_benefits_count, 1)
        parts.append(
            f"Plan includes {analysis.ehb_benefits_count} Essential Health Benefits "
            f"({ehb_ratio:.0%} of {analysis.total_benefits_count} total benefits).",
        )

    return " ".join(parts)


def format_cost_explanation(
    analysis: CostAnalysis,
    style: str = ExplanationStyle.DETAILED,
) -> str:
    """Generate cost explanation from analysis.

    Args:
        analysis: Cost analysis data
        style: Explanation style (detailed or concise)

    Returns:
        Human-readable explanation string
    """
    if style == ExplanationStyle.CONCISE:
        if analysis.avg_coinsurance_rate is not None:
            return f"Average coinsurance: {analysis.avg_coinsurance_rate:.0f}%."
        return f"Cost-sharing method: {analysis.cost_sharing_method}."

    # Detailed style
    parts: list[str] = []

    if analysis.cost_sharing_method == "copay":
        parts.append(
            "This plan uses copay-based cost-sharing, providing predictable out-of-pocket costs "
            "for covered services.",
        )
    elif analysis.cost_sharing_method == "coinsurance":
        if analysis.avg_coinsurance_rate is not None:
            rate_desc = "moderate" if 20 <= analysis.avg_coinsurance_rate <= 40 else "higher" if analysis.avg_coinsurance_rate > 40 else "lower"
            parts.append(
                f"This plan uses coinsurance with a {rate_desc} average rate of "
                f"{analysis.avg_coinsurance_rate:.0f}% for covered services.",
            )
    else:
        parts.append(
            "This plan uses a mixed cost-sharing approach, combining copays and coinsurance "
            "depending on the service type.",
        )

    if analysis.annual_maximum is not None:
        parts.append(f"The annual maximum benefit is ${analysis.annual_maximum:,.0f}.")

    if analysis.out_of_network_rate is not None:
        if analysis.avg_coinsurance_rate is not None:
            oon_diff = analysis.out_of_network_rate - analysis.avg_coinsurance_rate
            if oon_diff > 10:
                parts.append(
                    f"Out-of-network services have significantly higher coinsurance "
                    f"({analysis.out_of_network_rate:.0f}% vs {analysis.avg_coinsurance_rate:.0f}% in-network).",
                )
            else:
                parts.append(
                    f"Out-of-network coinsurance is {analysis.out_of_network_rate:.0f}%.",
                )
        else:
            parts.append(f"Out-of-network coinsurance is {analysis.out_of_network_rate:.0f}%.")

    return " ".join(parts)


def format_limit_explanation(
    analysis: LimitAnalysis,
    style: str = ExplanationStyle.DETAILED,
) -> str:
    """Generate limit explanation from analysis.

    Args:
        analysis: Limit analysis data
        style: Explanation style (detailed or concise)

    Returns:
        Human-readable explanation string
    """
    if style == ExplanationStyle.CONCISE:
        if analysis.benefits_with_quantity_limits == 0 and analysis.benefits_with_time_limits == 0:
            return "No quantity or time limits on covered services."
        return f"{analysis.benefits_with_quantity_limits + analysis.benefits_with_time_limits} benefits have limits."

    # Detailed style
    parts: list[str] = []

    if analysis.benefits_with_quantity_limits == 0 and analysis.benefits_with_time_limits == 0:
        parts.append("This plan has no quantity or time-based limits on covered services.")
    else:
        limit_parts: list[str] = []
        if analysis.benefits_with_quantity_limits > 0:
            limit_parts.append(f"{analysis.benefits_with_quantity_limits} with quantity limits")
        if analysis.benefits_with_time_limits > 0:
            limit_parts.append(f"{analysis.benefits_with_time_limits} with time-based limits")
        if limit_parts:
            parts.append(f"This plan applies limits to {len(limit_parts)} benefit category types: {', '.join(limit_parts)}.")

    if analysis.restrictive_limits:
        if len(analysis.restrictive_limits) == 1:
            parts.append(
                f"Note: {analysis.restrictive_limits[0]} has restrictive limits that may limit usage.",
            )
        elif len(analysis.restrictive_limits) <= 3:
            parts.append(
                f"Note: Restrictive limits apply to {', '.join(analysis.restrictive_limits)}.",
            )
        else:
            parts.append(
                f"Note: Restrictive limits apply to {len(analysis.restrictive_limits)} benefits, "
                f"including {', '.join(analysis.restrictive_limits[:2])} and others.",
            )

    return " ".join(parts)


def format_exclusion_explanation(
    analysis: ExclusionAnalysis,
    style: str = ExplanationStyle.DETAILED,
) -> str:
    """Generate exclusion explanation from analysis.

    Args:
        analysis: Exclusion analysis data
        style: Explanation style (detailed or concise)

    Returns:
        Human-readable explanation string
    """
    if style == ExplanationStyle.CONCISE:
        if analysis.benefits_with_exclusions == 0:
            return "No significant exclusions or restrictions."
        return f"{analysis.benefits_with_exclusions} benefit(s) have exclusions or restrictions."

    # Detailed style
    parts: list[str] = []

    if analysis.benefits_with_exclusions == 0:
        parts.append("This plan has minimal exclusions or restrictions on covered services.")
    else:
        if analysis.benefits_with_exclusions == 1:
            parts.append("One benefit category has exclusions or restrictions.")
        else:
            parts.append(
                f"{analysis.benefits_with_exclusions} benefit categories have exclusions or restrictions.",
            )
        if analysis.complex_exclusions > 0:
            parts.append(
                f"{analysis.complex_exclusions} of these have complex exclusions "
                "that may require detailed policy review to understand fully.",
            )
        if analysis.prior_coverage_required:
            parts.append("Some benefits require prior coverage history or have waiting periods before coverage begins.")

    return " ".join(parts)
