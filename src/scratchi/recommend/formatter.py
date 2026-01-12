"""Formatters for recommendation output in various formats."""

import json
from typing import Any

from scratchi.models.recommendation import Recommendation


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

    for rec in recommendations:
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
