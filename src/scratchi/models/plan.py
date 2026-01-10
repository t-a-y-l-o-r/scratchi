"""Plan data models for parsing insurance plan benefits."""

import logging
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scratchi.models.constants import (
    NO_CHARGE,
    NOT_APPLICABLE,
    NOT_COVERED,
    CoverageStatus,
    EHBStatus,
    EHBVarReason,
    YesNoStatus,
)

logger = logging.getLogger(__name__)


class PlanBenefit(BaseModel):
    """Model representing a single benefit for a health insurance plan.

    This model corresponds to a single row in the benefits CSV file.
    Handles special values like "Not Applicable", "Not Covered", percentages,
    and Yes/No strings.
    """

    business_year: int = Field(..., description="Plan year")
    state_code: str = Field(..., description="State abbreviation")
    issuer_id: str = Field(..., description="Insurance issuer ID")
    source_name: str = Field(..., description="Data source name")
    import_date: date = Field(..., description="Date data was imported")
    standard_component_id: str = Field(..., description="Standard component identifier")
    plan_id: str = Field(..., description="Unique plan identifier")
    benefit_name: str = Field(..., description="Name of the benefit")

    @field_validator("business_year", mode="before")
    @classmethod
    def parse_business_year(cls, value: Any) -> int:
        """Parse business year - convert string to int."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value.strip())
        raise ValueError(f"Invalid business year format: {value}")

    @field_validator("issuer_id", "state_code", "source_name", "standard_component_id", "plan_id", "benefit_name", mode="before")
    @classmethod
    def normalize_required_string(cls, value: Any) -> str:
        """Normalize required string fields - convert to string and strip."""
        if value == "" or value is None:
            raise ValueError(f"Required field cannot be empty: {value}")
        return str(value).strip()
    copay_inn_tier1: str | None = Field(
        default=None,
        description="In-network tier 1 copay (or 'Not Applicable')",
    )
    copay_inn_tier2: str | None = Field(
        default=None,
        description="In-network tier 2 copay (or 'Not Applicable')",
    )
    copay_outof_net: str | None = Field(
        default=None,
        description="Out-of-network copay (or 'Not Applicable')",
    )
    coins_inn_tier1: str | None = Field(
        default=None,
        description="In-network tier 1 coinsurance (percentage or 'Not Applicable')",
    )
    coins_inn_tier2: str | None = Field(
        default=None,
        description="In-network tier 2 coinsurance (percentage or 'Not Applicable')",
    )
    coins_outof_net: str | None = Field(
        default=None,
        description="Out-of-network coinsurance (percentage or 'Not Applicable')",
    )
    is_ehb: str | None = Field(
        default=None,
        description="Essential Health Benefit status: 'Yes', 'No', 'Not EHB', or None",
    )
    is_covered: str | None = Field(
        default=None,
        description="Coverage status: 'Covered', 'Not Covered', or None",
    )
    quant_limit_on_svc: str | None = Field(
        default=None,
        description="Whether quantity limit applies: 'Yes', 'No', or None",
    )
    limit_qty: float | None = Field(
        default=None,
        description="Quantity limit value (e.g., 2.0)",
    )
    limit_unit: str | None = Field(
        default=None,
        description="Unit for quantity limit (e.g., 'Exam(s) per Year')",
    )
    exclusions: str | None = Field(
        default=None,
        description="Exclusions text",
    )
    explanation: str | None = Field(
        default=None,
        description="Additional explanation text",
    )
    ehb_var_reason: str | None = Field(
        default=None,
        description="EHB variation reason (e.g., 'Substantially Equal', 'Not EHB')",
    )
    is_excl_from_inn_moop: str | None = Field(
        default=None,
        description="Excluded from in-network MOOP: 'Yes', 'No', or None",
    )
    is_excl_from_oon_moop: str | None = Field(
        default=None,
        description="Excluded from out-of-network MOOP: 'Yes', 'No', or None",
    )

    @field_validator("copay_inn_tier1", "copay_inn_tier2", "copay_outof_net", mode="before")
    @classmethod
    def normalize_copay(cls, value: Any) -> str | None:
        """Normalize copay values - convert empty strings to None."""
        if value == "" or value is None:
            return None
        return str(value).strip()

    @field_validator(
        "coins_inn_tier1",
        "coins_inn_tier2",
        "coins_outof_net",
        mode="before",
    )
    @classmethod
    def normalize_coinsurance(cls, value: Any) -> str | None:
        """Normalize coinsurance values - convert empty strings to None."""
        if value == "" or value is None:
            return None
        return str(value).strip()

    @field_validator("import_date", mode="before")
    @classmethod
    def parse_date(cls, value: Any) -> date:
        """Parse import date from string format YYYY-MM-DD."""
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value.strip())
        raise ValueError(f"Invalid date format: {value}")

    @field_validator("limit_qty", mode="before")
    @classmethod
    def parse_limit_qty(cls, value: Any) -> float | None:
        """Parse limit quantity - convert empty strings to None."""
        if value == "" or value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse limit_qty as float: {value}")
            return None

    @field_validator(
        "is_ehb",
        "is_covered",
        "quant_limit_on_svc",
        "is_excl_from_inn_moop",
        "is_excl_from_oon_moop",
        mode="before",
    )
    @classmethod
    def normalize_yes_no(cls, value: Any) -> str | None:
        """Normalize Yes/No fields - convert empty strings to None."""
        if value == "" or value is None:
            return None
        return str(value).strip()

    @field_validator(
        "limit_unit",
        "exclusions",
        "explanation",
        "ehb_var_reason",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: Any) -> str | None:
        """Normalize text fields - convert empty strings to None."""
        if value == "" or value is None:
            return None
        return str(value).strip()

    @model_validator(mode="after")
    def validate_covered_status(self) -> "PlanBenefit":
        """Validate that coverage status makes sense with other fields."""
        if self.is_covered == CoverageStatus.NOT_COVERED:
            # If not covered, most cost-sharing fields should be empty
            # but we don't enforce this strictly as data may have inconsistencies
            logger.debug(
                f"Plan {self.plan_id} benefit {self.benefit_name} is not covered",
            )
        return self

    def get_coinsurance_rate(self, field: str) -> float | None:
        """Extract numeric coinsurance rate from percentage string.

        Args:
            field: One of 'coins_inn_tier1', 'coins_inn_tier2', 'coins_outof_net'

        Returns:
            Float percentage (0-100) or None if not applicable/not found
        """
        value = getattr(self, field, None)
        if value is None:
            return None

        if NOT_APPLICABLE in value or NOT_COVERED in value:
            return None

        # Try to extract percentage value (e.g., "35.00%" -> 35.0)
        if "%" in value:
            try:
                # Extract numeric part before %
                numeric_part = value.split("%")[0].strip()
                return float(numeric_part)
            except (ValueError, IndexError):
                logger.warning(f"Could not parse coinsurance percentage: {value}")
                return None

        # Handle cases like "No Charge" or other non-percentage strings
        if NO_CHARGE in value or "No charge" in value:
            return 0.0

        return None

    def is_covered_bool(self) -> bool:
        """Return True if benefit is covered, False otherwise."""
        return self.is_covered == CoverageStatus.COVERED

    def is_ehb_bool(self) -> bool | None:
        """Return True if EHB, False if explicitly not EHB, None if unknown."""
        if self.is_ehb == EHBStatus.YES:
            return True
        if self.is_ehb == EHBStatus.NO or self.is_ehb == EHBStatus.NOT_EHB:
            return False
        return None

    def has_quantity_limit(self) -> bool:
        """Return True if quantity limit applies to this service."""
        return self.quant_limit_on_svc == YesNoStatus.YES

    def is_excluded_from_inn_moop_bool(self) -> bool | None:
        """Return True if excluded from in-network MOOP, False if not, None if unknown."""
        if self.is_excl_from_inn_moop == YesNoStatus.YES:
            return True
        if self.is_excl_from_inn_moop == YesNoStatus.NO:
            return False
        return None

    def is_excluded_from_oon_moop_bool(self) -> bool | None:
        """Return True if excluded from out-of-network MOOP, False if not, None if unknown."""
        if self.is_excl_from_oon_moop == YesNoStatus.YES:
            return True
        if self.is_excl_from_oon_moop == YesNoStatus.NO:
            return False
        return None

    model_config = ConfigDict(frozen=True)  # Make models immutable after creation
