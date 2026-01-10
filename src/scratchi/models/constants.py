"""Constants and Enums for plan benefit data models."""

from enum import StrEnum


class CoverageStatus(StrEnum):
    """Coverage status values for plan benefits."""

    COVERED = "Covered"
    NOT_COVERED = "Not Covered"


class YesNoStatus(StrEnum):
    """Yes/No status values used in various fields."""

    YES = "Yes"
    NO = "No"


class EHBStatus(StrEnum):
    """Essential Health Benefit status values."""

    YES = "Yes"
    NO = "No"
    NOT_EHB = "Not EHB"


class EHBVarReason(StrEnum):
    """EHB variation reason values."""

    NOT_EHB = "Not EHB"
    SUBSTANTIALLY_EQUAL = "Substantially Equal"


class CSVColumn(StrEnum):
    """CSV column names from the benefits and cost-sharing data file."""

    BUSINESS_YEAR = "BusinessYear"
    STATE_CODE = "StateCode"
    ISSUER_ID = "IssuerId"
    SOURCE_NAME = "SourceName"
    IMPORT_DATE = "ImportDate"
    STANDARD_COMPONENT_ID = "StandardComponentId"
    PLAN_ID = "PlanId"
    BENEFIT_NAME = "BenefitName"
    COPAY_INN_TIER1 = "CopayInnTier1"
    COPAY_INN_TIER2 = "CopayInnTier2"
    COPAY_OUTOF_NET = "CopayOutofNet"
    COINS_INN_TIER1 = "CoinsInnTier1"
    COINS_INN_TIER2 = "CoinsInnTier2"
    COINS_OUTOF_NET = "CoinsOutofNet"
    IS_EHB = "IsEHB"
    IS_COVERED = "IsCovered"
    QUANT_LIMIT_ON_SVC = "QuantLimitOnSvc"
    LIMIT_QTY = "LimitQty"
    LIMIT_UNIT = "LimitUnit"
    EXCLUSIONS = "Exclusions"
    EXPLANATION = "Explanation"
    EHB_VAR_REASON = "EHBVarReason"
    IS_EXCL_FROM_INN_MOOP = "IsExclFromInnMOOP"
    IS_EXCL_FROM_OON_MOOP = "IsExclFromOonMOOP"


# Constants for special cost-sharing values
NOT_APPLICABLE = "Not Applicable"
NOT_COVERED = "Not Covered"  # Same as CoverageStatus.NOT_COVERED but used in cost-sharing context
NO_CHARGE = "No Charge"
