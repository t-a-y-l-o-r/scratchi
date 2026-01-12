"""Formatters for recommendation output in various formats."""

import json
from typing import Any

from scratchi.models.recommendation import Recommendation


def _compare_recommendations(
    current: Recommendation,
    previous: Recommendation,
) -> list[str]:
    """Compare two recommendations and identify key differences.

    Compares the current (lower-ranked) recommendation with the previous
    (higher-ranked) recommendation to identify why the previous plan ranks higher.

    Args:
        current: Current recommendation (lower rank/higher number)
        previous: Previous recommendation (higher rank/lower number)

    Returns:
        List of key difference descriptions (max 3) highlighting why
        the previous plan ranks higher
    """
    differences: list[str] = []

    # Compare coverage analysis first (often most important)
    current_cov = current.reasoning_chain.coverage_analysis
    previous_cov = previous.reasoning_chain.coverage_analysis

    if current_cov.required_benefits_covered != previous_cov.required_benefits_covered:
        differences.append(
            f"Covers {previous_cov.required_benefits_covered} vs {current_cov.required_benefits_covered} required benefits",
        )
    elif len(previous_cov.missing_benefits) < len(current_cov.missing_benefits):
        differences.append(
            f"Fewer missing benefits ({len(previous_cov.missing_benefits)} vs {len(current_cov.missing_benefits)})",
        )

    # Compare user fit scores (coverage, cost, limit)
    score_diff_threshold = 0.05  # 5% difference threshold
    for dimension in ["coverage", "cost", "limit"]:
        if len(differences) >= 3:
            break
        current_score = current.user_fit_scores.get(dimension, 0.0)
        previous_score = previous.user_fit_scores.get(dimension, 0.0)
        diff = previous_score - current_score

        if diff > score_diff_threshold:  # Only show if previous is significantly better
            differences.append(
                f"Higher {dimension.capitalize()} score ({previous_score:.0%} vs {current_score:.0%})",
            )

    # Compare cost analysis (annual maximum)
    if len(differences) < 3:
        current_cost = current.reasoning_chain.cost_analysis
        previous_cost = previous.reasoning_chain.cost_analysis

        if previous_cost.annual_maximum is not None:
            if current_cost.annual_maximum is None:
                differences.append(f"Has annual maximum (${previous_cost.annual_maximum:,.0f})")
            elif previous_cost.annual_maximum > current_cost.annual_maximum * 1.1:  # 10% higher
                differences.append(
                    f"Higher annual maximum (${previous_cost.annual_maximum:,.0f} vs ${current_cost.annual_maximum:,.0f})",
                )

    # Compare limit analysis
    if len(differences) < 3:
        current_limit = current.reasoning_chain.limit_analysis
        previous_limit = previous.reasoning_chain.limit_analysis

        if len(previous_limit.restrictive_limits) < len(current_limit.restrictive_limits):
            differences.append(
                f"Fewer restrictive limits ({len(previous_limit.restrictive_limits)} vs {len(current_limit.restrictive_limits)})",
            )

    # Return top 3 differences
    return differences[:3]


def format_recommendations_json(
    recommendations: list[Recommendation],
    user_profile: dict[str, Any] | None = None,
) -> str:
    """Format recommendations as JSON.

    Args:
        recommendations: List of recommendations to format
        user_profile: Optional user profile data to include

    Returns:
        JSON string
    """
    output: dict[str, Any] = {
        "recommendations": [],
    }

    for rec in recommendations:
        rec_dict: dict[str, Any] = {
            "plan_id": rec.plan_id,
            "rank": rec.rank,
            "overall_score": rec.overall_score,
            "user_fit_scores": rec.user_fit_scores,
            "strengths": rec.reasoning_chain.strengths,
            "weaknesses": rec.reasoning_chain.weaknesses,
            "reasoning": {
                "coverage": rec.reasoning_chain.explanations[0]
                if len(rec.reasoning_chain.explanations) > 0
                else "",
                "cost": rec.reasoning_chain.explanations[1]
                if len(rec.reasoning_chain.explanations) > 1
                else "",
                "limits": rec.reasoning_chain.explanations[2]
                if len(rec.reasoning_chain.explanations) > 2
                else "",
                "exclusions": rec.reasoning_chain.explanations[3]
                if len(rec.reasoning_chain.explanations) > 3
                else "",
            },
            "trade_offs": [
                {
                    "aspect": trade_off.aspect,
                    "pro": trade_off.pro,
                    "con": trade_off.con,
                }
                for trade_off in rec.reasoning_chain.trade_offs
            ],
        }
        output["recommendations"].append(rec_dict)

    if user_profile:
        output["user_profile"] = {
            "family_size": user_profile.get("family_size"),
            "children_count": user_profile.get("children_count"),
            "adults_count": user_profile.get("adults_count"),
            "expected_usage": user_profile.get("expected_usage"),
        }

    output["summary"] = (
        f"Found {len(recommendations)} plan(s) matching your criteria. "
        f"Top recommendation: {recommendations[0].plan_id} "
        f"(score: {recommendations[0].overall_score:.2f})"
        if recommendations
        else "No recommendations found."
    )

    return json.dumps(output, indent=2)


