"""Main module for the scratchi package."""

import logging
import sys
from pathlib import Path

from scratchi.data_loader import load_plans_from_csv

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Override any existing configuration
    )


def main() -> int:
    """Main entry point for the application.

    Loads and displays plan data from the sample CSV file.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    _configure_logging()
    
    # Find the sample CSV file relative to the project root
    project_root = Path(__file__).parent.parent.parent
    csv_path = project_root / "data" / "sample.csv"

    if not csv_path.exists():
        logger.error(f"Sample CSV file not found: {csv_path}")
        return 1

    try:
        logger.info(f"Loading plan data from {csv_path}")
        benefits = load_plans_from_csv(csv_path)

        logger.info(f"Successfully loaded {len(benefits)} plan benefits")
        logger.info("")

        # Display statistics
        unique_plans = {benefit.plan_id for benefit in benefits}
        unique_benefits = {benefit.benefit_name for benefit in benefits}
        unique_states = {benefit.state_code for benefit in benefits}

        logger.info("Summary Statistics:")
        logger.info(f"  Total plan benefits: {len(benefits)}")
        logger.info(f"  Unique plans: {len(unique_plans)}")
        logger.info(f"  Unique benefit types: {len(unique_benefits)}")
        logger.info(f"  States: {', '.join(sorted(unique_states))}")
        logger.info("")

        # Display sample data (first 3 benefits)
        logger.info("Sample Benefits (first 3):")
        for i, benefit in enumerate(benefits[:3], 1):
            logger.info(f"  {i}. {benefit.benefit_name}")
            logger.info(f"     Plan: {benefit.plan_id}")
            logger.info(f"     State: {benefit.state_code}")
            logger.info(f"     Covered: {benefit.is_covered or 'N/A'}")
            if benefit.coins_inn_tier1:
                logger.info(f"     Coinsurance (Tier 1): {benefit.coins_inn_tier1}")
            logger.info("")

        return 0

    except FileNotFoundError as error:
        logger.error(f"CSV file not found: {error}")
        return 1
    except ValueError as error:
        logger.error(f"Failed to load CSV: {error}")
        return 1
    except Exception as error:
        logger.exception(f"Unexpected error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
