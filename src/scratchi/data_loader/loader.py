"""CSV loader for plan benefits data.

Performance Notes:
- Using Polars for high-performance CSV reading (5-10x faster than pandas)
- See docs/polars-migration-plan.md for migration details
- Current optimizations: iter_rows(), pre-computed field mappings, removed row.to_dict()
"""

import logging
from pathlib import Path
from typing import Any

import polars as pl

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


def _build_column_index_mapping(df: pl.DataFrame) -> list[tuple[int, str]]:
    """Build list of (tuple_index, model_field) pairs for efficient row parsing.

    Args:
        df: Polars DataFrame with CSV data

    Returns:
        List of (column_index, model_field_name) tuples for columns that exist
    """
    field_mappings: list[tuple[int, str]] = []
    column_names = df.columns
    for csv_column_enum, model_field in CSV_COLUMN_MAPPING.items():
        csv_column_name = csv_column_enum.value
        if csv_column_name in column_names:
            idx = column_names.index(csv_column_name)
            field_mappings.append((idx, model_field))
        else:
            logger.warning(f"Missing column '{csv_column_name}' in CSV file")
    return field_mappings


def parse_plan_benefit_from_tuple(
    row_tuple: tuple[Any, ...],
    field_mappings: list[tuple[int, str]],
) -> PlanBenefit:
    """Parse a row tuple from Polars iter_rows into a PlanBenefit model.

    Args:
        row_tuple: Tuple from df.iter_rows() containing row values
        field_mappings: Pre-computed list of (tuple_index, model_field) pairs

    Returns:
        PlanBenefit model instance

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Build mapped_data dict directly from pre-computed index/field pairs
    # Tuple elements correspond directly to DataFrame columns in order
    mapped_data: dict[str, Any] = {}
    for idx, model_field in field_mappings:
        value = row_tuple[idx]
        # Convert Polars null to empty string for consistency with validators
        mapped_data[model_field] = "" if value is None else value

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


def load_plans_dataframe(csv_path: str | Path) -> pl.DataFrame:
    """Load plan benefits from CSV file as a Polars DataFrame (lazy loading).
    
    This function loads the CSV without converting rows to Pydantic models,
    enabling efficient operations on the DataFrame. Convert rows to models
    only when needed using convert_row_to_plan_benefit().
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Polars DataFrame with plan benefits data
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV parsing fails or file is empty
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"Loading plan data from {csv_path}")
    
    try:
        # Read CSV with Polars - handles empty values and special characters
        # Polars reads all columns as strings by default, nulls are handled as None
        df = pl.read_csv(
            path,
            infer_schema_length=0,  # Read all columns as strings initially
            null_values=[""],  # Treat empty strings as null
        )
        
        # Check for empty DataFrame
        if df.height == 0:
            raise ValueError(f"CSV file is empty: {csv_path}")
        
        logger.info(f"Loaded {df.height} rows from CSV")
        return df
        
    except pl.exceptions.NoDataError as error:
        raise ValueError(f"CSV file is empty: {csv_path}") from error
    except pl.exceptions.ComputeError as error:
        raise ValueError(f"Failed to parse CSV file: {csv_path}") from error
    except Exception as error:
        logger.error(f"Unexpected error loading CSV: {error}")
        raise


def convert_dataframe_rows_to_benefits(
    df: pl.DataFrame,
    n_rows: int | None = None,
) -> list[PlanBenefit]:
    """Convert DataFrame rows to PlanBenefit models.
    
    Args:
        df: Polars DataFrame with plan benefits data
        n_rows: Optional number of rows to convert (from the start). If None, converts all rows.
    
    Returns:
        List of PlanBenefit models
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    if n_rows is None:
        rows_to_convert = df
    else:
        rows_to_convert = df.head(n_rows)
    
    # Pre-compute field mappings for efficient conversion
    field_mappings = _build_column_index_mapping(rows_to_convert)
    
    benefits: list[PlanBenefit] = []
    for row_tuple in rows_to_convert.iter_rows(named=False):
        try:
            benefit = parse_plan_benefit_from_tuple(row_tuple, field_mappings)
            benefits.append(benefit)
        except Exception as error:
            logger.warning(f"Failed to parse row: {error}")
            # Continue processing other rows
    
    return benefits


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
        # Read CSV with Polars - handles empty values and special characters
        # Polars reads all columns as strings by default, nulls are handled as None
        df = pl.read_csv(
            path,
            infer_schema_length=0,  # Read all columns as strings initially
            null_values=[""],  # Treat empty strings as null
        )

        # Check for empty DataFrame
        if df.height == 0:
            raise ValueError(f"CSV file is empty: {csv_path}")

        logger.info(f"Loaded {len(df)} rows from CSV")

        # Pre-compute field mappings once (performance optimization)
        # Returns list of (tuple_index, model_field) pairs for direct access
        field_mappings = _build_column_index_mapping(df)

        benefits: list[PlanBenefit] = []
        errors: list[tuple[int, str]] = []

        # Use iter_rows() for efficient iteration - returns tuples
        for row_num, row_tuple in enumerate(df.iter_rows(named=False), start=1):
            try:
                benefit = parse_plan_benefit_from_tuple(row_tuple, field_mappings)
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

    except pl.exceptions.NoDataError as error:
        raise ValueError(f"CSV file is empty: {csv_path}") from error
    except pl.exceptions.ComputeError as error:
        raise ValueError(f"Failed to parse CSV file: {csv_path}") from error
    except Exception as error:
        logger.error(f"Unexpected error loading CSV: {error}")
        raise
