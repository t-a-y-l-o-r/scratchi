"""User profiling agent for extracting preferences and requirements."""

from scratchi.profiling.agent import (
    create_profile_from_dict,
    create_profile_from_natural_language,
    extract_family_composition,
    infer_expected_usage,
)

__all__ = [
    "create_profile_from_dict",
    "create_profile_from_natural_language",
    "extract_family_composition",
    "infer_expected_usage",
]
