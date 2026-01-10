"""CSV loader for plan benefits data."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from scratchi.models.constants import CSVColumn
from scratchi.models.plan import PlanBenefit

logger = logging.getLogger(__name__)

# CSV column mapping to model field names using Enum keys
CSV_COLUMN_MAPPING: dict[CSVColumn, str] = {
    CSVColumn.BUSINESS_YEAR: "business_year",
    CSVColumn.STATE_CODE: "state_code",
    CSVColumn.ISSUER_ID: "issuer_id",
    CSVColumn.SOURCE_NAME: "source_name",
    CSVColumn.IMPORT_DATE: "import_date",
    CSVColumn.STANDARD_COMPONENT_ID: "standard_component_id",
    CSVColumn.PLAN_ID: "plan_id",
    CSVColumn.BENEFIT_NAME: "benefit_name",
    CSVColumn.COPAY_INN_TIER1: "copay_inn_tier1",
    CSVColumn.COPAY_INN_TIER2: "copay_inn_tier2",
    CSVColumn.COPAY_OUTOF_NET: "copay_outof_net",
    CSVColumn.COINS_INN_TIER1: "coins_inn_tier1",
    CSVColumn.COINS_INN_TIER2: "coins_inn_tier2",
    CSVColumn.COINS_OUTOF_NET: "coins_outof_net",
    CSVColumn.IS_EHB: "is_ehb",
    CSVColumn.IS_COVERED: "is_covered",
    CSVColumn.QUANT_LIMIT_ON_SVC: "quant_limit_on_svc",
    CSVColumn.LIMIT_QTY: "limit_qty",
    CSVColumn.LIMIT_UNIT: "limit_unit",
    CSVColumn.EXCLUSIONS: "exclusions",
    CSVColumn.EXPLANATION: "explanation",
    CSVColumn.EHB_VAR_REASON: "ehb_var_reason",
    CSVColumn.IS_EXCL_FROM_INN_MOOP: "is_excl_from_inn_moop",
    CSVColumn.IS_EXCL_FROM_OON_MOOP: "is_excl_from_oon_moop",
}


def _build_column_index_mapping(df: pd.DataFrame) -> dict[str, int]:
    """Build mapping from CSV column name to DataFrame column index.

    Args:
        df: DataFrame with CSV data

    Returns:
        Dictionary mapping CSV column names to their index positions
    """
    column_indices: dict[str, int] = {}
    for csv_column_enum in CSVColumn:
        csv_column_name = csv_column_enum.value
        if csv_column_name in df.columns:
            column_indices[csv_column_name] = df.columns.get_loc(csv_column_name)
        else:
            logger.warning(f"Missing column '{csv_column_name}' in CSV file")
    return column_indices


def parse_plan_benefit_from_tuple(
    row_tuple: tuple[Any, ...],
    column_indices: dict[str, int],
) -> PlanBenefit:
    """Parse a row tuple from itertuples into a PlanBenefit model.

    Args:
        row_tuple: Tuple from df.itertuples() containing row values
        column_indices: Mapping from CSV column names to tuple indices

    Returns:
        PlanBenefit model instance

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Map CSV column names to model field names using pre-computed indices
    # With index=False, tuple elements correspond directly to DataFrame columns in order
    mapped_data: dict[str, Any] = {}
    for csv_column_enum, model_field in CSV_COLUMN_MAPPING.items():
        csv_column_name = csv_column_enum.value
        if csv_column_name in column_indices:
            idx = column_indices[csv_column_name]
            mapped_data[model_field] = row_tuple[idx]

    try:
        return PlanBenefit(**mapped_data)
    except Exception as error:
        logger.error(f"Failed to parse row: {mapped_data}")
        raise ValueError(f"Invalid row data: {error}") from error


def parse_plan_benefit_row(row: dict[str, Any]) -> PlanBenefit:
    """Parse a single CSV row into a PlanBenefit model.

    Args:
        row: Dictionary with CSV column names as string keys

    Returns:
        PlanBenefit model instance

    Raises:
        ValueError: If required fields are missing or invalid

    Note:
        This function is kept for backwards compatibility with tests.
        For performance, use parse_plan_benefit_from_tuple() instead.
    """
    # Map CSV column names (strings from CSV) to model field names using Enum mapping
    mapped_data: dict[str, Any] = {}
    for csv_column_enum, model_field in CSV_COLUMN_MAPPING.items():
        # Convert Enum value (string) to match CSV header
        csv_column_name = csv_column_enum.value
        if csv_column_name in row:
            mapped_data[model_field] = row[csv_column_name]
        else:
            logger.warning(f"Missing column '{csv_column_name}' in CSV row")

    try:
        return PlanBenefit(**mapped_data)
    except Exception as error:
        logger.error(f"Failed to parse row: {mapped_data}")
        raise ValueError(f"Invalid row data: {error}") from error


def load_plans_from_csv(csv_path: str | Path) -> list[PlanBenefit]:
    """Load plan benefits from CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        List of PlanBenefit models

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV parsing fails
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info(f"Loading plan data from {csv_path}")

    try:
        # Read CSV with pandas - handles empty values and special characters
        df = pd.read_csv(
            path,
            dtype=str,  # Keep everything as string initially for validation
            keep_default_na=False,  # Don't convert empty strings to NaN
            na_values=[""],  # Treat empty strings as NaN for pandas
        )

        # Replace NaN with empty strings for our validators
        df = df.fillna("")

        logger.info(f"Loaded {len(df)} rows from CSV")

        # Pre-compute column index mapping once (performance optimization)
        column_indices = _build_column_index_mapping(df)

        benefits: list[PlanBenefit] = []
        errors: list[tuple[int, str]] = []

        # Use itertuples() instead of iterrows() for 10-100x performance improvement
        # index=False means we don't include the DataFrame index in the tuple
        for row_num, row_tuple in enumerate(df.itertuples(index=False, name=None), start=1):
            try:
                benefit = parse_plan_benefit_from_tuple(row_tuple, column_indices)
                benefits.append(benefit)
            except Exception as error:
                # row_num is 1-based from enumerate, add 1 for header row
                actual_row_num = row_num + 1
                error_msg = f"Row {actual_row_num}: {error}"
                errors.append((actual_row_num, str(error)))
                logger.warning(error_msg)

        if errors:
            logger.warning(
                f"Failed to parse {len(errors)} rows. "
                f"Successfully parsed {len(benefits)} rows.",
            )
            # Log first few errors for debugging
            for row_num, error_msg in errors[:5]:
                logger.warning(f"  Row {row_num}: {error_msg}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors")

        if not benefits:
            raise ValueError("No valid plan benefits found in CSV file")

        logger.info(f"Successfully parsed {len(benefits)} plan benefits")
        return benefits

    except pd.errors.EmptyDataError as error:
        raise ValueError(f"CSV file is empty: {csv_path}") from error
    except pd.errors.ParserError as error:
        raise ValueError(f"Failed to parse CSV file: {csv_path}") from error
    except Exception as error:
        logger.error(f"Unexpected error loading CSV: {error}")
        raise
