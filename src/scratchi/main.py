"""Main module for the scratchi package."""

import logging
import sys

import polars as pl

from scratchi.config import settings
from scratchi.data_loader import convert_dataframe_rows_to_benefits, load_plans_dataframe
from scratchi.models.constants import CSVColumn

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure logging for the application using settings."""
    logging.basicConfig(
        level=settings.logging_level_int,
        format=settings.log_format,
        datefmt=settings.log_date_format,
        force=True,  # Override any existing configuration
    )


def main() -> int:
    """Main entry point for the application.

    Loads and displays plan data from the sample CSV file.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    _configure_logging()

    csv_path = settings.csv_path

    if not csv_path.exists():
        logger.error(f"Sample CSV file not found: {csv_path}")
        return 1

    try:
        logger.info(f"Loading plan data from {csv_path}")
        # Load data as DataFrame (lazy - no model conversion yet)
        df = load_plans_dataframe(csv_path)

        logger.info(f"Successfully loaded {df.height} rows from CSV")
        logger.info("")

        # Compute statistics directly on DataFrame (very fast)
        total_rows = df.height
        unique_plans_count = df.select(pl.col(CSVColumn.PLAN_ID.value).n_unique()).item()
        unique_benefits_count = df.select(pl.col(CSVColumn.BENEFIT_NAME.value).n_unique()).item()
        unique_states = (
            df.select(pl.col(CSVColumn.STATE_CODE.value).unique().sort())
            .get_column(CSVColumn.STATE_CODE.value)
            .to_list()
        )

        logger.info("Summary Statistics:")
        logger.info(f"  Total plan benefits: {total_rows}")
        logger.info(f"  Unique plans: {unique_plans_count}")
        logger.info(f"  Unique benefit types: {unique_benefits_count}")
        logger.info(f"  States: {', '.join(unique_states)}")
        logger.info("")

        # Only convert the sample rows to models (lazy conversion)
        sample_count = settings.sample_display_count
        sample_benefits = convert_dataframe_rows_to_benefits(df, n_rows=sample_count)

        logger.info(f"Sample Benefits (first {sample_count}):")
        for i, benefit in enumerate(sample_benefits, 1):
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
