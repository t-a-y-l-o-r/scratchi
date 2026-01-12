"""Main CLI entry point."""

import logging
import sys
from pathlib import Path

from scratchi.cli.args import parse_args, validate_args
from scratchi.data_loader import (
    aggregate_plans_from_benefits,
    load_plans_from_csv,
)
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
    PriorityWeights,
    UserProfile,
)
from scratchi.profiling.agent import create_profile_from_dict
from scratchi.recommend.engine import RecommendationEngine
from scratchi.recommend.formatter import (
    format_recommendations_json,
    format_recommendations_markdown,
    format_recommendations_text,
)
from scratchi.reasoning.templates import ExplanationStyle

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity flags.

    Args:
        verbose: Enable verbose logging
        quiet: Suppress all non-error messages
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s" if not verbose else "%(levelname)s: %(message)s",
        force=True,
    )


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        args = parse_args()
    except SystemExit:
        return 1

    # Validate arguments
    is_valid, error_msg = validate_args(args)
    if not is_valid:
        logger.error(f"Error: {error_msg}")
        return 1

    # Configure logging
    _configure_logging(args.verbose, args.quiet)

    try:
        # Load plans from CSV
        if not args.quiet:
            logger.info(f"Loading plans from {args.csv}...")
        benefits = load_plans_from_csv(args.csv)
        plans = aggregate_plans_from_benefits(benefits)
        if not args.quiet:
            logger.info(f"Loaded {len(plans)} plans")

        if not plans:
            logger.error("No plans found in CSV file")
            return 1

        # Create user profile
        if not args.quiet:
            logger.info("Creating user profile...")
        user_data = {
            "family_size": args.family_size,
            "adults_count": args.adults,
            "children_count": args.children,
            "expected_usage": args.expected_usage,
            "required_benefits": args.required,
            "preferred_cost_sharing": args.preferred_cost_sharing,
        }
        user_profile = create_profile_from_dict(user_data)

        # Set priority weights
        if args.priority == "coverage":
            user_profile.priorities = PriorityWeights.coverage_focused()
        elif args.priority == "cost":
            user_profile.priorities = PriorityWeights.cost_focused()
        elif args.priority == "balanced":
            user_profile.priorities = PriorityWeights.balanced()
        else:
            user_profile.priorities = PriorityWeights.default()

        # Generate recommendations
        if not args.quiet:
            logger.info("Generating recommendations...")
        engine = RecommendationEngine()

        explanation_style = (
            ExplanationStyle.CONCISE
            if args.explanation_style == "concise"
            else ExplanationStyle.DETAILED
        )
        recommendations = engine.recommend(
            plans,
            user_profile,
            top_n=args.top,
            explanation_style=explanation_style,
        )

        if not recommendations:
            logger.warning("No recommendations found matching your criteria")
            return 0

        if not args.quiet:
            logger.info(f"Generated {len(recommendations)} recommendation(s)")

        # Format output
        if args.format == "json":
            output = format_recommendations_json(recommendations)
        elif args.format == "markdown":
            output = format_recommendations_markdown(recommendations)
        else:
            output = format_recommendations_text(recommendations)

        # Write output
        if args.output:
            try:
                output_path = args.output.expanduser()
                # Create parent directories if they don't exist
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(output, encoding="utf-8")
                if not args.quiet:
                    logger.info(f"Output written to {output_path}")
            except OSError as error:
                logger.error(f"Failed to write output file: {error}")
                return 1
        else:
            print(output)

        return 0

    except FileNotFoundError as error:
        logger.error(f"File not found: {error}")
        return 1
    except ValueError as error:
        logger.error(f"Invalid input: {error}")
        return 1
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as error:
        logger.exception(f"Unexpected error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
