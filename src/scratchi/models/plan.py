"""Plan data models for parsing insurance plan benefits."""

import logging
import re
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


def normalize_benefit_name(benefit_name: str) -> str:
    """Normalize a benefit name for consistent matching.

    This function normalizes benefit names to handle:
    - Case variations (converts to lowercase)
    - Whitespace variations (strips and collapses multiple spaces)
    - Preserves structure (hyphens, special characters)

    Args:
        benefit_name: The benefit name to normalize

    Returns:
        Normalized benefit name (lowercase, whitespace normalized)

    Examples:
        >>> normalize_benefit_name("Basic Dental Care - Adult")
        'basic dental care - adult'
        >>> normalize_benefit_name("Basic  Dental  Care - Adult ")
        'basic dental care - adult'
        >>> normalize_benefit_name("BASIC DENTAL CARE - ADULT")
        'basic dental care - adult'
    """
    if not benefit_name:
        return ""
    # Convert to lowercase
    normalized = benefit_name.lower()
    # Normalize whitespace: strip and collapse multiple spaces/tabs/newlines to single space
    normalized = re.sub(r"\s+", " ", normalized)
    # Strip leading/trailing whitespace
    normalized = normalized.strip()
    return normalized


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
        # Note: If not covered, most cost-sharing fields should be empty
        # but we don't enforce this strictly as data may have inconsistencies
        # Debug logging removed for performance (called 1.4M+ times)
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


class Plan(BaseModel):
    """Model representing an aggregated insurance plan with all its benefits.

    This model groups multiple PlanBenefit objects by plan_id into a single
    plan object with a dictionary of benefits keyed by normalized benefit_name.

    **Benefit Name Matching:**
    Benefit names are normalized for matching (case-insensitive, whitespace-normalized).
    This means:
    - "Basic Dental Care - Adult" matches "basic dental care - adult"
    - "Basic  Dental  Care - Adult" matches "Basic Dental Care - Adult"
    - Partial matches are NOT supported - "Basic Dental Care" does NOT match "Basic Dental Care - Adult"

    The original benefit names are preserved in the PlanBenefit objects, but lookups
    use normalized keys for consistency.
    """

    plan_id: str = Field(..., description="Unique plan identifier")
    standard_component_id: str = Field(..., description="Standard component identifier")
    benefits: dict[str, PlanBenefit] = Field(
        ...,
        description="Dictionary of benefits keyed by benefit_name",
    )
    state_code: str = Field(..., description="State abbreviation")
    issuer_id: str = Field(..., description="Insurance issuer ID")
    business_year: int = Field(..., description="Plan year")

    @classmethod
    def from_benefits(cls, benefits: list[PlanBenefit]) -> "Plan":
        """Create a Plan from a list of PlanBenefit objects.

        Args:
            benefits: List of PlanBenefit objects for the same plan

        Returns:
            Plan object with aggregated benefits

        Raises:
            ValueError: If benefits list is empty or benefits have inconsistent plan metadata
        """
        if not benefits:
            raise ValueError("Cannot create Plan from empty benefits list")

        # Use first benefit to extract plan-level metadata
        first_benefit = benefits[0]
        plan_id = first_benefit.plan_id
        standard_component_id = first_benefit.standard_component_id
        state_code = first_benefit.state_code
        issuer_id = first_benefit.issuer_id
        business_year = first_benefit.business_year

        # Validate all benefits belong to the same plan
        for benefit in benefits:
            if benefit.plan_id != plan_id:
                raise ValueError(
                    f"All benefits must have the same plan_id. "
                    f"Found {benefit.plan_id} != {plan_id}",
                )
            if benefit.standard_component_id != standard_component_id:
                raise ValueError(
                    f"All benefits must have the same standard_component_id. "
                    f"Found {benefit.standard_component_id} != {standard_component_id}",
                )
            if benefit.state_code != state_code:
                raise ValueError(
                    f"All benefits must have the same state_code. "
                    f"Found {benefit.state_code} != {state_code}",
                )
            if benefit.issuer_id != issuer_id:
                raise ValueError(
                    f"All benefits must have the same issuer_id. "
                    f"Found {benefit.issuer_id} != {issuer_id}",
                )
            if benefit.business_year != business_year:
                raise ValueError(
                    f"All benefits must have the same business_year. "
                    f"Found {benefit.business_year} != {business_year}",
                )

        # Build benefits dictionary keyed by normalized benefit_name
        # This allows case-insensitive and whitespace-normalized lookups
        benefits_dict: dict[str, PlanBenefit] = {}
        original_names: dict[str, str] = {}  # Map normalized -> original for logging
        for benefit in benefits:
            benefit_name = benefit.benefit_name
            normalized_name = normalize_benefit_name(benefit_name)
            
            if normalized_name in benefits_dict:
                logger.warning(
                    f"Duplicate benefit_name (after normalization) '{benefit_name}' "
                    f"(normalized: '{normalized_name}') for plan {plan_id}. "
                    f"Original: '{original_names[normalized_name]}', "
                    f"Duplicate: '{benefit_name}'. Keeping first occurrence.",
                )
            else:
                benefits_dict[normalized_name] = benefit
                original_names[normalized_name] = benefit_name

        return cls(
            plan_id=plan_id,
            standard_component_id=standard_component_id,
            benefits=benefits_dict,
            state_code=state_code,
            issuer_id=issuer_id,
            business_year=business_year,
        )

    def get_benefit(self, benefit_name: str) -> PlanBenefit | None:
        """Get a benefit by name using normalized matching.

        This method performs case-insensitive and whitespace-normalized matching
        to handle variations in benefit names. For example:
        - "Basic Dental Care - Adult" matches "basic dental care - adult"
        - "Basic Dental Care - Adult" matches "Basic  Dental  Care - Adult "

        Args:
            benefit_name: Name of the benefit to retrieve (will be normalized)

        Returns:
            PlanBenefit if found, None otherwise

        Examples:
            >>> plan.get_benefit("Basic Dental Care - Adult")
            <PlanBenefit ...>
            >>> plan.get_benefit("basic dental care - adult")
            <PlanBenefit ...>
            >>> plan.get_benefit("Basic  Dental  Care - Adult ")
            <PlanBenefit ...>
        """
        normalized_name = normalize_benefit_name(benefit_name)
        return self.benefits.get(normalized_name)

    def has_benefit(self, benefit_name: str) -> bool:
        """Check if plan has a specific benefit using normalized matching.

        Args:
            benefit_name: Name of the benefit to check (will be normalized)

        Returns:
            True if benefit exists, False otherwise
        """
        normalized_name = normalize_benefit_name(benefit_name)
        return normalized_name in self.benefits

    def get_covered_benefits(self) -> dict[str, PlanBenefit]:
        """Get all covered benefits.

        Returns:
            Dictionary of covered benefits keyed by benefit_name
        """
        return {
            name: benefit
            for name, benefit in self.benefits.items()
            if benefit.is_covered_bool()
        }

    def get_ehb_benefits(self) -> dict[str, PlanBenefit]:
        """Get all Essential Health Benefits.

        Returns:
            Dictionary of EHB benefits keyed by benefit_name
        """
        return {
            name: benefit
            for name, benefit in self.benefits.items()
            if benefit.is_ehb_bool() is True
        }

    model_config = ConfigDict(frozen=True)  # Make models immutable after creation
