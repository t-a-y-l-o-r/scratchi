"""User profiling agent implementation."""

import logging
import re
from typing import Any

from scratchi.models.user import (
    BudgetConstraints,
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)

logger = logging.getLogger(__name__)


def extract_family_composition(data: dict[str, Any]) -> tuple[int, int, int]:
    """Extract family composition from input data.

    Args:
        data: Dictionary containing family information

    Returns:
        Tuple of (family_size, children_count, adults_count)

    Raises:
        ValueError: If family composition cannot be determined
    """
    # Try explicit fields first
    if "family_size" in data and "children_count" in data and "adults_count" in data:
        family_size = int(data["family_size"])
        children_count = int(data["children_count"])
        adults_count = int(data["adults_count"])
        return (family_size, children_count, adults_count)

    # Try to infer from individual fields
    if "children_count" in data and "adults_count" in data:
        children_count = int(data["children_count"])
        adults_count = int(data["adults_count"])
        family_size = children_count + adults_count
        return (family_size, children_count, adults_count)

    # Try family_size alone (assume at least 1 adult)
    if "family_size" in data:
        family_size = int(data["family_size"])
        # Default: assume 1 adult, rest children
        if family_size == 1:
            return (1, 0, 1)
        # If family_size > 1, assume 2 adults, rest children
        adults_count = min(2, family_size - 1)
        children_count = family_size - adults_count
        return (family_size, children_count, adults_count)

    raise ValueError(
        "Cannot determine family composition. "
        "Provide 'family_size', 'children_count', and 'adults_count'",
    )


def infer_expected_usage(
    required_benefits: list[str],
    excluded_benefits_ok: list[str],
    family_size: int,
    children_count: int,
) -> ExpectedUsage:
    """Infer expected usage level from user input.

    Args:
        required_benefits: List of required benefit names
        excluded_benefits_ok: List of benefits user doesn't need
        family_size: Total family size
        children_count: Number of children

    Returns:
        ExpectedUsage enum value
    """
    # More required benefits suggests higher usage
    benefit_count_score = len(required_benefits) * 2

    # Children typically need more care
    children_score = children_count * 3

    # Larger families may need more care
    family_score = family_size

    # Special benefits that suggest higher usage
    high_usage_keywords = [
        "orthodontia",
        "major",
        "surgery",
        "specialist",
        "chronic",
    ]
    special_benefit_score = sum(
        5 for benefit in required_benefits
        if any(keyword in benefit.lower() for keyword in high_usage_keywords)
    )

    total_score = benefit_count_score + children_score + family_score + special_benefit_score

    if total_score >= 15:
        return ExpectedUsage.HIGH
    if total_score >= 8:
        return ExpectedUsage.MEDIUM
    return ExpectedUsage.LOW


def calculate_default_priorities(
    required_benefits: list[str],
    excluded_benefits_ok: list[str],
    preferred_cost_sharing: CostSharingPreference,
    budget_constraints: BudgetConstraints | None,
) -> PriorityWeights:
    """Calculate priority weights based on user input.

    Args:
        required_benefits: List of required benefit names
        excluded_benefits_ok: List of benefits user doesn't need
        preferred_cost_sharing: Preferred cost-sharing method
        budget_constraints: Optional budget constraints

    Returns:
        PriorityWeights object
    """
    # If budget constraints exist, prioritize cost more
    if budget_constraints is not None:
        if (
            budget_constraints.max_monthly_premium is not None
            or budget_constraints.max_annual_out_of_pocket is not None
        ):
            return PriorityWeights.cost_focused()

    # If many required benefits, prioritize coverage
    if len(required_benefits) >= 5:
        return PriorityWeights.coverage_focused()

    # If cost-sharing preference is specific, slightly favor cost
    if preferred_cost_sharing != CostSharingPreference.EITHER:
        return PriorityWeights(coverage_weight=0.35, cost_weight=0.45, limit_weight=0.2)

    # Default balanced approach
    return PriorityWeights.balanced()


