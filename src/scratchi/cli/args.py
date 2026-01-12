"""Command-line argument parsing for the CLI."""

import argparse
from pathlib import Path

from scratchi.reasoning.templates import ExplanationStyle


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Insurance plan recommendation engine with transparent reasoning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic recommendation
  scratchi --csv data/sample.csv --family-size 4 --children 2

  # With required benefits
  scratchi --csv data/sample.csv --family-size 2 --required "Basic Dental Care - Adult" "Orthodontia - Child"

  # JSON output
  scratchi --csv data/sample.csv --family-size 2 --format json

  # Top 3 recommendations
  scratchi --csv data/sample.csv --family-size 2 --top 3
        """,
    )

    # Required arguments
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to CSV file containing plan data",
    )

    # User profile arguments
    profile_group = parser.add_argument_group("User Profile")
    profile_group.add_argument(
        "--family-size",
        type=int,
        required=True,
        help="Total family size (adults + children)",
    )
    profile_group.add_argument(
        "--adults",
        type=int,
        default=None,
        help="Number of adults (default: family_size - children)",
    )
    profile_group.add_argument(
        "--children",
        type=int,
        default=0,
        help="Number of children (default: 0)",
    )
    profile_group.add_argument(
        "--expected-usage",
        type=str,
        choices=["Low", "Medium", "High"],
        default="Medium",
        help="Expected healthcare usage level (default: Medium)",
    )
    profile_group.add_argument(
        "--required",
        nargs="+",
        default=[],
        help="Required benefits (space-separated list)",
    )
    profile_group.add_argument(
        "--preferred-cost-sharing",
        type=str,
        choices=["Copay", "Coinsurance", "Either"],
        default="Either",
        help="Preferred cost-sharing method (default: Either)",
    )
    profile_group.add_argument(
        "--priority",
        type=str,
        choices=["default", "coverage", "cost", "balanced"],
        default="default",
        help="Priority weighting strategy (default: default)",
    )

    # Recommendation arguments
    rec_group = parser.add_argument_group("Recommendation Options")
    rec_group.add_argument(
        "--top",
        type=int,
        default=None,
        help="Limit recommendations to top N plans (default: all)",
    )
    rec_group.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    rec_group.add_argument(
        "--explanation-style",
        type=str,
        choices=["detailed", "concise"],
        default="detailed",
        help="Explanation detail level (default: detailed)",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: stdout)",
    )
    output_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[bool, str | None]:
    """Validate parsed arguments.

    Args:
        args: Parsed arguments

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate CSV file exists
    if not args.csv.exists():
        return False, f"CSV file not found: {args.csv}"

    # Validate non-negative values first
    if args.family_size < 1:
        return False, "Family size must be at least 1"

    if args.children < 0:
        return False, "Number of children cannot be negative"

    # Auto-calculate adults if not specified
    if args.adults is None:
        args.adults = args.family_size - args.children

    if args.adults < 0:
        return False, "Number of adults cannot be negative"

    # Validate family size consistency
    if args.adults + args.children != args.family_size:
        return False, (
            f"Family size mismatch: adults ({args.adults}) + children ({args.children}) "
            f"!= family_size ({args.family_size})"
        )

    # Validate top N
    if args.top is not None and args.top < 1:
        return False, "--top must be at least 1"

    return True, None