def format_recommendations_text(
    recommendations: list[Recommendation],
    user_profile: dict[str, Any] | None = None,
) -> str:
    """Format recommendations as human-readable text.

    Args:
        recommendations: List of recommendations to format
        user_profile: Optional user profile data to include

    Returns:
        Text string
    """
    lines: list[str] = []

    if not recommendations:
        return "No recommendations found."

    lines.append("=" * 60)
    lines.append("PLAN RECOMMENDATIONS")
    lines.append("=" * 60)
    lines.append("")

    if user_profile:
        lines.append("User Profile:")
        lines.append(f"  Family Size: {user_profile.get('family_size', 'N/A')}")
        if user_profile.get("children_count") is not None:
            lines.append(f"  Children: {user_profile.get('children_count')}")
        if user_profile.get("adults_count") is not None:
            lines.append(f"  Adults: {user_profile.get('adults_count')}")
        if user_profile.get("expected_usage"):
            lines.append(f"  Expected Usage: {user_profile.get('expected_usage')}")
        if user_profile.get("preferred_cost_sharing"):
            lines.append(f"  Preferred Cost Sharing: {user_profile.get('preferred_cost_sharing')}")
        required_benefits = user_profile.get("required_benefits", [])
        if required_benefits:
            lines.append(f"  Required Benefits: {len(required_benefits)} benefit(s)")
        lines.append("")

    for idx, rec in enumerate(recommendations):
        # Add comparison with previous plan if not the first one
        if idx > 0:
            previous = recommendations[idx - 1]
            differences = _compare_recommendations(rec, previous)
            if differences:
                lines.append(f"Key Differences from Rank #{previous.rank}:")
                for diff in differences:
                    lines.append(f"  • {diff}")
                lines.append("")

        lines.append(f"Rank #{rec.rank}: {rec.plan_id}")
        lines.append(f"Overall Score: {rec.overall_score:.2%}")
        lines.append("")
        lines.append("User Fit Scores:")
        for dimension, score in rec.user_fit_scores.items():
            lines.append(f"  {dimension.capitalize()}: {score:.2%}")
        lines.append("")

        if rec.reasoning_chain.strengths:
            lines.append("Strengths:")
            for strength in rec.reasoning_chain.strengths:
                lines.append(f"  • {strength}")
            lines.append("")

        if rec.reasoning_chain.weaknesses:
            lines.append("Weaknesses:")
            for weakness in rec.reasoning_chain.weaknesses:
                lines.append(f"  • {weakness}")
            lines.append("")

        if rec.reasoning_chain.explanations:
            lines.append("Reasoning:")
            for explanation in rec.reasoning_chain.explanations:
                lines.append(f"  {explanation}")
            lines.append("")

        if rec.reasoning_chain.trade_offs:
            lines.append("Trade-offs:")
            for trade_off in rec.reasoning_chain.trade_offs:
                lines.append(f"  {trade_off.aspect}:")
                lines.append(f"    Pro: {trade_off.pro}")
                lines.append(f"    Con: {trade_off.con}")
            lines.append("")

        # Only add separator if not the last recommendation
        if rec != recommendations[-1]:
            lines.append("-" * 60)
            lines.append("")

    return "\n".join(lines)


def format_recommendations_markdown(
    recommendations: list[Recommendation],
    user_profile: dict[str, Any] | None = None,
) -> str:
    """Format recommendations as Markdown.

    Args:
        recommendations: List of recommendations to format
        user_profile: Optional user profile data to include

    Returns:
        Markdown string
    """
    lines: list[str] = []

    if not recommendations:
        return "# Plan Recommendations\n\nNo recommendations found."

    lines.append("# Plan Recommendations")
    lines.append("")

    for rec in recommendations:
        lines.append(f"## Rank #{rec.rank}: {rec.plan_id}")
        lines.append("")
        lines.append(f"**Overall Score:** {rec.overall_score:.2%}")
        lines.append("")

        lines.append("### User Fit Scores")
        lines.append("")
        for dimension, score in rec.user_fit_scores.items():
            lines.append(f"- **{dimension.capitalize()}:** {score:.2%}")
        lines.append("")

        if rec.reasoning_chain.strengths:
            lines.append("### Strengths")
            lines.append("")
            for strength in rec.reasoning_chain.strengths:
                lines.append(f"- {strength}")
            lines.append("")

        if rec.reasoning_chain.weaknesses:
            lines.append("### Weaknesses")
            lines.append("")
            for weakness in rec.reasoning_chain.weaknesses:
                lines.append(f"- {weakness}")
            lines.append("")

        if rec.reasoning_chain.explanations:
            lines.append("### Reasoning")
            lines.append("")
            for explanation in rec.reasoning_chain.explanations:
                lines.append(f"{explanation}")
            lines.append("")

        if rec.reasoning_chain.trade_offs:
            lines.append("### Trade-offs")
            lines.append("")
            for trade_off in rec.reasoning_chain.trade_offs:
                lines.append(f"#### {trade_off.aspect}")
                lines.append("")
                lines.append(f"- **Pro:** {trade_off.pro}")
                lines.append(f"- **Con:** {trade_off.con}")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