def create_profile_from_dict(data: dict[str, Any]) -> UserProfile:
    """Create UserProfile from structured dictionary input.

    Args:
        data: Dictionary containing user profile data with keys:
            - family_size, children_count, adults_count (or inferred)
            - required_benefits (list[str])
            - excluded_benefits_ok (list[str], optional)
            - preferred_cost_sharing (str, optional)
            - expected_usage (str, optional)
            - priorities (dict, optional)
            - budget_constraints (dict, optional)

    Returns:
        UserProfile object

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Extract family composition
    family_size, children_count, adults_count = extract_family_composition(data)

    # Extract required benefits
    required_benefits = data.get("required_benefits", [])
    if not isinstance(required_benefits, list):
        raise ValueError("required_benefits must be a list")
    required_benefits = [str(b) for b in required_benefits]

    # Extract excluded benefits (optional)
    excluded_benefits_ok = data.get("excluded_benefits_ok", [])
    if not isinstance(excluded_benefits_ok, list):
        excluded_benefits_ok = []
    excluded_benefits_ok = [str(b) for b in excluded_benefits_ok]

    # Extract or infer expected usage
    if "expected_usage" in data:
        expected_usage_str = str(data["expected_usage"]).title()
        try:
            expected_usage = ExpectedUsage(expected_usage_str)
        except ValueError:
            logger.warning(
                f"Invalid expected_usage '{expected_usage_str}', inferring from input",
            )
            expected_usage = infer_expected_usage(
                required_benefits,
                excluded_benefits_ok,
                family_size,
                children_count,
            )
    else:
        expected_usage = infer_expected_usage(
            required_benefits,
            excluded_benefits_ok,
            family_size,
            children_count,
        )

    # Extract preferred cost sharing
    preferred_cost_sharing_str = data.get("preferred_cost_sharing", "Either")
    try:
        preferred_cost_sharing = CostSharingPreference(preferred_cost_sharing_str.title())
    except ValueError:
        logger.warning(
            f"Invalid preferred_cost_sharing '{preferred_cost_sharing_str}', using 'Either'",
        )
        preferred_cost_sharing = CostSharingPreference.EITHER

    # Extract budget constraints
    budget_data = data.get("budget_constraints")
    budget_constraints = None
    if budget_data:
        budget_constraints = BudgetConstraints(
            max_monthly_premium=budget_data.get("max_monthly_premium"),
            max_annual_out_of_pocket=budget_data.get("max_annual_out_of_pocket"),
            max_copay_per_visit=budget_data.get("max_copay_per_visit"),
        )

    # Extract or calculate priority weights
    if "priorities" in data and isinstance(data["priorities"], dict):
        priorities_data = data["priorities"]
        priorities = PriorityWeights(
            coverage_weight=float(priorities_data.get("coverage_weight", 0.4)),
            cost_weight=float(priorities_data.get("cost_weight", 0.4)),
            limit_weight=float(priorities_data.get("limit_weight", 0.2)),
        )
    else:
        priorities = calculate_default_priorities(
            required_benefits,
            excluded_benefits_ok,
            preferred_cost_sharing,
            budget_constraints,
        )

    return UserProfile(
        family_size=family_size,
        children_count=children_count,
        adults_count=adults_count,
        expected_usage=expected_usage,
        priorities=priorities,
        required_benefits=required_benefits,
        excluded_benefits_ok=excluded_benefits_ok,
        preferred_cost_sharing=preferred_cost_sharing,
        budget_constraints=budget_constraints,
    )


def create_profile_from_natural_language(text: str) -> UserProfile:
    """Create UserProfile from natural language input using basic keyword extraction.

    This is a basic implementation that extracts key information from text.
    For production, consider using LLM-based extraction.

    Args:
        text: Natural language text describing user needs

    Returns:
        UserProfile object

    Raises:
        ValueError: If essential information cannot be extracted
    """
    text_lower = text.lower()

    # Extract family size
    family_size = 1
    children_count = 0
    adults_count = 1

    # Look for family size patterns
    family_patterns = [
        r"family of (\d+)",
        r"(\d+) people",
        r"(\d+) members",
        r"(\d+) person",
    ]
    for pattern in family_patterns:
        match = re.search(pattern, text_lower)
        if match:
            family_size = int(match.group(1))
            break

    # Look for children patterns
    children_patterns = [
        r"(\d+) children?",
        r"(\d+) kids?",
        r"child",
        r"children",
    ]
    for pattern in children_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if match.group(0).startswith(("child", "kid")):
                # Just mentions children, try to infer count
                if family_size > 1:
                    children_count = max(1, family_size - 2)  # Assume 2 adults
                else:
                    children_count = 0
            else:
                children_count = int(match.group(1))
            break

    adults_count = family_size - children_count
    if adults_count < 1:
        adults_count = 1
        family_size = children_count + adults_count

    # Extract required benefits (basic keyword matching)
    benefit_keywords: dict[str, list[str]] = {
        "Orthodontia - Child": ["orthodontia", "braces", "child"],
        "Orthodontia - Adult": ["orthodontia", "braces", "adult"],
        "Basic Dental Care - Adult": ["basic", "adult", "dental", "cleaning"],
        "Basic Dental Care - Child": ["basic", "child", "dental", "cleaning"],
        "Major Dental Care - Adult": ["major", "adult", "dental", "crown", "root"],
        "Major Dental Care - Child": ["major", "child", "dental", "crown", "root"],
    }

    required_benefits: list[str] = []
    for benefit_name, keywords in benefit_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            required_benefits.append(benefit_name)

    # If no benefits found, add basic adult care as default
    if not required_benefits:
        required_benefits = ["Basic Dental Care - Adult"]

    # Extract excluded benefits
    excluded_benefits_ok: list[str] = []
    if "don't need" in text_lower or "don't want" in text_lower or "exclude" in text_lower:
        # Basic extraction - look for benefit names after exclusion keywords
        for benefit_name in benefit_keywords.keys():
            if benefit_name.lower() in text_lower:
                excluded_benefits_ok.append(benefit_name)

    # Extract cost preference
    preferred_cost_sharing = CostSharingPreference.EITHER
    if "copay" in text_lower or "copays" in text_lower:
        preferred_cost_sharing = CostSharingPreference.COPAY
    elif "coinsurance" in text_lower or "co-insurance" in text_lower:
        preferred_cost_sharing = CostSharingPreference.COINSURANCE

    # Extract budget constraints (basic)
    budget_constraints = None
    max_premium_patterns = [
        r"\$(\d+)\s*per\s*month",
        r"\$(\d+)\s*monthly",
        r"(\d+)\s*dollars?\s*per\s*month",
    ]
    for pattern in max_premium_patterns:
        match = re.search(pattern, text_lower)
        if match:
            max_monthly_premium = float(match.group(1))
            budget_constraints = BudgetConstraints(max_monthly_premium=max_monthly_premium)
            break

    # Infer expected usage
    expected_usage = infer_expected_usage(
        required_benefits,
        excluded_benefits_ok,
        family_size,
        children_count,
    )

    # Calculate priorities
    priorities = calculate_default_priorities(
        required_benefits,
        excluded_benefits_ok,
        preferred_cost_sharing,
        budget_constraints,
    )

    logger.info(
        f"Extracted profile from natural language: "
        f"family_size={family_size}, children={children_count}, "
        f"benefits={len(required_benefits)}",
    )

    return UserProfile(
        family_size=family_size,
        children_count=children_count,
        adults_count=adults_count,
        expected_usage=expected_usage,
        priorities=priorities,
        required_benefits=required_benefits,
        excluded_benefits_ok=excluded_benefits_ok,
        preferred_cost_sharing=preferred_cost_sharing,
        budget_constraints=budget_constraints,
    )
