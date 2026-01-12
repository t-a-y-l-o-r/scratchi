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
        parts.append(
            f"Plan covers {analysis.required_benefits_covered} out of "
            f"{analysis.required_benefits_total} required benefits ({ratio:.0%}).",
        )
        if analysis.missing_benefits:
            parts.append(f"Missing benefits: {', '.join(analysis.missing_benefits[:3])}")
            if len(analysis.missing_benefits) > 3:
                parts.append(f"and {len(analysis.missing_benefits) - 3} more.")
    else:
        parts.append("Plan provides comprehensive coverage across all benefit categories.")

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
        parts.append("Plan uses copay-based cost-sharing, providing predictable out-of-pocket costs.")
    elif analysis.cost_sharing_method == "coinsurance":
        if analysis.avg_coinsurance_rate is not None:
            parts.append(
                f"Plan uses coinsurance with an average rate of {analysis.avg_coinsurance_rate:.0f}% "
                "for covered services.",
            )
    else:
        parts.append("Plan uses a mixed cost-sharing approach (copays and coinsurance).")

    if analysis.annual_maximum is not None:
        parts.append(f"Annual maximum benefit: ${analysis.annual_maximum:,.0f}.")

    if analysis.out_of_network_rate is not None:
        parts.append(
            f"Out-of-network coinsurance: {analysis.out_of_network_rate:.0f}% "
            "(higher than in-network).",
        )

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
        parts.append("Plan has no quantity or time-based limits on covered services.")
    else:
        if analysis.benefits_with_quantity_limits > 0:
            parts.append(
                f"{analysis.benefits_with_quantity_limits} benefit(s) have quantity limits "
                "(e.g., number of visits or procedures per period).",
            )
        if analysis.benefits_with_time_limits > 0:
            parts.append(
                f"{analysis.benefits_with_time_limits} benefit(s) have time-based limits "
                "(e.g., per year or per month).",
            )

    if analysis.restrictive_limits:
        parts.append(
            f"Restrictive limits found on: {', '.join(analysis.restrictive_limits[:2])}.",
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
        parts.append("Plan has minimal exclusions or restrictions on covered services.")
    else:
        parts.append(
            f"{analysis.benefits_with_exclusions} benefit(s) have exclusions or restrictions.",
        )
        if analysis.complex_exclusions > 0:
            parts.append(
                f"{analysis.complex_exclusions} benefit(s) have complex exclusions "
                "that may require policy review.",
            )
        if analysis.prior_coverage_required:
            parts.append("Some benefits require prior coverage or waiting periods.")

    return " ".join(parts)
